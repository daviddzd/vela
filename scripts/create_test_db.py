"""Create (or re-create) the TEST database `vela_test`, so pytest never writes into the demo database
(its audit trail, notices, sequences...). Same SQL, same seed and same migrations as the demo database.

    python scripts/create_test_db.py        # ~1 min; run once, and again after new migrations
    docker compose exec api pytest          # tests/conftest.py connects to vela_test, never to vela

Steps (all inside the containers, nothing is installed on the laptop):
  1. DROP + CREATE DATABASE vela_test (owner = the same table owner as the demo database)
  2. database/sql 001 → 002 (seed) → 003 → 005 → 004, exactly like infra/db-init.sh
  3. the same grants for vela_api as infra/db-init.sh (the role already exists: roles are per server)
  4. alembic upgrade head against vela_test
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DB = "vela_test"

GRANTS = """
GRANT USAGE ON SCHEMA public TO vela_api;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO vela_api;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO vela_api;
REVOKE UPDATE, DELETE ON audit_log FROM vela_api;
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO vela_api;
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public GRANT USAGE ON SEQUENCES TO vela_api;
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
"""


def run(cmd: list[str], stdin: str | None = None, quiet: bool = True) -> None:
    out = subprocess.run(cmd, input=stdin, text=True, cwd=ROOT, capture_output=quiet)
    if out.returncode:
        sys.exit(f"Falló: {' '.join(cmd[:6])}…\n{(out.stderr or '').strip()[-2000:]}")


def db_shell(script: str) -> None:
    run(["docker", "compose", "exec", "-T", "db", "sh", "-c", script])


def main() -> None:
    print(f"1/4 Creando la base {TEST_DB}…")
    db_shell(f'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -q '
             f'-c "DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)" -c "CREATE DATABASE {TEST_DB} OWNER \\"$POSTGRES_USER\\""')
    print("2/4 Esquema y semilla (database/sql)…")
    db_shell("cd /repo && for f in 001_schema 002_load_seed 003_views 005_postgis 004_row_level_security; do "
             f'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d {TEST_DB} -f database/sql/$f.sql || exit 1; done')
    print("3/4 Permisos de vela_api…")
    run(["docker", "compose", "exec", "-T", "db", "sh", "-c",
         f'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d {TEST_DB} -v owner="$POSTGRES_USER"'], stdin=GRANTS)
    print("4/4 Migraciones (alembic)…")
    run(["docker", "compose", "run", "--rm", "--no-deps", "migrate", "sh", "-c",
         f'OWNER_DATABASE_URL="${{OWNER_DATABASE_URL%/*}}/{TEST_DB}" alembic upgrade head'])
    print(f"Listo: {TEST_DB} creada. Corre las pruebas con  docker compose exec api pytest")


if __name__ == "__main__":
    main()
