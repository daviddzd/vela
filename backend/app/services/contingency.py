"""Live environmental contingency (docs/spec/06): readings -> detection -> per-institution proposal ->
coordinator decision -> apply -> revert when the event ends.

Two kinds of events that never mix: REAL ("detected", from the calibrated readings only) and DEMO
("demo_scenario", from v_air_quality_live while a scenario run is active). Each has its own record
(run_id) and its own proposal. Nothing changes for patients without a coordinator's approval.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.events import publish
from app.services import air_model
from app.services import dispatcher as dsp
from app.services import operations as ops

PHASES = ("normal", "watch", "phase1")
CLOSE_AFTER_HOURS_BELOW = 2          # anti-flicker: 2 consecutive hourly readings below "watch" everywhere
OXYGEN_SERVICE = "SRV-08"
DISTRICT_NAMES_SQL = "SELECT district_id, name FROM districts"


def thresholds() -> dict:
    c = ops.settings_yaml()["contingency"]["thresholds"]
    return {"o3": c["o3_phase1_ppb_1h"], "pm25": c["pm25_phase1_ugm3_24h_avg"], "watch": c["watch_fraction"]}


def hour_floor(t: datetime) -> datetime:
    return t.astimezone(dsp.MEXICO_CITY).replace(minute=0, second=0, microsecond=0)


# ---- readings ------------------------------------------------------------------------------------

def ensure_readings(db: Session, now: datetime | None = None, max_backfill_hours: int = 72) -> int:
    """Insert the calibrated readings missing up to the current hour (fills the gap after the seed too)."""
    now = hour_floor(now or ops.now())
    stations = db.execute(text("""SELECT s.station_id, s.o3_factor::float AS o3f, s.pm25_factor::float AS pmf,
                                         max(r.measured_at) AS last
                                  FROM air_quality_stations s LEFT JOIN air_quality_readings r USING (station_id)
                                  GROUP BY s.station_id, s.o3_factor, s.pm25_factor""")).all()
    rows = []
    for s in stations:
        start = max((s.last + timedelta(hours=1)) if s.last else now, now - timedelta(hours=max_backfill_hours))
        t = hour_floor(start)
        while t <= now:
            o3, pm = air_model.reading(s.station_id, s.o3f, s.pmf, t)
            rows.append({"s": s.station_id, "t": t, "o3": o3, "pm": pm})
            t += timedelta(hours=1)
    if rows:
        db.execute(text("""INSERT INTO air_quality_readings (station_id, measured_at, o3_ppb, pm25_ugm3, source)
                           VALUES (:s, :t, :o3, :pm, 'synthetic_calibrated') ON CONFLICT DO NOTHING"""), rows)
    return len(rows)


def station_levels(db: Session, at: datetime, live: bool) -> list[dict]:
    """O3 of the hour and PM2.5 24-h average per station at `at`, with its phase.
    live=False: calibrated readings only (real events). live=True: v_air_quality_live (scenario in front)."""
    src = "v_air_quality_live" if live else "air_quality_readings"
    th = thresholds()
    rows = db.execute(text(f"""
        SELECT s.station_id, s.name, s.district_id, d.name AS district_name, s.lat::float, s.lon::float,
               (SELECT o3_ppb::float FROM {src} x WHERE x.station_id = s.station_id AND x.measured_at <= :at
                 ORDER BY measured_at DESC LIMIT 1) AS o3,
               (SELECT avg(pm25_ugm3)::float FROM {src} x WHERE x.station_id = s.station_id
                 AND x.measured_at > :at - interval '24 hours' AND x.measured_at <= :at) AS pm25_24h,
               (SELECT bool_or(source = 'scenario') FROM {src} x WHERE x.station_id = s.station_id
                 AND x.measured_at > :at - interval '24 hours' AND x.measured_at <= :at) AS scenario
        FROM air_quality_stations s JOIN districts d USING (district_id) ORDER BY s.station_id"""),
        {"at": at}).mappings().all()
    out = []
    for r in rows:
        o3, pm = r["o3"] or 0.0, r["pm25_24h"] or 0.0
        ratio = max(o3 / th["o3"], pm / th["pm25"])
        phase = "phase1" if ratio >= 1 else "watch" if ratio >= th["watch"] else "normal"
        pollutant = "o3" if o3 / th["o3"] >= pm / th["pm25"] else "pm25"
        out.append({**dict(r), "o3": round(o3, 1), "pm25_24h": round(pm, 1), "phase": phase, "pollutant": pollutant,
                    "scenario": bool(r["scenario"]) if live else False})
    return out


# ---- detection (worker, every minute) ---------------------------------------------------------------

def detect(db: Session, now: datetime | None = None) -> list[str]:
    """Open / escalate / close events. Returns ids of events that changed."""
    now = now or ops.now()
    hour = hour_floor(now)
    changed = []
    changed += _handle(db, station_levels(db, hour, live=False), origin="detected", run_id=None, hour=hour)
    run = db.execute(text("SELECT run_id, scenario FROM scenario_runs WHERE active")).first()
    if run:
        changed += _handle(db, station_levels(db, hour, live=True), origin="demo_scenario", run_id=run.run_id,
                           hour=hour, scenario=run.scenario)
    # demo events whose scenario was switched off end at once ("Volver a normal")
    for ev in db.execute(text("""SELECT e.event_id FROM contingency_events e JOIN scenario_runs r USING (run_id)
                                 WHERE e.ended_at IS NULL AND NOT r.active""")).scalars():
        close(db, ev)
        changed.append(ev)
    return changed


def _handle(db, levels, origin, run_id, hour, scenario=None) -> list[str]:
    worst = max(levels, key=lambda l: PHASES.index(l["phase"]))
    phase = worst["phase"]
    ev = db.execute(text("""SELECT * FROM contingency_events WHERE ended_at IS NULL AND
                            run_id IS NOT DISTINCT FROM :r"""), {"r": run_id}).mappings().first()
    hot = [l for l in levels if l["phase"] == ("phase1" if phase == "phase1" else "watch")]
    stations = [{k: l[k] for k in ("station_id", "district_id", "o3", "pm25_24h", "phase")} for l in levels if l["phase"] != "normal"]
    districts = sorted({l["district_id"] for l in hot})
    if ev is None:
        if phase == "normal":
            return []
        event_id = db.scalar(text("""
            INSERT INTO contingency_events (pollutant, phase, origin, scenario, run_id, districts, stations, last_checked_hour)
            VALUES (:p, :ph, :o, :sc, :r, :d, CAST(:st AS jsonb), :h) RETURNING event_id"""),
            {"p": worst["pollutant"], "ph": phase, "o": origin, "sc": scenario, "r": run_id, "d": districts,
             "st": json.dumps(stations), "h": hour})
        _platform_alert(db, event_id, phase, districts, origin)
        audit(db, user_id=None, institution_id=None, action="contingency_detected", entity="contingency_event",
              entity_id=event_id, detail={"phase": phase, "origin": origin, "districts": districts})
        if phase == "phase1":
            generate_proposals(db, event_id)
        publish(db, "contingency.changed", None, event_id=event_id, status="opened")
        return [event_id]

    event_id = ev["event_id"]
    if phase == "normal":
        if ev["last_checked_hour"] != hour:
            streak = ev["below_streak"] + 1
            db.execute(text("UPDATE contingency_events SET below_streak = :s, last_checked_hour = :h WHERE event_id = :e"),
                       {"s": streak, "h": hour, "e": event_id})
            if streak >= CLOSE_AFTER_HOURS_BELOW and run_id is None:
                close(db, event_id)
                return [event_id]
        return []
    escalated = PHASES.index(phase) > PHASES.index(ev["phase"])
    db.execute(text("""UPDATE contingency_events SET below_streak = 0, last_checked_hour = :h, stations = CAST(:st AS jsonb),
                       phase = CASE WHEN :esc THEN :ph ELSE phase END,
                       districts = CASE WHEN :esc THEN :d ELSE districts END WHERE event_id = :e"""),
               {"h": hour, "st": json.dumps(stations), "esc": escalated, "ph": phase, "d": districts, "e": event_id})
    if escalated and phase == "phase1":
        _platform_alert(db, event_id, phase, districts, origin)
        generate_proposals(db, event_id)
        publish(db, "contingency.changed", None, event_id=event_id, status="escalated")
        return [event_id]
    return []


def _platform_alert(db, event_id, phase, districts, origin) -> None:
    names = dict(db.execute(text(DISTRICT_NAMES_SQL)).all())
    label = {"phase1": "Fase I", "watch": "vigilancia"}[phase]
    prefix = "[Demostración] " if origin == "demo_scenario" else ""
    db.execute(text("""INSERT INTO alerts (institution_id, type, level, message, code)
                       VALUES (NULL, 'contingency', :lvl, :m, :c)"""),
               {"lvl": "critical" if phase == "phase1" else "watch", "c": f"contingency_{event_id}",
                "m": f"{prefix}Contingencia ambiental, {label}: {', '.join(names.get(d, d) for d in districts)}. "
                     "Revisa la propuesta en Contingencia."})


# ---- proposal --------------------------------------------------------------------------------------

def generate_proposals(db: Session, event_id: str) -> int:
    """One list per institution: raise priority of pollution-sensitive patients in affected districts, advance
    their oxygen-therapy visits, notify their families, recalculate today's routes if traffic is degraded."""
    ev = db.execute(text("SELECT * FROM contingency_events WHERE event_id = :e"), {"e": event_id}).mappings().one()
    if db.scalar(text("SELECT count(*) FROM contingency_proposals WHERE event_id = :e"), {"e": event_id}):
        return 0
    names = dict(db.execute(text(DISTRICT_NAMES_SQL)).all())
    pol = {"o3": "ozono", "pm25": "PM2.5"}[ev["pollutant"]]
    patients = db.execute(text("""
        SELECT pa.patient_id, pa.institution_id, pa.base_priority, vp.district_id,
               vp.first_name || ' ' || vp.paternal_surname AS name,
               vp.chronic_lung_disease, vp.heart_disease, vp.stroke
        FROM patients pa JOIN v_persons vp USING (person_id)
        WHERE pa.active AND vp.pollution_sensitive AND vp.district_id = ANY(:d)
          -- "sensitive" comes from health conditions: only with a valid health_data consent (docs/spec/11)
          AND EXISTS (SELECT 1 FROM v_consents c WHERE c.patient_id = pa.patient_id AND c.type = 'health_data' AND c.is_valid)"""),
        {"d": ev["districts"]}).mappings().all()
    rows = []
    for p in patients:
        cond = ", ".join(c for c, flag in (("enfermedad pulmonar crónica", p["chronic_lung_disease"]),
                                           ("enfermedad del corazón", p["heart_disease"]), ("antecedente de EVC", p["stroke"])) if flag)
        where = names.get(p["district_id"], p["district_id"])
        if p["base_priority"] != "high":
            rows.append({"i": p["institution_id"], "k": "raise_priority", "p": p["patient_id"], "r": None, "a": None,
                         "reason": f"{p['name']} vive en {where} (contingencia por {pol}) y es sensible a la contaminación "
                                   f"({cond}). Sube de prioridad {ops_priority(p['base_priority'])} a alta mientras dure la contingencia.",
                         "payload": {"from": p["base_priority"], "to": "high"}})
        for v in db.execute(text("""
                SELECT r.request_id, r.scheduled_for FROM service_requests r
                WHERE r.patient_id = :p AND r.service_id = :s AND r.status IN ('validated','queued','assigned')
                  AND r.scheduled_for BETWEEN now() + interval '90 minutes' AND now() + interval '48 hours'"""),
                {"p": p["patient_id"], "s": OXYGEN_SERVICE}).all():
            rows.append({"i": p["institution_id"], "k": "advance_oxygen", "p": p["patient_id"], "r": v.request_id, "a": None,
                         "reason": f"Oxigenoterapia de {p['name']} programada para el "
                                   f"{v.scheduled_for.astimezone(dsp.MEXICO_CITY):%d/%m %H:%M}; se propone adelantarla a lo antes posible.",
                         "payload": {"scheduled_for": v.scheduled_for.isoformat()}})
        for f in db.execute(text("""SELECT first_name || ' ' || paternal_surname AS fam FROM family_members
                                    WHERE patient_id = :p ORDER BY family_member_id LIMIT 1"""), {"p": p["patient_id"]}).all():
            msg = (f"Hay contingencia ambiental por {pol} en {where}. Por la salud de {p['name']}, eviten actividades al "
                   "aire libre, mantengan ventanas cerradas en las horas de más contaminación y llamen a la institución "
                   "si notan falta de aire. Si hay dificultad grave para respirar, llamen al 911.")
            rows.append({"i": p["institution_id"], "k": "notify_family", "p": p["patient_id"], "r": None, "a": None,
                         "reason": f"Avisar a {f.fam}, familiar de {p['name']}.", "payload": {"message": msg}})
    rows += _route_items(db, ev)
    for row in rows:
        db.execute(text("""INSERT INTO contingency_proposals (event_id, institution_id, kind, patient_id, request_id,
                           assignment_id, reason, payload) VALUES (:e, :i, :k, :p, :r, :a, :reason, CAST(:payload AS jsonb))"""),
                   {**row, "e": event_id, "payload": json.dumps(row["payload"])})
    for inst in sorted({r["i"] for r in rows}):
        audit(db, user_id=None, institution_id=inst, action="contingency_proposed", entity="contingency_event",
              entity_id=event_id, detail={"items": sum(1 for r in rows if r["i"] == inst)})
        publish(db, "contingency.changed", inst, event_id=event_id, status="proposed")
    return len(rows)


def ops_priority(p: str) -> str:
    return {"high": "alta", "medium": "media", "low": "baja"}[p]


def _route_items(db, ev) -> list[dict]:
    """Today's not-yet-started visits whose trip gets longer with the current traffic condition."""
    cond = active_traffic(db, ev["run_id"])
    if cond is None:
        return []
    factor, blocked, extra = cond
    traffic = ops.load_traffic(db)
    centroids = {d: (float(la), float(lo)) for d, la, lo in db.execute(text("SELECT district_id, lat, lon FROM districts")).all()}
    rows = []
    for a in db.execute(text("""
            SELECT a.assignment_id, a.institution_id, a.caregiver_id, a.planned_start, a.planned_end, a.travel_min::float,
                   ins.duration_min, c.base_lat::float AS clat, c.base_lon::float AS clon, pe.lat::float AS plat,
                   pe.lon::float AS plon, pe.district_id, pe.first_name || ' ' || pe.paternal_surname AS name
            FROM assignments a JOIN service_requests r USING (request_id) JOIN caregivers c USING (caregiver_id)
            JOIN institution_services ins ON ins.institution_id = r.institution_id AND ins.service_id = r.service_id
            JOIN patients pa ON pa.patient_id = r.patient_id JOIN persons pe ON pe.person_id = pa.person_id
            WHERE a.status = 'active' AND a.arrived_at IS NULL AND a.planned_start > now()
              AND (a.planned_start AT TIME ZONE 'America/Mexico_City')::date = (now() AT TIME ZONE 'America/Mexico_City')::date""")).mappings().all():
        arrival = a["planned_start"] + timedelta(minutes=a["travel_min"] or 0)   # also right for each person of a relay
        km = dsp.haversine_km(a["clat"], a["clon"], a["plat"], a["plon"])
        cg_district = min(centroids, key=lambda d: dsp.haversine_km(a["clat"], a["clon"], *centroids[d]))
        crosses = a["district_id"] in blocked or cg_district in blocked
        new_travel = dsp.trip_minutes(km, arrival, traffic, factor) + (extra if crosses else 0)
        if new_travel <= (a["travel_min"] or 0) + 1:
            continue
        rows.append({"i": a["institution_id"], "k": "recalculate_routes", "p": None, "r": None, "a": a["assignment_id"],
                     "reason": f"Visita a {a['name']} a las {arrival.astimezone(dsp.MEXICO_CITY):%H:%M}: con el tráfico actual "
                               f"el traslado pasa de {a['travel_min']:.0f} a {new_travel:.0f} min; se propone salir antes.",
                     "payload": {"new_planned_start": (arrival - timedelta(minutes=new_travel)).isoformat(),
                                 "new_travel_min": round(new_travel, 1)}})
    return rows


def active_traffic(db: Session, run_id: str | None = None):
    """(factor, blocked districts, extra minutes) of the active traffic condition, or None.
    Real events only see real conditions; demo events see their own run's."""
    row = db.execute(text("""SELECT extra_factor::float AS f, blocked_districts AS b, extra_minutes AS m
                             FROM traffic_conditions WHERE active AND run_id IS NOT DISTINCT FROM :r
                             ORDER BY started_at DESC LIMIT 1"""), {"r": run_id}).first()
    return (row.f, set(row.b), row.m) if row else None


# ---- decision ------------------------------------------------------------------------------------

class NotYours(Exception):
    """The proposal belongs to another institution (RLS hid it) or the user may not decide."""


def decide(db: Session, *, user_id: str, institution_id: str, event_id: str, approve: list[int] | None) -> dict:
    """approve=None -> approve all; [] -> reject all; [ids] -> approve those, reject the rest."""
    items = db.execute(text("""SELECT * FROM contingency_proposals WHERE event_id = :e AND institution_id = :i
                               AND status = 'proposed' ORDER BY proposal_id"""), {"e": event_id, "i": institution_id}).mappings().all()
    if approve is not None and set(approve) - {r["proposal_id"] for r in items}:
        raise NotYours()
    chosen = {r["proposal_id"] for r in items} if approve is None else set(approve)
    applied = 0
    for r in items:
        ok = r["proposal_id"] in chosen
        db.execute(text("""UPDATE contingency_proposals SET status = :s, decided_by = :u, decided_at = now()
                           WHERE proposal_id = :p"""), {"s": "approved" if ok else "rejected", "u": user_id, "p": r["proposal_id"]})
        if ok:
            _apply(db, r, user_id)
            applied += 1
    decision = "approved" if items and applied == len(items) else "partially_approved" if applied else "rejected"
    db.execute(text("""INSERT INTO contingency_decisions (event_id, institution_id, decision, decided_by, notes)
                       VALUES (:e, :i, :d, :u, :n)
                       ON CONFLICT (event_id, institution_id) DO UPDATE SET decision = EXCLUDED.decision,
                         decided_by = EXCLUDED.decided_by, decided_at = now(), notes = EXCLUDED.notes"""),
               {"e": event_id, "i": institution_id, "d": decision, "u": user_id, "n": f"{applied} de {len(items)} cambios aprobados"})
    audit(db, user_id=user_id, institution_id=institution_id, action="contingency_decided", entity="contingency_event",
          entity_id=event_id, detail={"decision": decision, "approved": applied, "total": len(items)})
    publish(db, "contingency.changed", institution_id, event_id=event_id, status=decision)
    return {"decision": decision, "approved": applied, "total": len(items)}


def _apply(db: Session, r, user_id: str) -> None:
    kind, payload = r["kind"], dict(r["payload"])
    if kind == "raise_priority":
        db.execute(text("""INSERT INTO priority_overrides (patient_id, institution_id, event_id, priority)
                           VALUES (:p, :i, :e, 'high')"""), {"p": r["patient_id"], "i": r["institution_id"], "e": r["event_id"]})
        # waiting requests of that patient move up in the queue now (originals kept to revert)
        changed = db.execute(text("""UPDATE service_requests x SET priority = 'high' FROM service_requests o
                                     WHERE x.request_id = o.request_id AND x.patient_id = :p AND x.status = 'queued'
                                       AND x.priority <> 'high' RETURNING x.request_id, o.priority"""), {"p": r["patient_id"]}).all()
        payload["changed_requests"] = {rid: prio for rid, prio in changed}
    elif kind == "advance_oxygen":
        rid = r["request_id"]
        db.execute(text("UPDATE assignments SET status = 'cancelled' WHERE request_id = :r AND status = 'active'"), {"r": rid})
        db.execute(text("""UPDATE service_requests SET status = 'cancelled', status_reason = 'advanced_by_contingency'
                           WHERE request_id = :r AND status IN ('validated','queued','assigned')"""), {"r": rid})
        soon = ops.now() + timedelta(minutes=30)
        soon = soon.replace(minute=soon.minute - soon.minute % 5, second=0, microsecond=0)
        payload["new_request_id"] = ops.create_request(
            db, user_id=user_id, institution_id=r["institution_id"], patient_id=r["patient_id"], service_id=OXYGEN_SERVICE,
            scheduled_for=soon, priority="high", origin="contingency")
    elif kind == "notify_family":
        db.execute(text("""INSERT INTO family_notices (institution_id, patient_id, event_id, message)
                           VALUES (:i, :p, :e, :m)"""), {"i": r["institution_id"], "p": r["patient_id"], "e": r["event_id"],
                                                         "m": payload["message"]})
    elif kind == "recalculate_routes":
        try:
            with db.begin_nested():
                db.execute(text("""UPDATE assignments SET planned_start = :ps, travel_min = :t
                                   WHERE assignment_id = :a AND status = 'active' AND arrived_at IS NULL"""),
                           {"ps": payload["new_planned_start"], "t": payload["new_travel_min"], "a": r["assignment_id"]})
            payload["result"] = "updated"
        except Exception:  # noqa: BLE001 - the earlier departure overlaps another visit: tell coordination
            payload["result"] = "needs_reassignment"
            db.execute(text("""INSERT INTO alerts (institution_id, type, level, message, code)
                               VALUES (:i, 'contingency', 'high', :m, NULL)"""),
                       {"i": r["institution_id"], "m": f"La visita {r['assignment_id']} ya no cabe con el tráfico actual: reasígnala."})
    db.execute(text("UPDATE contingency_proposals SET status = 'applied', payload = CAST(:pl AS jsonb) WHERE proposal_id = :p"),
               {"pl": json.dumps(payload), "p": r["proposal_id"]})
    audit(db, user_id=user_id, institution_id=r["institution_id"], action="contingency_applied", entity="contingency_proposal",
          entity_id=str(r["proposal_id"]), detail={"kind": kind, "event_id": r["event_id"]})


# ---- end of the event: everything back to the base priority ------------------------------------------

def close(db: Session, event_id: str) -> None:
    db.execute(text("UPDATE contingency_events SET ended_at = now() WHERE event_id = :e AND ended_at IS NULL"), {"e": event_id})
    db.execute(text("UPDATE priority_overrides SET active = false, ended_at = now() WHERE event_id = :e AND active"),
               {"e": event_id})
    for r in db.execute(text("""SELECT proposal_id, institution_id, payload FROM contingency_proposals
                                WHERE event_id = :e AND kind = 'raise_priority' AND status = 'applied'"""), {"e": event_id}).all():
        for rid, prio in (r.payload.get("changed_requests") or {}).items():
            db.execute(text("UPDATE service_requests SET priority = :p WHERE request_id = :r AND status = 'queued'"),
                       {"p": prio, "r": rid})
    db.execute(text("UPDATE contingency_proposals SET status = 'reverted' WHERE event_id = :e AND status = 'applied' "
                    "AND kind = 'raise_priority'"), {"e": event_id})
    db.execute(text("UPDATE contingency_proposals SET status = 'rejected' WHERE event_id = :e AND status = 'proposed'"),
               {"e": event_id})
    for n in db.execute(text("""SELECT DISTINCT institution_id, patient_id FROM contingency_proposals
                                WHERE event_id = :e AND kind = 'notify_family' AND status = 'applied'"""), {"e": event_id}).all():
        db.execute(text("""INSERT INTO family_notices (institution_id, patient_id, event_id, message) VALUES (:i, :p, :e,
                           'Terminó la contingencia ambiental. Las visitas vuelven a su prioridad habitual.')"""),
                   {"i": n.institution_id, "p": n.patient_id, "e": event_id})
    insts = [i for (i,) in db.execute(text("SELECT DISTINCT institution_id FROM contingency_proposals WHERE event_id = :e"),
                                      {"e": event_id}).all()]
    for inst in insts:
        audit(db, user_id=None, institution_id=inst, action="contingency_reverted", entity="contingency_event", entity_id=event_id)
    audit(db, user_id=None, institution_id=None, action="contingency_ended", entity="contingency_event", entity_id=event_id)
    publish(db, "contingency.changed", None, event_id=event_id, status="ended")


# ---- demo panel inputs (owner only; they change INPUT data, then the system detects by itself) ------

def activate_scenario(db: Session, scenario: str, user_id: str | None) -> str | None:
    """Switch the demo world. 'normal' deactivates the running scenario (its readings stay stored apart; the
    calibrated history is untouched) and its demo inputs. Returns the new run id (None for normal)."""
    for run_id in db.execute(text("UPDATE scenario_runs SET active = false, ended_at = now() WHERE active RETURNING run_id")).scalars().all():
        db.execute(text("UPDATE traffic_conditions SET active = false, ended_at = now() WHERE run_id = :r AND active"), {"r": run_id})
        db.execute(text("UPDATE caregiver_unavailability SET active = false, ends_at = now() WHERE run_id = :r AND active"), {"r": run_id})
    audit(db, user_id=user_id, institution_id=None, action="demo_scenario", entity="scenario", entity_id=scenario)
    if scenario == "normal":
        detect(db)          # closes the demo event at once and reverts its changes
        return None
    cfg = ops.settings_yaml()["scenarios"]
    sc = {**cfg[cfg[scenario]["extends"]], **cfg[scenario]} if "extends" in cfg[scenario] else cfg[scenario]
    ensure_readings(db)
    run_id = db.scalar(text("INSERT INTO scenario_runs (scenario, started_by) VALUES (:s, :u) RETURNING run_id"),
                       {"s": scenario, "u": user_id})
    # The episode "already built up": the last 24 h and the next `duration_hours` use the scenario's PM2.5
    # targets (a 24-h average cannot cross 97.5 otherwise). O3 keeps the calibrated value.
    now = hour_floor(ops.now())
    targets = sc["pm25_targets_ugm3"]
    rows = []
    for s in db.execute(text("SELECT station_id, o3_factor::float AS o3f, pm25_factor::float AS pmf FROM air_quality_stations")).all():
        t = now - timedelta(hours=23)
        while t <= now + timedelta(hours=sc.get("duration_hours", 24)):
            o3, _ = air_model.reading(s.station_id, s.o3f, s.pmf, t)
            rows.append({"r": run_id, "s": s.station_id, "t": t, "o3": o3 * sc.get("o3_factor", 1.0),
                         "pm": float(targets.get(s.station_id, targets["default"]))})
            t += timedelta(hours=1)
    db.execute(text("""INSERT INTO air_quality_scenario (run_id, station_id, measured_at, o3_ppb, pm25_ugm3)
                       VALUES (:r, :s, :t, :o3, :pm)"""), rows)
    if "extra_traffic_factor" in sc:
        db.execute(text("""INSERT INTO traffic_conditions (extra_factor, blocked_districts, extra_minutes, origin, run_id)
                           VALUES (:f, :b, :m, 'demo_scenario', :r)"""),
                   {"f": sc["extra_traffic_factor"], "b": sc.get("blocked_districts", []),
                    "m": ops.settings_yaml()["traffic"]["blockade_extra_minutes"], "r": run_id})
    publish(db, "contingency.changed", None, status="scenario", scenario=scenario)
    return run_id
