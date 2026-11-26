"""Two levels of voice emergency (CLAUDE.md rule 6, team decision 23 Nov 2026) and visits nobody closed.

- a rule fired            -> red 911 screen (emergency_source 'rule') + the usual critical 'emergency' alert;
- only the classifier     -> amber notice (emergency_source 'classifier') + critical 'emergency_review' alert with a
                             deadline; unanswered after classifier_only.escalate_after_minutes -> Dirección; both
                             answers ("era / no era emergencia") are audited;
- in progress long after its planned end -> "No cerrada" + alert (dispatch.not_closed_after_minutes).
"""
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.services import alerts_followup, oracle
from app.services import operations as ops
from tests.conftest import free_caregiver, login, session_on
from tests.test_voice import EMERGENCY_TEXT, fake_classifier, family_patient, send

CALM_TEXT = "el paciente comió bien y está tranquilo"          # the QA phrase v1 rated 0.925 "emergency"


@pytest.fixture(autouse=True)
def no_background_llm(monkeypatch):
    monkeypatch.setattr(oracle, "write_report", lambda rid, inst: None)


def _alerts(s, pid, kind):
    return s.execute(text("""SELECT alert_id, level, escalate_at, created_at FROM alerts
                             WHERE type = :k AND patient_id = :p AND created_at = now()"""), {"k": kind, "p": pid}).all()


def test_a_rule_is_red_with_the_usual_alert(tx_client, db_conn, monkeypatch):
    fake_classifier(monkeypatch, "routine")
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    r = send(tx_client, pid, EMERGENCY_TEXT)
    assert r["level"] == "emergency" and r["emergency_source"] == "rule"
    with session_on(db_conn, "INS-A") as s:
        assert [a.level for a in _alerts(s, pid, "emergency")] == ["critical"]
        assert _alerts(s, pid, "emergency_review") == []


def test_only_the_classifier_is_amber_with_a_review_alert_that_escalates_at_10_min(tx_client, db_conn, monkeypatch):
    fake_classifier(monkeypatch, "emergency")
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    r = send(tx_client, pid, CALM_TEXT)
    assert r["level"] == "emergency" and r["emergency_source"] == "classifier" and r["rule_hits"] == []
    assert alerts_followup.escalate_after_minutes() == 10                # config/emergency_rules.yaml
    with session_on(db_conn, "INS-A") as s:
        [review] = _alerts(s, pid, "emergency_review")
        assert review.level == "critical" and review.escalate_at - review.created_at == timedelta(minutes=10)
        assert _alerts(s, pid, "emergency") == []                       # not the red one
        level = s.scalar(text("SELECT triage_label FROM voice_reports WHERE report_id = :r"), {"r": r["report_id"]})
        assert level == "emergency"                                      # nothing is discarded
    with session_on(db_conn, "*") as s:
        alert_id = review.alert_id
        alerts_followup.escalate_overdue(s)                              # before the deadline: nothing happens
        assert s.scalar(text("SELECT escalated_at FROM alerts WHERE alert_id = :a"), {"a": alert_id}) is None
        s.execute(text("UPDATE alerts SET escalate_at = now() - interval '1 second' WHERE alert_id = :a"), {"a": alert_id})
        alerts_followup.escalate_overdue(s)                              # 10 min later, nobody answered
        assert s.scalar(text("SELECT escalated_at FROM alerts WHERE alert_id = :a"), {"a": alert_id}) is not None
        assert s.scalar(text("""SELECT count(*) FROM audit_log WHERE action = 'emergency_review_escalated'
                                AND entity_id = :a"""), {"a": alert_id}) == 1
        s.commit()
    login(tx_client, "owner@ejemplo.test")                               # Dirección sees it
    assert alert_id in [a["alert_id"] for a in tx_client.get("/api/alerts/escalated").json()]


@pytest.mark.parametrize("outcome, action", [("emergency", "emergency_review_confirmed"),
                                             ("not_emergency", "emergency_review_dismissed")])
def test_coordination_records_what_it_was(tx_client, db_conn, monkeypatch, outcome, action):
    fake_classifier(monkeypatch, "emergency")
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    send(tx_client, pid, CALM_TEXT)
    with session_on(db_conn, "INS-A") as s:
        [review] = _alerts(s, pid, "emergency_review")
    login(tx_client, "coordinacion.a@ejemplo.test")
    board = tx_client.get("/api/board").json()
    shown = next(a for a in board["alerts"] if a["alert_id"] == review.alert_id)
    assert shown["type"] == "emergency_review" and shown["escalate_at"]
    out = tx_client.post(f"/api/alerts/{review.alert_id}/review", json={"outcome": outcome}).json()
    assert out["resolution"] == outcome
    assert tx_client.post(f"/api/alerts/{review.alert_id}/review", json={"outcome": outcome}).status_code == 409
    with session_on(db_conn, "INS-A") as s:
        row = s.execute(text("SELECT status, resolution, handled_by FROM alerts WHERE alert_id = :a"),
                        {"a": review.alert_id}).one()
        assert (row.status, row.resolution, row.handled_by) == ("resolved", outcome, "USR-002")
        assert s.scalar(text("SELECT count(*) FROM audit_log WHERE action = :ac AND entity_id = :a"),
                        {"ac": action, "a": review.alert_id}) == 1
        confirmed = s.scalar(text("SELECT escalated_at IS NOT NULL FROM alerts WHERE alert_id = :a"),
                             {"a": out["confirmed_alert"]}) if out["confirmed_alert"] else None
    assert confirmed is (True if outcome == "emergency" else None)       # "era emergencia" escalates at once


def test_a_visit_nobody_finished_becomes_not_closed_with_an_alert(db_conn):
    with session_on(db_conn, "*") as s:
        free_caregiver(s, "CUI-003")
        rid = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                               scheduled_for, created_at, status) VALUES ('INS-A', 'PAC-0001', 'SRV-02', 'care_plan',
                               'medium', now() - interval '5 hours', now() - interval '6 hours', 'in_progress')
                               RETURNING request_id"""))
        aid = s.scalar(text("""INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval,
                               assigned_at, planned_start, planned_end, arrived_at)
                               VALUES (:r, 'INS-A', 'CUI-003', 'USR-002', 'auto', now() - interval '6 hours',
                                       now() - interval '5 hours 20 minutes', now() - interval '4 hours 30 minutes',
                                       now() - interval '5 hours') RETURNING assignment_id"""), {"r": rid})
        assert alerts_followup.mark_not_closed(s) >= 1
        assert s.scalar(text("SELECT status FROM service_requests WHERE request_id = :r"), {"r": rid}) == "not_closed"
        msg = s.scalar(text("SELECT message FROM alerts WHERE request_id = :r AND type = 'visit_not_closed'"), {"r": rid})
        assert "No cerrada" in msg and rid in msg
        alerts_followup.mark_not_closed(s)                               # next tick: no second alert
        assert s.scalar(text("SELECT count(*) FROM alerts WHERE request_id = :r AND type = 'visit_not_closed'"),
                        {"r": rid}) == 1
        # the person can still close it late with "Terminé"
        ops.mark_finished(s, user_id="USR-012", institution_id="INS-A", assignment_id=aid)
        assert s.scalar(text("SELECT status FROM service_requests WHERE request_id = :r"), {"r": rid}) == "completed"


def test_a_visit_still_within_its_time_is_not_touched(db_conn):
    with session_on(db_conn, "*") as s:
        free_caregiver(s, "CUI-004")
        rid = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                               scheduled_for, created_at, status) VALUES ('INS-A', 'PAC-0001', 'SRV-02', 'care_plan',
                               'medium', now() - interval '2 hours', now() - interval '3 hours', 'in_progress')
                               RETURNING request_id"""))
        s.execute(text("""INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval,
                          assigned_at, planned_start, planned_end, arrived_at)
                          VALUES (:r, 'INS-A', 'CUI-004', 'USR-002', 'auto', now() - interval '3 hours',
                                  now() - interval '2 hours 20 minutes', now() - interval '90 minutes',
                                  now() - interval '2 hours')"""), {"r": rid})   # ended 90 min ago: < 2 h
        alerts_followup.mark_not_closed(s)
        assert s.scalar(text("SELECT status FROM service_requests WHERE request_id = :r"), {"r": rid}) == "in_progress"


def test_classifier_confidence_is_for_coordination_and_physician_not_family(tx_client, db_conn, monkeypatch):
    """The review alert and the physician inbox carry the classifier's probabilities; the family's answer does not."""
    fake_classifier(monkeypatch, "emergency")
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    r = send(tx_client, pid, CALM_TEXT)
    assert "classifier_probs" not in r and "probs" not in r                # never shown to the family
    login(tx_client, "coordinacion.a@ejemplo.test")
    alerts = tx_client.get("/api/board").json()["alerts"]
    review = next(a for a in alerts if a["type"] == "emergency_review" and a["code"] == f"voice:{r['report_id']}")
    assert review["classifier_probs"] == {"routine": 0.1, "urgent": 0.1, "emergency": 0.8}
    login(tx_client, "cui-001@ejemplo.test")                               # physician of INS-A (PAC-0001 is theirs)
    rep = next((x for x in tx_client.get("/api/voice/reports").json() if x["report_id"] == r["report_id"]), None)
    assert rep is not None and rep["health_consent"]
    assert rep["classifier_probs"]["emergency"] == 0.8
