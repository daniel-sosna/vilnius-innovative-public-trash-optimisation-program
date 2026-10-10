# Import table CSV exports

`table_import` loads tables from CSV exports that a teammate shares. This is how to get collection data for development. Do not use [bin sync](bin-sync.md) for it: a full pass takes hours.

```bash
docker compose exec backend uv run python -m app.interfaces.table_import
```

`--dir PATH` reads another folder. The default is the [data directory](../development.md#data-directory), which is `VIPTOP_DATA_DIR` or `backend/data/`.

## Files

- Name each file `<table>_<digits>.csv`, e.g. `bins_202610091935.csv`. If one table has several files, the highest number wins. Other `.csv` files are ignored with a warning.
- The minimum for development is `sites_*.csv`, `bins_*.csv` and `bin_hist_*.csv`. `bin_schedule_*.csv` and `resident_requests_*.csv` are optional.
- Export settings are UTF-8, a header row, unquoted `NULL` for null (as DBeaver writes it) and quoted text. Export from a database at the same migration as yours.

## What an import replaces

- Only tables that have a file are emptied and reloaded, keeping their IDs. Other tables, such as `trucks`, are untouched.
- A table referenced by a table without a file is rejected, e.g. `sites` alone.
- Importing `sites`, `bins` or `bin_hist` clears the saved [bin sync](bin-sync.md) progress, so the next sync starts a fresh pass.
- Importing `bins` also empties the tables derived from bins. Refill them as shown in the table below.

| Emptied when `bins` is imported | Unless a file is present | Refill with |
|---|---|---|
| `bin_population` (`population_cells` is kept) | – | [bin population](bin-population.md) |
| `bin_days` | – | [bin-day calendar](bin-days.md), after bin population |
| `collection_stops`, `stop_bins` | – | [collection plan](collection-plan.md) |
| `bin_schedule` | `bin_schedule_*.csv` | [schedule sync](bin-schedule-sync.md) |
| `resident_requests` | `resident_requests_*.csv` | Cannot be refetched |

An import without `bins` leaves all of these unchanged. The output names every table it emptied.

## Safety and exit codes

- Everything runs in one transaction, so a failure leaves the database unchanged. **The current contents of the imported tables are discarded.**
- The command exits 0 on success. It exits 1 when there is nothing to import, the directory is missing or the import fails.
