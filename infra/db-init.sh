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
-- Tables and sequences that future Alembic migrations create (as this same owner role)
-- automatically get the same grants for vela_api. RLS for new tenant tables is still added
-- explicitly in each migration.
ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE ON TABLES TO vela_api;
ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
  GRANT USAGE ON SEQUENCES TO vela_api;
-- Functions are not executable by everyone by default; migrations GRANT EXECUTE one by one.
ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
  REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
SQL
