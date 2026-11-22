"""Pure dispatcher tests: no database (the same code SIRAG-D will import)."""
from datetime import datetime, time, timedelta

import pytest

from app.services import dispatcher as d

MX = d.MEXICO_CITY
T0 = datetime(2026, 11, 24, 10, 0, tzinfo=MX)       # a Tuesday
TRAFFIC = d.TrafficProfile({(dt, h): 20.0 for dt in ("weekday", "weekend") for h in range(24)})


def cg(cid, lat=19.40, lon=-99.10, skills=("nursing",), start=time(8), end=time(16), busy=()):
    return d.Caregiver(cid, frozenset(skills), start, end, lat, lon, tuple(busy))


def req(rid, priority="medium", at=T0, risk=1.0, created=T0 - timedelta(hours=1), skill="nursing", dur=30):
    return d.Request(rid, priority, skill, at, dur, 19.41, -99.11, created, risk)


def test_skill_shift_and_overlap_filter_candidates():
    busy_window = (T0 - timedelta(minutes=30), T0 + timedelta(minutes=10))
    options = d.rank_candidates(req("R1"), [
        cg("OK"), cg("WRONG_SKILL", skills=("therapy",)), cg("OFF_SHIFT", start=time(14), end=time(22)),
        cg("BUSY", busy=[busy_window])], TRAFFIC)
    assert [o.caregiver_id for o in options] == ["OK"]
    o = options[0]
    assert o.planned_end == T0 + timedelta(minutes=30) and o.planned_start < T0   # leaves before the visit


def test_night_shift_crossing_midnight():
    night = cg("NIGHT", start=time(20), end=time(8))
    assert d.rank_candidates(req("R", at=datetime(2026, 11, 25, 2, 0, tzinfo=MX)), [night], TRAFFIC)
    assert not d.rank_candidates(req("R", at=datetime(2026, 11, 25, 12, 0, tzinfo=MX)), [night], TRAFFIC)


def test_travel_time_uses_the_speed_of_the_hour():
    slow = d.TrafficProfile({(dt, h): (10.0 if h == 9 else 40.0) for dt in ("weekday", "weekend") for h in range(24)})
    far = cg("FAR", lat=19.50)
    fast_hour = d.rank_candidates(req("R", at=T0.replace(hour=13)), [far], slow)[0].travel_min
    rush_hour = d.rank_candidates(req("R", at=T0), [far], slow)[0].travel_min      # leaves at 9:xx
    assert rush_hour > 3 * fast_hour


def test_batch_never_double_books():
    decisions = d.dispatch([req("A"), req("B"), req("C")], [cg("ONLY")], TRAFFIC, now=T0)
    chosen = [x.chosen for x in decisions]
    assert sum(c is not None for c in chosen) == 1          # one nurse, one slot


def test_queue_order_priority_then_risk_then_wait():
    reqs = [req("LOW", "low", created=T0 - timedelta(hours=5)),
            req("MED_FRAGILE", "medium", risk=2.0),
            req("MED_OLD", "medium", risk=1.0, created=T0 - timedelta(hours=3)),
            req("MED_NEW", "medium", risk=1.0, created=T0 - timedelta(minutes=5)),
            req("HIGH", "high")]
    order = [r.request_id for r in d.order_queue(reqs, "risk_plus_live_traffic", T0)]
    assert order == ["HIGH", "MED_FRAGILE", "MED_OLD", "MED_NEW", "LOW"]
    fifo = [r.request_id for r in d.order_queue(reqs, "nearest", T0)]
    assert fifo[0] == "LOW"                                  # first come, first served


def test_risk_from_yaml_multipliers():
    m = {"chronic_lung_disease": 1.5, "age_80_plus": 1.3}
    assert d.patient_risk({"chronic_lung_disease": True, "age_80_plus": True, "stroke": True}, m) == pytest.approx(1.95)


def test_unknown_policy_is_rejected():
    with pytest.raises(ValueError):
        d.rank_candidates(req("R"), [cg("X")], TRAFFIC, policy="random")
