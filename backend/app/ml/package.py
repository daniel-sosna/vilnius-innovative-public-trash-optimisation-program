"""Export and independently verify the selected next-day predictor."""
from itertools import islice
from pathlib import Path
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile

import joblib
import numpy as np
import pandas as pd

from .common import ROOT, bin_blocks, digest, output_path, read_json, source_path, write_json, run_cli
from .features import FEATURES, aliases, contradictory_sites
from .modeling import load_model


def export_product(config):
    folder = output_path(config, 'product')
    folder.mkdir(parents=True, exist_ok=True)
    selected = read_json(output_path(config, 'selection.json'))
    bundle = load_model(output_path(config, 'models', f'{selected["model"]}.joblib'))
    joblib.dump({'name': bundle.name, 'preprocessing': bundle.preprocessing,
                 'model': bundle.model, 'metadata': bundle.metadata}, folder / 'model.joblib', compress=3)
    source = ROOT / 'backend/viptop_fill'
    target = folder / 'viptop_fill'
    target.mkdir(exist_ok=True)
    for item in source.glob('*.py'):
        shutil.copy2(item, target / item.name)
    write_json(folder / 'district_aliases.json', aliases(config))
    shutil.copy2(output_path(config, 'feature_dictionary.csv'), folder / 'feature_dictionary.csv')
    dependencies = ['numpy', 'pandas', 'scipy', 'scikit-learn', 'joblib', 'holidays']
    if bundle.name == 'catboost':
        dependencies.append('catboost')
    (folder / 'requirements.txt').write_text('\n'.join(f'{name}=={importlib.metadata.version(name)}' for name in dependencies) + '\n', encoding='utf-8')
    (folder / 'example.py').write_text(
        '"""Supply your own already-loaded DataFrames; the predictor performs no writes."""\n'
        'from viptop_fill import FillPredictor\n\n'
        'def predict(history_df, registry_df, today, day_counters_df=None, population_df=None):\n'
        '    predictor = FillPredictor.load(__import__("pathlib").Path(__file__).parent)\n'
        '    return predictor.predict_next_day(history_df, registry_df, today, day_counters_df, population_df)\n', encoding='utf-8')
    (folder / 'README.md').write_text(f'''# VipTop next-day fill predictor

Selected final model: **{bundle.name}**. Final fitting period ends 2026-08-31.
Algorithm, parameters and operational thresholds were selected before September.
The immutable source CSV contains synthetic historical assessments; this package
does not generate data, connect to a database, train or write predictions implicitly.

## Run on CPU

Use Python 3.12 and install `python -m pip install -r requirements.txt`. Keep the
supplied `viptop_fill/` package next to your integration script, or add this product
directory to your Python path. Load only this trusted delivered model artifact.

```python
from viptop_fill import FillPredictor
model = FillPredictor.load('/path/to/product')
result = model.predict_next_day(
    history_df=history, registry_df=registry, today='2026-09-15',
    day_counters_df=counters_for_2026_09_16, population_df=population,
)
# result columns are exactly bin_id and fill_level (predicted integer 0..4).
```

See `example.py` for a callable wrapper. The caller's DataFrames are unchanged.
No research folder, feature cache, GPU or database configuration is needed.

## Input DataFrames

- `history_df`: `bin_id`, `date`, `collection_status`, `fill_level`. Outcomes through
  selected today T inclusive are available. All daily rows, including NULL ratings,
  are needed for collection windows. Statuses are none/collected/retry_collected/
  failed/missed. Assessments are nullable integer 0..4. Dates are consecutive per
  observed bin, with unique keys; future outcomes are ignored. Empty history is
  supported when these four columns exist.
- `registry_df`: unique `bin_id` (or `id`), `site_id`, `waste_type`, `capacity_m3`,
  `sub_district`, `object_group`. Optional `resident_factor`/`population_cell_id`
  can be provided here. One prediction is returned per supplied registry bin.
- `day_counters_df` (optional): `bin_id`, `date=D` and any supplied safe counters:
  holidays_since_last_collection, collections_last_28d, missed_collections_28d,
  qr_alerts. D=T+1. These counter definitions already exclude D, so values are used
  without another shift. Extra outcome columns cannot enter the features.
- `population_df` (optional): unique `bin_id`, `population_cell_id`, resident_factor;
  supplements the registry. Use pandas NA/NaN/None for missing values.

The eight additional historical inputs are constructed by `viptop_fill/features.py`
in memory; they are not input columns the caller must store. The ordered 21-field
model contract is in feature_dictionary.csv. Genuine zero remains distinct from
unknown. Missing safe counts are reconstructed only where history proves them;
QR remains unknown unless a preceding success establishes reset zero. Static
unknown categories and missing/invalid attributes receive explicit handling.

## September demo and CSV adapter

Selected today means end-of-day in Europe/Vilnius. 2026-09-15 forecasts 2026-09-16;
2026-09-30 forecasts 2026-10-01. Training and inference share the same pure builder.
To read the existing immutable CSV in bounded batches, from this directory:

```powershell
python -m viptop_fill.csv_demo --product . --daily /path/to/history.csv --registry /path/to/bins.csv --population /path/to/population.csv --today 2026-09-15
```

This prints a preview and returns predictions in memory. `--output result.csv`
explicitly requests a two-column export. No constructed feature table is saved.
A future database integration supplies the same DataFrames; no connector is included.

## Output interpretation

`fill_level` is the five-class probability argmax. It is a prediction in a separate
result frame, never an update to the historical source assessment. It describes
the synthetic pre-service assessment for tomorrow. Models also support internal
probabilities; research's P(3)+P(4) operational threshold is distinct from argmax.
Synthetic collection-day metrics do not establish real-world/unlabeled-day accuracy.
New bins without assessment history can have substantially weaker predictive quality.
Registry coverage does not imply equal confidence. Versions and provenance are
recorded in manifest.json and the model metadata.
''', encoding='utf-8')
    manifest = {'model': bundle.name, 'metadata': bundle.metadata, 'features': FEATURES,
                'response_columns': ['bin_id', 'fill_level'], 'inference_device': 'cpu',
                'date_contract': 'Forecast D=today+1; outcomes <=today; four safe D counters unchanged',
                'files': {p.relative_to(folder).as_posix(): digest(p) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name != 'manifest.json'}}
    write_json(folder / 'manifest.json', manifest)


def verify_product(config):
    """Fresh-process check using raw observations only; feature values are never saved."""
    product = output_path(config, 'product')
    manifest = read_json(product / 'manifest.json')
    for name, sha in manifest['files'].items():
        if digest(product / name) != sha:
            raise ValueError(f'Product file checksum mismatch: {name}')
    raw = pd.concat(list(islice(bin_blocks(config), 6)), ignore_index=True)
    registry = pd.read_csv(source_path(config, 'registry'), keep_default_na=False, na_values=['', 'NULL'])
    history_ids = pd.read_csv(output_path(config, 'bin_label_counts.csv'), usecols=['bin_id']).bin_id
    extras = registry.loc[~registry.id.isin(history_ids)].head(2).id
    mapping = aliases(config)
    registry.loc[registry.site_id.isin(contradictory_sites(config, mapping)), 'sub_district'] = '__AMBIGUOUS__'
    registry = registry.loc[registry.id.isin(set(raw.bin_id) | set(extras))].copy()
    population = pd.read_csv(source_path(config, 'population'), keep_default_na=False, na_values=['', 'NULL'])
    population = population.loc[population.bin_id.isin(registry.id)]
    expected = {}
    selected = read_json(output_path(config, 'selection.json'))['model']
    for today, target in [('2026-09-15', '2026-09-16'), ('2026-09-30', '2026-10-01')]:
        output = pd.read_csv(output_path(config, 'predictions', f'{selected}_{target}.csv'))
        subset = output.loc[output.bin_id.isin(registry.id)].sort_values('bin_id')
        expected[today] = {'response': subset[['bin_id', 'predicted_fill_level']].astype(int).to_numpy().tolist(),
                           'probabilities': subset[[f'probability_class_{i}' for i in range(5)]].to_numpy().tolist()}
    # Temporary raw fixtures are copies of the immutable source, never engineered inputs.
    with tempfile.TemporaryDirectory(prefix='verify-product-', dir=output_path(config)) as temp:
        isolated = Path(temp).resolve()
        if not isolated.is_relative_to(output_path(config).resolve()):
            raise ValueError('Unexpected isolated verification path')
        shutil.copytree(product, isolated / 'product', ignore=shutil.ignore_patterns('__pycache__'))
        raw.to_csv(isolated / 'history.csv', index=False)
        registry.to_csv(isolated / 'registry.csv', index=False)
        population.to_csv(isolated / 'population.csv', index=False)
        (isolated / 'expected.json').write_text(json.dumps(expected), encoding='utf-8')
        script = '''import json,sys
from pathlib import Path
import pandas as pd
import numpy as np
root=Path(__file__).parent
sys.path.insert(0,str(root/'product'))
from viptop_fill import FillPredictor
from viptop_fill.features import build_next_day_features
from viptop_fill.csv_demo import predict_csv
model=FillPredictor.load(root/'product')
read=lambda name:pd.read_csv(root/name,keep_default_na=False,na_values=['','NULL'])
raw,registry,pop=read('history.csv'),read('registry.csv'),read('population.csv')
expected=json.loads((root/'expected.json').read_text())
observed=[]
before=set(root.rglob('*'))
for today,values in expected.items():
    result=model.predict_next_day(raw,registry,today,raw,pop)
    assert list(result)==['bin_id','fill_level']
    assert result.sort_values('bin_id').astype(int).to_numpy().tolist()==values['response']
    features=build_next_day_features(raw,registry,today,raw,pop,model.district_aliases).sort_values('bin_id')
    assert np.allclose(model.predict_proba(features),values['probabilities'],atol=1e-8)
    streamed=predict_csv(root/'product',root/'history.csv',registry,today,pop,chunk_rows=97 if today.endswith('15') else 1549)
    assert streamed.sort_values('bin_id').astype(int).to_numpy().tolist()==values['response']
    observed.append({'today':today,'rows':len(result)})
assert set(root.rglob('*'))==before, 'Runtime wrote files'
assert 'app.ml' not in sys.modules
print(json.dumps({'passed':True,'cases':observed,'probability_equality':True,'csv_batch_equality':True,'isolated':True,'inference_device':'cpu','implicit_writes':False}))
'''
        (isolated / 'verify.py').write_text(script, encoding='utf-8')
        env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
        completed = subprocess.run([sys.executable, '-I', '-B', str(isolated / 'verify.py')],
                                   cwd=isolated, env=env, capture_output=True, text=True, timeout=120)
        if completed.returncode:
            raise ValueError('Isolated product verification failed: ' + completed.stderr[-2500:])
        result = json.loads(completed.stdout)
    result.update(product_model=selected, active_features=len(FEATURES), manifest_sha256=digest(product / 'manifest.json'))
    write_json(output_path(config, 'product_verification.json'), result)


if __name__ == '__main__':
    run_cli('Verify the delivered product in a fresh isolated CPU process.', lambda c, a: verify_product(c))
