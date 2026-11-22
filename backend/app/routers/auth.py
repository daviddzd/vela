"""Login, logout and "who am I"."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core import ratelimit
from app.core.audit import audit
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.deps import CurrentUser, current_user
from app.core.roles import HOME_BY_ROLE, screens_for
from app.core.security import COOKIE_NAME, create_token, verify_password
from app.models.tables import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class MeOut(BaseModel):
    user_id: str
    display_name: str
    role: str
    institution_id: str | None
    home: str            # first screen after login
    screens: list[str]   # screens this role may open


def me_out(user: CurrentUser) -> MeOut:
    return MeOut(user_id=user.user_id, display_name=user.display_name, role=user.role,
                 institution_id=user.institution_id, home=HOME_BY_ROLE[user.role],
                 screens=screens_for(user.role))


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response) -> MeOut:
    settings = get_settings()
    ip = ratelimit.client_ip(request)
    if ratelimit.is_blocked(ip, settings.login_attempts_per_minute):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Demasiados intentos. Espera un minuto e inténtalo de nuevo.")
    email = body.email.strip().lower()
    with SessionLocal() as session, session.begin():
        user = session.scalar(select(User).where(func.lower(User.email) == email))
        ok = user is not None and user.active and verify_password(body.password, user.password_hash)
        audit(session, user_id=user.user_id if user else None,
              institution_id=user.institution_id if user else None,
              action="login" if ok else "login_failed", entity="user",
              entity_id=user.user_id if user else None, allowed=ok,
              detail=None if ok else {"email": email, "ip": ip})
    if not ok:
        ratelimit.record_failure(ip)
        # Same message for unknown email and wrong password: do not reveal which accounts exist.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos.")
    response.set_cookie(COOKIE_NAME, create_token(user.user_id, user.role, user.institution_id),
                        max_age=settings.jwt_hours * 3600, httponly=True,
                        secure=settings.cookie_secure, samesite="lax", path="/")
    return me_out(CurrentUser(user.user_id, user.role, user.institution_id, user.caregiver_id,
                              user.family_member_id, user.display_name))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser = Depends(current_user)) -> MeOut:
    return me_out(user)
