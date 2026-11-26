# 09 · Datos y fuentes

Todos los datos del sistema son **sintéticos**. Se generaron para que sus proporciones coincidan con
fuentes oficiales; ningún registro corresponde a una persona real.

## Archivos
| Archivo | Cómo se generó | Calibrado con |
|---|---|---|
| `database/seed/persons.csv` (20,000) | Cópula gaussiana (cargas 0.30 global, 0.45 cardiometabólica, 0.60 funcional) | Censo 2020, ENSANUT 2018-19 (y 2012 para estado cognitivo), ENASEM 2024, CONAPO |
| `database/seed/*` (resto) | `data/generator/legacy_es/generar_base.py` → `to_english_seed.py` | Precios de mercado de servicios, turnos típicos |
| `data/reference/air_quality_*.csv` | `build_reference_data.py` | Reportes SIMAT (máximos diarios O₃ ~93–113 ppb; episodios PM2.5 ~43–60 µg/m³; Fase I PM2.5 de 99.5 µg/m³ en SAC) |
| `data/reference/traffic_hourly_profile.csv` | `build_reference_data.py` | TomTom Traffic Index 2025, CDMX: 75.9 % congestión, ~13 km/h a las 18 h |
| `data/voice/triage_phrases.csv` | `build_triage_phrases.py` | Categorías de signos de alarma |
| `data/business/assumptions.csv` | Manual | DENUE, DataMéxico, Indeed, Banxico, DOF |

Comprobaciones de calibración: multimorbilidad amplia 57.9 % (ENSANUT ≈ 55.6 %); O₃ máximo diario de la red
105 ppb; PM2.5 en episodio 50 µg/m³; congestión laborable 75.9 %.

## Datos oficiales que se descargan en la laptop
`python scripts/download_reference_data.py --year 2025` intenta descargar:
- Catálogo de estaciones y datos horarios de SIMAT (`http://148.243.232.112:8080/opendata/`).
- Límites de alcaldías y colonias del portal de datos abiertos de la CDMX (API CKAN de `datos.cdmx.gob.mx`).
- AGEB del Censo 2020 (INEGI, SCITEL) — manual.

Si algo falla, el sistema sigue con los archivos calibrados. Las coordenadas actuales de las estaciones son
aproximadas (`location_source = approximate`); al descargar el catálogo oficial se actualizan a `official`.

## Fuentes principales
- INEGI, Censo de Población y Vivienda 2020; DENUE — https://www.inegi.org.mx
- INEGI, ENASEM 2024, vía *Estadísticas a propósito del Día Internacional de las Personas Adultas Mayores*,
  comunicado 89/26 (28 sep 2026): % de mujeres por edad (gráfica 1) y enfermedades entre quienes reportaron
  alguna (gráfica 6, p. 5) — https://www.inegi.org.mx/contenidos/saladeprensa/aproposito/2026/EAP_Adulmayor_26.pdf.
  Artritis, enfermedad pulmonar crónica y cáncer se publican **entre quienes reportaron alguna enfermedad**; para
  llevarlas a prevalencia poblacional se multiplican por 0.57 = 42.4 (hipertensión, ENSANUT) / 74.5 (hipertensión,
  ENASEM entre quienes reportan enfermedad). Ese factor es un **supuesto** del generador.
- INEGI, ENASEM 2021 (comunicado 2023): solo como contraste de diabetes por sexo, no se usa para generar datos.
- Prevalencias de referencia que muestra Panorama-AM: `data/reference/prevalence_reference.csv`.
- Límites de alcaldías: INEGI vía Datos Abiertos CDMX, CC BY 4.0 (`data/reference/official/README.md`).
- INSP, ENSANUT — https://ensanut.insp.mx
- SEDEMA, Sistema de Monitoreo Atmosférico — http://www.aire.cdmx.gob.mx
- Portal de Datos Abiertos CDMX — https://datos.cdmx.gob.mx
- TomTom Traffic Index — https://www.tomtom.com/traffic-index/
- Secretaría de Economía, DataMéxico — https://www.economia.gob.mx/datamexico/
- Ley Federal de Protección de Datos Personales en Posesión de los Particulares (DOF 20-03-2025; texto vigente) — https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf
- DOF, Tasas de interés interbancarias de equilibrio (TIIE a 28 días, nov 2026) — https://sidof.segob.gob.mx/notas/docFuente/5803553
- Las URL específicas de cada supuesto de negocio están en la columna `url` de `assumptions.csv`.
