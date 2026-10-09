# Spec Delta

This delta follows the completed `truck-ui` change, which introduces this capability. Archive `truck-ui` before archiving `update-data`; this file modifies that same capability path rather than introducing a second fleet-management capability.

## ADDED Requirements

### Requirement: Fleet retirement API
`DELETE /trucks/{id}` SHALL set `deleted=true` and `available=false` together for a nondeleted truck, return `204` without a body, and retain the row. A missing or already deleted ID SHALL return `404`. Management operations SHALL NOT physically delete trucks or restore them. Retirement SHALL NOT modify sites, physical bins, or bin history.

#### Scenario: Retire a truck independently of collection data
- **WHEN** a nondeleted truck is deleted through the API while sites, bins, and history exist
- **THEN** its row remains with deleted true and available false and all collection data retains its values and references

#### Scenario: Repeat a deletion
- **WHEN** deletion is requested again for an already deleted truck
- **THEN** the response is `404` and the retained record remains unchanged

## REMOVED Requirements

### Requirement: Soft-delete API
**Reason**: The historical-route scenario refers to tables deliberately removed by the replacement migration.
**Migration**: Keep the same DELETE endpoint, retained truck row, flags, status codes, and independent collection-data behavior.
