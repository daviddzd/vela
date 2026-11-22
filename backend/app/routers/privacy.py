"""/privacidad: privacy notice (everyone), consents with their validity, ARCO requests, and for dirección the audit
trail with filters plus a summary of blocked attempts (docs/spec/11).

Who sees what:
  notice        every role
  consents      coordinator (whole institution; registers / revokes), physician (own patients), family (own patient)
  ARCO          any user of an institution files one; coordinator sees the institution's, owner all, others their own
  audit trail   owner only (audit_log has no RLS: it is the platform's record)
"""
from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, current_user, require_role, tenant_db
from app.core.guards import family_patient_id, not_found_or_cross_tenant
from app.core.roles import CAREGIVER, COORDINATOR, FAMILY, OWNER, PHYSICIAN
from app.services import privacy as pv
from app.core.config import MEXICO_CITY

router = APIRouter(prefix="/api/privacy", tags=["privacy"])
PAGE_SIZE = 50


def legal_dir() -> Path:
    return Path(os.environ.get("LEGAL_DIR", Path(__file__).resolve().parents[3] / "docs" / "legal"))


@router.get("/notice")
def notice(user: CurrentUser = Depends(current_user)) -> dict:
    return {"markdown": (legal_dir() / "aviso_de_privacidad.md").read_text(encoding="utf-8"),
            "arco_days": pv.arco_days()}


# ---- consents ---------------------------------------------------------------------------------------

def _scope_patients(db: Session, user: CurrentUser) -> str:
    """SQL condition on pa.patient_id for the caller's role (RLS already limits the institution)."""
    if user.role == FAMILY:
        return "pa.patient_id = :fam_patient"
    if user.role == PHYSICIAN:
        return """EXISTS (SELECT 1 FROM assignments a JOIN service_requests r USING (request_id)
                          WHERE a.caregiver_id = :cg AND r.patient_id = pa.patient_id)"""
    return "true"


@router.get("/consents")
def consents(q: str | None = None, user: CurrentUser = Depends(require_role(COORDINATOR, PHYSICIAN, FAMILY)),
             db: Session = Depends(tenant_db)) -> dict:
    params = {"fam_patient": family_patient_id(db, user) if user.role == FAMILY else None,
              "cg": user.caregiver_id, "q": f"%{(q or '').strip()}%"}
    patients = db.execute(text(f"""
        SELECT pa.patient_id, pe.first_name || ' ' || pe.paternal_surname || ' ' || pe.maternal_surname AS name
        FROM patients pa JOIN persons pe USING (person_id)
        WHERE pa.active AND {_scope_patients(db, user)}
          AND (pe.first_name || ' ' || pe.paternal_surname || ' ' || pe.maternal_surname || ' ' || pa.patient_id) ILIKE :q
        ORDER BY pa.patient_id"""), params).mappings().all()
    ids = [p["patient_id"] for p in patients]
    rows = db.execute(text("""
        SELECT c.consent_id, c.patient_id, c.type, c.granted, c.granted_by, c.family_member_id, c.patient_assent,
               c.signed_on, c.expires_on, c.revoked_at, c.revoke_reason, v.is_valid,
               fm.first_name || ' ' || fm.paternal_surname AS signer_name
        FROM consents c JOIN v_consents v USING (consent_id)
        LEFT JOIN family_members fm ON fm.family_member_id = c.family_member_id
        WHERE c.patient_id = ANY(:ids)"""), {"ids": ids}).mappings().all()
    reps = db.execute(text("""
        SELECT family_member_id, patient_id, first_name || ' ' || paternal_surname AS name, relationship
        FROM family_members WHERE patient_id = ANY(:ids) AND is_legal_representative"""), {"ids": ids}).mappings().all() \
        if user.role == COORDINATOR else []
    by = {i: {"consents": {}, "representatives": []} for i in ids}
    for r in rows:
        by[r["patient_id"]]["consents"][r["type"]] = dict(r)
    for r in reps:
        by[r["patient_id"]]["representatives"].append(dict(r))
    return {"can_edit": user.role == COORDINATOR, "today": datetime.now(MEXICO_CITY).date().isoformat(),
            "patients": [{**p, **by[p["patient_id"]]} for p in patients]}


class ConsentIn(BaseModel):
    patient_id: str
    type: Literal["health_data", "home_care", "voice_assistant"]
    granted_by: Literal["patient", "legal_representative"]
    family_member_id: str | None = None
    patient_assent: Literal["yes", "no", "unable_to_express", "not_applicable"]
    signed_on: date
    expires_on: date


@router.post("/consents")
def record(body: ConsentIn, user: CurrentUser = Depends(require_role(COORDINATOR)),
           db: Session = Depends(tenant_db)) -> dict:
    if not db.scalar(text("SELECT 1 FROM patients WHERE patient_id = :p"), {"p": body.patient_id}):
        raise not_found_or_cross_tenant(db, user, "patient", body.patient_id)
    data = body.model_dump()
    return pv.record_consent(db, user_id=user.user_id, consent_type=data.pop("type"), **data)


class RevokeIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/consents/{consent_id}/revoke")
def revoke(consent_id: str, body: RevokeIn, user: CurrentUser = Depends(require_role(COORDINATOR)),
           db: Session = Depends(tenant_db)) -> dict:
    if not db.scalar(text("SELECT 1 FROM consents WHERE consent_id = :c"), {"c": consent_id}):
        raise not_found_or_cross_tenant(db, user, "consent", consent_id)
    return pv.revoke_consent(db, user_id=user.user_id, consent_id=consent_id, reason=body.reason)


# ---- ARCO -------------------------------------------------------------------------------------------

class ArcoIn(BaseModel):
    right_type: Literal["access", "rectification", "cancellation", "opposition"]
    description: str = Field(min_length=10, max_length=2000)
    contact: str = Field(min_length=3, max_length=200)


@router.post("/arco")
def file_arco(body: ArcoIn, user: CurrentUser = Depends(require_role(COORDINATOR, PHYSICIAN, CAREGIVER, FAMILY)),
              db: Session = Depends(tenant_db)) -> dict:
    """A family member files it about their patient's data; staff about their own account's data."""
    patient = family_patient_id(db, user) if user.role == FAMILY else None
    return pv.create_arco(db, user_id=user.user_id, institution_id=user.institution_id, patient_id=patient,
                          **body.model_dump())


@router.get("/arco")
def list_arco(user: CurrentUser = Depends(current_user), db: Session = Depends(tenant_db)) -> list[dict]:
    mine = "" if user.role in (COORDINATOR, OWNER) else "AND a.requested_by = :u"
    return [dict(r) for r in db.execute(text(f"""
        SELECT a.arco_id, a.institution_id, a.patient_id, a.right_type, a.description, a.contact, a.received_at,
               a.due_on, a.status, u.display_name AS requested_by
        FROM arco_requests a JOIN users u ON u.user_id = a.requested_by
        WHERE true {mine} ORDER BY a.received_at DESC LIMIT 200"""), {"u": user.user_id}).mappings()]


# ---- audit trail (dirección) ------------------------------------------------------------------------

def _filters(action: str | None, user_id: str | None, allowed: bool | None, start: date | None, end: date | None):
    where, p = ["true"], {}
    if action:
        where.append("l.action = :action"); p["action"] = action
    if user_id:
        where.append("l.user_id = :user_id"); p["user_id"] = user_id
    if allowed is not None:
        where.append("l.allowed = :allowed"); p["allowed"] = allowed
    if start:
        where.append("l.occurred_at >= :start"); p["start"] = datetime.combine(start, time.min, MEXICO_CITY)
    if end:
        where.append("l.occurred_at < :end"); p["end"] = datetime.combine(end + timedelta(days=1), time.min, MEXICO_CITY)
    return " AND ".join(where), p


@router.get("/audit")
def audit_trail(action: str | None = None, user_id: str | None = None, allowed: bool | None = None,
                start: date | None = None, end: date | None = None, page: int = Query(1, ge=1),
                user: CurrentUser = Depends(require_role(OWNER)), db: Session = Depends(tenant_db)) -> dict:
    where, p = _filters(action, user_id, allowed, start, end)
    total = db.scalar(text(f"SELECT count(*) FROM audit_log l WHERE {where}"), p)
    rows = db.execute(text(f"""
        SELECT l.audit_id, l.occurred_at, l.user_id, u.display_name, u.role, l.institution_id, l.action, l.entity,
               l.entity_id, l.allowed, l.detail
        FROM audit_log l LEFT JOIN users u USING (user_id) WHERE {where}
        ORDER BY l.occurred_at DESC, l.audit_id DESC LIMIT :lim OFFSET :off"""),
        {**p, "lim": PAGE_SIZE, "off": (page - 1) * PAGE_SIZE}).mappings().all()
    options = {"actions": db.scalars(text("SELECT DISTINCT action FROM audit_log ORDER BY 1")).all(),
               "users": [dict(r) for r in db.execute(text("""
                   SELECT DISTINCT l.user_id, u.display_name FROM audit_log l JOIN users u USING (user_id)
                   ORDER BY u.display_name""")).mappings()]}
    return {"total": total, "page": page, "page_size": PAGE_SIZE, "rows": [dict(r) for r in rows], "options": options}


@router.get("/audit/summary")
def blocked_summary(start: date | None = None, end: date | None = None,
                    user: CurrentUser = Depends(require_role(OWNER)), db: Session = Depends(tenant_db)) -> dict:
    """Blocked attempts: by kind, by day and the users with most attempts (for the selected dates)."""
    end = end or datetime.now(MEXICO_CITY).date()
    start = start or end - timedelta(days=29)
    where, p = _filters(None, None, False, start, end)
    by_action = db.execute(text(f"SELECT l.action, count(*) AS n FROM audit_log l WHERE {where} GROUP BY 1 ORDER BY 2 DESC"), p)
    by_day = db.execute(text(f"""SELECT (l.occurred_at AT TIME ZONE 'America/Mexico_City')::date AS day, count(*) AS n
                                 FROM audit_log l WHERE {where} GROUP BY 1 ORDER BY 1"""), p)
    by_user = db.execute(text(f"""SELECT l.user_id, u.display_name, u.role, count(*) AS n FROM audit_log l
                                  LEFT JOIN users u USING (user_id) WHERE {where}
                                  GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT 5"""), p)
    allowed = db.scalar(text(f"SELECT count(*) FROM audit_log l WHERE {_filters(None, None, True, start, end)[0]}"),
                        _filters(None, None, True, start, end)[1])
    return {"start": start.isoformat(), "end": end.isoformat(), "allowed": allowed,
            "by_action": [dict(r) for r in by_action.mappings()], "by_day": [dict(r) for r in by_day.mappings()],
            "by_user": [dict(r) for r in by_user.mappings()]}
