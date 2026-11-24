"""Live board snapshot (coordination; the owner sees every institution) and the real-time clock."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import MEXICO_CITY
from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.roles import COORDINATOR, OWNER
from app.services import care_plans
from app.services import dispatcher as dsp
from app.services import operations as ops

router = APIRouter(prefix="/api", tags=["board"])
TODAY = "(now() AT TIME ZONE 'America/Mexico_City')::date"
# A visit "in progress" belongs to today's board when it was scheduled today OR its service has not reached its
# planned end yet (a 12-h night service that began yesterday). A visit from an earlier day that nobody marked as
# finished (e.g. REQ-08939: arrived 22 Nov 15:09, never finished) is NOT "En visita" now.
SERVICE_END = "(SELECT max(x.planned_end) FROM assignments x WHERE x.request_id = r.request_id AND x.status = 'active')"
ON_BOARD = f"""((r.scheduled_for AT TIME ZONE 'America/Mexico_City')::date = {TODAY}
               OR (r.status = 'in_progress' AND {SERVICE_END} > now()))"""


@router.get("/time")
def server_time() -> dict:
    """Wall-clock time of the server in Mexico City. The UI syncs with it on load and every 5 min."""
    now = datetime.now(MEXICO_CITY)
    return {"now": now.isoformat(), "epoch_ms": int(now.timestamp() * 1000), "timezone": "America/Mexico_City"}


@router.get("/board")
def board(user: CurrentUser = Depends(require_role(COORDINATOR, OWNER)), db: Session = Depends(tenant_db)) -> dict:
    counters = db.execute(text(f"""
        SELECT count(*) FILTER (WHERE r.status = 'queued')                                    AS queued,
               count(*) FILTER (WHERE r.status = 'assigned' AND a.planned_start <= now())     AS on_the_way,
               count(*) FILTER (WHERE r.status = 'in_progress' AND {ON_BOARD})                AS in_visit,
               count(*) FILTER (WHERE r.status IN ('completed','closed')
                                AND (a.finished_at AT TIME ZONE 'America/Mexico_City')::date = {TODAY}) AS done_today
        FROM service_requests r
        LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active' AND a.leg = 1
        WHERE r.status IN ('queued','assigned','in_progress','completed','closed')
          AND r.scheduled_for > now() - interval '2 days'""")).mappings().one()

    waiting = db.execute(text("""
        SELECT r.request_id, r.institution_id, r.patient_id, r.priority, r.status_reason, r.scheduled_for, r.origin,
               s.name AS service_name, pe.first_name || ' ' || pe.paternal_surname AS patient_name,
               round(extract(epoch FROM now() - r.created_at) / 60)::int AS minutes_waiting
        FROM service_requests r JOIN services s USING (service_id)
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        WHERE r.status = 'queued'""")).mappings().all()
    # Same order the worker uses to dispatch (priority → patient risk → minutes waiting).
    by_id = {w["request_id"]: dict(w) for w in waiting}
    ordered = dsp.order_queue([ops.load_request(db, rid) for rid in by_id], ops.policy(), ops.now())
    queue = [{**by_id[r.request_id], "risk": round(r.risk, 2)} for r in ordered]

    alerts = db.execute(text("""
        SELECT alert_id, type, level, code, message, request_id, created_at, escalate_at, escalated_at FROM alerts
        WHERE status = 'open'
        ORDER BY (type = 'emergency_review') DESC, (level = 'critical') DESC, created_at DESC LIMIT 20""")).mappings().all()

    visits = db.execute(text(f"""
        SELECT r.request_id, r.patient_id, r.status, r.priority, r.scheduled_for, s.name AS service_name,
               pe.first_name || ' ' || pe.paternal_surname AS patient_name, pe.lat::float AS lat, pe.lon::float AS lon,
               c.first_name || ' ' || c.paternal_surname AS caregiver_name,
               rc.first_name || ' ' || rc.paternal_surname AS relay_caregiver_name,
               CASE WHEN b.assignment_id IS NOT NULL THEN a.planned_end END AS relay_at
        FROM service_requests r JOIN services s USING (service_id)
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active' AND a.leg = 1
        LEFT JOIN caregivers c ON c.caregiver_id = a.caregiver_id
        LEFT JOIN assignments b ON b.request_id = r.request_id AND b.status = 'active' AND b.leg = 2     -- relay
        LEFT JOIN caregivers rc ON rc.caregiver_id = b.caregiver_id
        WHERE {ON_BOARD}
          AND r.status NOT IN ('rejected','cancelled')
        ORDER BY r.scheduled_for""")).mappings().all()

    staff = db.execute(text("""
        SELECT caregiver_id, first_name || ' ' || paternal_surname AS name, type, base_lat::float AS lat,
               base_lon::float AS lon FROM caregivers WHERE active""")).mappings().all()

    # "Próximas visitas de hoy y mañana" (shown when nobody is waiting): requests that exist and are not started,
    # plus the care-plan visits the worker will create on the day (care_plans.forecast, same deterministic draw).
    soon = db.execute(text(f"""
        SELECT r.request_id, r.patient_id, r.scheduled_for, r.status, s.name AS service_name,
               pe.first_name || ' ' || pe.paternal_surname AS patient_name,
               c.first_name || ' ' || c.paternal_surname AS caregiver_name
        FROM service_requests r JOIN services s USING (service_id)
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active' AND a.leg = 1
        LEFT JOIN caregivers c ON c.caregiver_id = a.caregiver_id
        WHERE r.status IN ('validated','queued','assigned') AND r.scheduled_for > now()
          AND (r.scheduled_for AT TIME ZONE 'America/Mexico_City')::date <= {TODAY} + 1""")).mappings().all()
    upcoming = sorted([dict(v) for v in soon] + care_plans.forecast(db, days=2), key=lambda v: v["scheduled_for"])

    return {"now": ops.now().isoformat(), "counters": dict(counters), "queue": queue,
            "alerts": [dict(a) for a in alerts], "visits": [dict(v) for v in visits],
            "staff": [dict(s) for s in staff], "upcoming": upcoming}
