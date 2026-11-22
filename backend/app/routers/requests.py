"""Service requests: created by family or coordination, then validated and dispatched at once."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.guards import deny, family_patient_id, not_found_or_cross_tenant
from app.core.roles import COORDINATOR, FAMILY, OWNER
from app.services import operations as ops

router = APIRouter(prefix="/api/requests", tags=["requests"])


class RequestIn(BaseModel):
    patient_id: str | None = None          # family: ignored, always their own patient
    service_id: str
    scheduled_for: datetime                # without time zone = Mexico City time
    priority: Literal["low", "medium", "high"] | None = None   # coordinator only


def request_out(db: Session, request_id: str) -> dict:
    r = db.execute(text("""
        SELECT r.request_id, r.patient_id, r.service_id, s.name AS service_name, r.priority, r.origin,
               r.scheduled_for, r.created_at, r.status, r.status_reason, r.duplicate_of,
               v.assignment_id, v.caregiver_id, v.approval, v.planned_start, v.planned_end,
               c.first_name || ' ' || c.paternal_surname AS caregiver_name
        FROM service_requests r JOIN services s USING (service_id)
        LEFT JOIN v_service_requests v ON v.request_id = r.request_id
        LEFT JOIN caregivers c ON c.caregiver_id = v.caregiver_id
        WHERE r.request_id = :id"""), {"id": request_id}).mappings().one()
    return dict(r)


@router.post("", status_code=status.HTTP_201_CREATED)
def create(body: RequestIn, user: CurrentUser = Depends(require_role(COORDINATOR, FAMILY)),
           db: Session = Depends(tenant_db)) -> dict:
    if user.role == FAMILY:
        can = db.scalar(text("SELECT can_request_services FROM family_members WHERE family_member_id = :f"),
                        {"f": user.family_member_id})
        if not can:
            raise deny(user, "blocked_out_of_scope", "service_request", None,
                       "Tu registro no permite solicitar servicios. Habla con la coordinación.")
        patient_id = family_patient_id(db, user)
        # The family does not choose the priority: it comes from the patient's care level.
        priority = db.scalar(text("SELECT base_priority FROM patients WHERE patient_id = :p"), {"p": patient_id})
        origin = "family"
    else:
        if not body.patient_id or not body.priority:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indica paciente y prioridad.")
        patient_id, priority, origin = body.patient_id, body.priority, "coordinator"
        if db.scalar(text("SELECT 1 FROM patients WHERE patient_id = :p"), {"p": patient_id}) is None:
            raise not_found_or_cross_tenant(db, user, "patient", patient_id)
    request_id = ops.create_request(db, user_id=user.user_id, institution_id=user.institution_id,
                                    patient_id=patient_id, service_id=body.service_id,
                                    scheduled_for=body.scheduled_for, priority=priority, origin=origin)
    return request_out(db, request_id)


@router.get("/{request_id}")
def get_request(request_id: str, user: CurrentUser = Depends(require_role(COORDINATOR, FAMILY, OWNER)),
                db: Session = Depends(tenant_db)) -> dict:
    patient_id = db.scalar(text("SELECT patient_id FROM service_requests WHERE request_id = :r"), {"r": request_id})
    if patient_id is None:
        raise not_found_or_cross_tenant(db, user, "service_request", request_id)
    if user.role == FAMILY and patient_id != family_patient_id(db, user):
        raise deny(user, "blocked_out_of_scope", "service_request", request_id,
                   "Esta solicitud no es de tu familiar. El intento quedó registrado.")
    return request_out(db, request_id)
