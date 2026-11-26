#!/usr/bin/env bash
# Restore a backup made with scripts/backup_db.sh. REPLACES everything in the demo database.
#
#   bash scripts/restore_db.sh backups/vela_2026-11-30_1800.dump
#
# Stops api and worker (nobody writes while restoring), runs pg_restore --clean as the table owner, starts them again and
# runs verify_db.py. It asks for confirmation first.
set -euo pipefail
cd "$(dirname "$0")/.."
file="${1:-}"
if [[ -z "$file" || ! -f "$file" ]]; then
  echo "Uso: bash scripts/restore_db.sh backups/<archivo>.dump"; ls -1t backups/*.dump 2>/dev/null | head -5; exit 1
fi
read -r -p "Esto REEMPLAZA la base de la demo con $file. ¿Continuar? (escribe sí): " ok
[[ "$ok" == "sí" || "$ok" == "si" ]] || { echo "Cancelado."; exit 1; }
docker compose stop api worker
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --role="$POSTGRES_USER"' < "$file"
docker compose start api worker
python3 scripts/verify_db.py
echo "Restaurado desde $file."
