"""Shared test fixtures. Tests run against the real database inside Docker:

    docker compose exec api pytest

Rule: tests leave no garbage. Anything they change runs inside a transaction that is rolled back.
Only the audit_log rows produced by the API itself remain (that trail is append-only on purpose).
"""
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import ratelimit
from app.core.db import SessionLocal
from app.main import app

DEMO_PASSWORD = "Demo2026!"  # public demo password, synthetic users only

# The 5 test users from README.md → expected first screen.
DEMO_USERS = {
    "owner@ejemplo.test": ("owner", "/panorama"),
    "coordinacion.a@ejemplo.test": ("coordinator", "/tablero"),
    "cui-001@ejemplo.test": ("physician", "/reportes-voz"),
    "cui-003@ejemplo.test": ("caregiver", "/mis-visitas"),
    "fam-0001@ejemplo.test": ("family", "/familia"),
}


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
