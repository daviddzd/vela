"""Coverage of the week (/personal → "Cobertura de la semana"): by day and time slot, the skills with NOBODY on shift.

Pure functions (no database). Which hours a skill must be covered: the hours in which the institution's own staffing
plan has someone with that skill on shift (the union of their shifts, any day). A gap is a slot inside those hours in
which, on that particular day, nobody with the skill is on shift: because of the weekly rest day (LFT art. 69) or
because the person is out of service. Example: the only 08:00–16:00 nurse rests on Tuesday and the next nurse starts
at 10:00 → "martes 8:00–10:00: sin enfermería".

It does NOT judge whether the plan itself covers every hour the institution needs (e.g. no physician at night):
that is the institution's decision, as with the night shift (decisiones_pantallas_faltantes.md).
"On shift" is dispatcher.within_shift, the same rule the dispatcher uses to assign visits.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.services import dispatcher as dsp

STEP_MIN = 15                # slot size; every shift of the seed starts and ends on a quarter hour


@dataclass(frozen=True)
class Person:
    caregiver: dsp.Caregiver
    out: tuple[tuple[datetime, datetime | None], ...] = ()     # out-of-service windows (end None = until further notice)

    def available(self, t: datetime) -> bool:
        return not any(s <= t and (e is None or t < e) for s, e in self.out)


def _on_shift(cg: dsp.Caregiver, t: datetime) -> bool:
    return dsp.within_shift(cg, t, t + timedelta(minutes=STEP_MIN))


def week_gaps(people: list[Person], first_day: date, days: int = 7) -> list[dict]:
    """Gaps of the `days` days from `first_day` 00:00: [{skill, start, end}] in time order. Consecutive slots are
    merged (a night gap from 20:00 to 08:00 the next day is ONE gap)."""
    start = datetime.combine(first_day, datetime.min.time(), dsp.MEXICO_CITY)
    slots = [start + timedelta(minutes=STEP_MIN * i) for i in range(days * 24 * 60 // STEP_MIN)]
    gaps: list[dict] = []
    for skill in sorted({s for p in people for s in p.caregiver.skills}):
        staff = [p for p in people if skill in p.caregiver.skills]
        # the plan's hours for this skill: someone has a shift then on a day they work (rest day ignored)
        planned = [any(_on_shift(dsp.Caregiver("x", frozenset(), p.caregiver.shift_start, p.caregiver.shift_end, 0, 0), t)
                       for p in staff) for t in slots]
        current: dict | None = None
        for t, needed in zip(slots, planned):
            uncovered = needed and not any(p.caregiver.active and p.available(t) and _on_shift(p.caregiver, t)
                                           for p in staff)
            if uncovered and current is not None and current["end"] == t:
                current["end"] = t + timedelta(minutes=STEP_MIN)
            elif uncovered:
                current = {"skill": skill, "start": t, "end": t + timedelta(minutes=STEP_MIN)}
                gaps.append(current)
    return sorted(gaps, key=lambda g: (g["start"], g["skill"]))
