# Spec Delta

## MODIFIED Requirements

### Requirement: Remove missing bins only after complete bounded refresh
After full successful coverage, required detail retrieval, and history ingestion, cleanup SHALL delete unseen imported bins with non-NULL external IDs whose stored coordinates are inside that pass's bounding box, together with their history. Manual bins with NULL external IDs SHALL be excluded. Cleanup SHALL remove newly empty sites and recompute surviving affected site means. Cleanup and pass completion SHALL commit atomically. Trials and incomplete passes SHALL never perform cleanup.

#### Scenario: Remove a missing bin and its only-child site
- **WHEN** a successful unlimited refresh does not see an existing in-bounds imported bin that is its site's only child
- **THEN** that bin, all its history, and its site are removed

#### Scenario: Preserve out-of-bounds bins and shared sites
- **WHEN** a smaller full refresh removes an unseen in-bounds imported bin whose site also has an out-of-bounds member
- **THEN** the out-of-bounds bin and its history remain, and the shared site survives with recalculated means

#### Scenario: Defer cleanup after a request failure or trial
- **WHEN** any required tile/detail/history is unfinished or invocation limits are nonzero
- **THEN** no missing bins or their history are removed

#### Scenario: Recover from interrupted cleanup
- **WHEN** final cleanup cannot commit
- **THEN** its removals and completed marker roll back together and the next matching invocation retries finalization

#### Scenario: Accept a completely empty successful coverage pass
- **WHEN** every required tile is verified as successfully empty and no work failed or was limited
- **THEN** cleanup can remove all previously stored in-bounds imported bins and their history while preserving out-of-bounds and manual records

#### Scenario: Preserve an entirely manual Site
- **WHEN** a complete bounded refresh sees no external feature for a manual Site's NULL-external-ID Bins within its bounds
- **THEN** those Bins, their dependent records and their Site remain unchanged
- **AND** that Site is not selected as affected solely because its Bins have no external IDs

#### Scenario: Preserve a manual child under an imported Site
- **WHEN** complete cleanup removes all missing imported Bins from a Site that also contains a manual Bin
- **THEN** the manual Bin and its dependent records remain and the Site survives
- **AND** existing import averaging applies over the surviving membership
