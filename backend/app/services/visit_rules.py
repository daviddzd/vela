"""When a care-plan visit happens. Pure functions (no database): used by the operation's worker
(app/services/care_plans.py) AND by the SIRAG-D simulation, so both create visits the same way.

Rules taken from the seed generator (data/generator/legacy_es/generar_base.py, hora_deseada):
  - long shifts start when the shift starts: 8 h services at 08:00, 12 h services at 20:00
  - every other visit: a 15-min slot between 08:00 and 18:00
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MEXICO_CITY = ZoneInfo("America/Mexico_City")
VISIT_HOURS = (8, 18)
SLOT_MINUTES = 15
LONG_SERVICE_START = {"SRV-03": 8, "SRV-06": 8, "SRV-04": 20, "SRV-07": 20}


def visit_time(day: date, service_id: str, draw: float) -> datetime:
    """Start of the visit on `day`; `draw` in [0, 1) picks the slot for ordinary visits."""
    if service_id in LONG_SERVICE_START:
        return datetime.combine(day, time(LONG_SERVICE_START[service_id]), MEXICO_CITY)
    lo, hi = VISIT_HOURS
    slot = int(draw * (hi - lo) * 60 // SLOT_MINUTES)
    return datetime.combine(day, time(lo), MEXICO_CITY) + timedelta(minutes=slot * SLOT_MINUTES)
