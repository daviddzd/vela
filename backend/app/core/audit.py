"""Audit trail (CLAUDE.md rule 10): patient reads, assignment changes, approvals, contingency
decisions and blocked cross-tenant attempts go to `audit_log`."""
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.tables import AuditLog


def audit(session: Session, *, user_id: str | None, institution_id: str | None, action: str,
          entity: str, entity_id: str | None = None, allowed: bool = True,
          detail: dict | None = None) -> None:
    """Add an audit row to the caller's transaction (saved only if that transaction commits)."""
    session.add(AuditLog(user_id=user_id, institution_id=institution_id, action=action, entity=entity,
                         entity_id=entity_id, allowed=allowed, detail=detail))
    session.flush()   # write it now, so the trail keeps the real order of events


def audit_now(**kwargs) -> None:
    """Write an audit row in its OWN transaction and commit it at once.

    Used for denied actions: the request is about to fail (403/401) and its own transaction is
    rolled back, but the attempt must stay on record.
    """
    with SessionLocal() as session, session.begin():
        audit(session, **kwargs)
