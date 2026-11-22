# Decisiones técnicas · paso 5 (Panorama-AM)

Rama `feature/panorama`. Capturas de revisión en `docs/dev/capturas/`.

## 1. Datos solo por la API
- `/api/panorama/{operation, population, boundaries, air, traffic, institutions}` usan la sesión con seguridad
  por fila. Coordinación solo ve su institución (el filtro `institution` se ignora); Dirección puede filtrar.
- La población sale **solo** de las vistas agregadas sin nombres (`v_district_population`,
  `v_population_conditions`), con grupos ≥ 10 personas.

## 2. Línea base frente a "Con Vela"
- Migración 0004: `service_requests.is_baseline` = verdadero para las 2,864 solicitudes de la semilla
  (historial sintético de 30 días, despacho manual). Lo que crea el sistema es "Con Vela".
- La gráfica dibuja la línea base gris punteada y "Con Vela" en teal continuo; la tarjeta compara ambos
  periodos y "Con Vela" se llena a medida que hay operación. Puntual = llegada ≤ 15 min (supuesto).

## 3. Carga del personal
Horas de trabajo = tiempo en la visita + traslado estimado con **la misma función del despachador**
(`dispatcher.trip_minutes`: distancia × 1.4 ÷ velocidad de la hora). Hoy: ventanas planeadas; historial:
tiempo real en visita + traslado, promedio por día trabajado.

## 4. Referencias verificadas
- **ENSANUT 2018-19**: Salinas-Rodríguez, De la Cruz-Góngora y Manrique-Espinoza, *Salud Pública Mex.*
  2020;62:777-785 (doi 10.21149/11840). Los 13 valores del CSV y la multimorbilidad 55.6 % coinciden con los
  cuadros II y III (verificado el 21 nov 2026).
- **Multimorbilidad**: ENSANUT cuenta 2+ de 7 condiciones (incluye hipertrigliceridemia; no incluye obesidad
  ni depresión). La "amplia" del generador (57.9 %) suma obesidad y síntomas depresivos: la comparación con
  55.6 % es **aproximada** y la tarjeta lo dice.
- **ENASEM 2024** (no 2021): INEGI, comunicado 89/26, gráfica 6, p. 5. Artritis, pulmonar y cáncer se
  publican entre quienes reportaron alguna enfermedad; se muestran como "Referencia ajustada (supuesto ×0.57)".
- **Límites de alcaldías**: INEGI vía Datos Abiertos CDMX, CC BY 4.0 → se redistribuyen con atribución
  (`data/reference/official/README.md`). Si faltan, la API usa puntos por alcaldía.

## 5. Diseño de gráficas
- Paleta validada con un validador de daltonismo y contraste: teal de gráfica `#00879C`, coral `#E8704A`,
  violeta `#6250D6`; secuencial de 5 tonos teal. El teal de marca `#0F5C6E` no pasa el piso de croma como
  color de serie (se ve gris), así que se queda para la interfaz.
- Sin doble eje: O₃ y PM2.5 en dos gráficas, cada una con su umbral Fase I (`config/simulation.yaml`).
- Leyendas en HTML (no se enciman en el celular), "Ver como tabla" en cada tarjeta, íconos SVG con texto.
- **Cero cruzado**: Atkinson Hyperlegible (y Next) dibujan el 0 con diagonal y no tienen alternativa
  (revisado en las tablas OpenType). Los números grandes usan Lexend (OFL); el texto sigue en Atkinson.
- Fechas `dd/mm/aaaa` con un campo propio: el selector nativo seguía el idioma del navegador.
- ECharts y MapLibre se cargan solo en las pantallas que los usan.

## 6. Capturas
`frontend/scripts/capture.mjs` corre en el contenedor oficial de Playwright dentro de la red de Compose
(no instala navegadores en la laptop). Instrucciones en el encabezado del script.
