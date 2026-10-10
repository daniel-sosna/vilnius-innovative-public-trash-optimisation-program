# Tasks

## 1. Dependency and schema

- [x] 1.1 Add `holidays` to the backend with `uv add holidays` (updates `pyproject.toml` and `uv.lock`). Verify that `uv run python -c "import holidays; print(sorted(holidays.country_holidays('LT', years=2027)))"` lists 2027-03-28, 2027-03-29, Mother's Day 2027-05-02, Father's Day 2027-06-06 and 2027-12-24.
- [x] 1.2 Add Alembic migration `0011` (revises `0010`). It truncates `bin_days` and adds `collection_status` (TEXT NOT NULL, CHECK in the five values), `holidays_since_last_collection` (SMALLINT NOT NULL, ≥ 0), `collections_last_28d` and `missed_collections_28d` (SMALLINT NOT NULL, 0–28). Downgrade drops them. Verify that `alembic upgrade head`, `downgrade 0010` and `upgrade head` succeed and that `\d bin_days` shows the columns and checks.
- [x] 1.3 Add the four columns and check constraints to `BinDay` in `backend/app/infrastructure/models.py`. Verify that `alembic check` (or autogenerate in a scratch run) reports no differences.

## 2. Simulation core

- [x] 2.1 Add `backend/app/interfaces/bin_days/simulation.py` with cycle detection (design decision 4). Verify with a `python -c` snippet against the spec scenarios (weekly, Mon/Wed/Fri, two-weekly phase, daily, single date, irregular 10-01/10-08). On the current `bin_schedule` export, also verify the distribution 12,279 / 6,319 / 2,281 / 67 / 894.
- [x] 2.2 Implement the per-bin day walk (design decision 2): planned and retry attempts, cancellation by a planned day, the `failed`/`missed`/`collected`/`retry_collected`/`none` statuses, holiday factor with a 0.95 cap, and a per-bin `random.Random(f"{seed}:{bin_id}")`. Verify with snippets that `p_first=0` gives only `collected`/`none`, that forcing failures (`p=1`) on a weekly bin gives `failed, failed, missed`, and that a daily bin gives only `missed` on failure.
- [x] 2.3 Emit the start-of-day features in the same walk: a 28-day ring buffer for `collections_last_28d` and `missed_collections_28d`, and the holiday counter since the last success (counting from the simulation start before the first success). Rows are yielded only from `start`. Verify the spec scenarios: collected yesterday gives 0, 2026-10-30 to 2026-11-04 gives 2, a weekly bin with no failures has 4 on its first row, and a miss that becomes final on 10-07 is counted from 10-08 through 11-04.

## 3. Rebuild command

- [x] 3.1 Extend the argparse setup in `backend/app/interfaces/bin_days/cli.py` with `--seed` (default 42), `--p-first` (0.028), `--p-retry1` (0.40), `--p-retry2` (0.70) and `--holiday-factor` (2), validated before connecting. Verify that `--p-first 1.5` and `--holiday-factor -1` exit with 1, name the value and do not touch the database (run with the database stopped).
- [x] 3.2 Replace `REBUILD_SQL` with the pipeline from design decision 1: load eligible bins (with a `sub_district` and planned dates) and their dates, stream the simulated rows via `COPY` into a temporary table, then `TRUNCATE bin_days` and run `INSERT ... SELECT`, joining `bins` and computing the calendar features as before, all in one transaction under `SYNC_LOCK_TIMEOUT_MS`. Verify that a rebuild for 2026-09-09..2026-10-09 gives 21,695 × 31 = 672,545 rows, and that killing the process mid-run leaves the previous contents intact.
- [x] 3.3 Extend the success summary with the bins excluded for no schedule, the seed, the four parameters and the row count per status. Verify that it prints `147 excluded without sub_district, 109 excluded without schedule` and five status counts that sum to the row count.

## 4. Documentation

- [x] 4.1 Update the README section "Bin-day calendar": eligibility, the new options and defaults, the four columns (marked **synthetic**), the status meanings, the assumptions (repeating schedule, assumed probabilities with `bin_hist` reference rates, no holiday shifting, 35-day warm-up, 28-day cycle for single dates) and the updated row count and timing. Also fix the "holds no outcomes" sentence. Verify that the documented commands run as written.
- [x] 4.2 Update `docs/bin-day-calendar-verification.md`. Update the expected counts and add checks for: status values and transition rules (no `retry_collected` without a preceding `failed`, at most 2 consecutive `failed`), `collections_last_28d`/`missed_collections_28d` recomputed with SQL window functions and matching, holiday counts on 2026-11-03/04, identical output for the same seed and different output for another seed, and `--p-first 0` giving zero failures. Verify that every check passes against a fresh rebuild.

## 5. End-to-end check

- [x] 5.1 On a database loaded from the current exports, rebuild 2026-09-09..2026-10-09 and a one-year range. Run the full verification doc. Record the one-year runtime in the README, and check that the observed share of `missed` among planned occurrences is close to 0.028 × 0.40 × 0.70 ≈ 0.78% (higher around holidays).

## Workflow follow-up

- Archive the change with `/opsx:archive` after review, and check that `openspec/specs/bin-day-calendar/spec.md` contains the merged requirements.
