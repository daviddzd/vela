"""Consents (record / revoke) and ARCO requests (docs/spec/11, CLAUDE.md rule 5).

Revoking a consent takes effect AT ONCE: every function checks v_consents.is_valid on each request, and a
revoked row has granted = false. What else happens (team decision 22 Nov 2026):
  home_care     pending visits of the patient are cancelled (reason "consent_revoked") and coordination gets an
                alert; a visit ALREADY IN PROGRESS is not cancelled by itself: the alert asks coordination to
                decide. The family gets a notice.
  health_data   health data stop showing (the patient record checks it on every read).
  voice_assistant  the voice assistant stops accepting notes for that patient.
Everything is written to audit_log.
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.events import publish
from app.services import business_model as bm

TYPES = ("health_data", "home_care", "voice_assistant")
PENDING = ("registered", "validated", "queued", "assigned")
TYPE_ES = {"health_data": "datos de salud", "home_care": "atención a domicilio", "voice_assistant": "asistente de voz"}

ALERT_HOME_CARE_REVOKED = ("{patient}: se revocó el consentimiento de atención a domicilio. "
                           "{cancelled} visita(s) pendiente(s) cancelada(s).")
ALERT_IN_PROGRESS = (" Hay {n} visita en curso ({requests}): no se canceló sola, decide si se termina o se suspende.")
NOTICE_REVOKED = ("Se registró la revocación del consentimiento de {kind}. "
                  "Las funciones que dependen de él quedaron suspendidas.")
NOTICE_HOME_CARE = " Las visitas a domicilio pendientes se cancelaron."
NOTICE_RECORDED = "Se registró el consentimiento de {kind}, vigente hasta el {until}."


def add_business_days(start: date, days: int) -> date:
    """Monday-Friday only. Public holidays are NOT discounted: the date shown is an estimate (said on the page)."""
    d, left = start, days
    while left:
        d += timedelta(days=1)
        if d.weekday() < 5:
            left -= 1
    return d


def arco_days() -> int:
    return int(bm.assumptions()["arco_response_days"]["value"])


def _patient(db: Session, patient_id: str):
    row = db.execute(text("""SELECT pa.patient_id, pa.institution_id,
                                    pe.first_name || ' ' || pe.paternal_surname AS full_name
                             FROM patients pa JOIN persons pe USING (person_id) WHERE pa.patient_id = :p"""),
                     {"p": patient_id}).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado.")
    return row


def record_consent(db: Session, *, user_id: str, patient_id: str, consent_type: str, granted_by: str,
                   family_member_id: str | None, patient_assent: str, signed_on: date, expires_on: date) -> dict:
    """Register (or renew) a consent. The legal representative must be a family member of THIS patient
    marked as legal representative."""
    p = _patient(db, patient_id)
    if expires_on <= signed_on:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La vigencia debe terminar después de la firma.")
    if granted_by == "legal_representative":
        ok = db.scalar(text("""SELECT is_legal_representative FROM family_members
                               WHERE family_member_id = :f AND patient_id = :p"""), {"f": family_member_id, "p": patient_id})
        if not ok:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                "Quien firma debe ser un familiar registrado como representante legal de esta persona.")
    else:
        family_member_id = None
    consent_id = db.scalar(text("""
        INSERT INTO consents (consent_id, patient_id, institution_id, type, granted, granted_by, family_member_id,
                              patient_assent, signed_on, expires_on, recorded_by, recorded_at)
        VALUES ('CON-' || substr(gen_random_uuid()::text, 1, 8), :p, :i, :t, true, :gb, :f, :a, :s, :e, :u, now())
        ON CONFLICT (patient_id, type) DO UPDATE SET granted = true, granted_by = EXCLUDED.granted_by,
            family_member_id = EXCLUDED.family_member_id, patient_assent = EXCLUDED.patient_assent,
            signed_on = EXCLUDED.signed_on, expires_on = EXCLUDED.expires_on, recorded_by = EXCLUDED.recorded_by,
            recorded_at = now(), revoked_at = NULL, revoked_by = NULL, revoke_reason = NULL
        RETURNING consent_id"""), {"p": patient_id, "i": p.institution_id, "t": consent_type, "gb": granted_by,
                                   "f": family_member_id, "a": patient_assent, "s": signed_on, "e": expires_on, "u": user_id})
    audit(db, user_id=user_id, institution_id=p.institution_id, action="consent_recorded", entity="consent",
          entity_id=consent_id, detail={"patient_id": patient_id, "type": consent_type, "granted_by": granted_by,
                                        "patient_assent": patient_assent, "expires_on": expires_on.isoformat()})
    db.execute(text("INSERT INTO family_notices (institution_id, patient_id, message) VALUES (:i, :p, :m)"),
               {"i": p.institution_id, "p": patient_id,
                "m": NOTICE_RECORDED.format(kind=TYPE_ES[consent_type], until=expires_on.strftime("%d/%m/%Y"))})
    publish(db, "consent.changed", p.institution_id, patient_id=patient_id, consent_type=consent_type)
    return {"consent_id": consent_id}


def revoke_consent(db: Session, *, user_id: str, consent_id: str, reason: str) -> dict:
    c = db.execute(text("SELECT consent_id, patient_id, institution_id, type, granted FROM consents WHERE consent_id = :c"),
                   {"c": consent_id}).one_or_none()
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado.")
    if not c.granted:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este consentimiento ya no está otorgado.")
    db.execute(text("""UPDATE consents SET granted = false, revoked_at = now(), revoked_by = :u, revoke_reason = :r
                       WHERE consent_id = :c"""), {"u": user_id, "r": reason, "c": consent_id})
    result = {"consent_id": consent_id, "type": c.type, "cancelled": [], "in_progress": []}
    if c.type == "home_care":
        result |= _stop_home_visits(db, c.patient_id, c.institution_id)
    message = NOTICE_REVOKED.format(kind=TYPE_ES[c.type]) + (NOTICE_HOME_CARE if result["cancelled"] else "")
    db.execute(text("INSERT INTO family_notices (institution_id, patient_id, message) VALUES (:i, :p, :m)"),
               {"i": c.institution_id, "p": c.patient_id, "m": message})
    audit(db, user_id=user_id, institution_id=c.institution_id, action="consent_revoked", entity="consent",
          entity_id=consent_id, detail={"patient_id": c.patient_id, "type": c.type, "reason": reason,
                                        "cancelled_requests": result["cancelled"], "in_progress": result["in_progress"]})
    publish(db, "consent.changed", c.institution_id, patient_id=c.patient_id, consent_type=c.type)
    return result


def _stop_home_visits(db: Session, patient_id: str, institution_id: str) -> dict:
    """Cancel pending visits; never touch one already in progress (alert instead)."""
    pending = db.execute(text("""
        SELECT r.request_id FROM service_requests r
        WHERE r.patient_id = :p AND r.status = ANY(:pending)
          AND NOT EXISTS (SELECT 1 FROM assignments a WHERE a.request_id = r.request_id AND a.status = 'active'
                          AND a.arrived_at IS NOT NULL)"""), {"p": patient_id, "pending": list(PENDING)}).scalars().all()
    for rid in pending:
        db.execute(text("UPDATE assignments SET status = 'cancelled' WHERE request_id = :r AND status = 'active'"), {"r": rid})
        db.execute(text("UPDATE assignment_proposals SET status = 'superseded' WHERE request_id = :r AND status = 'open'"),
                   {"r": rid})
        db.execute(text("""UPDATE service_requests SET status = 'cancelled', status_reason = 'consent_revoked'
                           WHERE request_id = :r"""), {"r": rid})
        publish(db, "request.updated", institution_id, request_id=rid, status="cancelled")
    in_progress = db.execute(text("""
        SELECT r.request_id FROM service_requests r JOIN assignments a USING (request_id)
        WHERE r.patient_id = :p AND a.status = 'active' AND a.arrived_at IS NOT NULL AND a.finished_at IS NULL"""),
        {"p": patient_id}).scalars().all()
    name = _patient(db, patient_id).full_name
    message = ALERT_HOME_CARE_REVOKED.format(patient=name, cancelled=len(pending))
    if in_progress:
        message += ALERT_IN_PROGRESS.format(n=len(in_progress), requests=", ".join(in_progress))
    alert_id = db.scalar(text("""INSERT INTO alerts (institution_id, type, level, patient_id, message)
                                 VALUES (:i, 'consent', :l, :p, :m) RETURNING alert_id"""),
                         {"i": institution_id, "l": "high" if in_progress else "watch", "p": patient_id, "m": message})
    publish(db, "alert.created", institution_id, alert_id=alert_id)
    return {"cancelled": list(pending), "in_progress": list(in_progress), "alert_id": alert_id}


def create_arco(db: Session, *, user_id: str, institution_id: str, patient_id: str | None, right_type: str,
                description: str, contact: str) -> dict:
    received = db.scalar(text("SELECT (now() AT TIME ZONE 'America/Mexico_City')::date"))
    due = add_business_days(received, arco_days())
    arco_id = db.scalar(text("""
        INSERT INTO arco_requests (institution_id, patient_id, requested_by, right_type, description, contact, due_on)
        VALUES (:i, :p, :u, :r, :d, :c, :due) RETURNING arco_id"""),
        {"i": institution_id, "p": patient_id, "u": user_id, "r": right_type, "d": description, "c": contact, "due": due})
    audit(db, user_id=user_id, institution_id=institution_id, action="arco_request_created", entity="arco_request",
          entity_id=arco_id, detail={"right": right_type, "patient_id": patient_id})
    return {"arco_id": arco_id, "received_on": received.isoformat(), "due_on": due.isoformat(), "days": arco_days()}
