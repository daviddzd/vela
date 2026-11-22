"""Passwords (bcrypt) and session tokens (JWT stored in an httpOnly cookie)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

COOKIE_NAME = "vela_session"
ALGORITHM = "HS256"
# Tolerance for clock differences when checking "issued at" / "expires". Measured on the demo laptop (WSL2):
# the clock jumps BACK about 3 s every ~30 s when it re-syncs with Windows, so a token made just before a jump
# looked "issued in the future" and was rejected (intermittent 401 right after logging in). 60 s is plenty.
CLOCK_LEEWAY_SECONDS = 60


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against a bcrypt hash. The seed uses `$2a$` hashes made by pgcrypto,
    which the bcrypt library accepts as they are."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:  # malformed hash
        return False


def create_token(user_id: str, role: str, institution_id: str | None) -> str:
    """Signed token with who the user is. It is NOT trusted alone: every request re-checks the
    user in the database (app/core/deps.py) so a deactivated user is locked out immediately."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "role": role,
        "institution_id": institution_id,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_hours),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Return the claims, or None if the token is invalid or expired."""
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM], leeway=CLOCK_LEEWAY_SECONDS,
                          options={"require": ["sub", "role", "exp"]})
    except jwt.PyJWTError:
        return None
