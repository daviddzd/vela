"""Visits of the logged-in caregiver (or physician): today's agenda, "Llegué" and "Terminé"."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.guards import ensure_own_assignment
from app.core.roles import CAREGIVER, PHYSICIAN
from app.services import operations as ops

router = APIRouter(prefix="/api/visits", tags=["visits"])
STAFF = (CAREGIVER, PHYSICIAN)


@router.get("/mine")
def my_visits(user: CurrentUser = Depends(require_role(*STAFF)), db: Session = Depends(tenant_db)) -> list[dict]:
    """Today's visits (Mexico City date), only the caregiver's own."""
    rows = db.execute(text("""
        SELECT a.assignment_id, r.request_id, r.patient_id, r.status, r.scheduled_for, a.planned_start, a.planned_end,
               a.travel_min::float AS travel_min, a.arrived_at, a.finished_at, s.name AS service_name, r.priority,
               pe.first_name || ' ' || pe.paternal_surname AS patient_name, d.name AS district_name
        FROM assignments a JOIN service_requests r USING (request_id) JOIN services s USING (service_id)
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        JOIN districts d ON d.district_id = pe.district_id
        WHERE a.caregiver_id = :c AND a.status = 'active'
          AND (r.scheduled_for AT TIME ZONE 'America/Mexico_City')::date
              = (now() AT TIME ZONE 'America/Mexico_City')::date
        ORDER BY r.scheduled_for"""), {"c": user.caregiver_id}).mappings().all()
    return [dict(r) for r in rows]


def _step(action, assignment_id: str, user: CurrentUser, db: Session) -> dict:
    ensure_own_assignment(db, user, assignment_id)
    patient_id = db.scalar(text("""SELECT r.patient_id FROM assignments a JOIN service_requests r USING (request_id)
                                   WHERE a.assignment_id = :a"""), {"a": assignment_id})
    # Home visit only with a valid home_care consent (CLAUDE.md rule 5), checked again at the door.
    if not ops.has_valid_consent(db, patient_id, "home_care"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Falta consentimiento de atención a domicilio.")
    try:
        action(db, user_id=user.user_id, institution_id=user.institution_id, assignment_id=assignment_id)
    except ops.InvalidState:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta visita no está en el paso correcto.")
    return {"assignment_id": assignment_id,
            "status": db.scalar(text("SELECT r.status FROM assignments a JOIN service_requests r USING (request_id) "
                                     "WHERE a.assignment_id = :a"), {"a": assignment_id})}


@router.post("/{assignment_id}/arrive")
def arrive(assignment_id: str, user: CurrentUser = Depends(require_role(*STAFF)),
           db: Session = Depends(tenant_db)) -> dict:
    return _step(ops.mark_arrived, assignment_id, user, db)


@router.post("/{assignment_id}/finish")
def finish(assignment_id: str, user: CurrentUser = Depends(require_role(*STAFF)),
           db: Session = Depends(tenant_db)) -> dict:
    return _step(ops.mark_finished, assignment_id, user, db)
