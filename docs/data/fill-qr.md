# Synthetic fill and QR generation

Offline utilities prepare a bin-day CSV and synthetic assessment/QR labels.
Behaviour is specified in
[`synthetic-fill-and-qr`](../../openspec/specs/synthetic-fill-and-qr/spec.md).
These commands do not require a database.

## Setup and inputs

Use Python 3.12. From the repository root:

```powershell
python -m pip install -r scripts/requirements-fill-qr.txt
```

The base preparation utility also imports the backend's population-allocation
and calendar algorithms. `scripts/prepare_training_data.py --help` lists its
interval options. Its registry, schedule, service-history and population-density
exports are read from `backend/data/`; it writes the population export, base
bin-day CSV, observed daily service export and generation manifests there.

```powershell
python scripts/prepare_training_data.py --start YYYY-MM-DD --end YYYY-MM-DD
python scripts/adapt_fill_qr_rules.py --source /path/to/supplied-rules.md
python scripts/fill_qr.py
```

Preparation replaces its generated exports. Run it only when deliberately
building a source dataset; prediction uses the fixed enriched CSV.

## Generation options

`scripts/fill_qr.py --help` lists defaults and options:

| Option | Purpose |
|---|---|
| `--input`, `--output` | Base and enriched CSV paths |
| `--bins`, `--population`, `--schedule` | Reference exports; supply explicit paths for a shared folder |
| `--start`, `--end`, `--seed` | Inclusive interval and deterministic seed |
| `--rules` | Adapted English rules Markdown |
| `--diagnostics` | Destination for manifests, calibration and diagnostic arrays |
| `--calibration` | Reuse a frozen calibration matching the input provenance |
| `--fit-end` | Override the calibration fitting boundary |
| `--overwrite` | Explicitly allow replacement of the enriched output |

Defaults use the supplied exports under `backend/data/`. The rule adapter writes
Markdown, PDF, normalization aliases and a change log under `backend/data/rules/`;
`--output-dir` changes that destination. Run from the repository root so relative
CLI paths resolve consistently. [Development](../development.md#data-directory)
describes data-folder configuration for application commands.

## Analysis and assumptions

`scripts/validate_fill_qr.py` accepts the generator's path/interval options and
writes verification records, six charts, source arrays, sensitivity results and
`report.md` under `--diagnostics`. It reads the enriched CSV and does not regenerate
it. `--skip-full-verification` reuses a record only after checking source/output
hashes. Full generation and independent row-by-row verification are long-running;
the dataset has about 24 million daily rows.

The scenario assumes static registry/population snapshots, synthetic service
outcomes, no dated events and an assumed fullness response. Calibration uses a
fixed fitting period and is reused for subsequent periods and sensitivities.
No measured fill history or justified waste bulk density is available. Diagnostic
source-demand conservation does not establish physical volume balance or
real-world predictive accuracy.
