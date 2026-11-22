"""Inputs of SIRAG-D, read from files only (seed CSVs, reference CSVs, config/simulation.yaml).

There is no database access here on purpose: the simulation can never modify the operation database.
Everything is loaded once and shared (read-only) by every replication.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from app.services import dispatcher as dsp   # the SAME dispatcher the operation uses

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "database" / "seed"
REF = ROOT / "data" / "reference"
CHRONIC = ("diabetes", "hypertension", "high_cholesterol", "heart_disease", "stroke", "kidney_disease",
           "arthritis", "chronic_lung_disease", "cancer")
REFERENCE_DAY = date(2026, 11, 21)             # age is computed at this date (seed generation week)


def _rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _bool(v: str) -> bool:
    return v.strip().lower() in ("true", "t", "1")


@lru_cache
def config() -> dict:
    return yaml.safe_load((ROOT / "config" / "simulation.yaml").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Patient:
    patient_id: str
    institution_id: str
    district_id: str
    lat: float
    lon: float
    station_id: str                     # nearest air-quality station
    risk: float                         # product of YAML risk multipliers (dispatcher.patient_risk)
    pollution_coef: float               # relative increase per +10 ug/m3 PM2.5 (YAML pollution_effects)
    base_priority: str


@dataclass(frozen=True)
class CarePlan:
    care_plan_id: str
    patient_id: str
    institution_id: str
    service_id: str
    times_per_week: float


@dataclass(frozen=True)
class World:
    patients: list[Patient]
    plans: list[CarePlan]
    caregivers: dict[str, list[dsp.Caregiver]]          # by institution
    caregiver_district: dict[str, str]
    shift_minutes_per_day: dict[str, float]
    schedule: dict[str, str]                             # institution -> "day" | "24h"
    institution_district: dict[str, str]
    service_skill: dict[str, str]
    duration: dict[tuple[str, str], int]                 # (institution, service) -> minutes
    traffic: dsp.TrafficProfile
    pm25: dict[str, dict[datetime, float]]               # station -> hour -> ug/m3 (calibrated series)
    pm25_baseline: dict[str, float]                      # station -> 30-day mean
    station_district: dict[str, str]
    district_centroid: dict[str, tuple[float, float]]


def nearest(points: dict[str, tuple[float, float]], lat: float, lon: float) -> str:
    return min(points, key=lambda k: dsp.haversine_km(lat, lon, *points[k]))


@lru_cache
def load_world() -> World:
    cfg = config()
    mult = cfg["health_markov"]["risk_multipliers"]
    eff = cfg["health_markov"]["pollution_effects"]

    stations = {r["station_id"]: (float(r["lat"]), float(r["lon"])) for r in _rows(REF / "air_quality_stations.csv")}
    station_district = {r["station_id"]: r["district_id"] for r in _rows(REF / "air_quality_stations.csv")}
    districts = {r["district_id"]: (float(r["lat"]), float(r["lon"])) for r in _rows(SEED / "districts.csv")}

    persons = {r["person_id"]: r for r in _rows(SEED / "persons.csv")}
    patients = []
    for p in _rows(SEED / "patients.csv"):
        if not _bool(p["active"]):
            continue
        q = persons[p["person_id"]]
        b = {k: _bool(q[k]) for k in CHRONIC}
        age = (REFERENCE_DAY - date.fromisoformat(q["birth_date"])).days / 365.25
        flags = {"chronic_lung_disease": b["chronic_lung_disease"], "heart_disease": b["heart_disease"],
                 "stroke": b["stroke"], "diabetes": b["diabetes"],
                 "dependency_severe": q["dependency_level"] == "severe",
                 "dependency_moderate": q["dependency_level"] == "moderate",
                 "age_80_plus": age >= 80, "no_chronic_disease": not any(b.values())}
        # Pollution: respiratory coefficient for lung disease, cardiovascular for heart/stroke,
        # natural causes for everyone else (YAML apply_* lists). ASSUMPTION: applied to an hourly risk.
        if any(b[k] for k in eff["apply_respiratory_to"]):
            coef = eff["respiratory"]
        elif any(b[k] for k in eff["apply_cardiovascular_to"]):
            coef = eff["cardiovascular"]
        else:
            coef = eff["natural_causes"]
        lat, lon = float(q["lat"]), float(q["lon"])
        patients.append(Patient(p["patient_id"], p["institution_id"], q["district_id"], lat, lon,
                                nearest(stations, lat, lon), dsp.patient_risk(flags, mult), coef,
                                p["base_priority"]))

    active_ids = {p.patient_id for p in patients}
    plans = [CarePlan(r["care_plan_id"], r["patient_id"], r["institution_id"], r["service_id"], float(r["times_per_week"]))
             for r in _rows(SEED / "care_plans.csv") if _bool(r["active"]) and r["patient_id"] in active_ids]

    skills: dict[str, set] = {}
    for r in _rows(SEED / "caregiver_skills.csv"):
        skills.setdefault(r["caregiver_id"], set()).add(r["skill"])
    caregivers: dict[str, list[dsp.Caregiver]] = {}
    cg_district, shift_min = {}, {}
    for r in _rows(SEED / "caregivers.csv"):
        if not _bool(r["active"]):
            continue
        start, end = time.fromisoformat(r["shift_start"]), time.fromisoformat(r["shift_end"])
        cg = dsp.Caregiver(r["caregiver_id"], frozenset(skills.get(r["caregiver_id"], ())), start, end,
                           float(r["base_lat"]), float(r["base_lon"]))
        caregivers.setdefault(r["institution_id"], []).append(cg)
        # ASSUMPTION: the base is in the district whose centroid is closest
        cg_district[r["caregiver_id"]] = nearest(districts, cg.lat, cg.lon)
        minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
        shift_min[r["caregiver_id"]] = minutes if minutes > 0 else minutes + 24 * 60

    traffic = dsp.TrafficProfile({(r["day_type"], int(r["hour"])): float(r["avg_speed_kmh"])
                                  for r in _rows(REF / "traffic_hourly_profile.csv")})
    pm25: dict[str, dict[datetime, float]] = {}
    for r in _rows(REF / "air_quality_hourly.csv"):
        if r["pm25_ugm3"]:
            stamp = r["measured_at"]
            t = datetime.fromisoformat(stamp + ":00" if stamp[-3] in "+-" else stamp)   # "...-06" -> "...-06:00"
            pm25.setdefault(r["station_id"], {})[t] = float(r["pm25_ugm3"])
    baseline = {s: float(np.mean(list(v.values()))) for s, v in pm25.items()}

    return World(
        patients=patients, plans=plans, caregivers=caregivers, caregiver_district=cg_district,
        shift_minutes_per_day=shift_min,
        schedule={r["institution_id"]: r["schedule"] for r in _rows(SEED / "institutions.csv")},
        institution_district={r["institution_id"]: r["district_id"] for r in _rows(SEED / "institutions.csv")},
        service_skill={r["service_id"]: r["required_skill"] for r in _rows(SEED / "services.csv")},
        duration={(r["institution_id"], r["service_id"]): int(r["duration_min"])
                  for r in _rows(SEED / "institution_services.csv")},
        traffic=traffic, pm25=pm25, pm25_baseline=baseline, station_district=station_district,
        district_centroid=districts)


def road_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Road distance as the dispatcher estimates it (straight line x circuity factor)."""
    return dsp.haversine_km(lat1, lon1, lat2, lon2) * dsp.ROAD_CIRCUITY


def ceil_to(t: datetime, minutes: int) -> datetime:
    """Round up to the next multiple of `minutes` (dispatch grid)."""
    m = math.ceil((t.hour * 60 + t.minute + t.second / 60) / minutes) * minutes
    return t.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=m)
