"""High-priority approvals (coordination) and coordinator overrides."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.guards import not_found_or_cross_tenant
from app.core.roles import COORDINATOR
from app.routers.requests import request_out
from app.services import operations as ops

router = APIRouter(prefix="/api", tags=["approvals"])


class ChooseIn(BaseModel):
    caregiver_id: str


def proposals(db: Session, request_id: str) -> list[dict]:
    rows = db.execute(text("""
        SELECT p.rank, p.caregiver_id, c.first_name || ' ' || c.paternal_surname AS caregiver_name,
               c.type AS caregiver_type, p.travel_min::float AS travel_min, p.planned_start, p.planned_end,
               p.relay_caregiver_id, rc.first_name || ' ' || rc.paternal_surname AS relay_caregiver_name,
               CASE WHEN p.relay_caregiver_id IS NOT NULL THEN p.planned_end END AS relay_at
        FROM assignment_proposals p JOIN caregivers c ON c.caregiver_id = p.caregiver_id
        LEFT JOIN caregivers rc ON rc.caregiver_id = p.relay_caregiver_id
        WHERE p.request_id = :r AND p.status = 'open' ORDER BY p.rank"""), {"r": request_id}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/approvals")
def list_approvals(user: CurrentUser = Depends(require_role(COORDINATOR)),
                   db: Session = Depends(tenant_db)) -> list[dict]:
    """High-priority requests waiting for coordination, oldest first."""
    rows = db.execute(text("""
        SELECT r.request_id, r.patient_id,
               pe.first_name || ' ' || pe.paternal_surname || ' ' || pe.maternal_surname AS patient_name,
               s.name AS service_name, r.scheduled_for, r.created_at, r.status_reason, r.origin,
               round(extract(epoch FROM now() - r.created_at) / 60)::int AS minutes_waiting
        FROM service_requests r JOIN services s USING (service_id)
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        WHERE r.status = 'queued' AND r.priority = 'high'
        ORDER BY r.created_at""")).mappings().all()
    return [{**r, "options": proposals(db, r["request_id"])} for r in rows]


@router.post("/approvals/{request_id}")
def approve(request_id: str, body: ChooseIn, user: CurrentUser = Depends(require_role(COORDINATOR)),
            db: Session = Depends(tenant_db)):
    if db.scalar(text("SELECT 1 FROM service_requests WHERE request_id = :r"), {"r": request_id}) is None:
        raise not_found_or_cross_tenant(db, user, "service_request", request_id)
    try:
        ops.approve(db, user_id=user.user_id, institution_id=user.institution_id,
                    request_id=request_id, caregiver_id=body.caregiver_id)
    except ops.InvalidState:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta solicitud ya no está pendiente de aprobación.")
    except ops.NotAvailable:
        # Not a failure: the new proposals are saved (the transaction still commits) and shown.
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=jsonable_encoder({
            "detail": "Esa persona ya no está disponible. Calculamos nuevas opciones.",
            "options": proposals(db, request_id)}))
    return request_out(db, request_id)


@router.post("/assignments/{assignment_id}/reassign")
def reassign(assignment_id: str, body: ChooseIn, user: CurrentUser = Depends(require_role(COORDINATOR)),
             db: Session = Depends(tenant_db)) -> dict:
    """Coordinator override: move a not-yet-started visit to another free caregiver."""
    request_id = db.scalar(text("SELECT request_id FROM assignments WHERE assignment_id = :a"), {"a": assignment_id})
    if request_id is None:
        raise not_found_or_cross_tenant(db, user, "assignment", assignment_id)
    try:
        ops.reassign(db, user_id=user.user_id, institution_id=user.institution_id,
                     assignment_id=assignment_id, caregiver_id=body.caregiver_id)
    except ops.InvalidState:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta visita ya no se puede reasignar.")
    except ops.NotAvailable:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esa persona no está disponible en ese horario.")
    return request_out(db, request_id)
