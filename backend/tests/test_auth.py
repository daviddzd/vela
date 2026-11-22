"""Login with the seed's bcrypt hashes, role → first screen, and session re-check in the database."""
import pytest
from sqlalchemy import text

from app.core.deps import load_active_user
from app.core.security import COOKIE_NAME, decode_token
from tests.conftest import DEMO_USERS, login


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["db"] == "ok"


@pytest.mark.parametrize("email", DEMO_USERS)
def test_demo_users_log_in_to_their_home(client, email):
    role, home = DEMO_USERS[email]
    r = login(client, email)
    assert r.status_code == 200, r.text
    assert r.json()["role"] == role and r.json()["home"] == home
    assert home in r.json()["screens"]
    # Cookie is httpOnly and the JWT carries user_id, role and institution_id.
    set_cookie = r.headers["set-cookie"].lower()
    assert "httponly" in set_cookie and "samesite=lax" in set_cookie
    claims = decode_token(client.cookies[COOKIE_NAME])
    assert claims["sub"] == r.json()["user_id"] and claims["role"] == role
    assert "institution_id" in claims
    assert client.get("/api/auth/me").json()["home"] == home


def test_wrong_password_is_rejected(client):
    r = login(client, "coordinacion.a@ejemplo.test", "otra-cosa")
    assert r.status_code == 401
    assert COOKIE_NAME not in client.cookies


def test_failed_logins_are_rate_limited(client):
    for _ in range(5):
        assert login(client, "nadie@ejemplo.test", "x").status_code == 401
    assert login(client, "nadie@ejemplo.test", "x").status_code == 429


def test_no_cookie_means_401(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/patients/PAC-0001").status_code == 401


def test_deactivated_user_loses_the_session(client, rollback_session):
    """The token alone is not enough: the user must still be active in the database.
    The UPDATE is rolled back by the fixture, so the seed stays intact."""
    login(client, "coordinacion.a@ejemplo.test")
    claims = decode_token(client.cookies[COOKIE_NAME])
    assert load_active_user(rollback_session, claims) is not None
    rollback_session.execute(text("UPDATE users SET active = false WHERE user_id = :u"), {"u": claims["sub"]})
    rollback_session.expire_all()
    assert load_active_user(rollback_session, claims) is None


def test_role_change_invalidates_token(client, rollback_session):
    login(client, "cui-003@ejemplo.test")
    claims = decode_token(client.cookies[COOKIE_NAME])
    forged = {**claims, "role": "coordinator"}  # token claims a role the DB does not confirm
    assert load_active_user(rollback_session, forged) is None


def test_token_survives_the_clock_going_back(monkeypatch):
    """WSL2 moves the clock back ~3 s when it re-syncs: a token issued "in the future" must still be valid."""
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.core import security
    from app.core.config import get_settings
    future = datetime.now(timezone.utc) + timedelta(seconds=5)
    token = jwt.encode({"sub": "USR-001", "role": "owner", "institution_id": None, "iat": future,
                        "exp": future + timedelta(hours=1)}, get_settings().jwt_secret, algorithm=security.ALGORITHM)
    assert security.decode_token(token)["sub"] == "USR-001"
    expired = jwt.encode({"sub": "USR-001", "role": "owner", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
                         get_settings().jwt_secret, algorithm=security.ALGORITHM)
    assert security.decode_token(expired) is None                      # a really expired token is still refused
