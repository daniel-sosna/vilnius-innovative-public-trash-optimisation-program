# Spec Delta

## MODIFIED Requirements

### Requirement: Load population polygons from the density file
The command SHALL read a GeoJSON FeatureCollection of polygons in longitude/latitude. The default is `population_density_1ha.geojson` in the data directory: `VIPTOP_DATA_DIR` when set (relative values resolved from the repository root), otherwise `backend/data/`. `--file` gives another path. Each feature SHALL be stored as one population polygon whose identifier is the feature's `OBJECTID`, with its density value and its area. A rebuild SHALL replace all previously stored polygons.

#### Scenario: Current Vilnius file
- **WHEN** the command runs with the current density file
- **THEN** 14,079 population polygons are stored, identified by their `OBJECTID`

#### Scenario: Missing file
- **WHEN** the file does not exist
- **THEN** the command changes nothing, names the missing path and exits with 1

#### Scenario: Unreadable feature
- **WHEN** a feature has no `OBJECTID`, has a geometry that is not a polygon, or has a density value that is not a whole number, `"<11"` or null
- **THEN** the command changes nothing, names the feature and the problem, and exits with 1

#### Scenario: Shared data directory
- **WHEN** `VIPTOP_DATA_DIR` names a folder containing `population_density_1ha.geojson` and the command runs without `--file`
- **THEN** the polygons are read from that folder's file

#### Scenario: Explicit file beats the variable
- **WHEN** `VIPTOP_DATA_DIR` is set and the command is run with `--file /some/file.geojson`
- **THEN** the polygons are read from `/some/file.geojson`
