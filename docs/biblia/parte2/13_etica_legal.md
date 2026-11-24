# Ética y marco legal {#cap-etica}

## En una frase

!!! frase "En una frase"
    **Enlaza trata datos de salud de personas mayores, así que se diseñó desde la ley y la ética: consentimiento expreso
    por tipo de uso, derechos ARCO con plazos de ley, mínimos datos necesarios, bitácora, descanso y jornada laboral
    legal, y una inteligencia artificial que avisa pero no diagnostica, con una persona responsable en cada decisión
    delicada.**

## Explicado sin tecnicismos

Piensa en lo que esperarías si tu mamá fuera paciente:

- que nadie vea su información de salud sin que ella (o tú, si ella no puede) lo haya autorizado **por escrito**;
- poder pedir **qué datos tienen**, corregirlos o pedir que los borren, y que te respondan en un plazo;
- que la institución de al lado no pueda ver nada;
- que si algo sale mal, se sepa **quién** hizo qué;
- que una máquina **no le diga** «no es nada» cuando sí era algo;
- y que la enfermera que la cuida no trabaje jornadas ilegales.

Eso es lo que este capítulo explica: qué dice la ley y cómo Enlaza lo cumple.

## Por qué lo hicimos así

| Decidimos | En lugar de | Por qué |
|---|---|---|
| **Tres consentimientos separados** (salud, domicilio, voz) | Un solo «acepto todo» | La ley pide consentimiento expreso para datos sensibles; separar permite aceptar la visita pero no el asistente de voz. |
| **Consentimiento revisado en la API** | Solo en la pantalla | Esconder un botón no protege; la API bloquea la función (regla 5). |
| **El consentimiento también limita las decisiones automáticas** | Usar los datos de salud para priorizar a todos | Sin permiso de usar sus datos de salud, tampoco se usan en el despachador ni en la contingencia (decisión del equipo, 22 nov 2026). |
| **Una persona aprueba lo delicado** | Automatizar todo | IA responsable: responsabilidad trazable. Única excepción acotada: lo urgente sin respuesta (con aviso, bitácora y posibilidad de cambiarlo). |
| **Nunca decir «no es una emergencia»** | Tranquilizar a la familia | Una falsa calma puede costar una vida; una falsa alarma, unos minutos de una coordinadora. |
| **Cumplir la LFT en la asignación** | Optimizar sin límites | Un algoritmo que asigna turnos ilegales traslada el problema al personal. |
| **Datos sintéticos** | Datos reales | Un proyecto escolar no debe tratar datos sensibles reales. |

## Cómo funciona por dentro

### 1. Ley Federal de Protección de Datos Personales en Posesión de los Particulares (2025)

[[LFPDPPP]], publicada en el DOF el 20 de marzo de 2025. La autoridad es la Secretaría Anticorrupción y Buen Gobierno
(sustituye al INAI). Lo que aplica a Enlaza:

| La ley pide | Enlaza |
|---|---|
| Aviso de privacidad | `/privacidad` muestra el aviso (`docs/legal/aviso_de_privacidad.md`) a todos los roles |
| Consentimiento **expreso y por escrito** para datos sensibles (salud) | Tres tipos de [[consentimiento]] con firma, fecha y vencimiento; formato en `docs/legal/formato_consentimiento.md` |
| Representación de quien no puede decidir | Firma el representante legal (un familiar registrado de esa persona) y se registra el **asentimiento** de la persona |
| Derechos [[ARCO]] (acceso, rectificación, cancelación, oposición) | Formulario en `/privacidad` con folio y fecha límite |
| Plazo de respuesta (art. 31) | {{ neg.arco_response_days }} días hábiles para responder y {{ neg.arco_effective_days }} para hacerlo efectivo; los días son hábiles (art. 2, fr. VIII); el trámite es gratuito (art. 34) |
| Medidas de seguridad | Seguridad por fila, roles, contraseñas con bcrypt, bitácora (@ref(cap-seguridad)) |
| Minimización | Cada rol ve solo lo necesario; el audio no se guarda |

El plazo ARCO no está escrito en el código: sale de `assumptions.csv`, con su fuente. La fecha límite que muestra la
pantalla cuenta de lunes a viernes y **no descuenta días festivos**; la pantalla lo dice.

### 2. Ley Federal del Trabajo (LFT)

| Artículo | Qué dice | Cómo lo aplica Enlaza |
|---|---|---|
| 60 | Jornada diurna (6–20 h), nocturna (20–6 h) y mixta (si la parte nocturna es menor a {{ code.mixed_night_limit }}) | El tipo de jornada sale de las horas del turno |
| 61 | Máximo {{ code.max_day }} diurna, {{ code.max_night }} nocturna y {{ code.max_mixed }} mixta | Los turnos de día que se pasaban se recortaron; los nocturnos de 12 h se **marcan y se avisan**, no se cambian solos |
| 69 | Al menos un día de descanso por cada seis de trabajo | Cada persona tiene un día fijo de descanso y el despachador lo respeta |

Detalle en @ref(cap-operacion). La simulación midió el costo de cumplir la jornada nocturna (@ref(cap-sirag)).

### 3. Inteligencia artificial responsable

| Principio | Cómo se cumple |
|---|---|
| **Supervisión humana** | Lo de prioridad alta y las contingencias las aprueba una persona; el aviso ámbar lo revisa coordinación |
| **No diagnosticar** | El modelo de lenguaje solo resume; esquema fijo, filtro de frases prohibidas, «No es un diagnóstico» en pantalla |
| **Errar hacia el lado seguro** | Las reglas no manejan negaciones; el clasificador puede subir el nivel, nunca bajar una regla; el botón del 911 siempre visible |
| **Transparencia** | Evaluación con un holdout a ciegas; la meta de falsas alarmas que no se cumple se dice abiertamente |
| **Trazabilidad** | Toda decisión automática o humana queda en la bitácora (`assignment_approved_by_timeout`, `emergency_review_*`…) |
| **Privacidad** | Modelos locales: la voz no sale de la laptop |
| **Sesgo** | Se declara que Whisper no reconoce lenguas indígenas; botón para pedir que alguien llame; procedimiento para medir el error por grupo |

### 4. Los riesgos éticos que hay que poder discutir

1. **Falsas alarmas contra emergencias perdidas.** Elegimos no perder emergencias ({{ voz.holdout.sens }} en el holdout) a
   costa de falsas alarmas ({{ voz.holdout.fa100 }} por 100 notas). Mitigación: dos niveles de aviso y revisión humana
   (@ref(cap-voz)).
2. **Sesgo de reconocimiento de voz** por edad, acento y lengua. Mitigación parcial: escribir el mensaje y pedir que llamen.
3. **Automatizar asignaciones: ¿quién responde si falla?** Por eso existe la aprobación humana en lo de prioridad alta. El
   límite de tiempo es la excepción: solo lo urgente, tras {{ cfg.auto_apply_after }}, con aviso, bitácora y posibilidad de
   cambiarlo; la decisión salió de la simulación y queda trazable.
4. **Vigilancia del personal.** Las horas de llegada sirven para coordinar, no para sancionar; la carga se usa para repartir
   mejor el trabajo.
5. **Datos sintéticos que parecen reales.** Toda pantalla dice «Prototipo académico · datos sintéticos» para que nadie los
   confunda con personas reales.

### 5. Lo que muestra la pantalla de privacidad

![Consentimientos de una persona en `/privacidad` (coordinación): los tres tipos, quién firmó, el asentimiento y la vigencia, con «Revocar» y «Registrar o renovar».](capturas/tarjeta_consentimientos_01.png){.media}

![Derechos ARCO: el formulario crea una solicitud con folio y muestra la fecha límite de ley.](capturas/tarjeta_arco_01.png){.media}

![La bitácora para Dirección: resumen de los intentos bloqueados de los últimos días.](capturas/tarjeta_bitacora_01.png){.media}

!!! cuidado "Un detalle para la defensa"
    Casi todos los «intentos bloqueados» de la bitácora los dejaron las **pruebas automáticas**, que intentan a propósito
    accesos indebidos. Esos registros se quedan porque la bitácora no se borra. La pantalla lo avisa. Para una bitácora
    limpia, la Parte V explica cómo recrear la base antes de la defensa.

## Dónde está en el código

| Qué | Dónde |
|---|---|
| Aviso de privacidad y formato de consentimiento | `docs/legal/` |
| Consentimientos y ARCO | `backend/app/services/privacy.py`, `backend/app/routers/privacy.py`, migración `0008_privacy` |
| Pantalla | `frontend/src/pages/PrivacyPage.tsx` |
| Reglas laborales | `backend/app/services/labor.py` |
| Plazos ARCO con su fuente | `data/business/assumptions.csv` (`arco_response_days`, `arco_effective_days`) |
| Ética en la especificación | `docs/spec/11_etica_y_privacidad.md` |
| Pruebas | `backend/tests/test_consents.py`, `test_privacy.py`, `test_labor.py` |

## Números clave

{{ tabla neg.arco_response_days neg.arco_effective_days seed.consents code.max_day code.max_mixed code.max_night cfg.workdays seed.night_12h voz.holdout.sens voz.holdout.fa100 cfg.auto_apply_after }}

## Limitaciones honestas

- **Plantillas académicas, no asesoría legal**: el aviso y el formato no los revisó un abogado.
- **No se cubre la NOM-004-SSA3-2012** (expediente clínico): Enlaza no es un expediente; se usa solo como referencia de
  confidencialidad.
- **El plazo ARCO no descuenta festivos.**
- **El asentimiento se registra, pero el flujo de una persona que no está de acuerdo** depende de la institución.
- **Los nocturnos de 12 h siguen excediendo la ley** en la plantilla de la semilla: Enlaza lo señala, la institución decide.
- **No hay un comité de ética** ni evaluación de impacto formal: es un prototipo escolar.

## Preguntas que te pueden hacer

!!! pregunta "¿Qué ley de datos aplica y qué exige?"
    La Ley Federal de Protección de Datos Personales en Posesión de los Particulares, publicada el 20 de marzo de 2025. Los
    datos de salud son sensibles: requieren consentimiento expreso y por escrito, aviso de privacidad, derechos ARCO y medidas
    de seguridad. Enlaza tiene los tres consentimientos, el aviso en pantalla, el formulario ARCO con los plazos del art. 31 y
    las medidas de seguridad del capítulo 5.

!!! pregunta "¿Qué pasa si la persona mayor no puede decidir?"
    Firma su representante legal, que debe ser un familiar registrado de esa misma persona, y se registra el asentimiento de
    la persona (si estuvo de acuerdo, no, o no pudo expresarlo).

!!! pregunta "¿Cuánto tardan en responder una solicitud ARCO?"
    La ley da {{ neg.arco_response_days }} días hábiles para responder y {{ neg.arco_effective_days }} para hacerlo efectivo, ampliables
    una vez. La pantalla da un folio y la fecha límite, contando de lunes a viernes, y avisa que no descuenta festivos.

!!! pregunta "¿No es peligroso que una IA decida sobre la salud de alguien?"
    Por eso la IA de Enlaza no decide sobre la salud: avisa de posibles emergencias (y prefiere avisar de más), resume para
    el médico sin diagnosticar, y las decisiones delicadas las aprueba una persona. Todo queda en la bitácora.

!!! pregunta "¿Por qué aplicar la Ley Federal del Trabajo si es un prototipo?"
    Porque un sistema que asigna turnos puede normalizar jornadas ilegales. Lo aplicamos con las mismas reglas en la operación
    y en la simulación, y medimos cuánto cuesta cumplirla: así la institución decide con información.

!!! pregunta "¿Quién es responsable si el sistema se equivoca?"
    La institución, a través de la persona que aprobó, y Enlaza como proveedor del sistema. Por eso cada asignación de
    prioridad alta lleva el nombre de quien la aprobó, la excepción del límite de tiempo lleva su propia marca
    (`approval='timeout'`) y todo queda en una bitácora que no se puede borrar desde la aplicación.
