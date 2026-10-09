# Historical runtime preparation

## Post-import activation (2026-10-09)

The user confirmed the data import is over and explicitly requested removal of
temporary Compose overrides and use of the real Compose setup. This supersedes
the import-period isolation/no-reload constraints for activation in this checkout.
Implementation was transferred into the main source tree. The temporary overrides
and runtime-path pointer were removed from both checkouts and the temporary
runtime directory. Real `docker-compose.yml` passes `VITE_MAP_STYLE_URL` with a
configurable Liberty default. Its existing database/volumes and normal backend
entrypoint are retained; no models/migrations/import changes were introduced.
The frontend dependency volume needs `npm ci` to install MapLibre before normal
application startup. Docker access remains denied, so builds/launch and required
live HTTP/SQL checks remain unverified. Current commands/evidence are in
`docs/collection-site-browsing-verification.md`; earlier evidence is in the
linked historical document. Checkboxes remain 8/23; activation does not complete
any outstanding live check.

# Tasks 1.2 and 1.3 runtime preparation

Recorded on 2026-10-09 (Europe/Vilnius). Implementation and verification files live in `/home/stitas/.local/share/viptop-isolated/bins-ui`; original application source and permanent infrastructure files remain untouched.

- Task 1.2: prepared `verification.compose.yaml` and its temporary copy at `/tmp/viptop-bins-ui-verification-qqbzy83v/compose.override.yaml`. Compose v5.6.0 resolved the app-only configuration. Inline checks confirmed isolated build/source paths, unique images/dependency volumes, localhost application ports, no PostgreSQL service/data mounts, no dependencies, and a direct Uvicorn entrypoint with no migration/import/reload startup. `configuration-evidence.json` records the sanitized result.
- Task 1.3: created [the manual procedure](/home/stitas/.local/share/viptop-isolated/bins-ui/docs/collection-site-browsing-verification.md), including runtime ownership, startup/cleanup, GET-only requests, bounded read-only SQL and operational continuity checks. Its offline configuration check passed; documented shell/Python syntax and whitespace checks passed.
- Task 1.3 used its explicit no-access branch. `docker ps` still reports Docker socket permission denied; `sudo -n docker ps` requires a password. No images were built and no new containers were started. Real database/network connectivity, new container identities/endpoints and import progress remain unmet live checks. Placeholder values used for configuration validation are labeled synthetic and must be replaced only after read-only runtime inspection.
- The original Vite, Uvicorn, importer and PostgreSQL PIDs/cgroups remained present. All 136 original tracked files matched the pre-session hashes. Ports 8001 and 5174 had no listeners at the final check.

The task checkboxes record configuration/documentation completion under that fallback; they do not attest to successful live verification. Future feature implementation and independent build work should continue in the isolated checkout. Resolve runtime access before starting the prepared verification applications; do not change socket permissions or operational services to obtain it.
