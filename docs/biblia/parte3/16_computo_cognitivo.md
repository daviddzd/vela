# Cómputo Cognitivo {#cap-m-cc}

<p class="responsable">Responsable: {{ equipo.materias.computo_cognitivo }}</p>

## En una frase

!!! frase "Lo que aporta esta materia"
    **Enlaza Voz (antes ORACLE-Voz) combina tres técnicas de inteligencia artificial: reconocimiento de voz (Whisper),
    clasificación de texto (reglas + una red neuronal de Keras) y un modelo de lenguaje local (Ollama), evaluadas con un
    conjunto a ciegas y con una política de seguridad que prefiere una falsa alarma a una emergencia perdida.**

## Qué evalúa el profesor

Normalmente: el **problema cognitivo** (qué «entiende» el sistema), el **flujo** de procesamiento, los **datos** de
entrenamiento y cómo se dividieron, el **modelo** y por qué ese, la **evaluación** con métricas adecuadas (no solo
exactitud), el manejo de **errores**, **sesgos** y **ética** de la IA, y una **demostración** en vivo. (Confirmen con el
programa del profesor.)

## Los conceptos, desde cero

### Inteligencia artificial, aprendizaje automático y reglas

**Qué es.** IA es cualquier sistema que hace algo que parecería requerir inteligencia. Hay dos grandes formas: **reglas**
escritas por personas («si dice X, entonces Y») y **aprendizaje automático**, donde el programa aprende patrones de
ejemplos.

**Ejemplo.** Un filtro de correo basura puede tener reglas («si dice "ganaste un premio", es basura») o aprender de miles
de correos marcados.

**En Enlaza.** Las dos: **reglas** para lo que no puede fallar (`config/emergency_rules.yaml`, {{ cfg.emergency_categories }}
categorías, {{ cfg.emergency_patterns }} patrones) y un **clasificador** aprendido para lo que las reglas no prevén. El
clasificador puede **subir** el nivel, nunca bajar una regla.

### Procesamiento de lenguaje natural (NLP)

**Qué es.** Hacer que una computadora trabaje con lenguaje humano: entender, clasificar, resumir, traducir.

**En Enlaza.** Clasificar un mensaje (rutina, urgente, emergencia) y resumirlo para el médico.

### Reconocimiento automático del habla (ASR)

**Qué es.** Convertir voz en texto. Los modelos modernos son redes neuronales entrenadas con miles de horas de audio.

**En Enlaza.** [[ASR]] con **faster-whisper**, modelo `small`, en CPU. **Cuantización** `int8`: guardar los números del
modelo con menos precisión (enteros de 8 bits) para que pese menos y corra más rápido, con poca pérdida de exactitud.
Una nota de ~10 s tarda {{ voz.t_transcribe_10 }}.

### Normalización de texto

**Qué es.** Limpiar el texto para comparar sin que importen detalles: minúsculas, sin acentos, sin signos. **En Enlaza:**
«No puede RESPIRAR» y «no puede respirar» son lo mismo para las reglas.

### Clasificación y clases

**Qué es.** Asignar cada ejemplo a una categoría. Aquí tres clases: rutina, urgente, emergencia.

### Red neuronal, capas y *embedding*

**Qué es.** Una red neuronal es una función con muchos parámetros organizados en **capas**; al entrenar, se ajustan los
parámetros para equivocarse menos. Un ***embedding*** convierte cada palabra (o pedazo de palabra) en una lista de números
donde palabras parecidas quedan cerca.

**Ejemplo.** Como ubicar ciudades en un mapa: Puebla queda cerca de Tlaxcala y lejos de Tijuana. Un *embedding* ubica
palabras en un «mapa de significados».

**En Enlaza.** Dos vistas del texto: **palabras** (y pares de palabras) y **n-gramas de caracteres** (pedazos de 3 y 4
letras, que resisten errores de dedo); cada una pasa por un *embedding* y un promedio; se juntan y pasan por dos capas
densas hasta tres salidas con probabilidades (*softmax*).

### N-gramas

**Qué es.** Secuencias de *n* elementos seguidos. Bigramas de palabras: «no puede», «puede respirar». Trigramas de
caracteres: «res», «esp», «spi». **Por qué sirven:** «no puede respirar» como par dice más que las palabras sueltas, y los
pedazos de letras reconocen «respirrar» aunque esté mal escrito.

### Entrenamiento, validación, prueba y holdout

**Qué es.** Los datos se dividen: **entrenamiento** (el modelo aprende), **validación** (se eligen detalles, como cuándo
detenerse), **prueba** (se mide). Un **holdout a ciegas** es un conjunto que nadie usó para nada antes de la evaluación
final.

**Ejemplo.** Estudiar con la guía (entrenamiento), hacer un examen de práctica (validación) y presentar el examen final
con preguntas nuevas (holdout).

**En Enlaza.** Frases internas ({{ voz.split_train }} / {{ voz.split_validation }} / {{ voz.split_test }}), externas
({{ ref.external_phrases }}) y **holdout** ({{ ref.holdout_phrases }}, escritas por un agente que no vio las reglas ni los otros
conjuntos, guardadas en Git antes de evaluar). Falta un cuarto conjunto: las frases del equipo.

### Fuga de datos y sobreajuste

**Qué es.** **Sobreajuste:** el modelo memoriza los ejemplos en lugar de aprender el patrón; le va muy bien con lo que vio y
mal con lo nuevo. **Fuga de datos:** información de la prueba se «cuela» al entrenamiento o a las reglas.

**En Enlaza.** Por eso la prueba interna da {{ voz.internal_test.sens }} y F1 {{ voz.internal_test.f1 }}, pero el holdout
{{ voz.holdout.sens }} y F1 {{ voz.holdout.f1 }}. Las reglas se escribieron viendo el conjunto externo: ahí detectan
{{ vozr.externo.despues.sens }}, y en el holdout {{ vozr.holdout.despues.sens }}.

### Aumento de datos y pesos de clase

**Qué es.** **Aumento:** crear ejemplos nuevos a partir de los existentes (errores de dedo, muletillas, paráfrasis) para
que el modelo vea más variedad. **Pesos de clase:** hacer que equivocarse en una clase «cueste» más al entrenar.

**En Enlaza.** Ambos. Una emergencia mal clasificada cuesta {{ code.class_weight_emergency }} veces más que una rutina
(supuesto).

### Matriz de confusión

**Qué es.** Tabla que cruza lo real (filas) con lo que dijo el sistema (columnas). La diagonal son aciertos.

**En Enlaza** (holdout): de {{ voz.holdout.emergencies }} emergencias, {{ vozcm.holdout.emergency.emergency }} terminaron en
emergencia y {{ vozcm.holdout.emergency.routine }} en rutina; de las rutinas, {{ vozcm.holdout.routine.emergency }} terminaron en
emergencia (falsas alarmas). Tabla completa en @ref(cap-voz).

### Sensibilidad, precisión, F1 y falsas alarmas

**Qué es.**

- **Sensibilidad** (*recall*): de los casos reales, cuántos detecta. «¿Se me escapó alguno?»
- **Precisión**: de los que marcó, cuántos eran reales. «¿Cuántas alarmas fueron ciertas?»
- **F1**: equilibrio entre las dos. **F1 macro**: el promedio del F1 de cada clase.
- **Exactitud** (*accuracy*): porcentaje de aciertos totales. **Engaña** cuando una clase es rara o cuando un error cuesta
  más que otro.

**Ejemplo.** Un detector de humo muy sensible suena con el pan tostado (baja precisión) pero nunca se le escapa un
incendio (alta sensibilidad). Para un incendio, eso es lo que quieres.

**En Enlaza.** Métrica principal: **sensibilidad de emergencia del sistema completo** ({{ voz.holdout.sens }} en el holdout);
secundarias: falsas alarmas por cada 100 notas ({{ voz.holdout.fa100 }}) y F1 macro ({{ voz.holdout.f1 }}).

### Umbral de decisión

**Qué es.** El clasificador da probabilidades; el umbral decide a partir de cuánto se considera «emergencia». Subirlo
reduce falsas alarmas y también detecciones.

**En Enlaza.** No se subió el umbral de v1, porque bajaría la sensibilidad. El v2 de la rama pendiente eligió un umbral alto
y por eso perdió emergencias ({{ vozv2.v2.sens }}).

### Modelo de lenguaje grande (LLM), *prompt* y salida estructurada

**Qué es.** Un [[LLM]] es una red neuronal enorme entrenada para continuar texto; puede resumir, responder, redactar. El
***prompt*** es la instrucción que recibe. **Salida estructurada:** obligarlo a responder en un formato fijo (JSON con
campos definidos).

**En Enlaza.** Ollama corre el modelo configurado en `OLLAMA_MODEL` en la laptop. Instrucción: resumir, no inferir
enfermedades, no recomendar tratamientos. Esquema JSON fijo validado con Pydantic y filtro de frases prohibidas.

### Alucinación

**Qué es.** Cuando un LLM inventa algo que suena plausible pero no es cierto. **Mitigación en Enlaza:** temperatura baja,
«frases textuales» que citan lo dicho, campo «limitaciones», filtro y, sobre todo, el LLM **no decide nada**: el nivel lo
ponen las reglas y el clasificador.

### Codificador preentrenado (aprendizaje por transferencia)

**Qué es.** Usar un modelo ya entrenado con muchísimo texto como base y entrenar encima solo una parte pequeña.

**En Enlaza.** Fue el v2 (rama pendiente): mejor F1 ({{ vozv2.v2.f1 }} contra {{ vozv2.v1.f1 }}) pero menos sensibilidad; no
cumplió la regla de adopción escrita antes y no se adoptó.

### Sesgo e IA responsable

**Qué es.** Un modelo puede funcionar peor para ciertos grupos (acento, edad, lengua). IA responsable: supervisión humana,
transparencia, privacidad, seguridad y rendición de cuentas.

**En Enlaza.** Whisper no reconoce lenguas indígenas (se declara; botón «pedir que alguien me llame»); procedimiento de
WER por grupo listo y pendiente con voces reales; modelos locales; dos niveles de aviso con revisión humana
(@ref(cap-etica)).

## Por qué lo hicimos así

- **Reglas + clasificador** y no solo uno: las reglas son explicables y seguras; el clasificador ve lo que las reglas no.
- **Red pequeña entrenada desde cero** (v1) y no un modelo enorme: corre en CPU en milisegundos y se puede explicar.
- **Evaluación a ciegas**, porque la prueba interna está contaminada por cómo se construyeron reglas y modelo.
- **Dos niveles de aviso**, porque con una sola pantalla roja casi la mitad serían falsas.
- **Regla de adopción escrita antes de ver el holdout**, para no elegir el modelo según el resultado.

## Dónde se ve en el sistema

| Concepto | Dónde |
|---|---|
| ASR | `/voz` (grabar) → `voice/triage/service.py` (`/transcribe`) |
| Reglas | `config/emergency_rules.yaml`, `backend/app/services/triage_rules.py` |
| Clasificador | `voice/triage/classifier.py`, `augment.py` |
| Dos niveles | pantallas roja y ámbar en `/voz`; alerta en `/tablero` |
| LLM | `backend/app/services/llm_report.py`; `/reportes-voz` |
| Evaluación | `voice/eval/` → `voice/eval/results/` |
| Panel demo | «Frase de ejemplo escrita» en `/demo` |

## Números clave

{{ tabla voz.holdout.n voz.holdout.sens voz.holdout.sens_rules voz.holdout.fa100 voz.holdout.f1 voz.internal_test.sens voz.internal_test.f1 vozb.holdout.emerg_only_classifier vozb.holdout.red_false vozb.holdout.red vozv2.v2.sens vozv2.v2.fa100 voz.t_transcribe_10 voz.t_llm_short }}

## Limitaciones honestas

- **Falsas alarmas altas** en el holdout; la meta de menos de 10 por 100 no se cumple.
- **Frases sintéticas**; la evaluación con frases del equipo está pendiente.
- **Whisper medido con voz sintética**; exactitud con personas mayores reales sin medir.
- **Sin lenguas indígenas.**
- **Revisión humana de los reportes del LLM pendiente.**

## Qué decir en 2 minutos

!!! frase "Guion de 2 minutos · Cómputo Cognitivo"
    «Enlaza Voz escucha una nota de voz de una familia o del personal. **Whisper** la convierte en texto en la laptop.
    Después hay dos capas: **reglas** con nueve categorías de signos de alarma, que no pueden fallar, y un **clasificador**
    de Keras que lee palabras y pedazos de letras para reconocer lo que las reglas no prevén. El clasificador puede subir el
    nivel, nunca bajar una regla.

    Si es emergencia, la pantalla del 911 sale de inmediato: **roja** si fue una regla, **ámbar** si fue solo el
    clasificador, con revisión de coordinación. Después un **modelo de lenguaje local** resume para el médico, en un JSON fijo,
    **sin diagnosticar**.

    Lo evaluamos con un **holdout escrito a ciegas**: detecta {{ voz.holdout.sens }} de las emergencias, pero con
    {{ voz.holdout.fa100 }} falsas alarmas por cada 100 notas. La prueba interna daba {{ voz.internal_test.sens }}: no la
    presumimos porque esos datos se usaron para construir el sistema. Probamos un modelo preentrenado que bajaba las falsas
    alarmas, pero perdía emergencias, y no lo adoptamos porque habíamos escrito la regla antes de ver el resultado.»

## 10 preguntas difíciles

!!! pregunta "1. ¿Por qué no usar solo el clasificador, si aprende?"
    Porque una emergencia evidente («no puede respirar») no debe depender de un modelo estadístico que puede equivocarse.
    Las reglas son predecibles y explicables. El clasificador complementa: detectó {{ vozb.holdout.emerg_only_classifier }}
    emergencias del holdout que ninguna regla vio.

!!! pregunta "2. ¿Por qué no usar solo reglas?"
    Porque en el holdout las reglas solas detectaron {{ voz.holdout.sens_rules }} de las emergencias: la gente describe una
    emergencia de muchas formas que una lista no prevé.

!!! pregunta "3. ¿Qué es un holdout y por qué es tan importante aquí?"
    Un conjunto que nadie usó para entrenar, ajustar ni escribir reglas, y que se evalúa una sola vez. Las otras pruebas
    estaban «contaminadas»: el externo se usó para escribir reglas y entrenar. El holdout es el único número honesto.

!!! pregunta "4. ¿Por qué la exactitud no es buena métrica aquí?"
    Porque los errores no cuestan igual: perder una emergencia es mucho peor que una falsa alarma. Por eso la métrica
    principal es la sensibilidad de emergencia, y las falsas alarmas se reportan aparte.

!!! pregunta "5. ¿Cómo evitan que el LLM diagnostique o invente?"
    Instrucción explícita, temperatura baja, esquema JSON fijo sin campo de diagnóstico, validación con Pydantic, filtro de
    frases prohibidas y citas textuales de lo dicho. Y el LLM no decide nada: el nivel lo ponen reglas y clasificador.

!!! pregunta "6. ¿Qué es un embedding?"
    Una forma de convertir palabras en listas de números de modo que palabras con uso parecido queden cerca. La red aprende
    esos números al entrenar. Usamos dos: de palabras y de pedazos de letras.

!!! pregunta "7. ¿Por qué n-gramas de caracteres?"
    Porque en un mensaje de celular hay errores de dedo: «respirrar» es una palabra nueva para el modelo de palabras, pero
    comparte casi todos sus pedazos de 3 y 4 letras con «respirar».

!!! pregunta "8. ¿Por qué no adoptaron el modelo v2 si tiene mejor F1?"
    Porque la regla de adopción, escrita antes de abrir el holdout, exigía sensibilidad ≥ 98 % y menos falsas alarmas. v2 bajó
    las falsas alarmas a {{ vozv2.v2.fa100 }} pero su sensibilidad cayó a {{ vozv2.v2.sens }}: dejaba pasar más emergencias. Si
    cambiáramos la regla después de ver el resultado, el holdout ya no serviría como prueba.

!!! pregunta "9. ¿Qué pasa si la persona habla náhuatl o tiene un acento fuerte?"
    Whisper no reconoce bien lenguas indígenas; lo declaramos. La pantalla ofrece «No hablo español / Pedir que alguien me
    llame», que crea una solicitud a coordinación con la lengua. Medir el error por acento y edad con voces reales está
    pendiente.

!!! pregunta "10. ¿Por qué la IA corre en la laptop y no en la nube?"
    Privacidad (la voz de un paciente es un dato sensible y no sale de la computadora), costo cero y control. El costo es la
    velocidad del LLM ({{ voz.t_llm_short }} a {{ voz.t_llm_long }} por reporte), y por eso nada urgente lo espera.
