"""Alerts that need a person to act, and what happens if nobody does.

1. Voice note rated "emergency" ONLY by the classifier (no rule fired, ORACLE-Voz, docs/spec/05):
   the person saw the amber notice with 911; coordination gets a CRITICAL 'emergency_review' alert with a deadline
   (escalate_at). Coordination contacts the family and records the outcome:
     - "Contactada: era emergencia"    -> resolved as 'emergency' and escalated at once to Dirección (a new critical
                                          'emergency' alert, already escalated), audited;
     - "Contactada: no era emergencia" -> resolved as 'not_emergency', audited.
   If nobody answers before the deadline (classifier_only.escalate_after_minutes, config/emergency_rules.yaml), the
   worker escalates it to Dirección (escalated_at) and audits it. Nothing is discarded: the voice report keeps
   level "emergency".
2. A visit still "in progress" long after its planned end (someone forgot "Terminé", like REQ-08939): the worker
   marks it 'not_closed' ("No cerrada") and alerts coordination (dispatch.not_closed_after_minutes,
   config/simulation.yaml).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.services import operations as ops
from app.core.events import publish
from app.services.triage_rules import rules

REVIEW_ALERT = ("La nota de voz de {name} podría indicar algo urgente (lo detectó solo el "
                "clasificador, ninguna regla). Contacta a la familia y registra qué era.")
CONFIRMED_ALERT = "Emergencia confirmada por coordinación con la familia de {name} (nota de voz {report})."
NOT_CLOSED_ALERT = ("La visita {request} de {patient} con {caregiver} sigue abierta: su hora de fin ({end}) pasó hace "
                    "más de {hours} h. Se marcó como «No cerrada»; confirma con la persona si se realizó.")


class NotOpen(Exception):
    """The alert does not exist, is not a review alert, or was already resolved."""


def escalate_after_minutes() -> int:
    return int(rules()["classifier_only"]["escalate_after_minutes"])


def open_review(db: Session, *, institution_id: str, patient_id: str, patient_name: str, report_id: str) -> str:
    """Critical alert for coordination when only the classifier said "emergency"; returns its id."""
    alert_id = db.scalar(text("""
        INSERT INTO alerts (institution_id, type, level, patient_id, message, code, escalate_at)
        VALUES (:i, 'emergency_review', 'critical', :p, :m, :c, now() + :min * interval '1 minute') RETURNING alert_id"""),
        {"i": institution_id, "p": patient_id, "m": REVIEW_ALERT.format(name=patient_name), "c": f"voice:{report_id}",
         "min": escalate_after_minutes()})
    publish(db, "alert.created", institution_id, alert_id=alert_id, request_id=None)
    return alert_id


def review(db: Session, *, alert_id: str, outcome: str, user_id: str) -> dict:
    """Coordination (or Dirección) contacted the family: outcome 'emergency' or 'not_emergency'."""
    if outcome not in ("emergency", "not_emergency"):
        raise ValueError(outcome)
    row = db.execute(text("""
        UPDATE alerts SET status = 'resolved', resolved_at = now(), resolution = :o, handled_by = :u
        WHERE alert_id = :a AND type = 'emergency_review' AND status <> 'resolved'
        RETURNING institution_id, patient_id, code, escalated_at"""), {"a": alert_id, "o": outcome, "u": user_id}).one_or_none()
    if row is None:
        raise NotOpen(alert_id)
    report_id = (row.code or "").removeprefix("voice:")
    confirmed_id = None
    if outcome == "emergency":                     # escalate and record: Dirección sees it at once
        name = db.scalar(text("""SELECT pe.first_name || ' ' || pe.paternal_surname FROM patients pa
                                 JOIN persons pe USING (person_id) WHERE pa.patient_id = :p"""), {"p": row.patient_id})
        confirmed_id = db.scalar(text("""
            INSERT INTO alerts (institution_id, type, level, patient_id, message, escalated_at)
            VALUES (:i, 'emergency', 'critical', :p, :m, now()) RETURNING alert_id"""),
            {"i": row.institution_id, "p": row.patient_id, "m": CONFIRMED_ALERT.format(name=name, report=report_id)})
        publish(db, "alert.created", row.institution_id, alert_id=confirmed_id, request_id=None)
    audit(db, user_id=user_id, institution_id=row.institution_id,
          action="emergency_review_confirmed" if outcome == "emergency" else "emergency_review_dismissed",
          entity="alert", entity_id=alert_id,
          detail={"report_id": report_id, "patient_id": row.patient_id, "was_escalated": row.escalated_at is not None,
                  **({"confirmed_alert": confirmed_id} if confirmed_id else {})})
    publish(db, "alert.updated", row.institution_id, alert_id=alert_id)
    return {"alert_id": alert_id, "resolution": outcome, "confirmed_alert": confirmed_id}


def escalate_overdue(db: Session) -> int:
    """Worker: review alerts nobody answered before their deadline escalate to Dirección."""
    rows = db.execute(text("""
        UPDATE alerts SET escalated_at = now()
        WHERE type = 'emergency_review' AND status = 'open' AND escalated_at IS NULL AND escalate_at <= now()
        RETURNING alert_id, institution_id, code""")).all()
    for r in rows:
        audit(db, user_id=None, institution_id=r.institution_id, action="emergency_review_escalated", entity="alert",
              entity_id=r.alert_id, detail={"report_id": (r.code or "").removeprefix("voice:"),
                                             "after_minutes": escalate_after_minutes()})
        publish(db, "alert.updated", r.institution_id, alert_id=r.alert_id)
    return len(rows)


def mark_not_closed(db: Session) -> int:
    """Worker: visits in progress whose planned end passed more than N minutes ago become "No cerrada" + alert."""
    minutes = int(ops.settings_yaml()["dispatch"]["not_closed_after_minutes"])
    rows = db.execute(text("""
        WITH open_visits AS (
            SELECT r.request_id, r.institution_id, r.patient_id,
                   coalesce((SELECT max(x.planned_end) FROM assignments x WHERE x.request_id = r.request_id
                             AND x.status = 'active'), r.scheduled_for + s.duration_min * interval '1 minute') AS ends
            FROM service_requests r JOIN services s USING (service_id) WHERE r.status = 'in_progress')
        SELECT o.*, pe.first_name || ' ' || pe.paternal_surname AS patient,
               coalesce((SELECT string_agg(c.first_name || ' ' || c.paternal_surname, ' y ' ORDER BY a.leg)
                         FROM assignments a JOIN caregivers c USING (caregiver_id)
                         WHERE a.request_id = o.request_id AND a.status = 'active'), 'sin persona asignada') AS caregiver
        FROM open_visits o JOIN patients pa ON pa.patient_id = o.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        WHERE o.ends < now() - :m * interval '1 minute'"""), {"m": minutes}).all()
    for r in rows:
        ops.set_status(db, r.request_id, "not_closed")
        alert_id = db.scalar(text("""
            INSERT INTO alerts (institution_id, type, level, patient_id, request_id, code, message)
            VALUES (:i, 'visit_not_closed', 'high', :p, :r, 'not_closed', :m)
            ON CONFLICT DO NOTHING RETURNING alert_id"""),
            {"i": r.institution_id, "p": r.patient_id, "r": r.request_id,
             "m": NOT_CLOSED_ALERT.format(request=r.request_id, patient=r.patient, caregiver=r.caregiver,
                                          end=f"{r.ends.astimezone(ops.MEXICO_CITY):%d/%m/%Y %H:%M}", hours=minutes // 60)})
        audit(db, user_id=None, institution_id=r.institution_id, action="visit_not_closed", entity="service_request",
              entity_id=r.request_id, detail={"after_minutes": minutes})
        publish(db, "request.updated", r.institution_id, request_id=r.request_id, status="not_closed")
        if alert_id:
            publish(db, "alert.created", r.institution_id, alert_id=alert_id, request_id=r.request_id)
    return len(rows)
