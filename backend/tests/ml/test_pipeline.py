"""Existing focused ML checks adapted to the next-day product contract."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from app.ml.common import ROOT, HEADER, check_sequence, load_config, validate_splits
from app.ml.features import FEATURES, build_features, engineer_bin, engineer_bins, inference_row, registry_features
from viptop_fill.features import build_next_day_features
from viptop_fill.runtime import FillPredictor, model_input, validate_probabilities
from app.ml.modeling import fit_model, sample_features
from app.ml.evaluation import Metrics

def bin_fixture(bin_id=1):
    dates = pd.date_range('2025-01-01', periods=120)
    status = np.where(np.arange(120) % 3 == 1, 'collected', 'none')
    success = pd.Series(status == 'collected')
    fill = np.full(120, np.nan)
    indices = np.flatnonzero(success)[1:]
    fill[indices] = np.arange(len(indices)) % 5
    frame = pd.DataFrame({'bin_id': bin_id, 'date': dates, 'day_of_week': dates.isocalendar().day.to_numpy(),
                          'week_of_year': dates.isocalendar().week.to_numpy(), 'month': dates.month,
                          'season': (dates.month % 12) // 3 + 1, 'site_id': bin_id,
                          'waste_type': 'Mixed municipal waste', 'capacity_m3': 1.1,
                          'sub_district': 'Panerių sen.', 'object_group': 'Komercinė paskirtis',
                          'population_cell_id': 1, 'resident_factor': 0., 'collection_status': status,
                          'holidays_since_last_collection': 0,
                          'collections_last_28d': success.astype(int).shift(1, fill_value=0).rolling(28, min_periods=1).sum(),
                          'missed_collections_28d': 0, 'fill_level': fill,
                          'qr_alerts': np.where(np.arange(120) <= 1, np.nan, 0.)})
    return frame[HEADER]


class FeatureTests(unittest.TestCase):
    def test_batched_history_matches_individual_bins(self):
        first, second = bin_fixture(1), bin_fixture(2)
        second['fill_level'] = second.fill_level.where(second.fill_level.isna(), 4 - second.fill_level)
        mapping = {'Panerių sen.': 'Paneriai'}
        combined = engineer_bins(pd.concat([first, second], ignore_index=True), mapping)
        independent = pd.concat([engineer_bin(first, mapping), engineer_bin(second, mapping)], ignore_index=True)
        pd.testing.assert_frame_equal(combined, independent)
        self.assertTrue(pd.isna(combined.loc[len(first), 'previous_worker_rating']))
        self.assertEqual(combined.loc[len(first), 'history_label_count'], 0)

    def test_lags_precede_current_day_and_preserve_unlabeled_days(self):
        raw = bin_fixture()
        engineered = engineer_bin(raw, {'Panerių sen.': 'Paneriai'})
        self.assertEqual(engineered.loc[5, 'previous_worker_rating'], raw.loc[4, 'fill_level'])
        self.assertTrue(pd.isna(engineered.loc[4, 'previous_worker_rating']))
        self.assertEqual(engineered.loc[5, 'days_since_last_successful_collection'], 1)
        self.assertEqual(engineered.loc[5, 'days_since_previous_worker_rating'], 1)
        self.assertEqual(engineered.loc[5, 'collections_last_28d'], raw.loc[5, 'collections_last_28d'])

    def test_current_and_future_outcome_perturbation(self):
        raw = bin_fixture()
        day = raw.date.iloc[80]
        before = inference_row(raw, day, {'Panerių sen.': 'Paneriai'})
        changed = raw.copy()
        changed.loc[changed.date >= day, 'fill_level'] = 4
        changed.loc[changed.date >= day, 'collection_status'] = 'missed'
        after = inference_row(changed, day, {'Panerių sen.': 'Paneriai'})
        pd.testing.assert_frame_equal(before[FEATURES], after[FEATURES])

    def test_zero_and_missing_are_distinct(self):
        raw = bin_fixture()
        raw.loc[10, 'qr_alerts'] = np.nan
        features = engineer_bin(raw, {'Panerių sen.': 'Paneriai'})
        self.assertTrue(pd.isna(features.loc[10, 'qr_alerts']))
        self.assertEqual(features.loc[11, 'qr_alerts'], 0)
        self.assertEqual(features.loc[11, 'resident_factor'], 0)
        self.assertIn('missing_qr_history', features.loc[10, 'input_quality_flag'])
        self.assertNotIn('missing_qr_history', features.loc[11, 'input_quality_flag'])

    def test_duplicate_gap_and_wrong_bin_rejected(self):
        frame = bin_fixture()
        with self.assertRaises(ValueError):
            check_sequence(pd.concat([frame, frame.iloc[[0]]]))
        with self.assertRaises(ValueError):
            check_sequence(frame.drop(index=5))
        frame.loc[5, 'bin_id'] = 2
        with self.assertRaises(ValueError):
            check_sequence(frame)

    def test_future_qr_reset_and_unknown(self):
        raw = bin_fixture()
        day = raw.date.iloc[-1] + pd.Timedelta(days=1)
        raw.loc[raw.index[-1], 'collection_status'] = 'collected'
        reset = inference_row(raw, day, {'Panerių sen.': 'Paneriai'})
        self.assertEqual(reset.qr_alerts.iloc[0], 0)
        raw.loc[raw.index[-1], 'collection_status'] = 'none'
        unknown = inference_row(raw, day, {'Panerių sen.': 'Paneriai'})
        self.assertTrue(pd.isna(unknown.qr_alerts.iloc[0]))
        integer_season = unknown.copy(); integer_season['season'] = '2'
        decimal_season = unknown.copy(); decimal_season['season'] = '2.0'
        self.assertEqual(model_input(integer_season).season.iloc[0], model_input(decimal_season).season.iloc[0])

    def test_probability_validation(self):
        validate_probabilities(np.eye(5))
        for values in [np.ones((2, 5)), np.full((2, 5), np.nan), np.ones((2, 4))]:
            with self.assertRaises(ValueError):
                validate_probabilities(values)

    def test_metric_equivalence(self):
        from sklearn.metrics import f1_score, cohen_kappa_score, log_loss
        y = np.array([0, 1, 2, 3, 4, 4])
        p = np.eye(5)[[0, 2, 2, 4, 4, 1]] * .8 + .04
        metrics = Metrics(); metrics.add(y, p); report = metrics.report()
        self.assertAlmostEqual(report['macro_f1'], f1_score(y, p.argmax(1), average='macro'))
        self.assertAlmostEqual(report['quadratic_weighted_kappa'], cohen_kappa_score(y, p.argmax(1), weights='quadratic'))
        self.assertAlmostEqual(report['log_loss'], log_loss(y, p))

    def test_combined_urgent_probability_and_threshold(self):
        from sklearn.metrics import precision_score, recall_score, f1_score
        from app.ml.evaluation import prediction_frame, select_operational_threshold
        y = np.array([3, 4, 2, 0])
        p = np.array([[0, 0, .4, .3, .3], [0, 0, .4, .2, .4], [.1, .1, .5, .2, .1], [.6, .2, .1, .05, .05]])
        metrics = Metrics(.5); metrics.add(y, p); report = metrics.report()
        urgent = p[:, 3:].sum(axis=1) >= .5
        self.assertAlmostEqual(report['needs_collection_f1'], f1_score(y >= 3, urgent))
        self.assertAlmostEqual(report['needs_collection_precision'], precision_score(y >= 3, urgent))
        self.assertAlmostEqual(report['needs_collection_recall'], recall_score(y >= 3, urgent))
        self.assertLess(report['argmax_needs_collection_f1'], report['needs_collection_f1'])
        frame = prediction_frame(pd.DataFrame({'bin_id': range(4)}), p, 'fixture', 'validation', .5)
        self.assertEqual(frame.predicted_fill_level.iloc[0], 2)
        self.assertEqual(frame.needs_collection.iloc[0], 1)
        threshold, curve = select_operational_threshold(y, p)
        self.assertEqual(threshold, .5)
        self.assertEqual(len(curve), 19)


class FixtureIntegration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'backend/data/ml')
        self.folder=Path(self.temp.name)
        self.config=load_config(ROOT/'backend/configs/ml.yaml'); c=self.config
        c['paths'].update(daily=str(self.folder/'daily.csv'),registry=str(self.folder/'bins_1.csv'),population=str(self.folder/'population.csv'),output=str(self.folder/'output'))
        c['expected'].update(rows=240,daily_bins=2,registry_bins=3,start='2025-01-01',end='2025-04-30')
        c['splits']={'calibration':['2025-01-01','2025-02-09'],'train':['2025-02-10','2025-03-21'],'validation':['2025-03-22','2025-04-10'],'test':['2025-04-11','2025-04-30']}
        c['final_train']=['2025-02-10','2025-04-10']; c['demo_today']=['2025-04-10','2025-04-29']
        c['folds']=[{'train':['2025-02-10','2025-03-01'],'validation':['2025-03-02','2025-03-21']}]
        c['prediction_date']='2025-04-15'; c['search']['device']='cpu'; c['sampling']['final_rows']=60
        c['processing'].update(csv_chunk_rows=71,parquet_batch_rows=100)
        self.raw=pd.concat([bin_fixture(1),bin_fixture(2)],ignore_index=True); self.raw.to_csv(c['paths']['daily'],index=False)
        self.registry=self.raw.groupby('bin_id').first().reset_index()[['bin_id','site_id','waste_type','capacity_m3','sub_district','object_group']].rename(columns={'bin_id':'id'})
        cold=self.registry.iloc[[0]].copy(); cold['id']=3; cold['site_id']=3; cold['capacity_m3']=0
        self.registry=pd.concat([self.registry,cold],ignore_index=True); self.registry.to_csv(c['paths']['registry'],index=False)
        pd.DataFrame({'id':[1,2,3]}).to_csv(self.folder/'sites_1.csv',index=False)
        pd.DataFrame(columns=['id','bin_id','date','fill_level']).to_csv(self.folder/'bin_hist_1.csv',index=False)
        self.population=pd.DataFrame({'bin_id':[1,2,3],'population_cell_id':[1,1,1],'resident_factor':[0.,0.,0.]}); self.population.to_csv(c['paths']['population'],index=False)
    def tearDown(self):
        self.assertTrue(self.folder.resolve().is_relative_to((ROOT/'backend/data/ml').resolve()))
        self.temp.cleanup()
    def test_ephemeral_streaming_and_registry_coverage(self):
        build_features(self.config)
        self.assertFalse((self.folder/'output/features.parquet').exists()); self.assertFalse((self.folder/'output/registry_inputs').exists())
        frame=registry_features(self.config,'2025-04-15')
        core=build_next_day_features(self.raw,self.registry,'2025-04-14',self.raw,self.population,{'Panerių sen.':'Paneriai'})
        pd.testing.assert_frame_equal(frame.sort_values('bin_id')[FEATURES].reset_index(drop=True),core.sort_values('bin_id')[FEATURES].reset_index(drop=True))
        self.assertEqual(len(FEATURES),21)
    def test_cutoffs_reject_leakage(self):
        validate_splits(self.config); self.config['final_train'][1]='2026-09-01'
        with self.assertRaises(ValueError): validate_splits(self.config)
    def test_portable_reload_and_no_runtime_writes(self):
        import joblib,json
        build_features(self.config); sample=sample_features(self.config,self.config['splits']['train'],30,name='fixture',stratified=False)
        before=self.raw.copy(deep=True); registry_before=self.registry.copy(deep=True); population_before=self.population.copy(deep=True)
        for name,params in [('random_forest',{'n_estimators':10,'max_depth':4}),('catboost',{'iterations':10,'depth':2,'learning_rate':.1})]:
            bundle=fit_model(name,params,sample,self.config); product=self.folder/name; product.mkdir()
            joblib.dump({'name':name,'preprocessing':bundle.preprocessing,'model':bundle.model,'metadata':bundle.metadata},product/'model.joblib')
            (product/'district_aliases.json').write_text(json.dumps({'Panerių sen.':'Paneriai'})); predictor=FillPredictor.load(product)
            files=set(self.folder.rglob('*')); result=predictor.predict_next_day(self.raw,self.registry,'2025-04-14',self.raw,self.population)
            self.assertEqual(list(result),['bin_id','fill_level']); self.assertEqual(set(result.bin_id),{1,2,3}); self.assertTrue(result.fill_level.isin(range(5)).all()); self.assertEqual(files,set(self.folder.rglob('*')))
            generic_registry=self.registry.copy(); generic_registry['id']=generic_registry.id.map(lambda v:f'container-{v}')
            generic_registry.loc[generic_registry.id.eq('container-3'),['waste_type','object_group','sub_district']]=['new_material','new_group','unreviewed_district']
            generic_history=self.raw.copy(); generic_history['bin_id']=generic_history.bin_id.map(lambda v:f'container-{v}')
            generic_population=self.population.copy(); generic_population['bin_id']=generic_population.bin_id.map(lambda v:f'container-{v}')
            generic=predictor.predict_next_day(generic_history,generic_registry,'2025-04-14',generic_history,generic_population)
            self.assertEqual(set(generic.bin_id),{'container-1','container-2','container-3'}); self.assertTrue(generic.fill_level.isin(range(5)).all())
        pd.testing.assert_frame_equal(self.raw,before); pd.testing.assert_frame_equal(self.registry,registry_before); pd.testing.assert_frame_equal(self.population,population_before)
    def test_duplicate_history_and_unknown_registry_rejected(self):
        for raw in [pd.concat([self.raw,self.raw.iloc[[0]]],ignore_index=True),self.raw.assign(bin_id=999)]:
            with self.assertRaises(ValueError): build_next_day_features(raw,self.registry,'2025-04-14',self.raw,self.population,{})
    def test_mid_and_end_september_dates_ignore_future_outcomes(self):
        raw=bin_fixture(); raw['date']=pd.date_range('2026-06-04',periods=120)
        registry=raw.iloc[[0]][['bin_id','site_id','waste_type','capacity_m3','sub_district','object_group']]
        for today,target in [('2026-09-15','2026-09-16'),('2026-09-30','2026-10-01')]:
            before=build_next_day_features(raw,registry,today,raw,district_aliases={}); changed=raw.copy()
            changed.loc[changed.date>=target,'fill_level']=4; changed.loc[changed.date>=target,'collection_status']='missed'
            after=build_next_day_features(changed,registry,today,raw,district_aliases={}); pd.testing.assert_frame_equal(before[FEATURES],after[FEATURES]); self.assertEqual(before.date.iloc[0],pd.Timestamp(target))

if __name__=='__main__': unittest.main()
