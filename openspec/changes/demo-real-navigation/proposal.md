# Demo real navigation

## Why
The incoming route-planning feature supplies the real PyVRP solver. Demo must use it instead of illustrative balanced assignments while retaining road-following map geometry.

## What Changes
- Use one Maršrutai tab at /admin/routes for prediction and navigation; retire the separate stored-plan screen.
- Pass predicted due-bin levels to navigation; derive due-bin loads using the shared fill-volume assumptions.
- Solve per carrier with eligible stored trucks, capacity limits and landfill reloads, then render ordered trips through OSRM.
- Report unserved bins explicitly; preserve the read-only workflow, appearance animation and five-row truck pagination. Keep the predicted-bin map visible. Display the table immediately after prediction with a navigation spinner inside it, then populate assigned trucks without drawing all routes.
- Track each selected truck on its calculated road legs, including landfill returns, with a short-lived in-memory run lookup instead of a shared fixture.

## Capabilities
### Modified Capabilities
- `demo-planning`: real planning, one Maršrutai entry, immediate table results and explicit unserved coverage.
- `truck-driving-demo`: tracking the selected truck’s actual calculated route.
- `route-plan-viewing`: route-plan API access without the separate administrator screen.

## Impact
Backend demo request/response DTOs, navigation adapter, repeatable demo command, frontend navigation client/workflow and docs/development.md. Reuse app.optimization.routing; do not invoke the route-plan persistence wrapper.

## Assumptions
Demo loads cover the predicted due bins only, not every bin at their sites. The solver retains estimated detour distances; OSRM supplies display geometry. Stored fleet eligibility can leave bins unserved. No additional application verification is authorized.
