# Evaluación de ORACLE-Voz

## 1. Texto: prueba interna y conjunto externo
- **Interna**: división `test` de `data/voice/triage_phrases.csv`. Las reglas se escribieron viendo todo ese
  archivo, así que el 100 % ahí **no** demuestra que generalicen.
- **Externa**: `data/voice/external_phrases.csv`, 150 frases nuevas con otro estilo (coloquiales, errores de
  dedo, rodeos, regionalismos, frases largas). Se etiquetaron y se guardaron en Git **antes** de correr las
  reglas (commit `Add external phrase set…`). Las reglas no se cambiaron para pasarlo.

## 2. Voces reales del equipo (procedimiento)
Cada integrante graba **15 frases** del conjunto externo con su celular. Son frases inventadas: no se graba
ningún dato real.

1. **Consentimiento.** Cada persona acepta por escrito (puede ser un mensaje) que su voz se use solo para esta
   evaluación y que los audios no salen de la laptop del proyecto. Sin ese «sí», no se usa su audio.
2. **Frases.** Cada quien toma un bloque distinto para cubrir más casos:
   integrante 1: EXT-001 a EXT-005, EXT-051 a EXT-055 y EXT-101 a EXT-105; integrante 2: EXT-006 a EXT-010,
   EXT-056 a EXT-060 y EXT-106 a EXT-110; y así sucesivamente (5 de emergencia, 5 urgentes y 5 rutinarias).
3. **Cómo grabar.** Con la app de grabadora del celular, en un lugar normal (no un estudio), leyendo la frase
   como se la diría a alguien por teléfono. Un archivo por frase, con el nombre exacto de la frase:
   `EXT-001.m4a` (también sirven `.webm`, `.ogg`, `.wav`, `.mp3`).
4. **Dónde ponerlas.** `voice/eval/audio/<nombre_corto>/EXT-001.m4a`, etc. Esa carpeta **Git la ignora**.
5. **Datos del grupo** en `voice/eval/audio/team.csv` (sin nombres reales si no quieren):
   ```
   person,age_band,gender,accent,consent
   integrante1,20-29,mujer,CDMX,yes
   ```
6. **Correr:** `docker compose run --rm voice python -m voice.eval.bias_wer`. Reporta el WER por persona y
   grupo, y **cada emergencia que se pierde por un error de transcripción**: la frase original sí es emergencia,
   pero lo que Whisper entendió ya no.

## 3. Mozilla Common Voice (español, CC0)
Desde octubre de 2025, Common Voice **ya no está en Hugging Face**: solo se distribuye por
**Mozilla Data Collective** (https://datacollective.mozillafoundation.org). No se necesita token de Hugging Face.

Pasos para quien lo descargue:
1. Crear una cuenta en Mozilla Data Collective y aceptar las condiciones del conjunto *Common Voice Spanish*.
2. Descargar la versión en español más reciente. El archivo completo pesa decenas de GB; si se ofrece un
   subconjunto (*delta* o por segmento), basta para la prueba.
3. Descomprimir y copiar **solo** `validated.tsv` y la carpeta `clips/` a `voice/eval/audio/cv-es/`.
4. Correr: `docker compose run --rm voice python -m voice.eval.bias_wer --cv-n 300`. Toma una muestra de 300
   clips con edad declarada y reporta el WER por edad, género y acento.

No se usan videos ni audios sin licencia.
