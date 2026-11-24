# 05 · ORACLE-Voz (Cómputo Cognitivo)

Asistente de voz para familiares y cuidadores: escucha una nota, detecta si es una emergencia y prepara
un reporte estructurado para el médico. **No diagnostica.**

## Flujo
```
[¿consentimiento voice_assistant vigente?] ──no──► mensaje: "Falta autorización" (no se graba)
        │ sí
grabación (navegador, máx. 60 s, WebM/Opus) ──► faster-whisper (es, small, int8, CPU)
        ──► normalizar texto (minúsculas, sin acentos)
        ──► 1. reglas (config/emergency_rules.yaml) ──hit──► EMERGENCY
        ──► 2. clasificador Keras (emergency / urgent / routine)
        ──► nivel final = max(regla, clasificador)
EMERGENCY por REGLA ──► pantalla roja completa "Esto puede ser una emergencia. Llama al 911 ahora." + botón tel:911
                        + alerta crítica a coordinación (WebSocket)   [no espera al LLM]
EMERGENCY solo por CLASIFICADOR ──► aviso ámbar completo "Tu mensaje podría indicar algo urgente" con los signos
                        de peligro + el mismo botón grande tel:911 + "Coordinación te contactará en los próximos minutos"
                        + alerta CRÍTICA de revisión a coordinación (contactar a la familia; si nadie la atiende en
                        10 min, escala a Dirección)
todos     ──► LLM local (Ollama) genera reporte JSON ──► bandeja del médico
```

## Reglas de seguridad
- 9 categorías de emergencia (dificultad grave para respirar, dolor de pecho, inconsciencia, signos de
  EVC, convulsión, sangrado grave, caída grave, confusión súbita, autolesión).
- Sin manejo de negaciones: "ya no puede respirar" o "ya no quiere vivir" deben seguir siendo emergencia.
  Se prefiere una falsa alarma a una emergencia perdida.
- El clasificador puede subir el nivel, nunca bajar uno detectado por regla.
- **Dos niveles de aviso (decisión del equipo, 23/11/2026).** El nivel guardado es `emergency` en los dos casos:
  no se descarta nada y el reporte sigue primero en la bandeja del médico; solo cambia cómo se muestra.
  - **Se activó una regla** → pantalla roja del 911, como siempre.
  - **Solo el clasificador** (ninguna regla) → aviso ámbar, que no es tibio: título "Tu mensaje podría indicar algo
    urgente", la lista de signos concretos ("Llama al 911 ahora si la persona: no puede respirar o se ahoga, tiene
    dolor u opresión en el pecho, no responde o se desmayó, tiene la cara caída o no puede hablar, convulsiona,
    sangra mucho o habla de quitarse la vida"), el mismo botón grande del 911 y "Coordinación te contactará en los
    próximos minutos".
  - Coordinación recibe una alerta **crítica** con un contador "Contactar a la familia" y dos botones:
    "Contactada: era emergencia" (escala a Dirección y lo registra) y "Contactada: no era emergencia". Si nadie la
    atiende en `classifier_only.escalate_after_minutes` (10 min, `config/emergency_rules.yaml`), el proceso
    automático la escala a Dirección. Todo queda en la bitácora.
  - **Por qué.** En el conjunto de prueba final (holdout, 150 frases, `voice/eval/results/predictions_holdout.csv`)
    el clasificador, sin ninguna regla, marcó como emergencia **20 emergencias reales** que las reglas no
    detectaron y **32 falsas alarmas** (de 100 frases que no eran emergencia). Con una sola pantalla roja, 39 de
    las 88 pantallas rojas del holdout serían falsas (casi la mitad) y la gente aprendería a ignorarla; con dos
    niveles, la roja queda en 7 falsas de 36. Quitarle al clasificador todo aviso perdería esas 20 emergencias. Con dos niveles, las 20 siguen viendo el 911 y los signos de peligro, y una
    persona de coordinación confirma cada caso en minutos. Caso que lo motivó: "el paciente comió bien y está
    tranquilo" (nota escrita, PAC-0112) salió como emergencia con P = 0.925 solo por el clasificador v1.
- Confianza de transcripción < 0.6 o texto < 3 palabras → `needs_human_review = true` y se pide repetir.
- Si el asistente falla o tarda, la interfaz siempre muestra el botón "Llamar al 911".

## Datos y entrenamiento
- `data/voice/triage_phrases.csv`: 1,526 frases sintéticas en español de México (532 rutina, 532 urgente,
  462 emergencia), con casos difíciles; división 1,067 / 229 / 230 (entrenamiento / validación / prueba).
- Las reglas actuales detectan **462 de 462** emergencias del conjunto (0 omitidas) con 32 falsas alarmas
  en 1,064 frases no urgentes (`data/generator/check_emergency_rules.py`).
- Clasificador: `TextVectorization` (unigramas + bigramas) → `Embedding(64)` → `GlobalAveragePooling` →
  `Dense(32, relu)` → `Dense(3, softmax)`; pesos de clase para dar más costo a omitir emergencias.
- Métrica principal: **sensibilidad (recall) de emergencia del sistema completo = 100 % en prueba**;
  secundarias: F1 macro, matriz de confusión, falsas alarmas por cada 100 notas.

## Reporte para el médico (JSON validado con Pydantic)
```json
{"resumen": "...", "sintomas_mencionados": ["..."], "inicio": "...", "signos_de_alarma": ["..."],
 "medicamentos_mencionados": ["..."], "nivel_triaje": "urgent", "frases_textuales": ["..."],
 "limitaciones": "Transcripción automática; no es diagnóstico."}
```
Instrucción del sistema al LLM (en español): resumir lo dicho, no inferir enfermedades, no recomendar
tratamientos, marcar lo que no se entendió. Temperatura 0.2. Si el JSON no valida, se guarda solo la
transcripción y el nivel de triaje.

## Lenguas indígenas y sesgo
- Whisper no reconoce de forma confiable náhuatl, mixteco u otomí. El prototipo trabaja en español y lo
  declara como limitación; en pantalla se ofrece "Pedir que alguien llame" para quien no hable español.
- Prueba de sesgo: medir tasa de error por palabra (WER) con grabaciones de **licencia abierta**
  (Mozilla Common Voice, español, CC0) agrupadas por acento/edad declarados, más grabaciones propias del
  equipo con consentimiento. No usar videos o audios sin licencia.
- Reportar en `voice/eval/`: WER por grupo, sensibilidad de emergencia por grupo, tiempo de respuesta.
