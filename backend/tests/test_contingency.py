"""Live contingency: detection, no change without approval, partial approval, revert, tenant isolation,
real vs demo separation, anti-flicker, caregiver out of service. Everything runs in rolled-back transactions."""
import time
from datetime import datetime, timedelta

from sqlalchemy import text

from app.services import air_model
from app.services import contingency as ct
from app.services import operations as ops
from tests.conftest import free_caregiver, login, session_on


def _open_events(s):
    return s.execute(text("SELECT event_id, origin, run_id FROM contingency_events WHERE ended_at IS NULL")).all()


def test_live_model_is_deterministic_and_calibrated():
    h = datetime(2026, 12, 1, 15, 0, tzinfo=ops.MEXICO_CITY)
    assert air_model.reading("SAC", 1.0, 1.0, h) == air_model.reading("SAC", 1.0, 1.0, h)
    o3, pm = air_model.reading("SAC", 1.0, 1.0, h)
    assert 40 < o3 < 160 and 5 < pm < 60          # afternoon ozone peak, ordinary PM2.5


def test_demo_scenario_is_detected_by_one_worker_tick_without_changing_priorities(tx_client, db_conn):
    login(tx_client, "owner@ejemplo.test")
    started = time.perf_counter()
    assert tx_client.post("/api/demo/scenario", json={"scenario": "contingency_east"}).status_code == 200
    with session_on(db_conn, "*") as s:
        ct.ensure_readings(s)
        changed = ct.detect(s)                   # what the worker does every minute
        elapsed = time.perf_counter() - started
        events = _open_events(s)
        demo = [e for e in events if e.origin == "demo_scenario"]
        assert changed and len(demo) == 1 and elapsed < 60   # worker every 60 s + this -> < 2 min
        # nothing changed for any patient: there are only PROPOSALS
        assert s.scalar(text("SELECT count(*) FROM priority_overrides WHERE active")) == 0
        assert s.scalar(text("SELECT count(*) FROM contingency_proposals WHERE event_id = :e AND status = 'proposed'"),
                        {"e": demo[0].event_id}) > 0
        assert s.scalar(text("SELECT count(*) FROM family_notices")) == 0
        # calibrated history untouched: scenario readings live apart
        assert s.scalar(text("SELECT count(*) FROM air_quality_readings WHERE source = 'scenario'")) == 0


def test_partial_approval_applies_only_the_chosen_changes_and_normal_reverts(tx_client, db_conn):
    login(tx_client, "owner@ejemplo.test")
    r = tx_client.post("/api/demo/scenario", json={"scenario": "contingency_east"})
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    with session_on(db_conn, "*") as s:
        ct.detect(s)
        ev = [e for e in _open_events(s) if e.origin == "demo_scenario"][0].event_id
        raise_ids = s.scalars(text("""SELECT proposal_id FROM contingency_proposals WHERE event_id = :e
                                      AND institution_id = 'INS-A' AND kind = 'raise_priority'"""), {"e": ev}).all()
        patient = s.scalar(text("SELECT patient_id FROM contingency_proposals WHERE proposal_id = :p"), {"p": raise_ids[0]})
        base = s.scalar(text("SELECT base_priority FROM patients WHERE patient_id = :p"), {"p": patient})
        s.commit()
    assert raise_ids, "the scenario should propose raising someone's priority in INS-A"
    login(tx_client, "coordinacion.a@ejemplo.test")
    r = tx_client.post(f"/api/contingency/{ev}/decision", json={"mode": "selected", "ids": raise_ids[:1]}).json()
    assert r["decision"] == "partially_approved" and r["approved"] == 1
    with session_on(db_conn, "*") as s:
        assert ops.effective_priority(s, patient, base) == "high"
        assert s.scalar(text("SELECT base_priority FROM patients WHERE patient_id = :p"), {"p": patient}) == base
        assert s.scalar(text("SELECT count(*) FROM family_notices WHERE event_id = :e"), {"e": ev}) == 0   # not approved
        s.commit()
    login(tx_client, "owner@ejemplo.test")
    r = tx_client.post("/api/demo/scenario", json={"scenario": "normal"})       # closes the demo event at once
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    with session_on(db_conn, "*") as s:
        assert s.scalar(text("SELECT ended_at IS NOT NULL FROM contingency_events WHERE event_id = :e"), {"e": ev})
        assert ops.effective_priority(s, patient, base) == base                     # back to the base priority
        actions = set(s.scalars(text("SELECT action FROM audit_log WHERE entity_id = :e OR detail->>'event_id' = :e"),
                                {"e": ev}).all())
    assert {"contingency_detected", "contingency_proposed", "contingency_decided", "contingency_reverted"} <= actions


def test_an_institution_cannot_see_or_decide_another_institutions_proposal(tx_client, db_conn):
    login(tx_client, "owner@ejemplo.test")
    r = tx_client.post("/api/demo/scenario", json={"scenario": "contingency_east"})
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    with session_on(db_conn, "*") as s:
        ct.detect(s)
        ev = [e for e in _open_events(s) if e.origin == "demo_scenario"][0].event_id
        ins_a_ids = s.scalars(text("SELECT proposal_id FROM contingency_proposals WHERE event_id = :e AND institution_id = 'INS-A'"),
                              {"e": ev}).all()
        s.commit()
    login(tx_client, "coordinacion.b@ejemplo.test")
    seen = tx_client.get("/api/contingency/current").json()
    visible = {p["institution_id"] for e in seen["events"] for p in e["proposals"]}
    assert "INS-A" not in visible
    r = tx_client.post(f"/api/contingency/{ev}/decision", json={"mode": "selected", "ids": ins_a_ids[:2]})
    assert r.status_code == 403
    login(tx_client, "owner@ejemplo.test")                                  # the owner sees but does not decide
    assert tx_client.post(f"/api/contingency/{ev}/decision", json={"mode": "all"}).status_code == 403
    with session_on(db_conn, "*") as s:
        assert s.scalar(text("SELECT count(*) FROM priority_overrides WHERE event_id = :e"), {"e": ev}) == 0


def test_real_and_demo_events_never_mix(tx_client, db_conn):
    now = ct.hour_floor(ops.now())
    with session_on(db_conn, "*") as s:
        ct.ensure_readings(s)
        # a REAL episode at SAC: calibrated readings of the last 24 h above the PM2.5 threshold
        s.execute(text("""UPDATE air_quality_readings SET pm25_ugm3 = 120 WHERE station_id = 'SAC'
                          AND measured_at > :t - interval '24 hours' AND measured_at <= :t"""), {"t": now})
        ct.detect(s)
        s.commit()
    login(tx_client, "owner@ejemplo.test")
    r = tx_client.post("/api/demo/scenario", json={"scenario": "contingency_east"})
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    with session_on(db_conn, "*") as s:
        ct.detect(s)
        events = _open_events(s)
        assert {e.origin for e in events} == {"detected", "demo_scenario"} and len(events) == 2
        real = next(e.event_id for e in events if e.origin == "detected")
        demo = next(e.event_id for e in events if e.origin == "demo_scenario")
        overlap = s.scalar(text("""SELECT count(*) FROM contingency_proposals a JOIN contingency_proposals b
                                   ON a.proposal_id = b.proposal_id WHERE a.event_id = :r AND b.event_id = :d"""),
                           {"r": real, "d": demo})
        assert overlap == 0
        s.commit()
    tx_client.post("/api/demo/scenario", json={"scenario": "normal"})
    with session_on(db_conn, "*") as s:
        still = {e.origin for e in _open_events(s)}
    assert still == {"detected"}                                            # "normal" only ends the demo


def test_event_ends_after_two_hourly_readings_below_watch(db_conn):
    with session_on(db_conn, "*") as s:
        hot = [{"station_id": "SAC", "district_id": "09007", "o3": 50.0, "pm25_24h": 120.0, "phase": "phase1", "pollutant": "pm25"}]
        cold = [{**hot[0], "pm25_24h": 20.0, "phase": "normal"}]
        h0 = ct.hour_floor(ops.now())
        ct._handle(s, hot, "detected", None, h0)
        ev = _open_events(s)[0].event_id
        ct._handle(s, cold, "detected", None, h0 + timedelta(hours=1))          # 1 hour below: still open
        ct._handle(s, cold, "detected", None, h0 + timedelta(hours=1))          # same hour again: not counted twice
        assert s.scalar(text("SELECT ended_at FROM contingency_events WHERE event_id = :e"), {"e": ev}) is None
        ct._handle(s, cold, "detected", None, h0 + timedelta(hours=2))          # 2nd hour below: ends
        assert s.scalar(text("SELECT ended_at FROM contingency_events WHERE event_id = :e"), {"e": ev}) is not None


def test_caregiver_out_of_service_redispatches_pending_visits(db_conn):
    with session_on(db_conn, "*") as s:
        start = ops.now() + timedelta(hours=2)
        free_caregiver(s, "CUI-004")
        rid = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                               scheduled_for, created_at, status) VALUES ('INS-A', 'PAC-0002', 'SRV-02', 'coordinator',
                               'medium', :t, now(), 'assigned') RETURNING request_id"""), {"t": start})
        s.execute(text("""INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval, assigned_at,
                          planned_start, planned_end) VALUES (:r, 'INS-A', 'CUI-004', 'USR-002', 'auto', now(), :a, :b)"""),
                  {"r": rid, "a": start - timedelta(minutes=20), "b": start + timedelta(minutes=30)})
        out = ops.caregiver_out_of_service(s, caregiver_id="CUI-004", reason="prueba", origin="coordinator", user_id="USR-002")
        assert out["pending"] == 1
        assert "CUI-004" not in [c.caregiver_id for c in ops.load_caregivers(s, "INS-A", start)]
        row = s.execute(text("""SELECT r.status, a.caregiver_id FROM service_requests r LEFT JOIN assignments a
                                ON a.request_id = r.request_id AND a.status = 'active' WHERE r.request_id = :r"""), {"r": rid}).one()
        assert row.status in ("assigned", "queued") and row.caregiver_id != "CUI-004"   # same dispatcher, someone else or queue
        assert s.scalar(text("SELECT count(*) FROM alerts WHERE institution_id = 'INS-A' AND message LIKE '%fuera de servicio%'")) >= 1


def test_platform_wide_events_reach_every_board():
    from app.core.events import Client
    coordinator = Client(None, "coordinator", "INS-B")
    assert coordinator.wants({"type": "contingency.changed", "institution_id": None})
    assert not coordinator.wants({"type": "contingency.changed", "institution_id": "INS-A"})


def test_demo_panel_picks_an_active_institution_and_creates_the_urgent_request_there(tx_client):
    login(tx_client, "owner@ejemplo.test")
    state = tx_client.get("/api/demo/state").json()
    default = next(i for i in state["institutions"] if i["institution_id"] == state["default_institution"])
    if any(i["on_shift"] for i in state["institutions"]):
        assert default["on_shift"] > 0                      # someone is working there at this hour
    r = tx_client.post("/api/demo/urgent-request", json={"institution_id": "INS-B"}).json()
    login(tx_client, "coordinacion.b@ejemplo.test")
    req = tx_client.get(f"/api/requests/{r['request_id']}").json()
    assert req["priority"] == "high" and req["origin"] == "demo_scenario"
    login(tx_client, "coordinacion.a@ejemplo.test")
    assert tx_client.get(f"/api/requests/{r['request_id']}").status_code == 403      # INS-A cannot see it
