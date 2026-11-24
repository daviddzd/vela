"""Operations (TPS): service requests, validation, assignment and visit states.

This is the database side. The decision itself (who goes) is made by app/services/dispatcher.py,
which knows nothing about the database. Here we only: load the inputs, call the dispatcher, and save
the result. Every function receives a tenant-scoped session (RLS already applied).

Request states (docs/spec/03_base_de_datos.md):
  registered → validated → queued → assigned → in_progress → completed → closed
  exits: rejected (failed validation), cancelled, unattended (time passed and nobody went)
`queued` means "waiting": either for a free caregiver, or (high priority) for the coordinator to
approve one of the 3 proposals.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import yaml
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.events import publish
from app.services import dispatcher as dsp
from app.services import coverage, labor
from app.services.dispatcher import MEXICO_CITY

AUTO_PRIORITIES = ("low", "medium")       # applied at once (CLAUDE.md rule 3)
DUPLICATE_WINDOW = timedelta(hours=2)
MAX_DAYS_AHEAD = 30
INSERT_ATTEMPTS = 3                       # retries if another request took the slot meanwhile
OPEN_STATUSES = ("registered", "validated", "queued", "assigned", "in_progress", "completed", "closed")


class NotAvailable(Exception):
    """The caregiver chosen by the coordinator is no longer free. Carries fresh options."""
    def __init__(self, options: list[dsp.Option]):
        super().__init__("caregiver no longer available")
        self.options = options


class InvalidState(Exception):
    """The request/visit is not in a state that allows the action."""


# ---- configuration ------------------------------------------------------------------------------

def config_dir() -> Path:
    return Path(os.environ.get("CONFIG_DIR", Path(__file__).resolve().parents[3] / "config"))


def risk_multipliers() -> dict[str, float]:
    return settings_yaml()["health_markov"]["risk_multipliers"]


@lru_cache
def settings_yaml() -> dict:
    return yaml.safe_load((config_dir() / "simulation.yaml").read_text(encoding="utf-8"))


def late_tolerance() -> timedelta:
    """A visit may start up to this much after the requested time (same value as SIRAG-D)."""
    return timedelta(minutes=settings_yaml()["dispatch"]["late_tolerance_minutes"])


def policy() -> str:
    return os.environ.get("DISPATCH_POLICY", dsp.DEFAULT_POLICY)


def now() -> datetime:
    return datetime.now(MEXICO_CITY)


# ---- loading dispatcher inputs ------------------------------------------------------------------

def load_traffic(db: Session) -> dsp.TrafficProfile:
    rows = db.execute(text("SELECT day_type, hour, avg_speed_kmh FROM traffic_hourly_profile")).all()
    return dsp.TrafficProfile({(r.day_type, r.hour): float(r.avg_speed_kmh) for r in rows})


def risk_flags(r) -> dict[str, bool]:
    """Which risk multipliers apply (row with v_persons columns). Health data: use only with health_data consent."""
    return {"chronic_lung_disease": r.chronic_lung_disease, "heart_disease": r.heart_disease,
            "stroke": r.stroke, "diabetes": r.diabetes,
            "dependency_severe": r.dependency_level == "severe",
            "dependency_moderate": r.dependency_level == "moderate",
            "age_80_plus": r.age_group == "80+", "no_chronic_disease": r.chronic_disease_count == 0}


def risk_level(risk: float) -> str:
    """'low' / 'medium' / 'high' with the cutoffs of config/simulation.yaml (health_markov.risk_levels, ASSUMPTION)."""
    cut = settings_yaml()["health_markov"]["risk_levels"]
    return "high" if risk >= cut["high_from"] else "medium" if risk >= cut["medium_from"] else "low"


def load_request(db: Session, request_id: str) -> dsp.Request:
    r = db.execute(text("""
        SELECT r.request_id, r.priority, r.scheduled_for, r.created_at, s.required_skill,
               ins.duration_min, vp.lat, vp.lon, vp.chronic_lung_disease, vp.heart_disease, vp.stroke,
               vp.diabetes, vp.dependency_level, vp.age_group, vp.chronic_disease_count,
               coalesce((SELECT c.is_valid FROM v_consents c WHERE c.patient_id = r.patient_id
                         AND c.type = 'health_data'), false) AS health_consent
        FROM service_requests r
        JOIN services s ON s.service_id = r.service_id
        JOIN institution_services ins ON ins.institution_id = r.institution_id AND ins.service_id = r.service_id
        JOIN patients pa ON pa.patient_id = r.patient_id
        JOIN v_persons vp ON vp.person_id = pa.person_id
        WHERE r.request_id = :id"""), {"id": request_id}).one()
    flags = risk_flags(r)
    # Consent also inside the dispatcher (CLAUDE.md rule 5, docs/spec/11): without a valid health_data consent the
    # health-based risk is NOT used; the request competes only by its priority (risk = 1, neutral).
    risk = dsp.patient_risk(flags, risk_multipliers()) if r.health_consent else 1.0
    return dsp.Request(r.request_id, r.priority, r.required_skill, r.scheduled_for, r.duration_min,
                       float(r.lat), float(r.lon), r.created_at, risk)


def load_caregivers(db: Session, institution_id: str, around: datetime) -> list[dsp.Caregiver]:
    """Active caregivers of the institution with their booked windows near that day."""
    rows = db.execute(text("""
        SELECT c.caregiver_id, c.shift_start, c.shift_end, c.base_lat, c.base_lon, c.rest_day,
               array_agg(DISTINCT k.skill) AS skills
        FROM caregivers c JOIN caregiver_skills k USING (caregiver_id)
        WHERE c.institution_id = :inst AND c.active
          AND NOT EXISTS (SELECT 1 FROM caregiver_unavailability u WHERE u.caregiver_id = c.caregiver_id AND u.active
                          AND u.starts_at <= now() AND (u.ends_at IS NULL OR u.ends_at > now()))
        GROUP BY c.caregiver_id"""), {"inst": institution_id}).all()
    busy_rows = db.execute(text("""
        SELECT caregiver_id, planned_start, planned_end FROM assignments
        WHERE institution_id = :inst AND status = 'active' AND planned_start IS NOT NULL
          AND planned_end > :lo AND planned_start < :hi"""),
        {"inst": institution_id, "lo": around - timedelta(days=2), "hi": around + timedelta(days=2)}).all()
    busy: dict[str, list] = {}
    for b in busy_rows:
        busy.setdefault(b.caregiver_id, []).append((b.planned_start, b.planned_end))
    return [dsp.Caregiver(r.caregiver_id, frozenset(r.skills), r.shift_start, r.shift_end,
                          float(r.base_lat), float(r.base_lon), tuple(busy.get(r.caregiver_id, ())),
                          rest_day=r.rest_day)
            for r in rows]


# ---- labor rules in the operation (app/services/labor.py) ------------------------------------------------

LABOR_ALERT = ("{name}: su turno {start}–{end} es jornada {kind} de {hours:g} h y excede el máximo de {max:g} h "
               "del art. 61 de la Ley Federal del Trabajo. Vela no cambia la plantilla: lo decide la institución.")


def labor_alerts(db: Session) -> int:
    """One open alert per caregiver whose shift exceeds the legal maximum (only nocturna shifts can, see labor.py).
    Idempotent: it is not created again while the previous one is open."""
    created = 0
    for c in db.execute(text("""SELECT caregiver_id, institution_id, first_name || ' ' || paternal_surname AS name,
                                       shift_start, shift_end FROM caregivers WHERE active""")).all():
        legal = labor.legal_shift(c.shift_start, c.shift_end)
        if not legal["exceeds"]:
            continue
        code = f"legal_hours:{c.caregiver_id}"
        if db.scalar(text("SELECT 1 FROM alerts WHERE code = :c AND status <> 'resolved'"), {"c": code}):
            continue
        alert_id = db.scalar(text("""INSERT INTO alerts (institution_id, type, level, message, code)
                                     VALUES (:i, 'labor', 'watch', :m, :c) RETURNING alert_id"""),
                             {"i": c.institution_id, "c": code, "m": LABOR_ALERT.format(
                                 name=c.name, start=c.shift_start.strftime("%H:%M"), end=c.shift_end.strftime("%H:%M"),
                                 kind=legal["type"], hours=legal["hours"], max=legal["max_hours"])})
        publish(db, "alert.created", c.institution_id, alert_id=alert_id)
        created += 1
    return created


# ---- coverage of the week (app/services/coverage.py) ----------------------------------------------------

SKILL_ES = {"physician": "medicina", "nursing": "enfermería", "therapy": "terapia", "caregiving": "cuidados"}  # = es.ts
COVERAGE_ALERT = ("{day} {start}–{end}: sin {skill} en turno (por día de descanso o fuera de servicio). "
                  "Cambia un día de descanso en Personal si hace falta cubrirlo.")


def coverage_people(db: Session, institution_id: str) -> list[coverage.Person]:
    rows = db.execute(text("""
        SELECT c.caregiver_id, c.shift_start, c.shift_end, c.rest_day, c.active, array_agg(DISTINCT k.skill) AS skills,
               coalesce((SELECT array_agg(ARRAY[u.starts_at::text, coalesce(u.ends_at::text, '')])
                         FROM caregiver_unavailability u WHERE u.caregiver_id = c.caregiver_id AND u.active), '{}') AS out
        FROM caregivers c JOIN caregiver_skills k USING (caregiver_id)
        WHERE c.institution_id = :i GROUP BY c.caregiver_id"""), {"i": institution_id}).all()
    return [coverage.Person(dsp.Caregiver(r.caregiver_id, frozenset(r.skills), r.shift_start, r.shift_end, 0.0, 0.0,
                                          active=r.active, rest_day=r.rest_day),
                            tuple((datetime.fromisoformat(s), datetime.fromisoformat(e) if e else None) for s, e in r.out))
            for r in rows]


def coverage_gaps(db: Session, institution_id: str, first_day=None) -> list[dict]:
    """Gaps of the next 7 days (from today, Mexico City) of one institution; gaps that are already over are left out.
    It looks from the day BEFORE: a night gap that began yesterday at 21:30 keeps that start after midnight (same
    message, same alert code) instead of turning into a new "00:00–08:00" gap."""
    first = first_day or now().date()
    week_end = datetime.combine(first + timedelta(days=7), datetime.min.time(), MEXICO_CITY)
    return [g for g in coverage.week_gaps(coverage_people(db, institution_id), first - timedelta(days=1), days=8)
            if g["end"] > now() and g["start"] < week_end]


def coverage_message(gap: dict) -> str:
    """'Martes 01/12/2026 8:00–10:00: sin enfermería en turno …' (a gap across midnight names the day it ends)."""
    s, e = gap["start"].astimezone(MEXICO_CITY), gap["end"].astimezone(MEXICO_CITY)
    hm = lambda t: f"{t.hour}:{t.minute:02d}"                                     # noqa: E731
    if e.date() == s.date():
        end = hm(e)
    elif e.date() == s.date() + timedelta(days=1) and e.hour == 0 and e.minute == 0:
        end = "24:00"
    else:
        end = f"{labor.WEEKDAYS_ES[e.isoweekday()]} {e:%d/%m/%Y} {hm(e)}"
    return COVERAGE_ALERT.format(day=f"{labor.WEEKDAYS_ES[s.isoweekday()].capitalize()} {s:%d/%m/%Y}", start=hm(s),
                                 end=end, skill=SKILL_ES.get(gap["skill"], gap["skill"]))


def coverage_alerts(db: Session) -> int:
    """One open alert per gap of the next 7 days (code coverage:<skill>:<start>); alerts of gaps that no longer exist
    (someone changed a rest day, came back to service, or the gap is over) are resolved. Returns how many were created."""
    created = 0
    for inst in db.execute(text("SELECT institution_id FROM institutions WHERE active")).scalars().all():
        gaps = coverage_gaps(db, inst)
        codes = {f"coverage:{g['skill']}:{g['start'].astimezone(MEXICO_CITY):%Y%m%d%H%M}": g for g in gaps}
        open_codes = set(db.execute(text("""SELECT code FROM alerts WHERE institution_id = :i AND type = 'coverage'
                                            AND status <> 'resolved'"""), {"i": inst}).scalars().all())
        stale = list(open_codes - set(codes))
        if stale:
            db.execute(text("""UPDATE alerts SET status = 'resolved' WHERE institution_id = :i AND type = 'coverage'
                               AND code = ANY(:c) AND status <> 'resolved'"""), {"i": inst, "c": stale})
        for code, g in codes.items():
            if code in open_codes:
                continue
            alert_id = db.scalar(text("""INSERT INTO alerts (institution_id, type, level, message, code)
                                         VALUES (:i, 'coverage', 'watch', :m, :c) RETURNING alert_id"""),
                                 {"i": inst, "m": coverage_message(g), "c": code})
            publish(db, "alert.created", inst, alert_id=alert_id)
            created += 1
    return created


def set_rest_day(db: Session, *, caregiver_id: str, rest_day: int, user_id: str) -> dict:
    """Change the weekly rest day. Pending visits that now fall on it are re-dispatched with the SAME logic as
    "fuera de servicio" (low/medium at once, high through approval or the time limit)."""
    inst, old = db.execute(text("SELECT institution_id, rest_day FROM caregivers WHERE caregiver_id = :c"),
                           {"c": caregiver_id}).one()
    db.execute(text("UPDATE caregivers SET rest_day = :d WHERE caregiver_id = :c"), {"d": rest_day, "c": caregiver_id})
    cg = next((c for c in load_caregivers(db, inst, now()) if c.caregiver_id == caregiver_id), None)
    moved = []
    for a in db.execute(text("""SELECT assignment_id, request_id, planned_start, planned_end FROM assignments
                                WHERE caregiver_id = :c AND status = 'active' AND arrived_at IS NULL
                                  AND planned_start > now()"""), {"c": caregiver_id}).all():
        if cg is None or not dsp.within_shift(cg, a.planned_start, a.planned_end):
            if release_request(db, a.request_id, a.assignment_id):
                moved.append(a.request_id)
    if moved:
        dispatch_requests(db, inst, moved)
    audit(db, user_id=user_id, institution_id=inst, action="caregiver_rest_day_changed", entity="caregiver",
          entity_id=caregiver_id, detail={"from": old, "to": rest_day, "redispatched": moved})
    return {"caregiver_id": caregiver_id, "rest_day": rest_day, "redispatched": moved}


def load_holds(db: Session, institution_id: str) -> list[dsp.Hold]:
    """Active reservations: the rank-1 proposal of each high-priority request still waiting for approval,
    for approval.hold_minutes after it was proposed (shared rule with SIRAG-D: dispatcher.apply_holds)."""
    minutes = settings_yaml()["approval"]["hold_minutes"]
    rows = db.execute(text("""
        SELECT p.request_id, p.caregiver_id, p.planned_start, p.planned_end,
               p.relay_caregiver_id, p.relay_planned_start, p.relay_planned_end,
               p.created_at + :m * interval '1 minute' AS expires
        FROM assignment_proposals p JOIN service_requests r USING (request_id)
        WHERE p.institution_id = :i AND p.status = 'open' AND p.rank = 1 AND r.status = 'queued'"""),
        {"i": institution_id, "m": minutes}).all()
    holds = [dsp.Hold(r.request_id, r.caregiver_id, r.planned_start, r.planned_end, r.expires) for r in rows]
    return holds + [dsp.Hold(r.request_id, r.relay_caregiver_id, r.relay_planned_start, r.relay_planned_end, r.expires)
                    for r in rows if r.relay_caregiver_id]        # a relay reserves both people


def options_for(db: Session, request_id: str) -> list[dsp.Option]:
    """Options at the earliest feasible arrival, from the requested time up to the late tolerance.
    Other requests' reservations are respected; this request may use its own."""
    req = load_request(db, request_id)
    inst = db.scalar(text("SELECT institution_id FROM service_requests WHERE request_id = :id"), {"id": request_id})
    pool = dsp.apply_holds(load_caregivers(db, inst, req.scheduled_for), load_holds(db, inst), now(), request_id)
    factor, extra = traffic_effects(db, [req])
    return dsp.earliest_options(req, pool, load_traffic(db), policy(), now(), req.scheduled_for + late_tolerance(),
                                factor, extra.get(req.request_id))


def traffic_effects(db: Session, requests: list[dsp.Request]):
    """Current traffic condition (input data: a real roadblock or a demo scenario) as the dispatcher's
    extra_traffic_factor and per-request extra minutes for trips that start or end in a blocked district."""
    row = db.execute(text("""SELECT extra_factor::float AS f, blocked_districts AS b, extra_minutes AS m
                             FROM traffic_conditions WHERE active ORDER BY started_at DESC LIMIT 1""")).first()
    if row is None:
        return 1.0, {}
    blocked = set(row.b)
    centroids = {d: (float(la), float(lo)) for d, la, lo in db.execute(text("SELECT district_id, lat, lon FROM districts")).all()}

    def district_of(lat: float, lon: float) -> str:      # ASSUMPTION: nearest district centroid
        return min(centroids, key=lambda d: dsp.haversine_km(lat, lon, *centroids[d]))

    extra = {}
    for r in requests:
        patient_blocked = district_of(r.lat, r.lon) in blocked
        extra[r.request_id] = (lambda cg, pb=patient_blocked:
                               row.m if (pb or district_of(cg.lat, cg.lon) in blocked) else 0.0)
    return row.f, extra


def effective_priority(db: Session, patient_id: str, base: str) -> str:
    """Base priority, or 'high' while an APPROVED contingency override is active (base is never modified)."""
    raised = db.scalar(text("SELECT 1 FROM priority_overrides WHERE patient_id = :p AND active LIMIT 1"), {"p": patient_id})
    return "high" if raised else base


def caregiver_out_of_service(db: Session, *, caregiver_id: str, reason: str, origin: str, user_id: str | None,
                             run_id: str | None = None) -> dict:
    """Mark a caregiver unavailable and re-dispatch their pending visits with the SAME logic: low/medium are
    reassigned at once; high get proposals (approval, time limit). Coordination gets an alert."""
    inst = db.scalar(text("SELECT institution_id FROM caregivers WHERE caregiver_id = :c"), {"c": caregiver_id})
    db.execute(text("""INSERT INTO caregiver_unavailability (caregiver_id, institution_id, reason, origin, run_id)
                       VALUES (:c, :i, :r, :o, :run)"""), {"c": caregiver_id, "i": inst, "r": reason, "o": origin, "run": run_id})
    rows = db.execute(text("""
        SELECT request_id, assignment_id FROM assignments
        WHERE caregiver_id = :c AND status = 'active' AND arrived_at IS NULL AND planned_end > now()"""),
        {"c": caregiver_id}).all()
    pending = [r.request_id for r in rows if release_request(db, r.request_id, r.assignment_id)]
    for rid in pending:
        db.execute(text("UPDATE assignment_proposals SET status = 'superseded' WHERE request_id = :r AND status = 'open'"),
                   {"r": rid})
    dispatch_requests(db, inst, list(pending))
    result = dict(db.execute(text("""SELECT status, count(*) FROM service_requests WHERE request_id = ANY(:ids)
                                     GROUP BY 1"""), {"ids": list(pending)}).all()) if pending else {}
    name = db.scalar(text("SELECT first_name || ' ' || paternal_surname FROM caregivers WHERE caregiver_id = :c"), {"c": caregiver_id})
    alert_id = db.scalar(text("""INSERT INTO alerts (institution_id, type, level, message, code)
                                 VALUES (:i, 'anomaly', 'high', :m, NULL) RETURNING alert_id"""),
                         {"i": inst, "m": f"{name} quedó fuera de servicio. {len(pending)} visita(s) pendiente(s): "
                                          f"{result.get('assigned', 0)} reasignada(s) y {result.get('queued', 0)} en espera "
                                          "(las de prioridad alta, en Aprobaciones)."})
    publish(db, "alert.created", inst, alert_id=alert_id)
    audit(db, user_id=user_id, institution_id=inst, action="caregiver_out_of_service", entity="caregiver",
          entity_id=caregiver_id, detail={"reason": reason, "origin": origin, "pending": len(pending), "result": result})
    return {"caregiver_id": caregiver_id, "institution_id": inst, "pending": len(pending), "result": result}


def release_request(db: Session, request_id: str, assignment_id: str) -> bool:
    """A person of an assignment can no longer go. One person: the request goes back to the queue (True).
    Relay (two people): if nobody has arrived yet, BOTH legs are cancelled and the whole service is re-dispatched
    (True); if the first person is already there, only the relay is cancelled, the service stays in progress and
    coordination gets an alert to cover the relay (False: nothing to re-dispatch)."""
    started = db.scalar(text("""SELECT bool_or(arrived_at IS NOT NULL) FROM assignments
                                WHERE request_id = :r AND status = 'active'"""), {"r": request_id})
    if started:
        db.execute(text("UPDATE assignments SET status = 'cancelled' WHERE assignment_id = :a"), {"a": assignment_id})
        inst, patient = db.execute(text("SELECT institution_id, patient_id FROM service_requests WHERE request_id = :r"),
                                   {"r": request_id}).one()
        alert_id = db.scalar(text("""INSERT INTO alerts (institution_id, type, level, patient_id, message, request_id, code)
                                     VALUES (:i, 'anomaly', 'high', :p, :m, :r, 'relay_uncovered')
                                     ON CONFLICT (request_id, code) WHERE request_id IS NOT NULL DO NOTHING
                                     RETURNING alert_id"""),
                             {"i": inst, "p": patient, "r": request_id, "m": RELAY_UNCOVERED.format(request_id=request_id)})
        if alert_id:
            publish(db, "alert.created", inst, alert_id=alert_id, request_id=request_id)
        return False
    db.execute(text("UPDATE assignments SET status = 'cancelled' WHERE request_id = :r AND status = 'active'"),
               {"r": request_id})
    set_status(db, request_id, "queued", "caregiver_unavailable")
    return True


RELAY_UNCOVERED = ("La persona que iba a hacer el relevo de la solicitud {request_id} ya no puede ir. La primera persona "
                   "sigue en el domicilio: busca quién la releve al final de su turno.")


def duty_coordinator(db: Session, institution_id: str) -> str:
    """User recorded as `assigned_by` for automatic assignments (same convention as the seed)."""
    return db.scalar(text("""SELECT user_id FROM users WHERE role = 'coordinator' AND active
                             AND institution_id = :i ORDER BY user_id LIMIT 1"""), {"i": institution_id})


# ---- requests -----------------------------------------------------------------------------------

def create_request(db: Session, *, user_id: str | None, institution_id: str, patient_id: str, service_id: str,
                   scheduled_for: datetime, priority: str, origin: str,
                   care_plan_id: str | None = None, plan_date=None) -> str:
    """Register, validate and dispatch a request. Returns its id (look at its status afterwards)."""
    if scheduled_for.tzinfo is None:          # a time typed in the form is Mexico City time
        scheduled_for = scheduled_for.replace(tzinfo=MEXICO_CITY)
    request_id = db.scalar(text("""
        INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                                      scheduled_for, created_at, status, care_plan_id, plan_date)
        VALUES (:inst, :p, :s, :o, :prio, :at, now(), 'registered', :cp, :pd) RETURNING request_id"""),
        {"inst": institution_id, "p": patient_id, "s": service_id, "o": origin, "prio": priority,
         "at": scheduled_for, "cp": care_plan_id, "pd": plan_date})
    reason, duplicate_of = validate(db, request_id)
    if reason:
        db.execute(text("""UPDATE service_requests SET status = 'rejected', status_reason = :r,
                           duplicate_of = :d WHERE request_id = :id"""),
                   {"r": reason, "d": duplicate_of, "id": request_id})
        audit(db, user_id=user_id, institution_id=institution_id, action="request_rejected",
              entity="service_request", entity_id=request_id, allowed=False, detail={"reason": reason})
        publish(db, "request.created", institution_id, request_id=request_id, status="rejected")
        return request_id
    set_status(db, request_id, "validated")
    audit(db, user_id=user_id, institution_id=institution_id, action="request_created",
          entity="service_request", entity_id=request_id, detail={"priority": priority, "origin": origin})
    publish(db, "request.created", institution_id, request_id=request_id, status="validated")
    dispatch_requests(db, institution_id, [request_id])
    return request_id


def validate(db: Session, request_id: str) -> tuple[str | None, str | None]:
    """Return (reason_code, duplicate_of). reason_code None = valid. Codes are translated in es.ts."""
    r = db.execute(text("""
        SELECT r.patient_id, r.service_id, r.scheduled_for, pa.active AS patient_active,
               coalesce(ins.active, false) AS service_active,
               coalesce((SELECT is_valid FROM v_consents c
                         WHERE c.patient_id = r.patient_id AND c.type = 'home_care'), false) AS home_care
        FROM service_requests r
        JOIN patients pa ON pa.patient_id = r.patient_id
        LEFT JOIN institution_services ins ON ins.institution_id = r.institution_id
                                          AND ins.service_id = r.service_id
        WHERE r.request_id = :id"""), {"id": request_id}).one()
    if not r.patient_active:
        return "patient_inactive", None
    if not r.home_care:
        return "no_home_care_consent", None
    if not r.service_active:
        return "service_inactive", None
    if r.scheduled_for < now() - timedelta(minutes=5) or r.scheduled_for > now() + timedelta(days=MAX_DAYS_AHEAD):
        return "invalid_time", None
    dup = db.scalar(text("""
        SELECT request_id FROM service_requests
        WHERE patient_id = :p AND service_id = :s AND request_id <> :id AND status = ANY(:open)
          AND scheduled_for BETWEEN :at - :w AND :at + :w
        ORDER BY created_at LIMIT 1"""),
        {"p": r.patient_id, "s": r.service_id, "id": request_id, "open": list(OPEN_STATUSES),
         "at": r.scheduled_for, "w": DUPLICATE_WINDOW})
    if dup:
        return "duplicate", dup
    return None, None


def set_status(db: Session, request_id: str, status: str, reason: str | None = None) -> None:
    db.execute(text("UPDATE service_requests SET status = :s, status_reason = :r WHERE request_id = :id"),
               {"s": status, "r": reason, "id": request_id})


# ---- dispatching --------------------------------------------------------------------------------

def dispatch_requests(db: Session, institution_id: str, request_ids: list[str]) -> None:
    """Run the dispatcher on waiting requests of one institution and save the decisions.
    low/medium → assignment now; high → 3 proposals for the coordinator; nobody free → queued."""
    if not request_ids:
        return
    requests = [load_request(db, rid) for rid in request_ids]
    caregivers = dsp.apply_holds(load_caregivers(db, institution_id, min(r.scheduled_for for r in requests)),
                                 load_holds(db, institution_id), now())
    # Same function as SIRAG-D: earliest arrival from the requested time up to the late tolerance.
    latest = {r.request_id: r.scheduled_for + late_tolerance() for r in requests}
    factor, extra = traffic_effects(db, requests)
    decisions = dsp.dispatch_window(requests, caregivers, load_traffic(db), policy(), now(), latest, factor, extra)
    for d in decisions:
        rid = d.request.request_id
        if d.request.priority in AUTO_PRIORITIES:
            if d.chosen and save_assignment(db, institution_id, rid, d.options, approval="auto",
                                            assigned_by=duty_coordinator(db, institution_id)):
                continue
            set_status(db, rid, "queued", "no_caregiver_available")
        else:
            save_proposals(db, institution_id, rid, d.options[:3])
            set_status(db, rid, "queued", "awaiting_approval" if d.options else "no_caregiver_available")


def save_assignment(db: Session, institution_id: str, request_id: str, options: list[dsp.Option], *,
                    approval: str, assigned_by: str) -> str | None:
    """Insert the assignment with the first option that the database accepts.

    The EXCLUDE constraint `no_caregiver_overlap` is the final judge: if another request booked the
    same window a moment ago, the insert fails inside a SAVEPOINT, we recompute and try again."""
    for _ in range(INSERT_ATTEMPTS):
        if not options:
            return None
        o = options[0]
        try:
            with db.begin_nested():              # a relay inserts both people, or neither
                ids = [db.scalar(text("""
                    INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval,
                                             assigned_at, planned_start, planned_end, travel_min, leg)
                    VALUES (:r, :i, :c, :by, :ap, now(), :ps, :pe, :t, :leg) RETURNING assignment_id"""),
                    {"r": request_id, "i": institution_id, "c": leg.caregiver_id, "by": assigned_by,
                     "ap": approval, "ps": leg.planned_start, "pe": leg.planned_end, "t": leg.travel_min, "leg": n})
                       for n, leg in enumerate(o.legs, start=1)]
            aid = ids[0]
        except IntegrityError:
            options = options_for(db, request_id)   # someone took the slot: recompute
            continue
        set_status(db, request_id, "assigned")
        db.execute(text("""UPDATE assignment_proposals SET status = CASE WHEN caregiver_id = :c
                           THEN 'approved' ELSE 'superseded' END
                           WHERE request_id = :r AND status = 'open'"""), {"c": o.caregiver_id, "r": request_id})
        audit(db, user_id=assigned_by, institution_id=institution_id,
              action={"auto": "assignment_auto", "timeout": "assignment_approved_by_timeout"}.get(approval,
                                                                                            "assignment_approved"),
              entity="assignment", entity_id=aid,
              detail={"request_id": request_id, "caregiver_id": o.caregiver_id, "travel_min": o.travel_min,
                      "policy": policy(), **({"relay_caregiver_id": o.relay.caregiver_id, "relay_assignment_id": ids[1],
                                              "relay_at": o.planned_end.isoformat()} if o.relay else {})})
        publish(db, "assignment.approved", institution_id, request_id=request_id, assignment_id=aid,
                approval=approval)
        return aid
    return None


def save_proposals(db: Session, institution_id: str, request_id: str, options: list[dsp.Option]) -> None:
    """Replace the open proposals of a high-priority request: rank 1 = proposed, 2–3 = alternatives."""
    db.execute(text("UPDATE assignment_proposals SET status = 'superseded' "
                    "WHERE request_id = :r AND status = 'open'"), {"r": request_id})
    for rank, o in enumerate(options[:3], start=1):
        db.execute(text("""
            INSERT INTO assignment_proposals (request_id, institution_id, rank, caregiver_id, travel_min,
                                              planned_start, planned_end, policy, relay_caregiver_id,
                                              relay_travel_min, relay_planned_start, relay_planned_end)
            VALUES (:r, :i, :rank, :c, :t, :ps, :pe, :pol, :rc, :rt, :rps, :rpe)"""),
            {"r": request_id, "i": institution_id, "rank": rank, "c": o.caregiver_id, "t": o.travel_min,
             "ps": o.planned_start, "pe": o.planned_end, "pol": policy(),
             "rc": o.relay and o.relay.caregiver_id, "rt": o.relay and o.relay.travel_min,
             "rps": o.relay and o.relay.planned_start, "rpe": o.relay and o.relay.planned_end})
    if options:
        publish(db, "assignment.proposed", institution_id, request_id=request_id)


def approve(db: Session, *, user_id: str, institution_id: str, request_id: str, caregiver_id: str) -> str:
    """Coordinator approves (or overrides with) a caregiver for a high-priority request.
    If that caregiver is no longer free, new proposals are saved and NotAvailable is raised."""
    status = db.scalar(text("SELECT status FROM service_requests WHERE request_id = :r FOR UPDATE"),
                       {"r": request_id})
    if status != "queued":
        raise InvalidState(status)
    options = options_for(db, request_id)
    chosen = [o for o in options if o.caregiver_id == caregiver_id]
    if chosen:
        aid = save_assignment(db, institution_id, request_id, chosen, approval="coordinator",
                              assigned_by=user_id)
        if aid:
            return aid
        options = options_for(db, request_id)
    save_proposals(db, institution_id, request_id, options[:3])
    set_status(db, request_id, "queued", "awaiting_approval" if options else "no_caregiver_available")
    raise NotAvailable(options[:3])


def reassign(db: Session, *, user_id: str, institution_id: str, assignment_id: str, caregiver_id: str) -> str:
    """Coordinator override of an existing assignment (CLAUDE.md rule 3). The old row stays as
    'reassigned' for history; the new one is active."""
    a = db.execute(text("""SELECT request_id, caregiver_id, arrived_at FROM assignments
                           WHERE assignment_id = :a AND status = 'active' FOR UPDATE"""),
                   {"a": assignment_id}).one_or_none()
    if a is None or a.arrived_at is not None or db.scalar(text(
            "SELECT bool_or(arrived_at IS NOT NULL) FROM assignments WHERE request_id = :r AND status = 'active'"),
            {"r": a.request_id}):
        raise InvalidState("not reassignable")
    # A relay is reassigned as a whole: both people are released and the service is planned again
    db.execute(text("UPDATE assignments SET status = 'reassigned' WHERE request_id = :r AND status = 'active'"),
               {"r": a.request_id})
    chosen = [o for o in options_for(db, a.request_id) if o.caregiver_id == caregiver_id]
    new_id = save_assignment(db, institution_id, a.request_id, chosen, approval="coordinator",
                             assigned_by=user_id) if chosen else None
    if new_id is None:
        raise NotAvailable(options_for(db, a.request_id)[:3])
    audit(db, user_id=user_id, institution_id=institution_id, action="assignment_reassigned",
          entity="assignment", entity_id=new_id,
          detail={"previous": assignment_id, "from": a.caregiver_id, "to": caregiver_id})
    return new_id


# ---- visits -------------------------------------------------------------------------------------

# Team decision (Chrome review, 23 Nov 2026): "Llegué" opens 60 min before the person's own start (the scheduled time,
# or the hand-over time for a relay), and "Terminé" before half of their part of the visit asks "¿Seguro?".
ARRIVE_EARLY_MINUTES = 60
FINISH_CONFIRM_SHARE = 0.5
LEG_TIMES_SQL = """
    SELECT CASE WHEN a.leg = 2 THEN f.planned_end ELSE r.scheduled_for END AS due, a.arrived_at,
           coalesce(round(extract(epoch FROM a.planned_end - (a.planned_start + a.travel_min * interval '1 minute')) / 60),
                    s.duration_min)::int AS expected_min
    FROM assignments a JOIN service_requests r USING (request_id) JOIN services s USING (service_id)
    LEFT JOIN assignments f ON f.request_id = a.request_id AND f.status = 'active' AND f.leg = 1 AND a.leg = 2
    WHERE a.assignment_id = :a"""


def arrival_opens_at(db: Session, assignment_id: str) -> datetime | None:
    """From when this person may press "Llegué"; None if the assignment does not exist."""
    row = db.execute(text(LEG_TIMES_SQL), {"a": assignment_id}).one_or_none()
    return row.due - timedelta(minutes=ARRIVE_EARLY_MINUTES) if row and row.due else None


def early_finish(db: Session, assignment_id: str) -> int | None:
    """Minutes this part of the visit should last, when "Terminé" comes before half of them (ask to confirm)."""
    row = db.execute(text(LEG_TIMES_SQL), {"a": assignment_id}).one_or_none()
    if not row or row.arrived_at is None or not row.expected_min:
        return None
    on_site = (now() - row.arrived_at).total_seconds() / 60
    return row.expected_min if on_site < FINISH_CONFIRM_SHARE * row.expected_min else None


def mark_arrived(db: Session, *, user_id: str, institution_id: str, assignment_id: str) -> None:
    _visit_step(db, assignment_id, "assigned", "in_progress", "arrived_at", user_id, institution_id, "visit_arrived")


def mark_finished(db: Session, *, user_id: str, institution_id: str, assignment_id: str) -> None:
    _visit_step(db, assignment_id, "in_progress", "completed", "finished_at", user_id, institution_id,
                "visit_finished")


def confirm_visit(db: Session, *, user_id: str, institution_id: str, assignment_id: str) -> None:
    rid = db.scalar(text("""UPDATE assignments a SET family_confirmed = true FROM service_requests r
                            WHERE a.assignment_id = :a AND a.status = 'active' AND r.request_id = a.request_id
                              AND r.status = 'completed' RETURNING r.request_id"""), {"a": assignment_id})
    if rid is None:
        raise InvalidState("not completed")
    set_status(db, rid, "closed")
    audit(db, user_id=user_id, institution_id=institution_id, action="visit_confirmed",
          entity="assignment", entity_id=assignment_id)
    publish(db, "request.updated", institution_id, request_id=rid, status="closed")


def _visit_step(db, assignment_id, from_status, to_status, column, user_id, institution_id, action) -> None:
    """Llegué / Terminé. With a relay (two people) the service starts when the FIRST person arrives and ends when
    the RELAY finishes: the first person's "Terminé" and the relay's "Llegué" are recorded without changing it."""
    leg = db.execute(text("""SELECT a.leg, a.arrived_at, EXISTS (SELECT 1 FROM assignments b WHERE b.request_id = a.request_id
                                        AND b.status = 'active' AND b.leg = 2) AS has_relay
                             FROM assignments a WHERE a.assignment_id = :a AND a.status = 'active'"""),
                     {"a": assignment_id}).one_or_none()
    if leg is None:
        raise InvalidState(from_status)
    middle = (leg.has_relay and leg.leg == 1 and column == "finished_at") or (leg.leg == 2 and column == "arrived_at")
    expected = "in_progress" if leg.leg == 2 else from_status
    if leg.leg == 2 and column == "finished_at" and leg.arrived_at is None:
        raise InvalidState(from_status)
    # "Terminé" is never earlier than "Llegué", even if the laptop clock jumps back (WSL2 re-syncs ~3 s back)
    value = "greatest(clock_timestamp(), a.arrived_at + interval '1 second')" if column == "finished_at" else "clock_timestamp()"
    rid = db.scalar(text(f"""
        UPDATE assignments a SET {column} = {value} FROM service_requests r
        WHERE a.assignment_id = :a AND a.status = 'active' AND a.{column} IS NULL AND r.request_id = a.request_id
          AND (r.status = :from OR (:late AND r.status = 'not_closed')) RETURNING r.request_id"""),
        # a visit marked "No cerrada" (alerts_followup.mark_not_closed) can still be closed with a late "Terminé"
        {"a": assignment_id, "from": expected, "late": column == "finished_at"})
    if rid is None:
        raise InvalidState(from_status)
    if not middle:
        set_status(db, rid, to_status)
    audit(db, user_id=user_id, institution_id=institution_id, action=action, entity="assignment",
          entity_id=assignment_id, detail={"relay_leg": leg.leg} if leg.has_relay or leg.leg == 2 else None)
    publish(db, "visit.arrived" if column == "arrived_at" else "visit.finished", institution_id,
            request_id=rid, assignment_id=assignment_id)


def has_valid_consent(db: Session, patient_id: str, consent_type: str) -> bool:
    return bool(db.scalar(text("SELECT is_valid FROM v_consents WHERE patient_id = :p AND type = :t"),
                          {"p": patient_id, "t": consent_type}))
