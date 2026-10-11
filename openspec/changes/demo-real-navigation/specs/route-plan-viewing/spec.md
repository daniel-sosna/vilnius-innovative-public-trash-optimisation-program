# Spec Delta

## REMOVED Requirements

### Requirement: Route plan page
**Reason**: The single Maršrutai tab uses the current prediction and navigation workflow.
**Migration**: Use /admin/routes for planning or the existing /route-plans API to read saved plans.

### Requirement: Trucks, trips and stops on the map
**Reason**: The combined stored-plan map is replaced by per-truck tracking on calculated road geometry.
**Migration**: Open a truck from the navigation result table to view its own road path.

### Requirement: Savings and warnings on the page
**Reason**: The separate stored-plan screen is removed; completed planning displays truck results and unserved notices.
**Migration**: Stored optimizer and baseline figures remain readable through /route-plans.
