# `bin_days` columns

Data dictionary for `bin_days`, the bin-day calendar that feeds the synthetic fill-level
generator. How to build it, its options and its modelling assumptions are in
[Bin-day calendar](bin-days.md). The exact behaviour is specified
in [`openspec/specs/bin-day-calendar/spec.md`](../../openspec/specs/bin-day-calendar/spec.md),
and that spec wins if the two ever disagree.

- **Grain:** one row per eligible bin per date from `--start` to `--end`, inclusive. A bin is
  eligible when it has a `sub_district` and at least one stored planned date in `bin_schedule`.
- **Primary key:** `(bin_id, date)`.
- **Deletes:** `bin_id` references `bins.id` with `ON DELETE CASCADE`, so deleting a bin
  deletes its rows. A CSV import that replaces `bins` empties the whole table.
- **Rebuilds:** every rebuild replaces all rows. Copied values are a snapshot from rebuild
  time, the same on every date.

Kinds used below:

| Kind | Meaning |
|---|---|
| key | Identifies the row |
| calendar | Computed from the row's date |
| registry snapshot | Copied from `bins` at rebuild time; current registry values, not history |
| estimated | Derived from population data, copied from `bin_population`; not observed |
| synthetic | Simulated from the schedule with random failures; not observed |

## Summary

| Column | SQL type | Null | Kind |
|---|---|---|---|
| `bin_id` | `BIGINT` | no | key, registry snapshot |
| `date` | `DATE` | no | key |
| `day_of_week` | `SMALLINT` | no | calendar |
| `week_of_year` | `SMALLINT` | no | calendar |
| `month` | `SMALLINT` | no | calendar |
| `season` | `SMALLINT` | no | calendar |
| `site_id` | `BIGINT` | no | registry snapshot |
| `waste_type` | `TEXT` | no | registry snapshot |
| `capacity_m3` | `NUMERIC` | yes | registry snapshot |
| `sub_district` | `TEXT` | no | registry snapshot |
| `object_group` | `TEXT` | yes | registry snapshot |
| `population_cell_id` | `INTEGER` | yes | estimated |
| `resident_factor` | `DOUBLE PRECISION` | no | estimated |
| `collection_status` | `TEXT` | no | synthetic |
| `holidays_since_last_collection` | `SMALLINT` | no | synthetic |
| `collections_last_28d` | `SMALLINT` | no | synthetic |
| `missed_collections_28d` | `SMALLINT` | no | synthetic |

Example counts below come from the exports `bins_202610091935.csv` and
`bin_schedule_202610100342.csv`, with the calendar built for 2026-09-09..2026-10-09 and
default parameters (21,695 bins, 672,545 rows).

## Keys

### `bin_id`

Internal ID of the physical bin (`bins.id`, a generated identity, not the VASA
`external_id`). Join to `bins` for anything not copied here, such as coordinates or address.

### `date`

The calendar day the row describes. Every eligible bin has a row on every date of the range,
whatever its service history.

## Calendar

### `day_of_week`

ISO weekday: 1 = Monday … 7 = Sunday. Range enforced by a check constraint.

### `week_of_year`

ISO week number, 1–53 (enforced). Near New Year it can belong to the neighbouring year:
2027-01-01 is week 53.

### `month`

Calendar month, 1–12 (enforced).

### `season`

Meteorological season, 1–4 (enforced): 1 winter (Dec–Feb), 2 spring (Mar–May), 3 summer
(Jun–Aug), 4 autumn (Sep–Nov).

## Registry snapshot

These come from the bin's row in `bins` when the rebuild ran. They are not historical: a
later change in `bins` shows up only after the next rebuild, and then on every date.

### `site_id`

The collection site (`sites.id`) the bin belongs to. A site groups the bins at one
registered street address and house number, so several bins can share a site.
The current calendar covers 9,388 sites.

### `waste_type`

Waste stream the bin collects. The database does not restrict the values. Values in the
current export:

| Value | Bins in `bins` | Bins in calendar |
|---|---|---|
| `Mixed municipal waste` | 14,958 | 14,848 |
| `Paper/plastic waste` | 4,239 | 4,186 |
| `Glass waste` | 2,754 | 2,661 |

### `capacity_m3`

Bin volume as stored in the source, unchanged. The unit is assumed to be m³ but is **not
verified**. NULL means unknown (no eligible bins in the current calendar). Common values:
1.1 (8,607 bins), 0.24 (4,137), 5 (2,969), 3 (1,558), 0.12 (1,546). Two eligible bins have 0.

### `sub_district`

Seniūnija (eldership, Vilnius sub-district) of the bin, for example `Panerių sen.`. The
calendar covers 36. Never NULL here, because bins without one are excluded.

### `object_group`

Client category of the bin's users (the type of property it serves). The database does not
restrict the values. It also decides whether the bin counts as residential for
`resident_factor`; residential groups are marked with *. Values in the current export:

| Value | Meaning | Bins in `bins` | Bins in calendar |
|---|---|---|---|
| `Komercinė paskirtis` | Commercial premises | 8,540 | 8,481 |
| `Daugiabučiai namai` * | Apartment buildings | 8,476 | 8,410 |
| `Dvibučiai` * | Two-family houses | 2,779 | 2,682 |
| `Viešosios vietos` | Public places | 519 | 519 |
| NULL | Unknown | 476 | 455 |
| `Juridiniai asmenys` | Legal entities | 411 | 401 |
| `Sodų/garažų bendrijos` * | Garden/garage communities | 309 | 308 |
| `Viešosios įstaigos` | Public institutions | 177 | 176 |
| `Sodų bendrijos` * | Garden communities | 156 | 155 |
| `Daugiabučių/garažų bendrijos` * | Apartment/garage associations | 95 | 95 |
| `Garažų bendrijos` | Garage communities | 13 | 13 |

## Estimated population

Copied from `bin_population`, built by `python -m app.interfaces.bin_population` (see [Bin population](bin-population.md)). The
calendar rebuild refuses to run while an eligible bin has no allocation.

### `population_cell_id`

ID of the population-density polygon (`population_cells.id`, the source `OBJECTID`) that
contains the bin. NULL when the bin lies in no polygon (none in the current calendar). This
is only the bin's location; the residents it serves can come from other polygons.

### `resident_factor`

**Estimated** number of residents whose waste goes to this bin. It is not observed. Each
polygon's residents are assigned to the nearest residential collection point of each waste
type and split among that point's bins by capacity. It is 0 for non-residential bins (other
object groups, or capacity 0), which is 12,366 bins in the current calendar; the generator
supplies their baseline. Among the other bins: median 85, p90 449, max about 7,600.

## Synthetic collections

Simulated by the rebuild from the repeating stored schedule. On each planned day a
collection is attempted, failures are retried on up to two following days, and failure is
random with the `--p-first`, `--p-retry1`, `--p-retry2` and `--holiday-factor` probabilities.
The draws depend on `--seed`, `bin_id` and the arguments. The simulation starts 35 days
before `--start`, so the look-back columns are complete on the first row. None of these
columns are read from `bin_hist`.

### `collection_status`

Outcome of this day's own attempt. The check constraint allows exactly these values:

| Value | Meaning | Rows in current calendar |
|---|---|---|
| `none` | No attempt on this day | 463,746 |
| `collected` | First attempt succeeded | 198,845 |
| `retry_collected` | A retry succeeded | 2,254 |
| `failed` | Attempt failed and a retry follows the next day | 4,143 |
| `missed` | Attempt failed and no retry follows; the planned collection is finally missed | 3,557 |

`collected` and `retry_collected` are successful collections: the generator resets fill on
them.

### `holidays_since_last_collection`

Lithuanian public holidays from the day after the bin's latest successful collection
**before** this date through the day before this date. Today's own collection is not
counted. If the bin has no successful collection since the simulation start, counting
starts there. 0 or more (enforced). Holidays include Easter Sunday and Monday, Mother's Day
and Father's Day.

### `collections_last_28d`

Days with a successful collection (`collected` or `retry_collected`) from date − 28 through
date − 1. Today is not counted. 0–28 (enforced). A weekly bin without failures has 4.

### `missed_collections_28d`

Days with status `missed` from date − 28 through date − 1. Today is not counted. 0–28
(enforced). A planned collection counts once, on the day its last attempt failed, not on
the planned day. Collections that succeeded on a retry do not count.
