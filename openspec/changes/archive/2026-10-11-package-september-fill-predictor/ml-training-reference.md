# Next-day container fill prediction

## Repository layout

| Location | Responsibility |
|---|---|
| `backend/app/ml/` | Offline training, search, evaluation, explanations, reports and CLI stages |
| `backend/viptop_fill/` | Shared pure feature construction and standalone inference source |
| `backend/configs/ml.yaml` | Source paths, date boundaries, sampling and resource limits |
| `backend/requirements-ml.txt` | Optional research dependencies, separate from the API environment |
| `backend/tests/ml/` | Focused ML checks |
| `scripts/` | Offline source-data generation and explicit superseded-run cleanup |
| `docs/` | Data-generation guides and application verification instructions |
| `backend/data/ml/september-fill-predictor/` | Current models, analysis, reports and developer delivery |

Code and configuration belong outside the git-ignored `backend/data/` directory.
The delivered `product/viptop_fill/` is a checksum-verified copy of the shared source.
Models, charts and `product.zip` are generated local artifacts; transfer the ZIP
explicitly to developers because it is not included in Git.
The source preparation utility is `scripts/prepare_training_data.py`; archived
generation manifests retain the command and hashes recorded when they were created.

## Historical source

The immutable historical source is `backend/data/bin_days_20231010_20261009_enriched.csv`.
Its 19 columns and values remain unchanged. Registry, population and district aliases
are reference inputs. No database ingestion, connection or data regeneration is required.

## Dates and features

Selected date T means the end of today in Europe/Vilnius. Forecast date D is T+1:
2026-09-15 predicts 2026-09-16; 2026-09-30 predicts 2026-10-01. History includes T;
D's assessment and collection outcome never enter the model. The four safe counters
from D are retained without another shift: holidays_since_last_collection,
collections_last_28d, missed_collections_28d and qr_alerts. Their definitions exclude D.
The CSV adapter projects only those columns and bin/date keys from D.

`backend/viptop_fill/features.py` is the shared pure feature script. The 21 active inputs
combine the existing 13 calendar/static/counter fields with days since successful
collection, attempt and previous assessment; previous assessment and yesterday's
status; 7/90-day successful and 90-day missed collection counts. See the current
run's feature_dictionary.csv for the ordered active schema and windows. IDs are
keys, genuine zeros remain valid and unknown observations remain missing.

Constructed feature DataFrames remain in memory during fitting and inference.
The reader streams complete bin batches before selecting labeled rows, and retains
bounded fitting samples. Research commands explicitly export keys, predictions and
aggregate analysis. The product predictor performs no implicit writes.

## Training and evaluation

| Stage | Target dates |
|---|---|
| Calibration/history only | 2023-10-10..2024-10-09 |
| Selection fitting | 2024-10-10..2026-07-31 |
| Algorithm/threshold selection | 2026-08-01..2026-08-31 |
| Final fitting of both candidates | 2024-10-10..2026-08-31 |
| Demo today selections | 2026-09-01..2026-09-30 |
| Comparative next-day targets | 2026-09-02..2026-10-01 |

CatBoost and Random Forest tune on 20,000 deterministic rows over two expanding
folds. Four coarse plus four refined candidates each produce 32 search fits.
Each selection and final fit uses 100,000 rows; both algorithms share sample keys.
Seed 42, four CPU threads, verified CatBoost GPU with 50% GPU RAM, a 600-second
search limit and 2.5-GiB process RSS limit are retained. Pilot/probes, two selection
fits, two final fits and a site-holdout diagnostic fit are accounted for separately.

August combined classes-3/4 F1 selects the winner and each P(3)+P(4) threshold
(0.05..0.95, step 0.05; ties prefer proximity to 0.5). Freeze these decisions before
final refitting and demo evaluation. September never fits preprocessing or models.
August scores describe selection-stage models, not models subsequently fitted on August.
Final refits use fixed iteration counts and no overlapping early-stopping set.

Product fill_level is five-class probability argmax. Research also reports the frozen
probability-sum urgent decision and grouped-argmax urgent scores: these can disagree.
Analysis includes EDA, active-input baselines, confusion matrices, ordinal/errors,
quality strata, daily comparisons, importance, bounded SHAP and separate cold-start
site diagnostics. Every figure has a source table.

## Reproduce

Use the existing isolated Python 3.12 environment or backend/requirements-ml.txt.
From backend/ in PowerShell:

```powershell
$mlPython = './data/ml/.venv/Scripts/python.exe'
& $mlPython -m unittest discover -s tests/ml -v
& $mlPython -m app.ml.run --config configs/ml.yaml
& $mlPython -m app.ml.verify --config configs/ml.yaml
& $mlPython -m app.ml.predict --config configs/ml.yaml --today 2026-09-15
```

Current artifacts are under `backend/data/ml/september-fill-predictor/`:
README_REPORT.md has actual results, models/ holds both final comparison candidates,
and product/ is the selected developer package. Relative YAML paths resolve from the
repository root. The full run retains feature frames in one process; no feature caches
are necessary. Completed stages retain their frozen selection/evaluation on rerun.

## Developer interface

Copy product/, install its pinned CPU requirements and import its shipped package:

```python
from viptop_fill import FillPredictor
predictor = FillPredictor.load('product')
result = predictor.predict_next_day(
    history_df=history, registry_df=registry, today='2026-09-15',
    day_counters_df=counters_for_2026_09_16, population_df=population,
)
# Exactly bin_id, fill_level (predicted integer 0..4).
```

The supplied registry determines coverage, including bins without history. The product
README documents DataFrame schemas, absent-counter behavior and the CSV adapter.
Inference uses CPU and requires neither database settings, the other model nor research
outputs. Load only trusted delivered model artifacts. A future database caller supplies
the same DataFrames; that connector is outside this implementation.
The CSV demonstration prints a preview; add `--output result.csv` only when an explicit
two-column export is wanted. `app.ml.verify` checks all 30 scenarios, hashes, samples,
selection boundaries, chart sources and an isolated CPU package invocation.

## Interpretation and artifacts

Targets are synthetic assessments, mainly on successful collection days. Observed
history contains no real fill measurements. Previously inspected September dates are
comparative rather than a new untouched holdout. Static snapshots and weak no-rating-
history performance limit transfer. Complete coverage does not establish accuracy on
unlabeled days. Earlier September observations can update later historical features,
without changing fitted parameters.

Old experiment directories are removed only after replacement verification. Immutable
sources, shared environments and unrelated generation work remain. The copied product
is checked again after cleanup; only the current run's model artifacts are retained.
