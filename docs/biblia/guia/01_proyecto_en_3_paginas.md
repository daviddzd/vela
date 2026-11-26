# El proyecto en tres páginas {#guia-tres-paginas}

## El problema

En la Ciudad de México viven {{ seed.pop60_cdmx }} personas de 60 años o más. Las instituciones que las cuidan (residencias,
centros de día, redes de cuidado a domicilio) coordinan las visitas con llamadas, WhatsApp y hojas de cálculo: se pierden
solicitudes, no se sabe quién está libre ni cuánto tarda en llegar con el tráfico, lo urgente compite con lo rutinario y no queda
registro. Y en una contingencia ambiental, las personas con enfermedades del pulmón o del corazón son las más afectadas.

## La solución: Enlaza · cuidado coordinado

Una plataforma web por suscripción ([[SaaS]]) para esas instituciones (@ref(cap-que-es)):

- **Operación** (SIE): la familia, la coordinación, el plan de cuidado o una nota de voz crean una solicitud; el **despachador**
  elige solo a quien tiene la habilidad, está en turno, no es su día de descanso y llega antes con el tráfico de la hora. Lo
  rutinario se asigna solo; lo de prioridad alta lo **aprueba una persona**; lo urgente sin respuesta en {{ cfg.auto_apply_after }} se
  aplica con aviso (@ref(cap-operacion)).
- **Tiempo real**: el tablero de coordinación se actualiza solo, a la hora real de la CDMX (@ref(cap-tiempo-real)).
- **Panorama-AM** (Visualización): tableros que responden preguntas, comparan contra una referencia y no esconden lo localizado
  (@ref(cap-panorama)).
- **SIRAG-D** (Modelado y Simulación): simula semanas completas con el **mismo código** de asignación y **nos dijo cómo
  asignar**: priorizar por riesgo, y un límite de tiempo para cuando coordinación tarda en aprobar (@ref(cap-sirag)).
- **Contingencia**: detecta sola el aire contaminado, propone ajustes por institución y **nada cambia sin aprobación**
  (@ref(cap-contingencia)).
- **Enlaza Voz** (antes ORACLE-Voz; Cómputo Cognitivo): voz → texto → reglas → clasificador → pantalla 911 (roja si fue una regla,
  ámbar si fue solo el clasificador) → reporte para el médico que **no diagnostica** (@ref(cap-voz)).
- **Negocio** (Emprendimiento): suscripción por tamaño, equilibrio en el mes {{ bm.breakeven_month }}, LTV/CAC {{ bm.ltv_cac }}, mercado
  real del DENUE y un escenario recomendado con VPN {{ bm.sc.recommended.npv25 }}, que supone plan Gobierno y fundadores al {{ neg.founder_salary_year1_recommended }} % el año 1; sin ambos, VPN {{ bm.rec_wo_both }} (@ref(cap-negocio)).
- **Ética** (Práctica Profesional): tres consentimientos (y el asentimiento), ARCO, bitácora, Ley Federal del Trabajo e IA
  supervisada (@ref(cap-etica)).

## Cómo está hecho

Una sola aplicación en una laptop: PostgreSQL con **seguridad por fila** (una institución nunca ve a otra), FastAPI (Python),
React, un worker que da una vuelta por minuto, WebSocket, Caddy en un solo puerto, Whisper y el modelo de lenguaje
**{{ mod.llm_nombre }}** (Ollama) **locales**, y un túnel de Cloudflare que publica la laptop en **{{ ops.public_url }}**: una
dirección fija, no un hosting; si la laptop se apaga, se apaga Enlaza (@ref(cap-arquitectura)). Todos los datos son **sintéticos**: {{ seed.persons }} personas
calibradas con el Censo, la ENSANUT y la ENASEM (@ref(cap-datos)).

## Lo que mejor demuestra Enlaza

1. **La simulación nos dijo cómo asignar**: priorizar por riesgo baja la espera p90 de lo urgente de
   {{ sim.normal.human_dispatcher.high_wait_p90_min }} a {{ sim.normal.risk_priority.high_wait_p90_min }} min
   ({{ test.normal.high_wait_p90_min.risk_priority.p }}); cuando coordinación tarda {{ sens.approval_delay.5-15.label }} en aprobar,
   el límite de {{ cfg.auto_apply_after }} y la reserva la dejan en {{ sens.approval_delay.5-15.vela_timeout.high_wait_p90_min }} contra
   {{ sens.approval_delay.5-15.risk_plus_live_traffic.high_wait_p90_min }} sin el límite.
2. **La seguridad está en la base de datos**: sin institución, la API ve {{ db.rls_patients_none }} pacientes; con la Clínica Oriente,
   {{ db.rls_patients_insa }}; Dirección, {{ db.rls_patients_all }}.
3. **La evaluación de voz es honesta**: holdout a ciegas con {{ voz.holdout.sens }} de emergencias detectadas y
   {{ voz.holdout.fa100 }} falsas alarmas por 100 notas; por eso existen los dos niveles de aviso.

## Lo que hay que decir con honestidad

- El «sin atender» ({{ sim.normal.vela_timeout.unattended_pct }} en la simulación) **no** lo mejora ninguna forma de asignar: depende del
  personal disponible.
- La mayor parte de la mejora viene de **priorizar por riesgo**, no del tráfico.
- El asistente de voz tiene **muchas falsas alarmas** y no se ha probado con hablantes de lenguas originarias.
- El **VPN del plan base es negativo** ({{ bm.npv_25 }}); el escenario recomendado supone plan Gobierno y fundadores al {{ neg.founder_salary_year1_recommended }} % el año 1; sin ambos, VPN {{ bm.rec_wo_both }}.
- Gran parte del código lo escribió un asistente de programación con IA, con las reglas y la revisión del equipo
  (@ref(cap-construccion)).
