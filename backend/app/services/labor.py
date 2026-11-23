"""Labor rules of the Ley Federal del Trabajo (LFT), shared by the operation and SIRAG-D (team decision 22 Nov 2026).

Source: LFT, texto vigente, última reforma DOF 14-05-2026 (https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf).
  art. 60  Jornada diurna: between 06:00 and 20:00. Nocturna: between 20:00 and 06:00. Mixta: both, as long as the
           night part is LESS than 3.5 h; with 3.5 h or more it counts as nocturna.
  art. 61  Maximum per day: 8 h diurna, 7 h nocturna, 7.5 h mixta (article reformed DOF 01-05-2026).
  art. 69  At least one day of rest for every six days of work.

What Vela does with them:
  * shift type comes from the HOURS (art. 60), not from the label in the data ("mixed" 10:00-18:00 is diurna);
  * diurna / mixta shifts above the maximum are shortened to it (e.g. evening 14:00-22:00, mixta: 14:00-21:30);
  * nocturna shifts above 7 h are NOT changed (the staffing plan is the institution's decision): they are flagged
    "Excede la jornada legal (art. 61)" and coordination gets an alert;
  * every caregiver has one fixed weekly rest day (ISO weekday 1 = Monday ... 7 = Sunday), assigned in rotation so
    that people of the same shift and skill do not rest on the same day. The dispatcher (operation and SIRAG-D)
    never assigns a shift that STARTS on that day.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta

NIGHT_START, NIGHT_END = time(20, 0), time(6, 0)                 # art. 60
MAX_HOURS = {"diurna": 8.0, "mixta": 7.5, "nocturna": 7.0}       # art. 61
MIXTA_NIGHT_LIMIT = 3.5                                          # art. 60: 3.5 h or more of night -> nocturna
WEEKDAYS_ES = {1: "lunes", 2: "martes", 3: "miércoles", 4: "jueves", 5: "viernes", 6: "sábado", 7: "domingo"}


def _span(start: time, end: time) -> tuple[datetime, datetime]:
    s = datetime.combine(date(2026, 1, 5), start)
    e = datetime.combine(date(2026, 1, 5), end)
    if e <= s:
        e += timedelta(days=1)            # crosses midnight
    return s, e


def hours(start: time, end: time) -> float:
    s, e = _span(start, end)
    return (e - s).total_seconds() / 3600


def night_hours(start: time, end: time) -> float:
    """Hours of the shift that fall between 20:00 and 06:00 (art. 60)."""
    s, e = _span(start, end)
    total, t = 0.0, s
    while t < e:
        step = min(e, t + timedelta(minutes=15))
        if t.time() >= NIGHT_START or t.time() < NIGHT_END:
            total += (step - t).total_seconds() / 3600
        t = step
    return total


def shift_type(start: time, end: time) -> str:
    """'diurna' | 'mixta' | 'nocturna' by the hours of the shift (art. 60)."""
    night = night_hours(start, end)
    if night == 0:
        return "diurna"
    return "mixta" if night < MIXTA_NIGHT_LIMIT else "nocturna"


def legal_shift(start: time, end: time) -> dict:
    """The shift Vela uses. Diurna / mixta above the art. 61 maximum are shortened; nocturna is kept and flagged."""
    kind = shift_type(start, end)
    limit = MAX_HOURS[kind]
    new_end = end
    if kind in ("diurna", "mixta") and hours(start, end) > limit:
        new_end = (datetime.combine(date(2026, 1, 5), start) + timedelta(hours=limit)).time()
        kind = shift_type(start, new_end)                         # e.g. stays mixta after shortening
    return {"start": start, "end": new_end, "type": kind, "hours": round(hours(start, new_end), 2),
            "max_hours": MAX_HOURS[kind], "adjusted": new_end != end,
            "exceeds": hours(start, new_end) > MAX_HOURS[kind]}


def works_on(rest_day: int | None, day: date) -> bool:
    """False on the caregiver's weekly rest day (art. 69). The day is the one on which the shift STARTS."""
    return rest_day is None or day.isoweekday() != rest_day


def assign_rest_days(people: list[dict]) -> dict[str, int]:
    """Rotation of rest days. `people`: dicts with caregiver_id, institution_id, shift_start, shift_end, skill
    (the main one). Inside each institution, people of the same shift and skill get different days whenever there are
    7 or fewer of them; ties go to the day on which fewer people of the institution rest. Deterministic."""
    out: dict[str, int] = {}
    for inst in sorted({p["institution_id"] for p in people}):
        staff = sorted((p for p in people if p["institution_id"] == inst),
                       key=lambda p: (str(p["shift_start"]), p["skill"], p["caregiver_id"]))
        taken: list[dict] = []
        for p in staff:
            day = next_rest_day(p, taken)
            out[p["caregiver_id"]] = day
            taken.append({**p, "rest_day": day})
    return out


def _group(p: dict) -> tuple:
    return (str(p["shift_start"]), str(p["shift_end"]), p["skill"])


def next_rest_day(person: dict, others: list[dict]) -> int:
    """Rest day for one more person of an institution, given the others' rest days (dicts with shift_start,
    shift_end, skill, rest_day): the day fewest people of the same shift and skill rest, then the day fewest people
    of the institution rest, then the earliest day."""
    group = Counter(o["rest_day"] for o in others if _group(o) == _group(person))
    whole = Counter(o["rest_day"] for o in others)
    return min(range(1, 8), key=lambda d: (group[d], whole[d], d))


MAIN_SKILL_ORDER = ("physician", "nursing", "therapy", "caregiving")


def main_skill(skills) -> str:
    """The skill that defines the group for the rotation (a physician who also nurses counts as physician)."""
    return next((s for s in MAIN_SKILL_ORDER if s in skills), "caregiving")
