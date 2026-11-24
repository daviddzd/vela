"""Build the system seed CSVs (English identifiers) from the generator output (generate_population.py).

Usage: python to_english_seed.py <generator_csv_dir> <output_dir> [<existing_users_csv_with_hashes>]
"""
import os, sys, datetime as dt
import numpy as np
import pandas as pd

SRC, OUT = sys.argv[1], sys.argv[2]
USERS_WITH_HASH = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(2026)
TZ = "-06"

def rd(n):
    return pd.read_csv(os.path.join(SRC, f"{n}.csv"), dtype={"cve_mun": str}, keep_default_na=False, encoding="utf-8-sig")

def save(df, n):
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == bool:
            df[c] = df[c].map({True: "true", False: "false"})
    df.to_csv(os.path.join(OUT, f"{n}.csv"), index=False, encoding="utf-8", lineterminator="\n", na_rep="")
    print(f"{n:24s} {len(df):6d}")

def split_name(full):
    p = full.split()
    return " ".join(p[:-2]), p[-2], p[-1]

def as_bool(s):
    return s.astype(int).astype(bool)

alc = rd("alcaldias"); pob = rd("poblacion_sintetica"); ins = rd("instituciones"); pac = rd("pacientes")
fam = rd("familiares"); con = rd("consentimientos"); cui = rd("cuidadores"); srv = rd("catalogo_servicios")
plan = rd("plan_cuidado"); his = rd("historial_servicios"); usr = rd("usuarios_demo")

# ---------------------------------------------------------------- districts (alcaldías)
district_id = {r.alcaldia: "09" + r.cve_mun.zfill(3) for r in alc.itertuples()}
districts = pd.DataFrame({
    "district_id": alc.alcaldia.map(district_id), "name": alc.alcaldia,
    "population_60_plus_2020": alc.poblacion_60_mas_censo2020.astype(int),
    "lat": alc.lat_aprox, "lon": alc.lon_aprox,
    "indigenous_language_pct": alc.hlin_pct.replace("", None),
})
save(districts, "districts")

# ---------------------------------------------------------------- subscription plans
plans = pd.DataFrame([("basic", "Básico", 50, 2500), ("professional", "Profesional", 150, 6000),
                      ("institutional", "Institucional", None, 12000)],
                     columns=["plan_id", "name", "patient_limit", "monthly_price_mxn"])
plans["patient_limit"] = plans.patient_limit.astype("Int64")
save(plans, "subscription_plans")

# ---------------------------------------------------------------- institutions
INST_TYPE = {"Clínica geriátrica": "clinic", "Asilo / residencia": "residence", "Centro de día": "day_center",
             "Red de cuidado a domicilio": "home_care_network", "Red de cuidado pequeña": "home_care_network"}
institutions = pd.DataFrame({
    "institution_id": ins.institucion_id, "name": ins.nombre, "type": ins.tipo.map(INST_TYPE),
    "district_id": ins.alcaldia.map(district_id), "schedule": ins.horario.map({"Diurno": "day", "24 h": "24h"}),
    "plan_id": ins.plan_suscripcion.map({"Básico": "basic", "Profesional": "professional"}),
    "contract_date": ["2025-03-01", "2025-05-15", "2025-08-01", "2025-09-10", "2026-01-20"],
    "active": True,
})
save(institutions, "institutions")

# ---------------------------------------------------------------- services
SKILL = {"medico": "physician", "enfermeria": "nursing", "terapia": "therapy", "cuidado": "caregiving"}
services = pd.DataFrame({
    "service_id": srv.servicio_id, "name": srv.nombre, "required_skill": srv.habilidad_requerida.map(SKILL),
    "duration_min": srv.duracion_min.astype(int),
    "reference_price_mxn": pd.to_numeric(srv.precio_referencia_mxn.replace("", None)).astype("Int64"),
    "min_price_mxn": pd.to_numeric(srv.precio_min_mxn.replace("", None)).astype("Int64"),
    "max_price_mxn": pd.to_numeric(srv.precio_max_mxn.replace("", None)).astype("Int64"),
})
save(services, "services")
rows = []
for s in services.itertuples():
    for letter in srv.set_index("servicio_id").loc[s.service_id, "instituciones"].split(","):
        rows.append({"institution_id": f"INS-{letter}", "service_id": s.service_id, "duration_min": s.duration_min,
                     "price_mxn": s.reference_price_mxn, "active": True})
save(pd.DataFrame(rows).sort_values(["institution_id", "service_id"]), "institution_services")

# ---------------------------------------------------------------- persons
SEX = {"H": "M", "M": "F"}   # generator uses Spanish H/M; system uses M = male, F = female
MARITAL = {"Casado(a) o en unión": "married_union", "Viudo(a)": "widowed", "Soltero(a)": "single",
           "Divorciado(a) o separado(a)": "divorced_separated"}
INSURANCE = {"IMSS": "imss", "ISSSTE": "issste", "IMSS-Bienestar/INSABI": "imss_bienestar",
             "Privada u otra": "private_other", "Pemex, Defensa o Marina": "pemex_defense_navy",
             "Sin afiliación": "none"}
LANG = {"": None, "Náhuatl": "nahuatl", "Mixteco": "mixtec", "Otomí": "otomi", "Mazateco": "mazatec",
        "Zapoteco": "zapotec", "Mazahua": "mazahua", "Totonaco": "totonac", "Otra": "other"}
COGNITIVE = {"Sin deterioro": "none", "Deterioro cognitivo": "mild_impairment", "Demencia": "dementia"}
DEPENDENCY = {"Independiente": "independent", "Leve": "mild", "Moderada": "moderate", "Severa": "severe"}
CONDITIONS = {"diabetes": "diabetes", "hipertension": "hypertension", "hipercolesterolemia": "high_cholesterol",
              "enf_corazon": "heart_disease", "evc_embolia": "stroke", "enf_renal": "kidney_disease",
              "enf_pulmonar_cronica": "chronic_lung_disease", "artritis": "arthritis", "cancer": "cancer",
              "obesidad": "obesity", "anemia": "anemia", "sintomas_depresivos": "depressive_symptoms",
              "caida_12m": "fall_last_12m", "fragilidad": "frailty", "deterioro_visual": "visual_impairment",
              "deterioro_auditivo": "hearing_impairment", "dif_autocuidado": "selfcare_difficulty",
              "dif_actividades_aut": "iadl_difficulty", "limitacion_discapacidad": "disability_limitation"}
persons = pd.DataFrame({
    "person_id": pob.persona_id, "first_name": pob.nombre, "paternal_surname": pob.apellido_paterno,
    "maternal_surname": pob.apellido_materno, "sex": pob.sexo.map(SEX), "birth_date": pob.fecha_nacimiento,
    "district_id": pob.alcaldia.map(district_id), "lat": pob.lat, "lon": pob.lon,
    "marital_status": pob.estado_civil.map(MARITAL), "health_insurance": pob.afiliacion_salud.map(INSURANCE),
    "indigenous_language": pob.lengua_indigena.map(LANG),
})
for es, en in CONDITIONS.items():
    persons[en] = as_bool(pob[es])
persons["cognitive_status"] = pob.estado_cognitivo.map(COGNITIVE)
persons["dependency_level"] = pob.nivel_dependencia.map(DEPENDENCY)
assert persons.isna().sum().drop("indigenous_language").sum() == 0
save(persons, "persons")

# ---------------------------------------------------------------- patients
PRIORITY = {"Alta": "high", "Media": "medium", "Baja": "low"}
patients = pd.DataFrame({"patient_id": pac.paciente_id, "person_id": pac.persona_id,
                         "institution_id": pac.institucion_id, "admission_date": pac.fecha_alta,
                         "base_priority": pac.prioridad_base.map(PRIORITY), "active": True})
save(patients, "patients")
priority_of = patients.set_index("patient_id").base_priority

# ---------------------------------------------------------------- family members
REL = {"Hija": "daughter", "Hijo": "son", "Esposa/o": "spouse", "Nieta/o": "grandchild",
       "Sobrina/o": "nephew_niece", "Otro familiar": "other"}
nf = fam.nombre.map(split_name)
family = pd.DataFrame({
    "family_member_id": fam.familiar_id, "patient_id": fam.paciente_id, "institution_id": fam.institucion_id,
    "first_name": [x[0] for x in nf], "paternal_surname": [x[1] for x in nf], "maternal_surname": [x[2] for x in nf],
    "relationship": fam.parentesco.map(REL), "is_legal_representative": as_bool(fam.es_representante_legal),
    "can_request_services": as_bool(fam.autorizado_para_solicitar), "email": fam.correo,
})
save(family, "family_members")

# ---------------------------------------------------------------- consents
CTYPE = {"Uso de datos de salud": "health_data", "Atención domiciliaria": "home_care", "Asistente de voz": "voice_assistant"}
ASSENT = {"Sí": "yes", "No": "no", "No pudo expresarse": "unable_to_express", "No aplica": "not_applicable"}
consents = pd.DataFrame({
    "consent_id": con.consentimiento_id, "patient_id": con.paciente_id, "institution_id": con.institucion_id,
    "type": con.tipo.map(CTYPE), "granted": as_bool(con.otorgado),
    "granted_by": con.otorgado_por.map({"Paciente": "patient", "Representante legal": "legal_representative"}),
    "family_member_id": con.familiar_id.replace("", None), "patient_assent": con.asentimiento_paciente.map(ASSENT),
    "signed_on": con.fecha_firma, "expires_on": con.fecha_vencimiento,
})
save(consents, "consents")

# ---------------------------------------------------------------- caregivers
CTYPE_CG = {"Médico": "physician", "Enfermería": "nurse", "Terapeuta": "therapist", "Cuidador": "caregiver"}
SHIFT = {"diurno": "day", "mixto": "mixed", "vespertino": "evening", "nocturno": "night"}
nc = cui.nombre.map(split_name)
caregivers = pd.DataFrame({
    "caregiver_id": cui.cuidador_id, "institution_id": cui.institucion_id,
    "first_name": [x[0] for x in nc], "paternal_surname": [x[1] for x in nc], "maternal_surname": [x[2] for x in nc],
    "type": cui.tipo.map(CTYPE_CG), "shift": cui.turno.map(SHIFT), "shift_start": cui.hora_inicio,
    "shift_end": cui.hora_fin, "base_lat": cui.lat_base, "base_lon": cui.lon_base, "active": True,
})
save(caregivers, "caregivers")
save(pd.DataFrame([(r.cuidador_id, SKILL[h]) for r in cui.itertuples() for h in r.habilidades.split(",")],
                  columns=["caregiver_id", "skill"]), "caregiver_skills")

# ---------------------------------------------------------------- care plans
save(pd.DataFrame({"care_plan_id": plan.plan_id, "patient_id": plan.paciente_id, "institution_id": plan.institucion_id,
                   "service_id": plan.servicio_id, "times_per_week": plan.veces_por_semana,
                   "reason": plan.motivo, "active": True}), "care_plans")

# ---------------------------------------------------------------- users
ROLE = {"Dueño de la plataforma": "owner", "Coordinador(a)": "coordinator", "Médico": "physician",
        "Cuidador(a)": "caregiver", "Familiar": "family"}
users = pd.DataFrame({
    "user_id": usr.usuario_id, "role": usr.rol.map(ROLE), "institution_id": usr.institucion_id.replace("", None),
    "caregiver_id": [r.referencia_id if r.referencia_id.startswith("CUI") else None for r in usr.itertuples()],
    "family_member_id": [r.referencia_id if r.referencia_id.startswith("FAM") else None for r in usr.itertuples()],
    "display_name": usr.nombre.str.replace("Dueño Cuidado Inteligente MX", "Dirección Enlaza", regex=False),
    "email": usr.correo.str.replace("dueno@", "owner@", regex=False),
})
if USERS_WITH_HASH:
    old = pd.read_csv(USERS_WITH_HASH, dtype=str, keep_default_na=False).set_index("usuario_id").password_hash
    users["password_hash"] = users.user_id.map(old)
users["active"] = True
coordinator_of = users[users.role == "coordinator"].set_index("institution_id").user_id
save(users, "users")

# ---------------------------------------------------------------- service requests + assignments
def ts(date, hhmm):
    h, m = map(int, hhmm.split(":"))
    return dt.datetime.fromisoformat(date) + dt.timedelta(hours=h, minutes=m)

req, asg = [], []
for i, v in enumerate(his.itertuples(), start=1):
    rid = f"REQ-{i:05d}"
    sched = ts(v.fecha, v.hora_programada)
    created = sched - dt.timedelta(days=1) + dt.timedelta(hours=int(rng.integers(-6, 4)), minutes=int(rng.integers(0, 60)))
    if v.estado == "Cerrada":
        status, reason = "closed", None
    elif v.estado.startswith("Cancelada"):
        status, reason = "cancelled", "cancelled_by_family"
    else:
        status, reason = "unattended", "no_staff_available"
    req.append({"request_id": rid, "institution_id": v.institucion_id, "patient_id": v.paciente_id,
                "service_id": v.servicio_id, "origin": "care_plan", "priority": priority_of[v.paciente_id],
                "scheduled_for": sched.strftime("%Y-%m-%d %H:%M:%S") + TZ,
                "created_at": created.strftime("%Y-%m-%d %H:%M:%S") + TZ, "status": status, "status_reason": reason})
    if v.cuidador_id:
        assigned = created + dt.timedelta(minutes=int(rng.integers(5, 90)))
        arr = end = None
        if v.hora_llegada:
            arr = ts(v.fecha, v.hora_llegada)
            if arr < sched - dt.timedelta(hours=6): arr += dt.timedelta(days=1)
            end = ts(v.fecha, v.hora_fin)
            while end < arr: end += dt.timedelta(days=1)
        f = lambda d: d.strftime("%Y-%m-%d %H:%M:%S") + TZ if d else None
        asg.append({"assignment_id": f"ASG-{len(asg)+1:05d}", "request_id": rid, "institution_id": v.institucion_id,
                    "caregiver_id": v.cuidador_id, "assigned_by": coordinator_of[v.institucion_id],
                    "approval": "auto" , "assigned_at": f(assigned), "arrived_at": f(arr), "finished_at": f(end),
                    "family_confirmed": bool(int(v.confirmacion_familia)) if arr else False})
req = pd.DataFrame(req); asg = pd.DataFrame(asg)
# urgent (high priority) assignments need coordinator approval; routine ones are auto-approved
hi = asg.request_id.map(req.set_index("request_id").priority) == "high"
asg.loc[hi, "approval"] = "coordinator"
save(req, "service_requests")
save(asg, "assignments")
