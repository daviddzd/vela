#!/usr/bin/env bash
# Backup of the demo database (team decision 25 Nov 2026): before the defense and after every rehearsal.
#
#   bash scripts/backup_db.sh            # -> backups/vela_YYYY-MM-DD_HHMM.dump  (backups/ is git-ignored)
#   bash scripts/backup_db.sh ensayo1    # -> backups/vela_YYYY-MM-DD_HHMM_ensayo1.dump
#
# pg_dump in custom format (-Fc: compressed, restorable with scripts/restore_db.sh), run inside the db container as the
# table owner. It contains everything: seed, live operation, audit trail. It contains synthetic data only, but treat it as
# private anyway: never commit it.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
stamp="$(date +%Y-%m-%d_%H%M)"
name="vela_${stamp}${1:+_$1}.dump"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backups/$name"
size="$(du -h "backups/$name" | cut -f1)"
echo "Respaldo listo: backups/$name ($size)"
echo "Para restaurarlo: bash scripts/restore_db.sh backups/$name"
