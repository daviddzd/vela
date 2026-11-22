"""/pacientes, /pacientes/:id, /personal and consent inside automatic decisions (docs/spec/11):
without health_data the dispatcher, the queue and the contingency proposals do not use health-based risk."""
from datetime import timedelta

from sqlalchemy import text

from app.services import contingency as ct
from app.services import operations as ops
from tests.conftest import free_caregiver, login, session_on

PHYSICIAN = "cui-001@ejemplo.test"          # CUI-001, INS-A


def physician_patient(db_conn) -> str:
    with session_on(db_conn, "INS-A") as s:
        return s.scalar(text("""SELECT r.patient_id FROM assignments a JOIN service_requests r USING (request_id)
                                JOIN care_plans cp ON cp.patient_id = r.patient_id AND cp.active
                                WHERE a.caregiver_id = 'CUI-001' ORDER BY r.patient_id LIMIT 1"""))


def revoke_health(s, where: str, params: dict) -> None:
    s.execute(text(f"UPDATE consents SET granted = false WHERE type = 'health_data' AND {where}"), params)


# ---- consent inside the dispatcher and the contingency ---------------------------------------------------

def test_dispatcher_uses_only_priority_without_health_consent(db_conn):
    with session_on(db_conn, "INS-A") as s:
        rid = s.scalar(text("""SELECT r.request_id FROM service_requests r JOIN v_patients p USING (patient_id)
                               WHERE p.chronic_disease_count > 0 AND r.institution_id = 'INS-A' LIMIT 1"""))
        patient = s.scalar(text("SELECT patient_id FROM service_requests WHERE request_id = :r"), {"r": rid})
        with_consent = ops.load_request(s, rid).risk
        assert with_consent != 1.0                                     # health conditions change the risk
        revoke_health(s, "patient_id = :p", {"p": patient})
        assert ops.load_request(s, rid).risk == 1.0                    # neutral: only the priority counts


def test_contingency_does_not_target_sensitive_patients_without_health_consent(tx_client, db_conn):
    login(tx_client, "owner@ejemplo.test")
    with session_on(db_conn, "*") as s:
        revoke_health(s, "institution_id = 'INS-A'", {})
        s.commit()
    assert tx_client.post("/api/demo/scenario", json={"scenario": "contingency_east"}).status_code == 200
    with session_on(db_conn, "*") as s:
        ct.detect(s)
        ev = s.scalar(text("SELECT event_id FROM contingency_events WHERE ended_at IS NULL AND origin = 'demo_scenario'"))
        assert s.scalar(text("""SELECT count(*) FROM contingency_proposals WHERE event_id = :e
                                AND institution_id = 'INS-A' AND kind IN ('raise_priority','notify_family')"""), {"e": ev}) == 0
        # ...although INS-A does have pollution-sensitive patients in the affected districts (control)
        assert s.scalar(text("""SELECT count(*) FROM v_patients p JOIN contingency_events e ON p.district_id = ANY(e.districts)
                                WHERE e.event_id = :e AND p.institution_id = 'INS-A' AND p.active AND p.pollution_sensitive"""),
                        {"e": ev}) > 0


# ---- /pacientes ------------------------------------------------------------------------------------------

def test_list_scopes_filters_and_risk_only_with_consent(tx_client, db_conn):
    login(tx_client, "coordinacion.a@ejemplo.test")
    everyone = tx_client.get("/api/patients").json()
    sensitive = tx_client.get("/api/patients", params={"sensitive": "true"}).json()
    assert 0 < len(sensitive) < len(everyone) and all(p["pollution_sensitive"] for p in sensitive)
    with_risk = next(p for p in everyone if p["health_consent"])
    assert with_risk["risk_level"] in ("low", "medium", "high")
    with session_on(db_conn, "INS-A") as s:
        revoke_health(s, "patient_id = :p", {"p": with_risk["patient_id"]})
        s.commit()
    row = next(p for p in tx_client.get("/api/patients").json() if p["patient_id"] == with_risk["patient_id"])
    assert row["risk"] is None and row["risk_level"] is None and row["dependency_level"] is None
    login(tx_client, PHYSICIAN)
    assert len(tx_client.get("/api/patients").json()) < len(everyone)   # physician: own patients only


def test_record_minimizes_what_each_role_sees(tx_client, db_conn):
    pid = physician_patient(db_conn)
    login(tx_client, "coordinacion.a@ejemplo.test")
    r = tx_client.get(f"/api/patients/{pid}/record").json()
    assert r["can_request"] and not r["can_edit_plan"] and "email" in r["family"][0]
    assert all(v["transcript"] is None for v in r["voice_reports"])
    login(tx_client, PHYSICIAN)
    r = tx_client.get(f"/api/patients/{pid}/record").json()
    assert r["can_edit_plan"] and not r["can_request"] and "email" not in r["family"][0]
    login(tx_client, "coordinacion.b@ejemplo.test")
    assert tx_client.get(f"/api/patients/{pid}/record").status_code == 403


# ---- care plan changes -----------------------------------------------------------------------------------

def test_changing_a_plan_cancels_unassigned_future_visits_and_alerts_assigned_ones(tx_client, db_conn):
    pid = physician_patient(db_conn)
    with session_on(db_conn, "INS-A") as s:
        plan = s.execute(text("SELECT care_plan_id, service_id FROM care_plans WHERE patient_id = :p AND active LIMIT 1"),
                         {"p": pid}).one()
        free_caregiver(s, "CUI-004")
        ids = []
        for hours, st in ((26, "queued"), (50, "assigned")):        # different days (one visit per plan and day)
            ids.append(s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                                       scheduled_for, created_at, status, care_plan_id, plan_date)
                                       VALUES ('INS-A', :p, :s, 'care_plan', 'medium', now() + make_interval(hours => :h),
                                       now(), :st, :cp, (now() + make_interval(hours => :h))::date) RETURNING request_id"""),
                                  {"p": pid, "s": plan.service_id, "h": hours, "st": st, "cp": plan.care_plan_id}))
        s.execute(text("""INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval, assigned_at,
                          planned_start, planned_end) VALUES (:r, 'INS-A', 'CUI-004', 'USR-002', 'auto', now(),
                          now() + interval '49 hours 30 minutes', now() + interval '50 hours 30 minutes')"""), {"r": ids[1]})
        s.commit()
    body = {"service_id": plan.service_id, "times_per_week": 2, "reason": "Ajuste tras revisión médica"}
    login(tx_client, "coordinacion.a@ejemplo.test")
    assert tx_client.put(f"/api/patients/{pid}/care-plans/{plan.care_plan_id}", json=body).status_code == 403
    login(tx_client, PHYSICIAN)
    r = tx_client.put(f"/api/patients/{pid}/care-plans/{plan.care_plan_id}", json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["cancelled"] == [ids[0]] and out["assigned"] == [ids[1]]
    with session_on(db_conn, "INS-A") as s:
        assert s.execute(text("SELECT status, status_reason FROM service_requests WHERE request_id = :r"),
                         {"r": ids[0]}).one() == ("cancelled", "care_plan_changed")
        assert s.scalar(text("SELECT status FROM service_requests WHERE request_id = :r"), {"r": ids[1]}) == "assigned"
        assert s.scalar(text("SELECT count(*) FROM alerts WHERE type = 'care_plan' AND message LIKE :m"), {"m": f"%{ids[1]}%"}) == 1
        assert s.scalar(text("SELECT active FROM care_plans WHERE care_plan_id = :c"), {"c": plan.care_plan_id}) is False
        new = s.execute(text("SELECT active, times_per_week, replaces FROM care_plans WHERE care_plan_id = :c"),
                        {"c": out["care_plan_id"]}).one()
        assert new.active and float(new.times_per_week) == 2 and new.replaces == plan.care_plan_id
        assert s.scalar(text("SELECT count(*) FROM audit_log WHERE action = 'care_plan_changed' AND entity_id = :c"),
                        {"c": plan.care_plan_id}) == 1


def test_physician_cannot_change_a_plan_of_someone_not_in_their_care(tx_client, db_conn):
    with session_on(db_conn, "INS-A") as s:
        other = s.execute(text("""SELECT cp.patient_id, cp.care_plan_id, cp.service_id FROM care_plans cp WHERE cp.active
                                  AND NOT EXISTS (SELECT 1 FROM assignments a JOIN service_requests r USING (request_id)
                                                  WHERE a.caregiver_id = 'CUI-001' AND r.patient_id = cp.patient_id)
                                  LIMIT 1""")).one()
    login(tx_client, PHYSICIAN)
    r = tx_client.post(f"/api/patients/{other.patient_id}/care-plans/{other.care_plan_id}/end")
    assert r.status_code == 403


# ---- /personal -------------------------------------------------------------------------------------------

def test_staff_out_of_service_and_back_with_the_same_logic(tx_client, db_conn):
    login(tx_client, "fam-0001@ejemplo.test")
    assert tx_client.get("/api/staff").status_code == 403
    login(tx_client, "coordinacion.a@ejemplo.test")
    staff = tx_client.get("/api/staff").json()["staff"]
    assert staff and all(c["caregiver_id"] for c in staff) and {"on_shift_now", "week_load_pct", "skills"} <= staff[0].keys()
    r = tx_client.post("/api/staff/CUI-005/out-of-service", json={"reason": "Incapacidad"})
    assert r.status_code == 200 and r.json()["caregiver_id"] == "CUI-005"
    assert tx_client.post("/api/staff/CUI-005/out-of-service", json={"reason": "otra vez"}).status_code == 409
    row = next(c for c in tx_client.get("/api/staff").json()["staff"] if c["caregiver_id"] == "CUI-005")
    assert row["out_of_service"] and not row["on_shift_now"]
    assert tx_client.post("/api/staff/CUI-005/back-in-service").status_code == 200
    with session_on(db_conn, "INS-A") as s:
        assert "CUI-005" in [c.caregiver_id for c in ops.load_caregivers(s, "INS-A", ops.now() + timedelta(hours=1))]
    with session_on(db_conn, "*") as s:
        other = s.scalar(text("SELECT caregiver_id FROM caregivers WHERE institution_id = 'INS-B' LIMIT 1"))
    assert tx_client.post(f"/api/staff/{other}/out-of-service", json={"reason": "x" * 5}).status_code == 403
