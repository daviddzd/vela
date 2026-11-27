# Guion de narración · Videos de Enlaza

Fuente de los dos videos explicativos. **Se edita aquí**; los números se escriben como una clave entre dobles llaves y salen de
`docs/biblia/out/numeros.json` (el mismo script de la biblia y del coloquio). Cada bloque `### Escena` es un tramo del
video: **Se ve** dice qué aparece en pantalla (diapositiva o grabación de la app) y **Dice** es lo que lee la voz
sintética, palabra por palabra. Los tiempos son aproximados (la voz lee unas 140 palabras por minuto).

Cuentas de la grabación (contraseña `Demo2026!`, pública y solo para usuarios sintéticos): familia `fam-0002` y
`fam-0001`, coordinación `coordinacion.a`, cuidado `cui-003`, medicina `cui-001`, Dirección `owner`.

---

# Video 1 · Enlaza explicado (≈ 20 min)

## 1. Qué es Enlaza y qué problema resuelve (≈ 1:40)

### Escena 1.1 · Portada
**Se ve:** diapositiva de portada: «Enlaza · cuidado coordinado», «Video explicativo para el equipo», «Prototipo académico · datos sintéticos».

**Dice:**
Hola. Este video explica Enlaza en unos veinte minutos, para entender el proyecto y la aplicación sin leer toda la biblia.
Primero, qué problema resuelve. Después, un recorrido por la aplicación real, rol por rol. Luego, cómo funciona por dentro.
Al final, las seis materias y los números que hay que saberse.

### Escena 1.2 · El problema
**Se ve:** diapositiva «El problema»: el número de personas mayores, y cuatro íconos: WhatsApp, hoja de cálculo, tráfico, aire contaminado.

**Dice:**
En la Ciudad de México viven {{ seed.pop60_cdmx }} personas de sesenta años o más. Las instituciones que las cuidan,
residencias, centros de día y redes de cuidado a domicilio, coordinan las visitas con llamadas, WhatsApp y hojas de
cálculo. Se pierden solicitudes, nadie sabe quién está libre ni cuánto va a tardar con el tráfico, lo urgente compite
con lo rutinario y no queda registro. Y en una contingencia ambiental, las personas con enfermedades del pulmón o del
corazón son las más afectadas.

### Escena 1.3 · La solución
**Se ve:** diapositiva «La solución»: una frase grande y los seis módulos con su ícono.

**Dice:**
Enlaza es una plataforma web por suscripción para esas instituciones. La familia, la coordinación o una nota de voz
crean una solicitud; el sistema asigna sola a la persona adecuada; la coordinación sigue cada visita en vivo; la
dirección decide con datos; y una nota de voz que suena a emergencia abre de inmediato la pantalla del nueve once.
Es un prototipo escolar: la empresa es ficticia y todos los datos son sintéticos. Generamos {{ seed.persons }} personas
calibradas con el Censo, la ENSANUT y la ENASEM. Las proporciones se parecen a la realidad; las personas no existen.

## 2. Recorrido por la web, rol por rol (≈ 7:30)

### Escena 2.1 · Página pública y entrada
**Se ve:** grabación: `/` (página pública, desplazamiento lento) → «Entrar» → `/entrar`, se escribe `fam-0002@ejemplo.test`.

**Dice:**
Esta es la aplicación real, la misma que se abre en {{ ops.public_url }}. La página de inicio es pública y no muestra
datos de nadie. Cada persona entra con su correo y su contraseña, y Enlaza le muestra solo las pantallas de su rol.
La casilla «Modo sencillo» agranda la letra para quien lo necesite. Empezamos con una familia.

### Escena 2.2 · Familia: próximas visitas y solicitar
**Se ve:** grabación: `/familia` de `fam-0002`: «Próximas visitas», «Solicitar servicio» → visita de enfermería, mañana a las 11:00 → «Asignada» con el nombre de quien va.

**Dice:**
La familia ve las próximas visitas: lo que ya está asignado y lo que el plan de cuidado tiene programado. Para pedir
algo más, toca «Solicitar servicio», elige el servicio, el día y la hora. No elige la prioridad: se usa la del
paciente, para que nadie marque todo como urgente. Esta paciente es de prioridad media, así que la solicitud se asigna
sola, al instante: ya dice quién va a ir y a qué hora. Cuando la visita termina, la familia confirma que sí se hizo.

### Escena 2.3 · Familia con prioridad alta
**Se ve:** grabación: sesión de `fam-0001` → la misma solicitud → «En espera».

**Dice:**
Otra familia pide lo mismo, pero su paciente tiene prioridad alta. Entonces la solicitud queda en espera: Enlaza
propone a la mejor persona, pero la decisión la toma coordinación.

### Escena 2.4 · Coordinación: tablero en vivo
**Se ve:** grabación: `coordinacion.a` en `/tablero`: reloj, contadores, «¿Quién espera más?», alertas, mapa con figuras, indicador «En vivo».

**Dice:**
Esta es la pantalla de coordinación de la Clínica Oriente, el centro de la operación. Arriba, la hora real de la Ciudad
de México y los contadores: en cola, en camino, en visita y terminadas. «¿Quién espera más?» muestra la solicitud que
lleva más tiempo esperando. Las alertas avisan de franjas sin personal, turnos que exceden la jornada legal o notas de
voz por revisar. En el mapa, cada punto tiene forma y palabra, no solo color: triángulo en espera, círculo asignada.
Y el indicador «En vivo» dice que el tablero se actualiza solo, sin recargar.

### Escena 2.5 · Coordinación: aprobaciones
**Se ve:** grabación: `/aprobaciones`: la solicitud de `fam-0001` con el candidato propuesto, dos alternativas, tiempos de viaje → «Aprobar» → aparece en el tablero.

**Dice:**
En Aprobaciones está la solicitud de prioridad alta. Enlaza propone un candidato y dos alternativas, cada una con su
tiempo de viaje con el tráfico de esa hora. Coordinación aprueba cualquiera. Si la visita es urgente, es decir, en menos
de {{ cfg.urgent_within }}, y nadie contesta en {{ cfg.auto_apply_after }}, se aplica la propuesta con aviso: «aprobada por
tiempo». Mientras tanto, el horario del candidato queda reservado {{ cfg.hold_minutes }}, para que algo rutinario no se lo gane.

### Escena 2.6 · Coordinación: pacientes y personal
**Se ve:** grabación: `/pacientes` (filtros, indicador de riesgo) → ficha `PAC-0001` → `/personal` (turnos, descanso, cobertura).

**Dice:**
En Pacientes se busca y se filtra por alcaldía, prioridad o sensibilidad a la contaminación. La ficha muestra el plan de
cuidado, los consentimientos y el historial; los datos de salud solo aparecen si hay consentimiento, y abrir una ficha
queda en la bitácora. En Personal se ve quién está en turno, su jornada, su día de descanso y la cobertura de los
próximos días, con las franjas donde una habilidad se queda sin nadie.

### Escena 2.7 · Cuidado: Llegué y Terminé
**Se ve:** grabación: `cui-003` en `/mis-visitas` (vista de celular): la visita de hoy → «Llegué» → «Terminé».

**Dice:**
Ahora el personal de cuidado. En su celular ve sus visitas de hoy: hora, paciente, servicio, alcaldía y a qué hora
salir. Al llegar toca «Llegué», y al terminar, «Terminé». La hora la pone el servidor, no el teléfono, y antes de
aceptar, Enlaza vuelve a revisar que el consentimiento de atención a domicilio siga vigente. Si una visita dura más que
un turno legal, la cubren dos personas en relevo.

### Escena 2.8 · Voz: la familia escribe un mensaje de emergencia
**Se ve:** grabación: `fam-0001` en `/voz` → «Escribir el mensaje» → «Mi mamá no puede respirar y tiene los labios morados.» → pantalla roja «Llama al 911 ahora».

**Dice:**
El asistente de voz, Enlaza Voz, recibe una nota grabada, como un audio de WhatsApp, o un mensaje escrito. Para este
video lo escribimos: «Mi mamá no puede respirar y tiene los labios morados». La pantalla se pone roja: «Llama al nueve
once ahora», con un botón grande. Sale de inmediato, antes de cualquier reporte, porque la activó una regla de
emergencia. Si solo el clasificador hubiera sospechado, saldría un aviso ámbar y coordinación llamaría a la familia.

### Escena 2.9 · Medicina: reportes de voz
**Se ve:** grabación: `cui-001` en `/reportes-voz`: la nota recién enviada con transcripción, reglas activadas y resumen.

**Dice:**
La médica ve esa misma nota en Reportes de voz: la transcripción, las reglas que se activaron y un resumen que escribe
el modelo de lenguaje local. Arriba lo dice claro: es un resumen de lo que se dijo, no un diagnóstico. La médica solo
ve a sus pacientes, y solo si hay consentimiento de datos de salud.

### Escena 2.10 · Dirección: Panorama
**Se ve:** grabación: `owner` en `/panorama`: vista Operación (puntualidad, carga) → vista Panorama (población por alcaldía, referencias oficiales).

**Dice:**
Dirección es el único rol que ve todas las instituciones. Panorama reúne los tableros para decidir: puntualidad, carga
del personal y, en la otra vista, la población por alcaldía, las enfermedades comparadas con las referencias oficiales,
la calidad del aire y el tráfico. Cada gráfica responde una pregunta, se compara con una referencia y dice su fuente.

### Escena 2.11 · Dirección: simulación
**Se ve:** grabación: `/simulacion`: comparación de formas de asignar con intervalos de confianza, «Modo presentación».

**Dice:**
En Simulación están los resultados de SIRAG-D: semanas completas simuladas con el mismo código de asignación, que
comparan formas de asignar, con intervalos de confianza. Lo explicamos más adelante, porque nos dijo cómo asignar.

### Escena 2.12 · Dirección: contingencia
**Se ve:** grabación: `/demo` → «Contingencia en el oriente» → `/contingencia`: estaciones del aire, propuesta por institución → «Aprobar todo» → `/demo` → «Volver a normal».

**Dice:**
El panel de demostración solo cambia datos de entrada, como las lecturas del aire. Simulamos mala calidad del aire en el
oriente. En el minuto siguiente, el worker la detecta solo y Enlaza propone cambios por institución: adelantar visitas
de quienes tienen enfermedad del pulmón o del corazón y reacomodar al personal. Nada cambia sin aprobación: coordinación
revisa y aprueba. Al terminar, volvemos a la normalidad.

### Escena 2.13 · Dirección: negocio y privacidad
**Se ve:** grabación: `/negocio` (ingreso, costo fijo, equilibrio, VPN; etiquetas «supuesto») → `/privacidad` (aviso, ARCO, bitácora).

**Dice:**
En Negocio está el modelo financiero: ingreso por institución, costo fijo, punto de equilibrio y valor presente a cinco
años; cada cifra dice su fuente o dice «supuesto», y los supuestos se pueden cambiar. En Privacidad están el aviso de
privacidad, los derechos ARCO y, para Dirección, la bitácora de auditoría: quién abrió qué y quién intentó ver algo ajeno.

## 3. Cómo funciona por dentro (≈ 4:40)

### Escena 3.1 · El recorrido de una solicitud
**Se ve:** diagrama: solicitud → despachador (habilidad, turno, descanso, sin cruces, tráfico) → prioridad baja o media: asignada / alta: propuesta → coordinación aprueba (o «aprobada por tiempo» si es urgente) → visita → Llegué/Terminé → la familia confirma.

**Dice:**
Así viaja una solicitud. El despachador busca a quien tiene la habilidad, está en turno, no está en su día de descanso
y no tiene otra visita que se cruce. Entre ellos elige a quien llega antes con el tráfico de esa hora. Si la prioridad
es baja o media, se asigna sola. Si es alta, queda como propuesta y una persona de coordinación la aprueba; solo lo
urgente sin respuesta en {{ cfg.auto_apply_after }} se aplica con aviso. Después vienen la visita, «Llegué», «Terminé» y la
confirmación de la familia.

### Escena 3.2 · Arquitectura: el restaurante
**Se ve:** diagrama del restaurante: comedor = página web, mesero = API, bodega = base de datos, ayudante de cocina = worker, campanita = WebSocket, capitán de meseros = Caddy, repartidor = Cloudflare; todo dentro de una lonchera = Docker.

**Dice:**
Por dentro, Enlaza es como un restaurante. El comedor, donde la gente ve y toca, es la página web, hecha con React. El
mesero es la API, en Python: recibe cada pedido, revisa que esté permitido y trae la respuesta. La bodega es la base de
datos PostgreSQL, que guarda todo. Un ayudante de cocina, el worker, da una vuelta cada {{ code.worker_tick }}: crea visitas
del plan, reintenta la cola, revisa el aire y crea alertas. La campanita que suena cuando sale un plato es el WebSocket.
El capitán de meseros en la puerta es Caddy, una sola entrada para todo. Y el restaurante completo cabe en una lonchera:
Docker, que lo enciende igual en cualquier laptop.

### Escena 3.3 · Seguridad por fila
**Se ve:** diagrama del edificio: cinco pisos, un elevador; tres resultados: sin institución {{ db.rls_patients_none }}, Clínica Oriente {{ db.rls_patients_insa }}, Dirección {{ db.rls_patients_all }}.

**Dice:**
Cinco instituciones comparten la misma base de datos, y ninguna puede ver a otra. Piensen en un edificio donde el
elevador solo te lleva a tu piso: aunque te equivoques de botón, no te deja en el de otra empresa. Eso es la seguridad
por fila de PostgreSQL. La API se conecta con un usuario que no es dueño de las tablas y en cada petición fija la
institución. Sin institución, la API ve {{ db.rls_patients_none }} pacientes; con la Clínica Oriente, {{ db.rls_patients_insa }}; y
Dirección, {{ db.rls_patients_all }}. Un intento de ver algo ajeno responde con error y queda en la bitácora.

### Escena 3.4 · Tiempo real
**Se ve:** diagrama: base de datos → aviso «cambió la solicitud 123» → API → WebSocket → tablero vuelve a pedir los datos; reloj de la Ciudad de México.

**Dice:**
El tablero en vivo funciona como el tablero de llegadas de un aeropuerto: cambia solo cuando hay una novedad. Cuando algo
cambia, la base de datos avisa, y la API manda por el WebSocket un aviso corto, sin datos personales. El tablero
vuelve a pedir la información con los permisos de siempre. Si se cae la conexión, dice «Reconectando» y lo intenta de
nuevo cada {{ code.ws_retry_s }}. Y la hora siempre es la real de la Ciudad de México, la del servidor.

### Escena 3.5 · Los tres modelos de inteligencia artificial
**Se ve:** diagrama de Enlaza Voz: voz → Whisper (texto) → reglas → clasificador → pantalla roja o ámbar → qwen3:8b escribe el reporte para el médico. Debajo, una tarjeta por modelo con su número.

**Dice:**
Enlaza Voz usa tres modelos, todos dentro de la laptop. Primero, Whisper, en su versión {{ mod.whisper_modelo }}, de
{{ mod.whisper_archivo }}, convierte la voz en texto. Después, las reglas de emergencia revisan frases como «no puede
respirar»; si una se activa, es emergencia, y nada puede bajarla. Luego, un clasificador de texto, una red neuronal de
{{ mod.clasificador_parametros }} parámetros, que tarda unos {{ mod.clasificador_ms }}. Si dispara una regla, pantalla roja; si solo
sospecha el clasificador, aviso ámbar. Al final, el modelo de lenguaje {{ mod.llm_nombre }}, de {{ mod.llm_parametros }} parámetros, escribe
el reporte para el médico, en unos {{ mod.llm_gpu_reporte }} con la tarjeta gráfica integrada. Ese modelo nunca diagnostica y
nunca le dice a nadie que algo no es una emergencia.

### Escena 3.6 · El enlace enlaza.zenthinks.com
**Se ve:** diagrama: celular → internet → Cloudflare → túnel → laptop (Caddy :8080) → página, API, WebSocket.

**Dice:**
Por último, ¿cómo entra el público desde su celular? Un túnel de Cloudflare conecta la laptop con la dirección fija
{{ ops.public_url }}. No es un servidor en la nube: si la laptop se apaga, se apaga Enlaza. Todo entra por una sola puerta,
Caddy, en el puerto ocho mil ochenta. El túnel usa HTTP dos, para que funcione también en el hotspot de un celular, y
se reconecta solo cuando cambia la red. Si un día la página da el error diez treinta y tres, se abre PowerShell como
administrador y se reinicia el servicio cloudflared.

## 4. Las seis materias (≈ 6:20)

### Escena 4.1 · Sistemas de Información Empresarial
**Se ve:** diapositiva de materia: TPS, CRM, ERP, MIS, DSS; el número clave ({{ seed.assign_auto }} asignaciones automáticas y {{ seed.assign_coordinator }} aprobadas por coordinación); la limitación.

**Dice:**
Sistemas de Información Empresarial. Enlaza es, ante todo, un sistema de información, y tiene las cinco piezas que pide
la materia. Registra cada transacción de las visitas: eso es el TPS. Conoce a pacientes y familias: el CRM. Administra
al personal y los servicios: el ERP. Resume para decidir, en Panorama: el MIS. Y ayuda a elegir entre alternativas, con
la simulación y las propuestas de contingencia: el DSS. Todo vive en una sola base de datos de {{ db.tables_total }} tablas,
compartida por {{ seed.institutions }} instituciones que nunca se ven entre sí. El número clave: en el historial hay
{{ seed.service_requests }} solicitudes; {{ seed.assign_auto }} se asignaron solas y {{ seed.assign_coordinator }} las aprobó coordinación. La
limitación honesta: el ERP es acotado a propósito, sin nómina, facturación ni inventario, y Enlaza no se ha probado con
una institución real.

### Escena 4.2 · Modelado y Simulación
**Se ve:** diapositiva de materia: espera del percentil 90 de lo urgente, {{ sim.normal.human_dispatcher.high_wait_p90_min }} → {{ sim.normal.risk_priority.high_wait_p90_min }} min ({{ test.normal.high_wait_p90_min.risk_priority.p }}); validación {{ sim.val_sim_short_pct }} contra {{ sim.val_real_short_pct }}; la limitación.

**Dice:**
Modelado y Simulación. SIRAG-D es una simulación de eventos discretos: cada paciente tiene una cadena de Markov de salud,
y se simulan semanas completas con el mismo código de asignación de la aplicación. Compara cinco formas de asignar en
tres escenarios, con {{ cfg.replications }} réplicas, intervalos de confianza y pruebas pareadas. Se validó contra el
historial: en servicios cortos, el «sin atender» simulado es {{ sim.val_sim_short_pct }}, contra {{ sim.val_real_short_pct }} real. El
número clave: priorizar por riesgo baja la espera del percentil noventa de lo urgente de
{{ sim.normal.human_dispatcher.high_wait_p90_min }} a {{ sim.normal.risk_priority.high_wait_p90_min }} minutos. Y cuando coordinación tarda
{{ sens.approval_delay.5-15.label }} en aprobar, el límite de tiempo la deja en {{ sens.approval_delay.5-15.vela_timeout.high_wait_p90_min }}
minutos, contra {{ sens.approval_delay.5-15.risk_plus_live_traffic.high_wait_p90_min }} sin el límite. Ese hallazgo cambió el producto. La
limitación honesta: varias probabilidades de salud son supuestos, y el «sin atender», {{ sim.normal.vela_timeout.unattended_pct }}, no lo
mejora ninguna forma de asignar: depende del personal disponible.

### Escena 4.3 · Cómputo Cognitivo
**Se ve:** diapositiva de materia: {{ voz.holdout.sens }} de emergencias detectadas (reglas solas: {{ voz.holdout.sens_rules }}), {{ voz.holdout.fa100 }} falsas alarmas por 100 notas; la limitación.

**Dice:**
Cómputo Cognitivo. Enlaza Voz combina tres técnicas: reconocimiento de voz, clasificación de texto con reglas y una red
neuronal, y un modelo de lenguaje local. Se evaluó con un conjunto a ciegas de {{ voz.holdout.n }} frases que nunca se usó
para construirlo. El número clave: detectó el {{ voz.holdout.sens }} de las emergencias, cuando las reglas solas detectaban el
{{ voz.holdout.sens_rules }}. El clasificador encontró {{ vozb.holdout.emerg_only_classifier }} emergencias que las reglas no veían. Lo
pagamos con {{ voz.holdout.fa100 }} falsas alarmas por cada cien notas, y por eso existen los dos niveles: rojo cuando hay
una regla, ámbar cuando solo sospecha el clasificador, siempre con revisión de una persona. Preferimos una falsa alarma
revisada a una emergencia perdida. La limitación honesta: la meta de menos de diez falsas alarmas no se cumple, las
frases son sintéticas y no se ha probado con personas mayores reales ni con hablantes de lenguas originarias.

### Escena 4.4 · Visualización
**Se ve:** diapositiva de materia: {{ repo.pages }} pantallas; figura y palabra además de color; mínimo de {{ code.min_visits_rate }} y grupos de al menos {{ code.small_cell }}; la limitación.

**Dice:**
Visualización. Panorama y las {{ repo.pages }} pantallas de Enlaza se diseñaron para decidir y para cualquier persona. Cada
gráfica responde una pregunta, se compara con una referencia y dice su fuente. La contingencia se ve estación por
estación, no promediada, para no esconder lo localizado. Nada se comunica solo con color: también hay forma y palabra,
para personas con daltonismo. La letra es grande, los botones también, y todo se lee igual en el proyector que en un
celular. Un ejemplo de honestidad: un porcentaje solo se muestra si hay al menos {{ code.min_visits_rate }}, y ningún grupo
agregado tiene menos de {{ code.small_cell }}. La limitación honesta: no se ha probado con lectores de pantalla ni con
personas mayores, y los mapas con calles necesitan internet.

### Escena 4.5 · Emprendimiento
**Se ve:** diapositiva de materia: ingreso promedio {{ bm.arpa1 }}, equilibrio en el mes {{ bm.breakeven_month }}, VPN base {{ bm.npv_25 }}, recomendado {{ bm.sc.recommended.npv25 }}, LTV/CAC {{ bm.ltv_cac }}; la limitación.

**Dice:**
Emprendimiento. Enlaza es un negocio por suscripción, con tres planes según el tamaño de la institución. En promedio,
cada institución paga {{ bm.arpa1 }} al mes el primer año, y un cliente vale {{ bm.ltv_cac }} veces lo que cuesta
conseguirlo. El plan base deja de perder dinero en el mes {{ bm.breakeven_month }}, pero su valor presente neto al
{{ bm.rate_25 }} es negativo, {{ bm.npv_25 }}, y lo decimos de frente. El escenario recomendado limita la participación y crece
por regiones: da {{ bm.sc.recommended.npv25 }}, pero supone un plan Gobierno y que los fundadores cobren el
{{ neg.founder_salary_year1_recommended }} por ciento de su sueldo el primer año; sin esas dos cosas, el valor sería {{ bm.rec_wo_both }}. El
mercado se contó en el DENUE: {{ neg.denue_residences_private_cdmx }} residencias privadas en la Ciudad de México. La limitación
honesta: no hay entrevistas a clientes y los precios son supuestos.

### Escena 4.6 · Práctica Profesional
**Se ve:** diapositiva de materia: {{ seed.consents }} consentimientos, ARCO en {{ neg.arco_response_days }} días hábiles, jornada nocturna de {{ code.max_night }}, IA supervisada; la limitación.

**Dice:**
Práctica Profesional. Enlaza se construyó como lo haría un profesional responsable. Hay consentimiento informado por
tipo de uso, con vencimiento, y el asentimiento de la persona mayor; sin consentimiento, la API bloquea la función, no
solo la pantalla. Hay aviso de privacidad y derechos ARCO con los plazos de la ley: {{ neg.arco_response_days }} días hábiles para
responder. El despachador respeta la Ley Federal del Trabajo: el descanso semanal y la jornada nocturna máxima de
{{ code.max_night }}. La inteligencia artificial está supervisada por personas, y todo queda en la bitácora. También somos
honestos sobre quién hizo qué: gran parte del código lo escribió un asistente de programación con IA, con las reglas y
la revisión del equipo. La limitación honesta: las plantillas legales no las ha revisado un abogado, no hubo comité de
ética y el diagnóstico de campo todavía está en curso.

## 5. Cierre: los números que hay que saberse (≈ 1:10)

### Escena 5.1 · Números clave
**Se ve:** diapositiva con seis tarjetas de números, que aparecen una por una.

**Dice:**
Para cerrar, los números que hay que saberse. El mundo sintético: {{ seed.persons }} personas, {{ seed.institutions }}
instituciones y {{ seed.patients }} pacientes. La seguridad: sin institución, la API ve {{ db.rls_patients_none }} pacientes. La
operación: lo urgente sin respuesta se aplica con aviso a los {{ cfg.auto_apply_after }}. La simulación: priorizar por riesgo
baja la espera de lo urgente de {{ sim.normal.human_dispatcher.high_wait_p90_min }} a {{ sim.normal.risk_priority.high_wait_p90_min }} minutos.
La voz: {{ voz.holdout.sens }} de emergencias detectadas y {{ voz.holdout.fa100 }} falsas alarmas por cada cien notas. El modelo de
lenguaje: {{ mod.llm_nombre }}, local. Y el negocio: equilibrio en el mes {{ bm.breakeven_month }}, con un valor presente
negativo en el plan base, {{ bm.npv_25 }}, que decimos de frente.

### Escena 5.2 · Gracias
**Se ve:** diapositiva final: {{ ops.public_url }}, «La biblia de Enlaza tiene todo el detalle», «Prototipo académico · datos sintéticos».

**Dice:**
Todo el detalle, con cada fuente, está en la biblia de Enlaza. Y la aplicación está en {{ ops.public_url }}. Gracias.

---

# Video 2 · Demo del coloquio, plan B (≈ 4 min)

Sigue los cuatro pasos de «Demostración en vivo, paso a paso» de `docs/presentacion/guion_fuente.md`, con las mismas
cuentas. La voz se escribe en lugar de grabarse.

### Escena D.1 · Portada
**Se ve:** grabación: `/` de {{ ops.public_url }}.

**Dice:**
Enlaza coordina el cuidado de personas mayores en la Ciudad de México. Esta es la aplicación real, corriendo en una laptop
y publicada en {{ ops.public_url }}. Los datos son sintéticos. Vamos a ver cuatro pasos: una solicitud que se asigna sola,
una urgente que aprueba una persona, una contingencia ambiental y una nota de emergencia.

### Escena D.2 · Paso 1: la familia solicita y se asigna sola
**Se ve:** grabación: lado a lado, `fam-0002` en `/familia` (vista de celular) solicita enfermería mañana a las 11:00, y el `/tablero` de coordinación, donde aparece sin recargar, ya asignada.

**Dice:**
Paso uno. Desde el celular, una familia pide una visita de enfermería para mañana. Fíjense en el tablero de
coordinación: aparece sola, sin recargar, en un par de segundos, y ya tiene a alguien asignado. El despachador eligió a
quien tiene la habilidad, está en turno, no está en su día de descanso y llega antes con el tráfico de esa hora. Es
prioridad media, así que no necesitó aprobación: nadie tuvo que tocar nada.

### Escena D.3 · Paso 2: coordinación aprueba una urgente
**Se ve:** grabación: Dirección `/demo` → «Contingencia en el oriente» y «Crear solicitud urgente» → Coordinación `/aprobaciones` → «Aprobar» → `/tablero`.

**Dice:**
Paso dos. Ahora una solicitud urgente: prioridad alta, con la visita en menos de {{ cfg.urgent_within }}. Lo urgente no se
asigna solo: Enlaza propone a la mejor persona y coordinación decide. Aquí está, en Aprobaciones. Se aprueba, y en el
tablero cambia en vivo. Si coordinación no contesta en {{ cfg.auto_apply_after }}, se aplica con aviso, queda en la bitácora y
coordinación lo puede cambiar. Esa regla salió de la simulación: con una coordinación lenta, lo urgente esperaba demasiado.

### Escena D.4 · Paso 3: contingencia en el oriente
**Se ve:** grabación: Coordinación `/contingencia` (propuesta por institución) → «Aprobar todo» → `/tablero`; al final Dirección `/demo` → «Volver a normal».

**Dice:**
Paso tres. Hace un momento simulamos mala calidad del aire en el oriente de la ciudad, y el worker la detectó solo.
Enlaza propone cambios por institución: adelantar visitas de quienes tienen enfermedad del pulmón o del corazón y
reacomodar al personal. Nada cambia sin aprobación: coordinación revisa y aprueba todo, y el tablero ya muestra los
cambios. La contingencia se ve estación por estación, no promediada. Esto responde al incidente crítico del Problema
Prototípico: aire contaminado y calles bloqueadas, y el sistema reacciona sin que nadie pierda el control.

### Escena D.5 · Paso 4: nota de emergencia
**Se ve:** grabación: `fam-0001` en `/voz` → «Escribir el mensaje» → «Mi mamá no puede respirar y tiene los labios morados.» → pantalla roja.

**Dice:**
Paso cuatro. Una familia avisa lo que pasa: «Mi mamá no puede respirar y tiene los labios morados». Pantalla roja:
«Llama al nueve once ahora». Sale antes que el modelo de lenguaje, porque la activó una regla. Si solo el clasificador
hubiera sospechado, sería un aviso ámbar y coordinación llamaría a la familia. El médico recibe la transcripción y un
reporte que escribe un modelo de lenguaje local, {{ mod.llm_nombre }}. El sistema nunca diagnostica.

### Escena D.6 · Simulación y negocio
**Se ve:** grabación: `/simulacion` (modo presentación) → `/negocio`.

**Dice:**
Detrás de esto hay una simulación que cambió el producto: priorizar por riesgo baja la espera de lo urgente de
{{ sim.normal.human_dispatcher.high_wait_p90_min }} a {{ sim.normal.risk_priority.high_wait_p90_min }} minutos. Y un modelo de negocio honesto:
el plan base no alcanza, y el escenario recomendado crece por regiones. Una sola aplicación, seis materias, y datos que
dicen su fuente. Eso es Enlaza.
