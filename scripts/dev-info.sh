#!/usr/bin/env bash
# Print the URLs, database address and data directory of this checkout's running
# Docker Compose stack. Run from anywhere inside the checkout; needs only the Docker CLI.
set -u

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not reachable." >&2
  exit 1
fi

# The first running container identifies the project.
backend_id=$(docker compose ps -q backend 2>/dev/null | head -n 1)
if [ -z "$backend_id" ] || [ "$(docker inspect --format '{{.State.Running}}' "$backend_id")" != "true" ]; then
  echo "The stack for $(basename "$PWD") is not running. Start it with: docker compose up -d" >&2
  exit 1
fi

project=$(docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' "$backend_id")

# Mode: worktree mode when COMPOSE_FILE (environment, else .env) includes the worktree file.
compose_file=${COMPOSE_FILE:-}
if [ -z "$compose_file" ] && [ -f .env ]; then
  compose_file=$(sed -n 's/^COMPOSE_FILE=//p' .env | tail -n 1)
fi
case "$compose_file" in
  *docker-compose.worktree.yml*) mode="worktree (Docker-chosen ports unless a port variable is set)" ;;
  *) mode="default (fixed ports unless a port variable is set)" ;;
esac

# Host port of a service, empty when the service publishes none.
host_port() {
  docker compose port "$1" "$2" 2>/dev/null | head -n 1 | sed 's/.*://'
}

frontend_port=$(host_port frontend 5173)
backend_port=$(host_port backend 8000)
db_port=$(host_port db 5432)

db_id=$(docker compose ps -q db 2>/dev/null | head -n 1)
db_user=; db_name=
if [ -n "$db_id" ]; then
  db_user=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$db_id" | sed -n 's/^POSTGRES_USER=//p')
  db_name=$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$db_id" | sed -n 's/^POSTGRES_DB=//p')
fi

data_dir=$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Source}}{{end}}{{end}}' "$backend_id")

url() { # name port suffix
  if [ -n "$2" ]; then echo "  $1 http://localhost:$2$3"; else echo "  $1 (no host port published)"; fi
}

echo "Project:   $project"
echo "Mode:      $mode"
url "Frontend: " "$frontend_port" ""
url "Backend:  " "$backend_port" ""
url "API docs: " "$backend_port" "/docs"
if [ -n "$db_port" ]; then
  echo "  Database: localhost:$db_port (user ${db_user:-?}, database ${db_name:-?})"
else
  echo "  Database: (no host port published)"
fi
echo "Data dir:  ${data_dir:-unknown}"
