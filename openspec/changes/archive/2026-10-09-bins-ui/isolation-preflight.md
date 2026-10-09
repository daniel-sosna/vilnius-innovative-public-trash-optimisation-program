# Task 1.1 isolation preflight

Observed on 2026-10-09 (Europe/Vilnius). Only task 1.1 was performed.

## Checkout

- Operational repository: `/home/stitas/Projects/vilnius-innovative-public-trash-optimisation-program`.
- Isolated implementation repository: `/home/stitas/.local/share/viptop-isolated/bins-ui`.
- Branch: `bins-ui`; starting commit: `65ad94353bd37a6d61b3315aebdb8ca063649bb1`.
- Created with `git clone --no-hardlinks --branch bins-ui` from the operational repository. This is an independent clone, so it does not add worktree metadata to the operational repository.
- Copied the untracked `openspec/changes/bins-ui/` planning artifacts into the clone. Verified its OpenSpec root with `openspec list --json`.
- All 136 tracked files initially matched byte-for-byte and had distinct filesystem inodes. The clone contains no symlinks to operational files, copied root `.env`, `frontend/node_modules` or `backend/.venv`.
- Future application/package edits belong in the isolated repository. Planning evidence and task tracking remain available in both repositories; design decision 7 explicitly allows planning progress outside watched source.

## Runtime evidence

Docker API access remains unavailable:

```text
docker context show: default
docker context inspect default: unix:///var/run/docker.sock
docker ps: permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
sudo -n docker ps: sudo: a password is required
```

No socket permissions, daemon configuration or group membership were changed. Readable process metadata provided an independent read-only view through `ps`, `/proc/<pid>/cgroup`, `/proc/<pid>/mountinfo` and `/proc/<pid>/net/route`. Process working-directory symlink access was denied.

| Process | Host PID | Container ID from cgroup |
|---|---|---|
| Vite (`--host 0.0.0.0`) | 493715 | `9839af4607ca7fe76252728ac5d9907b73e8e03c962180fba402c19698de47c5` |
| Uvicorn (`--reload`) | 493931 | `88e61d3936a9fbbaf48c5794c503a6f2f9578a3d2b2a2b2ab3066abc576ecdd5` |
| Importer (`--max-sites 0 --max-tiles 0 --workers 8`) | 678068 | Same backend container |
| PostgreSQL | 493638 | `2e2c4be9479ed1c17b856d1b78a48571702cad81ad2f786d9992e98e25d8dc44` |

The live mount tables show:

| Container | Host source | Container destination |
|---|---|---|
| Frontend | Operational repository `frontend/` | `/app` |
| Frontend | `/root/var/lib/docker/volumes/vilnius-innovative-public-trash-optimisation-program_frontend_node_modules/_data` | `/app/node_modules` |
| Backend/importer | Operational repository `backend/` | `/app` |
| Backend/importer | `/root/var/lib/docker/volumes/vilnius-innovative-public-trash-optimisation-program_backend_venv/_data` | `/app/.venv` |
| PostgreSQL | `/root/var/lib/docker/volumes/vilnius-innovative-public-trash-optimisation-program_postgres_data/_data` | `/var/lib/postgresql/data` |

Other host filesystem mounts in these containers were their Docker-managed hostname, hosts and resolver files. The isolated repository's resolved path is outside every inspected host filesystem mount. Its application files have distinct inodes and no symlink aliases to the watched source, so editing them cannot change the files watched by the operational Vite/Uvicorn processes.

All four inspected processes expose an `eth0` route for `172.28.0.0/16` with gateway `172.28.0.1`. Host listeners exist on ports 5173, 8000 and 5432 (IPv4 and IPv6). These observations do not establish the Docker network's name, service DNS aliases, API-reported container names or safe access for starting verification containers. No database connection/query was attempted.

## Result and remaining limits

Task 1.1's isolated checkout and source-mount checks passed using readable process mount tables despite unavailable Docker API access. The original application source, environment and permanent Compose configuration remain unchanged. Existing application/import/database processes remained present after the preflight. Process presence confirms continuity only; import progress and database health were not queried.

Tasks 1.2 and 1.3 remain pending: no Compose override, verification containers, dependency installation, migrations, import invocation or database writes were performed. Docker network identity and container-management access must be established before any separate runtime startup. Do not transfer application changes into the original source mounts while they could interrupt import.

To repeat runtime inspection, first obtain current PIDs with `ps -eo pid,ppid,comm,args`, then read their `cgroup`, `mountinfo` and `net/route` files; the PIDs above are evidence for this observation, not permanent identifiers. `ss -ltnp '( sport = :5173 or sport = :8000 or sport = :5432 )'` repeats the occupied-port check without opening application or database connections.
