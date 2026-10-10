# Proposal

## Why

Service-zone coverage needs to remain easy to distinguish alongside district colors and population shading. Bold boundaries provide that distinction while keeping the existing light area tint.

## What Changes

- Use bold dark teal zone outlines above the other polygon datasets.
- Retain the original translucent teal fill, zone names and visual-only interactions.
- Remove the crosshatch and its pattern-image support following the user's revised request.
- Leave all verification to the user, as explicitly requested.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `map-layers`: Specify bold service-zone boundaries that remain legible over the other polygon layers.

## Impact

Frontend service-zone outline styling and relevant documentation. No backend, API, database, import or dependency changes. The change directory retains its original name; its final scope is bold zone boundaries.
