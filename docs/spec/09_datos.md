# 09 · Datos y fuentes

Todos los datos del sistema son **sintéticos**. Se generaron para que sus proporciones coincidan con
fuentes oficiales; ningún registro corresponde a una persona real.

## Archivos
| Archivo | Cómo se generó | Calibrado con |
|---|---|---|
| `database/seed/persons.csv` (20,000) | Cópula gaussiana (cargas 0.30 global, 0.45 cardiometabólica, 0.60 funcional) | Censo 2020, ENSANUT 2018/2022, ENASEM 2021, CONAPO |
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
- INEGI, Censo de Población y Vivienda 2020; ENASEM 2021; DENUE — https://www.inegi.org.mx
- INSP, ENSANUT — https://ensanut.insp.mx
- SEDEMA, Sistema de Monitoreo Atmosférico — http://www.aire.cdmx.gob.mx
- Portal de Datos Abiertos CDMX — https://datos.cdmx.gob.mx
- TomTom Traffic Index — https://www.tomtom.com/traffic-index/
- Secretaría de Economía, DataMéxico — https://www.economia.gob.mx/datamexico/
- DOF, Ley Federal de Protección de Datos Personales en Posesión de los Particulares (20-03-2025) — https://sidof.segob.gob.mx/notas/docFuente/5803553
- Las URL específicas de cada supuesto de negocio están en la columna `url` de `assumptions.csv`.
