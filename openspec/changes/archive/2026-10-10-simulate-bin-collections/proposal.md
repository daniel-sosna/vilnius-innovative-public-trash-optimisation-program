# Proposal

## Why

The synthetic fill-level generator needs to know when each bin was emptied. It also needs collection-history features to train on. Today `bin_days` is only a calendar × bin grid. VASA planned collection dates are now stored per bin in `bin_schedule`, so the rebuild can simulate realistic collections from them. It can also derive the look-back features the prediction model will use.

## What Changes

- The `bin_days` rebuild simulates **synthetic collection outcomes** for each bin and day:
  - Each bin's stored schedule (currently a one-month snapshot) is stretched over the requested range as a repeating cycle, keeping its phase.
  - A collection is attempted on every planned day, and a small random share of attempts fails. A failed attempt is retried on up to 2 following days, and retries fail much more often. The next planned day cancels any pending retries.
  - An attempt on a Lithuanian public holiday is more likely to fail.
  - Simulation starts 35 days before `--start`, so the first written rows already have full look-back features.
- New `bin_days` columns:
  - `collection_status`: the day's own outcome. One of `none`, `collected`, `retry_collected`, `failed` or `missed`.
  - `holidays_since_last_collection`: Lithuanian public holidays from the day after the last successful collection through yesterday.
  - `collections_last_28d`: successful collections from date − 28 to date − 1.
  - `missed_collections_28d`: planned collections that were finally not carried out, from date − 28 to date − 1. A miss counts on the day it becomes final.
- **BREAKING** (for the calendar contract): only bins that have a `sub_district` **and** at least one planned date are included. Bins without a schedule are skipped and counted in the summary. With the current exports that is 21,695 bins: 147 have no sub-district and 109 have no schedule.
- New rebuild options: `--seed` makes the result reproducible. `--p-first`, `--p-retry1`, `--p-retry2` and `--holiday-factor` set the failure model. The defaults are 0.028, 0.40, 0.70 and 2.
- The rebuild summary also reports the parameters, the seed and totals per outcome.
- New backend dependency: `holidays`, for Lithuanian public holidays, including movable ones.

## Capabilities

### New Capabilities

None. Collection simulation is part of the bin-day calendar, which is the input contract for synthetic generation.

### Modified Capabilities

- `bin-day-calendar`: changes to eligibility (now requires a schedule), the independence requirement (the calendar now reads `bin_schedule` and holds synthetic collection outcomes, but still not service history), output and arguments. New requirements cover schedule stretching, the failure and retry model, holidays, the four new columns, warm-up and reproducibility.

## Impact

- **Code**: `backend/app/interfaces/bin_days/cli.py` (the rebuild becomes a Python simulation plus a bulk load), `backend/app/infrastructure/models.py` (`BinDay`), and a new Alembic migration `0011` that adds the four columns.
- **Dependencies**: `holidays` added to `backend/pyproject.toml` and `uv.lock`.
- **Docs**: README section "Bin-day calendar" and `docs/bin-day-calendar-verification.md`.
- **Consumers**: the future fill-level generator and ML features read `bin_days`. The new columns are **synthetic**, not observed history. The generator still reads observed history from `bin_hist`.
- **Assumptions** (stated explicitly in the spec and design):
  - The stored schedule repeats unchanged over the whole range.
  - The failure probabilities are assumptions. The first-attempt rate is set below the 3.4% non-service rate seen in `bin_hist`, which includes non-failures such as "empty container". Retry rates are chosen so that misses remain visible.
  - Holidays do not move planned days.
- **Uncertainties**:
  - Rebuild time for long ranges (about 8M rows per year of range).
  - Bins with a single planned date per month are treated as every-four-weeks rather than same day-of-month.
