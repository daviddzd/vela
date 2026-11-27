# Guion del coloquio · Enlaza · cuidado coordinado

<!-- FUENTE del guion. NO editar guion_coloquio.md: se genera desde aquí con scripts/build_presentacion.sh.
     {{ clave }} = número de docs/biblia/out/numeros.json (el mismo script de la biblia); nada se escribe a mano.
     Cada sección «{#dN}» da las notas del orador de la diapositiva N (las viñetas de «Qué se dice»).
     «Dura» se suma solo: el total no puede pasar de 9:40 (10:00 menos 20 s de margen). -->

**Formato:** 10 minutos de exposición y 5 de preguntas del sínodo. **Presentación:** `docs/presentacion/enlaza_coloquio.pptx`
(y `.pdf`). **Dirección pública:** `https://enlaza.zenthinks.com`.

Lo que pide la rúbrica oficial (Problema Prototípico, «Rúbrica Analítica…», p. 5, exposición oral {{ doc.rub_oral }}): recursos
visuales profesionales, **demostración del prototipo en tiempo real**, **defender la viabilidad del plan de negocios** y **no
exceder el tiempo**. Este guion está hecho para eso: la demo ocupa la mitad del tiempo y el negocio cierra la exposición.

Las frases son **sugeridas**: dichas con sus palabras suenan mejor que memorizadas. Lo que sí hay que respetar son los tiempos.

## Reparto del tiempo

{{ reparto }}

## Minuto a minuto

### Diapositiva 1 · Portada {#d1}

**Habla:** Persona 1 · **Dura:** 0:20 · **Se ve:** portada con el QR.

**Qué se dice:**

- Buenos días. Somos el equipo de Enlaza, cuidado coordinado.
- Si quieren seguir la demostración en su celular, el QR abre la aplicación real: enlaza.zenthinks.com.
- En diez minutos les mostramos el problema, el sistema funcionando en vivo y por qué es un negocio viable.

### Diapositiva 2 · El problema {#d2}

**Habla:** Persona 1 · **Dura:** 0:35 · **Se ve:** tres cifras grandes y su fuente.

**Qué se dice:**

- En la Ciudad de México viven {{ seed.pop60_cdmx }} personas de 60 años o más, según el Censo 2020; en todo el país, {{ ctx.mexico_60mas_2024 }}.
- Y no llegan sanas: {{ cal.ref_multimorbidity }} vive con dos o más enfermedades crónicas, según la ENSANUT.
- Las residencias y los servicios a domicilio que las cuidan coordinan con llamadas, WhatsApp y hojas de cálculo: se pierden solicitudes, lo urgente compite con lo rutinario y no queda registro.

### Diapositiva 3 · La solución {#d3}

**Habla:** Persona 1 · **Dura:** 0:30 · **Se ve:** la frase y los seis módulos con su materia.

**Qué se dice:**

- Enlaza es una plataforma web por suscripción que asigna sola cada visita, deja lo delicado a una persona y avisa a tiempo de una emergencia.
- Cada módulo responde a una materia: la operación a SIE, la simulación a Modelado y Simulación, la voz a Cómputo Cognitivo, los tableros a Visualización, el negocio a Emprendimiento y la ética a Práctica Profesional.
- Pero es una sola aplicación, y se los vamos a enseñar funcionando.

### Diapositiva 4 · Demostración en vivo {#d4}

**Habla:** Persona 2, Persona 3 y Persona 4 · **Dura:** 4:50 · **Se ve:** la diapositiva de pausa con el QR y el recorrido; después, la pantalla de la laptop.

**Qué se dice:**

- (Persona 2) Ahora en vivo: esto es la aplicación real, corriendo en esta laptop y publicada en enlaza.zenthinks.com. Son cuatro pasos.
- Paso 1: una familia pide un servicio desde un celular y Enlaza lo asigna sola, sin que nadie toque nada.
- Paso 2: lo urgente sí lo aprueba una persona, y el tablero se actualiza en vivo.
- Paso 3: una contingencia ambiental en el oriente; Enlaza la detecta y propone cambios, pero nada cambia sin aprobación.
- Paso 4: una nota de voz de emergencia abre la pantalla roja del 911 antes que cualquier otra cosa.
- El paso a paso, con quién opera qué, está en la sección «Demostración en vivo, paso a paso».

#### 1:25–1:35 · Entrada a la demo

**Habla:** Persona 2 · **Dura:** 0:10 · **Se ve:** diapositiva 4 y luego el tablero de coordinación en el proyector.

- Ahora en vivo. En el proyector está el tablero de coordinación de la Clínica Oriente; y en este celular tenemos la cuenta de una familia.

#### 1:35–2:35 · Paso 1 · La familia solicita y se asigna sola

**Habla:** Persona 2 (narra) · **Opera:** Persona 3 en el celular · **Dura:** 1:00 · **Se ve:** el tablero en el proyector.

- Desde el celular, con datos móviles, la familia pide una visita de enfermería para hoy, en un par de horas.
- Fíjense en el tablero: aparece sola, sin recargar, en un par de segundos.
- Ya tiene a alguien asignado: el despachador eligió a quien tiene la habilidad, está en turno, no está en su día de descanso y llega antes con el tráfico de esa hora.
- Es prioridad media, así que no necesitó aprobación.

#### 2:35–3:45 · Paso 2 · Coordinación aprueba una urgente

**Habla:** Persona 2 (narra y opera la laptop) · **Dura:** 1:10 · **Se ve:** `/demo` → `/aprobaciones` → `/tablero`.

- (Antes de hablar, en la ventana de Dirección: «Contingencia en el oriente». Tarda hasta un minuto en detectarse; la usamos en el paso 3.)
- Ahora una solicitud urgente: prioridad alta, visita en menos de {{ cfg.urgent_within }}.
- Lo urgente no se asigna solo: Enlaza propone a la mejor persona y coordinación decide. Aquí está, en Aprobaciones.
- Apruebo, y en el tablero cambia en vivo.
- Si coordinación no contesta en {{ cfg.auto_apply_after }}, se aplica con aviso; eso lo decidimos por lo que nos mostró la simulación, se los cuento en un momento.

#### 3:45–5:05 · Paso 3 · Contingencia en el oriente

**Habla:** Persona 3 · **Opera:** Persona 2 · **Dura:** 1:20 · **Se ve:** `/contingencia` → «Aprobar todo» → `/tablero`; al final, `/demo` → «Volver a normal».

- Hace un minuto simulamos mala calidad del aire en el oriente de la ciudad. El worker la detectó solo.
- Enlaza propone cambios por institución: subir la prioridad de quienes tienen enfermedad del pulmón o del corazón, avisar a sus familias y, si tienen oxigenoterapia en las próximas horas, adelantarla. El personal se reacomoda solo si además hay tráfico degradado (escenario «Contingencia + bloqueo en Iztapalapa»).
- Nada cambia sin aprobación: coordinación revisa y aprueba todo.
- Y el tablero ya muestra los cambios. Esto responde al incidente crítico del Problema Prototípico.
- (Persona 2, sin decir nada, en la ventana de Dirección `/demo`: «Volver a normal», para que la contingencia no siga activa.)

#### 5:05–6:15 · Paso 4 · Nota de voz de emergencia

**Habla:** Persona 4 · **Opera:** Persona 4 en la ventana de la familia · **Dura:** 1:10 · **Se ve:** `/voz` → pantalla roja.

- Ahora la voz. Una familia graba lo que pasa, como mandaría un audio de WhatsApp.
- (Al micrófono, exactamente:) «Mi mamá no puede respirar y tiene los labios morados.»
- Pantalla roja, «Llama al 911 ahora». Sale antes que el modelo de lenguaje, porque la activó una regla.
- Si solo el clasificador hubiera sospechado, sería un aviso ámbar y coordinación llamaría a la familia.
- El médico recibe la transcripción y un reporte. El sistema nunca diagnostica.

### Diapositiva 5 · La simulación nos dijo cómo asignar {#d5}

**Habla:** Persona 3 · **Dura:** 0:40 · **Se ve:** la gráfica de espera de lo urgente, con sus intervalos, y el recuadro de la aprobación lenta.

**Qué se dice:**

- SIRAG-D simula semanas completas con el mismo código de asignación: {{ sim.runs_main }} corridas, {{ cfg.replications }} réplicas por combinación.
- Lo que más ayuda es priorizar por riesgo: la espera p90 de lo urgente baja de {{ sim.normal.human_dispatcher.high_wait_p90_min }} a {{ sim.normal.risk_priority.high_wait_p90_min }} minutos, con {{ test.normal.high_wait_p90_min.risk_priority.p }}. El tráfico casi no agrega.
- Y cuando coordinación tarda {{ sens.approval_delay.5-15.label }} en aprobar, el límite de {{ cfg.auto_apply_after }} y la reserva mantienen la espera en {{ sens.approval_delay.5-15.vela_timeout.high_wait_p90_min }}; sin el límite sube a {{ sens.approval_delay.5-15.risk_plus_live_traffic.high_wait_p90_min }}.
- (Historia, corrida anterior del 21 nov con la plantilla de 7 días, solo si da tiempo o si preguntan:) con coordinación lenta, Enlaza sin límite quedaba peor que el despacho humano ({{ hist.sens_antes_espera }}); por eso agregamos el límite y la reserva.

### Diapositiva 6 · Enlaza Voz {#d6}

**Habla:** Persona 4 · **Dura:** 0:40 · **Se ve:** los dos niveles y los números del holdout.

**Qué se dice:**

- Lo evaluamos a ciegas con {{ voz.holdout.n }} frases que nunca vio: detectó {{ voz.holdout.sens }} de las emergencias; solo con reglas habría sido {{ voz.holdout.sens_rules }}.
- El costo son {{ voz.holdout.fa100 }} falsas alarmas por cada 100 notas. Por eso hay dos niveles: la pantalla roja cuando hay una regla y un aviso ámbar que revisa coordinación cuando solo sospecha el clasificador.
- Preferimos una falsa alarma revisada por una persona a una emergencia perdida.

### Diapositiva 7 · Seguridad, privacidad y ética {#d7}

**Habla:** Persona 1 · **Dura:** 0:35 · **Se ve:** 0 / 150 / 400 y los cuatro compromisos.

**Qué se dice:**

- La seguridad está en la base de datos: sin institución, la API ve {{ db.rls_patients_none }} pacientes; con la Clínica Oriente, {{ db.rls_patients_insa }}; Dirección, {{ db.rls_patients_all }}.
- Sin consentimiento del tipo correcto, la API bloquea la voz, la visita o los datos de salud, y si la persona dice que no, también.
- Cumplimos la LFPDPPP con aviso, derechos ARCO y bitácora, y la Ley Federal del Trabajo: el despachador respeta descanso, jornada y relevos.

### Diapositiva 8 · Modelo de negocio y mercado {#d8}

**Habla:** Persona 4 · **Dura:** 0:40 · **Se ve:** la gráfica del DENUE y el modelo de suscripción.

**Qué se dice:**

- Vendemos una suscripción mensual por tamaño de institución: en promedio {{ bm.arpa1 }} al mes el primer año.
- El mercado no lo inventamos: lo contamos en el DENUE. Solo en la Ciudad de México hay {{ neg.denue_residences_private_cdmx }} residencias privadas, y crecemos a Estado de México, Jalisco y Nuevo León.
- Cada cliente vale {{ bm.ltv_cac }} veces lo que cuesta conseguirlo.

### Diapositiva 9 · Pitch: por qué invertir ahora {#d9}

**Habla:** Persona 3 · **Dura:** 0:30 · **Se ve:** inversión, VPN, TIR, la condición del escenario y el envejecimiento.

**Qué se dice:**

- Pedimos {{ bm.sc.recommended.investment }}. En el escenario recomendado el VPN al {{ bm.rate_25 }} es {{ bm.sc.recommended.npv25 }} y la TIR {{ bm.sc.recommended.tir }}.
- Y lo decimos en voz alta: ese escenario supone el plan Gobierno y que los fundadores cobran el {{ neg.founder_salary_year1_recommended }} % el primer año; sin ambos, el VPN sería negativo ({{ bm.rec_wo_both }}).
- ¿Por qué ahora? En la Ciudad de México las personas de 60 o más pasan de {{ ctx.cdmx_prop_60mas_2022 }} a {{ ctx.cdmx_prop_60mas_2030 }} de la población en 2030, según CONAPO.

### Diapositiva 10 · Cierre {#d10}

**Habla:** Persona 1 · **Dura:** 0:15 · **Se ve:** logros, limitaciones y siguientes pasos.

**Qué se dice:**

- En resumen: una sola aplicación, en tiempo real, que integra las seis materias y que la simulación nos ayudó a diseñar.
- Sus límites: datos sintéticos, falsas alarmas de voz y que falta probarla con una institución real; ese es el siguiente paso.

### Diapositiva 11 · Gracias {#d11}

**Habla:** Persona 1 · **Dura:** 0:05 · **Se ve:** «Gracias», «¿Preguntas?», el QR y los nombres. **Se queda en pantalla durante los 5 minutos de preguntas.**

**Qué se dice:**

- (Persona 1 pasa a esta diapositiva.) Gracias. Con gusto respondemos sus preguntas.

### Diapositiva 12 · Respaldo (no se presenta) {#d12}

**Habla:** quien esté narrando · **Dura:** 0:00 · **Se ve:** cuatro capturas de la demo.

**Qué se dice:**

- Solo si falla la demostración en vivo: se narra cada paso sobre su captura, con las mismas frases de la demo.

## Demostración en vivo, paso a paso

**Quién opera qué:** Persona 2 maneja la laptop (proyector) durante toda la demo; Persona 3 tiene el celular de la familia;
Persona 4 toma el micrófono de la laptop en el paso 4.

| Dispositivo | Cuenta (contraseña `Demo2026!`) | Dirección y pestañas |
|---|---|---|
| Laptop · ventana «Coordinación» (Chrome, perfil normal) | `coordinacion.a@ejemplo.test` | `https://enlaza.zenthinks.com`: pestañas `/tablero`, `/aprobaciones`, `/contingencia` |
| Laptop · ventana «Dirección» (Chrome, otro perfil) | `owner@ejemplo.test` | `https://enlaza.zenthinks.com/demo` |
| Laptop · ventana «Familia» (Edge) | `fam-0001@ejemplo.test` | `https://enlaza.zenthinks.com/voz`, con el permiso del micrófono ya aceptado |
| Laptop · ventana «Respaldo» (Edge) | `fam-0002@ejemplo.test` | `http://localhost:8080/familia` (otra dirección, otra sesión: sirve si el celular no tiene señal) |
| Celular de Persona 3, **con datos móviles** | `fam-0002@ejemplo.test` | `https://enlaza.zenthinks.com/familia` (prioridad media: se asigna sola) |

Cada ventana necesita su propia sesión: una misma ventana del navegador solo guarda una sesión por dirección. Por eso son
perfiles o navegadores distintos.

| Paso | Qué se hace | Qué se debe ver | Plan B |
|---|---|---|---|
| 1. La familia solicita | Celular: «Solicitar servicio», visita de enfermería, para hoy, en un par de horas (la fecha de hoy y la primera hora disponible unas dos horas después de la hora actual) | En el tablero del proyector aparece la solicitud, ya asignada y marcada «Nueva», sin recargar | Sin señal en el celular: Persona 2 lo hace en la ventana «Respaldo». Si el tablero no se mueve: recargar (F5) |
| 2. Urgente | Ventana Dirección: «Contingencia en el oriente» (para el paso 3) y «Crear solicitud urgente» → Coordinación `/aprobaciones` → «Aprobar» → `/tablero` | La solicitud pasa de Aprobaciones al tablero, en vivo | Si no aparece en Aprobaciones: recargar. Si se pasa de {{ cfg.auto_apply_after }}, sale «aprobada por tiempo»: se explica que esa es la regla |
| 3. Contingencia | Coordinación `/contingencia` → «Aprobar todo» → `/tablero`; después, Dirección `/demo` → «Volver a normal» | Propuesta por institución; tras aprobar, los cambios en el tablero | Si aún no hay propuesta (el worker revisa cada minuto): seguir con el paso 4 y volver al final; si no llega, diapositiva 12 (Respaldo). Siempre «Volver a normal» al terminar |
| 4. Voz | Ventana Familia `/voz`: grabar «Mi mamá no puede respirar y tiene los labios morados.» | Pantalla roja «Llama al 911 ahora» | Micrófono falla: «Escribir el mensaje» y pegar la misma frase. Servicio de voz caído: también escrito |

**Frases de voz ya probadas:**

- Emergencia (activa la regla de dificultad grave para respirar, pantalla roja): **«Mi mamá no puede respirar y tiene los labios morados.»** Usar exactamente esta.
- Rutina (por si piden otra): «Mi papá amaneció de buen humor, desayunó completo y ya se tomó sus pastillas.»
- **No usar** «Hoy mi mamá comió bien y durmió su siesta»: el clasificador la marca como emergencia (aviso ámbar). Si sale un
  ámbar inesperado, no es un error: es el momento de explicar los dos niveles y la revisión humana.

**Si falla todo lo demás:**

| Qué pasa | Qué hacer (sin detener la exposición) |
|---|---|
| No hay internet en el salón | Seguir en `http://localhost:8080` en las mismas ventanas (la app corre en la laptop). El QR del público no abrirá: decirlo y seguir |
| `enlaza.zenthinks.com` da error 502 o 1033 | Persona 1 corre `bash scripts/enlaza.sh estado` en la terminal mientras Persona 2 sigue en `http://localhost:8080`. Si es 502: `bash scripts/autostart.sh`. Si es 1033: PowerShell como administrador → `Restart-Service cloudflared`; si en 2 min no vuelve, plan B: túnel rápido `bash scripts/enlaza.sh rapido` (con `--protocol http2`) y QR nuevo con `uv run scripts/make_qr.py <enlace>` |
| La app no responde ni en `localhost` | Ir a la diapositiva 12 (Respaldo) y narrar los cuatro pasos sobre las capturas; al final, ofrecer el video de respaldo |
| El tablero dice «Reconectando…» | Esperar 5 s; si sigue, recargar |

## Preguntas del sínodo (5 minutos)

Mientras tanto se queda en pantalla la diapositiva 11 (Gracias, con el QR). En orden de probabilidad. Responde primero quien aparece; los demás completan solo si hace falta. Respuestas cortas: 20 a 30 s.

| # | Pregunta | Responde | Respuesta corta |
|---|---|---|---|
| 1 | ¿Es viable el negocio? ¿Cuándo es rentable? | Persona 3 | El plan base deja de perder dinero en el mes {{ bm.breakeven_month }}, pero su VPN al {{ bm.rate_25 }} es {{ bm.sc.base.npv25 }}; lo decimos. El recomendado limita la participación y crece por regiones: VPN {{ bm.sc.recommended.npv25 }}, TIR {{ bm.sc.recommended.tir }}, inversión {{ bm.sc.recommended.investment }}. |
| 2 | ¿Qué tan grande es el mercado? | Persona 4 | Contado en el DENUE: {{ neg.denue_residences_private_cdmx }} residencias privadas en la CDMX, {{ neg.denue_residences_private_edomex }} en el Estado de México, {{ neg.denue_residences_private_jalisco }} en Jalisco y {{ neg.denue_residences_private_nuevoleon }} en Nuevo León, más centros de día. Los públicos compran por licitación: van aparte. |
| 3 | ¿Ustedes programaron esto? | Persona 1 | El problema, el diseño, las reglas, las decisiones y la revisión son del equipo; la mayor parte del código la escribió un asistente de programación con IA (Claude Code) bajo esas reglas, con un pull request por cambio y {{ repo.tests_summary }}. Podemos defender cada parte. |
| 4 | ¿Por qué datos sintéticos? | Persona 1 | Porque son datos de salud y el proyecto es público. Generamos {{ seed.persons }} personas calibradas con el Censo, la ENSANUT y la ENASEM: las proporciones se parecen a la realidad, las personas no existen. |
| 5 | ¿Cómo evitan que una institución vea los datos de otra? | Persona 2 | Seguridad por fila en PostgreSQL: la API se conecta con un usuario que no es dueño de las tablas y fija la institución en cada petición; sin institución ve {{ db.rls_patients_none }} filas. Un intento ajeno responde 403 y queda en la bitácora. |
| 6 | ¿La máquina decide todo? | Persona 2 | No. Lo rutinario se asigna solo; lo de prioridad alta lo aprueba una persona. Solo lo urgente sin respuesta en {{ cfg.auto_apply_after }} se aplica con aviso, y coordinación lo puede cambiar. |
| 7 | ¿Qué pasa con una falsa alarma de voz? | Persona 4 | Si solo sospecha el clasificador, sale un aviso ámbar y coordinación llama a la familia; sin respuesta en {{ cfg.escalate_after }} se escala a Dirección. Preferimos una falsa alarma revisada a una emergencia perdida. |
| 8 | ¿Qué tan bueno es el asistente de voz? | Persona 4 | En el holdout a ciegas: {{ voz.holdout.sens }} de emergencias detectadas, {{ voz.holdout.fa100 }} falsas alarmas por 100 notas. No presumimos la prueba interna porque esos datos se usaron para construirlo. |
| 9 | ¿El modelo de lenguaje diagnostica? | Persona 4 | No. Resume lo dicho en un formato fijo con filtro de frases prohibidas; el nivel lo ponen las reglas y el clasificador, y nunca le dice a nadie que algo no es una emergencia. |
| 10 | ¿Cómo validaron la simulación? | Persona 3 | Con las reglas de antes, reproduce el «sin atender» del historial en servicios cortos ({{ sim.val_sim_short_pct }} contra {{ sim.val_real_short_pct }}); con turnos largos difiere y sabemos por qué. |
| 11 | ¿Qué cambió en el producto por la simulación? | Persona 3 | El límite de tiempo para lo urgente y la reserva del candidato: con una coordinación lenta, lo urgente esperaba más que con un despachador humano ({{ hist.sens_antes_espera }}, corrida del 21 nov). |
| 12 | ¿Cómo cumplen la ley de datos personales? | Persona 1 | Consentimiento por tipo de uso con vencimiento, y el asentimiento de la persona; aviso de privacidad; ARCO con los plazos de ley; seguridad por fila y bitácora. Sin consentimiento, la API bloquea la función. |
| 13 | ¿Y la Ley Federal del Trabajo? | Persona 2 | El despachador respeta el descanso semanal (art. 69), el tipo de jornada (art. 60), los máximos (art. 61) y los relevos; lo que exceda la ley se marca y se avisa. |
| 14 | ¿Qué pasa si falla el internet? | Persona 2 | Todo corre en la laptop; solo se pierden el enlace público y las calles del mapa. Seguimos en `localhost:8080`. |
| 15 | ¿Cómo eligen a quién mandar? | Persona 2 | Quien tiene la habilidad, está en turno, no está en su día de descanso y no tiene otra visita que se cruce; entre ellos, quien llega antes con el tráfico de esa hora. La cola va por prioridad, riesgo y espera. |
| 16 | ¿Por qué Friedman y no ANOVA? | Persona 3 | Porque todas las políticas se prueban sobre las mismas réplicas (números aleatorios comunes): son muestras pareadas y casi nunca normales. Después, Wilcoxon con corrección de Holm. |
| 17 | ¿Cómo responde Enlaza al incidente crítico? | Persona 1 | La contingencia se ve por estación, no promediada; el despachador prioriza riesgo y tráfico; una sola base reasigna sin copiar datos; la voz declara su sesgo; el consentimiento se exige en la API, y el negocio crece por regiones. |
| 18 | ¿Qué cambió desde el Avance 2? | Persona 1 | La asignación pasó de sugerida a automática con aprobación humana en lo delicado; más instituciones; y se agregaron la voz, la simulación, la contingencia, la ley laboral y el negocio. |
| 19 | ¿Qué no funciona o qué falta? | Persona 3 | Las falsas alarmas de voz, la evaluación con hablantes reales (también de lenguas originarias), el diagnóstico de campo y la prueba con una institución real. |
| 20 | ¿Cuánto le cuesta a una institución? | Persona 4 | Suscripción mensual por tamaño; en promedio {{ bm.arpa1 }} al mes el primer año. Conseguir un cliente cuesta {{ neg.cac_per_institution }} pesos y vale {{ bm.ltv_cac }} veces eso. |

## Checklist del día

**1 hora antes** (Persona 2 con la laptop, Persona 3 con el celular)

- [ ] Laptop conectada a la corriente; suspensión en «Nunca».
- [ ] `bash scripts/enlaza.sh estado`: «Conexión con Cloudflare: CONECTADO», «Protocolo: http2», reconexión automática instalada, archivos «bien», dirección pública ok, reloj en 0 s.
- [ ] **Si la página da error 1033: PowerShell como administrador → `Restart-Service cloudflared`.** Se arregla solo en menos de un minuto al cambiar de red; si no, este comando.
- [ ] Plan B listo: si en 2 min no vuelve, `bash scripts/enlaza.sh rapido` (túnel rápido con `--protocol http2`; en PowerShell: `cloudflared tunnel --protocol http2 --url http://localhost:8080`) y QR nuevo con `uv run scripts/make_qr.py <enlace>`.
- [ ] `uv run scripts/check_public_url.py`: 12 de 12.
- [ ] `ollama run` con el modelo de `OLLAMA_MODEL` y la frase «hola» (lo deja cargado).
- [ ] `bash scripts/backup_db.sh antes_coloquio` y `python3 scripts/reset_demo.py`; `python3 scripts/verify_db.py` en «Todo correcto».
- [ ] Ensayo rápido de los cuatro pasos y otra vez `python3 scripts/reset_demo.py`.

**15 minutos antes**

- [ ] Abrir las cuatro ventanas de la tabla de arriba, cada una con su sesión iniciada y en su pestaña.
- [ ] En la ventana Familia, aceptar el permiso del micrófono y **probar la frase** «Mi mamá no puede respirar y tiene los labios morados.»: debe salir la pantalla roja. Después, `python3 scripts/reset_demo.py` (borra esa prueba) y recargar las ventanas.
- [ ] Celular de Persona 3: wifi apagado, datos móviles, sesión de `fam-0002` en `/familia`.
- [ ] Proyector a 1280 × 720 o más; presentación abierta en modo presentador; cronómetro listo.
- [ ] La presentación en PDF y el video de respaldo en el escritorio, por si falla PowerPoint.

**Justo antes**

- [ ] Tablero de coordinación «● En vivo».
- [ ] Notificaciones de Windows y del celular en silencio.
- [ ] Cada quien sabe su primera frase y quién le pasa la palabra.

**Al terminar la presentación**

- [ ] `python3 scripts/reset_demo.py` (borra lo que creó la demo: solicitudes, la contingencia, la nota de voz y sus alertas).
- [ ] `bash scripts/backup_db.sh despues_coloquio` si se quiere guardar cómo quedó antes de limpiar (correrlo antes del reset).

## Video de respaldo (4 minutos)

Se graba **después** del último cambio de interfaz, con la grabadora de pantalla de Windows (Win + Alt + R o la Herramienta
Recortes), sin audio de fondo. Antes: `python3 scripts/reset_demo.py` y las mismas ventanas de la demo.

| Tiempo | Qué se graba | Qué se dice (voz en off, una sola persona) |
|---|---|---|
| 0:00–0:20 | Portada `https://enlaza.zenthinks.com` | «Enlaza coordina el cuidado de personas mayores. Esta es la aplicación real, en vivo.» |
| 0:20–1:10 | Celular (o ventana Respaldo) solicita; el tablero se actualiza | «La familia pide una visita; Enlaza la asigna sola a quien puede ir y llega antes.» |
| 1:10–2:00 | Dirección: «Crear solicitud urgente»; Coordinación aprueba; tablero | «Lo urgente lo aprueba una persona; el tablero se actualiza en vivo.» |
| 2:00–3:00 | Contingencia: propuesta y «Aprobar todo» | «Enlaza detecta la contingencia ambiental y propone cambios; nada cambia sin aprobación.» |
| 3:00–3:40 | Voz: frase de emergencia → pantalla roja | «Una nota de voz de emergencia abre la pantalla del 911 antes que cualquier otra cosa.» |
| 3:40–4:00 | `/simulacion` y `/negocio` | «La simulación cambió el producto, y el negocio es viable con crecimiento por regiones.» |

Al terminar: `python3 scripts/reset_demo.py`. Guardar el video como `docs/privado/video_respaldo.mp4` (Git lo ignora).
