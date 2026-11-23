"""Family screen: their patient's next visit, recent visits to confirm, and request history."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.guards import deny, family_patient_id, not_found_or_cross_tenant
from app.core.roles import FAMILY
from app.services import operations as ops

router = APIRouter(prefix="/api/family", tags=["family"])

VISIT_SQL = """
    SELECT r.request_id, r.status, r.status_reason, r.scheduled_for, r.priority, s.name AS service_name,
           a.assignment_id, a.arrived_at, CASE WHEN b.assignment_id IS NULL THEN a.finished_at ELSE b.finished_at END
           AS finished_at, a.family_confirmed, c.first_name || ' ' || c.paternal_surname AS caregiver_name,
           rc.first_name || ' ' || rc.paternal_surname AS relay_caregiver_name,
           CASE WHEN b.assignment_id IS NOT NULL THEN a.planned_end END AS relay_at
    FROM service_requests r JOIN services s USING (service_id)
    LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active' AND a.leg = 1
    LEFT JOIN caregivers c ON c.caregiver_id = a.caregiver_id
    LEFT JOIN assignments b ON b.request_id = r.request_id AND b.status = 'active' AND b.leg = 2     -- relay
    LEFT JOIN caregivers rc ON rc.caregiver_id = b.caregiver_id
    WHERE r.patient_id = :p {where} ORDER BY {order} LIMIT {limit}"""


@router.get("/overview")
def overview(user: CurrentUser = Depends(require_role(FAMILY)), db: Session = Depends(tenant_db)) -> dict:
    p = family_patient_id(db, user)
    info = db.execute(text("""
        SELECT pa.patient_id, pe.first_name || ' ' || pe.paternal_surname AS patient_name,
               fm.can_request_services
        FROM patients pa JOIN persons pe USING (person_id) JOIN family_members fm ON fm.patient_id = pa.patient_id
        WHERE fm.family_member_id = :f"""), {"f": user.family_member_id}).mappings().one()
    upcoming = db.execute(text(VISIT_SQL.format(
        where="AND r.status IN ('validated','queued','assigned','in_progress') AND r.scheduled_for > now() - interval '12 hours'",
        order="r.scheduled_for", limit=5)), {"p": p}).mappings().all()
    to_confirm = db.execute(text(VISIT_SQL.format(
        where="AND r.status = 'completed' AND NOT a.family_confirmed", order="r.scheduled_for DESC", limit=5)),
        {"p": p}).mappings().all()
    recent = db.execute(text(VISIT_SQL.format(where="", order="r.created_at DESC", limit=5)), {"p": p}).mappings().all()
    notices = db.execute(text("""SELECT message, created_at FROM family_notices WHERE patient_id = :p
                                 AND created_at > now() - interval '3 days' ORDER BY created_at DESC LIMIT 3"""),
                         {"p": p}).mappings().all()
    return {**info, "home_care_consent": ops.has_valid_consent(db, p, "home_care"),
            "notices": [dict(n) for n in notices],
            "next_visit": dict(upcoming[0]) if upcoming else None,
            "upcoming": [dict(r) for r in upcoming], "to_confirm": [dict(r) for r in to_confirm],
            "recent_requests": [dict(r) for r in recent]}


@router.post("/visits/{assignment_id}/confirm")
def confirm(assignment_id: str, user: CurrentUser = Depends(require_role(FAMILY)),
            db: Session = Depends(tenant_db)) -> dict:
    patient_id = db.scalar(text("""SELECT r.patient_id FROM assignments a JOIN service_requests r USING (request_id)
                                   WHERE a.assignment_id = :a"""), {"a": assignment_id})
    if patient_id is None:
        raise not_found_or_cross_tenant(db, user, "assignment", assignment_id)
    if patient_id != family_patient_id(db, user):
        raise deny(user, "blocked_out_of_scope", "assignment", assignment_id,
                   "Esta visita no es de tu familiar. El intento quedó registrado.")
    try:
        ops.confirm_visit(db, user_id=user.user_id, institution_id=user.institution_id, assignment_id=assignment_id)
    except ops.InvalidState:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta visita todavía no se puede confirmar.")
    return {"assignment_id": assignment_id, "status": "closed"}
