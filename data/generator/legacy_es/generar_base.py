"""
Generador de la base de datos sintética de Cuidado Inteligente MX.

Crea una población sintética de personas de 60 años y más de la CDMX y los datos
operativos de la plataforma (instituciones, pacientes, cuidadores, servicios,
plan de cuidado, historial de 30 días, consentimientos y usuarios de demo).

Todas las personas son ficticias. Las proporciones (alcaldía, sexo, edad,
enfermedades, afiliación, lengua indígena, limitación) se toman de fuentes
oficiales: INEGI (Censo 2020, ENASEM), INSP (ENSANUT 2018-19), CONAPO y el
estudio PLATINO. Ver la hoja "fuentes" del Excel.

Uso:  python generar_base.py  [carpeta_salida]
Semilla fija (2026): siempre genera exactamente los mismos datos.
"""
import sys, os, math, datetime as dt
import numpy as np
import pandas as pd
from scipy.stats import norm

SEED = 2026
N_POB = 20_000
FECHA_REF = dt.date(2026, 11, 20)          # "hoy" de la demo
HIST_INICIO = dt.date(2026, 10, 21)         # 30 días de historial
HIST_DIAS = 30
rng = np.random.default_rng(SEED)

# ----------------------------------------------------------------------------
# 1. PARÁMETROS REALES
# ----------------------------------------------------------------------------
# Población de 60+ por alcaldía (INEGI, Censo 2020). Clave INEGI del municipio.
# Coordenadas: punto central APROXIMADO de la zona urbana de cada alcaldía y
# dispersión (grados) para repartir puntos; se reemplazan por AGEB reales al
# descargar el Marco Geoestadístico.
# hlin_pct: % de población de 3+ que habla lengua indígena en la alcaldía
# (Censo 2020); None = se usa el promedio de la CDMX (1.4 %).
ALCALDIAS = [
    # nombre, cve, pob60, lat, lon, disp, hlin_pct
    ("Álvaro Obregón",          "010", 122_319, 19.360, -99.215, 0.018, None),
    ("Azcapotzalco",            "002",  78_650, 19.487, -99.185, 0.012, None),
    ("Benito Juárez",           "014",  87_344, 19.378, -99.160, 0.010, None),
    ("Coyoacán",                "003", 126_592, 19.330, -99.155, 0.014, None),
    ("Cuajimalpa de Morelos",   "004",  25_803, 19.360, -99.290, 0.012, None),
    ("Cuauhtémoc",              "015",  93_809, 19.432, -99.148, 0.010, None),
    ("Gustavo A. Madero",       "005", 203_469, 19.488, -99.110, 0.018, None),
    ("Iztacalco",               "006",  70_907, 19.395, -99.098, 0.009, None),
    ("Iztapalapa",              "007", 262_064, 19.355, -99.065, 0.020, 1.63),
    ("La Magdalena Contreras",  "008",  38_073, 19.310, -99.235, 0.010, None),
    ("Miguel Hidalgo",          "016",  71_111, 19.428, -99.200, 0.012, None),
    ("Milpa Alta",              "009",  16_437, 19.192, -99.023, 0.014, 3.3),
    ("Tláhuac",                 "011",  46_196, 19.285, -99.010, 0.012, None),
    ("Tlalpan",                 "012", 108_894, 19.285, -99.170, 0.016, 1.7),
    ("Venustiano Carranza",     "017",  78_964, 19.428, -99.105, 0.010, None),
    ("Xochimilco",              "013",  60_987, 19.262, -99.105, 0.014, 2.5),
]
POB60_CDMX = 1_491_619
HLIN_CDMX = 1.4

# Sexo y edad (Censo 2020, CDMX): 57.2 % mujeres; 60-69 = 9 %, 70-79 = 4.8 %,
# 80+ = 2.4 % de la población total (=> 55.6 %, 29.6 %, 14.8 % de los 60+).
P_MUJER = 0.572
P_GRUPO = {"60-69": 9.0/16.2, "70-79": 4.8/16.2, "80+": 2.4/16.2}
# Ajuste de % de mujeres por grupo (ENASEM 2024 nacional: 52.9, 53.3, 54.5 vs 53.2)
AJ_MUJER = {"60-69": -0.003, "70-79": 0.001, "80+": 0.013}

# Prevalencias ENSANUT 2018-19, población de 60+ (Salinas-Rodríguez et al., 2020).
# por grupo de edad [60-69, 70-79, 80-89, 90+] y total / hombres / mujeres (%)
ENSANUT = {
    "diabetes":            ([25.6, 25.8, 23.8,  9.4], 25.1, 22.4, 27.1),
    "hipertension":        ([38.8, 46.3, 48.7, 43.6], 42.4, 35.2, 47.8),
    "hipercolesterolemia": ([27.7, 26.5, 15.2, 13.1], 25.5, 20.6, 29.3),
    "enf_corazon":         ([ 5.1,  8.9, 12.2,  7.6],  7.1,  6.6,  7.6),
    "evc_embolia":         ([ 1.0,  1.3,  2.1,  1.4],  1.2,  1.3,  1.2),
    "enf_renal":           ([16.8, 15.6, 16.3, 14.3], 16.3, 12.1, 19.5),
    "sintomas_depresivos": ([37.1, 42.0, 48.2, 69.8], 40.6, 32.8, 46.5),
    "caida_12m":           ([ 3.4,  3.6,  6.3,  5.8],  3.9,  1.9,  5.4),
    "fragilidad":          ([ 8.8, 12.6, 12.7, 13.5], 10.6,  7.1, 13.2),
    "deterioro_visual":    ([ 9.7, 14.2, 22.0, 33.5], 13.1, 12.5, 13.5),
    "deterioro_auditivo":  ([ 2.8,  8.7, 14.7, 41.5],  6.9,  8.3,  5.8),
    "dif_autocuidado":     ([ 1.8,  4.2, 10.6, 29.8],  4.2,  3.4,  4.8),
    "dif_actividades_aut": ([ 0.8,  2.4,  5.5, 19.2],  2.2,  1.8,  2.5),
    "obesidad":            ([41.5, 28.9, 17.3,  1.4], 34.0, 26.1, 39.8),
    "anemia":              ([21.1, 34.2, 43.8, 45.1], 28.8, 28.1, 29.3),
}
# Enfermedades sin desglose por edad en la fuente: % total, hombres, mujeres.
# ENASEM 2024 publica el % ENTRE QUIENES REPORTARON ALGUNA ENFERMEDAD; se convierte
# a prevalencia poblacional con el factor 0.57 = 42.4 (hipertensión ENSANUT) / 74.5
# (hipertensión ENASEM 2024 entre quienes reportaron enfermedad).
F_REPORTA = 42.4 / 74.5
OTRAS = {
    "artritis":              (18.0*F_REPORTA, 11.8*F_REPORTA, 22.5*F_REPORTA),
    "enf_pulmonar_cronica":  ( 7.5*F_REPORTA,  7.4*F_REPORTA,  7.6*F_REPORTA),
    "cancer":                ( 5.1*F_REPORTA,  4.7*F_REPORTA,  5.4*F_REPORTA),
}
# Estado cognitivo (ENSANUT 2012, 60+): deterioro cognitivo 7.3 %, demencia 7.9 %.
# El gradiente por edad es un SUPUESTO (la fuente no lo publica en el resumen).
COG_TOTAL = {"deterioro_cognitivo": 7.3, "demencia": 7.9}
COG_EDAD = {"60-69": 0.45, "70-79": 1.0, "80+": 2.6}   # multiplicadores relativos

# Censo 2020 vía CONAPO, CDMX 60+
P_AFILIADO = 0.834
AFILIACION = {"IMSS": 59.3, "ISSSTE": 25.9, "IMSS-Bienestar/INSABI": 10.9,
              "Privada u otra": 5.2, "Pemex, Defensa o Marina": 1.8}
P_LIMITACION = {"H": 0.465, "M": 0.510}          # limitación, discapacidad o cond. mental
EDO_CIVIL = {"H": {"Casado(a) o en unión": 71.7, "Viudo(a)": 11.9, "Soltero(a)": 7.5, "Divorciado(a) o separado(a)": 8.8},
             "M": {"Casado(a) o en unión": 41.8, "Viudo(a)": 31.7, "Soltero(a)": 13.6, "Divorciado(a) o separado(a)": 12.8}}
P_HLI_60 = 0.0181                                  # 60+ CDMX que hablan lengua indígena
LENGUAS = {"Náhuatl": 0.33, "Mixteco": 0.14, "Otomí": 0.13, "Mazateco": 0.11,
           "Zapoteco": 0.11, "Mazahua": 0.08, "Totonaco": 0.05, "Otra": 0.05}  # 1/3 náhuatl real; resto supuesto

# ----------------------------------------------------------------------------
# 2. NOMBRES FICTICIOS
# ----------------------------------------------------------------------------
NOM_M = ["María","Guadalupe","Juana","Margarita","Josefina","Rosa","Teresa","Francisca","Leticia","Silvia",
         "Martha","Elena","Carmen","Alicia","Ana María","Patricia","Gloria","Yolanda","Irma","Socorro",
         "Esperanza","Concepción","Graciela","Luz María","Ofelia","Catalina","Rosario","Dolores","Estela","Beatriz",
         "Lucía","Isabel","Victoria","Angélica","Bertha","Consuelo","Raquel","Amparo","Celia","Elvira"]
NOM_H = ["José","Juan","Jesús","Francisco","Antonio","Pedro","Manuel","Miguel","Roberto","Javier",
         "Alfredo","Rafael","Carlos","Jorge","Fernando","Raúl","Ricardo","Enrique","Salvador","Arturo",
         "Alberto","Ignacio","Ramón","Sergio","Héctor","Guillermo","Luis","Mario","Rubén","Andrés",
         "Felipe","Gabriel","Armando","Ernesto","Gilberto","Agustín","Rodolfo","Joaquín","Tomás","Víctor"]
APELLIDOS = ["Hernández","García","Martínez","López","González","Pérez","Rodríguez","Sánchez","Ramírez","Cruz",
             "Flores","Gómez","Morales","Vázquez","Reyes","Jiménez","Torres","Díaz","Gutiérrez","Ruiz",
             "Mendoza","Aguilar","Ortiz","Moreno","Castillo","Romero","Álvarez","Méndez","Chávez","Rivera",
             "Juárez","Ramos","Domínguez","Herrera","Medina","Castro","Vargas","Guzmán","Velázquez","Rojas",
             "Contreras","Salazar","Luna","Ortega","Santiago","Guerrero","Bautista","Estrada","Cortés","Soto"]
NOM_JOVEN_M = ["Laura","Adriana","Claudia","Mónica","Verónica","Gabriela","Alejandra","Karla","Diana","Paola","Fernanda","Daniela"]
NOM_JOVEN_H = ["Alejandro","Eduardo","Ricardo","Óscar","Iván","Daniel","Jorge","Pablo","Rodrigo","Sergio","Diego","Hugo"]

def pick(lst, n=None):
    return rng.choice(lst, size=n) if n else rng.choice(lst)

# ----------------------------------------------------------------------------
# 3. POBLACIÓN SINTÉTICA (representativa de la CDMX)
# ----------------------------------------------------------------------------
def generar_poblacion(n):
    alc = pd.DataFrame(ALCALDIAS, columns=["alcaldia","cve_mun","pob60","lat","lon","disp","hlin_pct"])
    w = alc.pob60 / alc.pob60.sum()
    idx = rng.choice(len(alc), size=n, p=w)
    df = pd.DataFrame({"alcaldia": alc.alcaldia.values[idx], "cve_mun": alc.cve_mun.values[idx]})
    # grupo de edad y edad exacta
    grupos = list(P_GRUPO); pg = np.array(list(P_GRUPO.values())); pg /= pg.sum()
    g = rng.choice(grupos, size=n, p=pg)
    edad = np.empty(n, dtype=int)
    for gr, lo, hi, dec in [("60-69",60,69,0.03),("70-79",70,79,0.06),("80+",80,100,0.17)]:
        m = g == gr
        ages = np.arange(lo, hi+1); pw = np.exp(-dec*(ages-lo)); pw /= pw.sum()
        edad[m] = rng.choice(ages, size=m.sum(), p=pw)
    df["edad"] = edad; df["grupo_edad"] = g
    pm = np.array([P_MUJER + AJ_MUJER[x] for x in g])
    df["sexo"] = np.where(rng.random(n) < pm, "M", "H")
    # ubicación aproximada
    lat0 = alc.lat.values[idx]; lon0 = alc.lon.values[idx]; d = alc.disp.values[idx]
    df["lat"] = np.round(lat0 + np.clip(rng.normal(0,1,n),-2.2,2.2)*d, 5)
    df["lon"] = np.round(lon0 + np.clip(rng.normal(0,1,n),-2.2,2.2)*d*1.05, 5)
    # grupo fino para ENSANUT
    gf = np.where(edad >= 90, 3, np.where(edad >= 80, 2, np.where(edad >= 70, 1, 0)))

    # ---- enfermedades con cópula gaussiana (factores comunes => multimorbilidad realista)
    cardio = ["diabetes","hipertension","hipercolesterolemia","enf_corazon","evc_embolia","enf_renal","obesidad"]
    funcional = ["fragilidad","dif_autocuidado","dif_actividades_aut","caida_12m","deterioro_visual",
                 "deterioro_auditivo","demencia_lat"]
    G = rng.normal(size=n); C = rng.normal(size=n); F = rng.normal(size=n)
    def latente(nombre):
        a_g = 0.30
        a_c = 0.45 if nombre in cardio else 0.0
        a_f = 0.60 if nombre in funcional else (0.30 if nombre == "sintomas_depresivos" else 0.0)
        e = math.sqrt(max(1 - a_g**2 - a_c**2 - a_f**2, 0.02))
        return a_g*G + a_c*C + a_f*F + e*rng.normal(size=n)
    es_m = (df.sexo == "M").values
    for enf, (por_edad, tot, h, m) in ENSANUT.items():
        p_age = np.array(por_edad)[gf] / 100
        p = p_age * np.where(es_m, m/tot, h/tot)
        p = np.clip(p, 0.001, 0.97)
        df[enf] = (latente(enf) < norm.ppf(p)).astype(int)
    for enf, (tot, h, m) in OTRAS.items():
        p = np.where(es_m, m, h) / 100
        df[enf] = (latente(enf) < norm.ppf(p)).astype(int)
    # estado cognitivo (excluyente): demencia / deterioro / normal
    mult = np.array([COG_EDAD[x] for x in g])
    mult_norm = mult / np.average(list(COG_EDAD.values()), weights=pg)
    p_dem = np.clip(COG_TOTAL["demencia"]/100 * mult_norm, 0, 0.6)
    p_det = np.clip(COG_TOTAL["deterioro_cognitivo"]/100 * mult_norm, 0, 0.6)
    z = latente("demencia_lat")
    u_dem = norm.ppf(p_dem); u_det = norm.ppf(np.clip(p_dem + p_det, 0, 0.95))
    df["estado_cognitivo"] = np.where(z < u_dem, "Demencia", np.where(z < u_det, "Deterioro cognitivo", "Sin deterioro"))
    # multimorbilidad (≥2 enfermedades crónicas)
    cronicas = ["diabetes","hipertension","hipercolesterolemia","enf_corazon","evc_embolia","enf_renal",
                "artritis","enf_pulmonar_cronica","cancer"]
    df["num_enf_cronicas"] = df[cronicas].sum(axis=1)
    df["multimorbilidad"] = (df.num_enf_cronicas >= 2).astype(int)
    # definición amplia (calibrada contra ENSANUT 2018-19, 55.6 %; OJO: ENSANUT cuenta 2+ de 7 enfermedades
    # sin obesidad ni depresión, así que la comparación es aproximada): suma obesidad y síntomas depresivos
    df["multimorbilidad_amplia"] = ((df.num_enf_cronicas + df.obesidad + df.sintomas_depresivos) >= 2).astype(int)

    # limitación / discapacidad (Censo): incluye a todos con dificultad funcional,
    # y se completa al azar (más probable a mayor edad) hasta la meta por sexo.
    base = ((df.dif_autocuidado + df.dif_actividades_aut + df.fragilidad + df.deterioro_visual +
             df.deterioro_auditivo) > 0) | (df.estado_cognitivo == "Demencia")
    df["limitacion_discapacidad"] = base.astype(int)
    for sx in ["H","M"]:
        msk = (df.sexo == sx).values
        meta = P_LIMITACION[sx] * msk.sum()
        faltan = int(meta - df.loc[msk, "limitacion_discapacidad"].sum())
        cand = np.where(msk & (df.limitacion_discapacidad.values == 0))[0]
        if faltan > 0 and len(cand):
            wt = np.array([{"60-69":1.0,"70-79":1.8,"80+":3.0}[x] for x in g[cand]]); wt /= wt.sum()
            sel = rng.choice(cand, size=min(faltan, len(cand)), replace=False, p=wt)
            df.loc[sel, "limitacion_discapacidad"] = 1

    # nivel de dependencia (derivado; regla documentada en "diccionario")
    sev = (df.dif_autocuidado == 1) | ((df.estado_cognitivo == "Demencia") & (df.edad >= 80))
    mod = (df.dif_actividades_aut == 1) | (df.fragilidad == 1) | (df.estado_cognitivo == "Demencia")
    df["nivel_dependencia"] = np.where(sev, "Severa", np.where(mod, "Moderada",
                              np.where(df.limitacion_discapacidad == 1, "Leve", "Independiente")))

    # afiliación a servicios de salud
    afil = rng.random(n) < P_AFILIADO
    inst = list(AFILIACION); pa = np.array(list(AFILIACION.values())); pa /= pa.sum()
    df["afiliacion_salud"] = np.where(afil, rng.choice(inst, size=n, p=pa), "Sin afiliación")
    # estado civil por sexo
    ec = np.empty(n, dtype=object)
    for sx in ["H","M"]:
        msk = (df.sexo == sx).values
        cats = list(EDO_CIVIL[sx]); pc = np.array(list(EDO_CIVIL[sx].values())); pc /= pc.sum()
        ec[msk] = rng.choice(cats, size=msk.sum(), p=pc)
    df["estado_civil"] = ec
    # lengua indígena (proporcional al % de la alcaldía)
    hl = alc.set_index("alcaldia").hlin_pct.fillna(HLIN_CDMX)
    p_hli = P_HLI_60 * df.alcaldia.map(hl).values / HLIN_CDMX
    hli = rng.random(n) < p_hli
    df["habla_lengua_indigena"] = hli.astype(int)
    lg = list(LENGUAS); pl = np.array(list(LENGUAS.values())); pl /= pl.sum()
    df["lengua_indigena"] = np.where(hli, rng.choice(lg, size=n, p=pl), "")

    # nombres y fecha de nacimiento
    nombres = np.where(es_m, pick(NOM_M, n), pick(NOM_H, n))
    df["nombre"] = nombres
    df["apellido_paterno"] = pick(APELLIDOS, n); df["apellido_materno"] = pick(APELLIDOS, n)
    nac = [FECHA_REF.replace(year=FECHA_REF.year - int(a)) - dt.timedelta(days=int(rng.integers(1, 365)))
           for a in df.edad]
    df["fecha_nacimiento"] = nac
    df.insert(0, "persona_id", [f"PS-{i+1:05d}" for i in range(n)])
    cols = ["persona_id","nombre","apellido_paterno","apellido_materno","sexo","edad","grupo_edad","fecha_nacimiento",
            "alcaldia","cve_mun","lat","lon","estado_civil","afiliacion_salud","habla_lengua_indigena","lengua_indigena",
            "diabetes","hipertension","hipercolesterolemia","enf_corazon","evc_embolia","enf_renal","enf_pulmonar_cronica",
            "artritis","cancer","obesidad","anemia","sintomas_depresivos","estado_cognitivo","caida_12m","fragilidad",
            "deterioro_visual","deterioro_auditivo","dif_autocuidado","dif_actividades_aut","limitacion_discapacidad",
            "num_enf_cronicas","multimorbilidad","multimorbilidad_amplia","nivel_dependencia"]
    return df[cols], alc

# ----------------------------------------------------------------------------
# 4. INSTITUCIONES, SERVICIOS, CUIDADORES
# ----------------------------------------------------------------------------
INSTITUCIONES = pd.DataFrame([
    ("INS-A","Clínica Oriente","Clínica geriátrica","Iztapalapa","Diurno",150,15,"Profesional"),
    ("INS-B","Residencia Coyoacán","Asilo / residencia","Coyoacán","24 h",80,10,"Profesional"),
    ("INS-C","Centro de Día Aragón","Centro de día","Gustavo A. Madero","Diurno",60,6,"Profesional"),
    ("INS-D","Red Cuidar Tlalpan","Red de cuidado a domicilio","Tlalpan","24 h",70,8,"Profesional"),
    ("INS-E","Red Vecinal Iztacalco","Red de cuidado pequeña","Iztacalco","Diurno",40,5,"Básico"),
], columns=["institucion_id","nombre","tipo","alcaldia","horario","pacientes","cuidadores","plan_suscripcion"])
INSTITUCIONES["precio_plan_mxn_mes"] = INSTITUCIONES.plan_suscripcion.map({"Básico":2500,"Profesional":6000})

SERVICIOS = pd.DataFrame([
    ("SRV-01","Consulta geriátrica a domicilio",60,2200,1800,2800,"medico","A,B,C,D","Doctoralia (geriatras CDMX)"),
    ("SRV-02","Visita de enfermería (inyección, curación, signos vitales)",30,300,200,350,"enfermeria","A,B,C,D,E","Cronoshare (Xochimilco)"),
    ("SRV-03","Turno de enfermería 8 h",480,1300,980,1650,"enfermeria","A,B,D","Cronoshare (Coyoacán)"),
    ("SRV-04","Turno de enfermería 12 h",720,1950,1460,2480,"enfermeria","A,B,D","Cronoshare (Coyoacán)"),
    ("SRV-05","Terapia física o masaje terapéutico",60,900,600,1200,"terapia","A,B,C,E","Cronoshare (fisioterapia)"),
    ("SRV-06","Cuidador diurno 8 h",480,1050,900,1200,"cuidado","B,C,D,E","Cronoshare (Iztapalapa)"),
    ("SRV-07","Cuidador nocturno 12 h",720,1500,1300,1700,"cuidado","B,D","Cronoshare (Iztapalapa)"),
    ("SRV-08","Atención respiratoria / oxigenoterapia (visita)",45,650,None,None,"enfermeria","A,D","Supuesto: visita de enfermería + manejo de oxígeno; renta de concentrador 3,000-5,000/mes (UnoTV, 2021)"),
    ("SRV-09","Toma de muestras a domicilio",20,None,None,None,"enfermeria","A,C,D","Pendiente de cotizar"),
], columns=["servicio_id","nombre","duracion_min","precio_referencia_mxn","precio_min_mxn","precio_max_mxn",
            "habilidad_requerida","instituciones","fuente_precio"])

TURNOS = {"diurno": (8, 16), "mixto": (10, 18), "vespertino": (14, 22), "nocturno": (20, 32)}  # 32 = 8 am día sig.
HAB_TIPO = {"Médico": ["medico"], "Enfermería": ["enfermeria"], "Terapeuta": ["terapia"], "Cuidador": ["cuidado"]}

def generar_cuidadores():
    filas = []
    comp = {"INS-A": {"Médico":2,"Enfermería":8,"Terapeuta":2,"Cuidador":3},
            "INS-B": {"Médico":1,"Enfermería":4,"Terapeuta":1,"Cuidador":4},
            "INS-C": {"Médico":1,"Enfermería":2,"Terapeuta":1,"Cuidador":2},
            "INS-D": {"Médico":1,"Enfermería":4,"Terapeuta":0,"Cuidador":3},
            "INS-E": {"Médico":0,"Enfermería":2,"Terapeuta":1,"Cuidador":2}}
    alc_info = {a[0]: a for a in ALCALDIAS}
    k = 1
    for _, ins in INSTITUCIONES.iterrows():
        a = alc_info[ins.alcaldia]
        for tipo, cuantos in comp[ins.institucion_id].items():
            for j in range(cuantos):
                if ins.horario == "24 h" and tipo in ("Enfermería","Cuidador") and j % 3 == 2:
                    turno = "nocturno"
                else:
                    turno = ["diurno","mixto","diurno","vespertino"][j % 4] if tipo != "Médico" else "mixto"
                    if ins.horario == "Diurno" and turno == "vespertino": turno = "diurno"
                sx = "M" if rng.random() < 0.78 else "H"
                nom = pick(NOM_JOVEN_M if sx == "M" else NOM_JOVEN_H)
                ini, fin = TURNOS[turno]
                filas.append({"cuidador_id": f"CUI-{k:03d}", "institucion_id": ins.institucion_id,
                    "nombre": f"{nom} {pick(APELLIDOS)} {pick(APELLIDOS)}", "tipo": tipo,
                    "habilidades": ",".join(HAB_TIPO[tipo] + (["enfermeria"] if tipo=="Médico" else [])),
                    "turno": turno, "hora_inicio": f"{ini:02d}:00", "hora_fin": f"{fin%24:02d}:00",
                    "horas_turno": fin-ini,
                    "lat_base": round(a[3] + rng.normal(0, a[5]), 5), "lon_base": round(a[4] + rng.normal(0, a[5]), 5),
                    "activo": 1})
                k += 1
    return pd.DataFrame(filas)

# ----------------------------------------------------------------------------
# 5. PACIENTES (subconjunto de la población, con sesgo de selección documentado)
# ----------------------------------------------------------------------------
def generar_pacientes(pob):
    filas = []
    k = 1
    for _, ins in INSTITUCIONES.iterrows():
        cand = pob[pob.alcaldia == ins.alcaldia].copy()
        # Las personas atendidas por una institución de cuidado NO son un corte
        # representativo: se elige con mayor probabilidad a quien tiene más dependencia
        # y más enfermedades (pesos = SUPUESTO documentado).
        w = (1 + cand.nivel_dependencia.map({"Independiente":0,"Leve":1.0,"Moderada":3.0,"Severa":6.0})
               + 0.8*cand.num_enf_cronicas + 0.04*(cand.edad - 60))
        if ins.tipo.startswith("Asilo"):
            w = w * (1 + 1.5*(cand.edad >= 80))
        sel = cand.sample(n=int(ins.pacientes), weights=w, random_state=int(rng.integers(1e9)))
        for _, p in sel.iterrows():
            d = p.to_dict()
            d["paciente_id"] = f"PAC-{k:04d}"; d["institucion_id"] = ins.institucion_id
            d["fecha_alta"] = FECHA_REF - dt.timedelta(days=int(rng.integers(40, 900)))
            d["prioridad_base"] = ("Alta" if (d["nivel_dependencia"] == "Severa" or d["enf_pulmonar_cronica"] or d["enf_corazon"])
                                   else "Media" if d["nivel_dependencia"] == "Moderada" or d["num_enf_cronicas"] >= 3 else "Baja")
            filas.append(d); k += 1
    pac = pd.DataFrame(filas)
    cols = ["paciente_id","institucion_id","persona_id","fecha_alta","prioridad_base"] + \
           [c for c in pac.columns if c not in ("paciente_id","institucion_id","persona_id","fecha_alta","prioridad_base")]
    return pac[cols]

def generar_familiares_y_consentimientos(pac):
    fam, con = [], []
    for i, p in enumerate(pac.itertuples(), start=1):
        casado = p.estado_civil == "Casado(a) o en unión"
        par = rng.choice(["Hija","Hijo","Esposa/o","Nieta/o","Sobrina/o","Otro familiar"],
                         p=[0.42,0.22,0.16 if casado else 0.0,0.10,0.05,0.05 + (0.0 if casado else 0.16)])
        if par == "Esposa/o":
            sx = "H" if p.sexo == "M" else "M"
            nom = pick(NOM_H if sx == "H" else NOM_M); ap = pick(APELLIDOS)
        else:
            sx = "M" if par in ("Hija",) or (par not in ("Hijo",) and rng.random() < 0.6) else "H"
            nom = pick(NOM_JOVEN_M if sx == "M" else NOM_JOVEN_H)
            ap = p.apellido_paterno if par in ("Hija","Hijo","Nieta/o") else pick(APELLIDOS)
        rep_legal = int(p.estado_cognitivo == "Demencia" or p.nivel_dependencia == "Severa")
        fid = f"FAM-{i:04d}"
        fam.append({"familiar_id": fid, "paciente_id": p.paciente_id, "institucion_id": p.institucion_id,
                    "nombre": f"{nom} {ap} {pick(APELLIDOS)}", "parentesco": par, "es_representante_legal": rep_legal,
                    "autorizado_para_solicitar": 1,
                    "correo": f"{fid.lower()}@ejemplo.test"})
        otorga = "Representante legal" if rep_legal else "Paciente"
        if p.estado_cognitivo == "Demencia":
            asent = rng.choice(["Sí","No pudo expresarse","No"], p=[0.45,0.45,0.10])
        elif rep_legal:
            asent = rng.choice(["Sí","No"], p=[0.9,0.1])
        else:
            asent = "No aplica"
        fecha = p.fecha_alta
        for tipo in ["Uso de datos de salud","Atención domiciliaria","Asistente de voz"]:
            vigente = 1; vence = fecha + dt.timedelta(days=730)
            r = rng.random()
            if tipo == "Asistente de voz" and (r < 0.08 or asent == "No"):
                otorgado, vigente = 0, 0
            else:
                otorgado = 1
                if r < 0.04:                                   # algunos vencidos para probar la validación
                    vence = FECHA_REF - dt.timedelta(days=int(rng.integers(1, 60))); vigente = 0
                elif vence < FECHA_REF:
                    vence = FECHA_REF + dt.timedelta(days=int(rng.integers(10, 400)))
            con.append({"consentimiento_id": f"CON-{len(con)+1:05d}", "paciente_id": p.paciente_id,
                        "institucion_id": p.institucion_id, "tipo": tipo, "otorgado": otorgado,
                        "otorgado_por": otorga, "familiar_id": fid if rep_legal else "",
                        "asentimiento_paciente": asent, "fecha_firma": fecha, "fecha_vencimiento": vence,
                        "vigente": vigente})
    return pd.DataFrame(fam), pd.DataFrame(con)

# ----------------------------------------------------------------------------
# 6. PLAN DE CUIDADO E HISTORIAL DE 30 DÍAS
# ----------------------------------------------------------------------------
def generar_plan(pac):
    ofrece = {r.servicio_id: r.instituciones.split(",") for r in SERVICIOS.itertuples()}
    letra = lambda iid: iid[-1]
    filas = []
    def add(p, srv, veces_sem, motivo):
        if letra(p.institucion_id) in ofrece[srv]:
            filas.append({"plan_id": f"PLN-{len(filas)+1:05d}", "paciente_id": p.paciente_id,
                          "institucion_id": p.institucion_id, "servicio_id": srv,
                          "veces_por_semana": veces_sem, "motivo": motivo})
    for p in pac.itertuples():
        add(p, "SRV-01", 0.25 if (p.num_enf_cronicas >= 2 or p.enf_corazon or p.evc_embolia) else 0.125,
            "Control geriátrico periódico")
        if p.diabetes or p.hipertension:
            add(p, "SRV-02", 2 if (p.diabetes and p.hipertension) else 1, "Control de glucosa / presión arterial")
        if p.enf_pulmonar_cronica:
            add(p, "SRV-08", 1, "Enfermedad pulmonar crónica")
        if p.fragilidad or p.caida_12m or p.artritis:
            add(p, "SRV-05", 1, "Fragilidad, caídas o artritis")
        if p.nivel_dependencia == "Severa":
            add(p, "SRV-06", 1, "Dependencia severa (apoyo de cuidador)")
            add(p, "SRV-02", 1, "Dependencia severa (revisión de enfermería)")
            if p.institucion_id in ("INS-B","INS-D") and rng.random() < 0.25:
                add(p, "SRV-07", 0.5, "Vigilancia nocturna")
        elif p.nivel_dependencia == "Moderada" or p.estado_cognitivo == "Demencia":
            add(p, "SRV-06", 0.5, "Dependencia moderada o demencia")
        if p.enf_renal:
            add(p, "SRV-09", 0.25, "Seguimiento de función renal")
    return pd.DataFrame(filas)

def generar_historial(plan, cuid):
    srv = SERVICIOS.set_index("servicio_id")
    visitas = []
    for r in plan.itertuples():
        esperado = r.veces_por_semana * HIST_DIAS / 7
        n = rng.poisson(esperado)
        dias = sorted(rng.choice(HIST_DIAS, size=min(n, HIST_DIAS), replace=False)) if n else []
        for d in dias:
            visitas.append((HIST_INICIO + dt.timedelta(days=int(d)), r.paciente_id, r.institucion_id, r.servicio_id))
    vis = pd.DataFrame(visitas, columns=["fecha","paciente_id","institucion_id","servicio_id"])
    vis["duracion_min"] = vis.servicio_id.map(srv.duracion_min)
    vis["habilidad"] = vis.servicio_id.map(srv.habilidad_requerida)
    # hora deseada: turnos largos empiezan al inicio; visitas entre 8 y 18 h
    def hora_deseada(s):
        if s in ("SRV-03","SRV-06"): return 8*60
        if s in ("SRV-04","SRV-07"): return 20*60
        return int(rng.integers(8*60, 18*60) // 15 * 15)
    vis["min_deseado"] = [hora_deseada(s) for s in vis.servicio_id]
    vis = vis.sort_values(["fecha","institucion_id","min_deseado"]).reset_index(drop=True)
    # agenda: a cada cuidador apto se le asigna sin traslapes, con 20 min de traslado
    cuid = cuid.copy()
    cuid["ini_min"] = cuid.turno.map(lambda t: TURNOS[t][0]*60)
    cuid["fin_min"] = cuid.turno.map(lambda t: TURNOS[t][1]*60)
    res = []
    for (fecha, iid), grp in vis.groupby(["fecha","institucion_id"], sort=False):
        libres = {c.cuidador_id: c.ini_min for c in cuid[cuid.institucion_id == iid].itertuples()}
        info = cuid[cuid.institucion_id == iid].set_index("cuidador_id")
        for v in grp.itertuples():
            aptos = [c for c in libres if v.habilidad in info.loc[c, "habilidades"].split(",")]
            mejor, inicio = None, None
            for c in sorted(aptos, key=lambda c: max(libres[c], v.min_deseado)):
                st = max(libres[c], v.min_deseado, info.loc[c, "ini_min"])
                if st + v.duracion_min <= info.loc[c, "fin_min"]:
                    mejor, inicio = c, st; break
            d = {"fecha": fecha, "paciente_id": v.paciente_id, "institucion_id": iid, "servicio_id": v.servicio_id,
                 "hora_programada": f"{(v.min_deseado//60)%24:02d}:{v.min_deseado%60:02d}"}
            if mejor is None:
                d.update({"cuidador_id": "", "estado": "No atendida (sin personal disponible)", "hora_llegada": "",
                          "hora_fin": "", "espera_min": "", "confirmacion_familia": 0})
            else:
                retraso = int(rng.integers(0, 26))
                lleg = inicio + retraso; fin = lleg + v.duracion_min
                libres[mejor] = fin + 20                      # 20 min de traslado a la siguiente visita
                cancel = rng.random() < 0.03
                d.update({"cuidador_id": mejor,
                          "estado": "Cancelada por la familia" if cancel else "Cerrada",
                          "hora_llegada": "" if cancel else f"{(lleg//60)%24:02d}:{lleg%60:02d}",
                          "hora_fin": "" if cancel else f"{(fin//60)%24:02d}:{fin%60:02d}",
                          "espera_min": "" if cancel else lleg - v.min_deseado,
                          "confirmacion_familia": 0 if cancel else int(rng.random() < 0.92)})
            res.append(d)
    h = pd.DataFrame(res)
    h.insert(0, "visita_id", [f"VIS-{i+1:05d}" for i in range(len(h))])
    h["precio_mxn"] = h.servicio_id.map(SERVICIOS.set_index("servicio_id").precio_referencia_mxn)
    return h

def generar_usuarios(cuid, fam):
    u = [{"usuario_id": "USR-001", "rol": "Dueño de la plataforma", "institucion_id": "", "referencia_id": "",
          "nombre": "Dueño Cuidado Inteligente MX", "correo": "dueno@ejemplo.test", "contrasena_demo": "Demo2026!"}]
    for ins in INSTITUCIONES.itertuples():
        u.append({"rol": "Coordinador(a)", "institucion_id": ins.institucion_id, "referencia_id": "",
                  "nombre": f"Coordinación {ins.nombre}", "correo": f"coordinacion.{ins.institucion_id[-1].lower()}@ejemplo.test"})
        med = cuid[(cuid.institucion_id == ins.institucion_id) & (cuid.tipo == "Médico")]
        for m in med.itertuples():
            u.append({"rol": "Médico", "institucion_id": ins.institucion_id, "referencia_id": m.cuidador_id,
                      "nombre": m.nombre, "correo": f"{m.cuidador_id.lower()}@ejemplo.test"})
    for c in cuid[cuid.tipo != "Médico"].groupby("institucion_id").head(2).itertuples():
        u.append({"rol": "Cuidador(a)", "institucion_id": c.institucion_id, "referencia_id": c.cuidador_id,
                  "nombre": c.nombre, "correo": f"{c.cuidador_id.lower()}@ejemplo.test"})
    for f in fam.groupby("institucion_id").head(2).itertuples():
        u.append({"rol": "Familiar", "institucion_id": f.institucion_id, "referencia_id": f.familiar_id,
                  "nombre": f.nombre, "correo": f.correo})
    df = pd.DataFrame(u)
    df["usuario_id"] = [f"USR-{i+1:03d}" for i in range(len(df))]
    df["contrasena_demo"] = "Demo2026!"
    return df[["usuario_id","rol","institucion_id","referencia_id","nombre","correo","contrasena_demo"]]

# ----------------------------------------------------------------------------
def main(out):
    os.makedirs(out, exist_ok=True)
    pob, alc = generar_poblacion(N_POB)
    cuid = generar_cuidadores()
    pac = generar_pacientes(pob)
    fam, con = generar_familiares_y_consentimientos(pac)
    plan = generar_plan(pac)
    hist = generar_historial(plan, cuid)
    usr = generar_usuarios(cuid, fam)
    tablas = {"alcaldias": alc.drop(columns=["disp"]).rename(columns={"lat":"lat_aprox","lon":"lon_aprox",
                                                                       "pob60":"poblacion_60_mas_censo2020"}),
              "poblacion_sintetica": pob, "instituciones": INSTITUCIONES, "pacientes": pac,
              "familiares": fam, "consentimientos": con, "cuidadores": cuid, "catalogo_servicios": SERVICIOS,
              "plan_cuidado": plan, "historial_servicios": hist, "usuarios_demo": usr}
    for k, v in tablas.items():
        v.to_csv(os.path.join(out, f"{k}.csv"), index=False, encoding="utf-8-sig")
    return tablas

if __name__ == "__main__":
    t = main(sys.argv[1] if len(sys.argv) > 1 else "salida")
    for k, v in t.items():
        print(f"{k:22s} {len(v):6d} filas")
