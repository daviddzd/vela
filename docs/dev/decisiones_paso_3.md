# Decisiones técnicas · paso 3 (operación: solicitudes, asignación, visitas)

Rama `feature/operacion`. Migración `backend/migrations/versions/0002_operations.py`.

## 1. Fuga de privacidad en las vistas (encontrada y corregida)

**Qué pasaba.** Las vistas de la carga inicial (`v_persons`, `v_patients`, `v_consents`,
`v_service_requests`) se ejecutaban con los permisos de **su dueño** (el comportamiento por omisión
de PostgreSQL). El dueño no está sujeto a la seguridad por fila, así que `vela_api` *sin institución*
podía leer por medio de esas vistas las 400 fichas de pacientes de todas las instituciones, aunque
la tabla `patients` sí estuviera protegida. Lo reprodujimos (en una transacción que se deshizo):

| Consulta como `vela_api`, sin institución | Antes de 0002 | Después |
|---|---|---|
| `SELECT count(*) FROM patients` (tabla) | 0 | 0 |
| `SELECT count(*) FROM v_patients` | **400** | 0 |
| `SELECT count(*) FROM v_consents` | **1,200** | 0 |
| `SELECT count(*) FROM v_persons` | **20,000** | 0 |
 Además, la tabla `persons` (nombres, fecha de nacimiento,
enfermedades) no tenía seguridad por fila.

**Corrección.**
- `ALTER VIEW … SET (security_invoker = true)`: la vista aplica la seguridad por fila de **quien la
  consulta** (`vela_api`), no la de su dueño.
- `persons` con seguridad por fila: una persona solo es visible si es paciente de la institución de la
  sesión. `'*'` (Dirección Vela) ve las 20,000.
- Pruebas: sin institución las 4 vistas devuelven 0 filas; INS-A no encuentra en `persons` ni en
  `v_persons` a la persona de un paciente de INS-B (`backend/tests/test_privacy.py`).

**Tableros de población (paso 5).** Panorama-AM necesita a toda la población sintética, pero no
nombres. Para eso hay dos vistas **agregadas** que, a propósito, sí corren con permisos del dueño:
- `v_district_population`: por alcaldía, número de personas y porcentajes (multimorbilidad,
  dependencia moderada o severa, sensibilidad a contaminación, 80+), promedio de enfermedades.
- `v_population_conditions`: prevalencia de cada condición.

No tienen identificadores, nombres, fechas ni coordenadas, y ocultan cualquier grupo con menos de 10
personas (regla de celdas pequeñas para evitar reidentificación).

## 2. Los 173 traslapes "planeados" de la semilla

`verify_db.py` comprueba **0 traslapes** con los horarios reales (`arrived_at` – `finished_at`). Pero
si se mide con el horario **planeado** (`scheduled_for` + duración), la semilla tiene **173** pares
traslapados: es historial con retrasos y visitas que se recorrieron. Es realista y no se modifica.

Por eso la regla "nunca hay traslapes" no se puede aplicar a las filas históricas; se aplica a toda
asignación **nueva**, que ahora guarda su ventana planeada:
`planned_start` = hora de salida (visita − tiempo de viaje con tráfico) y `planned_end` = fin de la visita.

## 3. La restricción `EXCLUDE` (la base garantiza que no haya traslapes)

```sql
EXCLUDE USING gist (caregiver_id WITH =, tstzrange(planned_start, planned_end) WITH &&)
WHERE (planned_start IS NOT NULL AND status = 'active')
```

- Significa: no pueden existir dos filas con el **mismo cuidador** y ventanas que se **cruzan** (`&&`).
- La revisa PostgreSQL en cada inserción, así que funciona aunque dos solicitudes se despachen en el
  mismo instante (dos peticiones que leyeron la misma disponibilidad): la segunda inserción falla, la
  API recalcula y elige a otra persona (`save_assignment`, prueba `test_retry_when_slot_taken…`).
- **Es parcial**:
  - `planned_start IS NOT NULL`: las filas de la semilla tienen la ventana vacía; un rango con
    extremos nulos sería infinito y bloquearía todo.
  - `status = 'active'`: agregamos `assignments.status` (`active`, `cancelled`, `reassigned`). Una
    asignación cancelada o reasignada se queda como historial, pero ya no ocupa el horario.
- Para reasignar se conserva la fila anterior como `reassigned`; por eso la unicidad "una asignación
  por solicitud" ahora es "una asignación **activa** por solicitud" (índice único parcial).
- Pruebas: la base rechaza un traslape forzado; una asignación nueva convive con la semilla (incluso
  en el mismo horario real de una visita histórica) y con filas `reassigned`.

## 4. Despachador reutilizable

`backend/app/services/dispatcher.py` **no usa la base de datos**: recibe cuidadores, solicitudes y el
perfil de tráfico como datos y devuelve opciones ordenadas. La operación lo llama desde
`operations.py`; SIRAG-D (paso 6) lo importará tal cual, así la simulación prueba el mismo código.

- **Factible** (igual para toda política): habilidad requerida, visita dentro del turno (incluye
  turnos que cruzan medianoche) y sin traslape contando el viaje.
- **Viaje** = distancia en línea recta × 1.4 (circuidad, *supuesto* de `config/simulation.yaml`)
  ÷ velocidad de esa hora (`traffic_hourly_profile`, TomTom 2025). Se usa la velocidad **más lenta**
  entre la hora de salida y la de llegada: mejor llegar antes que tarde. Se mide desde la base del
  cuidador (simplificación del prototipo).
- **Políticas** (`policy`): `nearest` y `human_dispatcher` atienden por orden de llegada y eligen al
  más cercano; `risk_priority` ordena la cola por prioridad → riesgo → espera y elige al más cercano;
  `risk_plus_live_traffic` (la de Vela, por omisión) ordena igual y elige el **menor tiempo de viaje
  con el tráfico de la hora**. El retraso de 5–20 min del despacho humano lo agrega la simulación.
- **Riesgo del paciente** = producto de los multiplicadores de `config/simulation.yaml`
  (enfermedad pulmonar, cardiaca, EVC, diabetes, dependencia, 80+), los mismos que usa SIRAG-D.
- En un lote, cada elección reserva el horario antes de la siguiente: un lote nunca se traslapa.

## 5. Estados y aprobación

`registered → validated → queued → assigned → in_progress → completed → closed`; salidas
`rejected` (no pasó la validación, con motivo), `cancelled`, `unattended` (pasó la hora sin atender).

- **Validación**: paciente activo, consentimiento `home_care` vigente, servicio activo en la
  institución, fecha futura (máx. 30 días) y sin otra igual en ±2 h (`duplicate_of`).
- **Baja / media**: se asigna dentro de la misma petición (`approval='auto'`; prueba < 5 s).
  Como en la semilla, `assigned_by` es el usuario de coordinación de la institución.
- **Alta**: se guardan 3 propuestas (`assignment_proposals`: propuesto + 2 alternativas) y la
  solicitud queda `queued` con motivo `awaiting_approval`. Coordinación aprueba cualquiera (o cambia).
  Al aprobar se recalcula: si esa persona ya no está libre, se guardan opciones nuevas y la pantalla
  las muestra (respuesta 409 con `options`), en lugar de fallar.
- **Familiar**: no elige prioridad; se usa la `base_priority` del paciente.
- **Worker** (cada minuto): reintenta la cola en el orden de la política activa; alerta a
  coordinación si una alta lleva **10 min** sin aprobarse o una solicitud **30 min** sin personal;
  marca `unattended` lo que ya pasó. Cada alerta se crea una sola vez.

## 6. Alcance por rol y consentimiento

- Coordinación: toda su institución. Médico: solo pacientes que tienen o tuvieron una asignación con
  él (CUI-001: 90). Cuidador: solo sus visitas. Familiar: solo su paciente. Fuera de alcance → 403 y
  `blocked_out_of_scope` en la bitácora.
- La ficha del paciente muestra datos de salud solo con `health_data` vigente; si no, responde
  `health: null`, "Falta consentimiento" y registra `health_data_blocked`.
- "Llegué" y "Terminé" vuelven a revisar `home_care` vigente (visita a domicilio, regla 5).
- `/mis-visitas` también está abierta al médico: los médicos hacen consultas a domicilio (SRV-01).

## 7. Detalles para preguntas

- Las horas de llegada y término usan `clock_timestamp()` (reloj real), no `now()` (que en PostgreSQL
  es la hora de *inicio de la transacción*).
- Las pruebas corren dentro de una transacción que se deshace al final; solo quedan en `audit_log`
  los intentos denegados, que se registran en su propia transacción.
