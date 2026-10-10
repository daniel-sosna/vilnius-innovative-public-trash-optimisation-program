# Archive reconciliation — 2026-10-11

All 20 implementation tasks are complete. The predecessor
`train-fill-classifier` is archived as superseded experiment history without
syncing its obsolete delta. This change supplies the complete current
`daily-fill-prediction` contract; its Purpose and 19 requirement blocks are
synced to the new main spec unchanged.

The retained run records 14 passing focused checks, 31 passing integrated
checks, all 30 September today/next-day mappings and fresh-process CPU product
verification. The subsequent repository-layout review moved the preparation
utility from ignored data to `scripts/prepare_training_data.py`, updated its
paths and documented the layout. No training data or model artifact changed.

Archiving changes only OpenSpec documentation. The verified developer delivery
remains at `backend/data/ml/september-fill-predictor/product.zip`; models,
comparisons, charts and the English report remain in that run directory.
Unrelated data-generation and UI changes remain open.
