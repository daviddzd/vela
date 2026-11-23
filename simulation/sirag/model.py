"""SIRAG-D model: one replication = one simulated week for every institution.

Processes (SimPy, time unit = minutes since START):
  health    every hour, per patient, Markov chain stable -> at_risk -> crisis (YAML rates x risk
            multipliers x PM2.5 effect). A crisis creates a HIGH-priority request at once.
  plans     care-plan visits drawn per day (prob. times_per_week / 7, a 15-min slot in visiting hours),
            released 2 h before, exactly like the worker of the operation.
  dispatch  every 5 min: waiting requests are ordered and assigned with app.services.dispatcher
            (order_queue + rank_candidates + trip_minutes). Nothing of the dispatcher is re-written here.

Earliest arrival up to a limit is ALSO the operation's function (dispatcher.earliest_options):
  - care-plan visit: at its time, or up to the late tolerance after it (YAML dispatch.late_tolerance_minutes,
    the same value the worker uses); after that it is "sin atender".
  - crisis: as soon as possible; after 4 h without anyone it is "sin atender" (ASSUMPTION: the family goes
    to an emergency room) and the crisis ends.
What belongs only to the simulation are the decision delays:
  - human_dispatcher waits U(5, 20) min before every decision (YAML);
  - Vela's policies wait U(1, 5) min for the coordinator's approval of HIGH priority (ASSUMPTION);
  - "vela_timeout" = Vela + time-limited approval: an URGENT high-priority request (due within
    approval.urgent_within_minutes) never waits more than approval.auto_apply_after_minutes (YAML), as the
    worker does in the operation (queue.auto_apply_urgent).

Common random numbers: every random draw comes from streams seeded with (seed, replication) and keyed by
the identity of the thing being drawn (patient-hour, plan-day, request), so the four policies face the
same crises and the same visit requests in replication r.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timedelta

import numpy as np
import simpy

from app.services import dispatcher as dsp
from app.services import labor
from app.services.visit_rules import visit_time
from simulation.sirag.data import World, config, road_km

START = datetime(2026, 11, 9, 0, 0, tzinfo=dsp.MEXICO_CITY)       # a Monday inside the calibrated air series
CYCLE = 5                                    # dispatch cycle, minutes
PLAN_LATE_TOLERANCE = config()["dispatch"]["late_tolerance_minutes"]   # same value as the worker
CRISIS_GIVE_UP = 240                         # ASSUMPTION: after 4 h without staff -> emergency room
CRISIS_SERVICE = "SRV-02"                    # ASSUMPTION: crisis -> nursing visit (30 min)
RELEASE_BEFORE = 120                         # same as the worker (care_plans.RELEASE_BEFORE)
CONTINGENCY_START = START + timedelta(days=2, hours=8)            # Wednesday 08:00
# Policies of the experiment -> the dispatcher policy they use. "vela_timeout" is Vela's dispatcher plus the
# time-limited approval rule (a product rule, not a dispatcher rule).
DISPATCH_POLICY = {"nearest": "nearest", "risk_priority": "risk_priority", "risk_plus_live_traffic": "risk_plus_live_traffic",
                   "vela_timeout": "risk_plus_live_traffic", "human_dispatcher": "human_dispatcher"}
STATE_STABLE, STATE_RISK, STATE_CRISIS = 0, 1, 2


@dataclass(frozen=True)
class Params:
    policy: str
    scenario: str
    replication: int
    seed: int = 2026
    days: int = 7
    approval_delay: tuple[float, float] = (1.0, 5.0)    # Vela, high priority only
    risk_multiplier: float = 1.0                        # stress test knob (sensitivity only)
    extra_staff: str = ""                               # "¿y si contratamos?": "" | "requested" | "targeted"
    holds: bool = True                                  # reservation of the proposed candidate (off only to measure it)
    labor_rules: bool = True                            # rest day + legal shifts; False only for the seed validation


@dataclass
class SimRequest:
    key: str
    kind: str                     # "plan" | "crisis"
    institution_id: str
    patient_idx: int
    district_id: str
    service_id: str
    priority: str
    requested: datetime           # scheduled time (plan) or crisis onset
    created: datetime
    ready_at: datetime            # after the decision / approval delay
    deadline: datetime
    d: dsp.Request                # what the dispatcher sees
    assigned: dict | None = None
    unattended: bool = False


def uniform_for(key: str, params: Params, salt: str, lo: float, hi: float) -> float:
    """Deterministic U(lo, hi) for one identity: identical across policies (common random numbers)."""
    return random.Random(f"{params.seed}|{params.replication}|{salt}|{key}").uniform(lo, hi)


@dataclass
class Model:
    world: World
    params: Params
    env: simpy.Environment = field(default_factory=simpy.Environment)

    def __post_init__(self) -> None:
        cfg = config()
        self.rates = cfg["health_markov"]["base_transition_per_hour"]
        sc = cfg["scenarios"].get(self.params.scenario, {})
        if "extends" in sc:
            sc = {**cfg["scenarios"][sc["extends"]], **sc}
        self.scenario = sc
        self.contingency = self.params.scenario != "normal"
        self.window = (CONTINGENCY_START, CONTINGENCY_START + timedelta(hours=sc.get("duration_hours", 24)))
        self.traffic_factor = sc.get("extra_traffic_factor", 1.0)
        self.blocked = set(sc.get("blocked_districts", []))
        self.block_minutes = cfg["traffic"]["blockade_extra_minutes"]
        w = self.world
        self.n = len(w.patients)
        self.state = np.zeros(self.n, dtype=np.int8)
        self.risk = np.array([p.risk for p in w.patients]) * self.params.risk_multiplier \
            * cfg["health_markov"]["stress_test_multiplier"]
        self.coef = np.array([p.pollution_coef for p in w.patients])
        self.baseline = np.array([w.pm25_baseline.get(p.station_id, 0.0) for p in w.patients])
        self.health_rng = np.random.default_rng([self.params.seed, self.params.replication, 1])
        self.plans_rng = np.random.default_rng([self.params.seed, self.params.replication, 2])
        self.dispatch_policy = DISPATCH_POLICY[self.params.policy]
        self.caregivers = {k: list(v) for k, v in w.caregivers.items()}
        # "¿y si contratamos?" (sensitivity only). New staff are based at the centroid of the institution's
        # district (ASSUMPTION).
        #   requested: +1 night nurse (20-08) in each 24 h institution and +1 day caregiver (08-16) in INS-A
        #   targeted:  +1 day caregiver (08-16) in INS-B and INS-D, where 8-h day-caregiver visits go unattended
        #   night_legal: "Cumplir jornada nocturna" (team decision 22 Nov 2026): every night shift above the legal 7 h
        #                (art. 61) becomes TWO 7-h shifts, 20:00-03:00 and 01:00-08:00, so night positions double.
        # Hired / split staff also get a weekly rest day with the same rotation rule (labor.assign_rest_days).
        for inst, pool in self.caregivers.items():
            lat, lon = w.district_centroid[w.institution_district[inst]]
            new: list[dsp.Caregiver] = []
            if self.params.extra_staff == "requested":
                if w.schedule[inst] == "24h":
                    new.append(dsp.Caregiver(f"NEW-N-{inst}", frozenset({"nursing"}), time(20), time(8), lat, lon))
                if inst == "INS-A":
                    new.append(dsp.Caregiver(f"NEW-D-{inst}", frozenset({"caregiving"}), time(8), time(16), lat, lon))
            elif self.params.extra_staff == "targeted" and inst in ("INS-B", "INS-D"):
                new.append(dsp.Caregiver(f"NEW-D-{inst}", frozenset({"caregiving"}), time(8), time(16), lat, lon))
            elif self.params.extra_staff == "night_legal":
                for i, c in enumerate(list(pool)):
                    if labor.legal_shift(c.shift_start, c.shift_end)["exceeds"]:
                        pool[pool.index(c)] = replace(c, shift_end=time(3))                       # 20:00-03:00
                        new.append(replace(c, caregiver_id=f"{c.caregiver_id}-B", shift_start=time(1), rest_day=None))
            for c in new:                     # each new person gets a rest day without moving anyone else's
                as_dict = lambda x: {"shift_start": x.shift_start, "shift_end": x.shift_end,  # noqa: E731
                                     "skill": labor.main_skill(x.skills), "rest_day": x.rest_day}
                pool.append(replace(c, rest_day=labor.next_rest_day(as_dict(c), [as_dict(o) for o in pool])))
        self.pending: list[SimRequest] = []
        self.holds: dict[str, list[dsp.Hold]] = {k: [] for k in self.caregivers}   # reservations by institution
        self.done: list[SimRequest] = []
        self.at_risk_entries = 0               # transparency: how often patients entered "at risk"
        self.at_risk_entries_window = 0        # ... inside the contingency window and affected districts
        from simulation.sirag.metrics import AFFECTED
        self.affected = np.array([p.district_id in AFFECTED for p in self.world.patients])

    # ---- clock --------------------------------------------------------------------------------
    def now(self) -> datetime:
        return START + timedelta(minutes=self.env.now)

    def at(self, t: datetime) -> float:
        return (t - START).total_seconds() / 60

    # ---- air ----------------------------------------------------------------------------------
    def pm25(self, station: str, t: datetime) -> float:
        hour = t.replace(minute=0, second=0, microsecond=0)
        if self.contingency and self.window[0] <= t < self.window[1]:
            targets = self.scenario["pm25_targets_ugm3"]
            return float(targets.get(station, targets["default"]))
        return self.world.pm25.get(station, {}).get(hour, self.world.pm25_baseline.get(station, 0.0))

    # ---- health (Markov chain, hourly) --------------------------------------------------------
    def health(self):
        w, r = self.world, self.rates
        stations = [p.station_id for p in w.patients]
        while True:
            t = self.now()
            level = np.array([self.pm25(s, t) for s in stations])
            # PM2.5 effect: relative increase per +10 ug/m3 above the station's 30-day baseline.
            # ASSUMPTION: coefficients from daily admission/mortality studies applied to an hourly risk.
            rr = 1.0 + self.coef * np.maximum(0.0, level - self.baseline) / 10.0
            u = self.health_rng.random(self.n)                         # always n draws: streams stay aligned
            p01 = r["stable_to_at_risk"] * self.risk * rr
            to_risk = (self.state == STATE_STABLE) & (u < p01)
            to_crisis = (self.state == STATE_RISK) & (u < r["at_risk_to_crisis"])
            back = (self.state == STATE_RISK) & ~to_crisis & (u < r["at_risk_to_crisis"] + r["at_risk_to_stable"])
            self.at_risk_entries += int(to_risk.sum())
            if self.window[0] <= t < self.window[1]:
                self.at_risk_entries_window += int((to_risk & self.affected).sum())
            self.state[to_risk] = STATE_RISK
            self.state[back] = STATE_STABLE
            for i in np.flatnonzero(to_crisis):
                self.state[i] = STATE_CRISIS
                onset = t + timedelta(minutes=float(u[i] / r["at_risk_to_crisis"]) * 60)   # inside the hour
                self.env.process(self.crisis(int(i), onset))
            yield self.env.timeout(60)

    def crisis(self, i: int, onset: datetime):
        yield self.env.timeout(max(0.0, self.at(onset) - self.env.now))
        p = self.world.patients[i]
        self.add(f"crisis|{p.patient_id}|{onset:%Y%m%d%H%M}", "crisis", i, CRISIS_SERVICE, "high",
                 requested=onset, created=onset, deadline=onset + timedelta(minutes=CRISIS_GIVE_UP))

    # ---- care plans ---------------------------------------------------------------------------
    def plans(self):
        w = self.world
        index = {p.patient_id: i for i, p in enumerate(w.patients)}
        drawn = []
        for day in range(self.params.days):
            u = self.plans_rng.random((len(w.plans), 2))              # fixed-size draws per day
            for (plan, (a, b)) in zip(w.plans, u):
                if a >= min(plan.times_per_week / 7, 1.0):
                    continue
                when = visit_time((START + timedelta(days=day)).date(), plan.service_id, float(b))   # same rule as the worker
                drawn.append((when - timedelta(minutes=RELEASE_BEFORE), when, plan))
        drawn.sort(key=lambda x: x[0])
        for release, when, plan in drawn:
            yield self.env.timeout(max(0.0, self.at(release) - self.env.now))
            i = index[plan.patient_id]
            self.add(f"plan|{plan.care_plan_id}|{when:%Y%m%d}", "plan", i, plan.service_id,
                     w.patients[i].base_priority, requested=when, created=self.now(),
                     deadline=when + timedelta(minutes=PLAN_LATE_TOLERANCE))

    def add(self, key, kind, i, service, priority, requested, created, deadline) -> None:
        p, w, prm = self.world.patients[i], self.world, self.params
        if prm.policy == "human_dispatcher":
            lo, hi = config()["human_dispatcher_delay_minutes"]
            delay = uniform_for(key, prm, "human", lo, hi)
        elif priority == "high":
            delay = uniform_for(key, prm, "approval", *prm.approval_delay)     # same draw for both Vela variants
            appr = config()["approval"]
            urgent = requested - (created + timedelta(minutes=appr["auto_apply_after_minutes"])) \
                <= timedelta(minutes=appr["urgent_within_minutes"])
            if prm.policy == "vela_timeout" and urgent:
                delay = min(delay, appr["auto_apply_after_minutes"])           # applied "por tiempo"
        else:
            delay = 0.0
        d = dsp.Request(key, priority, w.service_skill[service], requested,
                        w.duration[(p.institution_id, service)] if (p.institution_id, service) in w.duration else 30,
                        p.lat, p.lon, created, p.risk)
        self.pending.append(SimRequest(key, kind, p.institution_id, i, p.district_id, service, priority,
                                       requested, created, created + timedelta(minutes=delay), deadline, d))

    # ---- dispatch (the operation's dispatcher, every 5 minutes) -------------------------------
    def extra_minutes(self, req: SimRequest):
        if not self.blocked:
            return None
        patient_blocked = req.district_id in self.blocked
        cd = self.world.caregiver_district
        # ASSUMPTION: a trip "crosses" the blocked district if it starts or ends there.
        return lambda cg: self.block_minutes if (patient_blocked or cd.get(cg.caregiver_id) in self.blocked) else 0.0

    def reserve(self, req: SimRequest, now: datetime) -> None:
        """Like the operation: a high-priority request waiting for approval gets a proposal, and the proposed
        caregiver's window is reserved for approval.hold_minutes (dispatcher.Hold / apply_holds)."""
        holds = self.holds[req.institution_id]
        if any(h.request_id == req.key for h in holds):
            return
        pool = dsp.apply_holds(self.caregivers[req.institution_id], holds, now)
        options = dsp.earliest_options(req.d, pool, self.world.traffic, self.dispatch_policy, now, req.deadline,
                                       self.traffic_factor, self.extra_minutes(req))
        if options:
            minutes = config()["approval"]["hold_minutes"]
            for leg in options[0].legs:                 # a relay reserves both people
                holds.append(dsp.Hold(req.key, leg.caregiver_id, leg.planned_start, leg.planned_end,
                                      req.created + timedelta(minutes=minutes)))

    def try_assign(self, req: SimRequest, now: datetime) -> bool:
        pool = self.caregivers[req.institution_id]
        extra = self.extra_minutes(req)
        # The operation's own functions: other requests' reservations are respected (this one may use its own),
        # then the earliest arrival from the requested time up to the deadline.
        usable = dsp.apply_holds(pool, self.holds[req.institution_id], now, except_request=req.key)
        options = dsp.earliest_options(req.d, usable, self.world.traffic, self.dispatch_policy, now, req.deadline,
                                       self.traffic_factor, extra)
        for o in options[:1]:
            by_id = {c.caregiver_id: c for c in pool}
            dsp.book(by_id, o)                          # the operation's function: both people of a relay
            pool[:] = list(by_id.values())
            legs = [(by_id[leg.caregiver_id], leg) for leg in o.legs]
            req.assigned = {"caregiver_id": o.caregiver_id, "arrival": o.arrival, "planned_start": o.planned_start,
                            "planned_end": o.visit_end, "travel_min": o.travel_min,
                            "relay": o.relay.caregiver_id if o.relay else None,
                            "work_min": sum((leg.planned_end - leg.planned_start).total_seconds() / 60 for _, leg in legs),
                            # ASSUMPTION: each person goes back to base
                            "km": sum(2 * road_km(cg.lat, cg.lon, req.d.lat, req.d.lon) for cg, _ in legs),
                            "overtime_min": sum(self.overtime(cg, leg.planned_start, leg.planned_end, leg.arrival)
                                                for cg, leg in legs)}
            if req.kind == "crisis":
                self.env.process(self.resolve(req.patient_idx, o.visit_end))
            return True
        return False

    def overtime(self, cg: dsp.Caregiver, start: datetime, end: datetime, visit: datetime) -> float:
        """Minutes of the trip + visit that fall outside the caregiver's shift (e.g. leaving before it starts)."""
        local = visit.astimezone(dsp.MEXICO_CITY)
        for back in (0, 1):
            day = local.date() - timedelta(days=back)
            s = datetime.combine(day, cg.shift_start, dsp.MEXICO_CITY)
            e = datetime.combine(day, cg.shift_end, dsp.MEXICO_CITY)
            if e <= s:
                e += timedelta(days=1)
            if s <= local < e:
                return max(0.0, (s - start).total_seconds() / 60) + max(0.0, (end - e).total_seconds() / 60)
        return 0.0

    def resolve(self, i: int, when: datetime):
        yield self.env.timeout(max(0.0, self.at(when) - self.env.now))
        self.state[i] = STATE_STABLE                                           # crisis resolves after service

    def dispatch(self):
        while True:
            now = self.now()
            for inst, pool in self.caregivers.items():                       # forget windows from long ago
                self.caregivers[inst] = [replace(c, busy=tuple(b for b in c.busy if b[1] > now - timedelta(hours=12)))
                                         for c in pool]
            if self.params.policy != "human_dispatcher" and self.params.holds:   # the human makes no proposals
                for r in self.pending:
                    if r.priority == "high" and r.ready_at > now:
                        self.reserve(r, now)
            ready = [r for r in self.pending if r.ready_at <= now]
            by_inst: dict[str, list[SimRequest]] = {}
            for r in ready:
                by_inst.setdefault(r.institution_id, []).append(r)
            for inst, reqs in by_inst.items():
                lookup = {r.key: r for r in reqs}
                for d in dsp.order_queue([r.d for r in reqs], self.dispatch_policy, now):
                    req = lookup[d.request_id]          # dsp.Request.request_id holds our key
                    if self.try_assign(req, now):
                        self.pending.remove(req)
                        self.done.append(req)
                        self.holds[inst] = [h for h in self.holds[inst] if h.request_id != req.key]
            for inst in self.holds:                                            # expired reservations
                self.holds[inst] = [h for h in self.holds[inst] if h.expires > now]
            for req in [r for r in self.pending if now > r.deadline]:          # gave up
                req.unattended = True
                self.pending.remove(req)
                self.done.append(req)
                if req.kind == "crisis":
                    self.state[req.patient_idx] = STATE_STABLE                  # ER takes over
            yield self.env.timeout(CYCLE)

    # ---- run ----------------------------------------------------------------------------------
    def run(self) -> list[SimRequest]:
        self.env.process(self.health())
        self.env.process(self.plans())
        self.env.process(self.dispatch())
        self.env.run(until=self.params.days * 24 * 60)
        # requests still waiting at the end whose deadline is inside the horizon count as unattended
        end = self.now()
        self.done += [r for r in self.pending if r.deadline <= end]
        for r in self.done:
            if r.assigned is None:
                r.unattended = True
        return self.done
