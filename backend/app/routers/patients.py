"""Patients: list and record. Health data only with a valid `health_data` consent (CLAUDE.md rule 5)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.guards import ensure_patient_scope, not_found_or_cross_tenant
from app.core.roles import COORDINATOR, OWNER, PHYSICIAN
from app.services import care_plans as cp
from app.services import operations as ops
from app.services.dispatcher import patient_risk
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
    district_id: str | None = None
    district_name: str | None = None
    age: int | None = None
    # health-derived fields: None when there is no valid health_data consent (CLAUDE.md rule 5)
    health_consent: bool = False
    dependency_level: str | None = None
    pollution_sensitive: bool | None = None
    risk: float | None = None
    risk_level: str | None = None        # low / medium / high (the UI shows it as text)


@router.get("", response_model=list[PatientRow])
def list_patients(q: str | None = None, district: str | None = None, priority: str | None = None,
                  dependency: str | None = None, sensitive: bool | None = None,
                  user: CurrentUser = Depends(require_role(COORDINATOR, PHYSICIAN, OWNER)),
                  db: Session = Depends(tenant_db)) -> list[PatientRow]:
    """Coordinator: whole institution. Physician: only their patients. Filters on health data (dependency,
    pollution sensitivity) only match patients with a valid health_data consent."""
    only_mine = "AND EXISTS (SELECT 1 FROM assignments a JOIN service_requests r USING (request_id) " \
                "WHERE a.caregiver_id = :c AND r.patient_id = vp.patient_id)" if user.role == PHYSICIAN else ""
    rows = db.execute(text(f"""
        SELECT vp.*, d.name AS district_name,
               coalesce((SELECT c.is_valid FROM v_consents c WHERE c.patient_id = vp.patient_id
                         AND c.type = 'health_data'), false) AS health_consent
        FROM v_patients vp JOIN districts d USING (district_id)
        WHERE true {only_mine}
          AND (:q = '' OR (vp.first_name || ' ' || vp.paternal_surname || ' ' || vp.maternal_surname || ' ' || vp.patient_id) ILIKE :ql)
          AND (:district = '' OR vp.district_id = :district)
          AND (:priority = '' OR vp.base_priority = :priority)
        ORDER BY vp.patient_id"""),
        {"c": user.caregiver_id, "q": (q or "").strip(), "ql": f"%{(q or '').strip()}%", "district": district or "",
         "priority": priority or ""}).all()
    multipliers = ops.risk_multipliers()
    out = []
    for r in rows:
        row = PatientRow(patient_id=r.patient_id, full_name=f"{r.first_name} {r.paternal_surname} {r.maternal_surname}",
                         base_priority=r.base_priority, active=r.active, district_id=r.district_id,
                         district_name=r.district_name, age=r.age, health_consent=r.health_consent)
        if r.health_consent:
            risk = patient_risk(ops.risk_flags(r), multipliers)
            row.dependency_level, row.pollution_sensitive = r.dependency_level, r.pollution_sensitive
            row.risk, row.risk_level = round(risk, 2), ops.risk_level(risk)
        if dependency and row.dependency_level != dependency:
            continue
        if sensitive is not None and row.pollution_sensitive is not sensitive:
            continue
        out.append(row)
    return out


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


# ---- full record (/pacientes/:id) --------------------------------------------------------------------

@router.get("/{patient_id}/record")
def record(patient_id: str, user: CurrentUser = Depends(require_role(COORDINATOR, PHYSICIAN, OWNER)),
           db: Session = Depends(tenant_db)) -> dict:
    """Everything the record screen shows, with the same scope and consent rules as GET /{patient_id}
    (that call also writes the read to audit_log)."""
    base = get_patient(patient_id, user, db).model_dump()
    consent = base["health"] is not None
    p = db.execute(text("""SELECT vp.*, d.name AS district_name, i.name AS institution_name
                           FROM v_patients vp JOIN districts d USING (district_id)
                           JOIN institutions i ON i.institution_id = vp.institution_id
                           WHERE vp.patient_id = :p"""), {"p": patient_id}).one()
    risk = patient_risk(ops.risk_flags(p), ops.risk_multipliers()) if consent else None
    plans = db.execute(text("""
        SELECT cp.care_plan_id, cp.service_id, s.name AS service_name, cp.times_per_week::float AS times_per_week,
               cp.reason, cp.active, cp.created_at, cp.ended_at, cp.replaces
        FROM care_plans cp JOIN services s USING (service_id) WHERE cp.patient_id = :p
        ORDER BY cp.active DESC, cp.care_plan_id"""), {"p": patient_id}).mappings().all()
    history = db.execute(text("""
        SELECT r.request_id, r.scheduled_for, r.status, r.status_reason, r.priority, r.origin, s.name AS service_name,
               r.care_plan_id, a.approval, a.arrived_at, a.finished_at,
               c.first_name || ' ' || c.paternal_surname AS caregiver_name
        FROM service_requests r JOIN services s USING (service_id)
        LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active'
        LEFT JOIN caregivers c ON c.caregiver_id = a.caregiver_id
        WHERE r.patient_id = :p ORDER BY r.scheduled_for DESC LIMIT 40"""), {"p": patient_id}).mappings().all()
    reports = [dict(r) for r in db.execute(text("""
        SELECT report_id, created_at, triage_label, input_mode, needs_human_review, reviewed_at,
               transcript, report_status, report
        FROM voice_reports WHERE patient_id = :p ORDER BY created_at DESC LIMIT 20"""), {"p": patient_id}).mappings()]
    for r in reports:   # content is health data, and the physician is who reads it
        if not consent or user.role != PHYSICIAN:
            r.update(transcript=None, report=None)
    family = db.execute(text(f"""
        SELECT family_member_id, first_name || ' ' || paternal_surname || ' ' || maternal_surname AS name, relationship,
               is_legal_representative, can_request_services{", email" if user.role == COORDINATOR else ""}
        FROM family_members WHERE patient_id = :p ORDER BY family_member_id"""), {"p": patient_id}).mappings().all()
    consents = db.execute(text("""
        SELECT c.type, c.granted, c.signed_on, c.expires_on, c.revoked_at, v.is_valid
        FROM consents c JOIN v_consents v USING (consent_id) WHERE c.patient_id = :p"""), {"p": patient_id}).mappings().all()
    services = db.execute(text("""
        SELECT s.service_id, s.name, ins.duration_min FROM institution_services ins JOIN services s USING (service_id)
        WHERE ins.institution_id = :i AND ins.active ORDER BY s.service_id"""), {"i": p.institution_id}).mappings().all()
    return {**base, "district_name": p.district_name, "institution_name": p.institution_name, "sex": p.sex,
            "risk": round(risk, 2) if risk is not None else None, "risk_level": ops.risk_level(risk) if risk is not None else None,
            "care_plans": [dict(x) for x in plans], "history": [dict(x) for x in history], "voice_reports": reports,
            "family": [dict(x) for x in family], "consents": [dict(x) for x in consents], "services": [dict(x) for x in services],
            "can_edit_plan": user.role == PHYSICIAN, "can_request": user.role == COORDINATOR}


# ---- care plan changes (physician, own patients) -------------------------------------------------------

class PlanIn(BaseModel):
    service_id: str
    times_per_week: float = Field(gt=0, le=14)
    reason: str = Field(min_length=3, max_length=200)


def _physician_scope(db: Session, user: CurrentUser, patient_id: str) -> str:
    inst = db.scalar(text("SELECT institution_id FROM patients WHERE patient_id = :p"), {"p": patient_id})
    if inst is None:
        raise not_found_or_cross_tenant(db, user, "patient", patient_id)
    ensure_patient_scope(db, user, patient_id)
    return inst


def _check_service(db: Session, inst: str, service_id: str) -> None:
    if not db.scalar(text("SELECT active FROM institution_services WHERE institution_id = :i AND service_id = :s"),
                     {"i": inst, "s": service_id}):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La institución no ofrece ese servicio.")


def _plan_of(db: Session, patient_id: str, plan_id: str):
    row = db.execute(text("SELECT * FROM care_plans WHERE care_plan_id = :c AND patient_id = :p AND active"),
                     {"c": plan_id, "p": patient_id}).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese plan no está activo para esta persona.")
    return row


@router.post("/{patient_id}/care-plans")
def add_plan(patient_id: str, body: PlanIn, user: CurrentUser = Depends(require_role(PHYSICIAN)),
             db: Session = Depends(tenant_db)) -> dict:
    inst = _physician_scope(db, user, patient_id)
    _check_service(db, inst, body.service_id)
    new_id = cp.new_plan(db, patient_id=patient_id, institution_id=inst, user_id=user.user_id, **body.model_dump())
    audit(db, user_id=user.user_id, institution_id=inst, action="care_plan_created", entity="care_plan",
          entity_id=new_id, detail={"patient_id": patient_id, **body.model_dump()})
    return {"care_plan_id": new_id, "cancelled": [], "assigned": []}


@router.put("/{patient_id}/care-plans/{plan_id}")
def change_plan(patient_id: str, plan_id: str, body: PlanIn, user: CurrentUser = Depends(require_role(PHYSICIAN)),
                db: Session = Depends(tenant_db)) -> dict:
    inst = _physician_scope(db, user, patient_id)
    old = _plan_of(db, patient_id, plan_id)
    _check_service(db, inst, body.service_id)
    effects = cp.end_plan(db, plan_id=plan_id, user_id=user.user_id)
    new_id = cp.new_plan(db, patient_id=patient_id, institution_id=inst, user_id=user.user_id, replaces=plan_id,
                         **body.model_dump())
    audit(db, user_id=user.user_id, institution_id=inst, action="care_plan_changed", entity="care_plan", entity_id=plan_id,
          detail={"patient_id": patient_id, "new_plan": new_id,
                  "before": {"service_id": old["service_id"], "times_per_week": float(old["times_per_week"])},
                  "after": body.model_dump(), **effects})
    return {"care_plan_id": new_id, **effects}


@router.post("/{patient_id}/care-plans/{plan_id}/end")
def end_plan(patient_id: str, plan_id: str, user: CurrentUser = Depends(require_role(PHYSICIAN)),
             db: Session = Depends(tenant_db)) -> dict:
    inst = _physician_scope(db, user, patient_id)
    _plan_of(db, patient_id, plan_id)
    effects = cp.end_plan(db, plan_id=plan_id, user_id=user.user_id)
    audit(db, user_id=user.user_id, institution_id=inst, action="care_plan_ended", entity="care_plan", entity_id=plan_id,
          detail={"patient_id": patient_id, **effects})
    return {"care_plan_id": plan_id, **effects}
