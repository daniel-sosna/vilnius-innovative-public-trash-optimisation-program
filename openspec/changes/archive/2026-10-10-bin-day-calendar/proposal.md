# Proposal

## Why

A future generator will add synthetic fill levels to historical data. It needs one row per bin per day, carrying that day's calendar features and the bin's attributes. Today the attributes live in `bins` and every consumer would rebuild the bin x day grid on its own. A shared, stored grid gives the generator, and later the prediction work, one consistent contract.

## What Changes

- New table `bin_days`: one row per bin per calendar day, containing:
  - `date`
  - `day_of_week`: ISO, 1 to 7, Monday is 1
  - `week_of_year`: ISO week
  - `month`
  - `season`: meteorological, 1 to 4
  - `bin_id`, `site_id`, `waste_type`, `capacity_m3`, `sub_district`, `object_group`, copied from `bins`
- New CLI `python -m app.interfaces.bin_days --start YYYY-MM-DD --end YYYY-MM-DD`. It replaces the whole table with the grid for that inclusive date range, all or nothing. Ranges longer than five years (1,827 days) are rejected.
- Bins with a NULL `sub_district` are excluded (currently 147 of 21,951). Bins with a NULL `object_group` are kept, with NULL in that column.
- Collection CSV imports that replace `bins` also empty `bin_days` in the same transaction. A developer then rebuilds it with the CLI. Without this, the new reference to `bins` would make the standard import fail. Bins removed by a VASA sync cleanup lose their `bin_days` rows.
- New Alembic migration that creates `bin_days`.

The table is built only from `bins` and the requested dates. It reads no service history (`bin_hist`), and it holds no observed outcomes, lagged collection counts or fill levels. The generator derives those from `bin_hist` itself.

## Capabilities

### New Capabilities
- `bin-day-calendar`: the stored bin x day grid with calendar features and bin attributes, and the explicit command that rebuilds it.

### Modified Capabilities
- `table-csv-import`: a collection import that replaces `bins` also empties the derived `bin_days` table. The "tables without a file are never emptied" rule gains this exception.

## Impact

- Backend: new ORM model, migration `0005`, and CLI package `app/interfaces/bin_days/`. A small change to `app/interfaces/table_import/cli.py` (truncation set).
- Database: a new table of about 21.8k bins x N days, about 676k rows for the current 31-day period. No existing table changes.
- Docs: a README section and a repeatable verification doc in `docs/`.
- Consumers: the future synthetic fill-level generator (data/ML) reads `bin_days`. No API or frontend changes.

**Assumptions and uncertainties**
- Season numbers: 1 is winter (Dec–Feb), 2 spring (Mar–May), 3 summer (Jun–Aug), 4 autumn (Sep–Nov).
- Every included bin is assumed to exist on every day of the range, because bins have no installation or removal dates. Attributes are a snapshot from when the table was built, not historical values.
- The operator chooses the date range. It is not taken from `bin_hist`. The expected first use is the current history period, 2026-09-09 to 2026-10-09.
- ISO week numbers near New Year can belong to the neighbouring year (for example, 2027-01-01 is in ISO week 53). No ISO year column is added.
