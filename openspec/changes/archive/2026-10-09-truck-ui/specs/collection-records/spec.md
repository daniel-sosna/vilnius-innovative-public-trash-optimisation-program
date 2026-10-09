# Spec Delta

## MODIFIED Requirements

### Requirement: Truck records
The system SHALL persist Truck records with only `id`, `name`, `max_bins_per_trip`, `available` and `deleted`, all required. Name SHALL be nonempty after trimming. Capacity SHALL be an integer 1–99 counting collection sites per trip. Availability SHALL be a boolean that future route generation can consume. Deletion SHALL be a boolean defaulting to false. A deleted truck SHALL always be unavailable.

#### Scenario: Persist truck capacity and availability
- **WHEN** a truck named "Truck 3" is stored with capacity 35 and availability true
- **THEN** the stored truck exposes a capacity of 35 sites per trip and availability true

#### Scenario: Reject unusable truck capacity
- **WHEN** a truck write supplies zero, a negative value, or a missing value for capacity
- **THEN** the write is rejected

#### Scenario: Enforce the upper capacity bound
- **WHEN** a truck write supplies capacity greater than 99
- **THEN** the write is rejected without changing the truck's existing values

#### Scenario: Reject an empty truck name
- **WHEN** a truck write supplies an empty or whitespace-only name
- **THEN** the write is rejected

#### Scenario: Default a new truck's deletion flag
- **WHEN** a valid new truck is stored without explicitly supplying its deletion flag
- **THEN** its stored deletion flag is false

#### Scenario: Reject inconsistent retired-truck availability
- **WHEN** a truck write would store deleted true and available true together
- **THEN** the write is rejected

### Requirement: Protect referenced collection records
The system SHALL reject physical deletion of a Bin referenced by a RouteStop or ServiceEvent, a Truck referenced by a Route, or a Route referenced by a RouteStop or ServiceEvent. Physical deletion of a parent SHALL NOT cascade into collection history or detach required relationships. Soft deletion of a Truck SHALL retain its row and SHALL NOT modify its historical Routes, RouteStops or ServiceEvents.

#### Scenario: Preserve a referenced site
- **WHEN** physical deletion is requested for a Bin used by stored routing or service records
- **THEN** the deletion is rejected and the referencing records remain intact

#### Scenario: Preserve route and truck attribution
- **WHEN** physical deletion is requested for a referenced Route or Truck
- **THEN** the deletion is rejected and existing route, stop, and service records remain intact

#### Scenario: Soft delete a referenced truck
- **WHEN** a truck used by stored routing or service records is soft deleted
- **THEN** its row is retained with deleted true and available false
- **AND** all route, stop and service-event records and foreign-key references remain intact

### Requirement: Derive service truck attribution through the route
ServiceEvent SHALL NOT store `truck_id`. Consumers SHALL be able to resolve its assigned truck through `ServiceEvent.route_id` followed by `Route.truck_id`, including when that Truck has been soft deleted.

#### Scenario: Resolve the servicing truck
- **WHEN** an event references route 15 and route 15 references truck 3
- **THEN** a consumer can resolve truck 3 through the route relationship without a truck field on the event

#### Scenario: Resolve attribution after retirement
- **WHEN** truck 3 has been soft deleted and a consumer reads a historical event through its route and retained truck relationship
- **THEN** truck 3's identity and name remain resolvable independently of its exclusion from management endpoints

## ADDED Requirements

### Requirement: Preserve collection data during truck schema upgrade
Upgrading storage for truck retirement SHALL set existing trucks' deletion flags to false and preserve their IDs, names, capacities and availability, along with all collection history and references. If an existing truck violates the new capacity or name constraints, the upgrade SHALL fail with an actionable diagnostic without silently correcting records or publishing a partial upgrade.

#### Scenario: Upgrade existing valid trucks
- **WHEN** initialized collection storage contains valid trucks and historical routes and is upgraded
- **THEN** each existing truck has deleted false and its prior values remain intact
- **AND** all Bins, Routes, RouteStops and ServiceEvents retain their values and references

#### Scenario: Detect incompatible existing records
- **WHEN** an existing truck has capacity above 99 or a blank name at upgrade time
- **THEN** preparation fails identifying the incompatible truck IDs and reason
- **AND** operational values and the previous schema remain unchanged until the operator resolves the incompatibility

#### Scenario: Repeat the upgrade
- **WHEN** schema preparation runs again on already upgraded storage
- **THEN** existing deletion flags and collection records remain unchanged
