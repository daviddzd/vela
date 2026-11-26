# Modelado y Simulación {#cap-m-sim}

<p class="responsable">Responsable: {{ equipo.materias.simulacion }}</p>

## En una frase

!!! frase "Lo que aporta esta materia"
    **SIRAG-D es un modelo de simulación de eventos discretos con agentes (pacientes con una cadena de Markov de salud),
    validado contra el historial, que compara cinco políticas de asignación en tres escenarios con
    {{ cfg.replications }} réplicas, intervalos de confianza y pruebas pareadas, y cuyo hallazgo cambió el producto real.**

## Qué evalúa el profesor

| Pide | Documento y sección | Dónde se responde |
|---|---|---|
| Entregable: «Simulador de Optimización de Servicios de Cuidado (Agentes/Markov)» | PP, «Evidencia integradora», p. 2 | conceptos (abajo); @ref(cap-sirag) |
| Enfoque híbrido: eventos discretos (SimPy) + modelado basado en agentes | PP, «Incidente crítico de la UCA: Modelo y Simulación», p. 13 | «Simulación de eventos discretos» y «Agentes» (abajo) |
| Optimizar distancias y costos de traslado y equilibrar la carga del personal | PP, p. 13 | km recorridos, horas extra y utilización como métricas; desempate por carga (abajo y @ref(cap-operacion)) |
| Que la simulación no se rompa ante perturbaciones extremas (contingencia, bloqueos, demanda que se dispara) y que priorice el riesgo clínico | PP, p. 13; «Problemas suscitados», p. 7 | «Respuesta al incidente crítico» (abajo) |
| El dilema: ceder el control a despachadores humanos o recalibrar el modelo en caliente | PP, p. 13; «Dilemas que plantea», p. 8 | «Respuesta al incidente crítico» |
| Simular la red (instituciones, pacientes, cuidadores, servicios) y probar reglas de asignación en un día normal y en una contingencia; entregar propuestas de asignación con tiempos de respuesta | Plan SIE, secciones 2 y 3 | @ref(cap-sirag) |
| Rigor metodológico y estadístico (argumentación científica) | PP, «Rúbrica Analítica», p. 4 | validación, IC, Friedman/Wilcoxon/Holm, sensibilidad (abajo) |
| Rúbrica propia de la materia | **no lo dicen los documentos: confirmar con el profesor** | — |

## Los conceptos, desde cero

### Modelo y simulación

**Qué es.** Un modelo es una versión simplificada de la realidad que conserva lo importante para una pregunta. Simular es
«correr» ese modelo en la computadora para ver qué pasaría.

**Ejemplo.** Un simulador de manejo: no es un coche real, pero tiene volante, frenos y tráfico, y sirve para practicar.

**En Enlaza.** Pregunta: *¿qué política de asignación atiende mejor a los pacientes de mayor riesgo cuando hay
contingencia ambiental y tráfico?* (@ref(cap-sirag)).

### Simulación de eventos discretos

**Qué es.** El reloj salta de un evento al siguiente (llega un cliente, termina un servicio) en lugar de avanzar segundo
a segundo. Entre eventos no pasa nada que importe.

**Ejemplo.** La fila de un banco: solo importa cuándo llega alguien y cuándo termina con el cajero.

**En Enlaza.** [[Simulación de eventos discretos]] con **SimPy**: eventos de salud cada hora, publicación de visitas del
plan, ciclo de despacho cada {{ code.sim_cycle }}, llegadas y términos de visitas. Una semana se simula en segundos.

### Agentes

**Qué es.** Entidades del modelo con estado y reglas propias. **En Enlaza:** cada paciente es un agente con su riesgo y su
estado de salud; el personal es un **recurso** con turnos y habilidades.

### Cadena de Markov

**Qué es.** Un sistema que pasa entre estados con probabilidades que dependen **solo del estado actual**, no de la
historia.

**Ejemplo.** El clima simplificado: si hoy llueve, mañana llueve con 60 %; si hoy hay sol, mañana llueve con 20 %. No
importa cómo estuvo la semana pasada.

**En Enlaza.** [[Cadena de Markov]] por hora: estable → en riesgo con {{ cfg.markov_stable_to_at_risk }} (× riesgo del paciente
× efecto del aire); en riesgo → estable con {{ cfg.markov_at_risk_to_stable }}; en riesgo → crisis con
{{ cfg.markov_at_risk_to_crisis }}; la crisis se resuelve al atenderse. Son **supuestos** calibrados.

### Variables aleatorias y distribuciones

**Qué es.** Una cantidad que sale de un sorteo con reglas (una distribución). **Uniforme:** todos los valores de un rango
igual de probables. **Poisson:** cuántas veces pasa algo en un periodo si ocurre a un ritmo promedio. **Bernoulli:** sí/no
con una probabilidad.

**En Enlaza.** Retraso del despacho humano: uniforme de {{ cfg.human_delay }}. Visitas del historial de la semilla:
[[Poisson]]. Cambio de estado de salud cada hora: Bernoulli con la probabilidad de la cadena.

### Semilla y números pseudoaleatorios

**Qué es.** Las computadoras generan números que parecen al azar a partir de una **semilla**; con la misma semilla salen
los mismos números. Eso hace el experimento **reproducible**.

**En Enlaza.** Semilla {{ gen.seed }}, derivada por réplica y por lo que se sortea (paciente-hora, plan-día, solicitud).

### Números aleatorios comunes

**Qué es.** Usar **los mismos sorteos** para todas las alternativas que se comparan, para que la diferencia se deba a la
alternativa y no a la suerte. Las muestras quedan **pareadas**.

**Ejemplo.** Para comparar dos marcas de llantas, las pones en el mismo coche, el mismo día, en la misma pista.

**En Enlaza.** En la réplica *r* las cinco políticas enfrentan las mismas visitas y las mismas crisis
([[números aleatorios comunes]]).

### Réplicas

**Qué es.** Repetir la simulación con semillas distintas para medir la variación del resultado. Una sola corrida puede
salir «de suerte».

**En Enlaza.** {{ cfg.replications }} réplicas de {{ cfg.horizon_days }} días por combinación: {{ sim.runs_main }} corridas
principales.

### Media, percentil y p90

**Qué es.** La **media** es el promedio. El **percentil 90 (p90)** es el valor por debajo del cual queda el 90 % de los
casos: describe «los casos malos» sin dejarse llevar por el peor de todos.

**Ejemplo.** Si el p90 del tiempo de entrega de una pizzería es 40 min, 9 de cada 10 pizzas llegan en 40 min o menos.

**En Enlaza.** La métrica principal es la **espera p90 de prioridad alta**: lo que importa en urgencias es no dejar
esperar mucho a nadie, no solo el promedio.

### Intervalo de confianza

**Qué es.** Un rango que, con un nivel de confianza (en Enlaza, {{ cfg.confidence }}), contiene el valor verdadero del promedio. Más réplicas →
intervalo más angosto.

**Ejemplo.** Una encuesta dice «42 % ± 3 puntos»: el valor real probablemente está entre 39 % y 45 %.

**En Enlaza.** Espera p90 de prioridad alta, Enlaza: {{ sim.normal.vela_timeout.high_wait_p90_min }} min
[{{ sim.normal.vela_timeout.high_wait_p90_min.ci }}]; despacho humano: {{ sim.normal.human_dispatcher.high_wait_p90_min }}
[{{ sim.normal.human_dispatcher.high_wait_p90_min.ci }}].

### Verificación y validación

**Qué es.** **Verificar**: el código hace lo que el modelo dice (no hay errores de programación). **Validar**: el modelo se
parece a la realidad para la pregunta que se hace.

**En Enlaza.** Verificación: pruebas automáticas (`simulation/tests/test_sirag.py`, incluida la que comprueba que se usa el
mismo despachador). Validación: con las reglas de antes, el «sin atender» de servicios cortos da {{ sim.val_sim_short_pct }}
contra {{ sim.val_real_short_pct }} del historial; con turnos largos difiere y se explica por qué.

### Prueba de hipótesis y valor p

**Qué es.** Se parte de la hipótesis «no hay diferencia» (nula). El **valor p** es la probabilidad de ver una diferencia
tan grande si en verdad no hubiera ninguna. Si p < 0.05, se rechaza la nula: la diferencia es **significativa**.

**Ejemplo.** Lanzas una moneda 100 veces y salen 70 águilas. Si la moneda fuera justa, eso sería rarísimo (p muy chico):
probablemente está cargada.

### Normalidad: Shapiro-Wilk

**Qué es.** Prueba si unos datos parecen venir de una distribución normal (la campana). Decide qué prueba usar después.

### ANOVA, Kruskal-Wallis, Friedman y Wilcoxon

**Qué es.** Pruebas para comparar grupos.

| Prueba | Para qué | Supone |
|---|---|---|
| ANOVA de una vía | 3+ grupos independientes | normalidad |
| Kruskal-Wallis | 3+ grupos independientes | nada de normalidad (usa rangos) |
| ANOVA de medidas repetidas | 3+ tratamientos sobre los mismos casos | normalidad |
| **[[Friedman]]** | 3+ tratamientos sobre los mismos casos | nada de normalidad |
| *t* pareada | 2 tratamientos sobre los mismos casos | normalidad |
| **[[Wilcoxon]]** de rangos con signo | 2 tratamientos sobre los mismos casos | nada de normalidad |

**En Enlaza.** Como las muestras están pareadas y las diferencias casi nunca son normales: **Friedman** para la comparación
global y **Wilcoxon** de cada política contra el despacho humano. Por ejemplo, espera p90 en escenario normal:
{{ test.normal.high_wait_p90_min.omnibus }}; Enlaza contra humano, {{ test.normal.high_wait_p90_min.vela_timeout.p }}.

### Comparaciones múltiples: corrección de Holm

**Qué es.** Si haces muchas pruebas con p < 0.05, alguna saldrá «significativa» por casualidad. [[Holm]] ajusta los valores
p para que eso no pase.

**Ejemplo.** Si lanzas 20 dardos al azar, alguno pega cerca del centro; no significa que seas buen tirador.

### Análisis de sensibilidad

**Qué es.** Mover un supuesto dudoso (uno a la vez) para ver si la conclusión cambia.

**En Enlaza.** Rapidez de aprobación (inmediata, 1–5, 5–15 min), riesgo de crisis (×1, ×2, ×3) y plantilla (actual con {{ sens.extra_staff.current.vela_timeout.staff }} personas, con refuerzos, con refuerzos dirigidos,
jornada nocturna legal). Con aprobación de 5–15 min, Enlaza (hoy)
{{ sens.approval_delay.5-15.vela_timeout.high_wait_p90_min }} contra {{ sens.approval_delay.5-15.human_dispatcher.high_wait_p90_min }}
del humano.

### Escenarios

**Qué es.** Condiciones del mundo que se prueban (no decisiones). **En Enlaza:** normal, contingencia en el oriente y
contingencia + bloqueo vial.

## Respuesta al incidente crítico de Modelado y Simulación

**El incidente** (PP, p. 13): un simulador calibrado para minimizar kilómetros con demanda «normal» colapsa en una
contingencia con bloqueos y demanda que se dispara un {{ doc.pico_crisis }}. Sigue mandando al personal por la ruta
«más corta» histórica, ignora el tráfico y atiende primero los chequeos cercanos que a los pacientes graves. Las
respuestas superan {{ doc.sim_respuesta }}. El dilema: pasar el control a despachadores humanos (lento) o hacer un *hotfix*
con variables no validadas (inestable).

**Por qué SIRAG-D no cae en esas fallas, y dónde todavía podría:**

| Falla del incidente | SIRAG-D / Enlaza |
|---|---|
| Ordena por cercanía | ordena la cola por **prioridad → riesgo → espera**; una crisis entra como prioridad alta |
| Ruta corta histórica sin tráfico | elige por **tiempo de viaje con la velocidad de esa hora**; el escenario con bloqueo multiplica el tráfico ×{{ cfg.roadblock_factor }} y suma {{ cfg.blockade_minutes }} por viaje que cruza Iztapalapa |
| Sin recalibración ante perturbaciones | los escenarios de contingencia y bloqueo se prueban **antes**, con {{ cfg.replications }} réplicas; en la operación, la contingencia se detecta sola y **propone** ajustes que una persona aprueba |
| Demanda que se dispara | sensibilidad con el riesgo de crisis ×2 y ×3: la espera de lo urgente sube, pero Enlaza mantiene su ventaja ({{ sens.risk_multiplier.3.vela_timeout.high_wait_p90_min }} contra {{ sens.risk_multiplier.3.human_dispatcher.high_wait_p90_min }} min de p90 con ×3) |

**El experimento que reproduce el incidente:** la política `nearest` (más cercano, por orden de llegada) es justo el
simulador del incidente. En el escenario de contingencia + bloqueo, su espera p90 de prioridad alta es
{{ sim.contingency_east_roadblocks.nearest.high_wait_p90_min }} min, contra {{ sim.contingency_east_roadblocks.vela_timeout.high_wait_p90_min }}
de Enlaza ({{ test.contingency_east_roadblocks.high_wait_p90_min.vela_timeout.p }} contra el despacho humano).

**Ante el dilema, la postura del equipo:** ni manual total ni *hotfix* a ciegas. La asignación automática usa reglas que
**ya se validaron en simulación**, coordinación aprueba lo delicado y, si no responde a tiempo en lo urgente, se aplica la
propuesta con aviso (el límite de tiempo, que salió de esta misma simulación). No usamos aleatorización sesgada
(*biased randomization*): no la necesitamos y no está validada.

**Lo que no cubre:** un aumento de demanda de {{ doc.pico_crisis }} no se simuló exactamente (el ×3 del riesgo es lo más
cercano); el tráfico es un promedio por hora, no tráfico en vivo; el costo en pesos de los traslados no se reporta, solo los
km ({{ sim.normal.vela_timeout.travel_km }} por semana).

## Por qué lo hicimos así

- **SimPy** porque es Python (el lenguaje del equipo) y es una biblioteca estándar de eventos discretos.
- **El mismo despachador** de la operación, para que las conclusiones valgan para el sistema real.
- **Friedman/Wilcoxon** y no ANOVA de una vía, porque las muestras están pareadas.
- **La sensibilidad aparte**, para no mezclar supuestos dudosos con el resultado principal.
- **Corrida fuera de línea y acelerada**, porque la operación usa el reloj real.

## Dónde se ve en el sistema

| Concepto | Dónde |
|---|---|
| Diagrama y supuestos | `docs/dev/sirag_d_modelo.md` y @ref(cap-sirag) |
| Cadena de Markov | `simulation/sirag/model.py` (`health`), `config/simulation.yaml` (`health_markov`) |
| Réplicas en paralelo | `simulation/sirag/runner.py`, `simulation/experiments/run.py` |
| Pruebas estadísticas | `simulation/sirag/stats.py` → `simulation/results/tests.csv` |
| Resultados con IC | `simulation/results/summary.csv`; pantalla `/simulacion` |
| Hallazgo que cambió el producto | `/simulacion` («Hallazgo de la simulación») y `backend/app/services/queue.py` |

## Números clave

{{ tabla cfg.replications cfg.horizon_days cfg.confidence sim.runs_main sim.runs_sensitivity sim.runs_validation sim.elapsed_s cfg.markov_stable_to_at_risk cfg.markov_at_risk_to_crisis sim.normal.vela_timeout.high_wait_p90_min sim.normal.human_dispatcher.high_wait_p90_min sim.val_real_short_pct sim.val_sim_short_pct }}

## Limitaciones honestas

- Las probabilidades de salud y varios parámetros son **supuestos**.
- El efecto del aire viene de estudios **diarios** aplicado **por hora**.
- La validación es **aproximada**.
- El despacho humano es un **modelo simplificado**.
- Una semana por réplica: no hay efectos de largo plazo.

## Qué decir en 2 minutos

!!! frase "Guion de 2 minutos · Modelado y Simulación"
    «SIRAG-D responde: ¿qué forma de asignar visitas atiende mejor a los pacientes de más riesgo cuando hay contingencia y
    tráfico? Es una **simulación de eventos discretos** en SimPy: cada paciente tiene una **cadena de Markov** por hora,
    estable, en riesgo o crisis, con probabilidades que suben con sus enfermedades y con el PM2.5. Las crisis generan
    solicitudes urgentes y el personal tiene sus turnos reales y su descanso de ley.

    Lo importante: la simulación usa **el mismo código de asignación** que la operación. Comparamos cinco políticas en tres
    escenarios con {{ cfg.replications }} réplicas de una semana y **números aleatorios comunes**, así que cada comparación es
    pareada; por eso usamos **Friedman y Wilcoxon con Holm** y no ANOVA de una vía.

    Primero **validamos**: con las reglas de antes, el modelo reproduce el historial en servicios cortos. Resultado: Enlaza
    baja la espera p90 de lo urgente de {{ sim.normal.human_dispatcher.high_wait_p90_min }} a
    {{ sim.normal.vela_timeout.high_wait_p90_min }} minutos ({{ test.normal.high_wait_p90_min.vela_timeout.p }}), pero no el «sin
    atender», que depende del personal.

    Y la **sensibilidad** encontró algo que cambió el producto: con una coordinación lenta, lo urgente esperaba de más. Por eso
    agregamos el límite de tiempo y la reserva del candidato.»

## 10 preguntas difíciles

!!! pregunta "1. ¿Por qué eventos discretos y no dinámica de sistemas o un modelo analítico de colas?"
    Porque nos interesan casos individuales (qué enfermera va a qué paciente, cuándo, con qué tráfico) y reglas complejas
    (turnos, descansos, relevos, aprobaciones). Un modelo de colas analítico supone llegadas y servicios simples; la
    dinámica de sistemas trabaja con agregados, no con personas.

!!! pregunta "2. ¿De dónde salen las probabilidades de la cadena de Markov?"
    Son supuestos documentados en `config/simulation.yaml`, calibrados para que las crisis sean poco frecuentes. Los
    multiplicadores por enfermedad también son supuestos; los efectos del PM2.5 sí vienen de estudios publicados. Lo
    decimos así y lo probamos con sensibilidad (riesgo ×2 y ×3).

!!! pregunta "3. ¿Por qué 30 réplicas?"
    Con {{ cfg.replications }} réplicas los intervalos de confianza ya separan las políticas en las métricas principales y el
    cómputo cabe en minutos ({{ sim.elapsed_s }} s para todo). Además 30 es suficiente para que las pruebas por rangos tengan
    buena potencia.

!!! pregunta "4. ¿Qué diferencia hay entre verificar y validar? ¿Qué hicieron de cada una?"
    Verificar es que el código haga lo que el modelo dice: pruebas automáticas, incluida una que comprueba que se usa el
    despachador de la operación. Validar es que el modelo se parezca a la realidad: comparamos el «sin atender» simulado con
    el del historial usando las reglas de antes.

!!! pregunta "5. La validación no coincide. ¿El modelo está mal?"
    Coincide en servicios cortos ({{ sim.val_sim_short_pct }} contra {{ sim.val_real_short_pct }}) y difiere en turnos largos por
    una razón concreta: el generador de la semilla asignaba esos turnos con dos horas de retraso y la simulación aplica la
    tolerancia acordada de {{ cfg.late_tolerance }}. Sabemos por qué difiere, que es lo que exige una validación honesta.

!!! pregunta "6. ¿Por qué Friedman y no ANOVA?"
    Porque las cinco políticas se prueban sobre las mismas réplicas (números aleatorios comunes): son medidas repetidas,
    no grupos independientes. Y Shapiro-Wilk mostró que las diferencias casi nunca son normales, así que usamos la versión
    no paramétrica pareada: Friedman y Wilcoxon.

!!! pregunta "7. ¿Qué es la corrección de Holm y por qué la usaron?"
    Comparamos varias políticas contra el despacho humano; con muchas pruebas, alguna saldría significativa por casualidad.
    Holm ajusta los valores p para mantener la probabilidad total de un falso positivo en 5 %.

!!! pregunta "8. ¿Por qué el p90 y no el promedio?"
    Porque en urgencias importa que nadie espere demasiado. El promedio puede verse bien aunque unos pocos esperen muchísimo;
    el p90 mira a «los casos malos».

!!! pregunta "9. ¿Qué es un análisis de sensibilidad y qué les mostró?"
    Mover un supuesto a la vez para ver si la conclusión cambia. Mostró que con una aprobación lenta lo urgente esperaba de
    más (esto cambió el producto) y que contratar donde está el cuello de botella baja el «sin atender» a
    {{ sens.extra_staff.targeted.vela_timeout.unattended_pct }}.

!!! pregunta "10. En el incidente, el simulador manda por la ruta más corta y atiende primero lo cercano. ¿El suyo haría lo mismo?"
    No, porque ordena por prioridad y riesgo y elige por tiempo de viaje con el tráfico de la hora. Y lo podemos mostrar: la
    política «más cercano» es justo la del incidente, y en contingencia con bloqueo su espera p90 de lo urgente es
    {{ sim.contingency_east_roadblocks.nearest.high_wait_p90_min }} min contra {{ sim.contingency_east_roadblocks.vela_timeout.high_wait_p90_min }}
    de Enlaza. Siendo honestos, la mayor parte de la mejora viene de priorizar, no del tráfico, que en nuestro modelo es un
    promedio por hora.
