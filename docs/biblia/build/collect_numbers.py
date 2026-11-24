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
        return f"${value:,.0f}"
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


# ----------------------------------------------------------------------------------------------------------------
# 7. Manual measurements (made once by a person; the file says when and where it is documented)
# ----------------------------------------------------------------------------------------------------------------
def manual() -> None:
    path = ROOT / "docs/biblia/datos/mediciones_manuales.yaml"
    for key, d in (read_yaml(str(path.relative_to(ROOT))) or {}).items():
        add(f"man.{key}", d["valor"], d["descripcion"], f"medición manual, {d['fecha']} ({d['documento']})")


def repo() -> None:
    """Counts of the repository itself (tests, screens, routers)."""
    tests = list((ROOT / "backend/tests").glob("test_*.py"))
    n_tests = sum(p.read_text(encoding="utf-8").count("\ndef test_") + p.read_text(encoding="utf-8").count("\nasync def test_")
                  for p in tests)
    for t in tests:
        txt = t.read_text(encoding="utf-8")
        add(f"repo.tests_{t.stem[5:]}", txt.count("\ndef test_") + txt.count("\nasync def test_"),
            f"Pruebas en {t.name}", f"backend/tests/{t.name}")
    add("repo.backend_test_files", len(tests), "Archivos de pruebas del backend", "backend/tests/test_*.py")
    add("repo.backend_tests", n_tests, "Pruebas del backend (funciones test_)", "backend/tests/test_*.py")
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
        ("code.worker_tick", "backend/app/worker.py", r"TICK_SECONDS = (\d+)", "Cada cuántos segundos da una vuelta el worker", "s"),
    ]
    for key, rel, pattern, label, unit in items:
        add(key, grab(rel, pattern), label, rel, unit=unit)
    add("code.ws_retry_s", grab("frontend/src/lib/useBoardSocket.ts", r"RETRY_MS = (\d+)") / 1000,
        "Reintento de conexión del tablero", "frontend/src/lib/useBoardSocket.ts (RETRY_MS / 1000)", unit="s")


def main() -> None:
    for step in (seed, calibration, generator, config, simulation, voice, voice_timings, business, manual, repo, code, database):
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
