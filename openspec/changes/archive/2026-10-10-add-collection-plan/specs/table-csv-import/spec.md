# Spec Delta

## ADDED Requirements

### Requirement: Empty the collection plan with replaced bins
When the import replaces `bins` and no `collection_stops` file is selected, it SHALL empty all stored collection plans (stops and their bins) in the same transaction, report that it did so and name `python -m app.interfaces.collection_plan` as the command that refills it. An import that does not replace `bins` SHALL keep the plan.

#### Scenario: Collection import empties the plan
- **WHEN** a collection plan is stored and files for `sites`, `bins` and `bin_hist` are imported
- **THEN** the import succeeds, no collection plan remains, and the output names the refill command

#### Scenario: History-only import keeps the plan
- **WHEN** only `bin_hist_*.csv` is present
- **THEN** every stored collection plan is unchanged
