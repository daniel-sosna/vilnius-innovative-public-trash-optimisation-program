# Spec Delta

## MODIFIED Requirements

### Requirement: Uniform service-zone context polygons
Enabling `Aptarnavimo zonos` SHALL display all returned service-zone polygons with one shared translucent fill color and bold dark teal boundaries, retaining stored shapes and holes. Zone boundaries SHALL remain legible above district and population areas. The basemap and other enabled datasets SHALL remain readable. Disabling the layer SHALL hide its fills, outlines and text together.

#### Scenario: Display the supplied zones
- **WHEN** the layer receives the supplied five stored zones
- **THEN** all five polygons use the same fill color and adjacent zones are distinguishable by bold boundaries
- **AND** no metric-based or per-zone color scheme is applied

#### Scenario: Hide every zone visual
- **WHEN** the administrator unchecks `Aptarnavimo zonos`
- **THEN** zone fills, boundaries and names disappear together while the basemap and other selected layers remain available

#### Scenario: Display alongside other polygon layers
- **WHEN** districts and population are enabled with service zones
- **THEN** bold zone boundaries remain visible above their area colors
- **AND** the zones have a light translucent tint without a hatch pattern
