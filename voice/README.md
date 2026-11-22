# ORACLE-Voz

Servicio interno `voice` (no tiene puerto público; solo lo llama la API en `http://voice:8001`):
**faster-whisper** `small` int8 en CPU (español) y el **clasificador Keras** de triaje.
La API orquesta todo (`backend/app/services/oracle.py`). **El audio nunca se guarda**, solo la transcripción.

## Flujo
1. **Consentimiento** `voice_assistant` vigente (revisado en la API). Sin él: no se graba ni se procesa nada.
2. **Transcripción** (o texto escrito si no hay micrófono o el servicio de voz no responde).
3. **Reglas** (`config/emergency_rules.yaml`, `backend/app/services/triage_rules.py`): una coincidencia es
   siempre `emergency`.
4. **Clasificador**: puede subir el nivel, nunca bajar una regla. Si no está disponible, se usan solo las
   reglas, el nivel mínimo es `urgent` y se marca `needs_human_review`.
5. **Emergencia**: pantalla completa «Esto puede ser una emergencia. Llama al 911 ahora.» y alerta crítica a
   coordinación, **antes** del LLM.
6. **Reporte** para el médico con Ollama (`OLLAMA_MODEL`, `think: false`, JSON validado con Pydantic, filtro
   de diagnósticos, recomendaciones y «no es emergencia»), en segundo plano.

Al familiar nunca se le dice «no es una emergencia»: el mensaje es «Tu mensaje se envió al equipo de
cuidado. Si la situación empeora, llama al 911.»

## Confianza de la transcripción (umbral documentado)
- `confidence` = promedio, ponderado por duración de cada segmento, de `exp(avg_logprob)` de Whisper (0–1).
- `no_speech_prob` = el mayor valor entre segmentos (probabilidad de que no haya voz).
- Se marca `needs_human_review` y se pide repetir si `confidence < 0.6`, si `no_speech_prob > 0.6` o si el
  texto tiene menos de 3 palabras. **Las reglas se aplican igual**: una emergencia con audio dudoso sigue
  siendo emergencia.

## Clasificador: entrenar o reentrenar
```bash
docker compose run --rm voice python -m voice.triage.classifier
```
Dos vistas del texto unidas: **palabras** (unigramas y bigramas) y **n-gramas de caracteres** (3 y 4 letras;
un error de dedo cambia una palabra entera pero solo unos cuantos n-gramas, así que el modelo lo resiste).
Datos: `triage_phrases.csv` (todas las divisiones) + `external_phrases.csv`, más **aumento de datos**
(`voice/triage/augment.py`: errores de dedo, muletillas, paráfrasis y mensajes largos que mezclan dos frases,
donde manda la parte más grave). El 15 % de las frases originales se aparta, sin aumento, para elegir la
época. **`holdout_phrases.csv` nunca se usa para entrenar**: es solo para la evaluación. Semilla 2026.
Guarda `voice/models/triage_classifier.keras`, que Git ignora. **Si la carpeta está vacía (clon nuevo), el
servicio lo entrena solo al arrancar** (~20 s); mientras tanto la API usa solo las reglas.

## Evaluación (`voice/eval/`, resultados en `voice/eval/results/`)
| Script | Qué mide |
|---|---|
| `python -m voice.eval.evaluate` | Sistema completo en la prueba interna, el conjunto externo y el **holdout** (la única prueba independiente): sensibilidad de emergencia, F1 macro, matriz de confusión, falsas alarmas por 100 notas, cada emergencia que se escapa |
| `python -m voice.eval.compare_rules` | Reglas anteriores frente a las agregadas el 21 nov 2026 (`proposed_rules.yaml`, ya aplicadas) |
| `python -m voice.eval.timings` | Tiempo de Whisper con notas de 10, 30 y 60 s y del reporte del LLM |
| `python -m voice.eval.review_reports` | 20 reportes para revisión humana (`reports_review.md`, criterio A8) |
| `python -m voice.eval.bias_wer` | WER por grupo y emergencias perdidas por transcripción (equipo y Common Voice) |

Todos se corren con `docker compose run --rm voice …`.
