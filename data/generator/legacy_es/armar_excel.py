"""Arma el Excel final a partir de los CSV generados por generar_base.py."""
import sys, os
import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

SRC = sys.argv[1] if len(sys.argv) > 1 else "csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "Base_Datos_Cuidado_Inteligente_MX.xlsx"

def rd(n): return pd.read_csv(os.path.join(SRC, f"{n}.csv"), dtype={"cve_mun": str}, keep_default_na=False)
T = {n: rd(n) for n in ["alcaldias","poblacion_sintetica","instituciones","pacientes","familiares","consentimientos",
                         "cuidadores","catalogo_servicios","plan_cuidado","historial_servicios","usuarios_demo"]}

wb = xlsxwriter.Workbook(OUT)
wb.formats[0].set_font_name("Arial"); wb.formats[0].set_font_size(10)
TEAL = "#0F5C6E"
F = {
 "h":   wb.add_format({"bold": True, "font_color": "white", "bg_color": TEAL, "font_name": "Arial", "font_size": 10, "border": 1, "text_wrap": True, "valign": "top"}),
 "t":   wb.add_format({"bold": True, "font_size": 16, "font_color": TEAL, "font_name": "Arial"}),
 "st":  wb.add_format({"bold": True, "font_size": 11, "font_name": "Arial"}),
 "wrap":wb.add_format({"text_wrap": True, "valign": "top", "font_name": "Arial", "font_size": 10}),
 "pct": wb.add_format({"num_format": "0.0%", "font_name": "Arial", "font_size": 10}),
 "pctb":wb.add_format({"num_format": "0.0%", "font_name": "Arial", "font_size": 10, "font_color": "#0000FF"}),
 "dif": wb.add_format({"num_format": "+0.0%;-0.0%;0.0%", "font_name": "Arial", "font_size": 10}),
 "int": wb.add_format({"num_format": "#,##0", "font_name": "Arial", "font_size": 10}),
 "intb":wb.add_format({"num_format": "#,##0", "font_name": "Arial", "font_size": 10, "font_color": "#0000FF"}),
 "mxn": wb.add_format({"num_format": "$#,##0", "font_name": "Arial", "font_size": 10}),
 "date":wb.add_format({"num_format": "yyyy-mm-dd", "font_name": "Arial", "font_size": 10}),
 "note":wb.add_format({"italic": True, "font_color": "#5B6870", "text_wrap": True, "font_name": "Arial", "font_size": 9}),
 "ok":  wb.add_format({"font_color": "#1F5A38", "bold": True, "font_name": "Arial", "font_size": 10}),
}

def tabla(nombre, df, anchos=None, fechas=(), dinero=()):
    ws = wb.add_worksheet(nombre)
    ws.write_row(0, 0, list(df.columns), F["h"])
    for j, c in enumerate(df.columns):
        col = df[c]
        if c in fechas:
            for i, v in enumerate(col, start=1):
                if v: ws.write_datetime(i, j, pd.Timestamp(v).to_pydatetime(), F["date"])
        else:
            fmt = F["mxn"] if c in dinero else None
            for i, v in enumerate(col, start=1):
                if v == "" or v is None: continue
                if isinstance(v, str):
                    try:
                        num = float(v) if v.replace(".", "", 1).replace("-", "", 1).isdigit() else None
                    except Exception: num = None
                    if num is not None and c not in ("cve_mun",):
                        ws.write_number(i, j, num, fmt)
                    else:
                        ws.write_string(i, j, v)
                else:
                    ws.write(i, j, v, fmt)
        w = (anchos or {}).get(c, min(max(len(str(c)) + 2, int(df[c].astype(str).str.len().quantile(0.95)) + 2), 45))
        ws.set_column(j, j, w)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, len(df), len(df.columns) - 1)
    ws.set_row(0, 30)
    return ws

# ---------------------------------------------------------------- LEEME
ws = wb.add_worksheet("LEEME"); ws.set_column(0, 0, 4); ws.set_column(1, 1, 30); ws.set_column(2, 2, 100)
ws.write(0, 1, "Base de datos sintética · Cuidado Inteligente MX", F["t"])
ws.write(1, 1, "Personas mayores de la CDMX y datos operativos de la plataforma. Generada el 20 de noviembre de 2026, semilla 2026.", F["note"])
r = 3
ws.write(r, 1, "Qué es", F["st"]); r += 1
for txt in [
 "Todas las personas, instituciones, cuidadores y familiares son FICTICIOS. No hay datos de personas reales.",
 "Las proporciones sí son reales: cuántas personas de 60+ viven en cada alcaldía, su sexo y edad, sus enfermedades, su afiliación a servicios de salud, la lengua indígena y la limitación o discapacidad se toman de INEGI (Censo 2020, ENASEM), INSP (ENSANUT 2018-19) y CONAPO. Ver la hoja 'fuentes'.",
 "Las enfermedades se asignan por edad y sexo, y con correlación entre ellas (quien tiene diabetes tiene más probabilidad de tener hipertensión), para que las combinaciones sean realistas.",
 "La hoja 'validacion' compara, con fórmulas, lo generado contra las cifras oficiales.",
]:
    ws.write(r, 2, "• " + txt, F["wrap"]); ws.set_row(r, 30); r += 1
r += 1; ws.write(r, 1, "Hojas", F["st"]); r += 1
hojas = [
 ("fuentes", "Cada cifra real usada, su valor, a qué población se refiere y su fuente con enlace. También los supuestos."),
 ("parametros_enfermedades", "Prevalencias por grupo de edad y sexo con que se generaron las enfermedades."),
 ("alcaldias", "Población de 60+ por alcaldía (Censo 2020) y su comparación con la población generada."),
 ("poblacion_sintetica", "20,000 personas de 60+ representativas de la CDMX. Sirve para mapas, análisis y el simulador."),
 ("instituciones", "Las 5 instituciones ficticias cliente (A y B son las del avance de SIE)."),
 ("pacientes", "400 pacientes tomados de la población sintética (ver advertencia 3)."),
 ("familiares", "Un familiar autorizado por paciente; indica si es representante legal."),
 ("consentimientos", "3 consentimientos por paciente (datos, atención, asistente de voz), con asentimiento y vigencia."),
 ("cuidadores", "44 cuidadores con tipo, habilidades, turno y ubicación base."),
 ("catalogo_servicios", "9 servicios con duración, precio de referencia de mercado en CDMX y qué institución los ofrece."),
 ("plan_cuidado", "Qué servicios recibe cada paciente y con qué frecuencia, según sus enfermedades y dependencia."),
 ("historial_servicios", "30 días de visitas (21 oct – 19 nov 2026) asignadas sin traslapes; incluye no atendidas por falta de personal."),
 ("usuarios_demo", "Cuentas de demo por rol con contraseña conocida (solo para la demostración)."),
 ("validacion", "Comparación automática entre lo generado y las cifras oficiales."),
 ("diccionario", "Qué significa cada columna y cómo se calcularon los campos derivados."),
]
for h, d in hojas:
    ws.write(r, 1, h); ws.write(r, 2, d, F["wrap"]); r += 1
r += 1; ws.write(r, 1, "Advertencias", F["st"]); r += 1
for txt in [
 "1. Ubicación aproximada: las coordenadas se reparten alrededor del centro de cada alcaldía. Para ubicar por AGEB real hay que descargar el Censo 2020 por AGEB y el Marco Geoestadístico del INEGI (desde aquí no fue posible descargarlos) y volver a correr el generador.",
 "2. Varias cifras de las fuentes son nacionales (ENSANUT, ENASEM). Se aplican a la CDMX porque no hay prevalencias por enfermedad publicadas para la CDMX y 60+ con este detalle.",
 "3. Los pacientes NO son representativos a propósito: una clínica o asilo atiende más a personas dependientes y con más enfermedades. Se eligieron con mayor probabilidad las personas con más dependencia; los pesos son un supuesto documentado en 'fuentes'.",
 "4. Las contraseñas de 'usuarios_demo' son públicas y solo valen para la demostración.",
]:
    ws.write(r, 2, txt, F["wrap"]); ws.set_row(r, 42); r += 1
r += 1; ws.write(r, 1, "Cómo regenerar", F["st"]); r += 1
ws.write(r, 2, "python generar_base.py csv  →  python armar_excel.py csv  (mismos datos siempre, por la semilla fija). Los CSV sirven para cargar la base PostgreSQL.", F["wrap"])

# ---------------------------------------------------------------- FUENTES
ws = wb.add_worksheet("fuentes")
cols = ["Dato", "Valor usado", "Población / año", "Fuente", "Enlace", "Tipo"]
ws.write_row(0, 0, cols, F["h"]); ws.set_row(0, 22)
for j, w in enumerate([34, 34, 24, 46, 60, 12]): ws.set_column(j, j, w, F["wrap"])
U_UNAM = "https://trabajosocial.unam.mx/politicasocial/material/vivienda/2021/vivie_feb_c_adultos_mayores_cdmx.pdf"
U_SEMU = "https://semujeres.cdmx.gob.mx/storage/app/media/Publicaciones/Boletin_Mujeres_habitando_CDMX_08-2025.pdf"
U_EAP = "https://www.inegi.org.mx/contenidos/saladeprensa/aproposito/2026/EAP_Adulmayor_26.pdf"
U_ENS = "https://ensanut.insp.mx/encuestas/ensanut2018/doctos/analiticos/estado.nutricional.de.los.adultos.mayores.pdf"
U_ENS12 = "https://www.redalyc.org/pdf/106/10628331032.pdf"
U_CON = "https://www.gob.mx/cms/uploads/attachment/file/702736/09_CDMX_PM.pdf"
U_SEPI = "https://sepi.cdmx.gob.mx/storage/app/media/PDFs%20informativos%20SEPI/CENSO2020/mapas-censo-alcaldias.pdf"
U_SEPI2 = "https://sepi.cdmx.gob.mx/storage/app/uploads/public/66f/472/de4/66f472de449dd418314492.pdf"
U_PLAT = "https://www.medigraphic.com/pdfs/neumo/nt-2020/nt201f.pdf"
U_ENA21 = "https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2023/ENASEM/ENASEM_21.pdf"
filas = [
 ("Población de 60+ por alcaldía", "Ver hoja 'alcaldias' (total 1,491,619)", "CDMX, Censo 2020", "INEGI, Censo de Población y Vivienda 2020 (citado por UNAM, Trabajo Social)", U_UNAM, "Real"),
 ("Sexo de la población de 60+", "57.2 % mujeres (853,207), 42.8 % hombres (638,412)", "CDMX, Censo 2020", "INEGI, Censo 2020 (Semujeres CDMX, boletín 2025)", U_SEMU, "Real"),
 ("Grupos de edad", "60-69: 9.0 %, 70-79: 4.8 %, 80+: 2.4 % de la población total", "CDMX, Censo 2020", "Semujeres CDMX con datos de SIESDE", U_SEMU, "Real"),
 ("% de mujeres por grupo de edad (ajuste)", "52.9 / 53.3 / 54.5 % (60-69 / 70-79 / 80+)", "Nacional, ENASEM 2024", "INEGI, Estadísticas a propósito del Día de las Personas Adultas Mayores 2026", U_EAP, "Real"),
 ("Enfermedades por edad y sexo", "Ver hoja 'parametros_enfermedades'", "Nacional 60+, ENSANUT 2018-19", "Salinas-Rodríguez et al. (2020), Salud Pública de México 62:777-785", U_ENS, "Real"),
 ("Artritis, enfermedad pulmonar crónica, cáncer", "18.0 / 7.5 / 5.1 % entre quienes reportan alguna enfermedad × 0.569", "Nacional 60+, ENASEM 2024", "INEGI, EAP 2026. Factor 0.569 = 42.4 (hipertensión ENSANUT) / 74.5 (hipertensión ENASEM entre quienes reportan enfermedad)", U_EAP, "Real + ajuste"),
 ("Deterioro cognitivo y demencia", "7.3 % y 7.9 %", "Nacional 60+, ENSANUT 2012", "Manrique-Espinoza et al. (2013), Salud Pública de México 55 supl. 2", U_ENS12, "Real"),
 ("Multimorbilidad (referencia)", "55.6 %", "Nacional 60+, ENSANUT 2018-19", "Salinas-Rodríguez et al. (2020)", U_ENS, "Real"),
 ("EPOC por espirometría (solo referencia)", "18.4 % en 60+ (incluye casos no diagnosticados)", "Ciudad de México, estudio PLATINO", "Neumología y Cirugía de Tórax, 2020", U_PLAT, "Referencia"),
 ("Afiliación a servicios de salud", "83.4 % afiliados; IMSS 59.3, ISSSTE 25.9, INSABI/IMSS-Bienestar 10.9, privada u otra 5.2, Pemex/Defensa/Marina 1.8", "CDMX 60+, Censo 2020", "CONAPO, Situación sociodemográfica de las personas mayores: Ciudad de México", U_CON, "Real"),
 ("Limitación, discapacidad o condición mental", "49.0 % (hombres 46.5, mujeres 51.0)", "CDMX 60+, Censo 2020", "CONAPO (infografía CDMX)", U_CON, "Real"),
 ("Estado civil por sexo", "H: unión 71.7, viudo 11.9, soltero 7.5, divorciado 8.8; M: 41.8, 31.7, 13.6, 12.8", "CDMX 60+, Censo 2020", "CONAPO (infografía CDMX; asignación de columnas inferida del diseño)", U_CON, "Real (lectura inferida)"),
 ("Habla lengua indígena (60+)", "1.81 %", "CDMX 60+, Censo 2020", "CONAPO (infografía CDMX; lectura de etiqueta ambigua, verificar)", U_CON, "Real (verificar)"),
 ("Lengua indígena por alcaldía (ajuste)", "CDMX 1.4 %, Milpa Alta 3.3, Xochimilco 2.5, Tlalpan 1.7, Iztapalapa ≈1.6 (≈29 mil hablantes)", "Población de 3+, Censo 2020", "SEPI CDMX, mapas del Censo por alcaldía", U_SEPI, "Real"),
 ("Lengua hablada", "1 de cada 3 hablantes habla náhuatl", "CDMX, Censo 2020", "SEPI CDMX", U_SEPI2, "Real; resto de lenguas supuesto"),
 ("Diabetes 53+ por sexo (contraste)", "Hombres 22.5 %, mujeres 28.1 %", "Nacional 53+, ENASEM 2021", "INEGI, comunicado ENASEM 2021", U_ENA21, "Referencia"),
 ("Precios de servicios", "Ver hoja 'catalogo_servicios'", "CDMX, consultado nov 2026", "Doctoralia y Cronoshare (plataformas de cotización); oxígeno: UnoTV 2021", "https://www.cronoshare.com.mx/servicios/enfermeras-domicilio/ciudad-de-mexico/xochimilco", "Real (mercado)"),
 ("SUPUESTO: gradiente de demencia por edad", "Multiplicadores 0.45 / 1.0 / 2.6 (60-69 / 70-79 / 80+), normalizados al total", "—", "Supuesto del equipo; la fuente no publica la prevalencia por edad", "", "Supuesto"),
 ("SUPUESTO: correlación entre enfermedades", "Factor general 0.30; cardiometabólico 0.45; funcional 0.60", "—", "Supuesto calibrado para multimorbilidad amplia ≈ 55.6 % (ENSANUT)", "", "Supuesto"),
 ("SUPUESTO: nivel de dependencia", "Severa: dificultad de autocuidado o demencia con 80+. Moderada: dificultad de actividades con autonomía, fragilidad o demencia. Leve: otra limitación. Independiente: ninguna", "—", "Regla del equipo a partir de los indicadores ENSANUT y del Censo", "", "Supuesto"),
 ("SUPUESTO: selección de pacientes", "Peso = 1 + {Leve 1, Moderada 3, Severa 6} + 0.8 × nº de enfermedades + 0.04 × (edad − 60); asilo ×2.5 si 80+", "—", "Supuesto: las instituciones atienden a personas más dependientes que el promedio", "", "Supuesto"),
 ("SUPUESTO: ubicación", "Centro aproximado de cada alcaldía ± dispersión normal", "—", "Pendiente de reemplazar por AGEB reales (Censo 2020 por AGEB + Marco Geoestadístico)", "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/doc/fd_agebmza_urbana_cpv2020.pdf", "Supuesto"),
 ("SUPUESTO: plan de cuidado, duraciones y personal", "Reglas por enfermedad en el generador; 20 min de traslado entre visitas", "—", "Supuesto, a validar en entrevistas de campo", "", "Supuesto"),
]
for i, f in enumerate(filas, start=1):
    for j, v in enumerate(f):
        if j == 4 and v: ws.write_url(i, j, v, string=v)
        else: ws.write(i, j, v, F["wrap"])
    ws.set_row(i, 42)
ws.freeze_panes(1, 0)

# ---------------------------------------------------------------- PARAMETROS
import importlib.util
spec = importlib.util.spec_from_file_location("gb", "generar_base.py"); gb = importlib.util.module_from_spec(spec); spec.loader.exec_module(gb)
ws = wb.add_worksheet("parametros_enfermedades")
hdr = ["Indicador", "60-69 %", "70-79 %", "80-89 %", "90+ %", "Total %", "Hombres %", "Mujeres %", "Fuente"]
ws.write_row(0, 0, hdr, F["h"]); ws.set_column(0, 0, 30); ws.set_column(1, 7, 11); ws.set_column(8, 8, 40)
r = 1
for k, (ed, t, h, m) in gb.ENSANUT.items():
    ws.write(r, 0, k); ws.write_row(r, 1, ed + [t, h, m]); ws.write(r, 8, "ENSANUT 2018-19 (60+)"); r += 1
for k, (t, h, m) in gb.OTRAS.items():
    ws.write(r, 0, k); ws.write_row(r, 5, [round(t, 1), round(h, 1), round(m, 1)]); ws.write(r, 8, "ENASEM 2024 ajustada (ver 'fuentes')"); r += 1
for k, v in gb.COG_TOTAL.items():
    ws.write(r, 0, k); ws.write(r, 5, v); ws.write(r, 8, "ENSANUT 2012 (60+); gradiente por edad supuesto"); r += 1
ws.freeze_panes(1, 1)

# ---------------------------------------------------------------- ALCALDIAS (con fórmulas)
alc = T["alcaldias"]
pob = T["poblacion_sintetica"]
NP = len(pob)
pc = {c: xl_col_to_name(i) for i, c in enumerate(pob.columns)}
rng_ = lambda c: f"poblacion_sintetica!${pc[c]}$2:${pc[c]}${NP+1}"
ws = wb.add_worksheet("alcaldias")
hdr = ["alcaldia", "cve_mun", "poblacion_60_mas_censo2020", "lat_aprox", "lon_aprox", "hlin_pct_alcaldia",
       "% del total CDMX (Censo)", "personas generadas", "% generado", "diferencia"]
ws.write_row(0, 0, hdr, F["h"]); ws.set_row(0, 30)
for i, row in enumerate(alc.itertuples(), start=1):
    ws.write_string(i, 0, row.alcaldia); ws.write_string(i, 1, str(row.cve_mun).zfill(3))
    ws.write_number(i, 2, float(row.poblacion_60_mas_censo2020), F["intb"])
    ws.write_number(i, 3, float(row.lat_aprox)); ws.write_number(i, 4, float(row.lon_aprox))
    if str(row.hlin_pct): ws.write_number(i, 5, float(row.hlin_pct))
    n = i + 1
    ws.write_formula(i, 6, f"=C{n}/SUM($C$2:$C${len(alc)+1})", F["pct"])
    ws.write_formula(i, 7, f"=COUNTIF({rng_('alcaldia')},A{n})", F["int"])
    ws.write_formula(i, 8, f"=H{n}/SUM($H$2:$H${len(alc)+1})", F["pct"])
    ws.write_formula(i, 9, f"=I{n}-G{n}", F["dif"])
t = len(alc) + 1
ws.write(t, 0, "Total CDMX", F["st"]); ws.write_formula(t, 2, f"=SUM(C2:C{t})", F["int"]); ws.write_formula(t, 7, f"=SUM(H2:H{t})", F["int"])
ws.write(t + 2, 0, "Población 60+: INEGI, Censo 2020. Coordenadas: centro aproximado de la zona urbana (supuesto). hlin_pct: % de población de 3+ que habla lengua indígena (vacío = promedio CDMX 1.4 %).", F["note"])
for j, w in enumerate([24, 9, 16, 10, 10, 12, 14, 12, 11, 11]): ws.set_column(j, j, w)
ws.freeze_panes(1, 1)

# ---------------------------------------------------------------- TABLAS DE DATOS
tabla("poblacion_sintetica", pob, fechas=("fecha_nacimiento",))
tabla("instituciones", T["instituciones"], dinero=("precio_plan_mxn_mes",))
tabla("pacientes", T["pacientes"], fechas=("fecha_alta", "fecha_nacimiento"))
tabla("familiares", T["familiares"])
tabla("consentimientos", T["consentimientos"], fechas=("fecha_firma", "fecha_vencimiento"))
tabla("cuidadores", T["cuidadores"])
tabla("catalogo_servicios", T["catalogo_servicios"], anchos={"nombre": 46, "fuente_precio": 60},
      dinero=("precio_referencia_mxn", "precio_min_mxn", "precio_max_mxn"))
tabla("plan_cuidado", T["plan_cuidado"])
tabla("historial_servicios", T["historial_servicios"], fechas=("fecha",), dinero=("precio_mxn",))
tabla("usuarios_demo", T["usuarios_demo"])

# ---------------------------------------------------------------- VALIDACION (fórmulas)
ws = wb.add_worksheet("validacion")
ws.write(0, 0, "Validación: lo generado contra las cifras oficiales", F["t"])
ws.write(1, 0, "Las metas (azul) vienen de las fuentes. Las columnas 'generado' son fórmulas sobre la hoja poblacion_sintetica; si se regenera la base, se recalculan solas.", F["note"])
hdr = ["Indicador", "Fuente", "Meta total", "Generado total", "Diferencia", "Meta hombres", "Generado hombres", "Meta mujeres", "Generado mujeres"]
ws.write_row(3, 0, hdr, F["h"]); ws.set_row(3, 30)
for j, w in enumerate([34, 30, 11, 13, 11, 12, 13, 12, 13]): ws.set_column(j, j, w)
S = rng_("sexo")
def prom(col, sx=None):
    if sx: return f"=AVERAGEIFS({rng_(col)},{S},\"{sx}\")"
    return f"=AVERAGE({rng_(col)})"
def cuenta(col, val, sx=None):
    if sx: return f"=COUNTIFS({rng_(col)},\"{val}\",{S},\"{sx}\")/COUNTIF({S},\"{sx}\")"
    return f"=COUNTIF({rng_(col)},\"{val}\")/COUNTA({rng_(col)})"
filas = [
 ("Mujeres", "Censo 2020", .572, cuenta("sexo", "M"), None, None, None, None),
 ("60-69 años", "Censo 2020", 9.0/16.2, cuenta("grupo_edad", "60-69"), None, None, None, None),
 ("70-79 años", "Censo 2020", 4.8/16.2, cuenta("grupo_edad", "70-79"), None, None, None, None),
 ("80 años y más", "Censo 2020", 2.4/16.2, cuenta("grupo_edad", "80+"), None, None, None, None),
]
for k, (ed, t_, h, m) in gb.ENSANUT.items():
    filas.append((k, "ENSANUT 2018-19", t_/100, prom(k), h/100, prom(k, "H"), m/100, prom(k, "M")))
for k, (t_, h, m) in gb.OTRAS.items():
    filas.append((k, "ENASEM 2024 ajustada", t_/100, prom(k), h/100, prom(k, "H"), m/100, prom(k, "M")))
filas += [
 ("Demencia", "ENSANUT 2012", .079, cuenta("estado_cognitivo", "Demencia"), None, None, None, None),
 ("Deterioro cognitivo", "ENSANUT 2012", .073, cuenta("estado_cognitivo", "Deterioro cognitivo"), None, None, None, None),
 ("Multimorbilidad amplia", "ENSANUT 2018-19", .556, prom("multimorbilidad_amplia"), .473, prom("multimorbilidad_amplia", "H"), .619, prom("multimorbilidad_amplia", "M")),
 ("Limitación o discapacidad", "Censo 2020 (CONAPO)", .49, prom("limitacion_discapacidad"), .465, prom("limitacion_discapacidad", "H"), .51, prom("limitacion_discapacidad", "M")),
 ("Sin afiliación a servicios de salud", "Censo 2020 (CONAPO)", .166, cuenta("afiliacion_salud", "Sin afiliación"), None, None, None, None),
 ("Habla lengua indígena", "Censo 2020 (CONAPO)", .0181, prom("habla_lengua_indigena"), None, None, None, None),
]
for i, (nom, fuente, mt, gt, mh, gh, mm, gm) in enumerate(filas, start=4):
    n = i + 1
    ws.write(i, 0, nom); ws.write(i, 1, fuente)
    ws.write_number(i, 2, mt, F["pctb"]); ws.write_formula(i, 3, gt, F["pct"]); ws.write_formula(i, 4, f"=D{n}-C{n}", F["dif"])
    if mh is not None:
        ws.write_number(i, 5, mh, F["pctb"]); ws.write_formula(i, 6, gh, F["pct"])
        ws.write_number(i, 7, mm, F["pctb"]); ws.write_formula(i, 8, gm, F["pct"])
last = 4 + len(filas)
ws.write(last + 1, 0, "Diferencia máxima absoluta", F["st"])
ws.write_formula(last + 1, 4, f"=MAX(MAX(E5:E{last}),-MIN(E5:E{last}))", F["pct"])
ws.write(last + 2, 0, "Con 20,000 personas, diferencias menores a ±1.5 puntos se deben al azar del muestreo. La multimorbilidad amplia incluye obesidad y síntomas depresivos para ser comparable con ENSANUT.", F["note"])
ws.freeze_panes(4, 1)

# ---------------------------------------------------------------- DICCIONARIO
ws = wb.add_worksheet("diccionario")
ws.write_row(0, 0, ["Hoja", "Columna", "Descripción"], F["h"])
ws.set_column(0, 0, 22); ws.set_column(1, 1, 26); ws.set_column(2, 2, 100, F["wrap"])
D = [
 ("poblacion_sintetica", "persona_id", "Identificador de la persona ficticia (PS-00001…)."),
 ("poblacion_sintetica", "nombre / apellidos", "Nombres ficticios elegidos al azar de listas de nombres comunes en México."),
 ("poblacion_sintetica", "sexo", "H = hombre, M = mujer (57.2 % mujeres, Censo 2020)."),
 ("poblacion_sintetica", "edad / grupo_edad", "Edad cumplida al 20 nov 2026; grupos 60-69, 70-79, 80+."),
 ("poblacion_sintetica", "alcaldia / cve_mun", "Alcaldía de residencia y su clave INEGI de municipio (entidad 09)."),
 ("poblacion_sintetica", "lat / lon", "Coordenadas APROXIMADAS dentro de la alcaldía (supuesto; reemplazar por AGEB)."),
 ("poblacion_sintetica", "estado_civil", "Según distribución por sexo de la CDMX (CONAPO)."),
 ("poblacion_sintetica", "afiliacion_salud", "Institución de salud (IMSS, ISSSTE, etc.) o 'Sin afiliación'."),
 ("poblacion_sintetica", "habla_lengua_indigena / lengua_indigena", "1 si habla una lengua indígena; cuál (náhuatl ≈ 1 de cada 3)."),
 ("poblacion_sintetica", "diabetes … anemia", "1 = tiene la condición, 0 = no. Prevalencias por edad y sexo (ver 'parametros_enfermedades')."),
 ("poblacion_sintetica", "enf_corazon", "Infarto, angina o insuficiencia cardiaca."),
 ("poblacion_sintetica", "evc_embolia", "Embolia o infarto cerebral (evento vascular cerebral)."),
 ("poblacion_sintetica", "enf_pulmonar_cronica", "Enfermedad pulmonar crónica diagnosticada (incluye EPOC). Clave para la contingencia ambiental."),
 ("poblacion_sintetica", "sintomas_depresivos", "Síntomas depresivos significativos (CES-D ≥ 5 en ENSANUT)."),
 ("poblacion_sintetica", "estado_cognitivo", "Sin deterioro / Deterioro cognitivo / Demencia."),
 ("poblacion_sintetica", "caida_12m", "Caída con lesión en los últimos 12 meses."),
 ("poblacion_sintetica", "fragilidad", "Categoría 'frágil' del índice de fragilidad de ENSANUT."),
 ("poblacion_sintetica", "dif_autocuidado", "Dificultad para bañarse, vestirse o comer (actividades básicas)."),
 ("poblacion_sintetica", "dif_actividades_aut", "Dificultad para actividades diarias con autonomía (instrumentales)."),
 ("poblacion_sintetica", "limitacion_discapacidad", "Limitación, discapacidad o condición mental según el Censo (incluye a quien tiene dificultades funcionales)."),
 ("poblacion_sintetica", "num_enf_cronicas", "Número de enfermedades crónicas diagnosticadas: diabetes, hipertensión, colesterol alto, corazón, embolia, renal, artritis, pulmonar, cáncer."),
 ("poblacion_sintetica", "multimorbilidad", "1 si tiene 2 o más de esas enfermedades crónicas."),
 ("poblacion_sintetica", "multimorbilidad_amplia", "1 si tiene 2 o más contando además obesidad y síntomas depresivos (comparable con ENSANUT, 55.6 %)."),
 ("poblacion_sintetica", "nivel_dependencia", "Severa / Moderada / Leve / Independiente (regla en 'fuentes')."),
 ("pacientes", "paciente_id / institucion_id / persona_id", "Paciente de la plataforma, su institución y la persona de la población sintética de la que proviene."),
 ("pacientes", "fecha_alta", "Fecha en que la institución dio de alta al paciente."),
 ("pacientes", "prioridad_base", "Alta: dependencia severa, enfermedad pulmonar o del corazón. Media: dependencia moderada o 3+ enfermedades. Baja: el resto."),
 ("familiares", "es_representante_legal", "1 si firma por el paciente (paciente con demencia o dependencia severa)."),
 ("consentimientos", "otorgado / vigente", "Si se otorgó y si sigue vigente al 20 nov 2026. Hay casos vencidos o negados a propósito para probar la validación."),
 ("consentimientos", "asentimiento_paciente", "Respuesta del paciente cuando firma un representante: Sí / No / No pudo expresarse / No aplica."),
 ("cuidadores", "habilidades", "Qué servicios puede dar: medico, enfermeria, terapia, cuidado."),
 ("cuidadores", "turno / hora_inicio / hora_fin", "diurno 8-16, mixto 10-18, vespertino 14-22, nocturno 20-08."),
 ("catalogo_servicios", "precio_referencia_mxn", "Precio medio de mercado en CDMX; min y max del rango consultado. Vacío = pendiente."),
 ("catalogo_servicios", "instituciones", "Letras de las instituciones que ofrecen el servicio (A-E)."),
 ("plan_cuidado", "veces_por_semana", "Frecuencia del servicio (0.25 = una vez al mes aprox.)."),
 ("historial_servicios", "estado", "Cerrada / Cancelada por la familia / No atendida (sin personal disponible)."),
 ("historial_servicios", "espera_min", "Minutos entre la hora programada y la llegada del cuidador."),
 ("historial_servicios", "confirmacion_familia", "1 si la familia confirmó la visita (evidencia de cierre)."),
 ("usuarios_demo", "contrasena_demo", "Contraseña pública solo para la demostración."),
]
for i, (h, c, d) in enumerate(D, start=1):
    ws.write(i, 0, h); ws.write(i, 1, c); ws.write(i, 2, d, F["wrap"])
ws.freeze_panes(1, 0)

# orden de hojas: LEEME primero
wb.close()
print("OK", OUT)
