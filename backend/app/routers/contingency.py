"""/api/contingency (coordination decides for ITS institution; the owner sees everything but does not decide)
and /api/demo (owner only: changes input data, the worker detects and proposes by itself)."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.guards import deny
from app.core.roles import COORDINATOR, OWNER
from app.services import contingency as ct
from app.services import operations as ops

router = APIRouter(prefix="/api", tags=["contingency"])


@router.get("/contingency/current")
def current(user: CurrentUser = Depends(require_role(COORDINATOR, OWNER)), db: Session = Depends(tenant_db)) -> dict:
    hour = ct.hour_floor(ops.now())
    run = db.execute(text("SELECT run_id, scenario, started_at FROM scenario_runs WHERE active")).mappings().first()
    events = db.execute(text("""
        SELECT event_id, pollutant, phase, origin, scenario, run_id, districts, started_at, ended_at
        FROM contingency_events WHERE ended_at IS NULL OR ended_at > now() - interval '6 hours'
        ORDER BY ended_at IS NOT NULL, started_at DESC""")).mappings().all()
    names = dict(db.execute(text(ct.DISTRICT_NAMES_SQL)).all())
    out = []
    for e in events:
        items = db.execute(text("""SELECT proposal_id, institution_id, kind, patient_id, request_id, assignment_id, reason,
                                          status, payload FROM contingency_proposals WHERE event_id = :e
                                   ORDER BY institution_id, kind, proposal_id"""), {"e": e["event_id"]}).mappings().all()
        decisions = db.execute(text("""SELECT institution_id, decision, decided_by, decided_at, notes FROM contingency_decisions
                                       WHERE event_id = :e"""), {"e": e["event_id"]}).mappings().all()
        out.append({**dict(e), "district_names": [names.get(d, d) for d in e["districts"]],
                    "traffic_active": ct.active_traffic(db, e["run_id"]) is not None,
                    "proposals": [dict(i) for i in items], "decisions": [dict(d) for d in decisions]})
    return {"now": ops.now().isoformat(), "thresholds": ct.thresholds(), "scenario": dict(run) if run else None,
            "stations": ct.station_levels(db, hour, live=True), "events": out, "can_decide": user.role == COORDINATOR}


class DecisionIn(BaseModel):
    mode: str                     # "all" | "selected" | "none"
    ids: list[int] = []


@router.post("/contingency/{event_id}/decision")
def decision(event_id: str, body: DecisionIn, user: CurrentUser = Depends(require_role(COORDINATOR)),
             db: Session = Depends(tenant_db)) -> dict:
    if db.scalar(text("SELECT 1 FROM contingency_events WHERE event_id = :e AND ended_at IS NULL"), {"e": event_id}) is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta contingencia ya terminó o no existe.")
    approve = None if body.mode == "all" else [] if body.mode == "none" else body.ids
    try:
        return ct.decide(db, user_id=user.user_id, institution_id=user.institution_id, event_id=event_id, approve=approve)
    except ct.NotYours:
        raise deny(user, "blocked_cross_tenant", "contingency_proposal", event_id,
                   "Esos cambios no son de tu institución. El intento quedó registrado.", ids=body.ids)


# ---- demo panel ------------------------------------------------------------------------------------

class ScenarioIn(BaseModel):
    scenario: str


@router.get("/demo/state")
def demo_state(user: CurrentUser = Depends(require_role(OWNER)), db: Session = Depends(tenant_db)) -> dict:
    run = db.execute(text("SELECT run_id, scenario, started_at FROM scenario_runs WHERE active")).mappings().first()
    staff = db.execute(text("""
        SELECT c.caregiver_id, c.institution_id, c.first_name || ' ' || c.paternal_surname AS name,
               count(DISTINCT a.assignment_id) FILTER (WHERE a.status = 'active' AND a.arrived_at IS NULL AND a.planned_end > now()) AS pending,
               coalesce(bool_or(u.active), false) AS unavailable,
               CASE WHEN c.shift_end > c.shift_start
                    THEN (now() AT TIME ZONE 'America/Mexico_City')::time BETWEEN c.shift_start AND c.shift_end
                    ELSE (now() AT TIME ZONE 'America/Mexico_City')::time >= c.shift_start
                         OR (now() AT TIME ZONE 'America/Mexico_City')::time < c.shift_end END AS on_shift
        FROM caregivers c LEFT JOIN assignments a USING (caregiver_id)
        LEFT JOIN caregiver_unavailability u ON u.caregiver_id = c.caregiver_id AND u.active
        WHERE c.active GROUP BY c.caregiver_id ORDER BY pending DESC, c.caregiver_id""")).mappings().all()
    insts = db.execute(text("SELECT institution_id, name FROM institutions ORDER BY institution_id")).mappings().all()
    # "activity at the current hour": staff on shift now (then pending visits) -> default institution
    activity = {i["institution_id"]: (sum(1 for s in staff if s["institution_id"] == i["institution_id"] and s["on_shift"]),
                                      sum(s["pending"] for s in staff if s["institution_id"] == i["institution_id"])) for i in insts}
    default = max(insts, key=lambda i: (activity[i["institution_id"]][0] > 0, activity[i["institution_id"]][1],
                                        activity[i["institution_id"]][0]))["institution_id"]
    return {"scenario": dict(run) if run else None, "staff": [dict(s) for s in staff], "default_institution": default,
            "institutions": [{**dict(i), "on_shift": activity[i["institution_id"]][0], "pending": activity[i["institution_id"]][1]}
                             for i in insts],
            "scenarios": ["normal", "contingency_east", "contingency_east_roadblocks"]}


@router.post("/demo/scenario")
def demo_scenario(body: ScenarioIn, user: CurrentUser = Depends(require_role(OWNER)), db: Session = Depends(tenant_db)) -> dict:
    if body.scenario not in ("normal", "contingency_east", "contingency_east_roadblocks"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Escenario desconocido.")
    return {"run_id": ct.activate_scenario(db, body.scenario, user.user_id), "scenario": body.scenario}


class UrgentIn(BaseModel):
    institution_id: str = "INS-A"


@router.post("/demo/urgent-request")
def demo_urgent(body: UrgentIn, user: CurrentUser = Depends(require_role(OWNER)), db: Session = Depends(tenant_db)) -> dict:
    """High-priority visit in 30 min for a pollution-sensitive patient of the chosen institution (origin demo_scenario)."""
    p = db.execute(text("""
        SELECT pa.patient_id FROM patients pa JOIN v_persons vp USING (person_id) JOIN v_consents c USING (patient_id)
        WHERE pa.institution_id = :i AND pa.active AND c.type = 'home_care' AND c.is_valid
        ORDER BY (vp.district_id IN ('09007','09006','09017','09011','09005')) DESC,
                 (vp.pollution_sensitive AND EXISTS (SELECT 1 FROM v_consents h WHERE h.patient_id = pa.patient_id
                                                     AND h.type = 'health_data' AND h.is_valid)) DESC,
                 random() LIMIT 1"""), {"i": body.institution_id}).scalar()
    if p is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esa institución no tiene pacientes con consentimiento vigente.")
    soon = ops.now() + timedelta(minutes=30)
    soon = soon.replace(minute=soon.minute - soon.minute % 5, second=0, microsecond=0)
    rid = ops.create_request(db, user_id=user.user_id, institution_id=body.institution_id, patient_id=p, service_id="SRV-02",
                             scheduled_for=soon, priority="high", origin="demo_scenario")
    return {"request_id": rid, "patient_id": p}


class CaregiverIn(BaseModel):
    caregiver_id: str | None = None


@router.post("/demo/caregiver-out")
def demo_caregiver_out(body: CaregiverIn, user: CurrentUser = Depends(require_role(OWNER)),
                       db: Session = Depends(tenant_db)) -> dict:
    cid = body.caregiver_id or db.scalar(text("""
        SELECT c.caregiver_id FROM caregivers c LEFT JOIN assignments a ON a.caregiver_id = c.caregiver_id
          AND a.status = 'active' AND a.arrived_at IS NULL AND a.planned_end > now()
        WHERE c.institution_id = 'INS-A' AND c.active
          AND NOT EXISTS (SELECT 1 FROM caregiver_unavailability u WHERE u.caregiver_id = c.caregiver_id AND u.active)
        GROUP BY c.caregiver_id ORDER BY count(a.assignment_id) DESC, c.caregiver_id LIMIT 1"""))
    run = db.scalar(text("SELECT run_id FROM scenario_runs WHERE active"))
    return ops.caregiver_out_of_service(db, caregiver_id=cid, reason="Fuera de servicio (panel de demostración)",
                                        origin="demo_scenario", user_id=user.user_id, run_id=run)
