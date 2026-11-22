"""Privacy: persons under RLS, views that respect RLS, aggregated population views, health-data
consent gate and the physician's scope."""
from sqlalchemy import text

from app.core.db import tenant_session
from tests.conftest import login, session_on

INS_B_PATIENT = "PAC-0151"


def test_persons_only_shows_own_patients():
    with tenant_session(None) as s:
        assert s.scalar(text("SELECT count(*) FROM persons")) == 0
    with tenant_session("INS-A") as s:
        assert s.scalar(text("SELECT count(*) FROM persons")) == 150
    with tenant_session("*") as s:
        assert s.scalar(text("SELECT count(*) FROM persons")) == 20000


def test_ins_a_cannot_read_ins_b_patient_through_persons():
    with tenant_session("*") as s:
        person_b = s.scalar(text("SELECT person_id FROM patients WHERE patient_id = :p"), {"p": INS_B_PATIENT})
    with tenant_session("INS-A") as s:
        for source in ("persons", "v_persons"):
            assert s.scalar(text(f"SELECT count(*) FROM {source} WHERE person_id = :x"), {"x": person_b}) == 0
        assert s.scalar(text("SELECT count(*) FROM v_patients WHERE patient_id = :p"), {"p": INS_B_PATIENT}) == 0


def test_views_no_longer_bypass_rls():
    """Before migration 0002 these views ran with the owner's rights and returned every row."""
    with tenant_session(None) as s:
        for view in ("v_persons", "v_patients", "v_consents", "v_service_requests"):
            assert s.scalar(text(f"SELECT count(*) FROM {view}")) == 0, view


def test_district_views_are_aggregated_and_anonymous():
    with tenant_session("INS-A") as s:   # any tenant: aggregates cover the whole synthetic population
        rows = s.execute(text("SELECT * FROM v_district_population")).mappings().all()
        cols = set(rows[0].keys())
        conditions = s.execute(text("SELECT * FROM v_population_conditions")).mappings().all()
    assert sum(r["persons_60_plus"] for r in rows) == 20000 and len(rows) == 16
    assert not cols & {"person_id", "first_name", "paternal_surname", "maternal_surname", "birth_date", "lat", "lon"}
    assert {c["condition"] for c in conditions} >= {"diabetes", "hypertension"}


def test_health_data_hidden_without_consent_and_audited(tx_client, db_conn):
    login(tx_client, "coordinacion.a@ejemplo.test")
    assert tx_client.get("/api/patients/PAC-0001").json()["health"] is not None
    with session_on(db_conn, "INS-A") as s:
        s.execute(text("UPDATE consents SET granted = false WHERE patient_id = 'PAC-0001' AND type = 'health_data'"))
        s.commit()
    body = tx_client.get("/api/patients/PAC-0001").json()
    assert body["health"] is None and body["health_notice"] == "Falta consentimiento"
    assert body["full_name"]                                               # administrative data still shown
    with session_on(db_conn, None) as s:
        assert s.scalar(text("""SELECT count(*) FROM audit_log WHERE action = 'health_data_blocked'
                                AND entity_id = 'PAC-0001' AND NOT allowed""")) >= 1


def test_physician_sees_only_own_patients(tx_client):
    with tenant_session("INS-A") as s:
        mine = s.scalar(text("""SELECT r.patient_id FROM assignments a JOIN service_requests r USING (request_id)
                                WHERE a.caregiver_id = 'CUI-001' LIMIT 1"""))
        not_mine = s.scalar(text("""SELECT patient_id FROM patients pa WHERE NOT EXISTS (
                                      SELECT 1 FROM assignments a JOIN service_requests r USING (request_id)
                                      WHERE a.caregiver_id = 'CUI-001' AND r.patient_id = pa.patient_id)
                                    LIMIT 1"""))
    login(tx_client, "cui-001@ejemplo.test")
    listed = {p["patient_id"] for p in tx_client.get("/api/patients").json()}
    assert mine in listed and not_mine not in listed and len(listed) == 90
    assert tx_client.get(f"/api/patients/{mine}").status_code == 200
    r = tx_client.get(f"/api/patients/{not_mine}")
    assert r.status_code == 403 and "no está a tu cargo" in r.json()["detail"]
    with tenant_session(None) as s:     # denial was committed on its own connection
        assert s.scalar(text("""SELECT count(*) FROM audit_log WHERE action = 'blocked_out_of_scope'
                                AND entity_id = :p AND user_id = 'USR-003'"""), {"p": not_mine}) >= 1
