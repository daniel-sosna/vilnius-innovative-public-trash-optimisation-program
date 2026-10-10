# Proposal

## Why

Prioritisation and routing need to know when each bin is planned to be collected, and VipTop currently stores only past service events (`bin_hist`). VASA publishes a per-bin collection plan at `/vasa-api/api/v1/dumpsters-schedule/{external_id}`, so we can populate it now, without waiting for prediction.

## What Changes

- New `bin_schedule` table: one row per bin and planned collection date.
- New manual command `python -m app.interfaces.bin_schedule_sync`. It reads the stored bins, fetches each bin's schedule from VASA and replaces that bin's rows with the response. Each bin is committed in its own transaction, and a bin whose request fails keeps its previous rows.
- New setting `VASA_SCHEDULE_URL_TEMPLATE`, with the public endpoint as its default and the same HTTPS validation as the other VASA URL templates.
- **BREAKING (developer workflow):** when the CSV table import replaces `bins` without a `bin_schedule` file, it now also empties `bin_schedule`. Before, it never emptied a table that had no file. Without this change, the new foreign key would make the current sites/bins/bin_hist import fail.

Observed source behaviour, probed on 2026-10-10:
- The response is `{"schedule": ["YYYY-MM-DD", ...]}` and covers the **current calendar month only**, past days included. Query parameters (`from`, `to`, `month`, `page`, ...) are ignored, so other months cannot be fetched.
- An unknown or invalid external ID returns `200 {"schedule": []}`, the same as a bin with no planned dates.
- Dates have no time of day. Frequencies seen range from once a month to almost daily.
- A request takes about 0.3 s. A full pass over the ~22k bins in the current export takes about 25 min with 4 workers.

## Capabilities

### New Capabilities
- `collection-schedules`: obtaining and storing VASA's planned collection dates per bin as a refreshable current-month snapshot, through an explicitly invoked command.

### Modified Capabilities
- `table-csv-import`: replacing `bins` without a `bin_schedule` file now also empties `bin_schedule` in the same transaction. This is an exception to the rule that tables without a file are never emptied implicitly.

## Impact

- **Database:** new Alembic migration `0005` creates `bin_schedule` with a foreign key to `bins.id` (`ON DELETE CASCADE`). Bins removed by `bin_sync` cleanup lose their schedule rows automatically.
- **Backend code:** new `app/services/bin_schedule_sync.py` and `app/interfaces/bin_schedule_sync/` CLI. `VasaClient` gets a `schedule()` method, `Settings` gets the new URL template, and `table_import` adds the implicit `bin_schedule` reset.
- **Shared contracts:** the CSV import behaviour above. `bin_schedule` can also be exported and imported as `bin_schedule_<digits>.csv` like the other tables.
- **Not in scope:** HTTP API or UI for schedules, keeping past months' schedules, resuming interrupted runs, running automatically on a timer.
- **Assumptions:** dates are Vilnius local calendar dates. One response is the complete current-month plan for that bin. An empty list is stored as "no planned dates", because it cannot be told apart from an unknown bin.
