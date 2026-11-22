"""FastAPI dependencies: who is calling, what role they have, and a tenant-scoped DB session."""
from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import ALL_INSTITUTIONS, SessionLocal, tenant_session
from app.core.roles import OWNER
from app.core.security import decode_token  # cookie name: security.COOKIE_NAME ("vela_session")
from app.models.tables import User


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    role: str
    institution_id: str | None
    caregiver_id: str | None
    family_member_id: str | None
    display_name: str

    @property
    def tenant(self) -> str:
        """Value for app.institution_id: '*' only for the owner, otherwise the user's institution."""
        return ALL_INSTITUTIONS if self.role == OWNER else self.institution_id  # type: ignore[return-value]


def load_active_user(session: Session, claims: dict) -> CurrentUser | None:
    """Re-check the token against the database: the user must exist, be active, and still have the
    same role and institution as when the token was issued. Otherwise the session is no longer valid."""
    user = session.get(User, claims["sub"])
    if (user is None or not user.active or user.role != claims.get("role")
            or user.institution_id != claims.get("institution_id")):
        return None
    return CurrentUser(user.user_id, user.role, user.institution_id, user.caregiver_id,
                       user.family_member_id, user.display_name)


def current_user(vela_session: str | None = Cookie(default=None)) -> CurrentUser:
    """Read the session cookie and return the logged-in user, or answer 401."""
    claims = decode_token(vela_session) if vela_session else None
    if claims is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inicia sesión para continuar.")
    with SessionLocal() as session:  # users table is not under RLS
        user = load_active_user(session, claims)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tu sesión ya no es válida. Inicia sesión de nuevo.")
    return user


def require_role(*roles: str):
    """Dependency factory: only the listed roles may call the endpoint (else 403)."""
    def checker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permiso para esta acción.")
        return user
    return checker


def tenant_db(user: CurrentUser = Depends(current_user)) -> Iterator[Session]:
    """One transaction per request, scoped with SET LOCAL app.institution_id to the user's institution.

    TODO(step 3): physicians and caregivers currently see their whole institution. In step 3 they must
    only see their own patients and visits (filter by users.caregiver_id → assignments/care team).
    """
    with tenant_session(user.tenant) as session:
        yield session
