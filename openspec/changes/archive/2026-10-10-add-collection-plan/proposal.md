# Proposal

## Why

An ML model will soon predict each bin's fill level for a day, and routing needs that turned into the list of sites each waste carrier has to visit. We fix the contract now and drive it with a mock prediction, so routing can be built against real bins and sites before the model is ready.

## What Changes

- A daily **collection plan**: for a given date, every stored bin gets a predicted fill level (0-4). Bins above a threshold are due. A stop exists for each (date, waste carrier, site) that has at least one due bin.
- Bins with no waste carrier go to an explicit **unassigned** group and are not dropped.
- The carrier's truck empties **all** of its bins at a site, not only the due ones. So each stop lists every bin of its carrier at the site, with its predicted fill level and a `due` flag, and holds two totals over all of them: `overall_volume_m3` (total capacity) and `overall_predicted_fill_m3` (predicted volume of waste), for truck-capacity routing.
- A command rebuilds the plan for one date (default today) with a threshold (default 2, strictly greater). It replaces only that date's plan, atomically, and prints a summary.
- A Python read function returns a date's stops grouped by carrier, optionally limited to some carriers. Routing calls it directly. No HTTP endpoint or UI in this change.
- The prediction source is a **mock**: a uniform random fill level 0-4 per real bin, seeded from the date, so a date always gives the same plan. The real model will replace only this source.
- CSV import that replaces `bins` empties the plan, like the other bin-derived tables.

## Capabilities

### New Capabilities

- `collection-plan`: the daily list of sites each waste carrier must serve, derived from predicted bin fill levels and a threshold, with the bins the carrier's truck empties at each stop. Covers the prediction input contract, the mock prediction, the rebuild command and reading the plan by carrier.

### Modified Capabilities

- `table-csv-import`: replacing `bins` also empties the collection plan, and the output names the command that refills it.

## Impact

- **Database:** new tables `collection_stops` and `stop_bins` (Alembic migration). They reference `sites` and `bins` and cascade on delete.
- **Backend:** a new CLI module under `app/interfaces/`, a prediction source under `app/ml/` (mock for now), and a service with the read function for routing. Also a small change to `table_import` so derived tables are emptied.
- **Shared contracts:** (1) the predictor output, a fill level 0-4 per bin for a date, which the data/ML side must produce; (2) the plan read by routing. Routing will write its own output separately and not modify this plan.
- **Not affected:** `bin_schedule`, `bin_hist`, `bin_days`, trucks, the frontend and HTTP APIs.
- **Assumptions:** all trucks can take any waste type, so only total volume matters per stop. Mock fill levels are random and not realistic. A missing `capacity_m3` counts as 0 and is reported. A fill level is translated to a share of the bin's capacity (0 -> 20%, 1 -> 50%, 2 -> 80%, 3 -> 100%, 4 -> 150%; above 100% means over-full), and that share is an assumption, not measured data.
