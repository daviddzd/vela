"""Requests that come from care plans (docs/spec/04, flow step 1: "una solicitud nace del plan de cuidado").

Each active plan has `times_per_week` visits. For every day we draw, deterministically, whether a
visit is due (probability times_per_week / 7) and at what time, from a hash of (care_plan_id, date):
the same plan and day always give the same answer, even after a restart, and over a month the number
of visits matches the plan.

The worker calls `create_due_requests()` every minute. A visit is released (the request is created)
2 h before its time, so during the day the board keeps receiving new requests in real time. Visits
less than 15 min ahead are skipped (too late to dispatch). The unique index (care_plan_id, plan_date)
makes it impossible to create the same visit twice.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import operations as ops
from app.services.dispatcher import MEXICO_CITY
from app.services.visit_rules import visit_time

RELEASE_BEFORE = timedelta(hours=2)
MIN_AHEAD = timedelta(minutes=15)
log = logging.getLogger("vela.care_plans")


def planned_visit(care_plan_id: str, day: date, times_per_week: float, service_id: str) -> datetime | None:
    """Time of the plan's visit on that day, or None if no visit is due. Pure and deterministic.
    The hour follows app/services/visit_rules.py (shared with the SIRAG-D simulation)."""
    digest = hashlib.sha256(f"{care_plan_id}|{day.isoformat()}".encode()).digest()
    draw = int.from_bytes(digest[:8], "big") / 2**64                   # uniform in [0, 1)
    if draw >= min(times_per_week / 7, 1.0):
        return None
    return visit_time(day, service_id, int.from_bytes(digest[8:16], "big") / 2**64)


def create_due_requests(db: Session, now: datetime | None = None) -> list[str]:
    """Create today's care-plan requests whose release time has arrived. Returns the new request ids."""
    now = now or ops.now()
    today = now.astimezone(MEXICO_CITY).date()
    plans = db.execute(text("""
        SELECT cp.care_plan_id, cp.patient_id, cp.institution_id, cp.service_id, cp.times_per_week::float AS tpw,
               i.schedule, pa.base_priority
        FROM care_plans cp JOIN patients pa USING (patient_id) JOIN institutions i ON i.institution_id = cp.institution_id
        WHERE cp.active AND pa.active AND i.active
          AND NOT EXISTS (SELECT 1 FROM service_requests r WHERE r.care_plan_id = cp.care_plan_id
                          AND r.plan_date = :today)"""), {"today": today}).all()
    created = []
    for p in plans:
        at = planned_visit(p.care_plan_id, today, p.tpw, p.service_id)
        if at is None or not (at - RELEASE_BEFORE <= now <= at - MIN_AHEAD):
            continue
        try:
            with db.begin_nested():   # one bad plan must not stop the others
                created.append(ops.create_request(
                    db, user_id=None, institution_id=p.institution_id, patient_id=p.patient_id,
                    service_id=p.service_id, scheduled_for=at,
                    priority=ops.effective_priority(db, p.patient_id, p.base_priority), origin="care_plan",
                    care_plan_id=p.care_plan_id, plan_date=today))
        except Exception as exc:  # noqa: BLE001
            log.warning("care plan %s not created: %s", p.care_plan_id, exc)
    return created


# ---- changes by the physician (team decision 22 Nov 2026) ----------------------------------------------
# A plan is never edited in place: the old plan ends and, for a change, a new plan replaces it. Effects on the
# requests the old plan ALREADY created for the future:
#   not assigned yet  -> cancelled, reason "care_plan_changed" ("plan de cuidado modificado")
#   already assigned  -> kept; coordination gets an alert to decide
# The new plan is used from the worker's next generation (the next minute it runs).

ALERT_ASSIGNED = ("Se modificó el plan de cuidado de {patient} ({service}). Hay {n} visita(s) futura(s) ya asignada(s) "
                  "de ese plan ({ids}): revisa si se mantienen.")
PENDING_UNASSIGNED = ("registered", "validated", "queued")


def end_plan(db: Session, *, plan_id: str, user_id: str) -> dict:
    plan = db.execute(text("""SELECT cp.care_plan_id, cp.patient_id, cp.institution_id, s.name AS service,
                                     pe.first_name || ' ' || pe.paternal_surname AS patient
                              FROM care_plans cp JOIN services s USING (service_id)
                              JOIN patients pa USING (patient_id) JOIN persons pe USING (person_id)
                              WHERE cp.care_plan_id = :p AND cp.active"""), {"p": plan_id}).one_or_none()
    if plan is None:
        return {"cancelled": [], "assigned": []}
    db.execute(text("UPDATE care_plans SET active = false, ended_at = now(), ended_by = :u WHERE care_plan_id = :p"),
               {"u": user_id, "p": plan_id})
    future = db.execute(text("""
        SELECT r.request_id, r.status FROM service_requests r
        WHERE r.care_plan_id = :p AND r.scheduled_for > now()
          AND r.status IN ('registered','validated','queued','assigned')"""), {"p": plan_id}).all()
    cancelled = [f.request_id for f in future if f.status in PENDING_UNASSIGNED]
    assigned = [f.request_id for f in future if f.status == "assigned"]
    for rid in cancelled:
        db.execute(text("UPDATE assignment_proposals SET status = 'superseded' WHERE request_id = :r AND status = 'open'"),
                   {"r": rid})
        db.execute(text("""UPDATE service_requests SET status = 'cancelled', status_reason = 'care_plan_changed'
                           WHERE request_id = :r"""), {"r": rid})
        ops.publish(db, "request.updated", plan.institution_id, request_id=rid, status="cancelled")
    if assigned:
        alert_id = db.scalar(text("""INSERT INTO alerts (institution_id, type, level, patient_id, message)
                                     VALUES (:i, 'care_plan', 'watch', :p, :m) RETURNING alert_id"""),
                             {"i": plan.institution_id, "p": plan.patient_id,
                              "m": ALERT_ASSIGNED.format(patient=plan.patient, service=plan.service, n=len(assigned),
                                                         ids=", ".join(assigned))})
        ops.publish(db, "alert.created", plan.institution_id, alert_id=alert_id)
    return {"cancelled": cancelled, "assigned": assigned}


def new_plan(db: Session, *, patient_id: str, institution_id: str, service_id: str, times_per_week: float,
             reason: str, user_id: str, replaces: str | None = None) -> str:
    return db.scalar(text("""
        INSERT INTO care_plans (care_plan_id, patient_id, institution_id, service_id, times_per_week, reason, active,
                                created_by, created_at, replaces)
        VALUES ('PLN-' || upper(substr(gen_random_uuid()::text, 1, 8)), :p, :i, :s, :t, :r, true, :u, now(), :old)
        RETURNING care_plan_id"""), {"p": patient_id, "i": institution_id, "s": service_id, "t": times_per_week,
                                     "r": reason, "u": user_id, "old": replaces})
