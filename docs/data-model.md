# Data model

The tables and what their data means. Columns and constraints are defined in [`backend/app/infrastructure/models.py`](../backend/app/infrastructure/models.py), and the schema is managed by Alembic (`backend/alembic/`).

<!-- agent-runtime:start -->

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
| `collection_stops`, `stop_bins` | Plan stop (date, carrier, site), and its bins | Model prediction | [Collection plan](data/collection-plan.md) |
| `route_plans`, `route_trucks`, `route_trips`, `route_stops` | Route plan (date, carrier), its trucks, their trips, and the stops of a trip | Optimised from predictions; distances estimated | [Route plan](data/route-plan.md) |
| `district_boundaries` | District (seniūnija) polygon | Source data | [District boundaries](data/district-boundaries.md), import |
| `service_zones` | Service-zone polygon | Source data | [Service zones](data/service-zones.md), import |
| `trucks` | Truck | Manual | Admin UI |
| `landfills` | Waste facility | Seeded by a migration | Migration |
| `vasa_import_runs`, `vasa_import_progress` | Bin sync pass, and its checkpoints | Internal | Bin sync |

## Sites and bins

- **Grouping.** A site groups the bins that share a registered street and house number (trimmed, whitespace-collapsed, case-folded). `site_key` is `address:<normalized>`, or `unknown:<external_id>` for a bin without an address. A site created in the admin UI gets `manual:<UUID>`, so it stays separate even when the address matches. Distance and client addresses do not affect grouping.
- **Location.** An imported site's coordinates are the arithmetic mean of all its bins, not a surveyed entrance. A manual site keeps the location the user selected.
<!-- agent-runtime:end -->

- **Address fields.** On site details, the address fields come from the bin with the lowest ID. A NULL is never filled in from another bin.
<!-- agent-runtime:start -->

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

<!-- agent-runtime:end -->

## Deletion

- Deleting a site deletes its bins. Deleting a bin deletes its history, schedule, population allocation, bin days, resident requests and plan entries.
- Deleting a site's last bin in the admin UI also deletes the site.
- Deleting a truck is a soft delete: `deleted` becomes true and `available` false, and the row stays.

<!-- agent-runtime:start -->

## Trucks and landfills

- `trucks.max_volume_m3` is a positive waste volume in m³ and can be fractional. `waste_carrier` is free text.
- `trucks.landfill_id` references `landfills` and can be NULL. A referenced landfill cannot be deleted.
- `landfills` is seeded from `vilnius_waste_facilities.geojson`, which is embedded in a migration, so no file or network is needed. Only `id` and `name` are required. Status, coordinate quality and verification dates are as supplied in the source file, not independently verified.

## Resident requests

`resident_requests` stores only the bin and a timestamp, in Europe/Vilnius local time, without a time zone. A request is a raw signal: it is not a verified fill level and does not create a service event. Every submission adds a row. Residents use these requests to ask for emptying before the scheduled truck arrival. A successful read with zero requests means no such requests were recorded for the queried bins and period, including when the entire table is empty; it does not mean the dataset is unavailable. Failed reads remain distinct from zero requests.


## Analytical identities and relationships

| Table | Key and relationships | Analytical columns and meanings |
|---|---|---|
| `sites` | Internal `id`; `bins.site_id` points here | `site_key`, address and own mean coordinates; location scope differs from selected members |
| `bins` | Internal `id`, nullable unique VASA `external_id`; `site_id` → sites | Own latitude/longitude, waste type, capacity, current carrier/object group, nullable address-list count; current attribution qualifies older events |
| `bin_hist` | Internal `id`; `bin_id` → bins | `date`, successful `was_serviced`, nullable/empty reason, nullable 0–3 observed fill; latest attempt and latest successful baseline differ |
| `resident_requests` | Internal `id`; `bin_id` → bins | Every timestamped submission remains separate, including repeated submissions; local naive wall-clock time |
| `bin_schedule` | Internal `id`, unique `(bin_id,date)`; bin → bins | Stored calendar-day plan, potentially future; no completed-service or missed-service proof |
| `population_cells` | Source `OBJECTID` as `id` | Rings with holes, envelope, density/ha, suppression, area/ha and full-polygon resident estimate; NULL density plus suppression false makes stored zero unavailable |
| `bin_population` | `bin_id` primary key → bins; nullable cell → population_cells | Stored `resident_factor`: nearest residential point allocation per waste stream, split by capacity; current coordinates may differ from stored cell attribution |
| `bin_days` | `(bin_id,date)`; bin → bins | Copied registry/estimated allocation snapshots and synthetic statuses, not observed history; detailed column semantics in bin-day dictionary |
| `collection_stops` | Internal `id`, unique date/carrier/site; site → sites | Planning-time whole-stop volume/predicted fill snapshots include all stop members; nullable carrier is an unassigned group |
| `stop_bins` | `(stop_id,bin_id)`; stop → collection_stops, bin → bins | Stored model-predicted `predicted_fill` 0–4 and `due`; selected entry subtotal differs from whole-stop snapshot; no query generates a plan |
| `route_plans` | Internal `id`, unique date/carrier | Parameters, summaries (optimised, baseline, saving) and unserved stops as JSON; no foreign keys to other tables |
| `route_trucks`, `route_trips`, `route_stops` | Truck → plan, trip → truck, stop `(trip_id,seq)` → trip; all cascade | Copies of truck, landfill and stop data at planning time (no references to `trucks`, `landfills`, `sites`), so later changes to those do not alter a stored plan; distances are straight-line estimates |
| `district_boundaries` | Internal `id`, unique district name/source ID | Source Polygon geometry/name; holes/boundaries matter, stored bin district text is separate |
| `service_zones` | Internal `id`, unique zone number | Source Polygon geometry/name/number; no observed fleet or historical service-zone attribution |
| `landfills` | Internal `id`, nullable unique source ID | Nullable location, quality, operator/role/status, waste streams and verification/source fields; geometric proximity is not a road route |
| `trucks` | Internal `id`; nullable landfill → landfills | Current carrier, positive volume, available/deleted state; deleted is retired; global registry has no geographic fleet/service history |

Rates use recorded events within one scope/window. Zero denominators and all-NULL
statistics are unavailable. PostgreSQL numeric NaN/Infinity capacity values are
invalid evidence and excluded from known capacity. Population suppression
assumptions are embedded in stored resident estimates; allocations across waste
streams cannot be added as unique residents. No route, service duration or
historical truck relationship is stored.

<!-- agent-runtime:end -->
`resident_requests` stores only the bin and a timestamp, in Europe/Vilnius local time, without a time zone. A request is a raw signal: it is not a verified fill level and does not create a service event. Every submission adds a row.

## Offline data and models

The [fill/QR generator](data/fill-qr.md) produces an enriched local CSV with
synthetic labels and QR counts. The [fill predictor](data/fill-prediction.md)
uses that fixed source and writes its models, analysis and standalone delivery
under the configured run directory. These are files rather than database tables;
the collection plan runs the exported model as described in its own guide.
