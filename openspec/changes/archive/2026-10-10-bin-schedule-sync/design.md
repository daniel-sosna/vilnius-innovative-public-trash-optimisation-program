# Design

## Context

- Bins are stored in `bins` (`external_id` is the VASA ID). They come from the CSV table import in development and from `bin_sync` otherwise.
- `app/integrations/vasa.py` already provides `VasaClient._get`: HTTPS GET with timeout, five attempts with exponential backoff, and no redirects. `Settings` validates the VASA URL templates.
- `app/services/bin_sync.py` has `bounded_responses()` (fetches with at most N futures in flight and returns results one at a time) and a `transaction()` helper that sets statement and lock timeouts.
- `table_import` empties replaced tables with one `TRUNCATE <list>` and resets each imported table's identity with `pg_get_serial_sequence(table, 'id')`. PostgreSQL rejects `TRUNCATE bins` while another table references `bins` unless that table is in the same statement.
- Source behaviour (current month only, no parameters, empty list for unknown IDs): see proposal.md.

## Goals / Non-Goals

**Goals:**
- Fill and refresh `bin_schedule` for all stored bins with one command that runs a full pass in under about 30 min.
- Keep the existing CSV import workflow working unchanged for teammates who have no schedule export.

**Non-Goals:**
- Keeping schedules from past months, or comparing planned and actual collections.
- Resume checkpoints, run records, or locking against `bin_sync`.
- Exposing schedules over HTTP or in the UI. That belongs to the consumer change.

## Decisions

### Table `bin_schedule(id, bin_id, date)`
```
bin_schedule
  id      BIGINT GENERATED ALWAYS AS IDENTITY  PK
  bin_id  BIGINT NOT NULL  FK -> bins.id ON DELETE CASCADE
  date    DATE   NOT NULL
  UNIQUE (bin_id, date)   -- also serves bin lookups
  INDEX  (date)           -- "which bins are due on day X"
```
- The surrogate `id` exists only so the table works with `table_import`, which requires an `id` identity column for its sequence reset. The natural key is `(bin_id, date)`.
- The FK is on `bins.id` rather than `external_id`, matching `bin_hist`. With `ON DELETE CASCADE`, `bin_sync` cleanup removes schedules with no extra code.
- Alternative: a single `planned_dates DATE[]` column on `bins`. Rejected because it makes "due on date X" queries and indexing awkward, and every refresh would rewrite the bins table.
- Column name `date` matches `bin_hist.date`.
- A `fetched_at` column was rejected (see the spec: empty and never-fetched are not distinguished).

### Separate command, not part of `bin_sync`
The command is `python -m app.interfaces.bin_schedule_sync` (CLI) plus `app/services/bin_schedule_sync.py` (loop and persistence). It reads its bins from the database, so it works the same after a CSV import or after `bin_sync`. Folding it into `bin_sync` would tie it to that importer's pass and checkpoint model, and to a run the README tells developers not to use.

### Reuse the VASA client and the bounded fetch
- Add `vasa_schedule_url_template` to `Settings`. The default is `https://atliekuaiksteles.vasa.lt/vasa-api/api/v1/dumpsters-schedule/{external_id}`, validated by the existing `{external_id}` HTTPS validator.
- Add `VasaClient.schedule(identity) -> list[date]`. It parses and validates the response, raising `VasaError` on a missing or non-list `schedule` or a non-ISO date, and deduplicates the dates.
- Reuse `bounded_responses()` and `transaction()` by importing them from `app.services.bin_sync`. They are not moved: moving them would change an unrelated module for no gain.
- Requests run in a `ThreadPoolExecutor(workers)`. Writes happen in the consuming (main) thread, one transaction per bin: `DELETE ... WHERE bin_id = :id` followed by a multi-row `INSERT`. A single writer avoids session sharing across threads, and each write is a few milliseconds compared with about 300 ms per request.

### Per-bin replace instead of whole-table swap
Each bin commits independently (see the spec). A whole-table swap at the end would keep the table consistent as of one moment. But it would lose 25 minutes of work on any failure, and it would hold every response in memory. A mix of months right after the month changes is acceptable because a re-run fixes it.

### Bins to process
`SELECT id, external_id FROM bins ORDER BY id [LIMIT n]` is read once at start, about 22k small rows. If a bin is deleted mid-run, its insert hits an FK violation. That bin's transaction rolls back and is reported as failed (see the spec).

### CSV import: implicit reset of `bin_schedule`
In `load_tables`, when `bins` is among the files and `bin_schedule` is not, add `bin_schedule` to the `TRUNCATE` list and log it. This mirrors the existing `SYNC_STATE_TABLES` handling. `bin_schedule` is a leaf table, so this cannot cascade any further. `bin_schedule` is not reset on a `bin_hist`-only import, because nothing would break.

### Exit codes
Same meanings as `bin_sync`, so operators and scripts read both commands the same way: 0 = every bin processed without failure. 1 = any failure, invalid arguments or configuration, or no stored bins. 2 = a run limited by a nonzero `--max-bins` with no failures. Failure wins over the limit. A nonzero limit always exits 2, even if it covers every stored bin, because `bin_sync` treats limits the same way. `--max-bins` counts bins rather than `bin_sync`'s `--max-sites` addresses, so the option name differs on purpose.

## Risks / Trade-offs

- [The source window is the current month only] → Dates are lost once the month ends. This is accepted by choice (snapshot). Proposal and README state it.
- [An empty list is ambiguous: unknown bin or no plan] → The summary reports the empty count. A sudden spike in empties after a run points to a source problem.
- [Last-days-of-month problem: early next month the snapshot keeps last month's dates until it is re-run] → Consumers filter on `date >= today`. README advises re-running at the start of each month.
- [The CSV import now empties a table implicitly] → It is limited to `bin_schedule` when `bins` is replaced, logged in the output, documented in the README, and covered by the modified spec. The data can be fetched again in minutes.
- [Running at the same time as `bin_sync`] → Only per-bin FK failures on deleted bins are possible. They are reported and fixed by re-running. No lock is added.
- [Measured full run, 2026-10-10] 21,951 bins with 4 workers took 12m58s and exited 0: 21,840 with dates, 111 empty, 0 failed, 203,222 dates stored.
- [VASA rate limiting with more workers] → `_get` already retries 429 with backoff. The default stays at 4 workers.

## Migration Plan

1. Migration `0005_bin_schedule` creates the table, and its downgrade drops it. `start.sh` applies it on container start, as for the earlier migrations.
2. Run `python -m app.interfaces.bin_schedule_sync` once after collection data is loaded.
3. Rollback: downgrade to `0004`, which drops only `bin_schedule`. The `table_import` change is harmless without the table, because the reset only applies when the table exists in the schema metadata.
