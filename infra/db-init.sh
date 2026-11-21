#!/bin/bash
# Runs once, the first time the db container starts with an empty volume.
set -euo pipefail
cd /repo
run() { psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"; }
for f in 001_schema 002_load_seed 003_views 005_postgis 004_row_level_security; do
  echo "== $f"; run -f "database/sql/$f.sql"
done
# API role: not the table owner, so row-level security applies to it.
run <<SQL
CREATE ROLE vela_api LOGIN PASSWORD '${VELA_API_DB_PASSWORD}';
GRANT USAGE ON SCHEMA public TO vela_api;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO vela_api;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO vela_api;
REVOKE UPDATE, DELETE ON audit_log FROM vela_api;
SQL
