# Práctica Profesional {#cap-m-pp}

<p class="responsable">Responsable: {{ equipo.materias.practica_profesional }}</p>

## En una frase

!!! frase "Lo que aporta esta materia"
    **Enlaza se construyó como lo haría un profesional responsable: con consentimiento informado, privacidad desde el
    diseño, cumplimiento de la ley de datos y de la ley del trabajo, IA supervisada por personas, trazabilidad,
    licencias respetadas y honestidad sobre lo que funciona, lo que no y quién hizo qué.**

## Qué evalúa el profesor

Normalmente: la **identificación de dilemas éticos**, el **marco legal** aplicable, cómo el producto **protege a las
personas** (datos, consentimiento), la **responsabilidad profesional** (quién responde), la **honestidad** en resultados y
autoría, y el **impacto social**. (Confirmen con el programa del profesor.)

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
fueron del equipo. La Parte IV («Cómo se construyó») lo explica completo y propone cómo contestarlo.

### Datos sintéticos como decisión ética

**Qué es.** Evitar tratar datos reales cuando no es necesario. **En Enlaza:** {{ seed.persons }} personas sintéticas
calibradas con fuentes oficiales; toda pantalla dice «Prototipo académico · datos sintéticos» para que nadie las confunda
con personas reales.

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
    Respuesta honesta en la Parte IV. En corto: el equipo definió el proyecto, las reglas, las decisiones y revisó cada cambio;
    gran parte del código lo escribió un asistente de programación (Claude Code) siguiendo esas reglas, con pruebas y un PR por
    cambio. Podemos explicar y defender cada parte, que es lo que muestra este libro.

!!! pregunta "10. ¿Qué impacto social tendría Enlaza en una institución real?"
    Potencialmente menos visitas perdidas y respuesta más rápida a lo urgente, familias informadas y personal con jornadas
    legales. Riesgos: dependencia de la tecnología, falsas alarmas y brecha digital de familias sin celular. Antes de usarlo con
    personas reales haría falta un piloto con consentimiento y evaluación.
