"""Patients: list and record. Health data only with a valid `health_data` consent (CLAUDE.md rule 5)."""
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.guards import ensure_patient_scope, not_found_or_cross_tenant
from app.core.roles import COORDINATOR, OWNER, PHYSICIAN
from app.services.operations import has_valid_consent

router = APIRouter(prefix="/api/patients", tags=["patients"])

CONDITIONS = ("diabetes", "hypertension", "high_cholesterol", "heart_disease", "stroke", "kidney_disease",
              "chronic_lung_disease", "arthritis", "cancer", "obesity", "anemia", "depressive_symptoms",
              "fall_last_12m", "frailty", "visual_impairment", "hearing_impairment")
MISSING_CONSENT = "Falta consentimiento"


class Health(BaseModel):
    conditions: list[str]          # codes; the UI translates them
    chronic_disease_count: int
    multimorbidity: bool
    dependency_level: str
    cognitive_status: str
    pollution_sensitive: bool


class PatientOut(BaseModel):
    patient_id: str
    institution_id: str
    full_name: str
    age: int
    district_id: str
    admission_date: date
    base_priority: str
    active: bool
    health: Health | None          # None when consent is missing
    health_notice: str | None      # "Falta consentimiento"


class PatientRow(BaseModel):
    patient_id: str
    full_name: str
    base_priority: str
    active: bool


@router.get("", response_model=list[PatientRow])
def list_patients(user: CurrentUser = Depends(require_role(COORDINATOR, PHYSICIAN, OWNER)),
                  db: Session = Depends(tenant_db)) -> list[PatientRow]:
    """Coordinator: whole institution. Physician: only their patients."""
    only_mine = "AND EXISTS (SELECT 1 FROM assignments a JOIN service_requests r USING (request_id) " \
                "WHERE a.caregiver_id = :c AND r.patient_id = pa.patient_id)" if user.role == PHYSICIAN else ""
    rows = db.execute(text(f"""
        SELECT pa.patient_id, pe.first_name || ' ' || pe.paternal_surname || ' ' || pe.maternal_surname AS full_name,
               pa.base_priority, pa.active
        FROM patients pa JOIN persons pe USING (person_id)
        WHERE true {only_mine} ORDER BY pa.patient_id"""), {"c": user.caregiver_id}).all()
    return [PatientRow(**r._mapping) for r in rows]


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: str,
                user: CurrentUser = Depends(require_role(COORDINATOR, PHYSICIAN, OWNER)),
                db: Session = Depends(tenant_db)) -> PatientOut:
    p = db.execute(text("SELECT * FROM v_patients WHERE patient_id = :id"), {"id": patient_id}).mappings().first()
    if p is None:
        raise not_found_or_cross_tenant(db, user, "patient", patient_id)
    ensure_patient_scope(db, user, patient_id)
    audit(db, user_id=user.user_id, institution_id=user.institution_id, action="read_patient",
          entity="patient", entity_id=patient_id)

    health, notice = None, None
    if has_valid_consent(db, patient_id, "health_data"):
        health = Health(conditions=[c for c in CONDITIONS if p[c]],
                        chronic_disease_count=p["chronic_disease_count"], multimorbidity=p["multimorbidity"],
                        dependency_level=p["dependency_level"], cognitive_status=p["cognitive_status"],
                        pollution_sensitive=p["pollution_sensitive"])
    else:
        notice = MISSING_CONSENT
        audit(db, user_id=user.user_id, institution_id=user.institution_id, action="health_data_blocked",
              entity="patient", entity_id=patient_id, allowed=False, detail={"consent": "health_data"})

    return PatientOut(patient_id=p["patient_id"], institution_id=p["institution_id"],
                      full_name=f"{p['first_name']} {p['paternal_surname']} {p['maternal_surname']}",
                      age=p["age"], district_id=p["district_id"], admission_date=p["admission_date"],
                      base_priority=p["base_priority"], active=p["active"], health=health,
                      health_notice=notice)
