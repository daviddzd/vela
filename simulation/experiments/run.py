"""SIRAG-D experiment. Run:   docker compose run --rm sim
(or:  docker compose run --rm sim python -m simulation.experiments.run --reps 30 --sens-reps 10)

Main:         5 policies x 3 scenarios x 30 replications of 7 days, seed 2026, common random numbers
              (the 4 of docs/spec/06 + "vela_timeout": Vela with time-limited approval of urgent requests).
Sensitivity:  (clearly separated, NOT main results) on the "normal" scenario:
              approval delay 0 / 1-5 / 5-15 min, crisis risk x1 / x2 / x3 (stress_test knob), and
              "¿y si contratamos?": +1 night nurse per 24 h institution and +1 day caregiver in INS-A; and
              "Cumplir jornada nocturna": each 12-h night shift split into two legal 7-h shifts (night staff x2).
Labor rules (LFT arts. 60, 61, 69; backend/app/services/labor.py) apply to EVERY run: weekly rest day and legal
shifts. Only the validation against the seed history uses the seed staffing (7 days a week, as it happened).
Outputs in simulation/results/: summary.csv, window.csv, tests.csv, validation.csv, sensitivity.csv,
run_info.json; one row per replication in results/raw/ (git-ignored).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from dataclasses import asdict
from datetime import datetime
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from simulation.sirag import stats as st
from simulation.sirag.data import ROOT, config
from simulation.sirag.model import Params
from simulation.sirag.runner import run_one

RESULTS = ROOT / "simulation" / "results"
SCENARIOS = ["normal", "contingency_east", "contingency_east_roadblocks"]
MAIN_METRICS = ["high_wait_mean_min", "high_wait_p90_min", "crisis_under_60_pct", "crisis_response_mean_min",
                "crisis_response_p90_min", "unattended_pct",
                "travel_km", "utilization_pct", "overtime_hours", "night_crisis_under_60_pct", "staff"]
WINDOW_METRICS = ["win_at_risk_entries", "win_crises", "win_crisis_under_60_pct", "win_high_wait_mean_min", "win_unattended_pct", "win_requests"]


def _run(p: Params) -> dict:
    out = run_one(p)
    out["approval_delay"] = f"{p.approval_delay[0]:g}-{p.approval_delay[1]:g}"
    out["risk_multiplier"] = p.risk_multiplier
    out["extra_staff"] = p.extra_staff or "current"
    return out


def baseline_unattended() -> dict:
    """Observed in the seed history (database/seed/service_requests.csv), by reason."""
    with open(ROOT / "database" / "seed" / "service_requests.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    no_staff = sum(r["status"] == "unattended" and r["status_reason"] == "no_staff_available" for r in rows)
    cancelled = sum(r["status"] == "cancelled" for r in rows)
    long_ids = ("SRV-03", "SRV-04", "SRV-06", "SRV-07")
    short = [r for r in rows if r["service_id"] not in long_ids and r["status"] != "cancelled"]
    return {"total": len(rows), "no_staff": no_staff, "cancelled": cancelled,
            "pct_all": 100 * no_staff / len(rows), "pct_without_cancelled": 100 * no_staff / (len(rows) - cancelled),
            "pct_short_services": 100 * sum(r["status"] == "unattended" for r in short) / len(short)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=config()["experiments"]["replications"])
    ap.add_argument("--sens-reps", type=int, default=30)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()
    seed = config()["experiments"]["seed"]
    started = time.perf_counter()

    main_jobs = [Params(pol, sc, r, seed) for sc in SCENARIOS for r in range(args.reps) for pol in st.POLICIES]
    sens_jobs = [Params(pol, "normal", r, seed, approval_delay=d) for d in ((0.0, 0.0), (5.0, 15.0))
                 for r in range(args.sens_reps) for pol in st.POLICIES]
    sens_jobs += [Params(pol, "normal", r, seed, risk_multiplier=k) for k in (2.0, 3.0)
                  for r in range(args.sens_reps) for pol in st.POLICIES]
    sens_jobs += [Params(pol, "normal", r, seed, extra_staff=k) for k in ("requested", "targeted", "night_legal")
                  for r in range(args.sens_reps) for pol in st.POLICIES]
    # Validation against the seed history: the staff as in the seed (7 days, seed shifts), human dispatcher
    valid_jobs = [Params("human_dispatcher", "normal", r, seed, labor_rules=False) for r in range(args.reps)]
    with Pool(args.workers) as pool:
        main_rows = pool.map(_run, main_jobs, chunksize=4)
        sens_rows = pool.map(_run, sens_jobs, chunksize=4)
        valid_rows = pool.map(_run, valid_jobs, chunksize=4)
    elapsed = time.perf_counter() - started

    runs = pd.DataFrame(main_rows)
    (RESULTS / "raw").mkdir(parents=True, exist_ok=True)
    runs.to_csv(RESULTS / "raw" / "runs.csv", index=False)
    st.summary(runs, MAIN_METRICS + ["at_risk_entries"], ["scenario", "policy"]).to_csv(RESULTS / "summary.csv", index=False)
    # Contingency effect on health, same replications (CRN): totals over all replications
    effect = runs[runs.policy == "human_dispatcher"].groupby("scenario")[["at_risk_entries", "win_at_risk_entries",
                                                                           "crises", "win_crises"]].sum()
    effect.to_csv(RESULTS / "contingency_effect.csv")
    st.summary(runs, WINDOW_METRICS, ["scenario", "policy"]).to_csv(RESULTS / "window.csv", index=False)
    st.compare(runs, [m for m in MAIN_METRICS if m != "staff"] + ["win_crisis_under_60_pct", "win_high_wait_mean_min"]).to_csv(
        RESULTS / "tests.csv", index=False)

    # Sensitivity: the main 1-5 min / x1 runs of the normal scenario are the middle level of each knob.
    base = runs[(runs.scenario == "normal") & (runs.replication < args.sens_reps)]
    sens = pd.concat([pd.DataFrame(sens_rows), base], ignore_index=True)
    sens["extra_staff"] = sens["extra_staff"].fillna("current")
    plain = (sens.approval_delay == "1-5") & (sens.extra_staff == "current")
    s1 = st.summary(sens[(sens.risk_multiplier == 1.0) & (sens.extra_staff == "current")], MAIN_METRICS,
                    ["approval_delay", "policy"]).assign(knob="approval_delay")
    s2 = st.summary(sens[plain], MAIN_METRICS, ["risk_multiplier", "policy"]).assign(knob="risk_multiplier")
    s3 = st.summary(sens[(sens.approval_delay == "1-5") & (sens.risk_multiplier == 1.0)], MAIN_METRICS,
                    ["extra_staff", "policy"]).assign(knob="extra_staff")
    pd.concat([s1, s2, s3], ignore_index=True).to_csv(RESULTS / "sensitivity.csv", index=False)
    sens.to_csv(RESULTS / "raw" / "sensitivity_runs.csv", index=False)
    # Paired tests inside each sensitivity level (same method as the main results)
    key = ["high_wait_p90_min", "crisis_response_p90_min", "crisis_under_60_pct", "unattended_pct"]
    tests = []
    for knob, col, levels in (("approval_delay", "approval_delay", ["0-0", "1-5", "5-15"]),
                              ("extra_staff", "extra_staff", ["current", "requested", "targeted", "night_legal"])):
        for level in levels:
            sub = sens[(sens[col] == level) & (sens.risk_multiplier == 1.0)
                       & ((sens.extra_staff == "current") if knob == "approval_delay" else (sens.approval_delay == "1-5"))]
            tests.append(st.compare(sub, key).assign(knob=knob, level=level))
    pd.concat(tests, ignore_index=True).to_csv(RESULTS / "sensitivity_tests.csv", index=False)

    obs = baseline_unattended()
    sim = pd.DataFrame(valid_rows)          # seed staffing (7 days): the seed history had no rest day
    mean, lo, hi, n = st.ci95(sim["unattended_pct"])
    smean, slo, shi, _ = st.ci95(sim["unattended_short_pct"])
    pd.DataFrame([{**obs, "sim_mean": mean, "sim_ci_low": lo, "sim_ci_high": hi, "sim_n": n,
                   "sim_short_mean": smean, "sim_short_ci_low": slo, "sim_short_ci_high": shi}]).to_csv(
        RESULTS / "validation.csv", index=False)

    info = {"finished_at": datetime.now().isoformat(timespec="seconds"), "elapsed_seconds": round(elapsed, 1),
            "workers": args.workers, "replications": args.reps, "sensitivity_replications": args.sens_reps,
            "runs_main": len(main_jobs), "runs_sensitivity": len(sens_jobs), "runs_validation": len(valid_jobs),
            "days": 7, "seed": seed,
            "labor_rules": "rest day (LFT art. 69) + legal shifts (arts. 60-61) in every experiment; "
                           "validation uses the seed staffing (7 days)",
            "params_example": asdict(main_jobs[0]),
            "approval": config()["approval"], "late_tolerance_minutes": config()["dispatch"]["late_tolerance_minutes"]}
    (RESULTS / "run_info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Listo: {len(main_jobs)} corridas principales + {len(sens_jobs)} de sensibilidad en {elapsed:.0f} s "
          f"con {args.workers} procesos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
