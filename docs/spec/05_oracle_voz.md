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
EMERGENCY ──► pantalla completa "Esto puede ser una emergencia. Llama al 911 ahora." + botón tel:911
              + alerta crítica a coordinación (WebSocket)   [no espera al LLM]
todos     ──► LLM local (Ollama) genera reporte JSON ──► bandeja del médico
```

## Reglas de seguridad
- 9 categorías de emergencia (dificultad grave para respirar, dolor de pecho, inconsciencia, signos de
  EVC, convulsión, sangrado grave, caída grave, confusión súbita, autolesión).
- Sin manejo de negaciones: "ya no puede respirar" o "ya no quiere vivir" deben seguir siendo emergencia.
  Se prefiere una falsa alarma a una emergencia perdida.
- El clasificador puede subir el nivel, nunca bajar uno detectado por regla.
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
