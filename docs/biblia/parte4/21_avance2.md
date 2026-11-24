# Del Avance 2 a la versión final {#cap-avance2}

## En una frase

!!! frase "En una frase"
    **El Avance 2 (*Cuidado Inteligente MX*) diseñó la transacción central para que la coordinadora asignara con ayuda de
    sugerencias; la versión final (*Enlaza*) la volvió automática con aprobación humana en lo delicado, multiplicó las
    instituciones ficticias, cambió varias reglas con razones y agregó voz, simulación, contingencia, ley laboral y negocio.**

## Explicado sin tecnicismos

El Avance 2 fue el plano; Enlaza es la casa construida. Al construir, algunas cosas del plano se confirmaron, otras se
cambiaron porque no funcionaban como se pensaba y otras se agregaron. Este capítulo sirve para responder «¿en qué cambió
respecto a lo que entregaron antes?», y para mostrar que cada cambio tuvo una razón.

Fuentes: *Cuidado Inteligente MX · Avance 2. Lógica funcional del sistema de información (versión 0.8)*, documento del equipo
para SIE, noviembre de 2026, y el *Plan general del proyecto (primer avance)*. Los dos están en `docs/privado/` y no se suben a
Git.

## Por qué lo hicimos así

El propio Avance 2 se presentó como «una primera versión del diseño funcional para revisión, no la solución definitiva». Los
cambios vinieron de tres fuentes: lo que mostró la simulación, lo que exigía la ley (datos personales y trabajo) y lo que se
encontró al usar el sistema (revisiones).

## Cómo funciona por dentro

### Lo que cambió, y por qué

| Tema | Avance 2 | Versión final | Por qué cambió |
|---|---|---|---|
| Nombre | Cuidado Inteligente MX; módulo de voz ORACLE-Voz | **Enlaza · cuidado coordinado**; **Enlaza Voz** | Identidad completa del 23 nov 2026; el nombre de la voz evita confusión con la marca Oracle |
| Quién asigna | la coordinadora decide; el DSS solo sugiere candidatos | **asignación automática**: baja y media se asignan solas; alta la aprueba coordinación; lo urgente sin respuesta, por tiempo | SIRAG-D: esperar a una persona en todo hace esperar más a lo urgente (@ref(cap-sirag)) |
| Instituciones | {{ doc.avance2_instituciones }} (A · Clínica Oriente, B · Residencia Coyoacán) | **{{ seed.institutions }}** (se suman Aragón, Tlalpan e Iztacalco) | Probar el aislamiento y la contingencia del oriente con más variedad |
| Acceso a otra institución | «no encontrado» (para no revelar que existe) | **403 y registro en la bitácora** | La institución prefiere saber que alguien lo intentó; el identificador no revela datos personales |
| Separación | la API filtra y la base repite el filtro con RLS «como segunda barrera» | la **base es la barrera principal** (RLS que falla cerrada) y la API revisa rol y alcance | Encontramos que un filtro olvidado (las vistas) exponía datos: la base debe proteger sola |
| Duplicados | mismo paciente y servicio con otra solicitud abierta en {{ doc.avance2_duplicado }}; **se une** sin preguntar | mismo paciente y servicio a {{ code.duplicate_window_h }}; **se rechaza con motivo** (`duplicate_of`) | Un paciente puede necesitar dos visitas el mismo día; unir sin avisar esconde errores |
| Estados | Registrada → Validada → En cola/Asignada → En curso → Realizada → Cerrada (Rechazada, Cancelada) | lo mismo **más** «sin atender» y «No cerrada» | Lo que pasa la tolerancia y lo que nadie cerró tenían que quedar con un estado propio |
| Escalamiento | más de {{ doc.avance2_escalar }} en cola → escalar | alertas a los {{ code.queue_alert }} (sin personal) y a los {{ code.approval_alert }} (sin aprobar); tolerancia de {{ cfg.late_tolerance }} | Avisar antes y reintentar cada minuto |
| Evidencia de cierre | llegada, salida, resultado y nota; confirmación del familiar; cierre del coordinador | llegada y término con la **hora del servidor**, confirmación de la familia y «No cerrada» automática | La hora la pone el servidor (no el teléfono); la nota de voz sustituye la nota escrita |
| Prioridad | prioridad por solicitud en los bocetos | **prioridad base del paciente**; la familia no la elige; la contingencia puede subirla temporalmente | Si quien pide elige, todo sería urgente |
| Asignar sin traslapes | «el TPS bloquea doble asignación» | **restricción `EXCLUDE` en PostgreSQL**, con el viaje incluido | La base lo garantiza aunque dos peticiones lleguen al mismo tiempo |
| DSS | «simulado» (SIRAG-D sugiere) | **despachador real** en la operación + **SIRAG-D** fuera de línea con el mismo código | Lo que se prueba en simulación es lo que corre en el sistema |
| EIS | futuro | Dirección ve todas las instituciones en Panorama y el negocio; **sin EIS formal** | Suficiente para el prototipo |
| Voz | «extra, si hay tiempo» (Plan General) | **Enlaza Voz completa** con dos niveles de aviso | Se terminó el flujo con texto y se agregó la voz |
| Cobro | suscripción o comisión, por decidir (Plan General) | **suscripción** por tamaño | Ingreso predecible; sin conflicto con instituciones de asistencia privada |
| Nube | futuro | sigue en la laptop + túnel; la nube está **presupuestada** desde el año {{ neg.hosting_start_year }} | Costo cero para el prototipo |
| Notificaciones | WhatsApp o SMS en el futuro | **siguen en el futuro**; avisos dentro de Enlaza | Fuera de alcance |

### Lo que se mantuvo

- La **transacción central** es la solicitud de servicio.
- **Un solo sistema** para las seis materias, sobre la misma base («base común» del Plan General).
- **Datos simulados** por razones éticas, combinados con datos ambientales reales calibrados.
- **ERP acotado**: sin nómina, inventario ni contabilidad.
- La **matriz de permisos** por rol: la familia solo su paciente, el personal solo sus visitas, nadie otra institución.
- La **contingencia ambiental** como escenario de prueba de todo el sistema.

### Lo que el Avance 2 proponía y no se hizo

| Propuesta | Estado | Por qué |
|---|---|---|
| Buscar duplicados de pacientes por nombre, fecha de nacimiento y CURP simulada antes de crear uno | **no implementado** | No hay alta de pacientes desde la app; vienen de la semilla |
| Anonimizar los datos personales al dar de baja a un paciente | **no implementado** | Fuera del alcance del prototipo |
| Corrección de datos por coordinación con motivo y valor anterior en la bitácora | **parcial** | El plan de cuidado se reemplaza (no se edita) y los consentimientos se revocan con motivo; no hay edición general de fichas |
| La familia cancela mientras la solicitud no está asignada | **confirmar en la app** | No se revisó para este libro |
| Tablero de negocio por institución (Plan General) | **no implementado** | El negocio solo lo ve Dirección |

### Las tres dudas del Avance 2, respondidas

1. **¿Basta una base con filtro en la API y RLS, o bases separadas?** Una base con RLS como barrera principal, probada con
   pruebas automáticas y `verify_db.py`.
2. **¿Es válida como evidencia la hora de llegada y salida más la confirmación del familiar?** Es la evidencia que usa Enlaza;
   la hora la pone el servidor y la visita sin cerrar se marca sola. Firma o foto quedan fuera.
3. **¿Duplicado en {{ doc.avance2_duplicado }}, unido sin preguntar?** Se cambió a {{ code.duplicate_window_h }} y rechazo con motivo.

## Dónde está en el código

| Tema | Dónde |
|---|---|
| Asignación automática y aprobaciones | `backend/app/services/operations.py`, `queue.py`, `dispatcher.py` |
| 403 entre instituciones | `backend/app/routers/patients.py`, migración `0001_entity_institution.py` |
| Duplicados | `operations.validate` |
| Estados nuevos | migraciones `0002_operations.py`, `0012_emergency_review_and_not_closed.py` |
| Cinco instituciones | `database/seed/institutions.csv` |

## Números clave

{{ tabla seed.institutions code.duplicate_window_h code.queue_alert code.approval_alert cfg.late_tolerance cfg.auto_apply_after seed.assign_auto seed.assign_coordinator }}

## Limitaciones honestas

- La comparación se basa en el Avance 2 (versión 0.8) y en el Plan General. Si hubo otros avances entregados, no están en el
  repositorio.
- Algunas propuestas del Avance 2 no se implementaron (CURP simulada, anonimización, tablero de negocio por institución).

## Preguntas que te pueden hacer

!!! pregunta "¿En qué cambió el proyecto respecto al Avance 2?"
    La asignación pasó de sugerida a automática con aprobación humana en lo delicado; pasamos de {{ doc.avance2_instituciones }} a {{ seed.institutions }} instituciones;
    el acceso entre instituciones se registra con 403 en vez de ocultarse; los duplicados se rechazan con motivo; y se
    agregaron voz, simulación, contingencia, ley laboral y el modelo de negocio. Cada cambio tiene una razón documentada.

!!! pregunta "¿Por qué ya no es la coordinadora quien asigna?"
    Porque la simulación mostró que, si una persona tiene que decidir todo, lo urgente espera más. Ahora lo rutinario se asigna
    solo y la coordinadora decide lo de prioridad alta. Sigue teniendo la última palabra: puede reasignar cualquier asignación.

!!! pregunta "En el Avance 2 decían «no encontrado» para no revelar que el paciente existe. ¿Por qué cambiaron?"
    Porque con 404 no se distingue un error de dedo de un intento indebido. El identificador no tiene datos personales, y para la
    institución es más valioso saber que alguien lo intentó: el 403 queda en la bitácora.

!!! pregunta "¿Qué cosas del Avance 2 no hicieron?"
    La búsqueda de duplicados por CURP simulada, la anonimización al dar de baja y el tablero de negocio por institución. Las
    dejamos fuera por alcance y lo decimos así.
