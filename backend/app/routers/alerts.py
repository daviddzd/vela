"""Alerts that need a person to act (app/services/alerts_followup.py).

- POST /api/alerts/{id}/review: coordination (or Dirección) contacted the family after a voice note that ONLY the
  classifier rated as emergency: "Contactada: era emergencia" / "Contactada: no era emergencia".
- GET  /api/alerts/escalated: Dirección sees what was escalated (review alerts nobody answered in time, and
  emergencies confirmed by coordination), from every institution.
- POST /api/alerts/{id}/acknowledge: Dirección says "Enterado".
Everything is audited.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.events import publish
from app.core.roles import COORDINATOR, OWNER
from app.services import alerts_followup

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class ReviewIn(BaseModel):
    outcome: str        # emergency | not_emergency


@router.post("/{alert_id}/review")
def review(alert_id: str, body: ReviewIn, user: CurrentUser = Depends(require_role(COORDINATOR, OWNER)),
           db: Session = Depends(tenant_db)) -> dict:
    if body.outcome not in ("emergency", "not_emergency"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Resultado no válido.")
    try:
        return alerts_followup.review(db, alert_id=alert_id, outcome=body.outcome, user_id=user.user_id)
    except alerts_followup.NotOpen:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta alerta ya se atendió.")


@router.get("/escalated")
def escalated(user: CurrentUser = Depends(require_role(OWNER)), db: Session = Depends(tenant_db)) -> list[dict]:
    rows = db.execute(text("""
        SELECT a.alert_id, a.type, a.institution_id, i.name AS institution_name, a.message, a.created_at,
               a.escalated_at, a.status
        FROM alerts a LEFT JOIN institutions i USING (institution_id)
        WHERE a.escalated_at IS NOT NULL AND a.status = 'open'
        ORDER BY a.escalated_at DESC""")).mappings().all()
    return [dict(r) for r in rows]


@router.post("/{alert_id}/acknowledge")
def acknowledge(alert_id: str, user: CurrentUser = Depends(require_role(OWNER)), db: Session = Depends(tenant_db)) -> dict:
    """Dirección has seen an escalated CONFIRMED emergency. A review alert still needs the family contacted, so it
    stays open until someone records the outcome (POST /review)."""
    inst = db.scalar(text("""UPDATE alerts SET status = 'acknowledged', handled_by = :u
                             WHERE alert_id = :a AND escalated_at IS NOT NULL AND status = 'open' AND type = 'emergency'
                             RETURNING institution_id"""), {"a": alert_id, "u": user.user_id})
    if inst is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta alerta ya se atendió o necesita registrar el contacto con la familia.")
    audit(db, user_id=user.user_id, institution_id=inst, action="alert_acknowledged", entity="alert", entity_id=alert_id)
    publish(db, "alert.updated", inst, alert_id=alert_id)
    return {"alert_id": alert_id, "status": "acknowledged"}
