import csv
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fill_qr import (Bin, Model, Scenario, prepare_catalog, classes, district,
                     worker_rating, poisson_from_uniform, lagged_reports, rng,
                     RATES, TYPES, HEADER, read_blocks, number, same_number,
                     Calibration, fit_calibration, worker_transition, TARGET_SHARES)


def residential(id_=1, site=1, resident=100., capacity=1.):
    return Bin(id_, site, 'Mixed municipal waste', capacity, 'Verkių sen.', 'Daugiabučiai namai', resident)


class RulesTests(unittest.TestCase):
    def model(self, bins=None, scenario=Scenario()):
        bins, _ = prepare_catalog(bins or {1:residential()})
        return Model(bins, '2026-10-01', '2026-10-10', scenario=scenario,
                     calibration=Calibration((1.,5.,20.,100.)))

    def test_exact_thresholds(self):
        np.testing.assert_array_equal(classes([0,19.999,20,49.999,50,79.999,80,100,100.001]), [0,0,1,1,2,2,3,3,4])

    def test_rates_and_all_types(self):
        self.assertEqual(len(TYPES),10)
        np.testing.assert_allclose(list(RATES.values()),[1.65,.99,.1155,.33,.0495],rtol=0,atol=0)
        np.testing.assert_allclose(np.array(list(RATES.values()))[1:]/1.65,[.6,.07,.2,.03])

    def test_aliases_and_ambiguity(self):
        self.assertEqual(district('  Verkių sen. '),'Verkiai')
        self.assertEqual(district('Naujoji  Vilnia'),'Naujoji Vilnia')
        self.assertEqual(district('Pašilačiai'),'Pašilaičiai')
        self.assertIsNone(district('Vilniaus'))
        self.assertIsNone(district('Vilniaus m. sav.'))

    def test_shared_fallback_across_categories(self):
        a,b = residential(),residential(2)
        a.category, b.category = 'Komercinė paskirtis','Viešosios vietos'
        b.capacity=3
        bins, fallbacks = prepare_catalog({1:a,2:b})
        self.assertEqual((a.exposure,b.exposure),(25.,75.))
        self.assertEqual(len(fallbacks),1)
        self.assertEqual(sum(x.exposure for x in bins.values()),100.)

    def test_homogeneous_equivalence_and_conservation(self):
        a,b = residential(resident=100),residential(2,resident=200,capacity=2)
        model=self.model({1:a,2:b})
        b1=rng(model.seed,'bin_B',1).lognormal(-.15**2/2,.15)
        b2=rng(model.seed,'bin_B',2).lognormal(-.15**2/2,.15)
        np.testing.assert_allclose(model.coefficients[1]/model.coefficients[2],b1/(2*b2))
        g=rng(model.seed,'site_stream_G',1,a.waste).lognormal(-.2**2/2,.2)
        q=300*1.65/1000*1.10*g
        self.assertAlmostEqual(sum(model.coefficients.values()),q,places=14)
        np.testing.assert_allclose(model.inflow(a)+model.inflow(b),q*model.shared[1,a.waste])

    def test_zero_residential_exposure(self):
        model=self.model({1:residential(resident=0)})
        s=model.simulate(1,['collected']+['none']*9)
        np.testing.assert_array_equal(s['inflow'],0)
        np.testing.assert_array_equal(s['qr'][1:],0)
        self.assertLess(np.nanmax(s['percent']),3.)

    def test_invalid_and_conflicting_districts_mask_both(self):
        a,b=residential(),residential(2)
        b.raw_district='Antakalnis'
        model=self.model({1:a,2:b})
        self.assertIn('contradictory_site_districts',a.reasons)
        for id_ in (1,2):
            s=model.simulate(id_,['collected']*10)
            np.testing.assert_array_equal(s['fill'],-1)
            np.testing.assert_array_equal(s['qr'],-1)
        for change in ({'category':''},{'capacity':0},{'resident':-1},{'raw_district':'Vilniaus'}):
            a=residential()
            for key,value in change.items():setattr(a,key,value)
            self.assertTrue(self.model({1:a}).bins[1].reasons)

    def test_missing_and_nonfinite_numeric_attributes_are_audited(self):
        for token in ('NULL','','not-a-number','nan','inf','-inf'):
            a=residential();a.capacity=number(token)
            model=self.model({1:a})
            self.assertIn('non_positive_or_non_finite_capacity',a.reasons)
            s=model.simulate(1,['collected']*10)
            np.testing.assert_array_equal(s['fill'],-1)
            np.testing.assert_array_equal(s['qr'],-1)
        self.assertTrue(same_number(number('NULL'),number('')))
        a=residential();a.resident=number('NULL')
        self.assertIn('invalid_residential_exposure',self.model({1:a}).bins[1].reasons)

    def test_anchor_mask_and_reset(self):
        model=self.model()
        statuses=['none','failed','collected','none','missed','retry_collected','none','failed','none','collected']
        s=model.simulate(1,statuses)
        np.testing.assert_array_equal(s['qr'][:3],-1)
        self.assertEqual(s['qr'][3],0)
        self.assertEqual(s['qr'][6],0)
        self.assertEqual(np.flatnonzero(s['fill']>=0).tolist(),[5,9])
        self.assertAlmostEqual(s['demand'][4]-s['demand'][3],s['inflow'][4])
        self.assertLess(s['residue'][6],3.)
        self.assertGreaterEqual(s['percent'][4],s['percent'][3])
        np.testing.assert_allclose(s['percent'],model.calibration.fullness(s['pressure'],s['residue']),equal_nan=True)

    def test_calibrated_shape_after_unchanged_worker_error(self):
        random=np.random.default_rng(37)
        pressure=np.r_[np.zeros(12000),random.lognormal(2,1.8,188000)]
        calibration,metadata=fit_calibration(pressure)
        residue=random.uniform(0,3,len(pressure))
        latent=classes(calibration.fullness(pressure,residue))
        expected=np.bincount(latent,minlength=5)/len(latent)@worker_transition()
        np.testing.assert_allclose(expected,TARGET_SHARES,atol=.012)
        self.assertEqual(metadata['zero_demand_share'],.06)

    def test_bound_monotonicity_and_extreme_demand_audit(self):
        calibration=Calibration((1.,5.,20.,100.))
        pressure=np.r_[0,np.geomspace(.00001,1e9,10000)]
        for residue in (0.,1.5,2.999):
            fullness=calibration.fullness(pressure,residue)
            self.assertEqual(fullness[0],residue)
            self.assertTrue(np.all(np.diff(fullness)>=0))
            self.assertTrue(np.all((fullness>=0)&(fullness<=120)))
        model=self.model({1:residential(resident=10000,capacity=.12)})
        s=model.simulate(1,['collected']+['none']*9)
        self.assertLessEqual(np.nanmax(s['percent']),120)
        self.assertGreater(np.nanmax(s['excess']),100)
        np.testing.assert_allclose(s['demand'][2:]-s['demand'][1:-1],s['inflow'][2:],atol=1e-12)

    def test_zero_mass_is_not_rebalanced_and_bad_calibration_rejected(self):
        calibration,metadata=fit_calibration(np.r_[np.zeros(100),np.arange(1,301)])
        self.assertGreaterEqual(metadata['latent_shares_for_fit'][0],.25)
        np.testing.assert_array_equal(calibration.fullness(np.zeros(20),np.ones(20)),1)
        for knots in ((0,1,2,3),(1,1,2,3),(1,2,3,float('inf'))):
            with self.assertRaises(ValueError):Calibration(knots)

    def test_qr_numerical_example(self):
        reports=np.array([0,1,2,4,0])
        known=np.array([False,True,True,True,True])
        success=np.array([True,False,False,True,False])
        np.testing.assert_array_equal(lagged_reports(reports,success,known),[-1,0,1,3,0])
        success[3]=False
        np.testing.assert_array_equal(lagged_reports(reports,success,known),[-1,0,1,3,7])

    def test_no_today_or_future_leakage(self):
        model=self.model()
        a=model.simulate(1,['collected']+['none']*9)
        b=model.simulate(1,['collected']+['none']*6+['collected']+['none']*2)
        np.testing.assert_array_equal(a['qr'][:8],b['qr'][:8])
        np.testing.assert_allclose(a['percent'][:8],b['percent'][:8],equal_nan=True)

    def test_reproducible_independent_qr_and_order(self):
        baseline=self.model({2:residential(2),1:residential()})
        altered=self.model({1:residential(),2:residential(2)},Scenario(qr_scale=1.5))
        statuses=['collected','none']*5
        a,b=baseline.simulate(1,statuses),altered.simulate(1,statuses)
        np.testing.assert_array_equal(a['fill'],b['fill'])
        np.testing.assert_array_equal(a['inflow'],b['inflow'])
        self.assertTrue(np.all(b['reports']>=a['reports']))
        baseline.simulate(2,statuses)
        again=baseline.simulate(1,statuses)
        for key in a:np.testing.assert_array_equal(a[key],again[key])

    def test_poisson_moments_zero_probability_and_rare_reports(self):
        uniform=np.random.default_rng(7).random(200000)
        x=poisson_from_uniform(np.full(len(uniform),3.),uniform)
        self.assertLess(abs(x.mean()-3),.025)
        self.assertLess(abs(x.var()-3),.05)
        self.assertLess(abs((x==0).mean()-np.exp(-3)),.003)
        rare=poisson_from_uniform(np.full(len(uniform),.02),uniform)
        self.assertLess(abs(rare.mean()-.02),.002)
        self.assertGreater(rare.sum(),0)

    def test_worker_error_frequency_and_adjacent_classes(self):
        random=np.random.default_rng(9)
        k=np.tile(np.arange(5),40000)
        rating=worker_rating(k,random.random(len(k)),random.random(len(k)))
        self.assertLess(abs((rating!=k).mean()-.1),.003)
        self.assertTrue(np.all(np.abs(rating-k)<=1))
        self.assertTrue(np.all((rating>=0)&(rating<=4)))
        inner=(k==2)&(rating!=k)
        self.assertLess(abs((rating[inner]==1).mean()-.5),.035)

    def test_gamma_and_lognormal_moments(self):
        x=rng(1,'gamma').gamma(1/.35**2,.35**2,200000)
        self.assertLess(abs(x.mean()-1),.003)
        self.assertLess(abs(x.std()/x.mean()-.35),.003)
        y=rng(1,'g').lognormal(-.2**2/2,.2,200000)
        self.assertLess(abs(y.mean()-1),.003)

    def test_calendar_and_paired_volume_sensitivity(self):
        a=self.model()
        b=self.model(scenario=Scenario(q_scale=1.5))
        c=self.model(scenario=Scenario(calendar=False))
        np.testing.assert_allclose(b.inflow(b.bins[1]),1.5*a.inflow(a.bins[1]))
        self.assertEqual(a.calendar[2],1.1) # Saturday
        self.assertEqual(c.calendar[2],1.)

    def test_duplicate_dates_and_unknown_status_rejected(self):
        model=self.model()
        with self.assertRaises(ValueError):model.simulate(1,['invented']*10)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bad.csv'
            with path.open('w',encoding='utf-8',newline='') as f:
                writer=csv.writer(f);writer.writerow(HEADER)
                for d in ['2026-10-01']*10:
                    writer.writerow([1,d,4,40,10,4,1,'Mixed municipal waste',1,'Verkių sen.','Daugiabučiai namai','',100,'none',0,0,0])
            with self.assertRaisesRegex(ValueError,'dates'):list(read_blocks(path,model))


if __name__=='__main__':unittest.main()
