"""Configuration, provenance and bounded I/O shared by offline ML stages."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.metadata
import json
import logging
from pathlib import Path
import platform
import sys
import time

import numpy as np
import pandas as pd
import psutil
import yaml

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_VERSION = 1
HEADER = ('bin_id,date,day_of_week,week_of_year,month,season,site_id,waste_type,'
          'capacity_m3,sub_district,object_group,population_cell_id,resident_factor,'
          'collection_status,holidays_since_last_collection,collections_last_28d,'
          'missed_collections_28d,fill_level,qr_alerts').split(',')
TEXT = ['date', 'waste_type', 'sub_district', 'object_group', 'collection_status']
SUCCESS = {'collected', 'retry_collected'}
STATUSES = SUCCESS | {'none', 'failed', 'missed'}
MODELS = ['catboost', 'random_forest']
PROBABILITY_COLUMNS = [f'probability_class_{i}' for i in range(5)]


def model_names(config):
    names = config.get('models', MODELS)
    if not names or len(set(names)) != len(names) or any(n not in MODELS for n in names):
        raise ValueError('models must be a nonempty unique subset of supported algorithms')
    return list(names)


def json_default(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, (Path, pd.Timestamp)):
        return str(value)
    if isinstance(value, (np.ndarray, set)):
        return list(value)
    raise TypeError(type(value).__name__)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False,
                               default=json_default, allow_nan=False), encoding='utf-8')
    for attempt in range(4):
        try:
            temp.replace(path)
            break
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(.05 * 2**attempt)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def object_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=json_default).encode()).hexdigest()


def load_config(path):
    path = Path(path)
    if not path.is_absolute() and not path.exists():
        path = ROOT / path
    config = yaml.safe_load(path.read_text(encoding='utf-8'))
    validate_splits(config)
    config['_root'] = ROOT
    return config


def validate_splits(config):
    periods = config['splits']
    previous = None
    for name in ['calibration', 'train', 'validation', 'test']:
        start, end = map(pd.Timestamp, periods[name])
        if start > end or (previous is not None and start <= previous):
            raise ValueError(f'Invalid or overlapping split: {name}')
        previous = end
    for fold in config['folds']:
        lo, hi = map(pd.Timestamp, periods['train'])
        a, b = map(pd.Timestamp, fold['train'])
        c, d = map(pd.Timestamp, fold['validation'])
        if not (lo <= a <= b < c <= d <= hi):
            raise ValueError('Every temporal fold must lie within train with train < validation')
    if pd.Timestamp(periods['validation'][1]) >= pd.Timestamp(config['prediction_date']):
        raise ValueError('Control date must follow model fitting and parameter-selection periods')

    if 'final_train' in config:
        final_start, final_end = map(pd.Timestamp, config['final_train'])
        cutoff = pd.Timestamp('2026-09-01')
        if not (pd.Timestamp(periods['calibration'][1]) < final_start <= final_end < cutoff):
            raise ValueError('Final fitting must follow calibration and end before 2026-09-01')
        if pd.Timestamp(periods['validation'][1]) >= cutoff or pd.Timestamp(periods['train'][1]) >= pd.Timestamp(periods['validation'][0]):
            raise ValueError('Selection must finish before September with fitting before validation')
        if pd.Timestamp(periods['test'][0]) <= final_end:
            raise ValueError('Demo targets must follow final fitting')


def source_path(config, name):
    path = Path(config['paths'][name])
    return path if path.is_absolute() else config['_root'] / path


def output_path(config, *parts):
    return source_path(config, 'output').joinpath(*parts)


def clean_config(config):
    return {k: v for k, v in config.items() if not k.startswith('_')}


def provenance(config):
    return {'schema_version': SCHEMA_VERSION, 'config_sha256': object_digest(clean_config(config)),
            'inputs': {name: {'path': config['paths'][name], 'sha256': digest(source_path(config, name))}
                       for name in ['daily', 'registry', 'district_aliases', 'population']
                       if source_path(config, name).exists()},
            'feature_code_sha256': digest(ROOT / 'backend/viptop_fill/features.py')}


def require_sources(config):
    data = ROOT / 'backend/data'
    for table in ['sites', 'bins', 'bin_hist']:
        if not any(p.stem[len(table) + 1:].isdigit() for p in data.glob(f'{table}_*.csv')):
            raise ValueError(f'Add the required {table}_<digits>.csv export to backend/data; do not run bin_sync')
    for name in ['daily', 'registry', 'district_aliases']:
        if not source_path(config, name).is_file():
            raise ValueError(f'Missing {name} input: {config["paths"][name]}')


def daily_chunks(config):
    dtype = {c: 'float64' for c in HEADER if c not in TEXT}
    dtype.update({c: 'string' for c in TEXT})
    dtype.update({'bin_id': 'int64', 'site_id': 'int64'})
    with pd.read_csv(source_path(config, 'daily'), dtype=dtype,
                     chunksize=config['processing']['csv_chunk_rows'],
                     keep_default_na=False, na_values=['', 'NULL']) as reader:
        for frame in reader:
            if list(frame) != HEADER:
                raise ValueError('Daily CSV must have the exact documented 19-column schema')
            frame['date'] = pd.to_datetime(frame.date, format='%Y-%m-%d', errors='raise')
            yield frame


def bin_blocks(config):
    carry = None
    previous_bin = None
    for chunk in daily_chunks(config):
        if carry is not None:
            chunk = pd.concat([carry, chunk], ignore_index=True)
        last_bin = chunk.bin_id.iloc[-1]
        carry = chunk.loc[chunk.bin_id == last_bin].copy()
        complete = chunk.loc[chunk.bin_id != last_bin]
        for key, frame in complete.groupby('bin_id', sort=False):
            if previous_bin is not None and key <= previous_bin:
                raise ValueError('CSV must be sorted by bin_id then date; repeated or unordered bin block')
            check_sequence(frame)
            previous_bin = key
            yield frame.reset_index(drop=True)
    if carry is not None:
        if previous_bin is not None and last_bin <= previous_bin:
            raise ValueError('Repeated or unordered final bin block')
        check_sequence(carry)
        yield carry.reset_index(drop=True)


def check_sequence(frame):
    if frame.bin_id.nunique() != 1 or frame.date.duplicated().any():
        raise ValueError('Expected one bin with unique dates per block')
    if len(frame) > 1 and not frame.date.diff().iloc[1:].eq(pd.Timedelta(days=1)).all():
        raise ValueError(f'Nonconsecutive or unordered dates for bin {frame.bin_id.iloc[0]}')


def split_mask(frame, period):
    return frame.date.between(pd.Timestamp(period[0]), pd.Timestamp(period[1]))


def versions():
    result = {'python': platform.python_version()}
    for name in ['numpy', 'pandas', 'scipy', 'scikit-learn', 'catboost',
                 'pyarrow', 'matplotlib', 'psutil', 'PyYAML', 'joblib', 'shap']:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = 'not installed'
    return result


def resources():
    memory = psutil.virtual_memory()
    return {'logical_cpus': psutil.cpu_count(), 'physical_cpus': psutil.cpu_count(logical=False),
            'total_ram_gib': memory.total / 2**30, 'available_ram_gib': memory.available / 2**30,
            'process_rss_gib': psutil.Process().memory_info().rss / 2**30,
            'free_disk_gib': psutil.disk_usage(str(ROOT)).free / 2**30}


@contextmanager
def stage(config, name):
    folder = output_path(config)
    folder.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler(folder / 'training.log', encoding='utf-8')])
    start = time.monotonic()
    logging.info('%s started; resources=%s', name, resources())
    try:
        yield
    finally:
        logging.info('%s elapsed=%.2fs; resources=%s', name, time.monotonic() - start, resources())


def run_cli(description, function, *, extra=None):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--config', default='configs/ml.yaml', help='YAML configuration; paths resolve from repository root')
    if extra:
        extra(parser)
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        with stage(config, function.__name__):
            function(config, args)
    except (ValueError, FileNotFoundError, RuntimeError, MemoryError) as error:
        logging.error('%s', error)
        sys.exit(1)
