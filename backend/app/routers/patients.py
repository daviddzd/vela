"""Patients. For now only the administrative record; health data and the consent gate
(CLAUDE.md rule 5) arrive in step 3."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.audit import audit, audit_now
from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.roles import COORDINATOR, OWNER, PHYSICIAN
from app.models.tables import Patient, Person

router = APIRouter(prefix="/api/patients", tags=["patients"])


class PatientOut(BaseModel):
    patient_id: str
    institution_id: str
    full_name: str
    admission_date: date
    base_priority: str
    active: bool


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: str,
                user: CurrentUser = Depends(require_role(COORDINATOR, PHYSICIAN, OWNER)),
                db: Session = Depends(tenant_db)) -> PatientOut:
    # TODO(step 3): a physician must only read patients under their care, not the whole institution.
    row = db.execute(select(Patient, Person).join(Person, Patient.person_id == Person.person_id)
                     .where(Patient.patient_id == patient_id)).first()
    if row is None:
        # RLS hides other institutions' rows, so "not found" may mean "belongs to someone else".
        # entity_institution() (Alembic 0001) tells us only WHICH institution owns the id, nothing else.
        owner_inst = db.scalar(text("SELECT entity_institution('patient', :id)"), {"id": patient_id})
        if owner_inst is not None and owner_inst != user.institution_id:
            audit_now(user_id=user.user_id, institution_id=user.institution_id,
                      action="blocked_cross_tenant", entity="patient", entity_id=patient_id,
                      allowed=False, detail={"target_institution": owner_inst})
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Este paciente pertenece a otra institución. El intento quedó registrado.")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente no encontrado.")
    patient, person = row
    audit(db, user_id=user.user_id, institution_id=user.institution_id, action="read_patient",
          entity="patient", entity_id=patient_id)
    return PatientOut(patient_id=patient.patient_id, institution_id=patient.institution_id,
                      full_name=f"{person.first_name} {person.paternal_surname} {person.maternal_surname}",
                      admission_date=patient.admission_date, base_priority=patient.base_priority,
                      active=patient.active)
