# Data model

The tables and what their data means. Columns and constraints are defined in [`backend/app/infrastructure/models.py`](../backend/app/infrastructure/models.py), and the schema is managed by Alembic (`backend/alembic/`).

| Table | One row per | Kind | Filled by |
|---|---|---|---|
| `sites` | Address-grouped collection site | Observed (VASA) or manual | [Import](data/import.md), [bin sync](data/bin-sync.md), admin UI |
| `bins` | Physical container | Observed (VASA) or manual | Same as `sites` |
| `bin_hist` | Service attempt of a bin | Observed | Import, bin sync |
| `bin_schedule` | Planned collection date of a bin | VASA plan, current month | [Schedule sync](data/bin-schedule-sync.md), import |
| `resident_requests` | Emptying request from the public resident page | Observed signal | Resident page |
| `population_cells` | Population-density polygon | Source data | [Bin population](data/bin-population.md) |
| `bin_population` | Bin | Estimated | Bin population |
| `bin_days` | Bin and calendar day | Copied, estimated and synthetic | [Bin-day calendar](data/bin-days.md) ([columns](data/bin-days-columns.md)) |
| `collection_stops`, `stop_bins` | Plan stop (date, carrier, site), and its bins | Mock prediction | [Collection plan](data/collection-plan.md) |
| `district_boundaries` | District (seniūnija) polygon | Source data | [District boundaries](data/district-boundaries.md), import |
| `service_zones` | Service-zone polygon | Source data | [Service zones](data/service-zones.md), import |
| `trucks` | Truck | Manual | Admin UI |
| `landfills` | Waste facility | Seeded by a migration | Migration |
| `vasa_import_runs`, `vasa_import_progress` | Bin sync pass, and its checkpoints | Internal | Bin sync |

## Sites and bins

- **Grouping.** A site groups the bins that share a registered street and house number (trimmed, whitespace-collapsed, case-folded). `site_key` is `address:<normalized>`, or `unknown:<external_id>` for a bin without an address. A site created in the admin UI gets `manual:<UUID>`, so it stays separate even when the address matches. Distance and client addresses do not affect grouping.
- **Location.** An imported site's coordinates are the arithmetic mean of all its bins, not a surveyed entrance. A manual site keeps the location the user selected.
- **Address fields.** On site details, the address fields come from the bin with the lowest ID. A NULL is never filled in from another bin.
- **Identity.** `bins.external_id` is the VASA ID and is unique when present. Manual bins have NULL; bin sync never sends or deletes them.
- **Attributes.** Only site, waste type and coordinates are required on a bin. Geographic and descriptive fields are free text, kept with the source's formatting (house numbers and postal codes too).
- **`client_count`** is the number of address-list entries, not residents. An empty list gives 0; a missing or malformed list gives NULL.
- **`capacity_m3`** stores the source value unchanged. That it is in cubic metres is an **unverified assumption**.
- **Waste types** keep their English source values (`Mixed municipal waste`, `Paper/plastic waste`, `Glass waste`). The UI translates them.

## Service history (`bin_hist`)

- Each row is an actual attempt, including failures, with a naive local timestamp and the source reason, which can be an empty string.
- `fill_level` is NULL or 0–3. Imported attempts have NULL.
- A row is unique by `(bin_id, date, was_serviced)`, so distinct attempts that share all three values collapse into one.
- Nothing is inferred: no truck, route, duration or fill.

## Deletion

- Deleting a site deletes its bins. Deleting a bin deletes its history, schedule, population allocation, bin days, resident requests and plan entries.
- Deleting a site's last bin in the admin UI also deletes the site.
- Deleting a truck is a soft delete: `deleted` becomes true and `available` false, and the row stays.

## Trucks and landfills

- `trucks.max_volume_m3` is a positive waste volume in m³ and can be fractional. `waste_carrier` is free text. The UI offers four carriers, but the database accepts any.
- `trucks.landfill_id` references `landfills` and can be NULL. A referenced landfill cannot be deleted.
- `landfills` is seeded from `vilnius_waste_facilities.geojson`, which is embedded in a migration, so no file or network is needed. Only `id` and `name` are required. Status, coordinate quality and verification dates are as supplied in the source file, not independently verified.

## Resident requests

`resident_requests` stores only the bin and a timestamp, in Europe/Vilnius local time, without a time zone. A request is a raw signal: it is not a verified fill level and does not create a service event. Every submission adds a row.
