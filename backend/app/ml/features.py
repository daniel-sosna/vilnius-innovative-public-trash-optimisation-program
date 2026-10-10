"""Bounded raw-data reading and ephemeral active-feature construction."""
from collections import Counter
import logging
import numpy as np
import pandas as pd
from viptop_fill.features import (FEATURES, NUMERIC, CATEGORICAL, HISTORY, SAFE_COUNTERS,
    capacity_range, normalize, quality_flags, engineer_bin, engineer_bins,
    registry_rows, build_next_day_features, feature_dictionary)
from .common import (bin_blocks, clean_config, object_digest, output_path, provenance,
                     read_json, require_sources, source_path, write_json, split_mask)

def aliases(config):
    table = pd.read_csv(source_path(config, 'district_aliases'), dtype=str, keep_default_na=False)
    return dict(zip(table.input.str.strip().str.replace(r'\s+', ' ', regex=True), table.canonical))


def contradictory_sites(config, district_aliases):
    registry = pd.read_csv(source_path(config, 'registry'), usecols=['site_id', 'sub_district'],
                           dtype={'sub_district': 'string'}, keep_default_na=False, na_values=['', 'NULL'])
    canonical = registry.sub_district.str.strip().str.replace(r'\s+', ' ', regex=True).map(district_aliases)
    counts = canonical.groupby(registry.site_id).nunique()
    return set(counts.index[counts > 1])


def complete_batches(config):
    """Bounded batches of complete bins, retaining history across CSV chunks."""
    pending, rows = [], 0
    for block in bin_blocks(config):
        pending.append(block)
        rows += len(block)
        if rows >= config['processing']['parquet_batch_rows']:
            yield pd.concat(pending, ignore_index=True)
            pending, rows = [], 0
    if pending:
        yield pd.concat(pending, ignore_index=True)



class Reservoir:
    def __init__(self, limit, seed):
        self.limit, self.seed, self.total = limit, seed, 0
        self.candidate = None
        self.mandatory = {}
    def offer(self, frame):
        if not len(frame):
            return
        from .modeling import seeded_keys
        self.total += len(frame)
        frame = frame.copy()
        frame['_priority'] = seeded_keys(frame, self.seed)
        merged = frame if self.candidate is None else pd.concat([self.candidate, frame], ignore_index=True)
        self.candidate = merged.nsmallest(self.limit, '_priority').copy()
        for i, schema in enumerate([['date', 'fill_level'], ['waste_type', 'object_group', 'fill_level']]):
            best = frame.loc[frame.groupby(schema, observed=True, dropna=False)['_priority'].idxmin()]
            merged = best if i not in self.mandatory else pd.concat([self.mandatory[i], best], ignore_index=True)
            self.mandatory[i] = merged.loc[merged.groupby(schema, observed=True, dropna=False)['_priority'].idxmin()].copy()
    def result(self):
        if self.candidate is None:
            raise ValueError('No eligible sample rows')
        mandatory = pd.concat(list(self.mandatory.values()), ignore_index=True).drop_duplicates(['bin_id', 'date'])
        if len(mandatory) > self.limit:
            raise ValueError('Mandatory marginal strata exceed sample limit')
        keys = pd.MultiIndex.from_frame(mandatory[['bin_id','date']])
        rest = self.candidate.loc[~pd.MultiIndex.from_frame(self.candidate[['bin_id','date']]).isin(keys)]
        return pd.concat([mandatory, rest.nsmallest(self.limit-len(mandatory), '_priority')], ignore_index=True).drop(columns='_priority')


def blank_registry_rows(config, day):
    registry = pd.read_csv(source_path(config, 'registry'), keep_default_na=False, na_values=['', 'NULL'])
    pop = pd.read_csv(source_path(config, 'population'), keep_default_na=False, na_values=['', 'NULL']) if source_path(config, 'population').exists() else None
    return registry_rows(registry, day, pop)


def inference_row(raw, day, district_aliases):
    if raw.empty:
        return None
    registry = raw.iloc[[-1]][['bin_id','site_id','waste_type','capacity_m3','sub_district','object_group','resident_factor','population_cell_id']]
    return build_next_day_features(raw, registry, pd.Timestamp(day)-pd.Timedelta(days=1),
                                  raw.loc[raw.date == pd.Timestamp(day), ['bin_id','date']+SAFE_COUNTERS],
                                  district_aliases=district_aliases)


def build_features(config, args=None):
    if '_frames' in config:
        return
    require_sources(config)
    mapping = aliases(config)
    ambiguous = contradictory_sites(config, mapping)
    folder = output_path(config)
    folder.mkdir(parents=True, exist_ok=True)
    config['_provenance'] = provenance(config)
    registry = pd.read_csv(source_path(config, 'registry'), keep_default_na=False, na_values=['','NULL'])
    sites = np.sort(registry.site_id.unique())
    heldout = np.random.default_rng(config['seed']).choice(sites, max(1,int(len(sites)*config['unseen_sites']['fraction'])), replace=False)
    config['_heldout'] = heldout
    reservoirs = {name: Reservoir(config['sampling']['final_rows'], config['seed']) for name in ['train','final','cold']}
    pieces = {'validation': [], 'test': [], 'demo': []}
    counts = Counter()
    intervals = Counter()
    labels_per_bin = []
    daily_bins = set()
    keep = ['bin_id','site_id','date','fill_level','capacity_range','history_label_count','has_daily_history','input_quality_flag']+FEATURES
    total = labeled = 0
    for block in complete_batches(config):
        engineered = engineer_bins(block, mapping, ambiguous_site_ids=ambiguous)
        total += len(block)
        labeled += int(block.fill_level.notna().sum())
        daily_bins.update(block.bin_id.unique())
        for bid, part in block.groupby('bin_id', sort=False):
            labels_per_bin.append({'bin_id': int(bid), 'last_date': str(part.date.max().date()), 'labeled_rows': int(part.fill_level.notna().sum())})
        for split, period in config['splits'].items():
            part = engineered.loc[split_mask(engineered, period)]
            for field in ['days_since_last_successful_collection','days_since_last_collection_attempt','days_since_previous_worker_rating']:
                vals, nums = np.unique(part[field].fillna(-1), return_counts=True)
                intervals.update({(split,field,float(v)):int(n) for v,n in zip(vals,nums)})
        selected = engineered.loc[engineered.fill_level.notna(), keep]
        counts.update(selected.groupby(['date','waste_type','capacity_range','object_group','fill_level'], observed=True).size().to_dict())
        reservoirs['train'].offer(selected.loc[split_mask(selected,config['splits']['train'])])
        final = selected.loc[split_mask(selected,config['final_train'])]
        reservoirs['final'].offer(final)
        reservoirs['cold'].offer(final.loc[~final.site_id.isin(heldout)])
        for split in ['validation','test']:
            pieces[split].append(selected.loc[split_mask(selected,config['splits'][split])].copy())
        pieces['demo'].append(engineered.loc[split_mask(engineered,config['splits']['test']),keep].copy())
        if len(daily_bins)//1000 != (len(daily_bins)-block.bin_id.nunique())//1000:
            logging.info('In-memory features: bins=%s rows=%s',len(daily_bins),total)
    if total != config['expected']['rows'] or len(daily_bins) != config['expected']['daily_bins']:
        raise ValueError('Feature input counts differ from expected counts')
    frames = {name: r.result() for name,r in reservoirs.items()}
    frames.update({name: pd.concat(parts, ignore_index=True) for name,parts in pieces.items()})
    del pieces
    # Registry-only rows have the same explicit missing-history representation as runtime.
    extras = []
    for day in pd.date_range(*config['splits']['test']):
        blank = blank_registry_rows(config,day)
        blank = normalize(blank.loc[~blank.bin_id.isin(daily_bins)],mapping,ambiguous)
        extras.append(blank[keep])
    frames['demo'] = pd.concat([frames['demo'], *extras],ignore_index=True)
    if frames['demo'].duplicated(['bin_id','date']).any() or len(frames['demo']) != len(registry)*len(pd.date_range(*config['splits']['test'])):
        raise ValueError('Full demo registry coverage failed')
    # Dates/IDs identify samples. Derived feature values exist only in these frames.
    config['_frames'] = frames
    config['_eligible'] = {name:r.total for name,r in reservoirs.items()}
    pd.DataFrame(labels_per_bin).to_csv(folder/'bin_label_counts.csv',index=False)
    pd.DataFrame([{'split':s,'feature':f,'days':d,'rows':n} for (s,f,d),n in intervals.items()]).to_csv(folder/'collection_interval_distribution.csv',index=False)
    pd.DataFrame(feature_dictionary()).to_csv(folder/'feature_dictionary.csv',index=False)
    pd.DataFrame([(*key,n) for key,n in counts.items()],columns=['date','waste_type','capacity_range','object_group','fill_level','count']).to_parquet(folder/'group_label_counts.parquet',index=False)
    signature = object_digest({'provenance': config['_provenance'], 'features':FEATURES,'rows':total})
    write_json(folder/'features_manifest.json',{'provenance':config['_provenance'],'daily_rows':total,'bins':len(daily_bins),
        'labeled_rows':labeled,'feature_columns':FEATURES,'configuration':clean_config(config),
        'features_sha256':signature,'storage':'in-memory only; digest identifies source/schema, not a persisted feature table'})
    logging.info('Ephemeral frames ready: %s',{k:len(v) for k,v in frames.items()})


def verify_cache(config):
    build_features(config)
    return read_json(output_path(config,'features_manifest.json'))


def registry_features(config,day):
    build_features(config)
    frame = config['_frames']['demo']
    result = frame.loc[frame.date == pd.Timestamp(day)].copy()
    if len(result) != config['expected']['registry_bins']:
        raise ValueError('Date outside prepared demo period; use the product CSV adapter for other dates')
    return result
