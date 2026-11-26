#!/usr/bin/env bash
# Runs at Windows sign-in (scheduled task "Enlaza - arranque", scripts/windows/install_startup_task.ps1).
#
# Why: Docker Desktop restarts the containers as soon as it starts, often BEFORE Ubuntu (WSL) is ready. Then the
# bind mounts from Ubuntu come out wrong: a container mounting a single file (db: infra/db-init.sh, proxy:
# infra/Caddyfile) fails to start ("not a directory"), and a container mounting folders (api, worker: config/,
# data/business/…) starts EMPTY and still looks "healthy" — without the emergency rules. `restart: unless-stopped`
# does not help: Docker does not retry a container that could not be created.
#
# This script waits for Docker, checks that every container sees its files, restarts the ones that do not, and
# waits for /api/health. Log: ~/.local/state/enlaza/arranque.log. Safe to run by hand at any time:
#   bash scripts/autostart.sh
set -uo pipefail
cd "$(dirname "$0")/.."
LOG_DIR="$HOME/.local/state/enlaza"; mkdir -p "$LOG_DIR"; LOG="$LOG_DIR/arranque.log"
exec > >(tee -a "$LOG") 2>&1
say() { echo "$(date '+%F %T') $*"; }

# A file each service must see; if it is missing, the mount came out wrong.
declare -A MUST_SEE=(
  [db]="/repo/docker-compose.yml /docker-entrypoint-initdb.d/10-init.sh"
  [api]="/config/emergency_rules.yaml /config/simulation.yaml /data/business/assumptions.csv /data/voice/triage_phrases.csv /simulation/results/summary.csv"
  [worker]="/config/emergency_rules.yaml /config/simulation.yaml"
  [voice]="/repo/docker-compose.yml /repo/config/emergency_rules.yaml"
  [proxy]="/etc/caddy/Caddyfile"
)

say "== Arranque de Enlaza"
for i in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 5; done
docker info >/dev/null 2>&1 || { say "FALLA: Docker no respondió en 5 minutos"; exit 1; }
say "Docker listo"

for attempt in 1 2 3; do
  docker compose up -d >/dev/null 2>&1   # creates/starts whatever is not running (db, proxy after a failed mount)
  bad=()
  for svc in "${!MUST_SEE[@]}"; do
    for f in ${MUST_SEE[$svc]}; do
      if ! docker compose exec -T "$svc" test -s "$f" 2>/dev/null; then bad+=("$svc"); break; fi
    done
  done
  [ ${#bad[@]} -eq 0 ] && { say "Montajes bien en todos los servicios (intento $attempt)"; break; }
  say "Montajes vacíos o servicio caído: ${bad[*]} → se reinician (intento $attempt)"
  docker compose restart "${bad[@]}" >/dev/null 2>&1
  sleep 10
done

for i in $(seq 1 36); do
  h=$(curl -s -m 5 http://localhost:8080/api/health)
  if echo "$h" | grep -q '"realtime":"ok"'; then say "App lista: $h"; exit 0; fi
  sleep 5
done
say "FALLA: /api/health no respondió bien en 3 minutos: ${h:-sin respuesta}"
exit 1
