# Pantallas faltantes: /pacientes, /pacientes/:id, /personal y mapas con calles

Rama `feature/pantallas-faltantes`. Capturas en el proyector: `docs/dev/capturas/pantallas/`.

## Auditoría (22 nov 2026)
Contra `docs/spec/04_roles_y_pantallas.md`: `/pacientes` y `/personal` mostraban «Próximamente» y
`/pacientes/:id` no existía. Además: el botón «Nota de voz» de `/mis-visitas` estaba desactivado, `/familia` no
llevaba al asistente de voz, los mapas eran solo el contorno de las alcaldías y quedaba un texto «(pendiente)»
sin usar. Todo eso quedó resuelto; ninguna pantalla de la especificación muestra ya «Próximamente».

## Consentimiento también en las decisiones automáticas (decisión del equipo)
Sin `health_data` vigente:
- el despachador y la cola **no usan el riesgo calculado con datos de salud**: la solicitud compite solo con su
  prioridad (riesgo neutro = 1; `operations.load_request`);
- la contingencia no propone subir de prioridad ni avisar a la familia por «sensible a la contaminación»
  (`contingency.generate_proposals`), y el panel demo no la prefiere para la solicitud urgente;
- `/pacientes` y la ficha muestran «Falta consentimiento» en lugar del riesgo, la dependencia y la sensibilidad.
Pruebas en `backend/tests/test_patients_staff.py`. Anotado en `docs/spec/11_etica_y_privacidad.md`.

## /pacientes y /pacientes/:id (coordinación y médico)
- Lista con búsqueda y filtros (alcaldía, prioridad, dependencia, sensibilidad a la contaminación) e indicador de
  riesgo con texto e icono. El riesgo es el mismo producto de factores que usa el despachador
  (`config/simulation.yaml`); los cortes bajo (< 1.3), medio (1.3 a < 2.0) y alto (≥ 2.0) son **supuesto** del
  equipo (`health_markov.risk_levels`).
- Ficha: datos generales, condiciones de salud (solo con consentimiento), plan de cuidado, historial,
  reportes de voz (el contenido solo lo ve el médico, con consentimiento), familiares (el correo solo coordinación)
  y consentimientos. Abrir la ficha queda en la bitácora (`read_patient`).
- **El médico ajusta el plan** (servicio y veces por semana) solo de sus pacientes. Un plan nunca se edita: el
  viejo termina y uno nuevo lo reemplaza (`replaces`; migración `0009`), con bitácora (`care_plan_created`,
  `care_plan_changed`, `care_plan_ended`). Las solicitudes futuras de ese plan sin asignación se cancelan con
  motivo «plan de cuidado modificado»; las ya asignadas se quedan y coordinación recibe una alerta. El plan nuevo
  se usa desde la siguiente generación del worker.
- **Coordinación crea una solicitud** desde la ficha con el formulario de siempre (la persona ya va elegida).

## /personal (coordinación)
Lista con tipo, habilidades, turno y «en turno ahora»; agenda del día en una línea de tiempo (traslado rayado,
visita sólida, y la misma información en texto); carga de la semana (horas asignadas de lunes a domingo frente a
las horas de su turno en 7 días); «fuera de servicio» con la **misma función** del panel demo
(`caregiver_out_of_service`) y «volver a servicio» (nuevo); mapa con sus bases.

## Mapas con calles
`frontend/src/components/StreetMap.tsx`: MapLibre GL con el estilo «positron» de **OpenFreeMap** (libre, sin
llave) y atribución a OpenStreetMap / OpenMapTiles; encima, los límites de las alcaldías y los puntos (forma +
palabra en la leyenda; detalle al pasar, tocar o enfocar con el teclado). Nombres de lugares en español cuando
OpenStreetMap los tiene. Se usa en el tablero, la contingencia y el personal; Panorama sigue coroplético.
**Respaldo:** sin WebGL, o si el estilo o los mosaicos no cargan en 8 s, se dibuja el mapa de alcaldías de antes
con un aviso. Comprobado bloqueando OpenFreeMap: aparece el respaldo.
**Privacidad:** el servicio de mosaicos solo sabe qué zona de la ciudad se ve; los puntos se dibujan en el navegador.

### Qué hubo que ajustar
- **MapLibre v6 dibuja en un web worker de módulo ES** que Vite no publicaba: el mapa quedaba en blanco
  («Worker failed to load») y caía al respaldo. Se importa con `?worker&url` y `setWorkerUrl`.
- **Tamaño:** si la tarjeta seguía creciendo al crear el mapa, se dibujaba en una franja; ahora sigue su tamaño
  (`ResizeObserver`).
- **Escudos de carreteras** vacíos al traducir nombres: solo se cambian las etiquetas con nombre, no las de número.
- **Playwright:** no hizo falta nada especial. Chromium 1.65 trae WebGL por SwiftShader (ANGLE/Vulkan) incluso
  sin ventana; además se comprobó con **ventana real** bajo `xvfb-run` (`headless: false`): las calles se ven en
  los dos modos. Las capturas se tomaron con ventana.

## Día de la defensa
`scripts/reset_demo.py` también regresa los planes de cuidado a la semilla si alguien los cambió en un ensayo (los
planes creados en el ensayo se desactivan; no se borran porque visitas pasadas pueden apuntar a ellos).
