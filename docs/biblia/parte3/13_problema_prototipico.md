# Lo que pide el Problema Prototípico y cómo responde Enlaza {#cap-m-pp-doc}

## En una frase

!!! frase "En una frase"
    **El documento oficial del curso pide un portafolio interdisciplinario, el SIPC-AM, con seis entregables que deben
    funcionar como un solo sistema y resistir un incidente crítico: una contingencia ambiental con bloqueos viales. Este
    capítulo resume qué pide, cómo se califica y dónde responde Enlaza a cada punto.**

## Explicado sin tecnicismos

Los profesores no van a calificar seis tareas separadas. Van a calificar si las seis piezas **trabajan juntas** cuando las
cosas salen mal. El documento lo dice con un ejemplo: un tablero que promedia, un simulador que manda al personal por calles
bloqueadas, un clasificador de voz que no entiende a hablantes de lenguas originarias, sistemas que no se hablan entre sí, un
consentimiento firmado por conveniencia y un plan de negocios que promete demasiado. Cada capítulo de esta Parte III dice
qué pide el documento de esa materia y dónde está la respuesta.

La Parte III está organizada **por materia porque así evalúa el sínodo**, pero **todo el equipo defiende todo**: no nos
dividimos por materias, y cualquiera de nosotros debe poder responder cualquier capítulo.

**Documentos citados** (son del equipo y no se suben a Git; están en `docs/privado/`):

- **PP:** *Problema Prototípico e Incidentes Críticos, semestre 2026-2*, Licenciatura en Ciencia de Datos para Negocios,
  Universidad Nacional “Rosario Castellanos”, Dirección de Asuntos Académicos, elaborado el 01-09-2026.
- **Plan SIE:** *Plan general del proyecto. Primer avance. Sistemas de Información Empresarial*, del equipo.
- **Avance 2:** *Cuidado Inteligente MX · Avance 2. Lógica funcional del sistema de información*, del equipo.

## Por qué lo hicimos así

El PP pide que los seis componentes «se alimentan de la misma base de datos y del mismo modelo de negocio» (PP, «Incidente
crítico», p. 6). Por eso Enlaza es **una sola aplicación**: la simulación usa el mismo despachador que la operación; la voz
crea solicitudes y alertas reales; Panorama lee la operación; el negocio usa los datos de uso del sistema (@ref(cap-que-es)).

## Cómo funciona por dentro

### 1. La evidencia integradora: seis entregables

| Componente que pide el PP (p. 2) | En Enlaza | Capítulos |
|---|---|---|
| Visualización: Dashboard de Monitoreo Territorial y Temporal (Shiny/R o Python) | Panorama-AM, tablero en vivo y contingencia (React + ECharts con API en Python) | @ref(cap-panorama), @ref(cap-m-vis) |
| Cómputo Cognitivo: Asistente Cognitivo por Voz y Clasificador de Riesgo (NLP/TensorFlow) | Enlaza Voz (antes ORACLE-Voz): Whisper + reglas + clasificador Keras/TensorFlow + LLM local | @ref(cap-voz), @ref(cap-m-cc) |
| Modelado y Simulación: Simulador de Optimización de Servicios de Cuidado (Agentes/Markov) | SIRAG-D: eventos discretos + agentes con cadena de Markov | @ref(cap-sirag), @ref(cap-m-sim) |
| SIE: Arquitectura del Sistema de Información Institucional (CRM/ERP/Nube) | Operación: TPS/CRM/ERP en una base con seguridad por fila | @ref(cap-operacion), @ref(cap-m-sie) |
| Emprendimiento: Plan de Negocios Viable y Canvas de la Startup | `/negocio`, `assumptions.csv`, Canvas, VPN, TIR, escenarios | @ref(cap-negocio), @ref(cap-m-emp) |
| Práctica Profesional: Diagnóstico de Campo, Protocolo de Ética y Práctica Profesional | Consentimientos, aviso, ARCO, bitácora, LFT; el diagnóstico de campo se hace esta semana (material en `docs/diagnostico/`) | @ref(cap-etica), @ref(cap-m-pp) |

!!! nota "Resuelto con el profesor de Visualización"
    El PP dice «Shiny/R o Python» para el tablero. Enlaza dibuja la interfaz con **React y ECharts**, y **toda la lógica
    analítica está en Python**: la API calcula cada indicador (`backend/app/routers/panorama.py`), la simulación y el modelo de
    negocio son Python, y el cuaderno `business/model.ipynb` usa el mismo módulo. La interfaz solo dibuja lo que Python ya
    calculó. **El profesor confirmó que lo importante es que el tablero se vea bien** (claro, legible y que responda preguntas),
    no la herramienta con que se dibuja.

### 2. Cómo se califica

La Evidencia Integradora vale el {{ doc.peso_total }} de la calificación final de **cada** asignatura: {{ doc.peso_portafolio }}
por el portafolio escrito (documento y repositorio de código) y {{ doc.peso_exposicion }} por la exposición y defensa (PP,
«Criterio de Evaluación y Rúbrica», p. 3).

| Criterio de la rúbrica (PP, p. 4-5) | Peso | Qué pide para «Excelente» | Dónde lo cubre Enlaza |
|---|---|---|---|
| Argumentación científica y fundamentación | {{ doc.rub_argumentacion }} | lógica matemática, estadística y financiera; justificación demográfica e histórica; decisiones basadas en datos | datos calibrados con Censo, ENSANUT y ENASEM (@ref(cap-datos)); IC y pruebas (@ref(cap-sirag)); VPN y TIR (@ref(cap-negocio)) |
| Contenido técnico e integración de las 6 UCA | {{ doc.rub_contenido }} | los seis entregables operan de forma sistémica; el plan de negocios se alimenta de la simulación y del tablero | una sola app; mismo despachador; negocio con datos de uso; riesgos de los otros componentes en el plan (@ref(cap-m-emp)) |
| Originalidad, innovación y enfoques | {{ doc.rub_originalidad }} | {{ doc.ideas_originales }} ideas originales; enfoques humanista, social/ambiental y de emprendimiento | ver «Ideas originales» y «Los tres enfoques», abajo |
| Expresión escrita y presentación | {{ doc.rub_escrita }} | estructura científica, esquemas de calidad, ortografía, **APA 7** | este libro y `docs/`; **pendiente:** revisar que las referencias del portafolio estén en APA 7 |
| Exposición oral, defensa y prototipo | {{ doc.rub_oral }} | demostración en tiempo real, solvencia técnica y ética, respuesta crítica | prototipo en vivo con reloj real y enlace público; guiones de 2 minutos y preguntas de cada capítulo (Parte V) |

### 3. Los tres enfoques (PP, «Planteamiento de la Problemática Integradora», p. 3)

| Enfoque | Lo que pide | En Enlaza |
|---|---|---|
| **Humanista**: dignidad y autonomía | no infantilizar; no invadir la privacidad de más | lenguaje «personas mayores»; modo sencillo; el asistente no diagnostica; minimización de datos |
| **Humanista**: ética de los datos | protección de identidad; prevenir sesgos por nivel cognitivo, edad o condición | consentimiento con asentimiento; seguridad por fila; sesgo de voz declarado y botón «pedir que me llamen» |
| **Social/ambiental**: desgaste familiar | aliviar la carga de quienes cuidan | la familia ve quién llega y cuándo, pide servicios y avisa por voz |
| **Social/ambiental**: justicia socioambiental | cruzar aire con salud para alertas preventivas en zonas vulnerables | contingencia que prioriza a pacientes sensibles en las alcaldías afectadas (@ref(cap-contingencia)) |
| **Emprendimiento**: sostenibilidad y escalabilidad | modelo viable, rentabilidad y retorno social | SaaS por suscripción; escenarios; equilibrio en el mes {{ bm.breakeven_month }} |
| **Emprendimiento**: innovación y financiamiento | plan para inversionistas ángel o capital semilla; *silver economy* | inversión necesaria {{ bm.investment }}; pitch en @ref(cap-m-emp) |

### 4. Ideas originales (el nivel «Excelente» pide {{ doc.ideas_originales }})

1. **La simulación usa el mismo código de asignación que la operación**: sus conclusiones valen para el sistema real.
2. **Un hallazgo de la simulación cambió el producto**: el límite de tiempo solo para lo urgente y la reserva del candidato.
3. **Dos niveles de aviso de emergencia** (rojo por regla, ámbar por clasificador con revisión humana), decididos con la matriz de
   errores del holdout.
4. **El consentimiento también limita las decisiones automáticas**: sin permiso de datos de salud, el despachador y la contingencia
   no los usan.
5. **La Ley Federal del Trabajo dentro del despachador** (descanso, jornada, relevos), con el costo de cumplirla medido en
   simulación.
6. **Ningún número sin fuente**: cada cifra de la app y de este libro sale de un archivo o dice «supuesto».
7. **«Datos insuficientes (N visitas)»** en lugar de un porcentaje engañoso, que responde al «espejismo del promedio» del PP.
8. **Evaluación de voz a ciegas** con regla de adopción escrita **antes** de ver los resultados.

### 5. El incidente crítico general y la respuesta de Enlaza

El PP (p. 6) plantea una contingencia extraordinaria por PM2.5 y ozono en la CDMX, con bloqueos viales y un pico de
{{ doc.pico_crisis }} en crisis respiratorias, que expone una falla en cada componente:

| Falla que describe el PP (p. 6) | Qué hace Enlaza | Qué no resuelve |
|---|---|---|
| Panorama-AM diluye en un promedio la crisis de un clúster de Iztapalapa | la contingencia se ve **por estación** y por alcaldía con su nivel; el tablero muestra cada visita; «datos insuficientes» en vez de un promedio engañoso | la coropleta de Panorama sí es por alcaldía (promedio); no hay vista por colonia |
| SIRAG-D manda por rutas históricas cortas ahora saturadas | el despachador elige por **tiempo de viaje con el tráfico de la hora**; el escenario de bloqueo suma tráfico y minutos; la contingencia propone **recalcular rutas** | tráfico por hora promedio, no en vivo; línea recta × factor, no rutas reales |
| La arquitectura CRM/ERP fragmentada retrasa la reasignación | una sola base: una alerta, un «fuera de servicio» o una contingencia **redespachan solos** | no hay integración con sistemas externos de una institución real |
| ORACLE-Voz pierde precisión con hablantes con contacto lingüístico indígena | el sesgo se **declara**; botón «No hablo español / Pedir que me llamen»; dos niveles con revisión humana; WER por grupo preparado | **no se midió** con voces reales de esos grupos (pendiente) |
| Presión para omitir el consentimiento de pacientes con demencia | el consentimiento se exige **en la API**: sin él no hay visita, voz ni datos de salud; se registra el asentimiento | el flujo institucional cuando la persona no asiente lo define la institución |
| El plan de negocios promete escalamiento nacional | el escenario recomendado limita la participación por entidad y crece por regiones; el VPN base negativo se dice | sin validación con inversionistas reales |

### 6. Los dilemas (PP, «Dilemas que plantea», p. 8) y la postura del equipo

| Dilema | Postura de Enlaza (para defender) |
|---|---|
| ¿Suspender, lanzar con advertencias o rediseñar? | Para la voz: **no desplegar** fuera de la CDMX sin medir el error por grupo lingüístico; mientras, advertencia explícita y alternativa humana (pedir que llamen). |
| ¿Qué principios de narrativa de datos son innegociables? | Innegociable: no esconder lo localizado ni mostrar porcentajes con pocos datos, y nada solo con color. Negociable: la simplicidad visual. |
| ¿Ceder a despachadores humanos o recalibrar con variables no validadas? | Ni una cosa ni la otra: la asignación automática usa reglas **validadas en simulación**; lo delicado lo aprueba una persona y la contingencia **propone**, no impone. |
| ¿Cómo integrar áreas sin comprometer seguridad ni autonomía? | Una base con roles y seguridad por fila: cada área ve lo suyo y la bitácora registra quién accede. |
| ¿Ceder ante la presión para omitir el consentimiento? | No. El sistema no lo permite técnicamente (bloqueo en la API) y queda registrado. |
| ¿Sostener la promesa de escalamiento nacional? | No. Escenario recomendado regional y con tope de participación, presentado con sus riesgos: supone plan Gobierno y fundadores al {{ neg.founder_salary_year1_recommended }} % el año 1; sin ambos, VPN {{ bm.rec_wo_both }}. |
| ¿Quién es responsable de un daño por interacción entre sistemas? | Trazabilidad: cada decisión automática o humana queda en la bitácora con su origen (`auto`, `coordinator`, `timeout`). |

## Dónde está en el código

Cada fila de las tablas anteriores apunta a su capítulo, y ahí está el código. Los documentos del curso están en
`docs/privado/`, que Git ignora.

## Números clave

{{ tabla doc.peso_total doc.peso_portafolio doc.peso_exposicion doc.rub_argumentacion doc.rub_contenido doc.rub_originalidad doc.rub_escrita doc.rub_oral doc.pico_crisis }}

## Limitaciones honestas

- El **diagnóstico de campo** (Práctica Profesional) se hace esta semana; la guía, el consentimiento verbal y la plantilla
  están en `docs/diagnostico/` y los hallazgos van en @ref(cap-m-pp).
- Falta la **evaluación de voz con hablantes reales**. Las referencias en **APA 7** están en el anexo de fuentes.
- El **respaldo** de la base es manual (`scripts/backup_db.sh`), no automático (@ref(cap-m-sie)).
- El tablero no es Shiny: la lógica está en Python y la interfaz solo dibuja. Resuelto con el profesor: lo importante es que el
  tablero se vea bien.

## Preguntas que te pueden hacer

!!! pregunta "¿Cómo se integran las seis materias?"
    En una sola aplicación y una sola base de datos. La simulación importa el despachador de la operación; la voz crea
    solicitudes y alertas en el tablero; Panorama lee la operación; el negocio cuenta servicios coordinados y horas ahorradas
    del sistema; la ética está en la API (consentimientos) y en la bitácora.

!!! pregunta "¿Qué pasa en Enlaza con el incidente crítico?"
    La contingencia se detecta sola por estación, se proponen ajustes por institución (prioridad a pacientes sensibles,
    oxigenoterapia, rutas, avisos) y coordinación los aprueba. El despachador ya elige por tráfico de la hora y el escenario
    con bloqueo suma tiempo. Lo mostramos en vivo con el panel de demostración.

!!! pregunta "¿Cuáles son sus ideas originales?"
    La simulación con el mismo código que la operación, el hallazgo de simulación que cambió el producto, los dos niveles de
    aviso de voz, el consentimiento aplicado a decisiones automáticas, la ley laboral dentro del despachador y «datos
    insuficientes» contra el espejismo del promedio.
