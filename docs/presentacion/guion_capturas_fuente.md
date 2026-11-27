# Guion del coloquio con capturas · Enlaza · cuidado coordinado

<!-- FUENTE del guion de la versión SIN demostración en vivo. NO editar guion_coloquio_capturas.md: se genera desde aquí
     con scripts/build_presentacion_capturas.sh (render_guion_capturas.py).
     {{ clave }} = número de docs/biblia/out/numeros.json; nada se escribe a mano. Una clave desconocida detiene el build.
     Cada sección «{#dN}» da las notas del orador de la diapositiva N. «Dura» se suma sola: el total debe quedar entre
     9:30 y 9:45, y cada diapositiva no puede pedir más de 2.6 palabras por segundo. El cronómetro acumulado se calcula. -->

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
- En diez minutos les mostramos el problema, cómo funciona la aplicación y en qué condiciones es un negocio viable.

### Diapositiva 2 · El problema {#d2}

**Habla:** Persona 1 · **Dura:** 0:35 · **Se ve:** tres cifras grandes y su fuente.

**Qué se dice:**

- En la Ciudad de México viven {{ seed.pop60_cdmx }} personas de 60 años o más; en todo el país, {{ ctx.mexico_60mas_2024 }}.
- Y {{ cal.ref_multimorbidity }} vive con dos o más enfermedades crónicas.
- Quienes las cuidan coordinan con llamadas, WhatsApp y hojas de cálculo: lo urgente compite con lo rutinario.

### Diapositiva 3 · La solución y cómo funciona {#d3}

**Habla:** Persona 1 · **Dura:** 0:55 · **Se ve:** los seis módulos en una fila, los dos carriles (visitas y voz) y la base de datos.

**Qué se dice:**

- Enlaza es una plataforma web por suscripción: asigna sola cada visita, deja lo delicado a una persona y avisa a tiempo de una emergencia.
- (Señala la fila de arriba.) Seis módulos, uno por materia: SIE, Modelado y Simulación, Cómputo Cognitivo, Visualización, Emprendimiento y Práctica Profesional. Una sola aplicación.
- (Señala el carril «Visitas».) Llega una solicitud y el despachador elige a quien tiene la habilidad, está en turno y llega antes; lo delicado lo aprueba una persona.
- (Señala el carril «Voz».) Una nota pasa primero por reglas de emergencia y después por un clasificador; al final, un resumen para la médica.
- (Señala la base de datos.) Todo vive en una sola base, donde cada institución ve solo lo suyo, la API pide el consentimiento y la bitácora registra todo.

### Diapositiva 4 · Paso 1 · La familia pide y se asigna sola {#d4}

**Habla:** Persona 2 · **Dura:** 0:50 · **Se ve:** el celular de la familia con «Asignada» y, abajo, el tablero de coordinación.

**Qué se dice:**

- Ahora, la aplicación en cuatro pasos, con capturas reales. Paso uno: una familia pide desde su celular una visita de enfermería para hoy, en un par de horas.
- (Señala la llamada 1.) Al instante dice «Asignada», (señala la llamada 2) y quién va.
- (Señala la fila de Víctor Chávez por su nombre: puede haber otras marcadas «Nueva» por el plan de cuidado.) En el tablero de coordinación aparece sola, marcada «Nueva».
- Nadie la tocó: es prioridad media, y el despachador eligió por habilidad, turno, descanso y tráfico.

### Diapositiva 5 · Paso 2 · Lo urgente lo decide una persona {#d5}

**Habla:** Persona 2 · **Dura:** 0:50 · **Se ve:** la solicitud urgente en Aprobaciones y el recuadro «Solo para lo urgente».

**Qué se dice:**

- Paso dos: una solicitud urgente. (Señala la llamada 1.) Prioridad alta, con visita en menos de {{ cfg.urgent_within }}.
- (Señala la llamada 2.) Enlaza propone a quien llega antes, (señala la llamada 3) muestra alternativas con su tiempo de viaje, y decide coordinación.
- (Señala el recuadro.) Solo para lo urgente: si coordinación no responde en {{ cfg.auto_apply_after }}, se aplica con aviso y queda en la bitácora. Eso salió de la simulación.
- Lo de prioridad alta que no es urgente siempre espera a una persona.

### Diapositiva 6 · Paso 3 · Contingencia en el oriente {#d6}

**Habla:** Persona 3 · **Dura:** 0:50 · **Se ve:** el mapa de estaciones y la propuesta para la institución.

**Qué se dice:**

- Paso tres: mala calidad del aire en el oriente. (Señala la llamada 1.) Enlaza la detectó sola, por estación, no promediada.
- (Señala la llamada 2.) Propone subir la prioridad de quienes tienen enfermedad del pulmón o del corazón, avisar a sus familias y, si tienen oxigenoterapia en las próximas horas, adelantarla.
- (Señala la llamada 3.) La oxigenoterapia solo se adelanta si hay una visita próxima, como esta de hoy; si no la hay, Enlaza no inventa cambios.
- (Señala la frase bajo el mapa.) Nada cambia sin aprobación.

### Diapositiva 7 · Paso 4 · Nota de emergencia y lo que recibe la médica {#d7}

**Habla:** Persona 4 · **Dura:** 0:50 · **Se ve:** la pantalla roja en el celular y el reporte de la médica.

**Qué se dice:**

- Paso cuatro: la voz. La familia escribe, como en un mensaje: «Mi mamá no puede respirar y tiene los labios morados».
- (Señala la llamada 1.) Pantalla roja: «Llama al 911 ahora». Sale antes que el modelo de lenguaje, porque la activó una regla, y coordinación ya está avisada.
- (Señala la llamada 2.) La médica recibe la transcripción, la regla que se activó y un resumen del modelo de lenguaje local,
- (señala la llamada 3) que lo dice claro: no es un diagnóstico.

### Diapositiva 8 · SIE {#d8}

**Habla:** Persona 2 · **Dura:** 0:45 · **Se ve:** la alerta de jornada y las asignaciones del historial.

**Qué se dice:**

- SIE: operación, personal y agenda en un solo lugar. En el historial, {{ seed.assign_auto }} asignadas solas y {{ seed.assign_coordinator }} aprobadas por coordinación, de {{ seed.service_requests }} solicitudes.
- (Señala las llamadas 1 y 2.) Los turnos nocturnos que exceden la ley se marcan; no se corrigen, lo decide la institución.
- Su límite: un ERP acotado y sin prueba con una institución real.

### Diapositiva 9 · Modelado y Simulación {#d9}

**Habla:** Persona 3 · **Dura:** 0:55 · **Se ve:** la gráfica de SIRAG-D, recortada, y las cifras a la derecha.

**Qué se dice:**

- SIRAG-D simula semanas completas con el mismo código de asignación: {{ sim.runs_main }} corridas, {{ cfg.replications }} réplicas por combinación.
- (Señala las llamadas 2 y 1.) Priorizar por riesgo baja la espera de lo urgente de {{ sim.normal.human_dispatcher.high_wait_p90_min }} a {{ sim.normal.risk_priority.high_wait_p90_min }} minutos, con {{ test.normal.high_wait_p90_min.risk_priority.p }}.
- (Señala el recuadro de abajo a la derecha.) Y cuando aprobar tarda {{ sens.approval_delay.5-15.label }}, el límite y la reserva la dejan en {{ sens.approval_delay.5-15.vela_timeout.high_wait_p90_min }}; sin ellos, {{ sens.approval_delay.5-15.risk_plus_live_traffic.high_wait_p90_min }}.
- La simulación nos dijo cómo asignar. Su límite: datos sintéticos.

### Diapositiva 10 · Visualización {#d10}

**Habla:** Persona 3 · **Dura:** 0:40 · **Se ve:** el Panorama-AM de Dirección.

**Qué se dice:**

- Panorama-AM es lo que ve Dirección. (Señala la llamada 1.) Contadores en vivo; (señala la llamada 2) la puntualidad antes y con Enlaza;
- (señala la llamada 3) y si faltan datos, lo dice en lugar de inventar una tendencia.
- Su límite: la línea base es sintética.

### Diapositiva 11 · Cómputo Cognitivo {#d11}

**Habla:** Persona 4 · **Dura:** 0:45 · **Se ve:** la pantalla roja y el aviso ámbar, lado a lado, y los números del holdout.

**Qué se dice:**

- La pantalla roja ya la vieron; lo nuevo es el ámbar. (Señala la llamada 2.) Si solo sospecha el clasificador, aviso ámbar y coordinación llama.
- A ciegas, con {{ voz.holdout.n }} frases, detectó {{ voz.holdout.sens }} de las emergencias, con {{ voz.holdout.fa100 }} falsas alarmas por cada 100 notas.
- Su límite: frases sintéticas; faltan hablantes reales.

### Diapositiva 12 · Emprendimiento {#d12}

**Habla:** Persona 4 · **Dura:** 0:50 · **Se ve:** las cuatro tarjetas grandes y la condición; arriba, la tabla de /negocio como contexto.

**Qué se dice:**

- Vendemos una suscripción mensual por institución. (Señala la llamada 2, la tarjeta roja.) El escenario base tiene un VPN negativo, y lo decimos.
- (Señala la llamada 1.) El recomendado pide {{ bm.sc.recommended.investment }}: VPN al {{ bm.rate_25 }} de {{ bm.sc.recommended.npv25 }} y TIR de {{ bm.sc.recommended.tir }}.
- (Señala la llamada 3.) Con una condición: supone el plan Gobierno y fundadores al {{ neg.founder_salary_year1_recommended }} % el primer año; sin ambos, el VPN sería {{ bm.rec_wo_both }}.

### Diapositiva 13 · Práctica Profesional {#d13}

**Habla:** Persona 1 · **Dura:** 0:30 · **Se ve:** la bitácora con el intento bloqueado y el {{ db.rls_patients_none }} / {{ db.rls_patients_insa }} / {{ db.rls_patients_all }}.

**Qué se dice:**

- (Señala la llamada 1.) Otra institución intentó ver un paciente de la Clínica Oriente: (señala la llamada 2) bloqueado y registrado.
- (Señala las cifras.) La API ve {{ db.rls_patients_none }} pacientes sin institución, {{ db.rls_patients_insa }} con una clínica y {{ db.rls_patients_all }} como Dirección.
- Sin consentimiento, la API bloquea, y el despachador respeta el día de descanso y marca los turnos que exceden la jornada.

### Diapositiva 14 · Gracias {#d14}

**Habla:** Persona 1 · **Dura:** 0:10 · **Se ve:** «Gracias», «¿Preguntas?», el siguiente paso, el QR y los nombres. **Se queda en pantalla durante los 5 minutos de preguntas.**

**Qué se dice:**

- Nuestro siguiente paso: un piloto con una residencia real. Gracias; con gusto respondemos sus preguntas.
- (No se dice; sirve para las preguntas. Logramos: seis materias en una sola app, la simulación cambió el producto, {{ repo.pytest_collected }} pruebas del backend. Límites: datos sintéticos, {{ voz.holdout.fa100 }} falsas alarmas por 100 notas de voz, falta una institución real. Después del piloto: voz con hablantes reales y diagnóstico de campo.)

### Diapositiva 15 · Respaldo: el mercado (no se presenta) {#d15}

**Habla:** quien responda · **Dura:** 0:00 · **Se ve:** establecimientos privados por entidad (DENUE).

**Qué se dice:**

- Solo si preguntan por el mercado: {{ neg.denue_residences_private_cdmx }} residencias privadas en la CDMX, contadas en el DENUE.

### Diapositiva 16 · Respaldo: los tres escenarios (no se presenta) {#d16}

**Habla:** quien responda · **Dura:** 0:00 · **Se ve:** base, conservador y recomendado, lado a lado (captura de /negocio).

**Qué se dice:**

- Solo si preguntan por la viabilidad: el escenario base pierde valor al {{ bm.rate_25 }} ({{ bm.sc.base.npv25 }}); el recomendado, {{ bm.sc.recommended.npv25 }}, con su condición.

### Diapositiva 17 · Respaldo: las cinco políticas (no se presenta) {#d17}

**Habla:** quien responda · **Dura:** 0:00 · **Se ve:** las cinco políticas con su intervalo de confianza y por qué la app dice otra cifra.

**Qué se dice:**

- {{ sim.normal.risk_priority.high_wait_p90_min }} es priorizar por riesgo; {{ sim.normal.vela_timeout.high_wait_p90_min }} es Enlaza con el límite de tiempo. Las dos se comparan contra los {{ sim.normal.human_dispatcher.high_wait_p90_min }} de la asignación humana.

## Preguntas probables del sínodo (5 minutos)

Mientras tanto se queda en pantalla la diapositiva 14 (Gracias). Responde primero quien aparece; los demás completan solo si hace
falta. Respuestas cortas: 20 a 30 s. Para mostrar una diapositiva de respaldo, en el modo presentador se escribe su número y Enter.

| # | Pregunta | Responde | Respuesta corta | Diapositiva |
|---|---|---|---|---|
| 1 | ¿Es viable el negocio? | Persona 4 | El escenario base tiene VPN al {{ bm.rate_25 }} de {{ bm.sc.base.npv25 }}; lo decimos. El recomendado limita la participación y crece por regiones: VPN {{ bm.sc.recommended.npv25 }}, TIR {{ bm.sc.recommended.tir }}, si se cumplen el plan Gobierno y el sueldo de fundadores al {{ neg.founder_salary_year1_recommended }} %; sin ambos, {{ bm.rec_wo_both }}. | 16 |
| 2 | ¿Qué tan grande es el mercado? | Persona 4 | Contado en el DENUE: {{ neg.denue_residences_private_cdmx }} residencias privadas en la CDMX, más Estado de México, Jalisco y Nuevo León. Los públicos compran por licitación: van aparte. | 15 |
| 3 | ¿Por qué la app dice {{ sim.normal.vela_timeout.high_wait_p90_min }}? | Persona 3 | {{ sim.normal.risk_priority.high_wait_p90_min }} es priorizar por riesgo; {{ sim.normal.vela_timeout.high_wait_p90_min }} es Enlaza con el límite de tiempo. Las dos se comparan contra los {{ sim.normal.human_dispatcher.high_wait_p90_min }} de la asignación humana. | 17 |
| 4 | ¿La máquina decide todo? | Persona 2 | No. Lo rutinario se asigna solo; lo de prioridad alta lo aprueba una persona. Solo lo urgente sin respuesta en {{ cfg.auto_apply_after }} se aplica con aviso, y coordinación lo puede cambiar. | 5 |
| 5 | ¿Cómo evitan que una institución vea los datos de otra? | Persona 1 | Seguridad por fila en PostgreSQL: la API fija la institución en cada petición; sin institución ve {{ db.rls_patients_none }} pacientes. Un intento ajeno responde 403 y queda en la bitácora. | 13 |
| 6 | ¿Qué pasa con una falsa alarma de voz? | Persona 4 | Si solo sospecha el clasificador, sale el aviso ámbar y coordinación llama a la familia; si no contesta en {{ cfg.escalate_after }}, pasa a Dirección. Preferimos una falsa alarma revisada a una emergencia perdida. | 11 |
| 7 | ¿El modelo de lenguaje diagnostica? | Persona 4 | No. Resume lo dicho en un formato fijo; el nivel lo ponen las reglas y el clasificador, y nunca le dice a nadie que algo no es una emergencia. | 7 |
| 8 | ¿Por qué no corrigen los turnos nocturnos largos? | Persona 2 | Porque la plantilla la decide la institución: Enlaza marca el turno que excede la jornada legal (art. 61) y avisa, pero no cambia contratos por su cuenta. | 8 |
| 9 | ¿Ustedes programaron esto? | Persona 1 | El problema, el diseño, las reglas y las decisiones son del equipo; la mayor parte del código la escribió un asistente de programación con IA (Claude Code) bajo esas reglas, con un pull request por cambio y {{ repo.tests_summary }}. Podemos defender cada parte. | 3 |
| 10 | ¿Qué no funciona o qué falta? | Persona 3 | Las falsas alarmas de voz, la evaluación con hablantes reales, el diagnóstico de campo y la prueba con una institución real. | 14 |

## Antes de presentar

- [ ] Las cuatro fuentes de `docs/presentacion/fuentes/` instaladas en la computadora que proyecta (o abrir el PDF).
- [ ] La presentación en modo presentador, con las notas visibles para quien habla; el PDF en el escritorio por si falla PowerPoint.
- [ ] Un cronómetro a la vista: al terminar la diapositiva 7 (paso 4) deben ir unos {{ crono_d7 }}.
- [ ] Cada quien sabe su primera frase y a quién le pasa la palabra.
