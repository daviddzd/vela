"""Acceptance criteria A3 and A5 (docs/spec/10) plus the no-overlap rule. Everything here runs inside
a transaction that is rolled back (see tx_client / db_conn in conftest.py)."""
import time
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.services import dispatcher as dsp
from app.services import operations as ops
from app.services import queue
from app.services.dispatcher import MEXICO_CITY
from tests.conftest import login, session_on

PATIENT = "PAC-0001"            # INS-A, all consents valid, family FAM-0001
NURSING_VISIT = "SRV-02"        # 30 min, skill nursing


def tomorrow_at(hour: int, minute: int = 0) -> str:
    day = datetime.now(MEXICO_CITY).date() + timedelta(days=1)
    return datetime(day.year, day.month, day.day, hour, minute).isoformat()   # naive = CDMX time


def new_request(client, priority="medium", at=None, patient=PATIENT, service=NURSING_VISIT):
    return client.post("/api/requests", json={"patient_id": patient, "service_id": service,
                                              "scheduled_for": at or tomorrow_at(10), "priority": priority})


# ---- A3: automatic assignment ------------------------------------------------------------------

def test_medium_request_is_assigned_automatically_in_under_5_s(tx_client):
    login(tx_client, "coordinacion.a@ejemplo.test")
    started = time.perf_counter()
    r = new_request(tx_client, "medium")
    elapsed = time.perf_counter() - started
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "assigned" and body["approval"] == "auto"
    assert body["caregiver_id"] and body["planned_start"] < body["scheduled_for"]
    assert elapsed < 5, f"took {elapsed:.2f}s"


def test_high_request_waits_for_coordinator_approval(tx_client):
    login(tx_client, "coordinacion.a@ejemplo.test")
    body = new_request(tx_client, "high").json()
    assert body["status"] == "queued" and body["status_reason"] == "awaiting_approval"
    assert body["assignment_id"] is None                                   # nothing applied yet

    pending = [p for p in tx_client.get("/api/approvals").json() if p["request_id"] == body["request_id"]]
    assert len(pending) == 1
    options = pending[0]["options"]
    assert [o["rank"] for o in options] == [1, 2, 3]                       # proposed + 2 alternatives

    approved = tx_client.post(f"/api/approvals/{body['request_id']}",
                              json={"caregiver_id": options[1]["caregiver_id"]})   # coordinator overrides
    assert approved.status_code == 200, approved.text
    a = approved.json()
    assert a["status"] == "assigned" and a["approval"] == "coordinator"
    assert a["caregiver_id"] == options[1]["caregiver_id"]


def test_approval_recalculates_when_candidate_is_no_longer_free(tx_client, db_conn):
    login(tx_client, "coordinacion.a@ejemplo.test")
    body = new_request(tx_client, "high").json()
    first = tx_client.get("/api/approvals").json()
    proposed = next(p for p in first if p["request_id"] == body["request_id"])["options"][0]

    # Meanwhile the proposed caregiver gets booked for that same window by another visit.
    with session_on(db_conn, "INS-A") as s:
        other = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin,
                                 priority, scheduled_for, created_at, status)
                                 VALUES ('INS-A', 'PAC-0002', 'SRV-02', 'coordinator', 'medium', :at, now(),
                                 'assigned') RETURNING request_id"""), {"at": proposed["planned_start"]})
        s.execute(text("""INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval,
                          assigned_at, planned_start, planned_end)
                          VALUES (:r, 'INS-A', :c, 'USR-002', 'auto', now(), :ps, :pe)"""),
                  {"r": other, "c": proposed["caregiver_id"], "ps": proposed["planned_start"],
                   "pe": proposed["planned_end"]})
        s.commit()

    r = tx_client.post(f"/api/approvals/{body['request_id']}", json={"caregiver_id": proposed["caregiver_id"]})
    assert r.status_code == 409
    assert "nuevas opciones" in r.json()["detail"]
    new_ids = [o["caregiver_id"] for o in r.json()["options"]]
    assert new_ids and proposed["caregiver_id"] not in new_ids
    # and the request is still waiting, with the fresh options saved
    still = next(p for p in tx_client.get("/api/approvals").json() if p["request_id"] == body["request_id"])
    assert [o["caregiver_id"] for o in still["options"]] == new_ids


# ---- validation --------------------------------------------------------------------------------

def test_without_home_care_consent_a_request_is_rejected(tx_client, db_conn):
    with session_on(db_conn, "INS-A") as s:
        s.execute(text("UPDATE consents SET expires_on = current_date - 1, signed_on = current_date - 400 "
                       "WHERE patient_id = :p AND type = 'home_care'"), {"p": PATIENT})
        s.commit()
    login(tx_client, "fam-0001@ejemplo.test")
    r = tx_client.post("/api/requests", json={"service_id": NURSING_VISIT, "scheduled_for": tomorrow_at(11)})
    assert r.status_code == 201
    assert r.json()["status"] == "rejected" and r.json()["status_reason"] == "no_home_care_consent"
    assert r.json()["assignment_id"] is None


def test_duplicate_within_2_hours_is_rejected(tx_client):
    login(tx_client, "coordinacion.a@ejemplo.test")
    first = new_request(tx_client, "medium", tomorrow_at(10)).json()
    second = new_request(tx_client, "medium", tomorrow_at(11, 30)).json()
    third = new_request(tx_client, "medium", tomorrow_at(13, 0)).json()
    assert second["status"] == "rejected" and second["duplicate_of"] == first["request_id"]
    assert third["status"] != "rejected"                                       # 3 h later is fine


def test_family_request_uses_patient_priority_and_own_patient(tx_client):
    login(tx_client, "fam-0001@ejemplo.test")
    r = tx_client.post("/api/requests", json={"patient_id": "PAC-0151", "service_id": NURSING_VISIT,
                                              "scheduled_for": tomorrow_at(12), "priority": "low"}).json()
    assert r["patient_id"] == PATIENT and r["priority"] == "high" and r["origin"] == "family"


# ---- no overlaps -------------------------------------------------------------------------------

def _insert_assignment(s, caregiver, start, end, status="active", patient="PAC-0003"):
    rid = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                           scheduled_for, created_at, status) VALUES ('INS-A', :p, 'SRV-02', 'coordinator',
                           'low', :ps, now(), 'assigned') RETURNING request_id"""), {"p": patient, "ps": start})
    s.execute(text("""INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval,
                      assigned_at, planned_start, planned_end, status)
                      VALUES (:r, 'INS-A', :c, 'USR-002', 'auto', now(), :ps, :pe, :st)"""),
              {"r": rid, "c": caregiver, "ps": start, "pe": end, "st": status})


def test_database_rejects_overlapping_windows(db_conn):
    start = datetime.now(MEXICO_CITY) + timedelta(days=2)
    with session_on(db_conn, "INS-A") as s:
        _insert_assignment(s, "CUI-003", start, start + timedelta(minutes=60))
        with pytest.raises(IntegrityError, match="no_caregiver_overlap"):
            with s.begin_nested():
                _insert_assignment(s, "CUI-003", start + timedelta(minutes=30), start + timedelta(minutes=90))


def test_new_assignment_coexists_with_seed_and_reassigned_rows(db_conn):
    with session_on(db_conn, "INS-A") as s:
        # A seed visit of CUI-003 (planned NULL, real arrival/finish times)...
        seed = s.execute(text("""SELECT arrived_at, finished_at FROM assignments
                                 WHERE caregiver_id = 'CUI-003' AND planned_start IS NULL
                                   AND arrived_at IS NOT NULL LIMIT 1""")).one()
        # ...does not block a new planned window at exactly that time,
        _insert_assignment(s, "CUI-003", seed.arrived_at, seed.finished_at)
        # and a reassigned row does not block either.
        later = seed.arrived_at + timedelta(days=60)
        _insert_assignment(s, "CUI-003", later, later + timedelta(minutes=30), status="reassigned")
        _insert_assignment(s, "CUI-003", later, later + timedelta(minutes=30))
        assert s.scalar(text("SELECT count(*) FROM assignments WHERE caregiver_id = 'CUI-003' "
                             "AND planned_start IS NOT NULL")) == 3


def test_retry_when_slot_taken_between_read_and_write(tx_client, db_conn, monkeypatch):
    """Two dispatches at the same instant: the second one read stale availability. The EXCLUDE
    constraint rejects its insert and save_assignment recomputes and picks someone else."""
    login(tx_client, "coordinacion.a@ejemplo.test")
    first = new_request(tx_client, "medium", tomorrow_at(10), patient=PATIENT).json()

    real = ops.load_caregivers
    calls = {"n": 0}

    def stale_first_time(db, inst, around):
        calls["n"] += 1
        cgs = real(db, inst, around)
        return [c.__class__(**{**c.__dict__, "busy": ()}) for c in cgs] if calls["n"] == 1 else cgs

    monkeypatch.setattr(ops, "load_caregivers", stale_first_time)
    # Same window, same skill, a patient next door: stale data would pick the same nurse.
    second = new_request(tx_client, "medium", tomorrow_at(10), patient="PAC-0002").json()
    assert second["status"] in ("assigned", "queued")
    assert second["caregiver_id"] != first["caregiver_id"]


# ---- worker: queue order, alerts, unattended ---------------------------------------------------

def test_worker_alerts_forgotten_approval_after_10_minutes(tx_client, db_conn):
    login(tx_client, "coordinacion.a@ejemplo.test")
    rid = new_request(tx_client, "high").json()["request_id"]
    with session_on(db_conn, "*") as s:
        queue.create_alerts(s)
        assert s.scalar(text("SELECT count(*) FROM alerts WHERE request_id = :r"), {"r": rid}) == 0
        s.execute(text("UPDATE service_requests SET created_at = now() - interval '11 minutes' "
                       "WHERE request_id = :r"), {"r": rid})
        queue.create_alerts(s)
        queue.create_alerts(s)                                   # second run: no duplicate
        rows = s.execute(text("SELECT code, level, message FROM alerts WHERE request_id = :r"), {"r": rid}).all()
    assert len(rows) == 1 and rows[0].code == "approval_pending" and "sin aprobarse" in rows[0].message


def test_worker_assigns_queued_requests_by_priority_then_risk(tx_client, db_conn):
    login(tx_client, "coordinacion.a@ejemplo.test")
    a = new_request(tx_client, "low", tomorrow_at(10), patient="PAC-0002").json()["request_id"]
    b = new_request(tx_client, "medium", tomorrow_at(10), patient="PAC-0003").json()["request_id"]
    with session_on(db_conn, "*") as s:
        # Put both back in the queue as if no one had been free, then let the worker retry.
        s.execute(text("UPDATE assignments SET status = 'cancelled' WHERE request_id IN (:a, :b)"), {"a": a, "b": b})
        s.execute(text("UPDATE service_requests SET status = 'queued' WHERE request_id IN (:a, :b)"), {"a": a, "b": b})
        assert queue.process_queue(s) >= 2
        statuses = dict(s.execute(text("SELECT request_id, status FROM service_requests "
                                       "WHERE request_id IN (:a, :b)"), {"a": a, "b": b}).all())
        audit_order = [r[0] for r in s.execute(text("""SELECT detail->>'request_id' FROM audit_log
            WHERE action = 'assignment_auto' AND detail->>'request_id' IN (:a, :b) ORDER BY audit_id"""),
            {"a": a, "b": b}).all()]
    assert statuses == {a: "assigned", b: "assigned"}
    assert audit_order[-2:] == [b, a]                            # medium before low


def test_worker_marks_past_queued_requests_unattended(db_conn):
    with session_on(db_conn, "*") as s:
        rid = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                               scheduled_for, created_at, status) VALUES ('INS-A', 'PAC-0002', 'SRV-02',
                               'coordinator', 'low', now() - interval '3 hours', now() - interval '4 hours',
                               'queued') RETURNING request_id"""))
        queue.mark_unattended(s)
        assert s.scalar(text("SELECT status FROM service_requests WHERE request_id = :r"), {"r": rid}) == "unattended"


# ---- visits: caregiver and family --------------------------------------------------------------

def _visit_now(db_conn, caregiver="CUI-003", patient=PATIENT) -> str:
    with session_on(db_conn, "INS-A") as s:
        rid = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                               scheduled_for, created_at, status) VALUES ('INS-A', :p, 'SRV-02', 'coordinator',
                               'medium', now(), now() - interval '1 hour', 'assigned') RETURNING request_id"""),
                       {"p": patient})
        aid = s.scalar(text("""INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval,
                               assigned_at, planned_start, planned_end)
                               VALUES (:r, 'INS-A', :c, 'USR-002', 'auto', now(), now() - interval '15 minutes',
                               now() + interval '30 minutes') RETURNING assignment_id"""),
                       {"r": rid, "c": caregiver})
        s.commit()
    return aid


def test_caregiver_arrives_finishes_and_family_confirms(tx_client, db_conn):
    aid = _visit_now(db_conn)
    login(tx_client, "cui-003@ejemplo.test")
    assert aid in [v["assignment_id"] for v in tx_client.get("/api/visits/mine").json()]
    assert tx_client.post(f"/api/visits/{aid}/finish").status_code == 409        # must arrive first
    assert tx_client.post(f"/api/visits/{aid}/arrive").json()["status"] == "in_progress"
    assert tx_client.post(f"/api/visits/{aid}/finish").json()["status"] == "completed"

    login(tx_client, "fam-0001@ejemplo.test")
    overview = tx_client.get("/api/family/overview").json()
    assert aid in [v["assignment_id"] for v in overview["to_confirm"]]
    assert tx_client.post(f"/api/family/visits/{aid}/confirm").json()["status"] == "closed"


def test_caregiver_cannot_touch_someone_elses_visit(tx_client, db_conn):
    aid = _visit_now(db_conn, caregiver="CUI-004")
    login(tx_client, "cui-003@ejemplo.test")
    assert aid not in [v["assignment_id"] for v in tx_client.get("/api/visits/mine").json()]
    assert tx_client.post(f"/api/visits/{aid}/arrive").status_code == 403


# ---- late tolerance (60 min, same value as SIRAG-D) ---------------------------------------------

def test_visit_is_assigned_late_within_tolerance_when_nobody_is_free_on_time(tx_client, db_conn):
    """Every INS-A nurse is busy until 10:25 tomorrow: a 10:00 visit is assigned to arrive later (<= 11:00)."""
    day = datetime.now(MEXICO_CITY).date() + timedelta(days=1)
    busy_from = datetime(day.year, day.month, day.day, 8, 0, tzinfo=MEXICO_CITY)
    busy_to = datetime(day.year, day.month, day.day, 10, 25, tzinfo=MEXICO_CITY)
    with session_on(db_conn, "INS-A") as s:
        nurses = s.scalars(text("""SELECT DISTINCT c.caregiver_id FROM caregivers c JOIN caregiver_skills k USING (caregiver_id)
                                   WHERE c.institution_id = 'INS-A' AND k.skill = 'nursing' AND c.active""")).all()
        for cg in nurses:
            _insert_assignment(s, cg, busy_from, busy_to)
        s.commit()
    login(tx_client, "coordinacion.a@ejemplo.test")
    body = new_request(tx_client, "medium", tomorrow_at(10)).json()
    assert body["status"] == "assigned", body
    arrival = datetime.fromisoformat(body["planned_end"]) - timedelta(minutes=30)
    assert busy_to <= arrival <= busy_to.replace(hour=11, minute=0)


def test_unattended_only_after_the_tolerance(db_conn):
    with session_on(db_conn, "*") as s:
        ids = {}
        for label, minutes in (("within", 30), ("past", 90)):
            ids[label] = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin,
                                   priority, scheduled_for, created_at, status) VALUES ('INS-A', 'PAC-0002', 'SRV-02',
                                   'coordinator', 'low', now() - :m * interval '1 minute', now() - interval '3 hours',
                                   'queued') RETURNING request_id"""), {"m": minutes})
        queue.mark_unattended(s)
        status = dict(s.execute(text("SELECT request_id, status FROM service_requests WHERE request_id IN (:a, :b)"),
                                {"a": ids["within"], "b": ids["past"]}).all())
    assert status == {ids["within"]: "queued", ids["past"]: "unattended"}


# ---- time-limited approval of URGENT high priority (finding of SIRAG-D) --------------------------

def _queued_high(s, minutes_ahead: int, proposed_minutes_ago: int) -> str:
    rid = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                           scheduled_for, created_at, status, status_reason) VALUES ('INS-A', 'PAC-0002', 'SRV-02',
                           'coordinator', 'high', now() + :m * interval '1 minute', now() - interval '10 minutes',
                           'queued', 'awaiting_approval') RETURNING request_id"""), {"m": minutes_ahead})
    s.execute(text("""INSERT INTO assignment_proposals (request_id, institution_id, rank, caregiver_id, travel_min,
                      planned_start, planned_end, policy, created_at)
                      VALUES (:r, 'INS-A', 1, 'CUI-004', 10, now(), now() + interval '1 hour', 'risk_plus_live_traffic',
                              now() - :ago * interval '1 minute')"""), {"r": rid, "ago": proposed_minutes_ago})
    return rid


def test_urgent_high_priority_is_applied_by_timeout_and_coordination_is_alerted(db_conn, monkeypatch):
    def fake_options(db, request_id):   # independent of the hour the test runs (night: nobody on shift)
        # a different window per request: the EXCLUDE constraint would (rightly) reject a shared one
        start = datetime.now(MEXICO_CITY) + timedelta(days=3, hours=int(request_id[-5:]) % 500)
        return [dsp.Option("CUI-004", 3.0, 10.0, start, start + timedelta(minutes=40), 0.0, start + timedelta(minutes=10))]
    monkeypatch.setattr(ops, "options_for", fake_options)
    with session_on(db_conn, "*") as s:
        urgent = _queued_high(s, minutes_ahead=40, proposed_minutes_ago=4)
        fresh = _queued_high(s, minutes_ahead=40, proposed_minutes_ago=1)       # still within the 3 minutes
        planned = _queued_high(s, minutes_ahead=24 * 60, proposed_minutes_ago=30)  # not urgent: waits for a person
        applied = queue.auto_apply_urgent(s)
        rows = dict(s.execute(text("""SELECT r.request_id, coalesce(a.approval, r.status) FROM service_requests r
                                      LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active'
                                      WHERE r.request_id IN (:a, :b, :c)"""), {"a": urgent, "b": fresh, "c": planned}).all())
        alert = s.scalar(text("SELECT message FROM alerts WHERE request_id = :r AND code = 'approved_by_timeout'"),
                         {"r": urgent})
        audited = s.scalar(text("""SELECT count(*) FROM audit_log WHERE action = 'assignment_approved_by_timeout'
                                   AND detail->>'request_id' = :r"""), {"r": urgent})
    assert urgent in applied and fresh not in applied and planned not in applied   # other live requests may also qualify
    assert rows == {urgent: "timeout", fresh: "queued", planned: "queued"}
    assert "sin aprobación" in alert and audited == 1


# ---- reservation of the proposed candidate (shared with SIRAG-D: dispatcher.apply_holds) --------

def test_proposed_candidate_is_reserved_until_the_hold_expires(tx_client, db_conn):
    login(tx_client, "coordinacion.a@ejemplo.test")
    high = new_request(tx_client, "high", tomorrow_at(10)).json()
    proposed = next(p for p in tx_client.get("/api/approvals").json() if p["request_id"] == high["request_id"])["options"][0]
    held = proposed["caregiver_id"]
    # Make every OTHER nurse busy, so the only way to serve a medium request at 10:00 is the held caregiver.
    day = datetime.now(MEXICO_CITY).date() + timedelta(days=1)
    lo = datetime(day.year, day.month, day.day, 8, 0, tzinfo=MEXICO_CITY)
    hi = datetime(day.year, day.month, day.day, 12, 0, tzinfo=MEXICO_CITY)
    with session_on(db_conn, "INS-A") as s:
        others = s.scalars(text("""SELECT DISTINCT c.caregiver_id FROM caregivers c JOIN caregiver_skills k USING (caregiver_id)
                                   WHERE c.institution_id = 'INS-A' AND k.skill = 'nursing' AND c.active AND c.caregiver_id <> :h"""),
                           {"h": held}).all()
        # three different patients with a valid home_care consent (none of them used by the blocking visits)
        p1, p2, blocker = s.scalars(text("""SELECT pa.patient_id FROM patients pa JOIN v_consents c USING (patient_id)
                                            WHERE pa.active AND c.type = 'home_care' AND c.is_valid
                                              AND pa.patient_id NOT IN ('PAC-0001', 'PAC-0002')
                                            ORDER BY pa.patient_id LIMIT 3""")).all()
        for cg in others:
            _insert_assignment(s, cg, lo, hi, patient=blocker)
        s.commit()
    medium = new_request(tx_client, "medium", tomorrow_at(10), patient=p1).json()
    if medium["caregiver_id"] == held:   # it may only use the held caregiver OUTSIDE the reserved window
        arrival = datetime.fromisoformat(medium["planned_end"]) - timedelta(minutes=30)
        assert arrival >= datetime.fromisoformat(proposed["planned_end"])
    else:
        assert medium["status"] == "queued", medium.get("status_reason")
    # After approval.hold_minutes without approval the reservation expires and the window is free again.
    with session_on(db_conn, "INS-A") as s:
        s.execute(text("UPDATE assignment_proposals SET created_at = now() - interval '20 minutes' WHERE request_id = :r"),
                  {"r": high["request_id"]})
        s.commit()
        assert ops.load_holds(s, "INS-A")[0].expires < ops.now()
    later = new_request(tx_client, "medium", tomorrow_at(10), patient=p2).json()
    assert later["status"] == "assigned" and later["caregiver_id"] == held
