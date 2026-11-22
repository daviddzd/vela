"""Consents registered / revoked by coordination (CLAUDE.md rule 5): a revocation blocks the dependent function AT
ONCE; home_care cancels pending visits but never one in progress; ARCO requests; the audit trail for dirección."""
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app.services import oracle
from app.services.privacy import add_business_days
from tests.conftest import free_caregiver, login, session_on
from tests.test_operations import new_request, tomorrow_at

PATIENT = "PAC-0001"            # INS-A, family FAM-0001 (legal representative), all three consents valid
INS_B_CONSENT = "CON-00451"     # PAC-0151, INS-B


@pytest.fixture(autouse=True)
def fake_voice(monkeypatch):
    monkeypatch.setattr(oracle, "write_report", lambda rid, inst: None)
    monkeypatch.setattr(oracle, "classify", lambda t: {"label": "routine", "probs": {}, "ms": 1})


def consent_id(db_conn, kind: str, patient: str = PATIENT) -> str:
    with session_on(db_conn, "*") as s:
        return s.scalar(text("SELECT consent_id FROM consents WHERE patient_id = :p AND type = :t"), {"p": patient, "t": kind})


def revoke(client, cid: str, reason: str = "La familia lo pidió por escrito"):
    return client.post(f"/api/privacy/consents/{cid}/revoke", json={"reason": reason})


def test_revoking_voice_consent_blocks_the_assistant_at_once(tx_client, db_conn):
    login(tx_client, "fam-0001@ejemplo.test")
    assert tx_client.post("/api/voice/text", json={"patient_id": PATIENT, "text": "buenos días"}).status_code == 200
    login(tx_client, "coordinacion.a@ejemplo.test")
    assert revoke(tx_client, consent_id(db_conn, "voice_assistant")).status_code == 200
    login(tx_client, "fam-0001@ejemplo.test")
    r = tx_client.post("/api/voice/text", json={"patient_id": PATIENT, "text": "buenos días"})
    assert r.status_code == 403                                                   # the very next request
    notices = tx_client.get("/api/family/overview").json()["notices"]
    assert any("asistente de voz" in n["message"] for n in notices)
    with session_on(db_conn, "INS-A") as s:
        assert s.scalar(text("SELECT count(*) FROM audit_log WHERE action = 'consent_revoked' AND entity_id = :c"),
                        {"c": consent_id(db_conn, "voice_assistant")}) == 1


def test_revoking_health_data_hides_health_and_recording_it_again_restores_it(tx_client, db_conn):
    login(tx_client, "coordinacion.a@ejemplo.test")
    assert tx_client.get(f"/api/patients/{PATIENT}").json()["health"] is not None
    assert revoke(tx_client, consent_id(db_conn, "health_data")).status_code == 200
    assert tx_client.get(f"/api/patients/{PATIENT}").json()["health"] is None
    today = date.today()
    r = tx_client.post("/api/privacy/consents", json={
        "patient_id": PATIENT, "type": "health_data", "granted_by": "legal_representative", "family_member_id": "FAM-0001",
        "patient_assent": "unable_to_express", "signed_on": today.isoformat(),
        "expires_on": (today + timedelta(days=365)).isoformat()})
    assert r.status_code == 200, r.text
    assert tx_client.get(f"/api/patients/{PATIENT}").json()["health"] is not None


def test_revoking_home_care_cancels_pending_visits_but_not_the_one_in_progress(tx_client, db_conn):
    login(tx_client, "coordinacion.a@ejemplo.test")
    pending = new_request(tx_client, "medium", tomorrow_at(11)).json()["request_id"]
    with session_on(db_conn, "INS-A") as s:                     # a visit of the same patient already started
        free_caregiver(s, "CUI-003")
        running = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                                   scheduled_for, created_at, status) VALUES ('INS-A', :p, 'SRV-02', 'coordinator', 'medium',
                                   now() - interval '20 minutes', now() - interval '1 hour', 'in_progress')
                                   RETURNING request_id"""), {"p": PATIENT})
        s.execute(text("""INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval, assigned_at,
                          planned_start, planned_end, arrived_at) VALUES (:r, 'INS-A', 'CUI-003', 'USR-002', 'auto',
                          now() - interval '1 hour', now() - interval '25 minutes', now() + interval '10 minutes',
                          now() - interval '20 minutes')"""), {"r": running})
        s.commit()

    r = revoke(tx_client, consent_id(db_conn, "home_care"))
    assert r.status_code == 200, r.text
    assert pending in r.json()["cancelled"] and r.json()["in_progress"] == [running]
    with session_on(db_conn, "INS-A") as s:
        assert s.execute(text("SELECT status, status_reason FROM service_requests WHERE request_id = :r"),
                         {"r": pending}).one() == ("cancelled", "consent_revoked")
        assert s.scalar(text("SELECT status FROM service_requests WHERE request_id = :r"), {"r": running}) == "in_progress"
        assert s.scalar(text("SELECT count(*) FROM assignments WHERE request_id = :r AND status = 'active'"), {"r": running}) == 1
        alert = s.scalar(text("SELECT message FROM alerts WHERE alert_id = :a"), {"a": r.json()["alert_id"]})
        assert "en curso" in alert and running in alert
    # a new home visit is rejected from now on
    assert new_request(tx_client, "medium", tomorrow_at(12)).json()["status_reason"] == "no_home_care_consent"
    login(tx_client, "fam-0001@ejemplo.test")
    assert any("se cancelaron" in n["message"] for n in tx_client.get("/api/family/overview").json()["notices"])


def test_only_coordination_records_or_revokes_and_never_another_institution(tx_client, db_conn):
    login(tx_client, "fam-0001@ejemplo.test")
    assert revoke(tx_client, consent_id(db_conn, "home_care")).status_code == 403
    login(tx_client, "coordinacion.a@ejemplo.test")
    assert revoke(tx_client, INS_B_CONSENT).status_code == 403                    # RLS hides it; recorded as blocked
    with session_on(db_conn, "*") as s:
        assert s.scalar(text("""SELECT count(*) FROM audit_log WHERE action = 'blocked_cross_tenant'
                                AND entity = 'consent' AND entity_id = :c"""), {"c": INS_B_CONSENT}) >= 1
        assert s.scalar(text("SELECT granted FROM consents WHERE consent_id = :c"), {"c": INS_B_CONSENT}) is True


def test_the_signer_must_be_a_legal_representative_of_that_patient(tx_client):
    login(tx_client, "coordinacion.a@ejemplo.test")
    today = date.today()
    body = {"patient_id": PATIENT, "type": "home_care", "granted_by": "legal_representative", "family_member_id": "FAM-0002",
            "patient_assent": "yes", "signed_on": today.isoformat(), "expires_on": (today + timedelta(days=30)).isoformat()}
    assert tx_client.post("/api/privacy/consents", json=body).status_code == 422
    assert tx_client.post("/api/privacy/consents", json={**body, "family_member_id": "FAM-0001",
                                                         "expires_on": today.isoformat()}).status_code == 422


def test_arco_request_gets_a_folio_and_the_legal_due_date(tx_client):
    login(tx_client, "fam-0001@ejemplo.test")
    r = tx_client.post("/api/privacy/arco", json={"right_type": "access", "contact": "fam-0001@ejemplo.test",
                                                  "description": "Quiero saber qué datos de salud de mi mamá tienen."})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["arco_id"].startswith("ARCO-") and body["days"] == 20
    assert body["due_on"] == add_business_days(date.fromisoformat(body["received_on"]), 20).isoformat()
    assert [a["arco_id"] for a in tx_client.get("/api/privacy/arco").json()] == [body["arco_id"]]
    login(tx_client, "coordinacion.a@ejemplo.test")
    assert body["arco_id"] in [a["arco_id"] for a in tx_client.get("/api/privacy/arco").json()]
    login(tx_client, "coordinacion.b@ejemplo.test")
    assert body["arco_id"] not in [a["arco_id"] for a in tx_client.get("/api/privacy/arco").json()]


def test_business_days_skip_weekends():
    assert add_business_days(date(2026, 11, 20), 1) == date(2026, 11, 23)     # Friday -> Monday
    assert add_business_days(date(2026, 11, 23), 20) == date(2026, 12, 21)


def test_audit_trail_is_for_direction_only_and_filters_blocked(tx_client):
    login(tx_client, "coordinacion.a@ejemplo.test")
    assert tx_client.get("/api/privacy/audit").status_code == 403
    login(tx_client, "owner@ejemplo.test")
    r = tx_client.get("/api/privacy/audit", params={"allowed": "false"}).json()
    assert r["total"] > 0 and all(not row["allowed"] for row in r["rows"])
    s = tx_client.get("/api/privacy/audit/summary").json()
    assert {"by_action", "by_day", "by_user"} <= s.keys()
