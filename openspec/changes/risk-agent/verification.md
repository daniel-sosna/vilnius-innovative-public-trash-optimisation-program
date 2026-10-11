# Verification

- Docker access: `sg docker -c 'docker compose ps'`; backend, database and frontend running.
- Required sources: configured `backend/data/` contains all three CSV export types, population GeoJSON and `bin_days_20231010_20261009_enriched.csv`.
- Artifact contracts: `cd backend && .venv/bin/python -m app.interfaces.container_adequacy.verify --artifact-contracts` exits 0. Legacy v1 and dated v2 day 1/18/30 accepted; eight malformed date, identity, completion, coverage and metric mutations rejected.
- Storage migration: `sg docker -c 'docker compose exec -T backend .venv/bin/python -m app.interfaces.container_adequacy_import.verify'` exits 0. Isolated database upgrade preserves a legacy row, accepts partial completion, rejects five invalid rows, and downgrades after dated-row removal. Temporary database removed.
- Batch import audit: the same isolated storage command rejects a valid-plus-invalid batch before writing, preserves unrelated rows, reimports idempotently and replaces only the explicitly selected revision. Exit 0.
- Data model documentation checked against the v1/v2 fixture metadata and validator fields.
- Prefix audit: `cd backend && .venv/bin/python -m app.interfaces.container_adequacy.verify --prefix-contracts` exits 0. Thirty incremental prefixes use a September 1 cohort; mutated later labels leave earlier counts, coverage, priors, uncertainty and categories unchanged. CLI modes are exclusive; missing cohort bin/day and undeclared bins rejected. A single-point fixture produced a nonconvergent fit; a two-point-per-stream fixture passes, and fit failures retain explicit cutoff/type feedback without a fallback method.
- Prefix publication audit also verifies 30 distinct dated identities, correct partial/full flags, identical repeated-run bytes, unchanged legacy September, explicit regeneration and preservation on invalid replacement.
- Repeatable audit is exposed through `--prefix-contracts` without an automated test suite. It reports coverage, sparse evidence, future-label independence, publication and CLI checks; exceptions produce nonzero exit codes.
- Preparation/import documentation checked against both CLI help outputs and fixture publication output. It records source cohort assumptions, the 30 dated names/version, reuse/regeneration and atomic publication side effects.

## Verification ownership

The developer requested that Codex perform no further verification and will
provide verification results. Checks recorded above ran before that request.
Implementation continues; unfinished verification and acceptance checkboxes
remain open pending developer evidence. No browser checks or production build
are run by Codex after that instruction.

## Preparation

The explicit preparation run generated all 30 September cutoffs in 149.77 s,
totaling 1,359,339,440 bytes. See `preparation.jsonl`. Sources remained unchanged
during generation (the generator enforces this before returning success).
Migration 0019 was applied to the running database. The source audit started
before the verification-ownership instruction; its captured output is in
`source-audit.json` and its process ended with exit 0 before cancellation.

## Implementation handoff

- All 30 generated cutoffs were imported in one transaction with exit 0.
  See `import-output.log`. Import timing was not captured by that invocation;
  subsequent explicit imports log input bytes and elapsed time.
- Catalog/API code accepts the shared September date and exact dated identity.
- Map code selects the exact cutoff, retains earlier-month/type choices and
  labels inclusive partial/full periods. Date/revision identity drives layer caching.
- Agent requests/responses carry the validated project date. Saved risk tools
  pin artifact identity/revision or absence, intersect exact geometry, bound
  listing/detail output and deduplicate serving-point evidence per waste stream.
- Date changes clear pending/completed agent answers and errors, retaining bbox.
- Runtime guidance and CLI examples carry the date contract.
- Official documentation consulted before tool changes:
  [strict function calling](https://developers.openai.com/api/docs/guides/function-calling#strict-mode).
  The existing schema converter closes objects and makes nullable fields required.

## Developer verification

These commands are provided for the developer; Codex has not run them after
verification was assigned to the developer. Tasks 2.5 and 3–5 remain open pending
their specified acceptance evidence.

```bash
# From repository root (use sg docker -c if the session lacks the group):
docker compose exec -T backend .venv/bin/python -m app.interfaces.analytics_agent.check --risk-contracts
docker compose exec -T backend .venv/bin/python -m app.interfaces.analytics_agent.check --bbox 54.68 25.27 54.70 25.30 --project-date 2026-09-18 --tool get_adequacy_summary --arguments '{"waste_type":null}'
docker compose exec -T frontend npm run build
```

The risk contract diagnostic prepares disposable database fixtures and uses
read-only tool dispatch, with no provider calls. It covers holes/boundaries,
invalid geometry, external points, 5/20 shared assessment counts, null metrics,
pagination, missing/empty/failed reads, pinned absence/replacement and budgets.
The supplied-data diagnostic reports elapsed time including discovery.

Use the task scenarios for September 1, 14, 18 and 30, reverse/rapid changes,
hidden layers, revision refresh, keyboard use and 320-pixel rendering. Confirm
that changing the date clears an agent run without starting another provider call.

## Presentation handoff

- Manual analysis-list refresh is removed; catalog-error retry remains.
  Re-enabling discovers the current catalog/revision while retaining result caching.
- Mandatory top-level instructions require a separate nonempty
  `## Konteinerių pakankamumas` section and forbid data-origin commentary.
- The backend response boundary rejects prohibited Lithuanian/English wording
  and missing/empty sections. It requests synthesis-only correction within the
  existing five-request/time limits; noncompliant text is withheld on all normal,
  SSE and partial-answer paths, with `response_policy` incomplete feedback.
- Internal artifact/tool provenance remains available for interpretation.
- No verification was run for these edits, as requested. Tasks 6.1–6.3 await
  developer verification.
