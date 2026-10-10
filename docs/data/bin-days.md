# Bin-day calendar

`bin_days` holds one row per bin per calendar day and is the input for the synthetic fill-level generator. It is built from `bins`, the planned dates in `bin_schedule`, `bin_population`, Lithuanian public holidays and the simulation parameters. It does not read `bin_hist` and contains no observed outcomes or fill levels. Every column is described in [`bin_days` columns](bin-days-columns.md), and behaviour is specified in [`bin-day-calendar`](../../openspec/specs/bin-day-calendar/spec.md).

Before building it, [import](import.md) the collection data (including `bin_schedule`) and run [bin population](bin-population.md). Then run:

```bash
docker compose exec backend uv run python -m app.interfaces.bin_days --start 2026-09-09 --end 2026-10-09
```

| Option | Default |
|---|---|
| `--start`, `--end` | Required. Inclusive range of at most 5 years (1,827 days). |
| `--seed` | 42 |
| `--p-first`, `--p-retry1`, `--p-retry2` | 0.028, 0.40, 0.70. Failure probability of the first attempt and of each retry, in [0, 1]. |
| `--holiday-factor` | 2. Multiplies the failure probability on holidays (at least 0). |

- Each run replaces the whole table in one transaction, so a failure leaves it unchanged.
- It exits 0 on success and 1 on invalid arguments or failure. The summary prints the seed, the parameters and the number of rows per status.
- The rebuild refuses to run while an eligible bin has no population allocation, for example after a sync adds bins.
- It runs in plain Python. 31 days × about 21,700 bins (about 670k rows) take about 20 s, and one year (about 7.9M rows) takes about 4 minutes.

## Which bins

A bin gets a row for every date when it has a `sub_district` and at least one stored planned date. All other bins are skipped and counted in the summary.

## Assumptions

- Bin attributes are a snapshot taken at rebuild time and applied to every date. Bins have no install or removal dates, so each included bin exists on every day.
- The stored schedule, which is the latest monthly snapshot, repeats over the whole range. Its cycle is the shortest of 1, 7, 14, 21 or 28 days that reproduces the stored dates. A single stored date, or irregular dates, mean every 28 days.
- A collection is attempted on every planned day. A failed attempt is retried the next day, and once more the day after. A planned day cancels a pending retry.
- The failure probabilities are assumptions, not fitted values. For reference, 3.4% of `bin_hist` events are non-serviced (including reasons that are not carrier failures), and 23% of next-day events after a non-service are non-serviced too.
- Holidays do not move collections. They multiply the failure probability by the factor, capped at 0.95.
- With the defaults, a planned collection is finally missed with probability 0.028 × 0.40 × 0.70 ≈ 0.78%. The observed share is higher, about 1.8% overall, because holidays raise it and a daily bin has no retry.
- The simulation starts 35 days before `--start`, so the first rows have complete 28-day features. Changing `--start` therefore changes the draws.
- Each bin has its own random stream, seeded by `seed` and `bin_id`, so the same arguments give identical output regardless of other bins.
- ISO weeks near New Year can belong to the neighbouring year (2027-01-01 is week 53).

## Keeping it in sync

A deleted bin loses its rows. An [import](import.md) of `bins` empties the table. Refreshing `bin_schedule` has no effect until the next rebuild.

The generator reads `bin_hist` itself. When a bin has several events on one day, it uses the last one, and it resets fill on `collected` and `retry_collected`.
