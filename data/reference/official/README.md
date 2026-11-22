# Datos oficiales descargados

`scripts/download_reference_data.py` guarda aquí los archivos oficiales (SIMAT, datos.cdmx, INEGI).
Por tamaño o licencia **no se suben a GitHub**, salvo la excepción de abajo; cada integrante los descarga
con el script.

## Excepción: `district_boundaries.geojson` (sí está en el repositorio)

| Campo | Valor |
|---|---|
| Conjunto | Límite de Alcaldías (áreas geoestadísticas municipales), identificador `alcaldias` |
| Productor | Instituto Nacional de Estadística y Geografía (INEGI) |
| Publicado en | Portal de Datos Abiertos de la Ciudad de México — https://datos.cdmx.gob.mx/dataset/alcaldias |
| Recurso | GeoJSON "Limite de las Alcaldías" (recurso `deb5c583-84e2-4e07-a706-1b3a0dbc99b0`, actualizado el 28 ago 2026) |
| Licencia | **CC-BY-4.0-ESP** (Creative Commons Atribución 4.0): permite copiar y redistribuir citando la fuente |
| Fecha de descarga | 21 nov 2026 |
| SHA-256 | `c02e3bb3e42281cf874b8e26b68514a7f34189b6209af51e79f7d1a87b0f1285` |
| Contenido | 16 polígonos; propiedades `CVEGEO` (= `districts.district_id`), `CVE_ENT`, `CVE_MUN`, `NOMGEO` |

Atribución que se muestra en la app: "Límites de alcaldías: INEGI, vía Datos Abiertos CDMX (CC BY 4.0)".

`neighborhoods.geojson` (colonias, ~6 MB) **no** se sube; solo lo usa el script como respaldo para
reconstruir los límites si la descarga directa falla.
