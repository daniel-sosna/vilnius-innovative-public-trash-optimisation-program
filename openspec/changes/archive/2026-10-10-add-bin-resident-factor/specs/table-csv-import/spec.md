# Spec Delta

## ADDED Requirements

### Requirement: Empty the resident allocation with replaced bins
When the import replaces `bins` and no `bin_population` file is selected, it SHALL empty the per-bin resident allocation in the same transaction, report that it did so and name `python -m app.interfaces.bin_population` as the command that refills it. Stored population polygons SHALL be kept. An import that does not replace `bins` SHALL keep the allocation.

#### Scenario: Collection import empties the allocation
- **WHEN** resident allocations are stored and files for `sites`, `bins` and `bin_hist` are imported
- **THEN** the import succeeds, no bin has a resident allocation, the population polygons are unchanged, and the output names the refill command

#### Scenario: History-only import keeps the allocation
- **WHEN** only `bin_hist_*.csv` is present
- **THEN** every bin keeps its resident allocation
