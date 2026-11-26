# Práctica Profesional {#cap-m-pp}

<p class="responsable">Responsable: {{ equipo.materias.practica_profesional }}</p>

## En una frase

!!! frase "Lo que aporta esta materia"
    **Enlaza se construyó como lo haría un profesional responsable: con consentimiento informado, privacidad desde el
    diseño, cumplimiento de la ley de datos y de la ley del trabajo, IA supervisada por personas, trazabilidad,
    licencias respetadas y honestidad sobre lo que funciona, lo que no y quién hizo qué.**

## Qué evalúa el profesor

| Pide | Documento y sección | Dónde se responde |
|---|---|---|
| Entregable: «Diagnóstico de Campo, Protocolo de Ética y Práctica Profesional» (en clínicas geriátricas) | PP, «Evidencia integradora», p. 2; «Incidente crítico», p. 6 | «Diagnóstico de campo» y «Protocolo de ética» (abajo) |
| Protocolo de consentimiento informado y manejo ético de datos de poblaciones vulnerables | PP, «Desarrollo del Problema Prototípico», p. 9 | «Protocolo de ética» (abajo); @ref(cap-etica) |
| Consentimiento de personas con demencia firmado por conveniencia; presión para omitirlo; detener y rediseñar el protocolo de inserción y gobernanza de datos | PP, «Incidente crítico de la UCA: Introducción a la Práctica Profesional», p. 16 | «Respuesta al incidente crítico» (abajo) |
| Resistencia del personal de salud a reportes «fríos»; ecosistema comprensible para distintos usuarios | PP, p. 16; p. 9 | «Respuesta al incidente crítico» |
| Enfoque humanista: dignidad, autonomía, no infantilizar, ética de los datos, prevenir sesgos | PP, «Planteamiento de la Problemática», p. 3 | conceptos (abajo); @ref(cap-m-pp-doc) |
| Consentimiento informado, privacidad, responsabilidades, supervisión humana; **validar el problema con personas reales del sector sin usar datos de pacientes** (evidencia de campo) | Plan SIE, secciones 2 y 3 | conceptos (abajo); «Diagnóstico de campo» |
| Habilidades blandas (pensamiento crítico, resolución de problemas, negociación, empatía, trabajo en equipo, manejo de conflictos, entre otras) | PP, «Identificación de las Habilidades Blandas», p. 5 | se demuestran en la defensa; **confirmar con el profesor** cómo se evalúan |
| Bibliografía recomendada: AMIPCI (2021), Hernández-Sampieri y Mendoza (2018), OMS (2021) | PP, p. 16 | **confirmar con el profesor** si se espera citarla en el protocolo |
| Rúbrica propia de la materia | **no lo dicen los documentos: confirmar con el profesor** | — |

## Los conceptos, desde cero

### Ética profesional y código de ética

**Qué es.** Las obligaciones de quien ejerce una profesión hacia las personas afectadas por su trabajo: no dañar, ser honesto,
proteger la confianza, respetar la ley y reconocer los límites de su competencia. Los códigos de ética (por ejemplo, el de la
ACM para computación) lo ponen por escrito.

**En Enlaza.** Decisiones concretas, no declaraciones: datos sintéticos, consentimiento por tipo, nunca decir «no es una
emergencia», aprobación humana en lo delicado, resultados honestos (incluido lo que no se cumple).

### Datos personales y datos personales sensibles

**Qué es.** Un dato personal identifica o puede identificar a una persona. Los **sensibles** (salud, origen étnico,
creencias…) pueden causar discriminación o daño grave si se exponen; la ley los protege más.

**En Enlaza.** Enfermedades, dependencia, medicamentos y grabaciones de voz son **sensibles** ([[LFPDPPP]] 2025).

### Consentimiento informado y asentimiento

**Qué es.** Autorización libre, previa, **informada** (la persona sabe para qué) y, para datos sensibles, **expresa y por
escrito**. El **asentimiento** es la conformidad de quien no puede consentir legalmente, aunque firme su representante.

**Ejemplo.** Antes de una cirugía te explican riesgos y firmas; si no puedes, firma un familiar y el médico registra si tú
estabas de acuerdo.

**En Enlaza.** Tres [[consentimiento|consentimientos]] separados (datos de salud, atención a domicilio, asistente de voz), con
vencimiento; representante legal registrado de esa persona; asentimiento registrado. Sin el vigente, la función se bloquea
**en la API** (regla 5).

### Aviso de privacidad y derechos ARCO

**Qué es.** El aviso dice qué datos, para qué, con quién se comparten y cómo ejercer derechos. [[ARCO]]: acceso,
rectificación, cancelación y oposición.

**En Enlaza.** Aviso en `/privacidad`; formulario ARCO con folio y fecha límite ({{ neg.arco_response_days }} días hábiles para
responder, {{ neg.arco_effective_days }} para hacerlo efectivo, art. 31).

### Privacidad desde el diseño y minimización

**Qué es.** Proteger la privacidad desde el principio, no al final; y tratar **solo** los datos necesarios.

**En Enlaza.** Seguridad por fila que falla cerrada, cada rol ve lo mínimo, el audio no se guarda, Panorama solo con datos
agregados (grupos de al menos {{ code.small_cell }}), IA local (la voz no sale de la laptop), datos sintéticos.

### Trazabilidad y rendición de cuentas

**Qué es.** Poder reconstruir quién decidió qué, cuándo y con qué información. Sin trazabilidad, nadie responde.

**En Enlaza.** Bitácora de solo agregar; cada asignación dice si fue automática, aprobada por quién o «por tiempo»;
contingencias, consentimientos y revisiones de voz quedan registrados.

### IA responsable

**Qué es.** Usar IA con supervisión humana, transparencia, equidad, privacidad, seguridad y rendición de cuentas.

**En Enlaza.** La IA avisa (y prefiere avisar de más), resume sin diagnosticar y no decide sobre la salud; lo delicado lo
aprueba una persona; la evaluación es a ciegas y se publican también las metas no cumplidas (@ref(cap-etica)).

### Derechos laborales

**Qué es.** La Ley Federal del Trabajo protege la jornada y el descanso. Un sistema que asigna trabajo puede normalizar
abusos si no la respeta.

**En Enlaza.** Descanso semanal (art. 69), tipo de jornada por horas (art. 60), máximos (art. 61); los nocturnos de 12 h que
exceden la ley se marcan y se avisan, no se cambian solos (decide la institución). La simulación midió el costo de cumplir.

### Vigilancia del personal

**Qué es.** Los datos de ubicación y horario pueden usarse para controlar o sancionar de más.

**En Enlaza.** Las horas de llegada sirven para **coordinar**, no para sancionar; la carga se usa para repartir mejor el
trabajo.

### Licencias y propiedad intelectual

**Qué es.** Todo código, tipografía, mapa o dato ajeno tiene una licencia que dice cómo usarlo.

**En Enlaza.** Código bajo **MIT**; datos sintéticos **CC BY 4.0**; tipografías **SIL OFL**; íconos **ISC**; mapas
**OpenStreetMap (ODbL)**; límites de alcaldías del INEGI vía Datos Abiertos CDMX (**CC BY 4.0**); todo en
`docs/creditos.md`. No se usaron audios ni imágenes sin licencia; «Oracle» se dejó de usar por ser marca registrada.

### Honestidad académica y uso de herramientas de IA

**Qué es.** Decir con claridad qué hizo cada quien y qué herramientas se usaron, sin exagerar ni esconder.

**En Enlaza.** Gran parte del código se escribió con un asistente de programación (Claude Code), dirigido y revisado por el
equipo, con reglas escritas (`CLAUDE.md`), un PR por cambio, pruebas y revisiones en el navegador. Las decisiones de producto
fueron del equipo. @ref(cap-construccion) lo explica completo y propone cómo contestarlo.

### Datos sintéticos como decisión ética

**Qué es.** Evitar tratar datos reales cuando no es necesario. **En Enlaza:** {{ seed.persons }} personas sintéticas
calibradas con fuentes oficiales; toda pantalla dice «Prototipo académico · datos sintéticos» para que nadie las confunda
con personas reales.

## Diagnóstico de campo

!!! nota "Estado: se hace esta semana"
    El PP pide un diagnóstico de campo y el Plan SIE propone «validar el problema con personas reales del sector (sin usar datos
    de pacientes)». El equipo lo hace la semana del 25 de noviembre de 2026. El material está en `docs/diagnostico/`:
    `guia_entrevista.md` (20 minutos, 12 preguntas), `consentimiento_verbal.md` (sin nombres ni datos de salud; se cita por rol y
    alcaldía) y `plantilla_resumen.md` (una por entrevista, en `docs/diagnostico/entrevistas/`).

Diseño:

| Elemento | Propuesta |
|---|---|
| Objetivo | validar que la coordinación de visitas es un problema real y qué información necesita cada actor |
| Método | entrevistas semiestructuradas (ruta cualitativa, Hernández-Sampieri y Mendoza, 2018) |
| Participantes | coordinación de una residencia o centro de día, personal de cuidado o enfermería, un geriatra, familiares cuidadores |
| Consentimiento | verbal, leído al inicio (`docs/diagnostico/consentimiento_verbal.md`); sin nombres ni datos de salud; cita por rol y alcaldía; audio solo si lo autorizan y se borra tras el resumen |
| Guía | `docs/diagnostico/guia_entrevista.md`: cómo coordinan hoy (4 preguntas), qué falla (5) y qué pensarían de algo como Enlaza (3) |
| Uso | ajustar la propuesta de valor, el precio y las pantallas; citar resultados en el portafolio |

### Hallazgos del diagnóstico de campo

!!! nota "Para llenar después de las entrevistas"
    Copiar aquí lo más importante de `docs/diagnostico/entrevistas/E01.md`, `E02.md`… Citar solo por rol y alcaldía.

| Entrevista | Rol y alcaldía | Fecha |
|---|---|---|
| E01 | ____ | ____ |
| E02 | ____ | ____ |
| E03 | ____ | ____ |

**Lo que supusimos y lo que encontramos**

| Lo que supuso Enlaza | Se confirmó / se contradijo / no se habló | Evidencia (frase textual, rol y alcaldía) |
|---|---|---|
| Hoy se coordina con llamadas, WhatsApp y hojas de cálculo | ____ | ____ |
| Se pierden o duplican solicitudes | ____ | ____ |
| No se sabe quién está libre ni cuánto tarda en llegar | ____ | ____ |
| Lo urgente compite con lo rutinario | ____ | ____ |
| La contingencia ambiental cambia la operación | ____ | ____ |
| Es aceptable que el sistema asigne lo rutinario y una persona apruebe lo urgente | ____ | ____ |
| Es aceptable el límite de tiempo en lo urgente | ____ | ____ |
| Los precios supuestos son razonables para una institución | ____ | ____ |
| Las familias usarían un asistente de voz | ____ | ____ |

**Qué cambiaríamos en Enlaza por lo que encontramos:** ____

## Protocolo de ética (consentimiento y gobernanza de datos)

El protocolo que aplica Enlaza, paso a paso (las partes en cursiva son de la institución, no del software):

1. *Valorar si la persona puede decidir.*
2. Explicar en lenguaje claro qué datos se usan y para qué; un consentimiento **por tipo** (datos de salud, atención a
   domicilio, asistente de voz), revocable (`docs/legal/formato_consentimiento.md`).
3. Firma la persona; si no puede, su **representante legal**, que debe ser un familiar registrado de **esa** persona, y se
   registra el **asentimiento** (sí, no, no pudo expresarlo).
4. Se registra en `/privacidad` con fecha de firma y vencimiento; queda en la bitácora.
5. **Sin consentimiento vigente, el sistema no procesa**: no hay visita, voz ni datos de salud, y las decisiones automáticas no usan
   sus datos de salud.
6. Revocar surte efecto al instante.
7. Derechos ARCO con folio y plazo de ley; bitácora que no se puede borrar.
8. *Si hay presión para saltarse el consentimiento, se detiene la intervención y se escala* (ver abajo).

!!! nota "El asentimiento cuenta (corregido el 25 nov 2026)"
    El formato de consentimiento dice que si la persona **no estuvo de acuerdo**, no se usa el asistente de voz. Al escribir este
    libro se encontró que el sistema solo **registraba** el asentimiento. El equipo decidió corregirlo (PR #21): si la persona no
    asintió (`patient_assent = 'no'`), **la voz se bloquea igual que sin consentimiento**, aunque el representante haya firmado,
    con el mensaje «La persona no estuvo de acuerdo con usar el asistente de voz… No se grabó nada.», y queda en la bitácora
    (`voice_blocked_no_assent`). Hay una prueba automática.

## Respuesta al incidente crítico de Práctica Profesional

**El incidente** (PP, p. 16, «El consentimiento silenciado»): durante el diagnóstico de campo, los estudiantes descubren que se
procesan historiales y voces de personas con demencia avanzada con permisos que los familiares firman por conveniencia, sin la
presencia ni la comprensión de los pacientes. La dirección de la clínica presiona para omitir el protocolo porque atrasa los
indicadores de los financiadores. Además, el personal de salud desconfía de reportes que «reducen a los pacientes a cifras».

- **Postura del equipo:** detener el procesamiento de esos datos y rediseñar el protocolo de inserción, aunque cueste tiempo y la
  relación con la institución. Un consentimiento firmado sin informar a la persona no es válido éticamente, aunque exista el
  papel.
- **Lo que hace el sistema:** no deja procesar sin consentimiento (bloqueo en la API) y obliga a registrar **quién** firmó y el
  **asentimiento**; todo queda auditado. Lo que no puede hacer es saber si la firma fue informada: eso es responsabilidad
  profesional de las personas (y por eso el asentimiento «no» ahora bloquea la voz).
- **Ante la desconfianza del personal de salud:** Enlaza no diagnostica ni sustituye el criterio clínico; el médico ve la
  transcripción y frases textuales, no solo un número; el modo sencillo y los textos cortos buscan que cada usuario lo entienda.

## Por qué lo hicimos así

- **Tres consentimientos** y no uno: la persona puede aceptar visitas y negarse al asistente de voz.
- **Revisar en la API** y no solo en la pantalla: esconder un botón no protege.
- **Dos niveles de aviso** y revisión humana: equilibrio entre no perder emergencias y no volver inútil la alarma.
- **Marcar y avisar** las jornadas ilegales en lugar de cambiarlas: la decisión es de la institución, pero informada.
- **Publicar lo que no se cumple** (falsas alarmas, VPN base negativo): la credibilidad depende de eso.

## Dónde se ve en el sistema

| Concepto | Dónde |
|---|---|
| Aviso de privacidad, ARCO, bitácora | `/privacidad`; `docs/legal/` |
| Consentimientos | `/privacidad` (coordinación); ficha del paciente |
| Bloqueo por consentimiento | `/voz` («Falta autorización…»), ficha («Falta consentimiento») |
| Jornada legal | `/personal` («Excede la jornada legal (art. 61)»), alertas del tablero |
| IA que no diagnostica | `/reportes-voz` («No es un diagnóstico») |
| Licencias | `LICENSE`, `docs/creditos.md` |
| Reglas del proyecto | `CLAUDE.md` |

## Números clave

{{ tabla seed.consents neg.arco_response_days neg.arco_effective_days code.small_cell code.max_night seed.night_12h voz.holdout.sens voz.holdout.fa100 cfg.auto_apply_after cfg.escalate_after }}

## Limitaciones honestas

- El **diagnóstico de campo** se hace esta semana; los hallazgos se agregan en la sección de arriba.
- El asentimiento «no» bloquea la **voz**; para las visitas y los datos de salud, qué hacer cuando la persona no asiente lo decide la
  institución.
- Plantillas legales **sin revisión de un abogado**.
- **Sin comité de ética** ni evaluación de impacto formal.
- El **flujo de una persona que no asiente** depende de la institución.
- Las falsas alarmas del asistente de voz **pueden generar ansiedad** en las familias; se mitiga, no se elimina.

## Qué decir en 2 minutos

!!! frase "Guion de 2 minutos · Práctica Profesional"
    «Enlaza trata datos de salud de personas mayores, que son **datos sensibles** según la Ley Federal de Protección de Datos
    Personales de 2025. Por eso usamos **datos sintéticos**, pedimos **tres consentimientos** separados, con representante
    legal y asentimiento cuando la persona no puede decidir, y la API **bloquea** la función si falta: no se graba voz, no se
    hace la visita, no se muestran datos de salud. Las personas ejercen sus derechos **ARCO** en la app, con folio y el plazo de
    ley.

    En la IA, la regla es que **avisa pero no decide**: prefiere una falsa alarma a una emergencia perdida, nunca dice «no es una
    emergencia», no diagnostica, y lo delicado lo aprueba una persona; todo queda en una **bitácora** que no se puede borrar.

    Aplicamos también la **Ley Federal del Trabajo**: descanso semanal y jornada máxima en la asignación.

    Y somos honestos: publicamos lo que no se cumple, como las falsas alarmas, y decimos cómo se construyó, incluido el uso de
    un asistente de programación con IA bajo nuestras reglas y revisión.»

## 10 preguntas difíciles

!!! pregunta "1. ¿Qué ley de protección de datos aplica y qué exige para datos de salud?"
    La LFPDPPP publicada el 20 de marzo de 2025. Los datos de salud son sensibles: requieren consentimiento expreso y por
    escrito, aviso de privacidad, derechos ARCO y medidas de seguridad. La autoridad es la Secretaría Anticorrupción y Buen
    Gobierno.

!!! pregunta "2. ¿Cómo obtienen consentimiento de alguien con demencia?"
    Firma su representante legal (un familiar registrado de esa persona) y se registra el asentimiento de la persona: si estuvo
    de acuerdo, si no, o si no pudo expresarlo.

!!! pregunta "3. ¿Qué pasa si una familia retira el consentimiento?"
    Surte efecto al instante: se cancelan las visitas pendientes (una en curso la decide coordinación), se dejan de mostrar los
    datos de salud o el asistente deja de aceptar notas, según el tipo. Todo queda en la bitácora.

!!! pregunta "4. Si la IA se equivoca y no detecta una emergencia, ¿quién es responsable?"
    El sistema no sustituye al 911 ni al juicio humano: el botón del 911 está siempre visible y la IA prefiere avisar de más.
    La responsabilidad es de la institución que opera y de Enlaza como proveedor; por eso todo es trazable. Lo decimos como
    riesgo ético abierto, no como resuelto.

!!! pregunta "5. ¿No es poco ético el límite de tiempo, que asigna sin una persona?"
    Es una excepción acotada: solo lo urgente, tras {{ cfg.auto_apply_after }} sin respuesta, con aviso a coordinación, marca en la
    bitácora y posibilidad de cambiarlo. Salió de la simulación: esperar a una persona lenta empeoraba la atención urgente. Es
    un equilibrio entre supervisión humana y daño por demora.

!!! pregunta "6. ¿Por qué no usaron datos reales para que fuera más útil?"
    Porque tratar datos sensibles reales en un proyecto escolar no tiene base legal ni ética suficiente. Los datos sintéticos
    calibrados permiten demostrar y publicar sin riesgo para nadie.

!!! pregunta "7. ¿El sistema vigila al personal?"
    Registra llegada y término para coordinar y como evidencia del servicio, no para sancionar. La carga se usa para repartir
    mejor el trabajo, y la asignación respeta el descanso y la jornada de ley.

!!! pregunta "8. ¿Respetaron las licencias de lo que usaron?"
    Sí: tipografías OFL, íconos ISC, mapas de OpenStreetMap con atribución, límites del INEGI con atribución CC BY 4.0, y nada de
    audios o imágenes sin licencia. Todo está en `docs/creditos.md`. Dejamos de usar «Oracle» por ser marca registrada.

!!! pregunta "9. ¿Ustedes programaron esto?"
    Respuesta honesta en @ref(cap-construccion). En corto: el equipo definió el proyecto, las reglas, las decisiones y revisó cada cambio;
    gran parte del código lo escribió un asistente de programación (Claude Code) siguiendo esas reglas, con pruebas y un PR por
    cambio. Podemos explicar y defender cada parte, que es lo que muestra este libro.

!!! pregunta "10. En el incidente, la clínica presiona para omitir el consentimiento de pacientes con demencia. ¿Qué harían?"
    Detener el procesamiento de esos datos y rediseñar el protocolo, aunque retrase los indicadores. Un permiso firmado por
    conveniencia, sin informar a la persona, no es un consentimiento válido. En Enlaza el sistema no procesa sin consentimiento
    vigente, registra quién firmó y el asentimiento de la persona, y todo queda en la bitácora. Lo que el software no puede
    garantizar es que la firma haya sido informada: eso es responsabilidad profesional nuestra y de la institución.
