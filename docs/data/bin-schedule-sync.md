# Collection schedules

`bin_schedule` holds VASA's planned collection dates, one row per bin and date. They are VASA's plan, not observed service. Behaviour is specified in [`collection-schedules`](../../openspec/specs/collection-schedules/spec.md).

Load the collection data first ([import](import.md)), then run:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_schedule_sync --max-bins 20   # trial
docker compose exec backend uv run python -m app.interfaces.bin_schedule_sync                 # all bins
```

| Option | Default |
|---|---|
| `--workers N` | 4 concurrent requests |
| `--max-bins N` | 0 (all). Process only the first N bins by ID. |

- **Exit codes.** 0 when every bin succeeded. 1 on any failed bin, invalid arguments or configuration, or no stored bins. 2 for a `--max-bins` run without failures.
- **Snapshot.** VASA returns only the current month. Each successful response replaces that bin's dates, so the table holds the latest month fetched. A failed bin keeps its previous dates, and the summary lists the external IDs of the first 20 failures. Re-run at the start of each month. Consumers should filter on `date >= today`.
- **Empty lists.** VASA returns an empty list both for a bin without a plan and for an unknown ID. The summary reports how many were empty, so a sudden jump points to a source problem.
- **Manual bins** have no external ID. They are skipped before the limit is applied.
- **Duration.** A full run takes about 13 minutes for about 22k bins with 4 workers.
- The source URL is `VASA_SCHEDULE_URL_TEMPLATE` (see [configuration](../development.md#configuration)).
