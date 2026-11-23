"""Metrics of one replication (docs/spec/06 + config/simulation.yaml)."""
from __future__ import annotations

from datetime import timedelta

import numpy as np

from app.services import labor
from app.services.dispatcher import MEXICO_CITY
from simulation.sirag.model import START, Model

LONG_SERVICES = ("SRV-03", "SRV-04", "SRV-06", "SRV-07")
AFFECTED = {"09005", "09006", "09007", "09011", "09017"}   # districts of stations with their own PM2.5 target


def summarize(model: Model, requests) -> dict:
    w, prm = model.world, model.params
    total = len(requests)
    short = [r for r in requests if r.service_id not in LONG_SERVICES]
    attended = [r for r in requests if not r.unattended]
    high = [r for r in attended if r.priority == "high"]
    waits = np.array([(r.assigned["arrival"] - r.requested).total_seconds() / 60 for r in high]) if high else np.array([])
    crises = [r for r in requests if r.kind == "crisis"]
    crisis_ok = [r for r in crises if not r.unattended
                 and (r.assigned["arrival"] - r.requested).total_seconds() / 60 <= 60]
    cresp = [(r.assigned["arrival"] - r.requested).total_seconds() / 60 for r in crises if not r.unattended]
    work_min = sum(r.assigned["work_min"] for r in attended)          # both people of a relay
    # Available time = shift minutes on the days each person WORKS (their weekly rest day excluded, LFT art. 69),
    # for everyone the model staffed (including hired staff in the sensitivity scenarios).
    sim_days = [(START + timedelta(days=d)).date() for d in range(prm.days)]
    shift_min = sum(labor.hours(c.shift_start, c.shift_end) * 60 * sum(labor.works_on(c.rest_day, d) for d in sim_days)
                    for pool in model.caregivers.values() for c in pool)
    # Crises that start at night (20:00-06:00, art. 60), for the "Cumplir jornada nocturna" sensitivity
    night_crises = [r for r in crises if r.requested.astimezone(MEXICO_CITY).hour >= 20
                    or r.requested.astimezone(MEXICO_CITY).hour < 6]

    out = {
        "policy": prm.policy, "scenario": prm.scenario, "replication": prm.replication,
        "requests": total, "crises": len(crises),
        "high_wait_mean_min": float(waits.mean()) if waits.size else np.nan,
        "high_wait_p90_min": float(np.percentile(waits, 90)) if waits.size else np.nan,
        "crisis_under_60_pct": 100 * len(crisis_ok) / len(crises) if crises else np.nan,
        "crisis_response_mean_min": float(np.mean(cresp)) if cresp else np.nan,
        "crisis_response_p90_min": float(np.percentile(cresp, 90)) if cresp else np.nan,
        "unattended_pct": 100 * sum(r.unattended for r in requests) / total if total else np.nan,
        **{f"{prio}_wait_p90_min": _p90([(r.assigned["arrival"] - r.requested).total_seconds() / 60
                                         for r in attended if r.priority == prio]) for prio in ("medium", "low")},
        "travel_km": sum(r.assigned["km"] for r in attended),
        "utilization_pct": 100 * work_min / shift_min,
        "night_crises": len(night_crises),
        "night_crisis_under_60_pct": 100 * sum(1 for r in night_crises if not r.unattended and
                                               (r.assigned["arrival"] - r.requested).total_seconds() / 60 <= 60)
                                     / len(night_crises) if night_crises else np.nan,
        "staff": sum(len(pool) for pool in model.caregivers.values()),
        "relays": sum(1 for r in attended if r.assigned.get("relay")),
        "overtime_hours": sum(r.assigned["overtime_min"] for r in attended) / 60,
        # for the validation: without the 8 h / 12 h shift services (see docs/dev/sirag_d_modelo.md)
        "unattended_short_pct": 100 * sum(r.unattended for r in short) / len(short) if short else np.nan,
        "at_risk_entries": model.at_risk_entries,
    }
    # The contingency where it happens: only inside the 24 h window and the affected districts.
    # Computed for every scenario (in "normal" it is the same window with ordinary air) for comparison.
    lo, hi = model.window
    inside = [r for r in requests if lo <= r.requested < hi and r.district_id in AFFECTED]
    in_crises = [r for r in inside if r.kind == "crisis"]
    in_high = [r for r in inside if r.priority == "high" and not r.unattended]
    in_waits = [(r.assigned["arrival"] - r.requested).total_seconds() / 60 for r in in_high]
    out.update({
        "win_requests": len(inside), "win_crises": len(in_crises), "win_at_risk_entries": model.at_risk_entries_window,
        "win_crisis_under_60_pct": 100 * sum(1 for r in in_crises if not r.unattended and
                                             (r.assigned["arrival"] - r.requested).total_seconds() / 60 <= 60)
                                   / len(in_crises) if in_crises else np.nan,
        "win_high_wait_mean_min": float(np.mean(in_waits)) if in_waits else np.nan,
        "win_unattended_pct": 100 * sum(r.unattended for r in inside) / len(inside) if inside else np.nan,
    })
    return out


def _p90(values: list[float]) -> float:
    return float(np.percentile(values, 90)) if values else np.nan
