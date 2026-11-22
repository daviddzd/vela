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


def load_request(db: Session, request_id: str) -> dsp.Request:
    r = db.execute(text("""
        SELECT r.request_id, r.priority, r.scheduled_for, r.created_at, s.required_skill,
               ins.duration_min, vp.lat, vp.lon, vp.chronic_lung_disease, vp.heart_disease, vp.stroke,
               vp.diabetes, vp.dependency_level, vp.age_group, vp.chronic_disease_count
        FROM service_requests r
        JOIN services s ON s.service_id = r.service_id
        JOIN institution_services ins ON ins.institution_id = r.institution_id AND ins.service_id = r.service_id
        JOIN patients pa ON pa.patient_id = r.patient_id
        JOIN v_persons vp ON vp.person_id = pa.person_id
        WHERE r.request_id = :id"""), {"id": request_id}).one()
    flags = {"chronic_lung_disease": r.chronic_lung_disease, "heart_disease": r.heart_disease,
             "stroke": r.stroke, "diabetes": r.diabetes,
             "dependency_severe": r.dependency_level == "severe",
             "dependency_moderate": r.dependency_level == "moderate",
             "age_80_plus": r.age_group == "80+", "no_chronic_disease": r.chronic_disease_count == 0}
    return dsp.Request(r.request_id, r.priority, r.required_skill, r.scheduled_for, r.duration_min,
                       float(r.lat), float(r.lon), r.created_at,
                       dsp.patient_risk(flags, risk_multipliers()))


def load_caregivers(db: Session, institution_id: str, around: datetime) -> list[dsp.Caregiver]:
    """Active caregivers of the institution with their booked windows near that day."""
    rows = db.execute(text("""
        SELECT c.caregiver_id, c.shift_start, c.shift_end, c.base_lat, c.base_lon,
               array_agg(DISTINCT k.skill) AS skills
        FROM caregivers c JOIN caregiver_skills k USING (caregiver_id)
        WHERE c.institution_id = :inst AND c.active
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
                          float(r.base_lat), float(r.base_lon), tuple(busy.get(r.caregiver_id, ())))
            for r in rows]


def load_holds(db: Session, institution_id: str) -> list[dsp.Hold]:
    """Active reservations: the rank-1 proposal of each high-priority request still waiting for approval,
    for approval.hold_minutes after it was proposed (shared rule with SIRAG-D: dispatcher.apply_holds)."""
    minutes = settings_yaml()["approval"]["hold_minutes"]
    rows = db.execute(text("""
        SELECT p.request_id, p.caregiver_id, p.planned_start, p.planned_end,
               p.created_at + :m * interval '1 minute' AS expires
        FROM assignment_proposals p JOIN service_requests r USING (request_id)
        WHERE p.institution_id = :i AND p.status = 'open' AND p.rank = 1 AND r.status = 'queued'"""),
        {"i": institution_id, "m": minutes}).all()
    return [dsp.Hold(r.request_id, r.caregiver_id, r.planned_start, r.planned_end, r.expires) for r in rows]


def options_for(db: Session, request_id: str) -> list[dsp.Option]:
    """Options at the earliest feasible arrival, from the requested time up to the late tolerance.
    Other requests' reservations are respected; this request may use its own."""
    req = load_request(db, request_id)
    inst = db.scalar(text("SELECT institution_id FROM service_requests WHERE request_id = :id"), {"id": request_id})
    pool = dsp.apply_holds(load_caregivers(db, inst, req.scheduled_for), load_holds(db, inst), now(), request_id)
    return dsp.earliest_options(req, pool, load_traffic(db), policy(), now(), req.scheduled_for + late_tolerance())


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
    decisions = dsp.dispatch_window(requests, caregivers, load_traffic(db), policy(), now(), latest)
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
            with db.begin_nested():
                aid = db.scalar(text("""
                    INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval,
                                             assigned_at, planned_start, planned_end, travel_min)
                    VALUES (:r, :i, :c, :by, :ap, now(), :ps, :pe, :t) RETURNING assignment_id"""),
                    {"r": request_id, "i": institution_id, "c": o.caregiver_id, "by": assigned_by,
                     "ap": approval, "ps": o.planned_start, "pe": o.planned_end, "t": o.travel_min})
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
                      "policy": policy()})
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
                                              planned_start, planned_end, policy)
            VALUES (:r, :i, :rank, :c, :t, :ps, :pe, :pol)"""),
            {"r": request_id, "i": institution_id, "rank": rank, "c": o.caregiver_id, "t": o.travel_min,
             "ps": o.planned_start, "pe": o.planned_end, "pol": policy()})
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
    if a is None or a.arrived_at is not None:
        raise InvalidState("not reassignable")
    db.execute(text("UPDATE assignments SET status = 'reassigned' WHERE assignment_id = :a"), {"a": assignment_id})
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
    rid = db.scalar(text(f"""
        UPDATE assignments a SET {column} = clock_timestamp() FROM service_requests r
        WHERE a.assignment_id = :a AND a.status = 'active' AND r.request_id = a.request_id
          AND r.status = :from RETURNING r.request_id"""), {"a": assignment_id, "from": from_status})
    if rid is None:
        raise InvalidState(from_status)
    set_status(db, rid, to_status)
    audit(db, user_id=user_id, institution_id=institution_id, action=action, entity="assignment",
          entity_id=assignment_id)
    publish(db, "visit.arrived" if to_status == "in_progress" else "visit.finished", institution_id,
            request_id=rid, assignment_id=assignment_id)


def has_valid_consent(db: Session, patient_id: str, consent_type: str) -> bool:
    return bool(db.scalar(text("SELECT is_valid FROM v_consents WHERE patient_id = :p AND type = :t"),
                          {"p": patient_id, "t": consent_type}))
