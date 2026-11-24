# Panorama-AM: ver para decidir {#cap-panorama}

## En una frase

!!! frase "En una frase"
    **Panorama-AM son los tableros de Enlaza: cada tarjeta responde una pregunta concreta de coordinación o de Dirección
    («¿estamos cumpliendo?», «¿dónde vive la población con más riesgo?»), con un número clave grande, una gráfica, su
    fuente y la etiqueta «Datos sintéticos», diseñada para leerse en el proyector y en el celular.**

## Explicado sin tecnicismos

Un buen tablero es como el tablero de un coche: no te muestra todo lo que pasa en el motor, te muestra **lo que
necesitas para decidir ahora** (velocidad, gasolina, una luz roja si algo falla). Panorama-AM sigue esa idea:

- cada tarjeta empieza con una **pregunta** en lenguaje normal;
- debajo, **un número grande** que la responde;
- después, la **gráfica** que lo explica y una nota con la **fuente**;
- y un botón «Ver como tabla» para quien no puede o no quiere leer la gráfica.

## Por qué lo hicimos así

| Decidimos | En lugar de | Por qué |
|---|---|---|
| **Título como pregunta** + número clave | Títulos técnicos («Distribución de…») | Quien decide necesita la respuesta, no el nombre de la gráfica. |
| **Fuente y «Datos sintéticos» en cada tarjeta** | Una sola nota al pie de la página | Regla 11: toda cifra dice de dónde sale. Un profesor puede señalar cualquier tarjeta. |
| **Datos solo por la API**, con seguridad por fila | Que la página lea la base directamente | Coordinación solo ve su institución; Dirección puede filtrar. |
| **Población desde vistas agregadas** (grupos de al menos {{ code.small_cell }}) | Consultar las personas una por una | Panorama no necesita nombres; los grupos chicos se ocultan para que nadie sea reidentificable. |
| **Línea base gris punteada** contra **«Con Enlaza»** en teal | Mostrar solo lo actual | Así se ve el antes y el después en la misma gráfica. |
| **Sin doble eje**: O₃ y PM2.5 en gráficas separadas | Dos contaminantes en una gráfica con dos ejes | El doble eje engaña: la escala de uno hace parecer grande o chico al otro. |
| **Paleta validada para daltonismo** y estados con ícono + palabra | Rojo y verde | Una persona con daltonismo no distinguiría «bien» de «mal» solo por el color. |
| **Coropleta de un solo tono** | Arcoíris de colores | Un solo tono de claro a oscuro se lee como «poco a mucho»; el arcoíris no tiene orden natural. |
| **ECharts y MapLibre** | Imágenes fijas | Gráficas interactivas (pasar el cursor, ver valores) y mapas con calles, cargados solo en las pantallas que los usan. |

## Cómo funciona por dentro

### Dos vistas

**Operación** (coordinación y Dirección; se actualiza en vivo):

| Pregunta | Qué muestra |
|---|---|
| ¿Qué está pasando ahora? | contadores: en cola, en camino, en visita, terminadas hoy |
| ¿Estamos cumpliendo? | puntualidad (llegada a más tardar {{ code.on_time }} tarde, supuesto) y «sin atender» por día: línea base contra «Con Enlaza» |
| ¿Cómo va la carga del personal? | horas de trabajo por persona frente a su turno (visita + traslado, calculado con la misma función del despachador) |
| ¿Quién espera más? | la cola ordenada por prioridad y espera |

**Panorama** (Dirección y coordinación):

| Pregunta | Qué muestra |
|---|---|
| ¿Dónde vive la población 60+ con más riesgo? | coropleta por alcaldía: multimorbilidad, dependencia, sensibilidad a la contaminación, 80+ |
| ¿Qué enfermedades pesan más? | prevalencia sintética contra la referencia ENSANUT o ENASEM |
| ¿Cómo está el aire? | serie por hora de O₃ y de PM2.5 por estación, con la línea del umbral de Fase I |
| ¿Cuándo es peor el tráfico? | mapa de calor hora × tipo de día (TomTom) |

![«¿Estamos cumpliendo?»: puntualidad y «sin atender» por día. La línea punteada es la línea base (historial «antes de Enlaza»); el punto teal, lo que lleva la operación del prototipo.](capturas/tarjeta_operacion_05.png){.media}

![«¿Qué enfermedades pesan más?»: la población sintética (teal) contra la referencia oficial (azul) y la referencia ajustada de la ENASEM (magenta, con el supuesto explicado debajo).](capturas/tarjeta_poblacion_02.png){.media}

### La línea base y «Con Enlaza»

La migración `0004` marca `is_baseline = verdadero` en las {{ seed.service_requests }} solicitudes de la semilla: son el
historial «antes de Enlaza» (despacho manual simulado). Todo lo que crea el sistema es «Con Enlaza». En todo el historial,
la puntualidad de la línea base es {{ seed.punctual_pct }} y el «sin atender», sin contar cancelaciones, es
{{ sim.val_real_nocancel_pct }}; la tarjeta muestra los últimos {{ code.panorama_days }} (por eso sus cifras pueden diferir un poco).

### Carga del personal

Horas de trabajo = tiempo en la visita + traslado estimado con `dispatcher.trip_minutes` (distancia × {{ cfg.circuity }} ÷
velocidad de la hora). Hoy: ventanas planeadas; historial: tiempo real en la visita + traslado, promedio por día trabajado.
Así un profesor no puede decir «el tablero calcula distinto que el despachador»: es la misma función.

### Principios de visualización aplicados

1. **Una pregunta por tarjeta** y el número que la responde arriba.
2. **Comparar con algo**: con la línea base, con la referencia oficial, con el umbral.
3. **Nada solo con color**: estados con ícono y palabra; leyendas en texto; «Ver como tabla» en cada tarjeta.
4. **Ejes honestos**: barras desde cero, sin doble eje.
5. **Paleta validada** (luminosidad, croma, daltonismo protan/deutan/tritan, contraste ≥ 3:1 sobre blanco), documentada en
   `docs/brand.md`.
6. **Probado en celular (390 px) y en proyector (1280 × 720)**, con capturas automáticas.
7. **Leyendas en HTML**, no dentro del lienzo de la gráfica, para que no se encimen en el celular.

### Referencias verificadas

Los valores de referencia (`data/reference/prevalence_reference.csv`) se verificaron contra los cuadros publicados: la
ENSANUT 2018-19 (Salinas-Rodríguez et al., 2020) y la ENASEM 2024 (INEGI, comunicado 89/26). Las tres enfermedades que la
ENASEM publica «entre quienes reportaron alguna» se muestran como «Referencia ajustada (supuesto ×{{ gen.enasem_factor }})», y
la tarjeta lo explica (@ref(cap-datos)).

## Dónde está en el código

| Qué | Dónde |
|---|---|
| Rutas (`/api/panorama/operation`, `population`, `air`, `traffic`, `boundaries`, `institutions`) | `backend/app/routers/panorama.py` |
| Vistas agregadas de población | `v_district_population`, `v_population_conditions` (migraciones `0002`, `0004`) |
| Pantalla y vistas | `frontend/src/pages/PanoramaPage.tsx`, `frontend/src/pages/panorama/` |
| Tarjeta común (pregunta, número, fuente, tabla) | `frontend/src/components/ChartCard.tsx` |
| Tema de las gráficas (paleta) | `frontend/src/charts/theme.ts` |
| Límites de alcaldías | `data/reference/official/district_boundaries.geojson` (INEGI vía Datos Abiertos CDMX, CC BY 4.0) |
| Pruebas | `backend/tests/test_panorama.py`, `frontend/scripts/ui_checks.mjs` |
| Decisiones | `docs/spec/07_panorama_am.md`, `docs/dev/decisiones_paso_5.md` |

## Números clave

{{ tabla code.on_time seed.punctual_pct sim.val_real_nocancel_pct seed.broad_multimorbidity_pct cal.ref_multimorbidity seed.hypertension_pct cal.ref_hypertension code.small_cell ref.air_stations ref.traffic_rows repo.tests_panorama }}

## Limitaciones honestas

- **«Con Enlaza» tiene pocos datos**: se llena con la operación del prototipo (unos días, con ensayos que se limpian). No es
  una comparación estadística; para eso está SIRAG-D.
- **«Puntual» = a lo más {{ code.on_time }} tarde** es un supuesto del equipo.
- **La población es sintética**: el mapa de riesgo muestra el mundo simulado, no a la CDMX real persona por persona.
- **El aire es la serie calibrada**, no la medición oficial del día.
- **No hay un EIS** (tablero ejecutivo) separado: Dirección usa Panorama con filtro por institución.

## Preguntas que te pueden hacer

!!! pregunta "¿Qué diferencia hay entre MIS y DSS en Panorama-AM?"
    La vista Operación es un MIS: resume lo que pasa (cola, puntualidad, carga) para controlar la operación. La parte que
    compara alternativas (la simulación de políticas y la propuesta de contingencia) es DSS: ayuda a elegir entre opciones.

!!! pregunta "¿Por qué cada gráfica tiene un título en forma de pregunta?"
    Porque un tablero sirve para decidir. Si el título es la pregunta («¿estamos cumpliendo?») y el número grande la
    respuesta, cualquiera entiende la tarjeta en segundos, aunque no sepa leer la gráfica.

!!! pregunta "¿Cómo se aseguran de que se lea con daltonismo?"
    La paleta se validó con un validador de daltonismo (protan, deutan, tritan) y de contraste, y ningún estado depende solo
    del color: siempre lleva ícono y palabra. Además, cada tarjeta tiene «Ver como tabla».

!!! pregunta "¿Por qué no pusieron O₃ y PM2.5 en una sola gráfica?"
    Porque necesitarían dos ejes con escalas distintas, y el doble eje engaña: según cómo se escalen, uno parece más
    grave que el otro. Van en dos gráficas, cada una con su umbral de Fase I.

!!! pregunta "¿Panorama puede mostrar datos de una persona?"
    No. La población sale solo de vistas agregadas por alcaldía o condición, sin nombres ni identificadores, y los grupos de
    menos de {{ code.small_cell }} personas se ocultan.

!!! pregunta "¿El tablero de carga calcula igual que el despachador?"
    Sí: usa la misma función de viaje (`dispatcher.trip_minutes`). Así no hay dos versiones del tiempo de traslado.
