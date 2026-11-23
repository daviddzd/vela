"""Relays (dispatcher.relay_options, same function in the operation and SIRAG-D) and the week coverage view."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import text

from app.services import coverage
from app.services import dispatcher as dsp
from app.services import labor
from app.services import operations as ops
from tests.conftest import free_caregiver, login, session_on

TZ = dsp.MEXICO_CITY
TRAFFIC = dsp.TrafficProfile({(d, h): 25.0 for d in ("weekday", "weekend") for h in range(24)})
MONDAY = date(2026, 11, 30)


def _cg(cid, start, end, skill="caregiving", rest_day=None):
    return dsp.Caregiver(cid, frozenset({skill}), time(start), time(end), 19.36, -99.16, rest_day=rest_day)


def _night_service(hours=12, skill="caregiving"):
    at = datetime.combine(MONDAY, time(20), TZ)
    return dsp.Request("R", "medium", skill, at, hours * 60, 19.37, -99.15, at - timedelta(hours=2))


def test_a_12h_service_is_covered_by_two_people_at_the_shift_boundary():
    legal_night = [_cg("FIRST", 20, 3), _cg("SECOND", 1, 8)]          # "Cumplir jornada nocturna": 20-03 + 01-08
    [o] = dsp.rank_candidates(_night_service(), legal_night, TRAFFIC)
    assert o.caregiver_id == "FIRST" and o.relay.caregiver_id == "SECOND"
    boundary = datetime.combine(MONDAY + timedelta(days=1), time(3), TZ)
    assert o.planned_end == boundary == o.relay.arrival                 # hand-over at the end of the first shift
    assert o.visit_end == datetime.combine(MONDAY + timedelta(days=1), time(8), TZ)


def test_one_person_is_preferred_and_short_services_never_relay():
    team = [_cg("FIRST", 20, 3), _cg("SECOND", 1, 8), _cg("WHOLE", 20, 8)]
    [o] = dsp.rank_candidates(_night_service(), team, TRAFFIC)
    assert o.caregiver_id == "WHOLE" and o.relay is None
    assert labor.needs_relay(720) and not labor.needs_relay(480)       # 8 h = the longest legal shift
    assert dsp.rank_candidates(_night_service(hours=8), [_cg("FIRST", 20, 3), _cg("SECOND", 1, 8)], TRAFFIC) == []


def test_the_relay_needs_the_same_skill_and_its_shift():
    assert dsp.rank_candidates(_night_service(), [_cg("FIRST", 20, 3), _cg("SECOND", 1, 8, "nursing")], TRAFFIC) == []
    resting = _cg("SECOND", 1, 8, rest_day=MONDAY.isoweekday() + 1)    # rests on Tuesday: no shift starts at 01:00
    assert dsp.rank_candidates(_night_service(), [_cg("FIRST", 20, 3), resting], TRAFFIC) == []


def test_a_batch_books_both_people():
    pool = [_cg("FIRST", 20, 3), _cg("SECOND", 1, 8)]
    first, second = dsp.dispatch([_night_service(), _night_service()], pool, TRAFFIC,
                                 now=datetime.combine(MONDAY, time(12), TZ))
    assert first.chosen.relay is not None and second.chosen is None   # nobody is double-booked


def _relay_in_db(s, day):
    """A 12-h night nursing service of INS-B saved as a relay of two INS-B nurses (CUI-019, then CUI-017)."""
    for c in ("CUI-017", "CUI-019"):
        free_caregiver(s, c)
    start = datetime.combine(day, time(20), TZ)
    rid = s.scalar(text("""INSERT INTO service_requests (institution_id, patient_id, service_id, origin, priority,
                           scheduled_for, created_at, status) VALUES ('INS-B', 'PAC-0177', 'SRV-04', 'coordinator',
                           'medium', :t, now(), 'validated') RETURNING request_id"""), {"t": start})
    boundary = start + timedelta(hours=7)
    second = dsp.Option("CUI-017", 1.0, 10.0, boundary - timedelta(minutes=10), start + timedelta(hours=12), 0, boundary)
    first = dsp.Option("CUI-019", 1.0, 10.0, start - timedelta(minutes=10), boundary, 0, start, relay=second)
    aid = ops.save_assignment(s, "INS-B", rid, [first], approval="auto", assigned_by="USR-005")
    return rid, aid


def test_the_operation_saves_a_relay_as_two_legs_and_one_request(db_conn):
    with session_on(db_conn, "INS-B") as s:
        rid, aid = _relay_in_db(s, (ops.now() + timedelta(days=3)).date())
        legs = s.execute(text("SELECT caregiver_id, leg FROM assignments WHERE request_id = :r AND status = 'active' "
                              "ORDER BY leg"), {"r": rid}).all()
        assert [(l.caregiver_id, l.leg) for l in legs] == [("CUI-019", 1), ("CUI-017", 2)]
        view = s.execute(text("SELECT * FROM v_service_requests WHERE request_id = :r"), {"r": rid}).mappings().all()
        assert len(view) == 1 and view[0]["assignment_id"] == aid and view[0]["relay_caregiver_id"] == "CUI-017"
        assert view[0]["planned_end"] - view[0]["relay_at"] == timedelta(hours=5)


def test_the_service_ends_when_the_relay_finishes(db_conn):
    with session_on(db_conn, "INS-B") as s:
        rid, aid = _relay_in_db(s, (ops.now() + timedelta(days=3)).date())
        relay_aid = s.scalar(text("SELECT assignment_id FROM assignments WHERE request_id = :r AND leg = 2"), {"r": rid})
        status = lambda: s.scalar(text("SELECT status FROM service_requests WHERE request_id = :r"), {"r": rid})  # noqa: E731
        kw = {"user_id": "USR-005", "institution_id": "INS-B"}
        try:
            ops.mark_arrived(s, assignment_id=relay_aid, **kw)          # the relay cannot arrive before the first person
            raise AssertionError("relay arrived first")
        except ops.InvalidState:
            pass
        ops.mark_arrived(s, assignment_id=aid, **kw)
        assert status() == "in_progress"
        ops.mark_arrived(s, assignment_id=relay_aid, **kw)
        ops.mark_finished(s, assignment_id=aid, **kw)                   # the first person leaves: still in progress
        assert status() == "in_progress"
        ops.mark_finished(s, assignment_id=relay_aid, **kw)
        assert status() == "completed"


def test_if_the_relay_cannot_go_before_the_start_the_whole_service_is_redispatched(db_conn):
    with session_on(db_conn, "INS-B") as s:
        rid, aid = _relay_in_db(s, (ops.now() + timedelta(days=3)).date())
        relay_aid = s.scalar(text("SELECT assignment_id FROM assignments WHERE request_id = :r AND leg = 2"), {"r": rid})
        assert ops.release_request(s, rid, relay_aid)
        assert s.scalar(text("SELECT count(*) FROM assignments WHERE request_id = :r AND status = 'active'"), {"r": rid}) == 0
        assert s.scalar(text("SELECT status FROM service_requests WHERE request_id = :r"), {"r": rid}) == "queued"


def test_caregiver_agenda_shows_the_relay(tx_client, db_conn):
    with session_on(db_conn, "INS-B") as s:
        rid, _ = _relay_in_db(s, ops.now().date())
        s.commit()
    login(tx_client, "cui-017@ejemplo.test")
    mine = [v for v in tx_client.get("/api/visits/mine").json() if v["request_id"] == rid]
    assert mine and mine[0]["relay_role"] == "relay" and mine[0]["step"] == "wait" and mine[0]["relay_partner_name"]


# ---- week coverage ---------------------------------------------------------------------------------

def test_a_rest_day_opens_a_gap_until_the_next_shift_starts():
    tuesday = 2
    people = [coverage.Person(_cg("EARLY", 8, 16, "nursing", rest_day=tuesday)),
              coverage.Person(_cg("LATE", 10, 18, "nursing", rest_day=4))]
    gaps = coverage.week_gaps(people, MONDAY)          # Monday 30 Nov ... Sunday 6 Dec 2026
    tue = [g for g in gaps if g["start"].date() == MONDAY + timedelta(days=1)]
    assert [(g["skill"], g["start"].time(), g["end"].time()) for g in tue] == [("nursing", time(8), time(10))]
    assert "Martes 1 8:00–10:00: sin enfermería" in ops.coverage_message(tue[0])
    thu = [g for g in gaps if g["start"].date() == MONDAY + timedelta(days=3)]
    assert [(g["start"].time(), g["end"].time()) for g in thu] == [(time(16), time(18))]


def test_out_of_service_counts_and_unplanned_hours_do_not():
    out = ((datetime.combine(MONDAY, time(0), TZ), None),)
    gaps = coverage.week_gaps([coverage.Person(_cg("ONLY", 8, 16, "therapy"), out)], MONDAY, days=1)
    assert [(g["start"].time(), g["end"].time()) for g in gaps] == [(time(8), time(16))]   # nothing at night: no plan
    assert coverage.week_gaps([coverage.Person(_cg("ONLY", 8, 16, "therapy"))], MONDAY, days=1) == []


def test_coverage_endpoint_and_alerts(tx_client, db_conn):
    login(tx_client, "coordinacion.b@ejemplo.test")
    c = tx_client.get("/api/staff/coverage").json()
    assert len(c["days"]) == 7 and c["gaps"] == sum(len(d["gaps"]) for d in c["days"])
    with session_on(db_conn, "*") as s:
        ops.coverage_alerts(s)
        assert ops.coverage_alerts(s) == 0                                  # idempotent
        n = s.scalar(text("SELECT count(*) FROM alerts WHERE type = 'coverage' AND status = 'open' AND institution_id = 'INS-B'"))
        assert n == len(ops.coverage_gaps(s, "INS-B"))
