# Proposal

## Why

The ML branch must incorporate origin/main's application work and documentation
conventions without losing its verified standalone predictor or fixed training
data. The merge conflicts in README.md, and the ML guides still use the flat
documentation layout.

## What Changes

- Merge origin/main into ml-training and retain its concise README and docs index.
- Consolidate operational ML and generation instructions under docs/data/;
  retain detailed experiment and rule-change evidence in the owning changes.
- Update affected links, script references and environment-dependent verification
  paths without changing generation formulas, model inputs or predictions.
- Verify the merged application and standalone delivery; record results here.

## Capabilities

No spec-level behaviour changes. Existing daily-fill-prediction,
synthetic-fill-and-qr and collection-plan contracts remain authoritative.
This maintenance change declares skip_specs.

## Impact

README.md, docs/data/fill-prediction.md, docs/data/fill-qr.md, relevant topic
documents, offline tooling and archived evidence locations. Preserve the input
CSV, trained bundles and product archive. No database ingestion, retraining,
service deployment or new test framework.
