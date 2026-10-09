# bin-synchronization Specification

## Purpose

Maintain VipTop's collection-site registry from the Vilnius public GIS source while preserving operational history and allowing the backend to operate with its last stored data when synchronization fails.

Source: [Vilnius installed collection sites, layer 29](https://opencity.idvilnius.lt/gis/rest/services/Miesto_tvark/Miesto_tvarkymas_public/MapServer/29).

## Requirements

### Requirement: Skip unusable external features
Discovery SHALL ignore recognized aggregate features and records excluded by the import filters. Unusable eligible physical-bin identities or geometry SHALL be logged, SHALL NOT overwrite existing bins, and SHALL prevent a pass from claiming complete coverage or performing cleanup. Valid records SHALL still be committed incrementally.

#### Scenario: Skip a feature with a missing identifier
- **WHEN** an apparently physical eligible feature has no usable external ID while another is valid
- **THEN** its issue is reported, the valid bin is eligible for import, and the pass remains incomplete

#### Scenario: Leave an existing site unchanged after invalid geometry
- **WHEN** a feature for a stored Bin has unusable coordinates
- **THEN** its existing Bin values remain unchanged and missing-bin removal is disabled for that pass

### Requirement: Represent missing addresses explicitly
An otherwise usable bin with a missing registered address SHALL receive its own deterministic fallback Site using `unknown:<external_id>` and a readable fallback label. Missing addresses SHALL be reported without discarding the bin or grouping unrelated unknown addresses.

#### Scenario: Insert a site without a source address
- **WHEN** bin 123 has neither street nor house number
- **THEN** it belongs to the site keyed `unknown:123`

#### Scenario: Clear a previously known address when the source omits it
- **WHEN** a previously addressed bin now has no registered address
- **THEN** it moves to its isolated fallback site while keeping its bin ID and history
- **AND** the affected old site is recalculated or removed if empty

### Requirement: Upsert by external identity
Import SHALL upsert physical bins by VASA external identity, retain generated Bin IDs, and update their mapped source attributes and Site membership. Repeated tile observations or identical imports SHALL NOT produce duplicate bins or history. Import SHALL NOT change truck records.

#### Scenario: Insert a new site
- **WHEN** a valid bin references a normalized registered address not yet stored
- **THEN** its site and bin become persistent without duplicate site identities

#### Scenario: Update an existing site's attributes
- **WHEN** a known bin's registered address or coordinates change
- **THEN** its identity and history remain and affected site memberships and means are updated

#### Scenario: Repeat the same import
- **WHEN** identical source data is refreshed
- **THEN** existing site, bin, and history identities are reused

#### Scenario: Update metadata on an existing site
- **WHEN** a known physical bin's inventory, geographical text attributes, group, carrier, capacity, or client count changes
- **THEN** its source attributes are updated without replacing the bin

#### Scenario: Clear metadata when the source no longer supplies it
- **WHEN** a usable bin no longer has an optional source attribute
- **THEN** that attribute becomes NULL without affecting its history or required identity

### Requirement: Import only on explicit invocation
VASA importing SHALL run only when an operator invokes the command. Application startup, restart, development reload, migrations, deployment, and idle runtime SHALL NOT fetch VASA data or schedule imports. The server SHALL operate with empty or existing collection storage independently of source availability or an independently launched importer.

#### Scenario: Start before populating bins
- **WHEN** the backend starts after schema preparation with empty bins
- **THEN** it serves requests and imports nothing until explicit invocation

#### Scenario: Restart or reload without refreshing the registry
- **WHEN** the backend restarts or reloads
- **THEN** it makes no source requests and performs no import cleanup

#### Scenario: Remain idle without automatic imports
- **WHEN** the backend runs without an operator launching the command
- **THEN** it performs no import or refresh

#### Scenario: Start while the source is unavailable
- **WHEN** schema preparation succeeds but VASA is unreachable
- **THEN** the backend serves without trying the source or waiting for its timeout

#### Scenario: Populate bins after application setup
- **WHEN** schema preparation is complete and the command is explicitly invoked
- **THEN** the importer fetches and persists VASA data under the manual import contract

#### Scenario: Keep import resource ownership independent
- **WHEN** backend shutdown occurs during a separately launched import
- **THEN** shutdown does not wait for the importer, which owns its own resource cleanup

### Requirement: Obtain synchronization settings from configuration
Database access SHALL retain the existing configuration conventions. VASA tile/detail/history endpoints and positive finite request timeout SHALL be configurable through root dotenv or environment, with environment precedence. Obsolete GIS settings SHALL not be required. No interval setting SHALL be used.

#### Scenario: Override the timeout in the environment
- **WHEN** dotenv specifies 30 seconds and the environment specifies 5 seconds
- **THEN** requests use 5 seconds

#### Scenario: Configure importing without an interval
- **WHEN** valid VASA and database settings are provided without an interval
- **THEN** configuration loads without scheduling an import

#### Scenario: Run entirely from deployment environment variables
- **WHEN** configuration exists only in process environment
- **THEN** the standalone image can migrate and import without a dotenv file

#### Scenario: Report missing configuration before operating
- **WHEN** required import configuration is unavailable
- **THEN** the command exits nonzero before source requests or import writes without disclosing credentials

#### Scenario: Reject an invalid timeout
- **WHEN** request timeout is zero, negative, or nonfinite
- **THEN** configuration is rejected before import

### Requirement: Load the shared dotenv file for native execution
Native backend entry points SHALL load the repository-root `.env` independently of the working directory and use the same settings contract for migration and explicit import. Unrelated keys in the shared file SHALL NOT make backend settings invalid. Configuration diagnostics SHALL NOT disclose the database connection's credentials.

#### Scenario: Invoke native commands from the backend directory
- **WHEN** valid settings are in the repository-root `.env` and native migration or import is invoked from `backend/`
- **THEN** the command obtains those settings without requiring the synchronization variables to be exported manually

#### Scenario: Read a shared file with PostgreSQL container settings
- **WHEN** the shared `.env` includes `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` alongside backend settings
- **THEN** those unrelated keys do not cause an extra-field validation failure

#### Scenario: Override a container connection for native use
- **WHEN** `.env` contains a connection using hostname `db` and the native process environment supplies a valid localhost connection
- **THEN** native commands use the environment connection while obtaining other settings from `.env`

### Requirement: Extract bin geographical metadata
Import SHALL extract `district`, `region`, `sub_district`, `city`, `street`, `house_number`, `postal_code`, and `territory_type` into the matching nullable Bin columns. When requested attributes are absent from tile properties, import SHALL fetch the bin detail endpoint using its VASA external ID. Missing or null values in a successful authoritative response SHALL remain NULL.

#### Scenario: Resolve metadata omitted by map tiles
- **WHEN** a discovered bin's tile properties omit any requested geographical field
- **THEN** import retrieves `/vasa-api/api/v1/dumpsters/{external_id}` and maps its bin-level attributes before counting that bin's discovery work as complete
- **AND** coordinates still come from tile geometry

#### Scenario: Preserve the supplied detail-response meanings
- **WHEN** the supplied response for bin 135353 is imported with valid tile coordinates
- **THEN** its Bin stores the eight geographical values, client_count 2, and unconverted capacity 1.1
- **AND** its Site address is `Didlaukio g. 53` with key `address:didlaukio g. 53`

#### Scenario: Resume required detail work after failure
- **WHEN** a required detail request fails after retries or its transaction fails
- **THEN** the pass remains incomplete, prior committed progress survives, and cleanup does not occur
- **AND** matching reruns resume unfinished detail work without duplicate bins or sites

#### Scenario: Refresh previously resolved details
- **WHEN** a full pass has completed and the next invocation starts a refresh
- **THEN** required detail responses are fetched again instead of reused from the completed pass

#### Scenario: Exclude container service snapshots
- **WHEN** a tile or detail response supplies current servicing status, service date, failure reason, or next service date
- **THEN** these values are not stored on bins and do not substitute for history-endpoint events

### Requirement: VASA eligibility and geographical limits
Import SHALL include only `Mixed municipal waste`, `Paper/plastic waste`, and `Glass waste`, exclude whitespace/case-normalized `Individualios valdos`, and retain the supplied Vilnius city filter. Only points inside the configured bounding box SHALL be imported. Default bounds SHALL be west 24.98, south 54.55, east 25.52, north 54.85.

#### Scenario: Exclude private holdings despite case and spacing
- **WHEN** a bin has group `  INDIVIDUALIOS   VALDOS `
- **THEN** it is excluded even if its waste type is allowed

#### Scenario: Exclude neighboring tile data outside bounds
- **WHEN** a tile contains a point outside the configured bounding box
- **THEN** that point is not imported

#### Scenario: Preserve relevant city filtering
- **WHEN** a feature has a nonempty city value that does not contain `vilniaus` case-insensitively
- **THEN** it is excluded; missing city alone does not exclude an otherwise eligible bin

### Requirement: Source count and capacity meanings
Client count SHALL be the number of entries in a valid `client_addresses` list, accepting a list or JSON-encoded list. Missing or malformed values SHALL produce NULL; an empty valid list SHALL produce 0. Source `volume` SHALL be stored without conversion, and cubic metres SHALL be documented as an unverified assumption.

#### Scenario: Parse served addresses rather than residents
- **WHEN** `client_addresses` is a list or JSON-encoded list of three entries
- **THEN** client count is 3 without estimating residents

#### Scenario: Distinguish zero from unknown
- **WHEN** one bin has `[]` and another has a malformed client-address value
- **THEN** their counts are 0 and NULL respectively

### Requirement: Pagewise history ingestion
Each history page SHALL become persistent independently through the dedicated VASA history endpoint. Import SHALL preserve `service_date`, `is_serviced`, and `non_serviced_reason`, follow all indicated pages using the HTTPS endpoint, and report malformed attempts rather than silently losing them. Newly inserted fill levels SHALL be NULL.

#### Scenario: Persist before the next history response
- **WHEN** page 1 succeeds and page 2 is slow or unavailable
- **THEN** page 1's attempts and progress are already committed

#### Scenario: Use pagination without following insecure links
- **WHEN** continuation links use another path or HTTP
- **THEN** the next page is requested on the configured HTTPS endpoint using its page number

#### Scenario: Report an unusable attempt
- **WHEN** an attempt lacks a usable timestamp or boolean status
- **THEN** the issue identifies its bin/page, valid attempts can persist, and that page is not counted as fully complete

### Requirement: Resume incomplete passes and refresh completed passes
With matching coverage settings, reruns SHALL resume unfinished work from a persistent incomplete pass and skip fully committed work. Once a pass has completed including cleanup, the next invocation SHALL create a new pass and refetch tiles, required bin details, and histories. Incompatible bounds, zoom, source, filter, or mapping settings SHALL not reuse checkpoints.

#### Scenario: Resume after interruption between history pages
- **WHEN** a process stops after committing page 2 and is invoked again with matching settings
- **THEN** committed pages remain and unfinished history work resumes without duplicate events

#### Scenario: Recover from interruption around transaction commit
- **WHEN** a response transaction is interrupted
- **THEN** its data and checkpoint are either both committed or both absent, allowing a safe rerun

#### Scenario: Refresh after full success
- **WHEN** a completed pass exists and a new invocation begins
- **THEN** tiles and history page 1 are fetched again and source changes can update stored values

#### Scenario: Change geographical scope
- **WHEN** an invocation uses different bounds from an incomplete pass
- **THEN** it creates separate coverage progress and cannot claim completion from that pass's checkpoints

### Requirement: Trial imports never establish full coverage
The command SHALL support `--max-sites`, `--max-tiles`, `--workers`, `--zoom`, and `--bbox`, with no distance-grouping option. Zero limits SHALL mean unlimited; workers SHALL default to 4, zoom to 17, and max-sites to 10. A trial SHALL not mark omitted eligible records as covered or mark its pass fully complete, even when its requests succeed.

#### Scenario: Promote a trial to an unlimited import
- **WHEN** a trial imported 10 addresses and the next matching invocation removes limits
- **THEN** its committed data is reused but partially processed tiles are revisited so omitted bins are not lost

#### Scenario: Validate flags before operating
- **WHEN** workers are nonpositive, limits are negative, or bounds/zoom are invalid
- **THEN** the command rejects the arguments before importing

### Requirement: Remove missing bins only after complete bounded refresh
After full successful coverage, required detail retrieval, and history ingestion, cleanup SHALL delete unseen bins whose stored coordinates are inside that pass's bounding box, together with their history. It SHALL remove newly empty sites and recompute surviving affected site means. Cleanup and the pass's completed marker SHALL commit atomically. Trials and incomplete passes SHALL never perform cleanup.

#### Scenario: Remove a missing bin and its only-child site
- **WHEN** a successful unlimited refresh does not see an existing in-bounds bin that is its site's only child
- **THEN** that bin, all its history, and its site are removed

#### Scenario: Preserve out-of-bounds bins and shared sites
- **WHEN** a smaller full refresh removes an unseen in-bounds bin whose site also has an out-of-bounds member
- **THEN** the out-of-bounds bin and its history remain, and the shared site survives with recalculated means

#### Scenario: Defer cleanup after a request failure or trial
- **WHEN** any required tile/detail/history is unfinished or invocation limits are nonzero
- **THEN** no missing bins or their history are removed

#### Scenario: Recover from interrupted cleanup
- **WHEN** final cleanup cannot commit
- **THEN** its removals and completed marker roll back together and the next matching invocation retries finalization

#### Scenario: Accept a completely empty successful coverage pass
- **WHEN** every required tile is verified as successfully empty and no work failed or was limited
- **THEN** cleanup can remove all previously stored in-bounds bins and their history while preserving out-of-bounds records

### Requirement: Bounded requests and retry diagnostics
The importer SHALL limit concurrent requests to the configured worker count and retry temporary failures with bounded exponential backoff. Exhausted requests, missing tiles, required details, missing histories, and invalid responses SHALL be identified in diagnostics and leave the pass incomplete. Recognized empty responses SHALL be distinguished from failed retrievals.

#### Scenario: Retry a temporary API failure
- **WHEN** a request temporarily fails and later succeeds within its retry allowance
- **THEN** its data commits once without duplicate rows

#### Scenario: Exhaust the retry allowance
- **WHEN** a tile or history request continues failing
- **THEN** the failed work is reported explicitly, remains resumable, and disables cleanup

### Requirement: VASA physical-bin coverage
An unlimited import SHALL discover physical bins through VASA Mapbox vector tiles across the configured bounding box, resolve required bin metadata, and retrieve every history page for each eligible discovered bin. A pass SHALL NOT be declared complete unless individual-bin coverage is established and all required tile, detail, and history work is committed without unresolved errors.

#### Scenario: Import a dataset spanning multiple pages
- **WHEN** a discovered bin's history spans several pages
- **THEN** every indicated page is retrieved before that bin's history is marked complete

#### Scenario: Preserve data when a later page fails
- **WHEN** earlier history pages are committed but a later page fails
- **THEN** the committed pages remain available, the pass remains incomplete, and no missing-bin cleanup occurs

#### Scenario: Use the supplied tile source
- **WHEN** the operator imports using the documented VASA endpoint
- **THEN** discovery retrieves `/api/cluster/{z}/{x}/{y}` tiles with the requested waste-type filter

#### Scenario: Advance after a short or empty intermediate page
- **WHEN** a short or empty history page still indicates continuation
- **THEN** the next page is requested instead of assuming history has ended

#### Scenario: Reject unusable pagination or aggregate-only coverage
- **WHEN** history pagination is malformed or discovery cannot establish individual-bin coverage at the selected zoom
- **THEN** the pass reports incomplete coverage and performs no missing-bin cleanup

### Requirement: VASA bin identity and coordinates
Discovery SHALL map VASA `props.id` to physical Bin external identity and convert tile-local point coordinates into WGS84 latitude and longitude. The site's registered address SHALL come from `street` plus `house_number`; grouping SHALL use the address-key contract. Source client addresses SHALL NOT supply site identity.

#### Scenario: Map a tile point without swapping axes
- **WHEN** a vector-tile point decodes to longitude 25.2963107 and latitude 54.7026118
- **THEN** the Bin retains those longitude and latitude meanings with the decoder's coordinate orientation respected

#### Scenario: Respect layer extent
- **WHEN** a layer uses an extent different from 4096
- **THEN** its own extent is used to convert local coordinates

### Requirement: Duplicate tile observations
Duplicate observations of the same physical bin across tiles SHALL resolve to one stored Bin. Conflicting source observations SHALL be reported and resolved deterministically rather than by network completion order. Unresolvable identity conflicts SHALL keep the pass incomplete and prevent cleanup.

#### Scenario: Detect duplicate bin IDs across tiles
- **WHEN** adjacent tiles contain the same VASA external ID
- **THEN** one Bin remains and its coordinates contribute once to its site average

#### Scenario: Diagnose conflicting observations
- **WHEN** tile observations disagree on a bin's registered address
- **THEN** the conflict is reported and the result follows the documented deterministic policy

### Requirement: Atomic incremental ingestion
Each tile's data and coverage checkpoint, each required detail response's metadata and progress, and each history page's events and checkpoint SHALL commit atomically. Failed transactions SHALL roll back their own work while earlier commits survive. A later failure SHALL not stop the separately running backend or permit cleanup. Import SHALL bound network concurrency and buffered response data.

#### Scenario: Handle unavailable VASA
- **WHEN** a request fails after its retry allowance
- **THEN** its work remains unfinished, the failure is reported, prior commits survive, and the backend can continue operating

#### Scenario: Reject a source error disguised as a response
- **WHEN** an endpoint returns a malformed payload or error payload
- **THEN** it is not treated as an empty successful response or a completed checkpoint

#### Scenario: Roll back a write failure
- **WHEN** a database error occurs after rows from one response were written but before commit
- **THEN** that response's rows and checkpoint roll back together
- **AND** earlier response transactions remain committed

### Requirement: Manual import diagnostics
The manual command SHALL retain the existing module invocation and report pass identity, scope, trial/full state, resumed work, fetched/committed counts, failures, and removals. It SHALL return 0 for full success, 1 for failure, and 2 for a deliberately limited incomplete trial. It SHALL produce no CSV files or start an application server.

#### Scenario: Inspect a successful manual import
- **WHEN** `python -m app.interfaces.bin_sync --max-sites 0 --max-tiles 0` completes all work and cleanup
- **THEN** the summary reports full success and committed counts and the command exits 0

#### Scenario: Inspect a failed manual import
- **WHEN** retrieval, validation, persistence, or cleanup fails
- **THEN** the command identifies unfinished work, exits 1, and retains previously committed progress

#### Scenario: Inspect a deliberately limited import
- **WHEN** the operator runs with `--max-sites 10` or a nonzero tile limit without request failures
- **THEN** the command reports incomplete coverage, warns that selected addresses may have unseen member bins, and exits 2

#### Scenario: End after one complete import
- **WHEN** the manual command finishes
- **THEN** it releases its network and database resources without leaving a timer, server, or background importer

#### Scenario: Refresh only when requested again
- **WHEN** the previous matching pass completed fully and the command is invoked again
- **THEN** a new pass fetches source data again and refreshes records rather than skipping old completed checkpoints
