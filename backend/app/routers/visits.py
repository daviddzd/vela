"""Visits of the logged-in caregiver (or physician): today's agenda, "Llegué" and "Terminé"."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.guards import ensure_own_assignment
from app.core.config import MEXICO_CITY
from app.core.roles import CAREGIVER, PHYSICIAN
from app.services import operations as ops

router = APIRouter(prefix="/api/visits", tags=["visits"])
STAFF = (CAREGIVER, PHYSICIAN)


@router.get("/mine")
def my_visits(user: CurrentUser = Depends(require_role(*STAFF)), db: Session = Depends(tenant_db)) -> list[dict]:
    """Today's visits (Mexico City date), only the caregiver's own. With a relay (two people, dispatcher.relay_options)
    each person sees their own part: `relay_role` 'first' (someone takes over at relay_at) or 'relay' (takes over at
    relay_at), the other person's name, and `step`, the button that applies to THEM (arrive / finish / done)."""
    rows = db.execute(text("""
        SELECT a.assignment_id, r.request_id, r.patient_id, r.status, r.scheduled_for, a.planned_start, a.planned_end,
               a.travel_min::float AS travel_min, a.arrived_at, a.finished_at, s.name AS service_name, r.priority,
               pe.first_name || ' ' || pe.paternal_surname AS patient_name, d.name AS district_name,
               CASE WHEN o.assignment_id IS NULL THEN NULL WHEN a.leg = 1 THEN 'first' ELSE 'relay' END AS relay_role,
               oc.first_name || ' ' || oc.paternal_surname AS relay_partner_name,
               CASE WHEN o.assignment_id IS NULL THEN NULL WHEN a.leg = 1 THEN a.planned_end ELSE o.planned_end END AS relay_at,
               CASE WHEN a.leg = 2 THEN o.planned_end ELSE r.scheduled_for END
                   - :early * interval '1 minute' AS arrive_from,         -- "Llegué" opens 60 min before
               coalesce(round(extract(epoch FROM a.planned_end - (a.planned_start + a.travel_min * interval '1 minute')) / 60),
                        s.duration_min)::int AS expected_min,            -- how long THIS person's part lasts
               CASE WHEN a.finished_at IS NOT NULL OR r.status IN ('completed','closed') THEN 'done'
                    WHEN a.arrived_at IS NOT NULL THEN 'finish'
                    WHEN a.leg = 2 AND r.status <> 'in_progress' THEN 'wait'      -- the first person has not arrived
                    WHEN a.leg = 1 AND r.status <> 'assigned' THEN 'wait'
                    ELSE 'arrive' END AS step
        FROM assignments a JOIN service_requests r USING (request_id) JOIN services s USING (service_id)
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        JOIN districts d ON d.district_id = pe.district_id
        LEFT JOIN assignments o ON o.request_id = a.request_id AND o.status = 'active' AND o.leg <> a.leg
        LEFT JOIN caregivers oc ON oc.caregiver_id = o.caregiver_id
        WHERE a.caregiver_id = :c AND a.status = 'active'
          AND ((r.scheduled_for AT TIME ZONE 'America/Mexico_City')::date = (now() AT TIME ZONE 'America/Mexico_City')::date
               OR (a.planned_start AT TIME ZONE 'America/Mexico_City')::date = (now() AT TIME ZONE 'America/Mexico_City')::date)
        ORDER BY coalesce(a.planned_start, r.scheduled_for)"""),
        {"c": user.caregiver_id, "early": ops.ARRIVE_EARLY_MINUTES}).mappings().all()
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
    ensure_own_assignment(db, user, assignment_id)
    opens = ops.arrival_opens_at(db, assignment_id)
    if opens and ops.now() < opens:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Podrás registrar tu llegada desde las "
                            f"{opens.astimezone(MEXICO_CITY):%H:%M} ({ops.ARRIVE_EARLY_MINUTES} min antes de la visita).")
    return _step(ops.mark_arrived, assignment_id, user, db)


@router.post("/{assignment_id}/finish", response_model=None)
def finish(assignment_id: str, confirm: bool = False, user: CurrentUser = Depends(require_role(*STAFF)),
           db: Session = Depends(tenant_db)) -> dict | JSONResponse:
    """Before half of the visit the screen asks "¿Seguro? La visita dura 30 min."; it sends confirm=true."""
    ensure_own_assignment(db, user, assignment_id)
    expected = ops.early_finish(db, assignment_id)
    if expected and not confirm:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={
            "detail": f"¿Seguro? La visita dura {expected} min.", "needs_confirmation": True, "expected_min": expected})
    return _step(ops.mark_finished, assignment_id, user, db)
