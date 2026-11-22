"""Dispatcher: pure functions, NO database and NO web framework.

The operational app (app/services/operations.py) and the SIRAG-D simulation (step 6) both import
this module, so the simulation tests exactly the same decision rules that run in production.

Inputs are plain dataclasses; outputs are ranked options. Time zone: every datetime must be
timezone-aware; shifts and the traffic profile are read in America/Mexico_City local time.

Policies (docs/spec/06_sirag_d_y_contingencia.md):
  nearest                 queue: first come, first served   candidates: shortest distance
  risk_priority           queue: priority → risk → wait     candidates: shortest distance
  risk_plus_live_traffic  queue: priority → risk → wait     candidates: shortest travel TIME with
                                                                        the traffic of that hour (Vela)
  human_dispatcher        queue: first come, first served   candidates: shortest distance
                          (the 5–20 min human decision delay is added by the simulation, not here)

Feasibility is the same for every policy (it is physics, not preference): right skill, visit inside
the shift, and no overlap with the caregiver's other visits including the travel time with traffic.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

MEXICO_CITY = ZoneInfo("America/Mexico_City")
POLICIES = ("nearest", "risk_priority", "risk_plus_live_traffic", "human_dispatcher")
DEFAULT_POLICY = "risk_plus_live_traffic"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
ROAD_CIRCUITY = 1.4          # config/simulation.yaml → traffic.road_circuity_factor (ASSUMPTION)
EARTH_RADIUS_KM = 6371.0


# ---- inputs -------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Caregiver:
    caregiver_id: str
    skills: frozenset[str]
    shift_start: time
    shift_end: time                      # shift_end <= shift_start → the shift ends the next day
    lat: float
    lon: float
    busy: tuple[tuple[datetime, datetime], ...] = ()   # planned windows already booked
    active: bool = True


@dataclass(frozen=True)
class Request:
    request_id: str
    priority: str                        # high | medium | low
    required_skill: str
    scheduled_for: datetime              # when the visit starts at the patient's home
    duration_min: int
    lat: float                           # patient's home
    lon: float
    created_at: datetime
    risk: float = 1.0                    # patient_risk(); higher = more fragile


@dataclass(frozen=True)
class TrafficProfile:
    """Average speed (km/h) per (day_type, hour) from traffic_hourly_profile (TomTom 2025)."""
    speed_kmh: dict[tuple[str, int], float]

    def speed_at(self, moment: datetime) -> float:
        local = moment.astimezone(MEXICO_CITY)
        day_type = "weekend" if local.weekday() >= 5 else "weekday"
        return self.speed_kmh[(day_type, local.hour)]


# ---- outputs ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Option:
    caregiver_id: str
    distance_km: float
    travel_min: float
    planned_start: datetime              # departure = scheduled_for - travel
    planned_end: datetime                # scheduled_for + duration
    load_min: float                      # minutes already booked that day (tie-breaker)
    arrival: datetime | None = None      # when the caregiver arrives (= the scheduled_for that was tried)


@dataclass
class Decision:
    request: Request
    options: list[Option] = field(default_factory=list)   # best first; empty = nobody available

    @property
    def chosen(self) -> Option | None:
        return self.options[0] if self.options else None


# ---- building blocks ----------------------------------------------------------------------------

def patient_risk(flags: dict[str, bool], multipliers: dict[str, float]) -> float:
    """Product of the risk multipliers that apply to the patient (config/simulation.yaml →
    health_markov.risk_multipliers, ASSUMPTIONS documented there). Example flags:
    {"chronic_lung_disease": True, "dependency_severe": False, "age_80_plus": True, ...}."""
    risk = 1.0
    for name, applies in flags.items():
        if applies and name in multipliers:
            risk *= multipliers[name]
    return risk


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def travel_minutes(distance_km: float, speed_kmh: float, extra_factor: float = 1.0) -> float:
    """Road distance (straight line × circuity) ÷ speed of that hour. extra_factor lets the
    simulation add a roadblock scenario (× 1.25)."""
    return distance_km * ROAD_CIRCUITY / speed_kmh * 60 * extra_factor


def trip_minutes(km: float, arrive_at: datetime, traffic: TrafficProfile, extra_factor: float = 1.0) -> float:
    """Travel time to arrive on time. The trip may span two hours of the traffic profile; we use the
    SLOWER of the arrival hour and the departure hour (conservative: better early than late)."""
    arrival_speed = traffic.speed_at(arrive_at - timedelta(minutes=1))
    first_guess = travel_minutes(km, arrival_speed, extra_factor)
    departure_speed = traffic.speed_at(arrive_at - timedelta(minutes=first_guess))
    return travel_minutes(km, min(arrival_speed, departure_speed), extra_factor)


def within_shift(cg: Caregiver, start: datetime, end: datetime) -> bool:
    """True if [start, end] fits inside one of the caregiver's shifts (local time).
    Checks the shift that starts on the visit's day and the one that started the day before
    (night shifts that cross midnight)."""
    local_start, local_end = start.astimezone(MEXICO_CITY), end.astimezone(MEXICO_CITY)
    for days_back in (0, 1):
        day = local_start.date() - timedelta(days=days_back)
        s = datetime.combine(day, cg.shift_start, MEXICO_CITY)
        e = datetime.combine(day, cg.shift_end, MEXICO_CITY)
        if e <= s:
            e += timedelta(days=1)
        if s <= local_start and local_end <= e:
            return True
    return False


def overlaps(start: datetime, end: datetime, busy: tuple[tuple[datetime, datetime], ...]) -> bool:
    return any(start < b_end and b_start < end for b_start, b_end in busy)


def booked_minutes_on(cg: Caregiver, day) -> float:
    return sum((e - s).total_seconds() / 60 for s, e in cg.busy
               if s.astimezone(MEXICO_CITY).date() == day)


# ---- policy -------------------------------------------------------------------------------------

def order_queue(requests: list[Request], policy: str, now: datetime) -> list[Request]:
    """Order in which waiting requests are dispatched."""
    _check(policy)
    if policy in ("nearest", "human_dispatcher"):
        return sorted(requests, key=lambda r: r.created_at)
    # priority first, then the most fragile patient, then whoever has waited longest
    return sorted(requests, key=lambda r: (PRIORITY_ORDER[r.priority], -r.risk,
                                           -(now - r.created_at).total_seconds()))


def rank_candidates(request: Request, caregivers: list[Caregiver], traffic: TrafficProfile,
                    policy: str = DEFAULT_POLICY, extra_traffic_factor: float = 1.0,
                    extra_minutes: Callable[[Caregiver], float] | None = None) -> list[Option]:
    """Every feasible caregiver for one request, best first according to the policy.

    extra_minutes (optional, used by SIRAG-D's roadblock scenario): fixed minutes added to the trip of a
    given caregiver, e.g. +15 min when the trip crosses a blocked district. The operation never passes it."""
    _check(policy)
    visit_end = request.scheduled_for + timedelta(minutes=request.duration_min)
    options: list[Option] = []
    for cg in caregivers:
        if not cg.active or request.required_skill not in cg.skills:
            continue
        if not within_shift(cg, request.scheduled_for, visit_end):
            continue
        km = haversine_km(cg.lat, cg.lon, request.lat, request.lon)
        minutes = trip_minutes(km, request.scheduled_for, traffic, extra_traffic_factor)
        if extra_minutes is not None:
            minutes += extra_minutes(cg)
        depart = request.scheduled_for - timedelta(minutes=minutes)
        if overlaps(depart, visit_end, cg.busy):
            continue
        options.append(Option(cg.caregiver_id, round(km, 2), round(minutes, 1), depart, visit_end,
                              booked_minutes_on(cg, request.scheduled_for.astimezone(MEXICO_CITY).date()),
                              request.scheduled_for))
    if policy == "risk_plus_live_traffic":
        key = lambda o: (o.travel_min, o.load_min, o.caregiver_id)  # noqa: E731
    else:
        key = lambda o: (o.distance_km, o.load_min, o.caregiver_id)  # noqa: E731
    return sorted(options, key=key)


def dispatch(requests: list[Request], caregivers: list[Caregiver], traffic: TrafficProfile,
             policy: str = DEFAULT_POLICY, now: datetime | None = None,
             extra_traffic_factor: float = 1.0) -> list[Decision]:
    """Dispatch a batch in queue order. Each choice books the caregiver's window before the next
    request is considered, so a batch can never produce overlaps."""
    now = now or datetime.now(MEXICO_CITY)
    pool = {cg.caregiver_id: cg for cg in caregivers}
    decisions = []
    for req in order_queue(requests, policy, now):
        options = rank_candidates(req, list(pool.values()), traffic, policy, extra_traffic_factor)
        decision = Decision(req, options)
        if decision.chosen:
            cg = pool[decision.chosen.caregiver_id]
            pool[cg.caregiver_id] = replace(cg, busy=cg.busy + ((decision.chosen.planned_start,
                                                                 decision.chosen.planned_end),))
        decisions.append(decision)
    return decisions


@dataclass(frozen=True)
class Hold:
    """Reservation of the proposed caregiver's window while a HIGH-priority request waits for approval.
    Other requests cannot take that window until `expires` (approval.hold_minutes after the proposal)."""
    request_id: str
    caregiver_id: str
    start: datetime
    end: datetime
    expires: datetime


def apply_holds(caregivers: list[Caregiver], holds: list[Hold], now: datetime,
                except_request: str | None = None) -> list[Caregiver]:
    """Caregivers with the active reservations added to their busy windows. The request that owns a
    reservation (except_request) can still use it. Used by the operation's worker AND by SIRAG-D."""
    by_cg: dict[str, list[tuple[datetime, datetime]]] = {}
    for h in holds:
        if h.expires > now and h.request_id != except_request:
            by_cg.setdefault(h.caregiver_id, []).append((h.start, h.end))
    return [replace(c, busy=c.busy + tuple(by_cg[c.caregiver_id])) if c.caregiver_id in by_cg else c
            for c in caregivers]


def arrival_times(requested: datetime, now: datetime, latest: datetime, step_min: int = 5):
    """Arrival times to try, earliest first: the requested time if it is still ahead, then every `step_min`
    minutes (on the clock grid) until `latest`. A request "as soon as possible" passes requested <= now."""
    if requested >= now:
        yield requested
    minute = (max(requested, now) - datetime(2000, 1, 1, tzinfo=MEXICO_CITY)).total_seconds() / 60
    t = datetime(2000, 1, 1, tzinfo=MEXICO_CITY) + timedelta(minutes=-(-minute // step_min) * step_min)
    if t == requested:
        t += timedelta(minutes=step_min)
    while t <= latest:
        yield t
        t += timedelta(minutes=step_min)


def earliest_options(request: Request, caregivers: list[Caregiver], traffic: TrafficProfile, policy: str,
                     now: datetime, latest: datetime, extra_traffic_factor: float = 1.0,
                     extra_minutes: Callable[[Caregiver], float] | None = None) -> list[Option]:
    """Ranked options at the EARLIEST arrival time (requested time first, then later, up to `latest`) at which
    someone can still leave on time (departure >= now). Used by the operation's worker (late tolerance) and by
    SIRAG-D, so both decide in exactly the same way. Empty list = nobody until `latest`."""
    for t in arrival_times(request.scheduled_for, now, latest):
        options = [o for o in rank_candidates(replace(request, scheduled_for=t), caregivers, traffic, policy,
                                              extra_traffic_factor, extra_minutes) if o.planned_start >= now]
        if options:
            return options
    return []


def dispatch_window(requests: list[Request], caregivers: list[Caregiver], traffic: TrafficProfile, policy: str,
                    now: datetime, latest: dict[str, datetime], extra_traffic_factor: float = 1.0,
                    extra_minutes: dict[str, Callable[[Caregiver], float]] | None = None) -> list[Decision]:
    """Like dispatch(), but each request may arrive late up to latest[request_id] (late tolerance).
    Each choice books the window before the next request is considered: a batch never overlaps."""
    pool = {cg.caregiver_id: cg for cg in caregivers}
    decisions = []
    for req in order_queue(requests, policy, now):
        options = earliest_options(req, list(pool.values()), traffic, policy, now, latest[req.request_id],
                                   extra_traffic_factor, (extra_minutes or {}).get(req.request_id))
        decision = Decision(req, options)
        if decision.chosen:
            cg = pool[decision.chosen.caregiver_id]
            pool[cg.caregiver_id] = replace(cg, busy=cg.busy + ((decision.chosen.planned_start,
                                                                 decision.chosen.planned_end),))
        decisions.append(decision)
    return decisions


def _check(policy: str) -> None:
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy {policy!r}; use one of {POLICIES}")
