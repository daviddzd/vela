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
                    service_id=p.service_id, scheduled_for=at, priority=p.base_priority, origin="care_plan",
                    care_plan_id=p.care_plan_id, plan_date=today))
        except Exception as exc:  # noqa: BLE001
            log.warning("care plan %s not created: %s", p.care_plan_id, exc)
    return created
