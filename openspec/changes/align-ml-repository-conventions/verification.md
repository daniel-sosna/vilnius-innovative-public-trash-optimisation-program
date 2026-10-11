# Merge verification

See `verification.json` for exact parents, timestamps, hashes and results.

| Check | Invocation / result |
|---|---|
| ML focused suite | From backend: `python -B -m unittest discover -s tests/ml -q`; 14 passed |
| Generator suite | From root: `python -B -X utf8 -m unittest discover -s scripts/tests -q`; 20 passed |
| Generator fixture | `python -B -X utf8 scripts/tests/check_fill_qr_pipeline.py`; 90 rows, 5 excluded bins, passed |
| Full saved delivery | From backend: `python -B -m app.ml.verify --config configs/ml.yaml`; 31 checks, 30 next-day dates, both candidates and isolated CPU product passed |
| Frontend | Installed package-lock.json with `npm ci --ignore-scripts --no-audit --no-fund`; `tsc -b`, `vite build` and `eslint .` passed |
| Backend | Isolated environment from `uv sync --project backend --locked --no-install-project`; app import/OpenAPI passed with 16 paths, no optional ML libraries imported |
| Migrations | `python -B -m alembic heads`; one head, `0016` |
| CLI imports | All 13 offline ML commands and collection-plan `--help` passed |
| Documentation | 16 active Markdown files, 99 local links/anchors, all docs indexed, README 104 lines |
| OpenSpec | Change validates strictly; all 19 main specs validate in normal mode |

The existing ML integration fixture was updated to supply source exports in its
configured directory. The ML suite's first run exposed missing fixture exports;
after adapting the fixture, all 14 checks passed. The production source guard
uses the configured registry directory rather than another checkout's defaults.

Detailed ML and generation guides and the rule-change log were moved byte-for-byte
after newline normalization into their owning archived changes. The active guides
describe setup, commands, configuration, costs and assumptions, linking the specs
for contracts. No generated source CSV, trained model or product ZIP was replaced.
Generator code differs only in its module-docstring guide pointer; executable
AST equality with the branch parent was verified. Generation manifests retain the
hashes of the code that actually produced the data.

The frontend reports a large-bundle warning. Upstream specs report existing
long-requirement warnings; the maintenance change itself passes strict validation.
The branch diff against origin/main passes the whitespace check. Four blank-EOF
warnings in the full merge diff are from files identical to upstream main;
those files and archived upstream evidence were retained unchanged. Redundant EOF
blank lines in nine ML entrypoints were removed with AST equality checked.
No live database or browser session was used. These checks cover imports, static
builds, the existing logic suites and the standalone ML package, not a live
database migration or end-to-end UI flow.
