"""Panorama-AM (MIS/DSS): data for the Operation and Panorama views (docs/spec/07_panorama_am.md).

Everything goes through the tenant-scoped session (RLS). Population data come ONLY from the
aggregated, anonymous views of migration 0002 (no names, no ids). Reference files (prevalence
reference, district boundaries) are read from data/reference, mounted read-only.

Filters: `district` (alcaldía) and date range; `institution` only for the owner (a coordinator is
already limited to their institution by RLS, so the parameter is ignored for them).
"""
from __future__ import annotations

import csv
import json
import os
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.roles import COORDINATOR, OWNER
from app.routers.board import ON_BOARD          # same "En visita" rule as the live board
from app.services import dispatcher as dsp
from app.services import operations as ops

router = APIRouter(prefix="/api/panorama", tags=["panorama"])
VIEWERS = require_role(COORDINATOR, OWNER)
ON_TIME_MINUTES = 15          # ASSUMPTION: "puntual" = arrived at most 15 min after the scheduled time
TZ = "America/Mexico_City"


def reference_dir() -> Path:
    return Path(os.environ.get("REFERENCE_DIR", Path(__file__).resolve().parents[3] / "data" / "reference"))


def default_range(start: date | None, end: date | None, days: int = 30) -> tuple[date, date]:
    end = end or ops.now().date()
    return start or end - timedelta(days=days - 1), end


def institution_scope(user: CurrentUser, institution: str | None) -> str | None:
    """Only the owner may narrow to one institution; for everyone else RLS already decides."""
    return institution if user.role == OWNER and institution else None


# ---- Operation view -----------------------------------------------------------------------------

@router.get("/operation")
def operation(user: CurrentUser = Depends(VIEWERS), db: Session = Depends(tenant_db),
              start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
              district: str | None = None, institution: str | None = None) -> dict:
    start, end = default_range(start, end)
    params = {"from": start, "to": end, "district": district, "inst": institution_scope(user, institution),
              "ontime": ON_TIME_MINUTES}
    filters = """AND (CAST(:inst AS text) IS NULL OR r.institution_id = :inst)
                 AND (CAST(:district AS text) IS NULL OR pe.district_id = :district)"""
    base = f"""FROM service_requests r
               JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
               LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active' AND a.leg = 1
               WHERE (r.scheduled_for AT TIME ZONE '{TZ}')::date BETWEEN :from AND :to {filters}"""

    # Daily punctuality and unattended share. Denominator for "sin atender": requests whose outcome is
    # known (closed, completed or unattended); cancelled/rejected/pending ones are not counted.
    daily = db.execute(text(f"""
        SELECT (r.scheduled_for AT TIME ZONE '{TZ}')::date AS day, r.is_baseline,
               count(*) FILTER (WHERE r.status IN ('closed','completed','unattended'))      AS decided,
               count(*) FILTER (WHERE r.status = 'unattended')                             AS unattended,
               count(*) FILTER (WHERE a.arrived_at IS NOT NULL)                            AS arrived,
               count(*) FILTER (WHERE a.arrived_at <= r.scheduled_for + :ontime * interval '1 minute') AS on_time
        {base} GROUP BY 1, 2 ORDER BY 1, 2"""), params).mappings().all()

    def pct(a: int, b: int) -> float | None:
        return round(100 * a / b, 1) if b else None

    def summary(rows) -> dict:
        t = {k: sum(d[k] for d in rows) for k in ("decided", "unattended", "arrived", "on_time")}
        return {**t, "on_time_pct": pct(t["on_time"], t["arrived"]), "unattended_pct": pct(t["unattended"], t["decided"])}

    # "baseline" = seed history before Vela (is_baseline); "vela" = everything the running system created.
    periods = {"baseline": summary([d for d in daily if d["is_baseline"]]),
               "vela": summary([d for d in daily if not d["is_baseline"]])}
    totals = summary(daily)
    series = [{"day": d["day"].isoformat(), "period": "baseline" if d["is_baseline"] else "vela",
               "on_time_pct": pct(d["on_time"], d["arrived"]), "unattended_pct": pct(d["unattended"], d["decided"]),
               "visits": d["arrived"]} for d in daily]

    load = staff_load(db, params, filters)

    queue = db.execute(text(f"""
        SELECT r.priority, count(*) AS waiting,
               max(round(extract(epoch FROM now() - r.created_at) / 60))::int AS max_wait_min
        FROM service_requests r
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        WHERE r.status = 'queued' {filters}
        GROUP BY 1"""), params).mappings().all()
    by_priority = {q["priority"]: dict(q) for q in queue}

    counters = db.execute(text(f"""
        SELECT count(*) FILTER (WHERE r.status = 'queued')                                AS queued,
               count(*) FILTER (WHERE r.status = 'assigned' AND a.planned_start <= now()) AS on_the_way,
               count(*) FILTER (WHERE r.status = 'in_progress' AND {ON_BOARD})      AS in_visit,
               count(*) FILTER (WHERE r.status IN ('completed','closed')
                                AND (a.finished_at AT TIME ZONE '{TZ}')::date = (now() AT TIME ZONE '{TZ}')::date) AS done_today
        FROM service_requests r
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active' AND a.leg = 1
        WHERE r.scheduled_for > now() - interval '2 days' {filters}"""), params).mappings().one()

    return {"from": start.isoformat(), "to": end.isoformat(), "on_time_minutes": ON_TIME_MINUTES,
            "counters": dict(counters),
            "on_time_pct": totals["on_time_pct"], "unattended_pct": totals["unattended_pct"],
            "totals": totals, "periods": periods, "daily": series, "staff_load": load,
            "queue_by_priority": [by_priority.get(p, {"priority": p, "waiting": 0, "max_wait_min": None})
                                  for p in ("high", "medium", "low")]}


def staff_load(db: Session, params: dict, filters: str) -> list[dict]:
    """Working hours per caregiver = time at the visit + estimated travel to it.

    Travel uses the SAME function as the dispatcher (dispatcher.trip_minutes: straight-line distance
    from the caregiver's base × 1.4 ÷ speed of that hour from traffic_hourly_profile).
      - today: the planned window of each active assignment (it already is travel + visit)
      - history: real time on site (finished − arrived) + estimated travel, averaged per worked day
    """
    traffic = ops.load_traffic(db)
    caregivers = db.execute(text("""
        SELECT caregiver_id, first_name || ' ' || paternal_surname AS name, type, institution_id,
               round((extract(epoch FROM (shift_end - shift_start)) / 3600 + 24)::numeric % 24, 1)::float AS shift_hours
        FROM caregivers WHERE active AND (CAST(:inst AS text) IS NULL OR institution_id = :inst)
        ORDER BY caregiver_id"""), params).mappings().all()
    today = dict(db.execute(text(f"""
        SELECT a.caregiver_id, sum(extract(epoch FROM a.planned_end - a.planned_start)) / 3600
        FROM assignments a JOIN service_requests r USING (request_id)
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        WHERE a.status = 'active' AND a.planned_start IS NOT NULL
          AND (r.scheduled_for AT TIME ZONE '{TZ}')::date = (now() AT TIME ZONE '{TZ}')::date {filters}
        GROUP BY 1"""), params).all())
    visits = db.execute(text(f"""
        SELECT a.caregiver_id, a.arrived_at, extract(epoch FROM a.finished_at - a.arrived_at) / 60 AS on_site_min,
               c.base_lat::float AS clat, c.base_lon::float AS clon, pe.lat::float AS plat, pe.lon::float AS plon
        FROM assignments a JOIN service_requests r USING (request_id) JOIN caregivers c USING (caregiver_id)
        JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        WHERE a.finished_at IS NOT NULL AND (r.scheduled_for AT TIME ZONE '{TZ}')::date BETWEEN :from AND :to
          {filters}"""), params).mappings().all()
    minutes: dict[str, float] = {}
    days: dict[str, set] = {}
    for v in visits:
        km = dsp.haversine_km(v["clat"], v["clon"], v["plat"], v["plon"])
        travel = dsp.trip_minutes(km, v["arrived_at"], traffic)
        minutes[v["caregiver_id"]] = minutes.get(v["caregiver_id"], 0) + float(v["on_site_min"]) + travel
        days.setdefault(v["caregiver_id"], set()).add(v["arrived_at"].astimezone(dsp.MEXICO_CITY).date())
    return [{**dict(c), "hours_today": round(float(today.get(c["caregiver_id"], 0)), 1),
             "avg_hours_per_day": round(minutes.get(c["caregiver_id"], 0) / 60 / len(days[c["caregiver_id"]]), 1)
             if c["caregiver_id"] in days else 0.0} for c in caregivers]


@router.get("/institutions")
def institutions(user: CurrentUser = Depends(VIEWERS), db: Session = Depends(tenant_db)) -> list[dict]:
    """Institution filter options (the owner sees all; a coordinator only their own)."""
    rows = db.execute(text("SELECT institution_id, name FROM institutions ORDER BY institution_id")).mappings().all()
    return [dict(r) for r in rows]


# ---- Panorama view ------------------------------------------------------------------------------

@lru_cache
def prevalence_reference() -> dict[str, dict]:
    with open(reference_dir() / "prevalence_reference.csv", encoding="utf-8") as f:
        return {r["condition"]: {**r, "reference_pct": float(r["reference_pct"]), "adjusted": r["adjusted"] == "true"}
                for r in csv.DictReader(f)}


@router.get("/population")
def population(user: CurrentUser = Depends(VIEWERS), db: Session = Depends(tenant_db),
               district: str | None = None) -> dict:
    """Synthetic 60+ population, aggregated per district (anonymous views, small cells hidden)."""
    districts = db.execute(text("SELECT * FROM v_district_population ORDER BY district_id")).mappings().all()
    city = db.execute(text("""
        SELECT sum(persons_60_plus)::int AS persons,
               round(sum(multimorbidity_pct * persons_60_plus) / sum(persons_60_plus), 1)::float AS multimorbidity_pct,
               round(sum(dependency_moderate_severe_pct * persons_60_plus) / sum(persons_60_plus), 1)::float
                 AS dependency_moderate_severe_pct,
               round(sum(pollution_sensitive_pct * persons_60_plus) / sum(persons_60_plus), 1)::float AS pollution_sensitive_pct,
               round(sum(multimorbidity_broad_pct * persons_60_plus) / sum(persons_60_plus), 1)::float AS multimorbidity_broad_pct
        FROM v_district_population""")).mappings().one()
    ref = prevalence_reference()
    conditions = [{**dict(c), "prevalence_pct": float(c["prevalence_pct"]), "reference": ref.get(c["condition"])}
                  for c in db.execute(text("SELECT * FROM v_population_conditions ORDER BY prevalence_pct DESC"))
                  .mappings().all()]
    rows = [{k: (float(v) if hasattr(v, "is_finite") else v) for k, v in d.items()} for d in districts]
    return {"city": dict(city), "districts": rows, "conditions": conditions,
            "indicator_reference": {"multimorbidity_broad_pct": ref.get("multimorbidity")},
            "selected": next((r for r in rows if r["district_id"] == district), None)}


@lru_cache
def _boundaries() -> dict | None:
    path = reference_dir() / "official" / "district_boundaries.geojson"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    for feature in data["features"]:   # keep only what the map needs
        p = feature["properties"]
        feature["properties"] = {"district_id": p["CVEGEO"], "name": p["NOMGEO"]}
    return data


@router.get("/boundaries")
def boundaries(user: CurrentUser = Depends(VIEWERS), db: Session = Depends(tenant_db)) -> dict:
    """Official district polygons if the file is present; otherwise district centroids (points)."""
    geo = _boundaries()
    if geo is not None:
        return {"available": True, "geojson": geo}
    points = db.execute(text("SELECT district_id, name, lat::float, lon::float FROM districts ORDER BY 1")).mappings().all()
    return {"available": False, "points": [dict(p) for p in points]}


@lru_cache
def contingency_thresholds() -> dict:
    cfg = yaml.safe_load((ops.config_dir() / "simulation.yaml").read_text(encoding="utf-8"))["contingency"]["thresholds"]
    return {"o3_ppb_1h": cfg["o3_phase1_ppb_1h"], "pm25_ugm3_24h": cfg["pm25_phase1_ugm3_24h_avg"],
            "watch_fraction": cfg["watch_fraction"]}


@router.get("/air")
def air(user: CurrentUser = Depends(VIEWERS), db: Session = Depends(tenant_db), station: str | None = None,
        district: str | None = None, start: date | None = Query(None, alias="from"),
        end: date | None = Query(None, alias="to")) -> dict:
    """Hourly O3 and 24 h average PM2.5 for one station, with the contingency thresholds."""
    stations = db.execute(text("""
        SELECT s.station_id, s.name, s.district_id, d.name AS district_name, s.location_source
        FROM air_quality_stations s JOIN districts d USING (district_id) ORDER BY s.station_id""")).mappings().all()
    candidates = [s for s in stations if not district or s["district_id"] == district] or list(stations)
    chosen = station if station in {s["station_id"] for s in stations} else candidates[0]["station_id"]
    last = db.scalar(text(f"SELECT max((measured_at AT TIME ZONE '{TZ}')::date) FROM air_quality_readings"))
    end = end or last
    start = start or end - timedelta(days=6)
    # Live view: calibrated history, with an ACTIVE demo scenario in front (marked so the chart can label it).
    rows = db.execute(text(f"""
        SELECT measured_at, o3_ppb, pm25_24h, scenario FROM (
          SELECT measured_at, o3_ppb::float,
                 round(avg(pm25_ugm3) OVER (ORDER BY measured_at RANGE BETWEEN interval '23 hours' PRECEDING AND CURRENT ROW)::numeric, 1)::float AS pm25_24h,
                 source = 'scenario' AS scenario
          FROM v_air_quality_live WHERE station_id = :s
            AND (measured_at AT TIME ZONE '{TZ}')::date BETWEEN :from - 1 AND :to) x
        WHERE (measured_at AT TIME ZONE '{TZ}')::date BETWEEN :from AND :to
        ORDER BY measured_at"""), {"s": chosen, "from": start, "to": end}).mappings().all()
    return {"station": chosen, "stations": [dict(s) for s in stations], "from": start.isoformat(),
            "to": end.isoformat(), "data_until": last.isoformat() if last else None,
            "thresholds": contingency_thresholds(),
            "series": [{"t": r["measured_at"].isoformat(), "o3": r["o3_ppb"], "pm25_24h": r["pm25_24h"],
                        "scenario": r["scenario"]} for r in rows],
            "max_o3": max((r["o3_ppb"] for r in rows if r["o3_ppb"] is not None), default=None),
            "max_pm25_24h": max((r["pm25_24h"] for r in rows if r["pm25_24h"] is not None), default=None)}


@router.get("/traffic")
def traffic(user: CurrentUser = Depends(VIEWERS), db: Session = Depends(tenant_db)) -> dict:
    rows = db.execute(text("""SELECT day_type, hour, congestion_pct::float, avg_speed_kmh::float
                              FROM traffic_hourly_profile ORDER BY day_type, hour""")).mappings().all()
    peak = max(rows, key=lambda r: r["congestion_pct"])
    return {"cells": [dict(r) for r in rows], "peak": dict(peak)}
