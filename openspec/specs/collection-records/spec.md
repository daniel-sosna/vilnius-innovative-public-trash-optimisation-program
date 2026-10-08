# collection-records Specification

## Purpose

Provide persistent collection-site, truck, route, stop, and service-observation records that future collection workflows and analytical consumers can use without duplicating operational facts.

## Requirements

### Requirement: Collection site records
The system SHALL persist Bin records with only `id`, `lat`, `lon`, `address`, `type`, and `greening`. The ID SHALL be the external integer `KAIKS_NR` and SHALL NOT be generated. A Bin SHALL represent one collection site. Coordinates SHALL be required finite geographic degrees, with latitude in [-90, 90] and longitude in [-180, 180]. An unknown address SHALL be represented as `NULL`.

#### Scenario: Persist a collection site
- **WHEN** a site with external ID 634, latitude 54.6872, longitude 25.2797, and a known address is persisted
- **THEN** its Bin ID is 634 and its latitude, longitude, and address retain their respective meanings

#### Scenario: Reject unusable stored coordinates
- **WHEN** a Bin write supplies a missing coordinate, a nonfinite value, latitude outside [-90, 90], or longitude outside [-180, 180]
- **THEN** the write is rejected without changing existing records

#### Scenario: Preserve a site without an address
- **WHEN** a usable site has no address
- **THEN** its Bin can be stored with an unknown address and required coordinates

### Requirement: Truck records
The system SHALL persist Truck records with only `id`, `name`, `max_bins_per_trip`, and `available`. Name, capacity, and availability SHALL be required. Capacity SHALL be a positive integer counting collection sites per trip, and availability SHALL be a boolean that future route generation can consume.

#### Scenario: Persist truck capacity and availability
- **WHEN** a truck named "Truck 3" is stored with capacity 35 and availability true
- **THEN** the stored truck exposes a capacity of 35 sites per trip and availability true

#### Scenario: Reject unusable truck capacity
- **WHEN** a truck write supplies zero, a negative value, or a missing value for capacity
- **THEN** the write is rejected

### Requirement: Daily route records
The system SHALL persist Route records with only `id`, `service_date`, `truck_id`, and `status`, all required. Each Route SHALL identify one assigned truck and one planned service date, interpreted in Europe/Vilnius. Allowed statuses SHALL be `PLANNED`, `IN_PROGRESS`, and `COMPLETED`; omitted status on creation SHALL default to `PLANNED`. Storage SHALL permit multiple routes for a truck, including on the same date.

#### Scenario: Store separate trips for one truck
- **WHEN** two routes are persisted for the same truck and service date
- **THEN** both routes receive distinct IDs and retain their own ordered stops

#### Scenario: Default a new route status
- **WHEN** a valid new route is persisted without an explicit status
- **THEN** its status is `PLANNED`

#### Scenario: Reject an unsupported route status
- **WHEN** a route write supplies a status outside the three allowed values
- **THEN** the write is rejected

### Requirement: Ordered route stop records
The system SHALL persist RouteStop records with only `id`, `route_id`, `bin_id`, and `stop_order`, all required. Stop order SHALL be a positive integer using one-based positions. Two stops within one route SHALL NOT share a position. Different routes SHALL be able to reuse the same position numbers.

#### Scenario: Read an ordered route
- **WHEN** a route has stored positions 3, 1, and 2
- **THEN** its ordered stop sequence can be retrieved as positions 1, 2, and 3

#### Scenario: Reject duplicate positions within a route
- **WHEN** another stop is persisted at an existing position in the same route
- **THEN** the write is rejected

#### Scenario: Reuse positions on another route
- **WHEN** two different routes each receive their first stop
- **THEN** both can store position 1

#### Scenario: Reject a nonpositive stop position
- **WHEN** a route stop is persisted with stop order zero or a negative value
- **THEN** the write is rejected

### Requirement: Raw service observation records
The system SHALL persist ServiceEvent records with only `id`, `bin_id`, `service_ts`, `fill_level`, `duration`, and `route_id`, all required. Each event SHALL represent complete emptying of one collection site. `service_ts` SHALL identify the completion instant using a timezone-aware timestamp; `fill_level` SHALL describe the observed state immediately before emptying. Duration SHALL be a nonnegative integer number of seconds.

#### Scenario: Preserve an actual collection observation
- **WHEN** site 920 is completely emptied during route 15 with observed fill level `FULL`, duration 90 seconds, and a known completion instant
- **THEN** the event retains bin 920, route 15, the completion instant, `FULL`, and duration 90
- **AND** the completion instant identifies the beginning of the next fill cycle

#### Scenario: Reject an invalid service duration
- **WHEN** an event is written with a negative or missing duration
- **THEN** the write is rejected

#### Scenario: Preserve timestamp instants across offsets
- **WHEN** a service completion timestamp is supplied with an explicit UTC offset
- **THEN** its stored timestamp represents the same instant independently of the display timezone

### Requirement: Categorical fill observations
A ServiceEvent fill level SHALL be exactly one of `EMPTY`, `LESS_THAN_HALF`, `MORE_THAN_HALF`, and `FULL`. The system SHALL retain these as observed categories without substituting predicted probabilities or invented numeric fill percentages.

#### Scenario: Store each allowed observed category
- **WHEN** valid events use any of the four allowed categories
- **THEN** each event retains the supplied observed category

#### Scenario: Reject an unsupported fill category
- **WHEN** an event supplies another category or omits its fill level
- **THEN** the write is rejected

### Requirement: Independent generated record identities
Truck, Route, RouteStop, and ServiceEvent SHALL each have a generated integer primary key named `id`. Their primary keys SHALL NOT be composite, and callers SHALL NOT need to supply these IDs when creating valid records.

#### Scenario: Generate a stop identity independently of its position
- **WHEN** a valid route stop is inserted without an ID
- **THEN** storage generates its ID independently of route ID, bin ID, and stop order

#### Scenario: Generate identities for the other internal records
- **WHEN** valid Truck, Route, and ServiceEvent records are inserted without IDs
- **THEN** each receives an independently generated primary key

### Requirement: Required entity relationships
The system SHALL require valid references for `Route.truck_id`, `RouteStop.route_id`, `RouteStop.bin_id`, `ServiceEvent.bin_id`, and `ServiceEvent.route_id`. Each reference SHALL be non-null and SHALL identify an existing record of the corresponding entity.

#### Scenario: Reject a missing relationship
- **WHEN** a write supplies `NULL` for any required entity reference
- **THEN** the write is rejected

#### Scenario: Reject a nonexistent parent
- **WHEN** a route, stop, or event references a truck, route, or bin that does not exist
- **THEN** the write is rejected

### Requirement: Protect referenced collection records
The system SHALL reject deletion of a Bin referenced by a RouteStop or ServiceEvent, a Truck referenced by a Route, or a Route referenced by a RouteStop or ServiceEvent. Deleting a parent SHALL NOT cascade into collection history or detach required relationships.

#### Scenario: Preserve a referenced site
- **WHEN** deletion is requested for a Bin used by stored routing or service records
- **THEN** the deletion is rejected and the referencing records remain intact

#### Scenario: Preserve route and truck attribution
- **WHEN** deletion is requested for a referenced Route or Truck
- **THEN** the deletion is rejected and existing route, stop, and service records remain intact

### Requirement: Derive service truck attribution through the route
ServiceEvent SHALL NOT store `truck_id`. Consumers SHALL be able to resolve its assigned truck through `ServiceEvent.route_id` followed by `Route.truck_id`.

#### Scenario: Resolve the servicing truck
- **WHEN** an event references route 15 and route 15 references truck 3
- **THEN** a consumer can resolve truck 3 through the route relationship without a truck field on the event

### Requirement: Preserve raw per-site history
The system SHALL preserve multiple ServiceEvents per Bin with their raw facts and allow chronological retrieval by service timestamp, with event ID breaking timestamp ties. Stored records SHALL NOT add derived service intervals, ML features, predictions, generic metadata, audit fields, or historical site snapshots.

#### Scenario: Retrieve consecutive raw observations
- **WHEN** a Bin has service events on 1 September and 4 September
- **THEN** a consumer can retrieve both observations in chronological order and derive the elapsed interval outside the core record schema

#### Scenario: Distinguish simultaneous event ordering
- **WHEN** two events for one Bin have the same timestamp
- **THEN** event ID provides deterministic retrieval order without fabricating a positive elapsed interval

### Requirement: Schema readiness before serving
Standard backend startup SHALL prepare the versioned collection schema before serving requests. Repeating preparation on an up-to-date database SHALL preserve existing records. If schema preparation fails, the backend SHALL NOT begin serving requests. Schema preparation SHALL NOT import external Bin data.

#### Scenario: Start against an empty database
- **WHEN** the backend is started through its documented startup path against an empty configured database
- **THEN** the five collection tables and their constraints are available before request serving
- **AND** the Bin registry remains empty until an operator explicitly imports sites

#### Scenario: Restart against an initialized database
- **WHEN** the backend restarts with the current schema and existing collection records
- **THEN** schema preparation preserves those records without triggering a Bin import

#### Scenario: Refuse startup after schema preparation failure
- **WHEN** required schema preparation fails
- **THEN** startup reports the failure and does not launch request serving

### Requirement: Optional site metadata text
Bin `type` and `greening` SHALL each accept arbitrary text or `NULL`. Storage SHALL NOT restrict either field to a fixed list of labels or require a referenced classification record. These fields SHALL describe source site attributes rather than predicted fill or derived analytical features.

#### Scenario: Persist recognized Lithuanian labels
- **WHEN** a Bin is written with type `B3 (pusiau požeminiai)` and greening `Taip, agentūrai ES pritarus`
- **THEN** both supplied strings are retained with their Lithuanian characters

#### Scenario: Accept labels outside the known GIS mappings
- **WHEN** a valid Bin is written with type `Future collection-site type` and greening `Future greening description`
- **THEN** both strings are accepted without an allowed-value rejection

#### Scenario: Represent unknown metadata
- **WHEN** a valid Bin is written without type and greening information
- **THEN** both fields can be `NULL` while its required ID and coordinates remain present

#### Scenario: Upgrade existing collection records
- **WHEN** existing collection storage is upgraded to include the optional metadata fields before another import
- **THEN** existing Bins have `NULL` metadata while their IDs, coordinates, and addresses remain unchanged
- **AND** all existing truck, route, stop, and service-event records and references are preserved
