"""Plan visits of the next days, before the worker creates them (care_plans.forecast): the SAME deterministic draw
the worker uses, never a visit twice, and shown to the family (7 days) and on the board (today and tomorrow)."""
from datetime import datetime, time, timedelta

from sqlalchemy import text

from app.services import care_plans
from app.services import operations as ops
from tests.conftest import login, session_on


def test_the_forecast_is_the_worker_draw_and_skips_created_visits(db_conn):
    with session_on(db_conn, "INS-A") as s:
        now = datetime.combine(ops.now().date(), time(6), ops.MEXICO_CITY)
        fc = care_plans.forecast(s, now=now, days=7)
        assert fc, "INS-A has active care plans"
        tpw = dict(s.execute(text("SELECT care_plan_id, times_per_week::float FROM care_plans WHERE active")).all())
        svc = dict(s.execute(text("SELECT care_plan_id, service_id FROM care_plans WHERE active")).all())
        for v in fc[:30]:
            day = v["scheduled_for"].astimezone(ops.MEXICO_CITY).date()
            assert v["scheduled_for"] == care_plans.planned_visit(v["care_plan_id"], day, tpw[v["care_plan_id"]], svc[v["care_plan_id"]])
            assert now < v["scheduled_for"] < now + timedelta(days=7)
        # once the worker creates one of them, it leaves the forecast
        first = fc[0]
        created = care_plans.create_due_requests(s, now=first["scheduled_for"] - timedelta(hours=1))
        assert created
        day = first["scheduled_for"].astimezone(ops.MEXICO_CITY).date()
        again = care_plans.forecast(s, now=now, days=7)
        assert (first["care_plan_id"], first["scheduled_for"]) not in {(v["care_plan_id"], v["scheduled_for"]) for v in again}
        assert s.scalar(text("SELECT count(*) FROM service_requests WHERE care_plan_id = :c AND plan_date = :d"),
                        {"c": first["care_plan_id"], "d": day}) == 1


def test_family_sees_7_days_and_the_last_3_visits(tx_client, db_conn):
    login(tx_client, "fam-0001@ejemplo.test")
    o = tx_client.get("/api/family/overview").json()
    assert len(o["last_visits"]) <= 3
    when = [v["scheduled_for"] for v in o["upcoming"]]
    assert when == sorted(when)
    limit = (ops.now() + timedelta(days=7)).isoformat()
    assert all(w < limit for w in when)
    assert all(v["status"] in ("planned", "validated", "queued", "assigned", "in_progress") for v in o["upcoming"])


def test_board_lists_today_and_tomorrow(tx_client):
    login(tx_client, "coordinacion.a@ejemplo.test")
    b = tx_client.get("/api/board").json()
    end = datetime.combine(ops.now().date() + timedelta(days=2), time(0), ops.MEXICO_CITY).isoformat()
    assert all(v["scheduled_for"] < end for v in b["upcoming"])
