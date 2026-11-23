"""Labor rules (LFT arts. 60, 61, 69; app/services/labor.py), shared by the operation and SIRAG-D."""
from datetime import datetime, time, timedelta

from sqlalchemy import text

from app.services import dispatcher as dsp
from app.services import labor
from app.services import operations as ops
from tests.conftest import login, session_on


def test_shift_type_comes_from_the_hours_not_the_label():
    assert labor.shift_type(time(10), time(18)) == "diurna"          # labelled "mixed" in the seed: legally daytime
    assert labor.shift_type(time(14), time(22)) == "mixta"           # 2 h of night (< 3.5 h)
    assert labor.shift_type(time(20), time(8)) == "nocturna"
    assert labor.shift_type(time(16), time(23, 30)) == "nocturna"    # exactly 3.5 h of night -> nocturna (art. 60)


def test_legal_shift_shortens_mixta_and_only_flags_nocturna():
    evening = labor.legal_shift(time(14), time(22))
    assert evening["end"] == time(21, 30) and evening["adjusted"] and not evening["exceeds"]   # 7.5 h (art. 61)
    day = labor.legal_shift(time(10), time(18))
    assert day["end"] == time(18) and not day["adjusted"] and not day["exceeds"]
    night = labor.legal_shift(time(20), time(8))
    assert night["end"] == time(8) and not night["adjusted"] and night["exceeds"] and night["max_hours"] == 7


def test_rotation_spreads_rest_days_inside_a_group():
    people = [{"caregiver_id": f"C{i}", "institution_id": "X", "shift_start": time(8), "shift_end": time(16),
               "skill": "nursing"} for i in range(7)]
    assert sorted(labor.assign_rest_days(people).values()) == [1, 2, 3, 4, 5, 6, 7]


def test_dispatcher_never_uses_the_rest_day():
    tuesday = datetime(2026, 12, 1, 9, 0, tzinfo=dsp.MEXICO_CITY)
    cg = dsp.Caregiver("C", frozenset({"nursing"}), time(8), time(16), 19.4, -99.1, rest_day=2)
    assert not dsp.within_shift(cg, tuesday, tuesday + timedelta(hours=1))
    assert dsp.within_shift(cg, tuesday + timedelta(days=1), tuesday + timedelta(days=1, hours=1))
    night = dsp.Caregiver("N", frozenset({"nursing"}), time(20), time(8), 19.4, -99.1, rest_day=2)
    monday_night = datetime(2026, 12, 1, 2, 0, tzinfo=dsp.MEXICO_CITY)   # shift that started Monday 20:00: works
    assert dsp.within_shift(night, monday_night, monday_night + timedelta(minutes=30))


def test_the_database_has_a_rest_day_for_everyone_and_legal_day_shifts(db_conn):
    with session_on(db_conn, "*") as s:
        rows = s.execute(text("SELECT rest_day, shift_start, shift_end FROM caregivers WHERE active")).all()
    assert rows and all(1 <= r.rest_day <= 7 for r in rows)
    assert all(not labor.legal_shift(r.shift_start, r.shift_end)["exceeds"]
               for r in rows if labor.shift_type(r.shift_start, r.shift_end) != "nocturna")


def test_changing_the_rest_day_redispatches_visits_that_fall_on_it(tx_client, db_conn):
    with session_on(db_conn, "INS-A") as s:
        day = (ops.now() + timedelta(days=2)).date()
        start = datetime.combine(day, time(11), dsp.MEXICO_CITY)
        rid = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                               scheduled_for, created_at, status) VALUES ('INS-A', 'PAC-0002', 'SRV-02', 'coordinator',
                               'medium', :t, now(), 'assigned') RETURNING request_id"""), {"t": start + timedelta(minutes=20)})
        s.execute(text("UPDATE caregivers SET rest_day = :d WHERE caregiver_id = 'CUI-004'"),
                  {"d": (day.isoweekday() % 7) + 1})                                   # rests another day
        s.execute(text("""UPDATE assignments SET status = 'reassigned' WHERE caregiver_id = 'CUI-004' AND status = 'active'
                          AND planned_start IS NOT NULL AND arrived_at IS NULL"""))
        s.execute(text("""INSERT INTO assignments (request_id, institution_id, caregiver_id, assigned_by, approval, assigned_at,
                          planned_start, planned_end) VALUES (:r, 'INS-A', 'CUI-004', 'USR-002', 'auto', now(), :a, :b)"""),
                  {"r": rid, "a": start, "b": start + timedelta(minutes=50)})
        s.commit()
    login(tx_client, "coordinacion.a@ejemplo.test")
    r = tx_client.put("/api/staff/CUI-004/rest-day", json={"rest_day": day.isoweekday()})
    assert r.status_code == 200 and r.json()["redispatched"] == [rid]
    with session_on(db_conn, "INS-A") as s:
        assert s.scalar(text("SELECT count(*) FROM assignments WHERE request_id = :r AND caregiver_id = 'CUI-004' "
                             "AND status = 'active'"), {"r": rid}) == 0
        assert s.scalar(text("SELECT count(*) FROM audit_log WHERE action = 'caregiver_rest_day_changed' "
                             "AND entity_id = 'CUI-004'")) >= 1


def test_night_shifts_above_the_legal_maximum_raise_one_alert_and_are_not_changed(db_conn):
    with session_on(db_conn, "*") as s:
        night = s.scalar(text("SELECT count(*) FROM caregivers WHERE active AND shift_start = '20:00' AND shift_end = '08:00'"))
        assert ops.labor_alerts(s) == night and ops.labor_alerts(s) == 0              # idempotent
        assert s.scalar(text("SELECT count(*) FROM alerts WHERE type = 'labor' AND status = 'open'")) >= night
        assert s.scalar(text("SELECT count(*) FROM caregivers WHERE shift_start = '20:00' AND shift_end = '08:00'")) == night


def test_staff_shows_rest_day_and_the_legal_flag(tx_client):
    login(tx_client, "coordinacion.b@ejemplo.test")
    staff = tx_client.get("/api/staff").json()["staff"]
    night = [c for c in staff if c["legal_type"] == "nocturna"]
    assert night and all(c["exceeds_legal"] for c in night)
    assert all(1 <= c["rest_day"] <= 7 for c in staff)
