# Guion del coloquio con capturas · Enlaza · cuidado coordinado

<!-- FUENTE del guion de la versión SIN demostración en vivo. NO editar guion_coloquio_capturas.md: se genera desde aquí
     con scripts/build_presentacion_capturas.sh (render_guion_capturas.py).
     {{ clave }} = número de docs/biblia/out/numeros.json; nada se escribe a mano. Una clave desconocida detiene el build.
     Cada sección «{#dN}» da las notas del orador de la diapositiva N. «Dura» se suma sola: el total debe quedar entre
     9:30 y 10:00, y cada diapositiva no puede pedir más de 2.6 palabras por segundo. El cronómetro acumulado se calcula. -->

**Formato:** 10 minutos de exposición y 5 de preguntas del sínodo. **Presentación:** `docs/presentacion/enlaza_coloquio_capturas.pptx`
(y `.pdf`). Esta versión **no tiene demostración en vivo**: capturas reales de la app cuentan los mismos cuatro pasos.

**Cómo leerlo:** cada diapositiva dice quién habla, cuánto dura, el cronómetro acumulado al terminarla y qué se dice. Lo que va
entre paréntesis es una acción, no se dice: «(Señala la llamada 2.)» quiere decir señalar en la pantalla el círculo con el 2.
Las cuatro personas defienden todo el proyecto; el reparto es solo para la exposición.

Las frases son **sugeridas**: dichas con sus palabras suenan mejor que memorizadas. Lo que sí hay que respetar son los tiempos.

## Reparto del tiempo

{{ reparto }}

## Minuto a minuto

### Diapositiva 1 · Portada {#d1}

**Habla:** Persona 1 · **Dura:** 0:15 · **Se ve:** portada con el QR.

**Qué se dice:**

- Buenos días. Somos el equipo de Enlaza, cuidado coordinado.
- En diez minutos les mostramos el problema, cómo funciona la aplicación y por qué es un negocio viable.

### Diapositiva 2 · El problema {#d2}

**Habla:** Persona 1 · **Dura:** 0:30 · **Se ve:** tres cifras grandes y su fuente.

**Qué se dice:**

- En la Ciudad de México viven {{ seed.pop60_cdmx }} personas de 60 años o más; en todo el país, {{ ctx.mexico_60mas_2024 }}.
- Y {{ cal.ref_multimorbidity }} vive con dos o más enfermedades crónicas.
- Quienes las cuidan coordinan con llamadas, WhatsApp y hojas de cálculo: lo urgente compite con lo rutinario.

### Diapositiva 3 · La solución {#d3}

**Habla:** Persona 1 · **Dura:** 0:25 · **Se ve:** la frase y los seis módulos con su materia.

**Qué se dice:**

- Enlaza es una plataforma web por suscripción: asigna sola cada visita, deja lo delicado a una persona y avisa a tiempo de una emergencia.
- Cada módulo responde a una de las seis materias, pero es una sola aplicación.

### Diapositiva 4 · Cómo funciona por dentro {#d4}

**Habla:** Persona 1 · **Dura:** 0:35 · **Se ve:** dos carriles (visitas y voz) y la base de datos abajo.

**Qué se dice:**

- (Señala el carril «Visitas».) Llega una solicitud y el despachador elige a quien tiene la habilidad, está en turno y llega antes.
- Lo delicado lo aprueba una persona.
- (Señala el carril «Voz».) Una nota pasa primero por reglas de emergencia y después por un clasificador; al final, un resumen para la médica.
- (Señala la base de datos.) Y todo vive en una sola base, donde cada institución ve solo lo suyo.

### Diapositiva 5 · Paso 1 · La familia pide para hoy {#d5}

**Habla:** Persona 2 · **Dura:** 0:30 · **Se ve:** el formulario de la familia y su respuesta, en celular.

**Qué se dice:**

- Ahora, la aplicación en cuatro pasos, con capturas reales. Paso uno: una familia, desde su celular.
- (Señala las llamadas 1 y 2.) Pide una visita de enfermería para hoy, en un par de horas.
- (Señala la llamada 4.) Al instante dice «Asignada». (Señala la llamada 5.) Y quién va.

### Diapositiva 6 · Paso 1 · Se asigna sola {#d6}

**Habla:** Persona 2 · **Dura:** 0:35 · **Se ve:** el tablero de coordinación y el celular del personal.

**Qué se dice:**

- (Señala la fila de Víctor Chávez por su nombre: puede haber otras marcadas «Nueva» por el plan de cuidado.) En el tablero de coordinación aparece sola, marcada «Nueva».
- (Señala la llamada 2.) Nadie la tocó: es prioridad media y el despachador eligió por habilidad, turno, descanso y tráfico.
- (Señala la llamada 3.) Y el personal la ve en su celular y marca «Llegué» al llegar.

### Diapositiva 7 · Paso 2 · Lo urgente lo decide una persona {#d7}

**Habla:** Persona 2 · **Dura:** 0:35 · **Se ve:** la solicitud urgente en Aprobaciones.

**Qué se dice:**

- Paso dos: una solicitud urgente. (Señala la llamada 1.) Prioridad alta, con visita en menos de {{ cfg.urgent_within }}.
- (Señala la llamada 2.) Enlaza propone a quien llega antes, (señala la llamada 3) muestra alternativas con su tiempo de viaje,
- (señala la llamada 4) y decide coordinación.

### Diapositiva 8 · Paso 2 · Aprobada, en vivo {#d8}

**Habla:** Persona 2 · **Dura:** 0:25 · **Se ve:** el tablero con la urgente ya asignada y la regla de lo urgente.

**Qué se dice:**

- (Señala la fila de Joaquín Guerrero por su nombre: puede haber otras marcadas «Nueva» por el plan de cuidado.) Aprobada, y el tablero cambió en vivo, (señala la llamada 2) con quien propuso Enlaza.
- (Señala el recuadro de la derecha.) Si coordinación no responde en {{ cfg.auto_apply_after }}, se aplica con aviso, solo para lo urgente. Eso salió de la simulación.

### Diapositiva 9 · Paso 3 · Contingencia en el oriente {#d9}

**Habla:** Persona 3 · **Dura:** 0:45 · **Se ve:** el mapa de estaciones, la propuesta para la institución y los botones de aprobación.

**Qué se dice:**

- Paso tres: mala calidad del aire en el oriente. (Señala la llamada 1.) Enlaza la detectó sola, por estación, no promediada.
- (Señala la llamada 2.) Propone subir la prioridad de quienes tienen enfermedad del pulmón o del corazón, avisar a sus familias y, si tienen oxigenoterapia en las próximas horas, adelantarla.
- (Señala la llamada 3.) La oxigenoterapia solo se adelanta si hay una visita próxima, como esta de hoy; si no la hay, Enlaza no inventa cambios.
- (Señala la llamada 4.) Nada cambia sin aprobación.

### Diapositiva 10 · Paso 4 · Una nota de emergencia {#d10}

**Habla:** Persona 4 · **Dura:** 0:35 · **Se ve:** la nota escrita y la pantalla roja, en celular.

**Qué se dice:**

- Paso cuatro: la voz. (Señala la llamada 1.) La familia escribe, como en un mensaje: «Mi mamá no puede respirar y tiene los labios morados».
- (Señala la llamada 3.) Pantalla roja: «Llama al 911 ahora». Sale antes que el modelo de lenguaje, porque la activó una regla.
- (Señala la llamada 4.) Y coordinación ya está avisada.

### Diapositiva 11 · Paso 4 · Lo que recibe la médica {#d11}

**Habla:** Persona 4 · **Dura:** 0:30 · **Se ve:** el reporte de voz de la médica.

**Qué se dice:**

- (Señala las llamadas 1 y 2.) La médica recibe la transcripción y la regla que se activó.
- (Señala la llamada 3.) Un modelo de lenguaje local resume lo que se dijo, (señala la llamada 4) y lo dice claro: no es un diagnóstico.

### Diapositiva 12 · SIE {#d12}

**Habla:** Persona 2 · **Dura:** 0:25 · **Se ve:** la alerta de jornada y las asignaciones del historial.

**Qué se dice:**

- SIE: operación, personal y agenda en un solo lugar. En el historial, {{ seed.assign_auto }} asignadas solas y {{ seed.assign_coordinator }} aprobadas por coordinación.
- (Señala las llamadas 1 y 2.) Los turnos nocturnos que exceden la ley se marcan; no se corrigen, lo decide la institución.
- Su límite: un ERP acotado y sin prueba real.

### Diapositiva 13 · Modelado y Simulación {#d13}

**Habla:** Persona 3 · **Dura:** 0:50 · **Se ve:** la gráfica de SIRAG-D, recortada, y las cifras a la derecha.

**Qué se dice:**

- SIRAG-D simula semanas completas con el mismo código de asignación: {{ sim.runs_main }} corridas, {{ cfg.replications }} réplicas por combinación.
- (Señala las llamadas 2 y 1.) Priorizar por riesgo baja la espera de lo urgente de {{ sim.normal.human_dispatcher.high_wait_p90_min }} a {{ sim.normal.risk_priority.high_wait_p90_min }} minutos, con {{ test.normal.high_wait_p90_min.risk_priority.p }}.
- (Señala el recuadro de abajo a la derecha.) Y cuando aprobar tarda {{ sens.approval_delay.5-15.label }}, el límite y la reserva la dejan en {{ sens.approval_delay.5-15.vela_timeout.high_wait_p90_min }}; sin ellos, {{ sens.approval_delay.5-15.risk_plus_live_traffic.high_wait_p90_min }}.
- La simulación nos dijo cómo asignar. Su límite: datos sintéticos.

### Diapositiva 14 · Visualización {#d14}

**Habla:** Persona 3 · **Dura:** 0:30 · **Se ve:** el Panorama-AM de Dirección.

**Qué se dice:**

- Panorama-AM es lo que ve Dirección. (Señala la llamada 1.) Contadores en vivo; (señala la llamada 2) la puntualidad antes y con Enlaza;
- (señala la llamada 3) y si faltan datos, lo dice en lugar de inventar una tendencia.
- Su límite: la línea base es sintética.

### Diapositiva 15 · Cómputo Cognitivo {#d15}

**Habla:** Persona 4 · **Dura:** 0:35 · **Se ve:** la pantalla roja y el aviso ámbar, lado a lado, y los números del holdout.

**Qué se dice:**

- (Señala la llamada 1.) Si se activa una regla, pantalla roja. (Señala la llamada 2.) Si solo sospecha el clasificador, aviso ámbar y coordinación llama.
- A ciegas, con {{ voz.holdout.n }} frases, detectó {{ voz.holdout.sens }} de las emergencias, con {{ voz.holdout.fa100 }} falsas alarmas por cada 100 notas.
- Su límite: frases sintéticas; faltan hablantes reales.

### Diapositiva 16 · Emprendimiento {#d16}

**Habla:** Persona 4 · **Dura:** 0:45 · **Se ve:** los tres escenarios de /negocio y las cifras del recomendado.

**Qué se dice:**

- Vendemos una suscripción mensual por institución. (Señala la llamada 2.) El plan base tiene un VPN negativo, y lo decimos.
- (Señala la llamada 1.) El recomendado pide {{ bm.sc.recommended.investment }}: VPN al {{ bm.rate_25 }} de {{ bm.sc.recommended.npv25 }} y TIR de {{ bm.sc.recommended.tir }}.
- (Señala el recuadro de abajo.) Con una condición: supone el plan Gobierno y fundadores al {{ neg.founder_salary_year1_recommended }} % el primer año; sin ambos, el VPN sería {{ bm.rec_wo_both }}.

### Diapositiva 17 · Práctica Profesional {#d17}

**Habla:** Persona 1 · **Dura:** 0:30 · **Se ve:** la bitácora con el intento bloqueado y el {{ db.rls_patients_none }} / {{ db.rls_patients_insa }} / {{ db.rls_patients_all }}.

**Qué se dice:**

- (Señala la llamada 1.) Otra institución intentó ver un paciente de la Clínica Oriente: (señala la llamada 2) bloqueado y registrado.
- (Señala las cifras.) La API ve {{ db.rls_patients_none }} pacientes sin institución, {{ db.rls_patients_insa }} con una clínica y {{ db.rls_patients_all }} como Dirección.
- Sin consentimiento, la API bloquea, y el despachador respeta descanso y jornada.

### Diapositiva 18 · Cierre {#d18}

**Habla:** Persona 3 · **Dura:** 0:20 · **Se ve:** logros, límites honestos y siguientes pasos.

**Qué se dice:**

- Una sola aplicación que integra las seis materias y que la simulación ayudó a diseñar.
- Sus límites: datos sintéticos, falsas alarmas de voz y falta probarla con una institución real.

### Diapositiva 19 · Gracias {#d19}

**Habla:** Persona 1 · **Dura:** 0:05 · **Se ve:** «Gracias», «¿Preguntas?», el QR y los nombres. **Se queda en pantalla durante los 5 minutos de preguntas.**

**Qué se dice:**

- Gracias. Con gusto respondemos sus preguntas.

### Diapositiva 20 · Respaldo: el mercado (no se presenta) {#d20}

**Habla:** quien responda · **Dura:** 0:00 · **Se ve:** establecimientos privados por entidad (DENUE).

**Qué se dice:**

- Solo si preguntan por el mercado: {{ neg.denue_residences_private_cdmx }} residencias privadas en la CDMX, contadas en el DENUE.

### Diapositiva 21 · Respaldo: los tres escenarios (no se presenta) {#d21}

**Habla:** quien responda · **Dura:** 0:00 · **Se ve:** base, conservador y recomendado, lado a lado (captura de /negocio).

**Qué se dice:**

- Solo si preguntan por la viabilidad: el base pierde valor al {{ bm.rate_25 }} ({{ bm.sc.base.npv25 }}); el recomendado, {{ bm.sc.recommended.npv25 }}, con su condición.

### Diapositiva 22 · Respaldo: las cinco políticas (no se presenta) {#d22}

**Habla:** quien responda · **Dura:** 0:00 · **Se ve:** las cinco políticas con su intervalo de confianza y por qué la app dice otra cifra.

**Qué se dice:**

- {{ sim.normal.risk_priority.high_wait_p90_min }} es priorizar por riesgo; {{ sim.normal.vela_timeout.high_wait_p90_min }} es Enlaza con el límite de tiempo. Las dos se comparan contra los {{ sim.normal.human_dispatcher.high_wait_p90_min }} de la asignación humana.

## Preguntas probables del sínodo (5 minutos)

Mientras tanto se queda en pantalla la diapositiva 19 (Gracias). Responde primero quien aparece; los demás completan solo si hace
falta. Respuestas cortas: 20 a 30 s. Para mostrar una diapositiva de respaldo, en el modo presentador se escribe su número y Enter.

| # | Pregunta | Responde | Respuesta corta | Diapositiva |
|---|---|---|---|---|
| 1 | ¿Es viable el negocio? | Persona 4 | El plan base tiene VPN al {{ bm.rate_25 }} de {{ bm.sc.base.npv25 }}; lo decimos. El recomendado limita la participación y crece por regiones: VPN {{ bm.sc.recommended.npv25 }}, TIR {{ bm.sc.recommended.tir }}, si se cumplen el plan Gobierno y el sueldo de fundadores al {{ neg.founder_salary_year1_recommended }} %; sin ambos, {{ bm.rec_wo_both }}. | 21 |
| 2 | ¿Qué tan grande es el mercado? | Persona 4 | Contado en el DENUE: {{ neg.denue_residences_private_cdmx }} residencias privadas en la CDMX, más Estado de México, Jalisco y Nuevo León. Los públicos compran por licitación: van aparte. | 20 |
| 3 | ¿Por qué la app dice {{ sim.normal.vela_timeout.high_wait_p90_min }}? | Persona 3 | {{ sim.normal.risk_priority.high_wait_p90_min }} es priorizar por riesgo; {{ sim.normal.vela_timeout.high_wait_p90_min }} es Enlaza con el límite de tiempo. Las dos se comparan contra los {{ sim.normal.human_dispatcher.high_wait_p90_min }} de la asignación humana. | 22 |
| 4 | ¿La máquina decide todo? | Persona 2 | No. Lo rutinario se asigna solo; lo de prioridad alta lo aprueba una persona. Solo lo urgente sin respuesta en {{ cfg.auto_apply_after }} se aplica con aviso, y coordinación lo puede cambiar. | 8 |
| 5 | ¿Cómo evitan que una institución vea los datos de otra? | Persona 1 | Seguridad por fila en PostgreSQL: la API fija la institución en cada petición; sin institución ve {{ db.rls_patients_none }} pacientes. Un intento ajeno responde 403 y queda en la bitácora. | 17 |
| 6 | ¿Qué pasa con una falsa alarma de voz? | Persona 4 | Si solo sospecha el clasificador, sale el aviso ámbar y coordinación llama a la familia; si no contesta en {{ cfg.escalate_after }}, pasa a Dirección. Preferimos una falsa alarma revisada a una emergencia perdida. | 15 |
| 7 | ¿El modelo de lenguaje diagnostica? | Persona 4 | No. Resume lo dicho en un formato fijo; el nivel lo ponen las reglas y el clasificador, y nunca le dice a nadie que algo no es una emergencia. | 11 |
| 8 | ¿Por qué no corrigen los turnos nocturnos largos? | Persona 2 | Porque la plantilla la decide la institución: Enlaza marca el turno que excede la jornada legal (art. 61) y avisa, pero no cambia contratos por su cuenta. | 12 |
| 9 | ¿Ustedes programaron esto? | Persona 1 | El problema, el diseño, las reglas y las decisiones son del equipo; la mayor parte del código la escribió un asistente de programación con IA (Claude Code) bajo esas reglas, con un pull request por cambio y {{ repo.tests_summary }}. Podemos defender cada parte. | 4 |
| 10 | ¿Qué no funciona o qué falta? | Persona 3 | Las falsas alarmas de voz, la evaluación con hablantes reales, el diagnóstico de campo y la prueba con una institución real. | 18 |

## Antes de presentar

- [ ] Las cuatro fuentes de `docs/presentacion/fuentes/` instaladas en la computadora que proyecta (o abrir el PDF).
- [ ] La presentación en modo presentador, con las notas visibles para quien habla; el PDF en el escritorio por si falla PowerPoint.
- [ ] Un cronómetro a la vista: al terminar la diapositiva 8 deben ir unos {{ crono_d8 }}.
- [ ] Cada quien sabe su primera frase y a quién le pasa la palabra.
