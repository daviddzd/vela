"""/personal (coordination): caregivers of the institution, who is on shift now, the day's timeline per person
(trip + visit), the week's load, out of service / back in service, and their bases for the map.

"Fuera de servicio" uses EXACTLY the same function as the demo panel (operations.caregiver_out_of_service):
pending visits are re-dispatched by the dispatcher (low/medium at once, high through approval or the time limit).
"Volver a servicio" closes the unavailability; new visits can be assigned to the person again.
Week load = hours of active assignments this week (Monday–Sunday) / (shift hours x working days per week).
Working days per week: config/simulation.yaml -> staffing.workdays_per_week (ASSUMPTION 6, LFT art. 69).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import MEXICO_CITY
from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.events import publish
from app.core.guards import not_found_or_cross_tenant
from app.core.roles import COORDINATOR
from app.services import dispatcher as dsp
from app.services import operations as ops

router = APIRouter(prefix="/api/staff", tags=["staff"])
COORD = require_role(COORDINATOR)


def _shift_hours(start: time, end: time) -> float:
    s = datetime.combine(date(2026, 1, 1), start)
    e = datetime.combine(date(2026, 1, 1), end)
    if e <= s:
        e += timedelta(days=1)
    return (e - s).total_seconds() / 3600


def _on_shift(start: time, end: time, now: datetime) -> bool:
    cg = dsp.Caregiver("x", frozenset(), start, end, 0.0, 0.0)
    return dsp.within_shift(cg, now, now + timedelta(minutes=1))


@router.get("")
def staff(user: CurrentUser = Depends(COORD), db: Session = Depends(tenant_db)) -> dict:
    now = ops.now()
    week_start = datetime.combine(now.date() - timedelta(days=now.weekday()), time.min, MEXICO_CITY)
    rows = db.execute(text("""
        SELECT c.caregiver_id, c.first_name || ' ' || c.paternal_surname || ' ' || c.maternal_surname AS name, c.type,
               c.shift, c.shift_start, c.shift_end, c.base_lat::float AS lat, c.base_lon::float AS lon, c.active,
               array_agg(DISTINCT k.skill ORDER BY k.skill) AS skills,
               (SELECT u.reason FROM caregiver_unavailability u WHERE u.caregiver_id = c.caregiver_id AND u.active
                ORDER BY u.starts_at DESC LIMIT 1) AS out_reason,
               -- live visits have a planned window; seed history only real arrival / finish times
               (SELECT coalesce(sum(extract(epoch FROM (coalesce(a.planned_end, a.finished_at)
                                                         - coalesce(a.planned_start, a.arrived_at)))), 0) / 3600
                FROM assignments a WHERE a.caregiver_id = c.caregiver_id AND a.status = 'active'
                  AND coalesce(a.planned_start, a.arrived_at) >= :ws AND coalesce(a.planned_start, a.arrived_at) < :we) AS week_hours,
               (SELECT count(*) FROM assignments a WHERE a.caregiver_id = c.caregiver_id AND a.status = 'active'
                  AND coalesce(a.planned_start, a.arrived_at) >= :ds AND coalesce(a.planned_start, a.arrived_at) < :de) AS visits_today
        FROM caregivers c JOIN caregiver_skills k USING (caregiver_id)
        GROUP BY c.caregiver_id ORDER BY c.caregiver_id"""),
        {"ws": week_start, "we": week_start + timedelta(days=7),
         "ds": datetime.combine(now.date(), time.min, MEXICO_CITY),
         "de": datetime.combine(now.date() + timedelta(days=1), time.min, MEXICO_CITY)}).mappings().all()
    workdays = float(ops.settings_yaml()["staffing"]["workdays_per_week"])   # ASSUMPTION, LFT art. 69
    out = []
    for r in rows:
        capacity = _shift_hours(r["shift_start"], r["shift_end"]) * workdays
        out.append({**dict(r), "shift_start": r["shift_start"].strftime("%H:%M"), "shift_end": r["shift_end"].strftime("%H:%M"),
                    "on_shift_now": r["active"] and r["out_reason"] is None and _on_shift(r["shift_start"], r["shift_end"], now),
                    "out_of_service": r["out_reason"] is not None, "week_hours": round(float(r["week_hours"]), 1),
                    "week_capacity_hours": round(capacity, 1),
                    "week_load_pct": round(100 * float(r["week_hours"]) / capacity, 1) if capacity else None})
    return {"now": now.isoformat(), "week_start": week_start.date().isoformat(), "workdays_per_week": workdays, "staff": out}


@router.get("/{caregiver_id}/day")
def day(caregiver_id: str, on: date | None = None, user: CurrentUser = Depends(COORD),
        db: Session = Depends(tenant_db)) -> dict:
    """The person's timeline for a day: for each visit, the trip (planned_start → arrival) and the visit itself."""
    if not db.scalar(text("SELECT 1 FROM caregivers WHERE caregiver_id = :c"), {"c": caregiver_id}):
        raise not_found_or_cross_tenant(db, user, "caregiver", caregiver_id)
    on = on or ops.now().date()
    start = datetime.combine(on, time.min, MEXICO_CITY)
    rows = db.execute(text("""
        SELECT a.assignment_id, r.request_id, r.status, r.priority, s.name AS service_name, a.planned_start, a.planned_end,
               a.travel_min::float AS travel_min, a.arrived_at, a.finished_at, r.patient_id,
               pe.first_name || ' ' || pe.paternal_surname AS patient_name
        FROM assignments a JOIN service_requests r USING (request_id) JOIN services s USING (service_id)
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        WHERE a.caregiver_id = :c AND a.status = 'active'
          AND coalesce(a.planned_start, a.arrived_at) >= :s AND coalesce(a.planned_start, a.arrived_at) < :e
        ORDER BY coalesce(a.planned_start, a.arrived_at)"""),
        {"c": caregiver_id, "s": start, "e": start + timedelta(days=1)}).mappings().all()
    c = db.execute(text("SELECT shift_start, shift_end FROM caregivers WHERE caregiver_id = :c"), {"c": caregiver_id}).one()
    visits = []
    for r in rows:
        r = dict(r)
        if r["planned_start"] is not None:           # live visits: trip, then the visit
            r["arrive_at"] = r["planned_start"] + timedelta(minutes=r["travel_min"] or 0)
        else:                                        # seed history: only real arrival / finish times
            r["arrive_at"] = r["arrived_at"]
            r["planned_end"] = r["finished_at"]
        visits.append(r)
    return {"date": on.isoformat(), "shift_start": c.shift_start.strftime("%H:%M"), "shift_end": c.shift_end.strftime("%H:%M"),
            "visits": visits}


class OutIn(BaseModel):
    reason: str = Field(min_length=3, max_length=200)


@router.post("/{caregiver_id}/out-of-service")
def out_of_service(caregiver_id: str, body: OutIn, user: CurrentUser = Depends(COORD),
                   db: Session = Depends(tenant_db)) -> dict:
    if not db.scalar(text("SELECT 1 FROM caregivers WHERE caregiver_id = :c"), {"c": caregiver_id}):
        raise not_found_or_cross_tenant(db, user, "caregiver", caregiver_id)
    if db.scalar(text("SELECT 1 FROM caregiver_unavailability WHERE caregiver_id = :c AND active"), {"c": caregiver_id}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta persona ya está fuera de servicio.")
    result = ops.caregiver_out_of_service(db, caregiver_id=caregiver_id, reason=body.reason, origin="coordinator",
                                          user_id=user.user_id)
    return result


@router.post("/{caregiver_id}/back-in-service")
def back_in_service(caregiver_id: str, user: CurrentUser = Depends(COORD), db: Session = Depends(tenant_db)) -> dict:
    if not db.scalar(text("SELECT 1 FROM caregivers WHERE caregiver_id = :c"), {"c": caregiver_id}):
        raise not_found_or_cross_tenant(db, user, "caregiver", caregiver_id)
    closed = db.execute(text("""UPDATE caregiver_unavailability SET active = false, ends_at = now()
                                WHERE caregiver_id = :c AND active RETURNING unavailability_id"""),
                        {"c": caregiver_id}).scalars().all()
    if not closed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta persona no estaba fuera de servicio.")
    audit(db, user_id=user.user_id, institution_id=user.institution_id, action="caregiver_back_in_service",
          entity="caregiver", entity_id=caregiver_id)
    publish(db, "request.updated", user.institution_id, caregiver_id=caregiver_id)
    return {"caregiver_id": caregiver_id, "back_in_service": True}
