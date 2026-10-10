# Bin synchronization (VASA)

`bin_sync` refreshes `sites`, `bins` and `bin_hist` from the VASA API. It is slow: a full pass takes hours. Use it only to refresh the shared data snapshot. For development, use the [CSV import](import.md). Behaviour is specified in [`bin-synchronization`](../../openspec/specs/bin-synchronization/spec.md).

```bash
docker compose exec backend uv run python -m app.interfaces.bin_sync --max-sites 10                # trial
docker compose exec backend uv run python -m app.interfaces.bin_sync --max-sites 0 --max-tiles 0   # full pass
```

| Option | Default |
|---|---|
| `--bbox WEST SOUTH EAST NORTH` | `24.98 54.55 25.52 54.85`, inclusive point bounds |
| `--zoom` | 17 |
| `--workers` | 4 concurrent requests |
| `--max-sites` | 10. 0 means unlimited. |
| `--max-tiles` | 0, meaning unlimited |

## Scope

- The sync reads VASA cluster tiles, with bin details and paginated history for each bin.
- It imports only Mixed municipal waste, Paper/plastic waste and Glass waste. It excludes `Individualios valdos`, keeps only bins whose city is Vilnius or missing, and keeps only points inside `--bbox`.
- Detail attributes are authoritative, but coordinates come from the tile.

## Runs, resume and cleanup

- **Trial runs.** Any nonzero limit makes a run a trial. A trial exits 2 and never removes bins.
- **Resuming.** A matching incomplete run resumes. Bounds, zoom, URLs and the filter and mapping versions define the scope, while limits and worker count may change between attempts. VASA has no snapshot token, so resuming is best effort.
- **Exit codes.** A full success exits 0, and the next run then starts a fresh pass. Failures exit 1 and keep the progress already committed.
- **Checkpoints.** Each tile, detail response and history page commits together with its checkpoint. Transient errors are retried 5 times with backoff, capped at 20 s. Pagination is limited to 10,000 pages.
- **Cleanup.** Only a full successful pass cleans up. In one final transaction it does the following:
  - removes bins that were not seen and whose stored coordinates lie inside `--bbox`, together with their history;
  - removes sites left empty;
  - recalculates the coordinate means of the remaining sites.

  Bins outside the bounds survive cleanup, and so do manual bins (NULL external ID). A narrower `--bbox` refreshes only that area, as a separate scope.
- **Locking.** A PostgreSQL advisory lock rejects a second importer that runs at the same time.

## Settings

`DATABASE_URL`, `VASA_TILE_URL_TEMPLATE`, `VASA_BIN_URL_TEMPLATE`, `VASA_HISTORY_URL_TEMPLATE` and `BIN_SYNC_HTTP_TIMEOUT_SECONDS` are described in [configuration](../development.md#configuration). The HTTP timeout is per socket wait, not a whole-run deadline. Database connections time out after 10 s, and importer statements after 30 s, with a 5 s lock timeout.
