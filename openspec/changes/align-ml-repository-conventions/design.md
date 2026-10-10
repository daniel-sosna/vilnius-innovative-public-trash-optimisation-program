# Design

## Context

origin/main adds collection planning, map layers, shared data-directory setup and
a topic-based documentation policy. The ML branch adds offline generation,
training and a portable viptop_fill package. The collection-plan provider remains
a mock; connecting database observations to the portable predictor is separate work.

## Decisions

- Resolve README using main's structure, adding only relevant table rows, tree
  entries and index links. Keep it below 150 lines.
- Put concise setup, commands, paths, durations and assumptions in
  docs/data/fill-prediction.md and docs/data/fill-qr.md. Link the specs and delivered
  developer README for behavioural contracts. Keep detailed analysis and rule
  revisions in their archived changes; avoid altering recorded experiment facts.
- Preserve separate optional research dependencies and portable source under
  backend/viptop_fill. API imports must not require optional model libraries.
- Offline inputs remain explicit YAML/CLI paths. A shared data folder is supplied
  through those paths; export checks use the configured registry directory.
  Product isolation uses the invoking interpreter rather than a checkout-specific
  virtual environment. Do not change model payloads or feature formulas.
- Record checks in this change. Use existing ML/generator checks, document/link
  validation, standalone package verification and frontend build/lint. A live
  database is not needed to establish the merge and documentation changes.

## Risks

Moved guide references can break tooling; search active source and docs after moves.
Generator source hashes change when its guide pointer changes; preserve existing
generation manifests as records of the actual generating source. Verify that the
executable generator AST, CSV and delivered model hashes stay unchanged.
