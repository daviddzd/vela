"""SIRAG-D tests. Run:  docker compose run --rm sim pytest -q simulation/tests"""
import ast
from pathlib import Path

from app.services import dispatcher as dsp
from simulation.sirag import model as M
from simulation.sirag.data import load_world
from simulation.sirag.runner import run_one

SIM = Path(__file__).resolve().parents[1]


def test_reproducible_with_the_same_seed():
    p = M.Params("risk_plus_live_traffic", "normal", 3)
    assert run_one(p) == run_one(p)


def test_common_random_numbers_same_crises_for_every_policy():
    """In replication r every policy faces the same care-plan visits and (almost always) the same crises."""
    w = load_world()
    keys = {}
    for pol in ("nearest", "risk_priority", "risk_plus_live_traffic", "vela_timeout", "human_dispatcher"):
        reqs = M.Model(w, M.Params(pol, "normal", 5)).run()
        keys[pol] = {r.key for r in reqs if r.kind == "plan"}, [r.key for r in reqs if r.kind == "crisis"][:3]
    plans = {k: v[0] for k, v in keys.items()}
    first_crises = {k: v[1] for k, v in keys.items()}
    assert len({frozenset(v) for v in plans.values()}) == 1
    assert len({tuple(v) for v in first_crises.values()}) == 1      # early crises cannot depend on the policy


def test_uses_the_operation_dispatcher_by_import():
    """No copy of the dispatcher: the model imports app.services.dispatcher and calls its functions."""
    tree = ast.parse((SIM / "sirag" / "model.py").read_text(encoding="utf-8"))
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "app.services" in imports and M.dsp is dsp
    src = (SIM / "sirag" / "model.py").read_text(encoding="utf-8")
    # the same functions the operation's worker calls (queue -> operations.dispatch_requests / options_for)
    assert "dsp.earliest_options(" in src and "dsp.order_queue(" in src and "dsp.apply_holds(" in src
    for own in ("def rank_candidates", "def trip_minutes", "def earliest_options", "def arrival_times", "def probe",
                "def apply_holds"):
        assert own not in src


def test_no_overlaps_in_simulated_assignments():
    w = load_world()
    reqs = M.Model(w, M.Params("risk_plus_live_traffic", "contingency_east_roadblocks", 1)).run()
    by_cg = {}
    for r in reqs:
        if r.assigned:
            by_cg.setdefault(r.assigned["caregiver_id"], []).append((r.assigned["planned_start"], r.assigned["planned_end"]))
    for windows in by_cg.values():
        windows.sort()
        assert all(a[1] <= b[0] for a, b in zip(windows, windows[1:]))


def test_simulation_has_no_database_access():
    """It reads CSV files only: no database driver is imported anywhere in simulation/."""
    for py in [*(SIM / "sirag").rglob("*.py"), *(SIM / "experiments").rglob("*.py")]:
        text = py.read_text(encoding="utf-8")
        assert "sqlalchemy" not in text and "psycopg" not in text, py


def test_human_dispatcher_delay_and_late_tolerance():
    w = load_world()
    m = M.Model(w, M.Params("human_dispatcher", "normal", 0))
    reqs = m.run()
    delays = [(r.ready_at - r.created).total_seconds() / 60 for r in reqs]
    assert min(delays) >= 5 and max(delays) <= 20
    late = [(r.assigned["arrival"] - r.requested).total_seconds() / 60 for r in reqs if r.kind == "plan" and r.assigned]
    assert max(late) <= M.PLAN_LATE_TOLERANCE == 60


def test_timeout_caps_the_approval_wait_of_urgent_requests_only():
    w = load_world()
    slow = (5.0, 15.0)
    reqs = M.Model(w, M.Params("vela_timeout", "normal", 2, approval_delay=slow)).run()
    crises = [r for r in reqs if r.kind == "crisis"]
    planned_high = [r for r in reqs if r.kind == "plan" and r.priority == "high"]
    assert crises and all((r.ready_at - r.created).total_seconds() / 60 <= 3 for r in crises)
    # scheduled high-priority visits (released 2 h ahead) are not urgent: they keep the human approval wait
    assert all((r.ready_at - r.created).total_seconds() / 60 >= 5 for r in planned_high)


def test_extra_staff_adds_the_hires():
    w = load_world()
    m = M.Model(w, M.Params("risk_plus_live_traffic", "normal", 0, extra_staff="requested"))
    new = [c.caregiver_id for pool in m.caregivers.values() for c in pool if c.caregiver_id.startswith("NEW-")]
    n24 = sum(1 for s in w.schedule.values() if s == "24h")
    assert len(new) == n24 + 1 and "NEW-D-INS-A" in new


def test_targeted_hiring_is_used():
    w = load_world()
    reqs = M.Model(w, M.Params("risk_plus_live_traffic", "normal", 0, extra_staff="targeted")).run()
    assert any(r.assigned and r.assigned["caregiver_id"].startswith("NEW-D-") for r in reqs)


def test_reserved_window_is_not_taken_by_others():
    """While a high-priority request waits for approval its proposed window is reserved (dispatcher.apply_holds)."""
    from datetime import datetime, time, timedelta
    start = datetime(2026, 11, 10, 10, 0, tzinfo=dsp.MEXICO_CITY)
    cg = dsp.Caregiver("C1", frozenset({"nursing"}), time(8), time(16), 19.4, -99.1)
    hold = dsp.Hold("HIGH-1", "C1", start - timedelta(minutes=20), start + timedelta(minutes=30), start)
    low = dsp.Request("LOW-1", "low", "nursing", start, 30, 19.41, -99.11, start - timedelta(hours=2))
    traffic = load_world().traffic
    now = start - timedelta(hours=1)
    assert dsp.rank_candidates(low, dsp.apply_holds([cg], [hold], now), traffic) == []          # reserved
    assert dsp.rank_candidates(low, dsp.apply_holds([cg], [hold], start + timedelta(minutes=1)), traffic)  # expired
    own = dsp.Request("HIGH-1", "high", "nursing", start, 30, 19.41, -99.11, start - timedelta(hours=2))
    assert dsp.rank_candidates(own, dsp.apply_holds([cg], [hold], now, except_request="HIGH-1"), traffic)  # its own
