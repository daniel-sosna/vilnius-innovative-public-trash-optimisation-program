# Fill prediction

Offline training compares CatBoost and Random Forest and exports one selected
model. Behaviour and date/input contracts are specified in
[`daily-fill-prediction`](../../openspec/specs/daily-fill-prediction/spec.md).
The [collection plan](collection-plan.md) uses its own mock provider.

## Setup

Use Python 3.12 and an isolated environment. From the repository root:

```powershell
python -m venv backend/data/ml/.venv
& ./backend/data/ml/.venv/Scripts/python.exe -m pip install -r backend/requirements-ml.txt
```

The research environment includes both model libraries and analysis tools.
CatBoost training requires a working CUDA device; product inference uses CPU.
The API environment and Docker image do not install the research dependencies.

## Configuration and commands

[`backend/configs/ml.yaml`](../../backend/configs/ml.yaml) defines source files,
time partitions, samples and resource limits. Relative paths resolve from the
repository root. For shared exports, set these paths to the shared folder;
offline YAML/CLI paths are explicit and do not read backend database settings.
Application data-directory configuration is in [Development](../development.md#data-directory).

From `backend/`, using that environment:

```powershell
$mlPython = './data/ml/.venv/Scripts/python.exe'
& $mlPython -m app.ml.run --config configs/ml.yaml
& $mlPython -m app.ml.predict --config configs/ml.yaml --today YYYY-MM-DD
```

- `run` reads source CSVs, trains the configured candidates and writes models,
  analysis, predictions and a product directory under `paths.output`. Completed
  stages reuse their recorded selection and evaluation.
- `predict` prints a preview. Add `--output result.csv` for an explicit export.
- `--config` chooses another YAML file. Stage commands under `app.ml` expose `--help`.
- Source preparation is described in [Fill/QR generation](fill-qr.md). Inference
  uses the fixed enriched CSV; source generation is a separate command.

## Delivery and runtime

The configured run directory contains:

| Path | Contents |
|---|---|
| `models/` | Both final comparison candidates |
| `README_REPORT.md`, `charts/`, `chart_sources.csv` | Results, figures and their source-table index |
| `feature_dictionary.csv` | Ordered active inputs and window definitions |
| `product/` | Selected model, preprocessing, portable source, CPU dependencies and usage example |
| `product.zip` | Developer handoff archive |

`backend/viptop_fill/` supplies shared feature construction and inference;
`backend/app/ml/` supplies research orchestration. The product README documents
the developer invocation and caller DataFrames. Copy the product, install its
`requirements.txt`, and run its example with supplied input frames. Generated
artifacts are git-ignored and must be transferred separately.

The bounded CSV adapter scans the full source for each requested date; a full
registry scan takes roughly 4–5 minutes on the development machine. Supplying
DataFrames avoids repeated CSV scans. Feature frames stay in memory.

## Assumptions

Targets are synthetic assessments concentrated on collection days; measured fill
observations are unavailable. Registry attributes are static snapshots. Accuracy
on the labeled subset does not establish accuracy on unlabeled bins or bins
without assessment history. The run report contains measured comparisons and
cold-start results.
