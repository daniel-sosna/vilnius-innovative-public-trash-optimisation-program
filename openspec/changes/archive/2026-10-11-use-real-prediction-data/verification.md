# Verification

Manual end-to-end check of tasks 4.1 and 5.1, run in the Docker stack with the shared data folder
(history CSV, bins export, `bin_population.csv`, `ml/september-fill-predictor/product/`).

## Guards

| Command | Result |
|---|---|
| `collection_plan` (no `--date`) | argparse error, exit 1 |
| `--date 2026-10-11` | "only September 2026 ... is available for simulation", exit 1 |
| `--date 2026-13-01` | not a YYYY-MM-DD date, exit 1 |
| history CSV absent (empty data dir) | "Historical data is not present in the system" |
| model file `district_aliases.json` absent | "Fill prediction model is not present: district_aliases.json missing ...", exit 1 |

`collection_stops` stayed empty after every failed run.

## Run: `--date 2026-09-15` (threshold 2)

- Wall time 55 s.
- bins evaluated 21,951; due 8,863; bins of the stops without capacity 0.
- Stops stored under 2026-09-16: 6,206 (Ecoservice 2,613, Ekonovus 2,305, Kauno švara 1,288; unassigned 0). None under 2026-09-15.
- Levels in stops: 0: 497, 1: 1,127, 2: 2,684, 3: 4,887, 4: 3,976 (3 and 4 are due).
- 40% of evaluated bins fall in levels 3-4; not investigated.

## Rerun: `--threshold 3`

- Wall time 56 s; due 3,976 (level 4 only); stops 3,186 (Ecoservice 1,492, Ekonovus 1,147, Kauno švara 547).
- 2026-09-16 was replaced; no other date has stops (no other date was built, so "other dates unchanged" was not exercised).

## Gap handling (patched predictor, before the model was available)

A predictor missing one stored bin and adding an unknown bin ID built successfully: the missing bin was in no stop and the unknown ID was ignored.
