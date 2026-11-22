"""Shared test fixtures. Tests run inside Docker against a SEPARATE database, `vela_test`, created from the same
SQL, seed and migrations as the demo database (python scripts/create_test_db.py):

    docker compose exec api pytest

So the tests never write into the demo database: its audit trail only shows real use (rehearsals, defense).
Rule: tests leave no garbage. Anything they change runs inside a transaction that is rolled back.
Only the audit_log rows produced by the API itself remain in vela_test (that trail is append-only on purpose).
"""
import os

# Must run BEFORE the app is imported: the engine reads DATABASE_URL once. Same user (vela_api), other database.
TEST_DB = os.environ.get("TEST_DATABASE_NAME", "vela_test")
os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/" + TEST_DB

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core import ratelimit  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402

DEMO_PASSWORD = "Demo2026!"  # public demo password, synthetic users only

# The 5 test users from README.md → expected first screen.
DEMO_USERS = {
    "owner@ejemplo.test": ("owner", "/panorama"),
    "coordinacion.a@ejemplo.test": ("coordinator", "/tablero"),
    "cui-001@ejemplo.test": ("physician", "/reportes-voz"),
    "cui-003@ejemplo.test": ("caregiver", "/mis-visitas"),
    "fam-0001@ejemplo.test": ("family", "/familia"),
}


@pytest.fixture(scope="session", autouse=True)
def _only_the_test_database() -> None:
    """Stop at once if the tests are not connected to the test database (never touch the demo data)."""
    try:
        with SessionLocal() as s:
            name = s.scalar(text("SELECT current_database()"))
    except Exception as exc:  # noqa: BLE001
        pytest.exit(f"No hay base de pruebas '{TEST_DB}'. Créala con: python scripts/create_test_db.py ({exc.__class__.__name__})")
    if name != TEST_DB:
        pytest.exit(f"Las pruebas están conectadas a '{name}', no a '{TEST_DB}'. No se corre nada.")


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> None:
    ratelimit.reset()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str, password: str = DEMO_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


@pytest.fixture
def rollback_session() -> Iterator[Session]:
    """A vela_api session whose changes are always rolled back at the end of the test."""
    session = SessionLocal()
    session.begin()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---- step 3: tests that create data -------------------------------------------------------------
# The API's tenant session is replaced by one bound to a single connection whose outer transaction is
# ROLLED BACK at the end of the test. Each request runs inside a SAVEPOINT of that transaction, so the
# API behaves normally (commit = release savepoint) but nothing survives the test. Only rows written by
# audit_now() (denied attempts, own connection) remain, as agreed.
from fastapi import Depends  # noqa: E402
from sqlalchemy.orm import Session as _Session  # noqa: E402

from app.core.db import engine, set_tenant  # noqa: E402
from app.core.deps import CurrentUser, current_user, tenant_db  # noqa: E402


@pytest.fixture
def db_conn():
    conn = engine.connect()
    outer = conn.begin()
    try:
        yield conn
    finally:
        outer.rollback()
        conn.close()


def free_caregiver(s, caregiver_id: str) -> None:
    """Set aside the caregiver's LIVE pending visits (created by the worker from today's care plans) inside the
    test transaction, so a test that books a window at a real hour does not collide with them. Rolled back."""
    s.execute(text("""UPDATE assignments SET status = 'reassigned' WHERE caregiver_id = :c AND status = 'active'
                      AND planned_start IS NOT NULL AND arrived_at IS NULL"""), {"c": caregiver_id})


def session_on(conn, institution_id: str | None) -> _Session:
    """A session on the test connection, scoped to a tenant (changes are rolled back with the test)."""
    s = _Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    if institution_id is not None:
        set_tenant(s, institution_id)
    return s


@pytest.fixture
def tx_client(db_conn):
    def override(user: CurrentUser = Depends(current_user)):
        s = _Session(bind=db_conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        with s.begin():
            set_tenant(s, user.tenant)
            yield s
        s.close()

    app.dependency_overrides[tenant_db] = override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(tenant_db, None)
