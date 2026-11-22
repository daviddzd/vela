"""Acceptance criterion A4 (docs/spec/10), automated part: events reach /ws/board in < 2 s and never
cross institutions. The Cloudflare part is checked by hand (docs/dev/decisiones_paso_4.md).

These tests COMMIT only a NOTIFY (no rows), so they leave nothing in the database.
"""
import time
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from starlette.websockets import WebSocketDisconnect

from app.core import events
from app.core.db import SessionLocal, tenant_session
from app.main import app
from app.services.care_plans import create_due_requests, planned_visit
from tests.conftest import login, session_on

WAIT_LISTENER_S = 10


def wait_listening() -> None:
    deadline = time.monotonic() + WAIT_LISTENER_S
    while not events.hub.listening:
        assert time.monotonic() < deadline, "LISTEN connection did not start"
        time.sleep(0.05)


def publish_committed(event_type: str, institution_id: str, **ids) -> None:
    """Commit a transaction that only sends a NOTIFY."""
    with SessionLocal() as s, s.begin():
        events.publish(s, event_type, institution_id, **ids)


@pytest.fixture
def live():
    """App with its lifespan running (LISTEN loop started)."""
    with TestClient(app) as c:
        wait_listening()
        yield c


def board_socket(client: TestClient, email: str, **headers):
    login(client, email)
    return client.websocket_connect("/ws/board", headers=headers or {})


def next_event(ws) -> dict:
    """Next message that is not a keep-alive."""
    while True:
        msg = ws.receive_json()
        if msg["type"] not in ("ping", "ready"):
            return msg


def test_time_endpoint(client):
    body = client.get("/api/time").json()
    assert body["timezone"] == "America/Mexico_City" and body["now"].endswith("-06:00")
    assert abs(body["epoch_ms"] / 1000 - time.time()) < 5


def test_event_arrives_in_under_2_seconds(live):
    with board_socket(live, "coordinacion.a@ejemplo.test") as ws:
        assert ws.receive_json()["type"] == "ready"
        started = time.perf_counter()
        publish_committed("request.created", "INS-A", request_id="REQ-TEST-1")
        event = next_event(ws)
        elapsed = time.perf_counter() - started
    assert event["type"] == "request.created" and event["request_id"] == "REQ-TEST-1"
    assert elapsed < 2, f"{elapsed:.2f}s"
    assert set(event) <= {"type", "institution_id", "at", "request_id", "status"}   # no personal data


def test_ins_a_does_not_receive_ins_b_events(live):
    with board_socket(live, "coordinacion.a@ejemplo.test") as ws:
        ws.receive_json()                                            # ready
        publish_committed("alert.created", "INS-B", alert_id="AL-B")
        publish_committed("alert.created", "INS-A", alert_id="AL-A")
        assert next_event(ws)["alert_id"] == "AL-A"                  # B was filtered out, A arrives first


def test_owner_receives_every_institution(live):
    with board_socket(live, "owner@ejemplo.test") as ws:
        ws.receive_json()
        publish_committed("visit.arrived", "INS-B", assignment_id="ASG-B")
        publish_committed("visit.arrived", "INS-A", assignment_id="ASG-A")
        assert [next_event(ws)["assignment_id"] for _ in range(2)] == ["ASG-B", "ASG-A"]


def test_rolled_back_change_sends_no_event(live):
    with board_socket(live, "coordinacion.a@ejemplo.test") as ws:
        ws.receive_json()
        with SessionLocal() as s:
            s.begin()
            events.publish(s, "request.created", "INS-A", request_id="REQ-ROLLED-BACK")
            s.rollback()
        publish_committed("request.created", "INS-A", request_id="REQ-COMMITTED")
        assert next_event(ws)["request_id"] == "REQ-COMMITTED"


@pytest.mark.parametrize("email, headers, code", [
    (None, {}, 4401),                                                  # no session cookie
    ("fam-0001@ejemplo.test", {}, 4403),                               # role without board
    ("cui-003@ejemplo.test", {}, 4403),
    ("coordinacion.a@ejemplo.test", {"origin": "https://evil.example"}, 4403),   # foreign site
])
def test_socket_rejections(live, email, headers, code):
    if email:
        login(live, email)
    with live.websocket_connect("/ws/board", headers=headers or {}) as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == code


def test_origin_compares_host_not_scheme(live):
    """Through Cloudflare the browser says https://x.trycloudflare.com while the API sees http."""
    login(live, "coordinacion.a@ejemplo.test")
    headers = {"origin": "https://demo.trycloudflare.com", "host": "demo.trycloudflare.com"}
    with live.websocket_connect("/ws/board", headers=headers) as ws:
        assert ws.receive_json()["type"] == "ready"


def test_listener_reconnects_after_its_connection_dies(live):
    """Simulates a PostgreSQL restart for the LISTEN connection: kill it and expect events again."""
    with tenant_session(None) as s:
        killed = s.scalar(text("SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity "
                               "WHERE application_name = :n"), {"n": events.listener_name()})
    assert killed == 1
    deadline = time.monotonic() + 15
    while events.hub.listening and time.monotonic() < deadline:   # first it notices the loss...
        time.sleep(0.05)
    wait_listening()                                               # ...then it listens again
    with board_socket(live, "coordinacion.a@ejemplo.test") as ws:
        ws.receive_json()
        publish_committed("request.created", "INS-A", request_id="REQ-AFTER-RECONNECT")
        assert next_event(ws)["request_id"] == "REQ-AFTER-RECONNECT"


def test_cookie_secure_follows_the_visitor_scheme(client):
    r = client.post("/api/auth/login", json={"email": "owner@ejemplo.test", "password": "Demo2026!"},
                    headers={"cf-visitor": '{"scheme":"https"}'})
    assert "secure" in r.headers["set-cookie"].lower()
    r = client.post("/api/auth/login", json={"email": "owner@ejemplo.test", "password": "Demo2026!"})
    assert "secure" not in r.headers["set-cookie"].lower()


# ---- board snapshot ---------------------------------------------------------------------------

def test_board_snapshot_is_scoped_to_the_institution(tx_client, db_conn):
    login(tx_client, "coordinacion.a@ejemplo.test")
    tomorrow = (date.today() + timedelta(days=1)).isoformat() + "T10:00"
    new = tx_client.post("/api/requests", json={"patient_id": "PAC-0001", "service_id": "SRV-02",
                                                "scheduled_for": tomorrow, "priority": "high"}).json()
    board = tx_client.get("/api/board").json()
    assert set(board["counters"]) == {"queued", "on_the_way", "in_visit", "done_today"}
    assert new["request_id"] in [q["request_id"] for q in board["queue"]]
    assert {q["institution_id"] for q in board["queue"]} == {"INS-A"}
    assert board["queue"][0]["priority"] == "high"
    with session_on(db_conn, "INS-A") as s:
        inst_staff = s.scalar(text("SELECT count(*) FROM caregivers WHERE active"))
    assert len(board["staff"]) == inst_staff


# ---- care plans -------------------------------------------------------------------------------

def test_planned_visit_is_deterministic_and_matches_frequency():
    day = date(2026, 12, 1)
    assert planned_visit("CP-1", day, 3.5, "SRV-02") == planned_visit("CP-1", day, 3.5, "SRV-02")
    days = [day + timedelta(days=i) for i in range(700)]
    visits = [planned_visit("CP-1", d, 3.5, "SRV-02") for d in days]
    assert 300 < sum(v is not None for v in visits) < 400               # ≈ 350 = 3.5/7 × 700
    hours = {v.hour for v in visits if v}
    assert min(hours) >= 8 and max(hours) < 18                          # inside visiting hours
    long_shift = {planned_visit("CP-2", d, 7, "SRV-06").hour for d in days[:30]}
    assert long_shift == {8}                                            # 8-h shifts start at 08:00 (seed rule)


def test_care_plan_requests_are_created_once(db_conn):
    with session_on(db_conn, "*") as s:
        first = create_due_requests(s)
        second = create_due_requests(s)
        assert second == []
        if first:
            rows = s.execute(text("SELECT origin, care_plan_id IS NOT NULL, plan_date FROM service_requests "
                                  "WHERE request_id = ANY(:ids)"), {"ids": first}).all()
            assert all(r[0] == "care_plan" and r[1] for r in rows)
