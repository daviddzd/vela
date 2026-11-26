"""Collect every number that "La biblia de Enlaza" shows, straight from the repository and the database.

Rule of the bible: no number is typed by hand in the chapters. A chapter writes {{ key }} and build.py
replaces it with the value collected here. Each value keeps its source (file, query or config key), which
is printed in the "Números clave" tables and in docs/biblia/out/numeros.csv for the final check.

Run (inside the vela-biblia image, see scripts/build_biblia.sh):
    python3 docs/biblia/build/collect_numbers.py   # writes docs/biblia/out/numeros.json and numeros.csv

(Named collect_numbers.py, not numbers.py: a file called numbers.py would hide Python's own `numbers` module.)

Sources, in this order:
  1. database/seed/*.csv            -> what the seed contains (fixed, versioned)
  2. the live database (vela_api)   -> row-level security proof, calibration percentages
  3. config/*.yaml                  -> parameters shared by the operation and SIRAG-D
  4. simulation/results/*           -> SIRAG-D results
  5. voice/eval/results/metrics.json -> Enlaza Voz evaluation
  6. data/business/assumptions.csv  -> business model inputs (each row has its own source)
  7. docs/biblia/datos/mediciones_manuales.yaml -> measurements made by hand (with date and document)
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "biblia" / "out"

NUMBERS: dict[str, dict] = {}


# ----------------------------------------------------------------------------------------------------------------
# Formatting (Spanish, Mexico: 20,000 and 57.9 %)
# ----------------------------------------------------------------------------------------------------------------
def fmt(value, kind: str = "int", decimals: int = 1) -> str:
    """Format a value the way the bible prints it."""
    if isinstance(value, str):
        return value
    if kind == "int":
        return f"{round(value):,}"
    if kind == "pct":
        return f"{value:,.{decimals}f} %"
    if kind == "dec":
        return f"{value:,.{decimals}f}"
    if kind == "money":
        return f"−${-value:,.0f}" if value < 0 else f"${value:,.0f}"
    raise ValueError(kind)


def add(key: str, value, label: str, source: str, kind: str = "int", decimals: int = 1, unit: str = "") -> None:
    """Register one number. `label` is the Spanish description shown in tables; `source` where it came from."""
    if key in NUMBERS:
        raise KeyError(f"duplicated key {key}")
    text = fmt(value, kind, decimals) + (f" {unit}" if unit else "")
    NUMBERS[key] = {"value": value, "text": text, "label": label, "source": source}


def read_csv(rel: str) -> list[dict]:
    with open(ROOT / rel, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def flag(v: str) -> int:
    """Seed booleans are written 'true'/'false'."""
    return 1 if v.strip().lower() in ("true", "1", "t") else 0


def read_yaml(rel: str) -> dict:
    with open(ROOT / rel, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ----------------------------------------------------------------------------------------------------------------
# 1. Seed (database/seed)
# ----------------------------------------------------------------------------------------------------------------
def seed() -> None:
    tables = {
        "districts": "alcaldías", "institutions": "instituciones cliente (ficticias)", "services": "servicios del catálogo",
        "subscription_plans": "planes de suscripción", "persons": "personas sintéticas de 60 años o más",
        "patients": "pacientes", "family_members": "familiares", "consents": "consentimientos",
        "caregivers": "personas del personal (cuidado, enfermería, terapia, medicina)", "caregiver_skills": "habilidades del personal",
        "users": "cuentas de demostración", "care_plans": "planes de cuidado",
        "service_requests": "solicitudes del historial", "assignments": "asignaciones del historial",
        "institution_services": "servicios activos por institución",
    }
    for table, label in tables.items():
        rows = read_csv(f"database/seed/{table}.csv")
        add(f"seed.{table}", len(rows), f"Semilla: {label}", f"database/seed/{table}.csv (filas)")

    districts = read_csv("database/seed/districts.csv")
    add("seed.pop60_cdmx", sum(int(d["population_60_plus_2020"]) for d in districts),
        "Personas de 60 años o más en la CDMX (Censo 2020)", "database/seed/districts.csv, suma de population_60_plus_2020")

    users = read_csv("database/seed/users.csv")
    for role, n in Counter(u["role"] for u in users).items():
        add(f"seed.users_{role}", n, f"Cuentas de demostración con rol {role}", "database/seed/users.csv")

    req = read_csv("database/seed/service_requests.csv")
    st = Counter(r["status"] for r in req)
    add("seed.requests_unattended", st["unattended"], "Solicitudes del historial sin atender", "database/seed/service_requests.csv, status")
    add("seed.requests_unattended_pct", 100 * st["unattended"] / len(req), "Solicitudes del historial sin atender (%)",
        "database/seed/service_requests.csv, status", kind="pct")
    add("seed.requests_cancelled", st["cancelled"], "Solicitudes del historial canceladas", "database/seed/service_requests.csv, status")
    days = {r["scheduled_for"][:10] for r in req}
    add("seed.history_days", len(days), "Días de historial en la semilla", "database/seed/service_requests.csv, fechas distintas")
    add("seed.requests_per_day", len(req) / len(days), "Solicitudes por día en el historial (promedio)",
        "database/seed/service_requests.csv", kind="dec", decimals=0)

    asg = read_csv("database/seed/assignments.csv")
    ap = Counter(a["approval"] for a in asg)
    add("seed.assign_auto", ap.get("auto", 0), "Asignaciones automáticas del historial", "database/seed/assignments.csv, approval")
    add("seed.assign_coordinator", ap.get("coordinator", 0), "Asignaciones aprobadas por coordinación en el historial",
        "database/seed/assignments.csv, approval")

    for plan in read_csv("database/seed/subscription_plans.csv"):
        add(f"seed.plan_limit_{plan['plan_id']}", int(plan["patient_limit"]) if plan["patient_limit"] else "sin límite",
            f"Límite de pacientes del plan {plan['name']}", "database/seed/subscription_plans.csv")
    from datetime import datetime as _dt
    sched = {r["request_id"]: r["scheduled_for"] for r in req}
    arrived = [a for a in asg if a["arrived_at"]]
    on_time = sum(1 for a in arrived
                  if round((_dt.fromisoformat(a["arrived_at"][:19]) - _dt.fromisoformat(sched[a["request_id"]][:19])).total_seconds() / 60) <= 15)
    add("seed.punctual_pct", 100 * on_time / len(arrived), "Historial: llegadas a más tardar 15 min después de la hora (línea base)",
        "database/seed/assignments.csv + service_requests.csv", kind="pct")
    persons = read_csv("database/seed/persons.csv")
    n = len(persons)
    chronic = ["diabetes", "hypertension", "high_cholesterol", "heart_disease", "stroke", "kidney_disease",
               "arthritis", "chronic_lung_disease", "cancer"]
    broad = sum(1 for p in persons
                if sum(flag(p[c]) for c in chronic) + flag(p["obesity"]) + flag(p["depressive_symptoms"]) >= 2)
    add("seed.broad_multimorbidity_pct", 100 * broad / n, "Multimorbilidad amplia en la población sintética",
        "database/seed/persons.csv (2+ de 9 crónicas + obesidad + síntomas depresivos)", kind="pct")
    women = sum(1 for p in persons if p["sex"] == "F")
    add("seed.women_pct", 100 * women / n, "Mujeres en la población sintética", "database/seed/persons.csv, sex", kind="pct")
    for cond, label in [("hypertension", "hipertensión"), ("diabetes", "diabetes")]:
        add(f"seed.{cond}_pct", 100 * sum(flag(p[cond]) for p in persons) / n, f"Prevalencia sintética de {label}",
            f"database/seed/persons.csv, {cond}", kind="pct")

    cg = read_csv("database/seed/caregivers.csv")
    for typ, k in Counter(c["type"] for c in cg).items():
        add(f"seed.caregivers_{typ}", k, f"Personal de tipo {typ}", "database/seed/caregivers.csv, type")
    add("seed.night_12h", sum(1 for c in cg if c["shift_start"][:5] == "20:00" and c["shift_end"][:5] == "08:00"),
        "Personas con turno nocturno de 12 h (20:00–08:00)", "database/seed/caregivers.csv")
    pat = read_csv("database/seed/patients.csv")
    for ins, k in Counter(p["institution_id"] for p in pat).items():
        add(f"seed.patients_{ins.replace('-', '_')}", k, f"Pacientes de {ins}", "database/seed/patients.csv")


# ----------------------------------------------------------------------------------------------------------------
# 2. Live database (as vela_api, the same role the API uses)
# ----------------------------------------------------------------------------------------------------------------
def database() -> None:
    url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
    if not url:
        print("AVISO: sin DATABASE_URL; se omiten los números de la base", file=sys.stderr)
        return
    import psycopg2

    conn = psycopg2.connect(url)
    src = "consulta en vivo como vela_api (docs/biblia/build/collect_numbers.py)"
    with conn, conn.cursor() as cur:
        def count(setting: str | None, table: str) -> int:
            cur.execute("BEGIN")
            if setting is not None:
                cur.execute("SELECT set_config('app.institution_id', %s, true)", (setting,))
            cur.execute(f"SELECT count(*) FROM {table}")  # table names are constants of this script
            value = cur.fetchone()[0]
            cur.execute("ROLLBACK")
            return value

        add("db.rls_patients_none", count(None, "patients"), "Pacientes que ve la API sin institución en la sesión", src)
        add("db.rls_patients_insa", count("INS-A", "patients"), "Pacientes que ve la API con INS-A", src)
        add("db.rls_patients_all", count("*", "patients"), "Pacientes que ve la API con '*' (Dirección)", src)
        add("db.rls_vpatients_none", count(None, "v_patients"), "Fichas en la vista v_patients sin institución", src)
        add("db.rls_persons_none", count(None, "v_persons"), "Personas en v_persons sin institución", src)

        cur.execute("BEGIN")
        cur.execute("SELECT set_config('app.institution_id', '*', true)")
        cur.execute("""SELECT count(*) FROM pg_tables t WHERE schemaname = 'public' AND rowsecurity""")
        add("db.tables_with_rls", cur.fetchone()[0], "Tablas con seguridad por fila activada", "pg_tables.rowsecurity")
        cur.execute("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
        add("db.tables_total", cur.fetchone()[0], "Tablas en el esquema public", "pg_tables")
        cur.execute("SELECT count(*) FROM pg_views WHERE schemaname = 'public'")
        add("db.views_total", cur.fetchone()[0], "Vistas en el esquema public", "pg_views")
        cur.execute("SELECT count(*) FROM air_quality_readings")
        add("db.air_readings", cur.fetchone()[0], "Lecturas de calidad del aire en la base", "air_quality_readings")
        cur.execute("SELECT count(*) FROM air_quality_stations")
        add("db.air_stations", cur.fetchone()[0], "Estaciones de monitoreo del aire", "air_quality_stations")
        cur.execute("SELECT version_num FROM alembic_version")
        add("db.alembic_head", cur.fetchone()[0], "Última migración aplicada", "alembic_version")
        cur.execute("ROLLBACK")
    conn.close()
    migrations = sorted((ROOT / "backend/migrations/versions").glob("0*.py"))
    add("repo.migrations", len(migrations), "Migraciones de Alembic", "backend/migrations/versions")


# ----------------------------------------------------------------------------------------------------------------
# 3. Configuration shared by the operation and SIRAG-D
# ----------------------------------------------------------------------------------------------------------------
def config() -> None:
    sim = read_yaml("config/simulation.yaml")
    src = "config/simulation.yaml"
    ap, dp = sim["approval"], sim["dispatch"]
    add("cfg.auto_apply_after", ap["auto_apply_after_minutes"], "Minutos de espera antes de «aprobada por tiempo»",
        f"{src} approval.auto_apply_after_minutes", unit="min")
    add("cfg.urgent_within", ap["urgent_within_minutes"], "Una solicitud alta es urgente si la visita es en menos de",
        f"{src} approval.urgent_within_minutes", unit="min")
    add("cfg.hold_minutes", ap["hold_minutes"], "Duración de la reserva de una propuesta", f"{src} approval.hold_minutes", unit="min")
    add("cfg.late_tolerance", dp["late_tolerance_minutes"], "Tolerancia de inicio tardío de una visita",
        f"{src} dispatch.late_tolerance_minutes", unit="min")
    add("cfg.not_closed_after", dp["not_closed_after_minutes"], "Minutos tras el fin planeado para marcar «No cerrada»",
        f"{src} dispatch.not_closed_after_minutes", unit="min")
    add("cfg.workdays", sim["staffing"]["workdays_per_week"], "Días laborables por semana (LFT art. 69)",
        f"{src} staffing.workdays_per_week")
    add("cfg.circuity", sim["traffic"]["road_circuity_factor"], "Factor de circuidad (línea recta → calle)",
        f"{src} traffic.road_circuity_factor", kind="dec")
    ex = sim["experiments"]
    add("cfg.replications", ex["replications"], "Réplicas por combinación en SIRAG-D", f"{src} experiments.replications")
    add("cfg.horizon_days", ex["horizon_days"], "Días simulados por réplica", f"{src} experiments.horizon_days")
    add("cfg.confidence", 100 * ex["confidence_level"], "Nivel de confianza de los intervalos",
        f"{src} experiments.confidence_level", kind="pct", decimals=0)
    add("cfg.policies", len(sim["dispatch_policies"]), "Políticas de despacho comparadas", f"{src} dispatch_policies")
    add("cfg.pm25_phase1", sim["contingency"]["thresholds"]["pm25_phase1_ugm3_24h_avg"],
        "Umbral de Fase I por PM2.5 (promedio 24 h)", f"{src} contingency.thresholds", kind="dec", unit="µg/m³")
    lo, hi = sim["human_dispatcher_delay_minutes"]
    add("cfg.human_delay", f"{lo}–{hi}", "Retraso del despacho humano (supuesto)", f"{src} human_dispatcher_delay_minutes", unit="min")

    hm = sim["health_markov"]
    for k, v in hm["base_transition_per_hour"].items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            add(f"cfg.markov_{k}", v, f"Probabilidad por hora {k.replace('_', ' ')} (supuesto)", f"{src} health_markov", kind="dec",
                decimals=4 if v < 0.01 else 2)
    for k, v in hm["risk_multipliers"].items():
        add(f"cfg.mult_{k}", v, f"Multiplicador de riesgo: {k} (supuesto)", f"{src} health_markov.risk_multipliers", kind="dec", decimals=2)
    add("cfg.risk_medium_from", hm["risk_levels"]["medium_from"], "Riesgo «medio» desde (supuesto)", src, kind="dec")
    add("cfg.risk_high_from", hm["risk_levels"]["high_from"], "Riesgo «alto» desde (supuesto)", src, kind="dec")
    for k, v in hm["pollution_effects"].items():
        if isinstance(v, (int, float)):
            add(f"cfg.pm_{k}", 100 * v, f"Aumento por +10 µg/m³ de PM2.5: {k}", f"{src} health_markov.pollution_effects", kind="pct",
                decimals=2)
    th = sim["contingency"]["thresholds"]
    add("cfg.o3_phase1", th["o3_phase1_ppb_1h"], "Umbral de Fase I por ozono (1 h)", f"{src} contingency.thresholds", unit="ppb")
    add("cfg.watch_pct", 100 * th["watch_fraction"], "Vigilancia: porcentaje del umbral (supuesto)", f"{src} contingency.thresholds",
        kind="pct", decimals=0)
    add("cfg.detect_every", sim["contingency"]["detection_interval_minutes"], "Intervalo de detección configurado",
        f"{src} contingency", unit="min")
    sc = sim["scenarios"]
    add("cfg.sac_target", sc["contingency_east"]["pm25_targets_ugm3"]["SAC"], "PM2.5 objetivo en la estación SAC (escenario)",
        f"{src} scenarios.contingency_east", unit="µg/m³")
    add("cfg.ramp", sc["contingency_east"]["ramp_minutes"], "Rampa del escenario de contingencia", f"{src} scenarios", unit="min")
    add("cfg.scenario_hours", sc["contingency_east"]["duration_hours"], "Duración del escenario de contingencia", f"{src} scenarios",
        unit="h")
    add("cfg.roadblock_factor", sc["contingency_east_roadblocks"]["extra_traffic_factor"], "Factor de tráfico con bloqueo (supuesto)",
        f"{src} scenarios", kind="dec", decimals=2)
    add("cfg.blockade_minutes", sim["traffic"]["blockade_extra_minutes"], "Minutos extra por viaje que cruza el bloqueo (supuesto)",
        f"{src} traffic", unit="min")

    rules = read_yaml("config/emergency_rules.yaml")
    cats = rules["categories"]
    add("cfg.emergency_categories", len(cats), "Categorías de signos de alarma (reglas de Enlaza Voz)",
        "config/emergency_rules.yaml categories")
    add("cfg.emergency_patterns", sum(len(c["patterns"]) for c in cats.values()), "Patrones de texto de las reglas de emergencia",
        "config/emergency_rules.yaml categories.*.patterns")
    co = rules.get("classifier_only", {})
    if "escalate_after_minutes" in co:
        add("cfg.escalate_after", co["escalate_after_minutes"], "Minutos para escalar a Dirección una alerta solo del clasificador",
            "config/emergency_rules.yaml classifier_only.escalate_after_minutes", unit="min")


# ----------------------------------------------------------------------------------------------------------------
# 4. SIRAG-D results
# ----------------------------------------------------------------------------------------------------------------
def simulation() -> None:
    info = json.loads((ROOT / "simulation/results/run_info.json").read_text(encoding="utf-8"))
    src = "simulation/results/run_info.json"
    add("sim.runs_main", info["runs_main"], "Corridas principales de SIRAG-D", src)
    add("sim.runs_sensitivity", info["runs_sensitivity"], "Corridas de sensibilidad", src)
    add("sim.runs_validation", info["runs_validation"], "Corridas de validación", src)
    add("sim.elapsed_s", info["elapsed_seconds"], "Segundos que tardó toda la experimentación", src, kind="dec", decimals=0)
    add("sim.workers", info["workers"], "Procesos en paralelo", src)

    v = read_csv("simulation/results/validation.csv")[0]
    vs = "simulation/results/validation.csv"
    add("sim.val_real_pct", float(v["pct_all"]), "Historial: solicitudes sin atender (%)", vs, kind="pct")
    add("sim.val_real_nocancel_pct", float(v["pct_without_cancelled"]), "Historial: sin atender, sin contar cancelaciones (%)", vs,
        kind="pct")
    add("sim.val_real_short_pct", float(v["pct_short_services"]), "Historial: sin atender, servicios cortos (%)", vs, kind="pct")
    add("sim.val_sim_short_pct", float(v["sim_short_mean"]), "Simulación: sin atender, servicios cortos (%)", vs, kind="pct")
    add("sim.val_sim_short_ci", f"{float(v['sim_short_ci_low']):.1f}–{float(v['sim_short_ci_high']):.1f} %",
        "Simulación: IC 95 % de servicios cortos sin atender", vs)

    summary = read_csv("simulation/results/summary.csv")
    ss = "simulation/results/summary.csv"
    names = {"human_dispatcher": "despacho humano", "nearest": "más cercano", "risk_priority": "prioridad por riesgo",
             "risk_plus_live_traffic": "Enlaza (riesgo + tráfico)", "vela_timeout": "Enlaza con límite de tiempo"}
    for r in summary:
        key = f"sim.{r['scenario']}.{r['policy']}.{r['metric']}"
        kind = "pct" if r["metric"].endswith("_pct") else "dec"
        add(key, float(r["mean"]), f"{r['metric']} · {names.get(r['policy'], r['policy'])} · {r['scenario']}", ss, kind=kind)
        add(key + ".ci", f"{float(r['ci_low']):.1f}–{float(r['ci_high']):.1f}",
            f"IC 95 % de {r['metric']} · {names.get(r['policy'], r['policy'])} · {r['scenario']}", ss)


def pfmt(p: float) -> str:
    """p-value as printed in the bible."""
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def simulation_more() -> None:
    """Sensitivity, statistical tests, holds check, contingency window (SIRAG-D)."""
    names = {"human_dispatcher": "despacho humano", "nearest": "más cercano", "risk_priority": "prioridad por riesgo",
             "risk_plus_live_traffic": "Enlaza sin límite de tiempo", "vela_timeout": "Enlaza (como opera hoy)"}
    src = "simulation/results/sensitivity.csv"
    for r in read_csv(src):
        level = r["approval_delay"] or r["risk_multiplier"] or r["extra_staff"]
        level = level.replace(".0", "")
        key = f"sens.{r['knob']}.{level}.{r['policy']}.{r['metric']}"
        kind = "pct" if r["metric"].endswith("_pct") else ("int" if r["metric"] == "staff" else "dec")
        add(key, float(r["mean"]), f"Sensibilidad {r['knob']}={level}: {r['metric']} · {names.get(r['policy'])}", src, kind=kind)
        add(key + ".ci", f"{float(r['ci_low']):.1f}–{float(r['ci_high']):.1f}", f"IC 95 % de {key}", src)
        if r["approval_delay"] and "-" in level and f"sens.approval_delay.{level}.label" not in NUMBERS:  # "5-15" -> "5–15 min"
            lo, hi = level.split("-")
            add(f"sens.approval_delay.{level}.label", f"{lo}–{hi} min", "Nivel de retraso de la aprobación en la sensibilidad", src)

    for fname, prefix in (("tests.csv", "test"), ("sensitivity_tests.csv", "senstest")):
        src = f"simulation/results/{fname}"
        for r in read_csv(src):
            base = f"{prefix}.{r['scenario']}.{r['metric']}"
            if prefix == "senstest":
                base = f"{prefix}.{r['knob']}.{r['level'].replace('.0', '')}.{r['metric']}"
            add(base + ".omnibus", f"{r['omnibus']} ({pfmt(float(r['omnibus_p']))})", f"Prueba global {base}", src)
            add(base + ".pairwise", r["pairwise_test"], f"Prueba por pares {base}", src)
            for pol in ("nearest", "risk_priority", "risk_plus_live_traffic", "vela_timeout"):
                if r.get(f"{pol}_diff_mean", "") == "":
                    continue
                add(f"{base}.{pol}.diff", float(r[f"{pol}_diff_mean"]), f"Diferencia media vs. despacho humano: {base} · {names[pol]}",
                    src, kind="dec", decimals=1)
                add(f"{base}.{pol}.p", pfmt(float(r[f"{pol}_p_holm"])), f"p con Holm: {base} · {names[pol]}", src)

    src = "simulation/results/holds_check.csv"
    for r in read_csv(src):
        kind = "pct" if r["metric"].endswith("_pct") else "dec"
        add(f"holds.{r['metric']}.with", float(r["with_holds"]), f"{r['metric']} con reserva", src, kind=kind)
        add(f"holds.{r['metric']}.without", float(r["without_holds"]), f"{r['metric']} sin reserva", src, kind=kind)
        add(f"holds.{r['metric']}.p", pfmt(float(r["p_holm"])), f"p con Holm, reserva: {r['metric']}", src)

    src = "simulation/results/contingency_effect.csv"
    for r in read_csv(src):
        for k in ("at_risk_entries", "win_at_risk_entries", "crises", "win_crises"):
            add(f"ceff.{r['scenario']}.{k}", int(r[k]), f"{k} (30 semanas) · {r['scenario']}", src)

    src = "simulation/results/window.csv"
    for r in read_csv(src):
        kind = "pct" if r["metric"].endswith("_pct") else "dec"
        add(f"win.{r['scenario']}.{r['policy']}.{r['metric']}", float(r["mean"]),
            f"Ventana de contingencia: {r['metric']} · {names.get(r['policy'])} · {r['scenario']}", src, kind=kind)


# ----------------------------------------------------------------------------------------------------------------
# 5. Enlaza Voz evaluation
# ----------------------------------------------------------------------------------------------------------------
def voice() -> None:
    m = json.loads((ROOT / "voice/eval/results/metrics.json").read_text(encoding="utf-8"))
    src = "voice/eval/results/metrics.json"
    names = {"internal_test": "prueba interna", "external": "externa", "holdout": "holdout"}
    for split, label in names.items():
        d = m.get(split)
        if not d:
            continue
        add(f"voz.{split}.n", d["n"], f"Frases en la evaluación {label}", src)
        add(f"voz.{split}.emergencies", d["emergencies"], f"Emergencias en la evaluación {label}", src)
        add(f"voz.{split}.sens", d["emergency_sensitivity_pct"], f"Sensibilidad a emergencias, {label}", src, kind="pct")
        add(f"voz.{split}.sens_rules", d["emergency_sensitivity_rules_only_pct"],
            f"Sensibilidad solo con reglas, {label}", src, kind="pct")
        add(f"voz.{split}.f1", d["macro_f1"], f"F1 macro, {label}", src, kind="dec", decimals=3)
        add(f"voz.{split}.fa100", d["false_alarms_per_100_notes"], f"Falsas alarmas por 100 notas, {label}", src, kind="dec")
        add(f"voz.{split}.missed", len(d.get("missed_emergencies", [])), f"Emergencias no detectadas, {label}", src)
        cm = d["confusion_matrix"]["values"]
        labs = ["routine", "urgent", "emergency"]
        for i, t in enumerate(labs):
            for j, p_ in enumerate(labs):
                add(f"vozcm.{split}.{t}.{p_}", cm[i][j], f"Matriz de confusión {label}: real {t}, predicho {p_}", src)


# ----------------------------------------------------------------------------------------------------------------
# 6. Business assumptions (each row carries its own source)
# ----------------------------------------------------------------------------------------------------------------
def calibration() -> None:
    """Synthetic population vs the official references it was calibrated with."""
    persons = read_csv("database/seed/persons.csv")
    n = len(persons)
    ref = read_csv("data/reference/prevalence_reference.csv")
    chronic = ["diabetes", "hypertension", "high_cholesterol", "heart_disease", "stroke", "kidney_disease",
               "arthritis", "chronic_lung_disease", "cancer"]
    names = {"diabetes": "diabetes", "hypertension": "hipertensión", "high_cholesterol": "colesterol alto",
             "heart_disease": "enfermedad del corazón", "stroke": "embolia (EVC)", "kidney_disease": "enfermedad renal",
             "depressive_symptoms": "síntomas depresivos", "fall_last_12m": "caída en 12 meses", "frailty": "fragilidad",
             "obesity": "obesidad", "arthritis": "artritis", "chronic_lung_disease": "enfermedad pulmonar crónica",
             "cancer": "cáncer", "multimorbidity": "multimorbilidad"}
    for r in ref:
        c = r["condition"]
        add(f"cal.ref_{c}", float(r["reference_pct"]), f"Referencia oficial: {names.get(c, c)} ({r['survey']})",
            f"data/reference/prevalence_reference.csv · {r['survey']}", kind="pct")
        if c in persons[0]:
            add(f"cal.syn_{c}", 100 * sum(flag(p[c]) for p in persons) / n, f"Población sintética: {names.get(c, c)}",
                f"database/seed/persons.csv, {c}", kind="pct")
    dep = Counter(p["dependency_level"] for p in persons)
    pats = {p["person_id"] for p in read_csv("database/seed/patients.csv")}
    dep_p = Counter(p["dependency_level"] for p in persons if p["person_id"] in pats)
    for level in dep:
        k = slug_ascii(level)
        add(f"cal.dep_pop_{k}", 100 * dep[level] / n, f"Dependencia «{level}» en la población sintética",
            "database/seed/persons.csv, dependency_level", kind="pct")
        add(f"cal.dep_pat_{k}", 100 * dep_p[level] / len(pats), f"Dependencia «{level}» entre los pacientes",
            "database/seed/persons.csv + patients.csv", kind="pct")
    ages = [2026 - int(p["birth_date"][:4]) for p in persons]
    add("cal.pct_80plus", 100 * sum(a >= 80 for a in ages) / n, "Personas de 80 años o más (aprox., por año de nacimiento)",
        "database/seed/persons.csv, birth_date", kind="pct")
    ages_p = [2026 - int(p["birth_date"][:4]) for p in persons if p["person_id"] in pats]
    add("cal.pct_80plus_patients", 100 * sum(a >= 80 for a in ages_p) / len(ages_p), "Pacientes de 80 años o más (aprox.)",
        "database/seed/persons.csv + patients.csv", kind="pct")

    traffic = read_csv("data/reference/traffic_hourly_profile.csv")
    wk = [t for t in traffic if t["day_type"] == "weekday"]
    peak = max(wk, key=lambda t: float(t["congestion_pct"]))
    add("ref.traffic_peak_congestion", float(peak["congestion_pct"]), f"Congestión máxima en día laborable ({peak['hour']} h)",
        "data/reference/traffic_hourly_profile.csv (TomTom Traffic Index 2025)", kind="pct")
    add("ref.traffic_peak_speed", float(peak["avg_speed_kmh"]), "Velocidad promedio en la hora más congestionada",
        "data/reference/traffic_hourly_profile.csv (TomTom Traffic Index 2025)", kind="dec", unit="km/h")
    add("ref.traffic_free_speed", float(peak["free_flow_speed_kmh"]), "Velocidad sin tráfico (flujo libre)",
        "data/reference/traffic_hourly_profile.csv", kind="dec", unit="km/h")
    day = [float(t["congestion_pct"]) for t in wk if 6 <= int(t["hour"]) <= 22]
    add("ref.traffic_day_mean", sum(day) / len(day), "Congestión promedio de 6 a 22 h, día laborable (calibrada al índice TomTom)",
        "data/reference/traffic_hourly_profile.csv; calibración en data/generator/build_reference_data.py", kind="pct")
    add("ref.traffic_rows", len(traffic), "Filas del perfil de tráfico (24 h × laborable/fin de semana)",
        "data/reference/traffic_hourly_profile.csv")

    air = read_csv("data/reference/air_quality_hourly.csv")
    add("ref.air_rows", len(air), "Lecturas horarias de aire en el archivo calibrado", "data/reference/air_quality_hourly.csv")
    add("ref.air_o3_max", max(float(a["o3_ppb"]) for a in air), "Ozono máximo horario de la red (serie calibrada)",
        "data/reference/air_quality_hourly.csv", kind="dec", decimals=0, unit="ppb")
    add("ref.air_pm25_max", max(float(a["pm25_ugm3"]) for a in air), "PM2.5 máximo horario (serie calibrada)",
        "data/reference/air_quality_hourly.csv", kind="dec", decimals=0, unit="µg/m³")
    add("ref.air_stations", len(read_csv("data/reference/air_quality_stations.csv")), "Estaciones de monitoreo (archivo)",
        "data/reference/air_quality_stations.csv")

    for f, label in [("triage_phrases", "Frases de entrenamiento y prueba interna"), ("external_phrases", "Frases externas"),
                     ("holdout_phrases", "Frases holdout")]:
        add(f"ref.{f}", len(read_csv(f"data/voice/{f}.csv")), f"{label} de Enlaza Voz", f"data/voice/{f}.csv")


def generator() -> None:
    """Constants of the synthetic-data generator and the planned overlaps of the seed history."""
    import re
    from datetime import datetime, timedelta
    rel = "data/generator/legacy_es/generar_base.py"
    src = (ROOT / rel).read_text(encoding="utf-8")

    def grab(pattern: str) -> float:
        return float(re.search(pattern, src).group(1))
    add("gen.seed", str(int(grab(r"SEED = (\d+)"))), "Semilla del generador (siempre los mismos datos)", rel)
    add("gen.load_general", grab(r"a_g = ([\d.]+)"), "Carga del factor común general (cópula)", rel, kind="dec", decimals=2)
    add("gen.load_cardio", grab(r"a_c = ([\d.]+)"), "Carga del factor cardiometabólico (cópula)", rel, kind="dec", decimals=2)
    add("gen.load_functional", grab(r"a_f = ([\d.]+)"), "Carga del factor funcional (cópula)", rel, kind="dec", decimals=2)
    add("gen.enasem_factor", grab(r"factor ([\d.]+) ="), "Factor para llevar la ENASEM a prevalencia poblacional (supuesto)",
        rel, kind="dec", decimals=2)
    add("gen.travel_gap", grab(r"fin \+ (\d+)\s+# \d+ min de traslado"), "Minutos de traslado entre visitas en el historial",
        rel, unit="min")

    # Planned overlaps: same caregiver, windows [scheduled_for, + duration] that cross (docs/dev/decisiones_paso_3.md)
    dur = {s["service_id"]: int(s["duration_min"]) for s in read_csv("database/seed/services.csv")}
    req = {r["request_id"]: r for r in read_csv("database/seed/service_requests.csv")}
    by_cg: dict[str, list] = {}
    for a in read_csv("database/seed/assignments.csv"):
        r = req[a["request_id"]]
        start = datetime.fromisoformat(r["scheduled_for"][:19])   # all seed times are Mexico City (-06)
        by_cg.setdefault(a["caregiver_id"], []).append((start, start + timedelta(minutes=dur[r["service_id"]])))
    pairs = 0
    for wins in by_cg.values():
        wins.sort()
        for i in range(len(wins)):
            for j in range(i + 1, len(wins)):
                if wins[j][0] >= wins[i][1]:
                    break
                pairs += 1
    add("gen.planned_overlaps", pairs, "Pares de visitas del historial que se cruzan con el horario PLANEADO",
        "database/seed/service_requests.csv + assignments.csv + services.csv")


def slug_ascii(text: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower().replace(" ", "_")


def voice_breakdown() -> None:
    """Two-level emergency notice, computed from the per-phrase predictions (voice/eval/results/predictions_*.csv)."""
    for split, fname in (("holdout", "predictions_holdout.csv"), ("external", "predictions_external.csv"),
                         ("internal_test", "predictions_internal_test.csv")):
        src = f"voice/eval/results/{fname}"
        rows = read_csv(src)
        rule = lambda r: r["rule_hits"] not in ("", "[]")
        emerg = [r for r in rows if r["label"] == "emergency"]
        non = [r for r in rows if r["label"] != "emergency"]
        red = [r for r in rows if rule(r)]
        amber = [r for r in rows if not rule(r) and r["final"] == "emergency"]
        items = {
            "non_emergencies": (len(non), "Frases que no son emergencia"),
            "emerg_by_rules": (sum(rule(r) for r in emerg), "Emergencias que detectan las reglas"),
            "emerg_only_classifier": (sum(1 for r in emerg if not rule(r) and r["final"] == "emergency"),
                                      "Emergencias que solo detecta el clasificador"),
            "false_alarms": (sum(1 for r in non if r["final"] == "emergency"), "Falsas alarmas (no era emergencia)"),
            "false_by_rules": (sum(1 for r in non if rule(r)), "Falsas alarmas que vienen de reglas"),
            "false_by_classifier": (sum(1 for r in non if not rule(r) and r["final"] == "emergency"),
                                    "Falsas alarmas que vienen solo del clasificador"),
            "red": (len(red), "Pantallas rojas (se activó una regla)"),
            "red_false": (sum(1 for r in red if r["label"] != "emergency"), "Pantallas rojas falsas"),
            "amber": (len(amber), "Avisos ámbar (solo el clasificador)"),
            "amber_false": (sum(1 for r in amber if r["label"] != "emergency"), "Avisos ámbar falsos"),
            "all_emergency_screens": (len(red) + len(amber), "Pantallas de emergencia si todo fuera rojo"),
        }
        for k, (v, label) in items.items():
            add(f"vozb.{split}.{k}", v, f"{label} · {split}", src)
    src = "voice/eval/results/rules_comparison.csv"
    for r in read_csv(src):
        k = slug_ascii(r["conjunto"]).replace(",", "").replace("__", "_")
        tag = "antes" if r["reglas"] == "antes" else "despues"
        add(f"vozr.{k}.{tag}.sens", float(r["sensitivity_pct"]), f"Solo reglas, {r['conjunto']}, {r['reglas']}: sensibilidad", src, kind="pct")
        add(f"vozr.{k}.{tag}.fa100", float(r["false_alarms_per_100"]), f"Solo reglas, {r['conjunto']}, {r['reglas']}: falsas alarmas/100", src, kind="dec")
    v2 = OUT / "v2_holdout.json"      # written by build_biblia.sh from the unmerged branch feature/voz-clasificador-v2
    if v2.exists():
        d = json.loads(v2.read_text(encoding="utf-8"))
        src2 = "rama feature/voz-clasificador-v2 (sin fusionar): voice/eval/results/v2_holdout.json"
        for model, tag in (("v2_minilm", "v2"), ("v1_active", "v1")):
            m = d[model]
            add(f"vozv2.{tag}.sens", m["emergency_sensitivity_pct"], f"Holdout {tag}: sensibilidad", src2, kind="pct")
            add(f"vozv2.{tag}.fa100", m["false_alarms_per_100_notes"], f"Holdout {tag}: falsas alarmas/100", src2, kind="dec")
            add(f"vozv2.{tag}.f1", m["macro_f1"], f"Holdout {tag}: F1 macro", src2, kind="dec", decimals=3)
            add(f"vozv2.{tag}.missed", len(m["missed_emergencies"]), f"Holdout {tag}: emergencias no detectadas", src2)
            add(f"vozv2.{tag}.ms", m["latency_cpu"]["median_ms"], f"Holdout {tag}: tiempo por nota (mediana)", src2,
                kind="dec", decimals=0, unit="ms")
    review = (ROOT / "voice/eval/results/reports_review.md").read_text(encoding="utf-8")
    add("voz.reports_reviewed", review.count("| ready ("), "Reportes del LLM revisados (criterio A8)", "voice/eval/results/reports_review.md")
    add("voz.reports_clean", review.count("sin frases prohibidas"), "Reportes sin frases prohibidas (filtro automático)",
        "voice/eval/results/reports_review.md")
    tri = read_csv("data/voice/triage_phrases.csv")
    for lab, n in Counter(r["label"] for r in tri).items():
        add(f"voz.phr_{lab}", n, f"Frases internas con nivel {lab}", "data/voice/triage_phrases.csv")
    for sp, n in Counter(r["split"] for r in tri).items():
        add(f"voz.split_{sp}", n, f"Frases internas en el conjunto {sp}", "data/voice/triage_phrases.csv")


def voice_timings() -> None:
    """Measured times of Whisper and the local LLM (voice/eval/timings.py, laptop CPU)."""
    rows = read_csv("voice/eval/results/timings.csv")
    src = "voice/eval/results/timings.csv"
    by = {r["what"]: float(r["seconds"]) for r in rows}
    add("voz.t_whisper_load", by["load whisper small int8"], "Cargar Whisper small (int8)", src, kind="dec", unit="s")
    for n in (10, 30, 60):
        runs = [float(r["seconds"]) for r in rows if r["what"].startswith(f"transcribe ~{n} s")]
        add(f"voz.t_transcribe_{n}", sum(runs) / len(runs), f"Transcribir una nota de ~{n} s (promedio de {len(runs)} corridas)",
            src, kind="dec", unit="s")
    llm = [r for r in rows if r["what"].startswith("LLM report")]
    add("voz.t_llm_short", float(llm[0]["seconds"]), "Reporte del LLM, nota corta", src, kind="dec", unit="s")
    add("voz.t_llm_long", float(llm[-1]["seconds"]), "Reporte del LLM, nota larga", src, kind="dec", unit="s")


def business() -> None:
    rows = read_csv("data/business/assumptions.csv")
    add("neg.assumptions_rows", len(rows), "Supuestos y datos del modelo de negocio", "data/business/assumptions.csv")
    add("neg.assumptions_real", sum(1 for r in rows if r["type"] == "real"), "Datos con fuente real en assumptions.csv",
        "data/business/assumptions.csv, type = real")
    for r in rows:
        try:
            value = float(r["value"])
        except ValueError:
            value = r["value"]
        kind = "int" if isinstance(value, float) and value.is_integer() and abs(value) >= 1 else "dec"
        if isinstance(value, float) and kind == "dec":
            decimals = 2 if abs(value) < 10 else 1
        else:
            decimals = 1
        tag = "" if r["type"] == "real" else " (supuesto)"
        add(f"neg.{r['key']}", value, r["description_es"] + tag, f"assumptions.csv · {r['source']}", kind=kind,
            decimals=decimals)


def business_model() -> None:
    """The same calculation as /negocio: backend/app/services/business_model.py on data/business/assumptions.csv."""
    import importlib.util
    os.environ["BUSINESS_DIR"] = str(ROOT / "data/business")
    spec = importlib.util.spec_from_file_location("business_model", ROOT / "backend/app/services/business_model.py")
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    src = "backend/app/services/business_model.py sobre data/business/assumptions.csv (lo mismo que /negocio)"
    m = bm.model()
    add("bm.arpa1", m["average_revenue_year1"], "Ingreso promedio por institución, año 1 (MXN/mes)", src, kind="money")
    add("bm.fixed1", m["fixed_costs_year1"], "Costo fijo mensual, año 1 (MXN)", src, kind="money")
    add("bm.breakeven_static", m["breakeven_institutions_static"], "Punto de equilibrio: costo fijo ÷ ingreso promedio", src,
        unit="instituciones")
    add("bm.breakeven_month", m["breakeven_month"], "Mes desde el que ya no se pierde dinero", src)
    add("bm.breakeven_year", m["breakeven_year"], "Año del equilibrio mensual", src)
    add("bm.payback_month", m["payback_month"] or "no ocurre", "Mes en que se recupera lo perdido (caja ≥ 0)", src)
    add("bm.investment", m["investment"]["amount"], "Inversión necesaria (punto más bajo de la caja)", src, kind="money")
    add("bm.investment_month", m["investment"]["month"], "Mes de la inversión máxima", src)
    for n in m["npv"]:
        add(f"bm.npv_{int(n['rate_pct'])}", n["npv"], f"VPN a 5 años al {n['rate_pct']:g} %", src, kind="money")
        add(f"bm.rate_{int(n['rate_pct'])}", n["rate_pct"], "Tasa de descuento nominal", src, kind="pct", decimals=0)
    u = m["unit"]
    add("bm.margin", u["margin_month"], "Margen mensual por institución (ingreso − soporte y hospedaje)", src, kind="money")
    add("bm.variable_cost", u["variable_cost_month"], "Costo variable mensual por institución", src, kind="money")
    add("bm.lifetime", u["lifetime_months"], "Vida esperada de un cliente (1 ÷ churn)", src, kind="dec", decimals=0, unit="meses")
    add("bm.ltv", u["ltv"], "LTV (margen × vida, sin descontar)", src, kind="money")
    add("bm.cac", u["cac"], "CAC: costo de conseguir una institución", src, kind="money")
    add("bm.ltv_cac", f"{u['ltv_cac']:.1f} : 1", "LTV / CAC", src)
    add("bm.cac_payback", u["cac_payback_months"], "Meses para recuperar el CAC", src, kind="dec", unit="meses")
    for y in m["years"]:
        add(f"bm.y{y['year']}.customers", y["customers_end"], f"Instituciones al cierre del año {y['year']} (base)", src,
            kind="dec", decimals=0)
        add(f"bm.y{y['year']}.profit", y["profit"], f"Utilidad del año {y['year']} (base)", src, kind="money")
    w = bm.what_for_npv_zero()
    add("bm.zero_price", w["plan_professional_price"], "Precio Profesional que haría el VPN base = 0", src, kind="money")
    add("bm.zero_year5", w["customers_year5"], "Instituciones en el año 5 que harían el VPN base = 0", src, kind="dec", decimals=0)
    add("bm.zero_cac", w["cac"], "CAC que haría el VPN base = 0", src, kind="money")
    sc = bm.scenarios()
    for name, label in (("base", "base"), ("conservative", "conservador"), ("recommended", "recomendado")):
        d = sc[name]
        add(f"bm.sc.{name}.investment", d["investment"]["amount"], f"Escenario {label}: inversión necesaria", src, kind="money")
        add(f"bm.sc.{name}.breakeven", d["breakeven_month"] or "no ocurre", f"Escenario {label}: mes de equilibrio", src)
        add(f"bm.sc.{name}.payback", d["payback_month"] or "no ocurre", f"Escenario {label}: mes en que recupera lo perdido", src)
        add(f"bm.sc.{name}.npv25", d["npv"][1]["npv"], f"Escenario {label}: VPN al {d['npv'][1]['rate_pct']:g} %", src, kind="money")
        add(f"bm.sc.{name}.customers5", d["customers_year5"], f"Escenario {label}: instituciones en el año 5", src,
            kind="dec", decimals=0)
        for region, sh in d["shares"].items():
            if sh["share_pct"] is not None:
                add(f"bm.sc.{name}.share_{region}", sh["share_pct"], f"Escenario {label}: participación privada en {region}, año 5",
                    src, kind="pct")
    add("bm.sc.recommended.gov5", sc["recommended"]["government_year5"], "Recomendado: centros públicos (plan Gobierno), año 5",
        src, kind="dec", decimals=0)
    # TIR (tasa interna de retorno): the annual rate at which the 5-year NPV is exactly 0 (same npv() as /negocio)
    def irr(rows):
        lo, hi = -90.0, 500.0
        f = lambda r: bm.npv(rows, r)
        if f(lo) * f(hi) > 0:
            return None
        for _ in range(100):
            mid = (lo + hi) / 2
            if (f(mid) > 0) == (f(lo) > 0):
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    v = bm.inputs()
    f_ = v["conservative_customer_factor"] / 100
    totals = [v["customers_year1"], *bm._targets(v["customer_growth_year2_5"])]
    cons = bm.inputs({"customers_year1": totals[0] * f_,
                      "customer_growth_year2_5": ",".join(str(round(x * f_, 4)) for x in totals[1:])})
    for name, label, rows in (("base", "base", bm.simulate(v)), ("conservative", "conservador", bm.simulate(cons)),
                              ("recommended", "recomendado", bm.simulate_recommended(v))):
        r = irr(rows)
        add(f"bm.sc.{name}.tir", r if r is not None else "no existe (el flujo nunca se vuelve positivo)",
            f"Escenario {label}: TIR anual a 5 años", src + "; TIR = tasa con VPN 0", kind="pct")
    plans = {r["plan_id"]: r for r in read_csv("database/seed/subscription_plans.csv")}
    for pid, key in (("basic", "plan_basic_price"), ("professional", "plan_professional_price")):
        price = float(v[key]); limit = float(plans[pid]["patient_limit"])
        add(f"bm.per_patient_{pid}", price / limit, f"Costo mensual por paciente con el plan {plans[pid]['name']} lleno",
            "precio del plan (assumptions.csv) ÷ límite de pacientes (subscription_plans.csv)", kind="money")
    rw = sc["recommended_without"]
    add("bm.rec_wo_gov", rw["government"], "Recomendado sin plan Gobierno: VPN 25 %", src, kind="money")
    add("bm.rec_wo_cut", rw["founder_cut"], "Recomendado sin recorte a fundadores: VPN 25 %", src, kind="money")
    add("bm.rec_wo_both", rw["both"], "Recomendado sin ninguno de los dos: VPN 25 %", src, kind="money")


# ----------------------------------------------------------------------------------------------------------------
# 7. Manual measurements (made once by a person; the file says when and where it is documented)
# ----------------------------------------------------------------------------------------------------------------
def manual() -> None:
    path = ROOT / "docs/biblia/datos/mediciones_manuales.yaml"
    for key, d in (read_yaml(str(path.relative_to(ROOT))) or {}).items():
        add(f"man.{key}", d["valor"], d["descripcion"], f"medición manual, {d['fecha']} ({d['documento']})")


def history() -> None:
    """Results of earlier runs that explain team decisions (docs/biblia/datos/historico.yaml)."""
    for key, d in (read_yaml("docs/biblia/datos/historico.yaml") or {}).items():
        add(f"hist.{key}", d["valor"], d["descripcion"] + " (histórico)", f"histórico, {d['fecha']} ({d['documento']})")


def git_history() -> None:
    """Commits and merged pull requests on main (out/git_main.txt, written by build_biblia.sh with git log)."""
    import re
    f = OUT / "git_main.txt"
    if not f.exists():
        return
    lines = [l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    prs = [l for l in lines if re.search(r"\(#\d+\)$", l)]
    add("git.commits_main", len(lines), "Commits en la rama main", "git log main (out/git_main.txt)")
    add("git.prs_main", len(prs), "Pull requests fusionados en main", "git log main: commits que terminan en (#N)")
    days = sorted({l[:10] for l in lines})
    add("git.first_day", days[0], "Primer commit en main", "git log main")
    add("git.last_day", days[-1], "Último commit en main", "git log main")


def course_documents() -> None:
    """Figures quoted from the course documents (docs/biblia/datos/problema_prototipico.yaml)."""
    for key, d in (read_yaml("docs/biblia/datos/problema_prototipico.yaml") or {}).items():
        add(f"doc.{key}", d["valor"], d["descripcion"], f"documento del curso: {d['documento']}")


def context() -> None:
    """Official context figures (aging, "why now") with page (docs/biblia/datos/contexto.yaml)."""
    for key, d in (read_yaml("docs/biblia/datos/contexto.yaml") or {}).items():
        add(f"ctx.{key}", d["valor"], d["descripcion"], f"{d['documento']} · {d['url']}")


def repo() -> None:
    """Counts of the repository itself (tests, screens, routers)."""
    tests = list((ROOT / "backend/tests").glob("test_*.py"))
    n_tests = sum(p.read_text(encoding="utf-8").count("\ndef test_") + p.read_text(encoding="utf-8").count("\nasync def test_")
                  for p in tests)
    # pytest runs more tests than there are functions: @pytest.mark.parametrize runs one function once per data set.
    # scripts/build_biblia.sh saves `pytest --collect-only -q` (run inside the api container) to out/pytest_collect.txt.
    collected_file = OUT / "pytest_collect.txt"
    collected = [l.strip() for l in collected_file.read_text(encoding="utf-8").splitlines()] if collected_file.exists() else []
    for t in tests:
        txt = t.read_text(encoding="utf-8")
        funcs = txt.count("\ndef test_") + txt.count("\nasync def test_")
        runs = sum(1 for c in collected if c.startswith(f"tests/{t.name}::"))
        add(f"repo.testfuncs_{t.stem[5:]}", funcs, f"Funciones de prueba en {t.name}", f"backend/tests/{t.name}")
        if collected:
            add(f"repo.tests_{t.stem[5:]}", runs, f"Pruebas que corre pytest en {t.name}",
                "pytest --collect-only (out/pytest_collect.txt)")
    if collected:
        add("repo.pytest_collected", len(collected), "Pruebas del backend que corre pytest",
            "pytest --collect-only -q en el contenedor api (out/pytest_collect.txt)")
    add("repo.backend_test_files", len(tests), "Archivos de pruebas del backend", "backend/tests/test_*.py")
    add("repo.backend_tests", n_tests, "Funciones de prueba del backend (def test_…)", "backend/tests/test_*.py")
    if collected:
        add("repo.tests_summary", f"{len(collected)} pruebas ({n_tests} funciones)",
            "Pruebas del backend: las que corre pytest y las funciones que las definen",
            "pytest --collect-only + backend/tests/test_*.py")
    add("repo.routers", len([p for p in (ROOT / "backend/app/routers").glob("*.py") if p.name != "__init__.py"]),
        "Routers (grupos de rutas) de la API", "backend/app/routers")
    add("repo.services", len([p for p in (ROOT / "backend/app/services").glob("*.py") if p.name != "__init__.py"]),
        "Servicios (reglas de negocio) del backend", "backend/app/services")
    add("repo.pages", len([p for p in (ROOT / "frontend/src/pages").glob("*Page.tsx") if p.name != "PlaceholderPage.tsx"]),
        "Pantallas del frontend", "frontend/src/pages/*Page.tsx")
    es = (ROOT / "frontend/src/i18n/es.ts").read_text(encoding="utf-8")
    add("repo.es_lines", es.count("\n"), "Líneas de textos en español de la interfaz", "frontend/src/i18n/es.ts")


def code() -> None:
    """Constants written in the code (read with a regular expression, so a change in the code shows up here)."""
    import re

    def grab(rel: str, pattern: str) -> float:
        m = re.search(pattern, (ROOT / rel).read_text(encoding="utf-8"))
        if not m:
            raise SystemExit(f"no encontré {pattern!r} en {rel}")
        return float(m.group(1))

    items = [
        ("code.jwt_hours", "backend/app/core/config.py", r"jwt_hours: int = (\d+)", "Horas que dura la sesión (JWT)", "h"),
        ("code.login_attempts", "backend/app/core/config.py", r"login_attempts_per_minute: int = (\d+)",
         "Intentos fallidos de inicio de sesión permitidos por minuto e IP", ""),
        ("code.ws_ping", "backend/app/ws/board.py", r"PING_SECONDS = (\d+)", "Cada cuántos segundos el WebSocket manda ping", "s"),
        ("code.ws_recheck", "backend/app/ws/board.py", r"RECHECK_SECONDS = (\d+)",
         "Cada cuántos segundos el WebSocket vuelve a revisar la sesión", "s"),
        ("code.ws_retry", "frontend/src/lib/useBoardSocket.ts", r"RETRY_MS = (\d+)", "Reintento de conexión del tablero", "ms"),
        ("code.duplicate_window_h", "backend/app/services/operations.py", r"DUPLICATE_WINDOW = timedelta\(hours=(\d+)\)",
         "Ventana para considerar duplicada una solicitud (antes o después)", "h"),
        ("code.max_days_ahead", "backend/app/services/operations.py", r"MAX_DAYS_AHEAD = (\d+)",
         "Días hacia adelante que se puede pedir una visita", "días"),
        ("code.care_plan_release_h", "backend/app/services/care_plans.py", r"RELEASE_BEFORE = timedelta\(hours=(\d+)\)",
         "Horas antes de la visita en que el worker publica la solicitud del plan de cuidado", "h"),
        ("code.small_cell", "backend/migrations/versions/0004_baseline_and_broad_multimorbidity.py", r"HAVING count\(\*\) >= (\d+)",
         "Tamaño mínimo de un grupo en las vistas agregadas (regla de celdas pequeñas)", "personas"),
        ("code.approval_alert", "backend/app/services/queue.py", r"APPROVAL_ALERT_AFTER = timedelta\(minutes=(\d+)\)",
         "Minutos sin aprobar antes de alertar a coordinación (prioridad alta)", "min"),
        ("code.queue_alert", "backend/app/services/queue.py", r"QUEUE_ALERT_AFTER = timedelta\(minutes=(\d+)\)",
         "Minutos sin personal antes de alertar a coordinación", "min"),
        ("code.on_time", "backend/app/routers/panorama.py", r"ON_TIME_MINUTES = (\d+)",
         "Una llegada es «puntual» si es a lo más estos minutos tarde (supuesto)", "min"),
        ("code.close_after_hours", "backend/app/services/contingency.py", r"CLOSE_AFTER_HOURS_BELOW = (\d+)",
         "Lecturas horarias seguidas debajo de vigilancia para cerrar una contingencia", ""),
        ("code.max_day", "backend/app/services/labor.py", r'"diurna": ([\d.]+)', "Jornada diurna máxima (LFT art. 61)", "h"),
        ("code.max_mixed", "backend/app/services/labor.py", r'"mixta": ([\d.]+)', "Jornada mixta máxima (LFT art. 61)", "h"),
        ("code.max_night", "backend/app/services/labor.py", r'"nocturna": ([\d.]+)', "Jornada nocturna máxima (LFT art. 61)", "h"),
        ("code.mixed_night_limit", "backend/app/services/labor.py", r"MIXTA_NIGHT_LIMIT = ([\d.]+)",
         "Horas nocturnas a partir de las que una jornada mixta cuenta como nocturna (art. 60)", "h"),
        ("code.min_ahead", "backend/app/services/care_plans.py", r"MIN_AHEAD = timedelta\(minutes=(\d+)\)",
         "Minutos mínimos de anticipación para publicar una visita del plan", "min"),
        ("code.clock_resync_min", "frontend/src/lib/clock.ts", r"RESYNC_MS = (\d+) \* 60", "Cada cuántos minutos la página resincroniza el reloj", "min"),
        ("code.clock_leeway", "backend/app/core/security.py", r"CLOCK_LEEWAY_SECONDS = (\d+)",
         "Tolerancia de reloj al validar la sesión (por los saltos de WSL2)", "s"),
        ("code.sim_cycle", "simulation/sirag/model.py", r"CYCLE = (\d+)", "Ciclo de despacho en la simulación", "min"),
        ("code.oxygen_window_h", "backend/app/services/contingency.py", r"now\(\) \+ interval '(\d+) hours'",
         "Horas hacia adelante en que se buscan oxigenoterapias para adelantar", "h"),
        ("code.demo_urgent_min", "backend/app/services/contingency.py", r"soon = ops.now\(\) \+ timedelta\(minutes=(\d+)\)",
         "Minutos a los que el panel demo programa la solicitud urgente", "min"),
        ("code.class_weight_emergency", "voice/triage/classifier.py", r"CLASS_WEIGHT = \{0: [\d.]+, 1: [\d.]+, 2: ([\d.]+)\}",
         "Peso de la clase «emergencia» al entrenar (una emergencia omitida cuesta más, supuesto)", ""),
        ("code.class_weight_urgent", "voice/triage/classifier.py", r"CLASS_WEIGHT = \{0: [\d.]+, 1: ([\d.]+),",
         "Peso de la clase «urgente» al entrenar (supuesto)", ""),
        ("code.panorama_days", "backend/app/routers/panorama.py", r"days: int = (\d+)", "Días que muestra Panorama por omisión", "días"),
        ("code.min_visits_rate", "backend/app/routers/panorama.py", r"MIN_VISITS_FOR_RATE = (\d+)",
         "Visitas «Con Enlaza» mínimas para mostrar un porcentaje en Panorama (supuesto del equipo)", "visitas"),
        ("code.worker_tick", "backend/app/worker.py", r"TICK_SECONDS = (\d+)", "Cada cuántos segundos da una vuelta el worker", "s"),
    ]
    for key, rel, pattern, label, unit in items:
        v = grab(rel, pattern)
        add(key, v, label, rel, unit=unit, kind="int" if v.is_integer() else "dec")
    add("code.ws_retry_s", grab("frontend/src/lib/useBoardSocket.ts", r"RETRY_MS = (\d+)") / 1000,
        "Reintento de conexión del tablero", "frontend/src/lib/useBoardSocket.ts (RETRY_MS / 1000)", unit="s")


def main() -> None:
    for step in (seed, calibration, generator, config, simulation, simulation_more, voice, voice_breakdown, voice_timings, business, business_model, manual, history, course_documents, context, git_history, repo, code, database):
        step()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "numeros.json").write_text(json.dumps(NUMBERS, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    with open(OUT / "numeros.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["clave", "texto", "descripcion", "fuente"])
        for k, d in NUMBERS.items():
            w.writerow([k, d["text"], d["label"], d["source"]])
    print(f"{len(NUMBERS)} números → {OUT / 'numeros.json'}")


if __name__ == "__main__":
    main()
