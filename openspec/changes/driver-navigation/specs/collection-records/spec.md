# Spec Delta

## MODIFIED Requirements

### Requirement: Nullable numeric fill observations
BinHist `fill_level` SHALL accept only NULL or the integers 0 through 4, where 4 means overflowing. Newly imported VASA attempts SHALL have NULL fill level. Import SHALL NOT infer fill from successful or unsuccessful servicing, and refreshing an existing attempt SHALL preserve a subsequently recorded fill observation.

#### Scenario: Import history without invented fill
- **WHEN** successful and unsuccessful attempts are imported
- **THEN** newly inserted rows both have NULL fill level

#### Scenario: Preserve subsequent observation on refresh
- **WHEN** an existing attempt has fill level 2 and is encountered again
- **THEN** refresh updates source attributes without clearing its fill level

#### Scenario: Accept level 4
- **WHEN** a history write supplies 4
- **THEN** storage accepts it

#### Scenario: Reject unsupported fill values
- **WHEN** a history write supplies -1 or 5
- **THEN** storage rejects it
