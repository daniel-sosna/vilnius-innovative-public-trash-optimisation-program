"""Offline synthetic fill/QR generator. See docs/data/fill-qr.md."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass, asdict
from datetime import date, timedelta, datetime, timezone
import hashlib
from itertools import groupby
import json
import math
from pathlib import Path
import platform

import holidays
import numpy as np
import scipy
from scipy.stats import poisson

HEADER = 'bin_id,date,day_of_week,week_of_year,month,season,site_id,waste_type,capacity_m3,sub_district,object_group,population_cell_id,resident_factor,collection_status,holidays_since_last_collection,collections_last_28d,missed_collections_28d'.split(',')
SUCCESS = {'collected', 'retry_collected'}
STATUSES = SUCCESS | {'none', 'failed', 'missed'}
TYPES = {
    'Viešosios vietos': (1.20, False), 'Sodų/garažų bendrijos': (.65, True),
    'Sodų bendrijos': (.70, True), 'Garažų bendrijos': (.45, False),
    'Viešosios įstaigos': (1.10, False), 'Daugiabučiai namai': (1., True),
    'Daugiabučių/garažų bendrijos': (.90, True), 'Juridiniai asmenys': (1.10, False),
    'Dvibučiai': (1., True), 'Komercinė paskirtis': (1.30, False),
}
RATES = {'Mixed municipal waste': 1.65, 'Paper/plastic waste': .9900,
         'Glass waste': .1155, 'Food/organic waste': .3300, 'Textiles': .0495}
UPLIFT = {'Verkiai', 'Naujininkai', 'Grigiškės'}
ALIASES = {
    'Panerių sen.': 'Paneriai', 'Pašilaičių sen.': 'Pašilaičiai',
    'Grigiškių sen.': 'Grigiškės', 'Pilaitės sen.': 'Pilaitė',
    'Lazdynų sen.': 'Lazdynai', 'Vilkpėdės sen.': 'Vilkpėdė',
    'Naujininkų sen.': 'Naujininkai', 'Karoliniškių sen.': 'Karoliniškės',
    'Žvėryno sen.': 'Žvėrynas', 'Šeškinės sen.': 'Šeškinė',
    'Verkių sen.': 'Verkiai', 'Justiniškių sen.': 'Justiniškės',
    'Viršuliškių sen.': 'Viršuliškės', 'Fabijoniškių sen.': 'Fabijoniškės',
    'Pašilačiai': 'Pašilaičiai', 'Šnipiškių sen.': 'Šnipiškės',
    'Naujamiesčio sen.': 'Naujamiestis', 'Senamiesčio sen.': 'Senamiestis',
    'Rasų sen.': 'Rasos', 'Naujosios Vilnios sen.': 'Naujoji Vilnia',
    'Antakalnio sen.': 'Antakalnis', 'Žirmūnų sen.': 'Žirmūnai',
}
ALIASES.update({v: v for v in list(ALIASES.values())})
SEVERITY = np.array([.002, .002, .005, .020, .300])
TARGET_SHARES = np.array([.10, .20, .40, .20, .10])
MAX_FILL = 120.


@dataclass(frozen=True)
class Calibration:
    """Frozen response of fullness to new assigned demand since last success."""
    pressure_knots: tuple
    max_fill: float = MAX_FILL

    def __post_init__(self):
        knots = np.asarray(self.pressure_knots, dtype=float)
        if knots.shape != (4,) or not np.all(np.isfinite(knots)) or not np.all(np.diff(np.r_[0., knots]) > 0):
            raise ValueError('Calibration needs four strictly increasing positive finite knots')
        if self.max_fill != MAX_FILL:
            raise ValueError('The approved fullness ceiling is 120%')

    def fullness(self, pressure, residue):
        pressure, residue = np.broadcast_arrays(np.asarray(pressure, float), np.asarray(residue, float))
        x = np.r_[0., self.pressure_knots]
        y = np.r_[0., (np.array([20.,50.,80.,100.])-1.5)/(self.max_fill-1.5)]
        response = np.interp(pressure, x, y)
        tail = pressure > x[-1]
        scale = max(x[-1]-x[-2], np.finfo(float).eps)
        response = np.where(tail, y[-1]+(1-y[-1])*(-np.expm1(-np.maximum(pressure-x[-1],0)/scale)), response)
        return np.clip(residue+(self.max_fill-residue)*response, 0., self.max_fill)


def worker_transition():
    matrix = np.eye(5)*.9
    for k in range(5):
        neighbours = [j for j in (k-1,k+1) if 0 <= j <= 4]
        matrix[k, neighbours] = .1/len(neighbours)
    return matrix


def fit_calibration(pressures):
    values = np.asarray(pressures, dtype=float)
    if len(values) < 4 or not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError('Insufficient or invalid calibration demand observations')
    latent = np.linalg.solve(worker_transition().T, TARGET_SHARES)
    zero = float((values == 0).mean())
    # A genuine atom at zero cannot be transformed into positive waste.
    if zero >= latent[0]:
        first = min(.95, zero+.005)
        latent[1:] *= (1-first)/(1-latent[0])
        latent[0] = first
    quantiles = np.cumsum(latent)[:-1]
    knots = np.quantile(values, quantiles)
    calibration = Calibration(tuple(knots.tolist()))
    metadata = {'response':asdict(calibration), 'target_worker_shares':TARGET_SHARES.tolist(),
                'latent_shares_for_fit':latent.tolist(), 'expected_worker_shares':(latent@worker_transition()).tolist(),
                'quantile_probabilities':quantiles.tolist(), 'zero_demand_share':zero,
                'assessments_used':len(values), 'method':'global monotone demand response; linear knots and exponential saturation; residue retained'}
    return calibration, metadata


def clean(value):
    value = ' '.join(str(value).split())
    return '' if value in {'NULL', 'None', 'nan'} else value


def district(value):
    return ALIASES.get(clean(value))


def number(value):
    """Missing/invalid numeric attributes are auditable, rather than parse failures."""
    try:
        return float(clean(value))
    except (TypeError, ValueError):
        return float('nan')


def same_number(left, right):
    return left == right or (math.isnan(left) and math.isnan(right))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def rng(seed, namespace, *keys):
    payload = json.dumps([seed, namespace, *keys], ensure_ascii=False, separators=(',', ':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(payload).digest()[:16], 'little'))


def classes(fill):
    fill = np.asarray(fill)
    return ((fill >= 20).astype(np.int8) + (fill >= 50) + (fill >= 80) + (fill > 100))


def worker_rating(latent, error_u, side_u):
    latent = np.asarray(latent, dtype=np.int8)
    rating = latent.copy()
    error = np.asarray(error_u) < .10
    delta = np.where(np.asarray(side_u) < .5, -1, 1)
    delta = np.where(latent == 0, 1, np.where(latent == 4, -1, delta))
    rating[error] += delta[error]
    return rating


def poisson_from_uniform(mean, uniform):
    result = np.zeros(len(mean), dtype=np.int64)
    mask = np.asarray(mean) > 0
    result[mask] = poisson.ppf(np.clip(np.asarray(uniform)[mask], np.nextafter(0., 1.), np.nextafter(1., 0.)), np.asarray(mean)[mask]).astype(np.int64)
    return result


def lagged_reports(reports, success, known):
    """R[d] excludes reports and service on d, including on success days."""
    total = np.cumsum(reports, dtype=np.int64)
    previous = np.maximum.accumulate(np.where(success, np.arange(len(success)), -1))
    previous = np.r_[-1, previous[:-1]]
    before = np.r_[0, total[:-1]]
    result = before - np.where(previous >= 0, total[np.maximum(previous, 0)], 0)
    result[~known] = -1
    return result


@dataclass
class Bin:
    id: int
    site: int
    waste: str
    capacity: float
    raw_district: str
    category: str
    resident: float
    cell: str = ''
    canonical_district: str | None = None
    reasons: tuple = ()
    exposure: float = 0.


@dataclass(frozen=True)
class Scenario:
    name: str = 'baseline'
    q_scale: float = 1.
    mixed_q: float = 1.65
    calendar: bool = True
    type_effect: bool = True
    qr_scale: float = 1.
    district_uplift: float = 1.10


def prepare_catalog(bins):
    by_site = defaultdict(list)
    for b in bins.values():
        b.canonical_district = district(b.raw_district)
        reasons = []
        if b.category not in TYPES:
            reasons.append('missing_or_unsupported_object_group')
        if b.waste not in RATES:
            reasons.append('unknown_waste_stream')
        if not math.isfinite(b.capacity) or b.capacity <= 0:
            reasons.append('non_positive_or_non_finite_capacity')
        if b.category in TYPES and TYPES[b.category][1] and (not math.isfinite(b.resident) or b.resident < 0):
            reasons.append('invalid_residential_exposure')
        if b.canonical_district is None:
            reasons.append('unresolved_district')
        b.reasons = tuple(reasons)
        by_site[b.site].append(b)
    for members in by_site.values():
        if len({b.canonical_district for b in members if b.canonical_district}) > 1:
            for b in members:
                b.reasons += ('contradictory_site_districts',)
    nonres = defaultdict(list)
    for b in bins.values():
        if b.reasons:
            continue
        if TYPES[b.category][1]:
            b.exposure = b.resident
        else:
            nonres[b.site, b.waste].append(b)
    fallbacks = []
    for (site, waste), members in sorted(nonres.items()):
        total = sum(b.capacity for b in members)
        for b in members:
            b.exposure = 100 * b.capacity / total
        fallbacks.append({'site_id': site, 'waste_type': waste, 'total_users': 100,
                          'bin_ids': ';'.join(str(b.id) for b in members),
                          'excluded_site_stream_bins': ';'.join(str(b.id) for b in by_site[site] if b.waste == waste and b.reasons)})
    return bins, fallbacks


def load_catalog(bins_path, population_path, schedule_path):
    with Path(schedule_path).open(encoding='utf-8-sig', newline='') as f:
        scheduled = {int(r['bin_id']) for r in csv.DictReader(f)}
    with Path(population_path).open(encoding='utf-8-sig', newline='') as f:
        population = {int(r['bin_id']): r for r in csv.DictReader(f)}
    bins = {}
    with Path(bins_path).open(encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            id_ = int(r['id'])
            # This is the existing bin-day export's eligibility contract.
            if id_ not in scheduled or not clean(r['sub_district']):
                continue
            p = population[id_]
            bins[id_] = Bin(id_, int(r['site_id']), r['waste_type'], number(r['capacity_m3']),
                            r['sub_district'], clean(r['object_group']), number(p['resident_factor']), p['population_cell_id'])
    return prepare_catalog(bins)


class Model:
    def __init__(self, bins, start, end, seed=20261009, scenario=Scenario(), calibration=None):
        self.bins, self.seed, self.scenario = bins, seed, scenario
        self.calibration = calibration
        self.start, self.end = date.fromisoformat(str(start)), date.fromisoformat(str(end))
        if self.end < self.start:
            raise ValueError('End precedes start')
        self.dates = [self.start + timedelta(days=d) for d in range((self.end-self.start).days+1)]
        self.date_strings = [d.isoformat() for d in self.dates]
        self.range_key = [self.start.isoformat(), self.end.isoformat()]
        calendar = holidays.country_holidays('LT', years=sorted({d.year for d in self.dates}))
        self.calendar = np.array([(1.05 if d.month in (12,1,2) else .95 if d.month in (6,7,8) else 1.) * (1.1 if d.weekday() >= 5 else 1.) * (1.2 if d in calendar else 1.) for d in self.dates]) if scenario.calendar else np.ones(len(self.dates))
        self.groups = defaultdict(list)
        for b in bins.values():
            if not b.reasons:
                self.groups[b.site, b.waste].append(b)
        self.coefficients = {}
        self.shared = {}
        self.propensity = {}
        self.max_conservation_error = 0.
        for key, members in self.groups.items():
            members.sort(key=lambda b: b.id)
            effective = np.array([b.exposure * (TYPES[b.category][0] if scenario.type_effect else 1.) * (scenario.district_uplift if b.canonical_district in UPLIFT else 1.) for b in members])
            weights = effective * np.array([rng(seed, 'bin_B', b.id).lognormal(-.15**2/2, .15) for b in members])
            allocation = weights / weights.sum() if weights.sum() else weights
            q = (scenario.mixed_q if key[1] == 'Mixed municipal waste' else RATES[key[1]]) * scenario.q_scale
            g = rng(seed, 'site_stream_G', *key).lognormal(-.20**2/2, .20)
            base = q/1000 * effective.sum() * g
            for b, weight in zip(members, allocation):
                self.coefficients[b.id] = base * weight
            error = abs(sum(self.coefficients[b.id] for b in members)-base)
            self.max_conservation_error = max(self.max_conservation_error, error)
        for site in {b.site for b in bins.values() if not b.reasons}:
            self.propensity[site] = float(np.clip(rng(seed, 'site_U', site).lognormal(-.70**2/2, .70), .2, 2.5))

    def inflow(self, b):
        key = b.site, b.waste
        if key not in self.shared:
            z = rng(self.seed, 'daily_gamma', *key, *self.range_key).gamma(1/.35**2, .35**2, len(self.dates))
            self.shared[key] = self.calendar * z
        return self.coefficients[b.id] * self.shared[key]

    def raw_state(self, bin_id, statuses):
        """Unchanged source-demand balance, never a physical fullness percentage."""
        b = self.bins[bin_id]
        n = len(self.dates)
        if len(statuses) != n or set(statuses)-STATUSES:
            raise ValueError(f'Invalid statuses for bin {bin_id}')
        success = np.isin(statuses, list(SUCCESS))
        indices = np.arange(n)
        prior = np.r_[-1, np.maximum.accumulate(np.where(success, indices, -1))[:-1]]
        known = prior >= 0
        eps = np.zeros(n)
        eps[success] = rng(self.seed, 'residue', b.id, *self.range_key).uniform(0, .03, success.sum())
        inflow = self.inflow(b)
        cumulative = np.cumsum(inflow)
        added = np.maximum(cumulative-cumulative[np.maximum(prior, 0)], 0.)
        residue = 100*eps[np.maximum(prior, 0)]
        demand = added+b.capacity*residue/100
        pressure = 100*added/b.capacity
        for values in (residue,demand,pressure):values[~known]=np.nan
        return dict(success=success,known=known,inflow=inflow,residue=residue,demand=demand,
                    excess=np.maximum(demand-b.capacity,0.),pressure=pressure)

    def simulate(self, bin_id, statuses):
        if self.calibration is None:
            raise ValueError('Fit or supply a frozen calibration before simulating fullness')
        b = self.bins[bin_id]
        n = len(self.dates)
        if len(statuses) != n or set(statuses)-STATUSES:
            raise ValueError(f'Invalid statuses for bin {bin_id}')
        fill = np.full(n, -1, dtype=np.int8)
        qr = np.full(n, -1, dtype=np.int64)
        empty = np.full(n, np.nan)
        if b.reasons:
            return dict(fill=fill, qr=qr, percent=empty, latent=fill.copy(), reports=np.zeros(n,dtype=np.int64), inflow=np.zeros(n), known=np.zeros(n,dtype=bool), success=np.isin(statuses, list(SUCCESS)), mean=np.zeros(n), demand=empty.copy(),excess=empty.copy(),residue=empty.copy(),pressure=empty.copy())
        raw = self.raw_state(bin_id,statuses)
        known, success, inflow = raw['known'], raw['success'], raw['inflow']
        percent = self.calibration.fullness(raw['pressure'],raw['residue'])
        latent = classes(percent)
        latent[~known] = -1
        worker = rng(self.seed, 'worker', b.id, *self.range_key)
        rating = worker_rating(latent, worker.random(n), worker.random(n))
        assess = known & success
        fill[assess] = rating[assess]
        mean = np.zeros(n)
        mean[known] = b.exposure * np.clip(.1*self.propensity[b.site], 0, 1) * SEVERITY[latent[known]] * self.scenario.qr_scale
        uniform = rng(self.seed, 'qr', b.id, *self.range_key).random(n)
        reports = poisson_from_uniform(mean, uniform)
        qr = lagged_reports(reports, success, known)
        return dict(fill=fill, qr=qr, percent=percent, latent=latent, reports=reports, mean=mean, **raw)


def read_blocks(path, model):
    seen = set()
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        if next(reader) != HEADER:
            raise ValueError('Input must have the original 17-column schema')
        for key, group in groupby(reader, key=lambda r: int(r[0])):
            if key in seen or key not in model.bins:
                raise ValueError(f'Duplicate/unknown bin block: {key}')
            seen.add(key)
            rows = list(group)
            if [r[1] for r in rows] != model.date_strings:
                raise ValueError(f'Missing, duplicate or unordered dates for bin {key}')
            b = model.bins[key]
            first = rows[0]
            if int(first[6]) != b.site or first[7] != b.waste or not same_number(number(first[8]), b.capacity) or clean(first[9]) != clean(b.raw_district) or clean(first[10]) != b.category or not same_number(number(first[12]), b.resident) or first[11] != b.cell:
                raise ValueError(f'Static fields disagree with catalog for bin {key}')
            static = [first[j] for j in range(6, 13)]
            for r in rows:
                if len(r) != 17 or [r[j] for j in range(6,13)] != static or r[13] not in STATUSES:
                    raise ValueError(f'Conflicting static fields/status for bin {key}')
            yield key, rows
    if seen != set(model.bins):
        raise ValueError(f'Incomplete bin roster: missing {len(set(model.bins)-seen)} bins')


def select_sample(model, limit=240):
    """Whole site/stream pools, plus extremes and every type/stream/district stratum."""
    ranked = sorted(model.groups, key=lambda k: hashlib.sha256(repr(k).encode()).hexdigest())
    chosen = set(ranked[:limit])
    strata = {}
    for key in ranked:
        for b in model.groups[key]:
            for label in [('type', b.category), ('waste', b.waste), ('district', b.canonical_district), ('zero', str(b.exposure == 0))]:
                strata.setdefault(label, key)
    chosen.update(strata.values())
    valid = [b for b in model.bins.values() if not b.reasons]
    for b in sorted(valid, key=lambda b: b.exposure/b.capacity, reverse=True)[:5]:
        chosen.add((b.site, b.waste))
    return {b.id for key in chosen for b in model.groups[key]}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def calibrate_input(args, model, input_hash):
    static_hashes = {str(p):digest(p) for p in [args.bins,args.population,args.schedule]}
    provenance = {'input_sha256':input_hash,'static_inputs':static_hashes,'seed':args.seed,
                  'range':[args.start,args.end]}
    if args.calibration:
        metadata = json.loads(args.calibration.read_text(encoding='utf-8'))
        if any(metadata.get(k) != v for k,v in provenance.items()):
            raise ValueError('Calibration provenance differs from the generation inputs/range/seed')
        return Calibration(**metadata['response']), metadata
    try:
        anniversary = model.start.replace(year=model.start.year+1)
    except ValueError:
        anniversary = model.start.replace(year=model.start.year+1,day=28)
    fit_end = min(model.end, date.fromisoformat(args.fit_end) if args.fit_end else anniversary-timedelta(days=1))
    if fit_end < model.start:
        raise ValueError('Calibration end precedes generation start')
    fit_mask = np.array([d <= fit_end for d in model.dates])
    observations = []
    for index,(id_,rows) in enumerate(read_blocks(args.input,model),1):
        if not model.bins[id_].reasons:
            state = model.raw_state(id_,[r[13] for r in rows])
            mask = state['known'] & state['success'] & fit_mask
            observations.append(state['pressure'][mask])
        if index % 2000 == 0:
            print(f'Calibration scanned {index}/{len(model.bins)} bins',flush=True)
    calibration, metadata = fit_calibration(np.concatenate(observations))
    metadata.update(provenance)
    metadata['fit_start'],metadata['fit_end'] = args.start,str(fit_end)
    metadata['fit_is_synthetic_not_empirical'] = True
    return calibration,metadata


def generate(args):
    bins, fallbacks = load_catalog(args.bins, args.population, args.schedule)
    model = Model(bins, args.start, args.end, args.seed)
    output = args.output
    if output.resolve() == args.input.resolve():
        raise ValueError('Output must differ from input')
    if output.exists() and not args.overwrite:
        raise FileExistsError(f'{output}; use --overwrite explicitly')
    output.parent.mkdir(parents=True, exist_ok=True)
    args.diagnostics.mkdir(parents=True, exist_ok=True)
    input_hash = digest(args.input)
    model.calibration, calibration_metadata = calibrate_input(args,model,input_hash)
    write_json(args.diagnostics/'calibration.json',calibration_metadata)
    print('Frozen calibration: '+json.dumps(calibration_metadata['response']),flush=True)
    exclusions = [{'bin_id': b.id, 'site_id': b.site, 'waste_type': b.waste, 'object_group': b.category, 'capacity_m3': b.capacity, 'sub_district': b.raw_district, 'reasons': ';'.join(b.reasons)} for b in bins.values() if b.reasons]
    for name, records in [('exclusions.csv', exclusions), ('fallbacks.csv', fallbacks)]:
        with (args.diagnostics/name).open('w',encoding='utf-8',newline='') as f:
            if records:
                writer = csv.DictWriter(f,fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    sample = select_sample(model)
    selected = {}
    counts = Counter()
    fill_counts = np.zeros(5, dtype=np.int64)
    latent_counts = np.zeros(5, dtype=np.int64)
    latent_visit_counts = np.zeros(5, dtype=np.int64)
    latent_nonvisit_counts = np.zeros(5, dtype=np.int64)
    daily = np.zeros((3,len(model.dates)))
    status_counts = Counter()
    stratum_counts = defaultdict(lambda: np.zeros(7, dtype=np.int64))
    period_counts = defaultdict(lambda: np.zeros(5,dtype=np.int64))
    fit_mask = np.array([str(d) <= calibration_metadata['fit_end'] for d in model.dates])
    years = np.array([d.year-model.start.year-int((d.month,d.day)<(model.start.month,model.start.day))+1 for d in model.dates])
    bounds = {'minimum_fullness':MAX_FILL,'maximum_fullness':0.,'days_at_ceiling':0,
              'maximum_assigned_demand_m3':0.,'maximum_excess_demand_m3':0.,
              'source_inflow_total_m3':0.,'monotonicity_checks':0}
    temporary = output.with_suffix(output.suffix+'.partial')
    with temporary.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(HEADER+['fill_level','qr_alerts'])
        for number, (id_, rows) in enumerate(read_blocks(args.input, model), 1):
            statuses = [r[13] for r in rows]
            s = model.simulate(id_, statuses)
            b = bins[id_]
            for r, target, qr in zip(rows, s['fill'], s['qr']):
                writer.writerow(r + [str(target) if target >= 0 else '', str(qr) if qr >= 0 else ''])
            counts['rows'] += len(rows)
            counts['bins'] += 1
            counts['fill_null'] += int((s['fill'] < 0).sum())
            counts['qr_null'] += int((s['qr'] < 0).sum())
            counts['known_days'] += int(s['known'].sum())
            counts['reports_generated'] += int(s['reports'].sum())
            counts['qr_nonzero_days'] += int((s['qr'] > 0).sum())
            counts['qr_sum'] += int(s['qr'][s['qr'] >= 0].sum())
            counts['qr_max'] = max(counts['qr_max'], int(s['qr'].max()))
            assess = s['fill'] >= 0
            if s['known'].any():
                values = s['percent'][s['known']]
                assert np.all(np.isfinite(values)) and np.all((values>=0)&(values<=MAX_FILL))
                bounds['minimum_fullness'] = min(bounds['minimum_fullness'],float(values.min()))
                bounds['maximum_fullness'] = max(bounds['maximum_fullness'],float(values.max()))
                bounds['days_at_ceiling'] += int((values==MAX_FILL).sum())
                bounds['maximum_assigned_demand_m3'] = max(bounds['maximum_assigned_demand_m3'],float(np.nanmax(s['demand'])))
                bounds['maximum_excess_demand_m3'] = max(bounds['maximum_excess_demand_m3'],float(np.nanmax(s['excess'])))
                continuous = s['known'][1:] & s['known'][:-1] & ~s['success'][:-1]
                assert np.all(np.diff(s['percent'])[continuous] >= -1e-9)
                bounds['monotonicity_checks'] += int(continuous.sum())
            bounds['source_inflow_total_m3'] += float(s['inflow'].sum())
            for label,mask in [('calibration',fit_mask),('after_calibration',~fit_mask)]+[(f'year_{y}',years==y) for y in np.unique(years)]:
                period_counts[label] += np.bincount(s['fill'][assess & mask],minlength=5)
            counts['worker_errors'] += int((s['fill'][assess] != s['latent'][assess]).sum())
            fill_counts += np.bincount(s['fill'][assess], minlength=5)
            latent_counts += np.bincount(s['latent'][s['known']], minlength=5)
            latent_visit_counts += np.bincount(s['latent'][s['known'] & s['success']], minlength=5)
            latent_nonvisit_counts += np.bincount(s['latent'][s['known'] & ~s['success']], minlength=5)
            daily[0] += s['inflow']
            daily[1] += s['latent'] == 4
            daily[2] += s['known']
            status_counts.update(statuses)
            for label in [('waste', b.waste), ('type', b.category), ('exposure', 'zero' if b.exposure == 0 else 'positive')]:
                vector = stratum_counts['|'.join(label)]
                vector[:5] += np.bincount(s['latent'][s['known']], minlength=5)
                vector[5] += int(s['known'].sum())
                vector[6] += int(s['reports'].sum())
            if id_ in sample:
                selected[str(id_)] = np.stack([s['fill'],s['qr'],s['percent'],s['latent'],s['reports'],s['inflow'],s['success'],s['mean'],s['demand'],s['excess'],s['residue'],s['pressure']])
            if number % 1000 == 0:
                print(f'Generated {number}/{len(bins)} bins; {counts["rows"]:,} rows', flush=True)
    temporary.replace(output)
    np.savez_compressed(args.diagnostics/'sample_trajectories.npz', **selected)
    np.savez_compressed(args.diagnostics/'daily_totals.npz', values=daily)
    write_json(args.diagnostics/'sample_catalog.json', {str(i): asdict(bins[i]) for i in sorted(sample)})
    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'kind': 'Synthetic worker labels and lagged synthetic QR counts; no measured fill validation',
        'range': {'start': args.start, 'end': args.end, 'days': len(model.dates)},
        'seed': args.seed, 'scenario': asdict(Scenario()),
        'versions': {'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'holidays':holidays.__version__},
        'inputs': {str(p):digest(p) if p != args.input else input_hash for p in [args.input,args.bins,args.population,args.schedule]},
        'output': {'file': str(output), 'sha256': digest(output)},
        'code_sha256': digest(Path(__file__)),
        'rules_sha256': digest(args.rules),
        'calibration':calibration_metadata, 'calibration_sha256':digest(args.diagnostics/'calibration.json'),
        'fullness_and_demand_checks':bounds, 'period_worker_counts':{k:v.tolist() for k,v in period_counts.items()},
        'sample_array_rows':['fill_level','qr_alerts','fullness_percent','latent_class','daily_reports','source_inflow_m3','success','qr_mean','assigned_demand_m3','excess_source_demand_m3','residue_percent','new_demand_pressure'],
        'counts': dict(counts), 'fill_counts':fill_counts.tolist(), 'latent_counts':latent_counts.tolist(),
        'latent_visit_counts':latent_visit_counts.tolist(), 'latent_nonvisit_counts':latent_nonvisit_counts.tolist(),
        'status_counts':dict(status_counts), 'strata':{k:v.tolist() for k,v in stratum_counts.items()},
        'excluded_bins':len(exclusions), 'excluded_rows':len(exclusions)*len(model.dates),
        'exclusion_reason_counts':dict(Counter(r for b in bins.values() for r in b.reasons)),
        'fallback_site_streams':len(fallbacks), 'fallback_sites':len({x['site_id'] for x in fallbacks}),
        'max_allocation_coefficient_error_m3':model.max_conservation_error,
        'sample_bins':len(sample), 'sample_pools':len({(bins[i].site,bins[i].waste) for i in sample}),
        'assumptions':['Static registry/population snapshots over three years','Previously synthetic collection calendar','100 equivalent users per non-residential site/stream','No events: E=1','Unknown initial state until first success','Successful service assumed assessable','Residual U(0,.03), worker adjacent error .10','User-assumed bell-shaped worker shares .10/.20/.40/.20/.10; not measured normality','Frozen first-year monotone fullness calibration, upper bound 120%; source demand is separately conserved','NULL is an empty CSV field; -1 only in internal diagnostic arrays','No measured fill; annual mass check unavailable without bulk density'],
    }
    write_json(args.diagnostics/'manifest.json', manifest)
    print(json.dumps({'output':str(output),'counts':dict(counts),'excluded_bins':len(exclusions),'sha256':manifest['output']['sha256']}), flush=True)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=Path('backend/data/bin_days_20231010_20261009.csv'))
    p.add_argument('--output',type=Path,default=Path('backend/data/bin_days_20231010_20261009_enriched.csv'))
    p.add_argument('--bins',type=Path,default=Path('backend/data/bins_202610091935.csv'))
    p.add_argument('--population',type=Path,default=Path('backend/data/bin_population.csv'))
    p.add_argument('--schedule',type=Path,default=Path('backend/data/bin_schedule_202610100342.csv'))
    p.add_argument('--rules',type=Path,default=Path('backend/data/rules/vilnius_two_column_generation_rules_v4.md'))
    p.add_argument('--calibration',type=Path,help='Reuse a frozen calibration with matching input provenance')
    p.add_argument('--fit-end',help='Last calibration date; default is the end of the first year')
    p.add_argument('--diagnostics',type=Path,default=Path('backend/data/validation/fill_qr'))
    p.add_argument('--start',default='2023-10-10')
    p.add_argument('--end',default='2026-10-09')
    p.add_argument('--seed',type=int,default=20261009)
    p.add_argument('--overwrite',action='store_true')
    return p


if __name__ == '__main__':
    generate(parser().parse_args())
