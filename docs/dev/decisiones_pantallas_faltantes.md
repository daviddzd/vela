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

### Carga semanal: días laborables (decisión del equipo, 22 nov 2026)
La capacidad semanal es **horas de turno × días laborables por semana**, con `staffing.workdays_per_week` en
`config/simulation.yaml` (**supuesto: 6**). Fuente: Ley Federal del Trabajo, art. 69, texto vigente (última
reforma DOF 14-05-2026; el artículo se reformó el 01-05-2026): «Por cada seis días de trabajo se deberá otorgar,
por lo menos, un día de descanso con goce de salario íntegro». Para cambiarlo: editar el YAML y reiniciar la API
(`docker compose restart api worker`). Un turno de 8 h da 48 h por semana (antes 56 h).

**¿Usan el mismo valor Panorama-AM y SIRAG-D?**
- **Panorama-AM:** no usa días por semana. Compara las horas trabajadas **por día trabajado** con las horas del
  turno de ese día, así que el supuesto no cambia sus resultados.
- **SIRAG-D (resuelto el 22 nov 2026, rama `feature/descanso-semanal`):** ahora cada persona descansa un día
  fijo por semana en la operación y en la simulación (misma función, `backend/app/services/labor.py`), y la
  utilización cuenta solo los días trabajados. Con eso la utilización del escenario normal es **28.1 %** (antes
  26.2 % suponiendo 7 días). Detalle y todas las cifras nuevas: `docs/dev/sirag_d_modelo.md`, secciones 2.1 y 5.

### Hallazgo: jornada legal (LFT arts. 60 y 61)
El tipo de jornada sale de las horas (art. 60), no de la etiqueta: el turno «mixed» de la semilla (10:00–18:00)
es **diurno** (8 h, permitido) y el vespertino 14:00–22:00 es **mixto** (2 h nocturnas) y excedía las 7.5 h: quedó
en 14:00–21:30 en la operación y en la simulación. Los turnos nocturnos de 20:00 a 08:00 (12 h, 4 personas en
INS-B e INS-D) **exceden las 7 h** del art. 61. Vela no cambia la plantilla por su cuenta: `/personal` los marca
«Excede la jornada legal (art. 61)» y el worker crea una alerta para coordinación (una por persona, sin repetir).
Sensibilidad «Cumplir jornada nocturna» (dos turnos de 7 h, 20:00–03:00 y 01:00–08:00): **+4 personas** (44 → 48).
Sin relevos, el «sin atender» subía de 19.1 % a 19.6 % (los servicios de 12 h de noche ya no cabían en un turno
de 7 h). **Con relevos** (sección siguiente) queda en 19.15 % frente a 19.07 %: prácticamente igual. Las crisis
nocturnas atendidas en < 60 min pasan de 43.9 % a 45.0 % (sin diferencia: pocas crisis de noche). Cumplir la
jornada cuesta 4 plazas y ya no empeora el servicio, pero tampoco lo mejora; lo decide cada institución.

### Relevos (decisión del equipo, 22 nov 2026)
Un servicio más largo que cualquier turno legal (más de 8 h, art. 61: SRV-04 y SRV-07, de 12 h) que nadie puede
cubrir solo se cubre con **dos personas consecutivas de la misma habilidad**: la primera trabaja hasta el final de
su turno; la segunda llega en ese momento (la frontera de turno) y se queda hasta el final. Siempre se prefiere a
una sola persona. Misma función en la operación y en SIRAG-D: `dispatcher.relay_options` (desde `rank_candidates`).

En la operación (migración `0011`):
- `assignments.leg`: 1 = primera persona, 2 = relevo; una asignación activa por solicitud **y por tramo**. Las
  dos se guardan juntas o ninguna (la restricción `no_caregiver_overlap` protege a cada persona).
- Aprobaciones: cada propuesta muestra también al relevo y la hora del cambio; la reserva cubre a las dos.
- Visitas: el servicio empieza cuando llega la primera persona y termina cuando termina el relevo. En
  `/mis-visitas` cada quien ve su parte («Te releva…» / «Relevas a…») y su propio botón; el relevo no puede
  registrar su llegada antes que la primera persona.
- Si alguien del relevo queda fuera de servicio o cambia su descanso **antes de que empiece**, se liberan los
  dos y el servicio se vuelve a despachar completo. Si la primera persona ya está en el domicilio y el relevo no
  puede ir, se cancela solo el relevo y coordinación recibe una alerta (`relay_uncovered`) para cubrirlo.
- Reasignar un relevo lo vuelve a planear completo (con la persona elegida como primera).
- Con la plantilla actual nadie necesita relevo (los nocturnos de 12 h cubren solos esos servicios): las corridas
  principales de SIRAG-D no cambiaron (comprobado: resultados idénticos fuera de «Cumplir jornada nocturna»).

## Cobertura de la semana (`/personal`)
Para los próximos 7 días, por día y franja, las habilidades **sin nadie en turno** («martes 8:00–10:00: sin
enfermería»), y quién descansa cada día (`app/services/coverage.py`, función pura; «en turno» es
`dispatcher.within_shift`, la misma regla del despachador). Una habilidad debe estar cubierta en las horas en que
la propia plantilla de la institución tiene a alguien con esa habilidad (la unión de sus turnos); el hueco aparece
cuando ese día nadie está, por descanso o fuera de servicio. No juzga si la plantilla cubre todas las horas que la
institución necesita (por ejemplo, médico de noche): eso lo decide la institución. El worker crea la misma alerta
para coordinación (tipo `coverage`, una por franja, sin repetir) y la resuelve sola cuando el hueco desaparece
(alguien cambió su descanso o volvió a servicio) o ya pasó.

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

## Descanso semanal y día de la defensa (martes 1 dic 2026)
Cada persona tiene un día de descanso fijo (`caregivers.rest_day`, migración `0010`), asignado en rotación con
`labor.assign_rest_days` (la misma función en la migración, en SIRAG-D y en `scripts/reset_demo.py`) y editable en
`/personal`; al cambiarlo, las visitas ya asignadas que caen en el nuevo día se reasignan con el despachador.
Cobertura el martes 1 de diciembre (calculada con `dispatcher.within_shift`, la misma regla de asignación):

| Institución | 9:00 | 15:00 | 22:00 | Descansa ese día |
|---|---|---|---|---|
| INS-A | 7 (cuidados, enfermería) | 13 (las 4 habilidades) | — (institución de día) | Karla Jiménez (terapia, 08–16), Karla Castillo (cuidadora, 08–16) |
| INS-B | 2 (cuidados, terapia) | 7 (las 4 habilidades) | 1 (enfermería) | Daniela Moreno (enfermera, 08–16), Eduardo Reyes (cuidador, 20–08) |
| INS-C | 2 (cuidados, terapia) | 5 (las 4 habilidades) | — | Alejandro Rojas (enfermero, 08–16) |
| INS-D | 1 (cuidados) | 5 (cuidados, enfermería, medicina) | 2 (cuidados, enfermería) | Alejandra Domínguez (enfermera, 08–16) |
| INS-E | 2 (cuidados, terapia) | 4 (cuidados, enfermería, terapia) | — | Karla Vázquez (enfermera, 08–16) |

Todas tienen personal por la mañana y por la tarde. Ojo: en INS-B, C, D y E la única enfermera de turno de
mañana descansa ese martes, así que de 8:00 a 10:00 no hay enfermería hasta que entra el turno de 10:00. Si se
quiere evitar en la demostración, se cambia su día de descanso en `/personal` (las visitas se reasignan solas).
