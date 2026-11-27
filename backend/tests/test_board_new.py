"""Board: a request created or assigned in the last 10 minutes goes first in "Próximas visitas" and is marked new
(team decision 26 Nov 2026). Before, a new visit for tomorrow could be number 13 of a list that shows 12.
Everything runs inside a transaction that is rolled back (tx_client / db_conn in conftest.py)."""
from datetime import datetime, timedelta

from sqlalchemy import text

from app.routers.board import NEW_MINUTES
from app.services.dispatcher import MEXICO_CITY
from tests.conftest import login, session_on

SHOWN = 12                      # BoardPage shows the first 12 of "Próximas visitas"
NURSING_VISIT = "SRV-02"


def tomorrow_at(hour: int) -> str:
    day = datetime.now(MEXICO_CITY).date() + timedelta(days=1)
    return datetime(day.year, day.month, day.day, hour).isoformat()   # naive = CDMX time


def family_asks_for_tomorrow_11(client) -> dict:
    """fam-0002 (PAC-0002, INS-A, medium priority) asks for nursing tomorrow at 11:00, as in the demo."""
    login(client, "fam-0002@ejemplo.test")
    r = client.post("/api/requests", json={"service_id": NURSING_VISIT, "scheduled_for": tomorrow_at(11)})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "assigned", r.json()
    return r.json()


def test_new_request_for_tomorrow_is_first_among_more_than_12(tx_client):
    req = family_asks_for_tomorrow_11(tx_client)
    login(tx_client, "coordinacion.a@ejemplo.test")
    up = tx_client.get("/api/board").json()["upcoming"]
    assert len(up) > SHOWN, f"the scenario needs more than {SHOWN} upcoming visits, there are {len(up)}"
    first = up[0]
    assert first["request_id"] == req["request_id"] and first["is_new"] is True
    assert first["caregiver_name"]                                   # it says who goes
    # without the change it would have been hidden: by time alone it is not among the first 12
    by_time = sorted(up, key=lambda v: v["scheduled_for"])
    assert [v.get("request_id") for v in by_time].index(req["request_id"]) >= SHOWN
    # the rest keeps its order by time
    rest = [v["scheduled_for"] for v in up[1:]]
    assert rest == sorted(rest)


def test_other_institution_does_not_see_it(tx_client):
    req = family_asks_for_tomorrow_11(tx_client)
    login(tx_client, "coordinacion.b@ejemplo.test")
    up = tx_client.get("/api/board").json()["upcoming"]
    assert req["request_id"] not in {v.get("request_id") for v in up}
    assert "PAC-0002" not in {v["patient_id"] for v in up}
    assert not any(v.get("is_new") for v in up)


def test_after_10_minutes_it_is_not_new_any_more(tx_client, db_conn):
    req = family_asks_for_tomorrow_11(tx_client)
    with session_on(db_conn, "INS-A") as s:
        s.execute(text("UPDATE service_requests SET created_at = now() - make_interval(mins => :m + 1) "
                       "WHERE request_id = :r"), {"m": NEW_MINUTES, "r": req["request_id"]})
        s.execute(text("UPDATE assignments SET assigned_at = now() - make_interval(mins => :m + 1) "
                       "WHERE request_id = :r"), {"m": NEW_MINUTES, "r": req["request_id"]})
        s.commit()
    login(tx_client, "coordinacion.a@ejemplo.test")
    up = tx_client.get("/api/board").json()["upcoming"]
    mine = [v for v in up if v.get("request_id") == req["request_id"]]
    assert mine and mine[0]["is_new"] is False
    when = [v["scheduled_for"] for v in up]
    assert when == sorted(when)
