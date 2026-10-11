# Tasks

- [x] 1. Resolve shared API/frontend route and navbar conflicts, preserving shared backend access and date context.
- [x] 2. Replace illustrative assignments with the existing PyVRP solver, carrier/capacity/depot inputs and OSRM trip geometry without database writes.
- [x] 3. Pass current prediction levels through navigation; report and display unserved bins with exact partition checks; update the repeatable command.
- [x] 4. Update docs/development.md with solver/load assumptions and runtime limits.
- [x] 5. Use one Maršrutai tab, remove the separate stored-plan screen and all-route drawing, and keep the map visible and show the truck table after prediction, with navigation loading inside it and five-row result pages.
- [x] 6. Replace the shared tracking fixture with the selected truck’s cached service-generated road legs; preserve camera following, disappearing passed line and service-stop collection coloring.
- [x] 7. Update README feature URLs and docs/development.md and docs/data/route-plan.md for the consolidated screen and transient route lifetime.
- [ ] 8. Developer verifies optimized assignments, depot returns, partial/all-unserved results, road geometry, appearance sequencing and existing routes/date navigation. No agent-run checks.

- [x] 9. Keep solver imports out of API startup and report missing PyVRP explicitly during navigation; rebuild the backend to install the incoming locked solver dependency.

- [x] 10. Keep the predicted-bin map visible after navigation, reveal the truck table after prediction, and move navigation loading into its table body.
