"""Calibrated synthetic air-quality model, the SAME one as data/generator/build_reference_data.py, so the worker
can produce "now" readings every hour (source = 'synthetic_calibrated').

Per hour and station:
  O3    = city daily max   x photochemical shape (peak ~15 h)             x station o3_factor   x lognormal(0, 0.08)
  PM2.5 = city daily mean  x shape (morning peak ~9 h + evening bump ~21 h) x station pm25_factor x lognormal(0, 0.15)
  city daily drivers: O3 max ~ N(86, 10) clipped 62-120 ppb; PM2.5 mean ~ N(22, 5.5) clipped 11-36 ug/m3
  (calibrated with SIMAT / SSA weekly reports, see docs/spec/09_datos.md).
The model has no day-of-week effect (neither does the original). Every draw is seeded with (2026, date, hour,
station), so the same hour always gives the same value: re-running the worker never changes history.
"""
from __future__ import annotations

import math
import random
from datetime import date, datetime

SEED = 2026


def city_drivers(day: date) -> tuple[float, float]:
    rnd = random.Random(f"{SEED}|city|{day.isoformat()}")
    o3_max = min(max(rnd.gauss(86, 10), 62), 120)
    pm_mean = min(max(rnd.gauss(22, 5.5), 11), 36)
    return o3_max, pm_mean


def reading(station_id: str, o3_factor: float, pm25_factor: float, hour: datetime) -> tuple[float, float]:
    """(O3 ppb, PM2.5 ug/m3) for one station at one local hour."""
    o3_max, pm_mean = city_drivers(hour.date())
    h = hour.hour
    shape_o3 = 0.15 + 0.85 * math.exp(-((h - 15) ** 2) / (2 * 2.6 ** 2))
    shape_pm = 0.75 + 0.55 * math.exp(-((h - 9) ** 2) / (2 * 2.2 ** 2)) + 0.2 * math.exp(-((h - 21) ** 2) / (2 * 2.5 ** 2))
    rnd = random.Random(f"{SEED}|{station_id}|{hour.isoformat()}")
    o3 = o3_max * shape_o3 * o3_factor * rnd.lognormvariate(0, 0.08)
    pm = pm_mean * shape_pm * pm25_factor * rnd.lognormvariate(0, 0.15)
    return round(o3, 1), round(pm, 1)
