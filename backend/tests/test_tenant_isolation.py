"""Acceptance criterion A2 (docs/spec/10): without an institution the API sees 0 rows, and a user of
INS-A gets 403 when asking for a patient of INS-B, with the attempt stored in audit_log."""

import pytest
from sqlalchemy import text

from app.core.db import tenant_session
from tests.conftest import login

TENANT_TABLES = ["institutions", "patients", "family_members", "consents", "caregivers",
                 "care_plans", "service_requests", "assignments"]
INS_B_PATIENT = "PAC-0151"   # belongs to INS-B in database/seed/patients.csv
INS_A_PATIENT = "PAC-0001"


def count(session, table: str) -> int:
    return session.scalar(text(f"SELECT count(*) FROM {table}"))


@pytest.mark.parametrize("table", TENANT_TABLES)
def test_without_institution_api_role_sees_zero_rows(table):
    with tenant_session(None) as s:
        assert s.scalar(text("SELECT current_user")) == "vela_api"
        assert count(s, table) == 0


def test_with_institution_sees_only_its_rows():
    with tenant_session("INS-A") as s:
        assert count(s, "patients") == 150
        assert s.scalar(text("SELECT count(DISTINCT institution_id) FROM patients")) == 1
    with tenant_session("*") as s:
        assert count(s, "patients") == 400


def test_setting_is_local_to_the_transaction():
    """SET LOCAL semantics: after commit the next transaction on the same connection sees nothing."""
    with tenant_session("INS-A") as s:
        assert count(s, "patients") == 150
    with tenant_session(None) as s:
        assert count(s, "patients") == 0


def test_cross_tenant_read_is_403_and_audited(client):
    with tenant_session(None) as s:   # position in the trail, not the clock (WSL2 moves the clock back ~3 s)
        last_id = s.scalar(text("SELECT coalesce(max(audit_id), 0) FROM audit_log"))
    assert login(client, "coordinacion.a@ejemplo.test").status_code == 200

    assert client.get(f"/api/patients/{INS_A_PATIENT}").status_code == 200   # own institution
    r = client.get(f"/api/patients/{INS_B_PATIENT}")
    assert r.status_code == 403
    assert "otra institución" in r.json()["detail"]
    assert client.get("/api/patients/PAC-9999").status_code == 404           # does not exist

    with tenant_session(None) as s:  # audit_log is not under RLS; vela_api may SELECT it
        row = s.execute(text("""SELECT user_id, institution_id, allowed, detail->>'target_institution'
                                FROM audit_log
                                WHERE action = 'blocked_cross_tenant' AND entity_id = :p
                                  AND audit_id > :last
                                ORDER BY audit_id DESC LIMIT 1"""),
                        {"p": INS_B_PATIENT, "last": last_id}).one()
    assert tuple(row) == ("USR-002", "INS-A", False, "INS-B")


def test_owner_reads_any_institution(client):
    login(client, "owner@ejemplo.test")
    assert client.get(f"/api/patients/{INS_B_PATIENT}").json()["institution_id"] == "INS-B"


def test_caregiver_and_family_cannot_open_patient_records(client):
    for email in ("cui-003@ejemplo.test", "fam-0001@ejemplo.test"):
        login(client, email)
        assert client.get(f"/api/patients/{INS_A_PATIENT}").status_code == 403


def test_entity_institution_only_answers_known_entities():
    with tenant_session(None) as s:
        q = text("SELECT entity_institution(:e, :i)")
        assert s.scalar(q, {"e": "patient", "i": INS_B_PATIENT}) == "INS-B"
        assert s.scalar(q, {"e": "patient", "i": "PAC-9999"}) is None
        assert s.scalar(q, {"e": "users", "i": "USR-001"}) is None          # not in the fixed list
        assert s.scalar(q, {"e": "patient; DROP TABLE x", "i": "1"}) is None


def test_entity_institution_is_not_executable_by_public():
    with tenant_session(None) as s:
        # grantee = 0 in aclexplode() means PUBLIC
        public_grants = s.scalar(text("""SELECT count(*) FROM pg_proc, aclexplode(proacl) a
                                          WHERE proname = 'entity_institution' AND a.grantee = 0"""))
        api_can = s.scalar(text("SELECT has_function_privilege('vela_api', "
                                "'entity_institution(text,text)', 'EXECUTE')"))
        definer, config = s.execute(text("""SELECT prosecdef, proconfig::text FROM pg_proc
                                            WHERE proname = 'entity_institution'""")).one()
    assert public_grants == 0 and api_can and definer
    assert "search_path=public" in config


def test_ws_route_answers():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app).websocket_connect("/ws/ping") as ws:
        assert ws.receive_json() == {"type": "pong"}


def test_audit_log_stays_append_only_for_the_api_role():
    with tenant_session(None) as s:
        can_update = s.scalar(text("SELECT has_table_privilege('vela_api', 'audit_log', 'UPDATE')"))
        can_delete = s.scalar(text("SELECT has_table_privilege('vela_api', 'audit_log', 'DELETE')"))
    assert not can_update and not can_delete
