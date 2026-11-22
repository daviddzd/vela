# ORACLE-Voz · decisiones y resultados (paso 7)

Rama `feature/oracle-voz`. Detalle técnico en `voice/README.md` y `voice/eval/README.md`.

## 1. Arquitectura y seguridad
- Servicio interno `voice` (sin puerto público): faster-whisper `small` int8 en CPU y clasificador Keras.
  La API orquesta: **consentimiento** `voice_assistant` → transcripción → **reglas** → clasificador
  (solo puede subir el nivel) → aviso de emergencia **antes** del LLM → reporte en segundo plano.
- **El audio no se guarda**, solo la transcripción (minimización de datos).
- Al familiar nunca se le dice «no es una emergencia»: «Tu mensaje se envió al equipo de cuidado. Si la
  situación empeora, llama al 911». El botón «Llamar al 911» está siempre visible en `/voz`.
- Plan B en cada paso: sin micrófono o sin servicio de voz → escribir; sin clasificador → solo reglas, nivel
  mínimo `urgent` y revisión humana; sin modelo en `voice/models/` → se entrena al arrancar; sin LLM o con JSON
  inválido → se guarda solo la transcripción y el nivel.
- «No hablo español / Pedir que alguien me llame» crea una solicitud a coordinación con la lengua registrada.

## 2. Evaluación del triaje (texto, sistema completo)
Decisiones del equipo (21 nov 2026): aplicar las reglas propuestas, reentrenar el clasificador con el interno
+ el externo y medir **solo en un tercer conjunto a ciegas** (`data/voice/holdout_phrases.csv`). Lo escribió
un subagente que no vio las reglas ni los otros CSV, con 50 frases por nivel y las 9 categorías, y se guardó
en Git (commit `Add blind holdout phrase set…`) **antes** de evaluarlo. No se usa para ajustar nada.

| Conjunto | n | Sensibilidad de emergencia | Solo reglas | F1 macro | Falsas alarmas / 100 notas | ¿Independiente? |
|---|---|---|---|---|---|---|
| Prueba interna (`triage_phrases.csv`, `test`) | 230 | 100 % | 100 % | 0.978 | 2.2 | No (reglas y entrenamiento) |
| Externo (`external_phrases.csv`) | 150 | 100 % | 100 % | 0.894 | 8.7 | No (reglas y entrenamiento) |
| **Holdout a ciegas** | 150 | **98 %** | **58 %** | **0.647** | **26.0** | **Sí** |

**Metas en el holdout:** sensibilidad ≥ 98 % → **se cumple** (49 de 50). Menos de 10 falsas alarmas por 100
notas → **no se cumple** (26.0: 39 de 100 mensajes no urgentes terminan en la pantalla del 911).

- **Se escapó 1 emergencia:** HLD-070, una autolesión descrita sin palabras obvias («encontré vacías las
  cajas de sus pastillas para dormir… está muy adormilada; me había dicho que ya no quería ser una carga»).
  Las reglas no la ven y el clasificador dijo «rutina».
- **EXT-025** (convulsión) ya la detecta la regla `seizure` («temblando todo el cuerpo», «espuma por la boca»);
  hay una prueba automática.
- **Reglas nuevas, antes → después (solo reglas):** holdout 42 % → 58 % de emergencias detectadas, con
  3.3 → 4.7 falsas alarmas por 100. Ayudan con frases nuevas, pero muy lejos del 100 % del externo: se
  escribieron viéndolo. En el CSV interno no agregan falsas alarmas.
- **Origen de las 39 falsas alarmas del holdout:** 7 vienen de reglas (negaciones y sentido figurado: «no se
  desmayó», «de broma», «ataque de nervios», «la boca chueca desde hace años») y 32 del clasificador. El
  clasificador detecta **20 de las 49 emergencias** que no ve ninguna regla, así que quitarlo bajaría la
  sensibilidad a 58 %.
- **Clasificador reentrenado:** palabras + n-gramas de caracteres (resiste errores de dedo), con aumento de
  datos (errores de dedo, muletillas, paráfrasis y mensajes que mezclan dos frases). Exactitud de validación
  0.968 en frases originales apartadas; antes daba 1.000, una señal de que memorizaba plantillas.

### Opciones para bajar las falsas alarmas sin perder sensibilidad (decide el equipo)
1. **Negaciones y contexto en las reglas** («no se desmayó», «de broma», «desde hace años»): quitaría ~7 de
   39. Se tendría que validar con un **cuarto conjunto**: las frases del equipo (`team_phrases_*.csv`).
2. **Más variedad real para el clasificador:** con las 20 frases por integrante y paráfrasis escritas por
   personas (no plantillas). Es la causa de fondo: el clasificador nunca vio frases como las del holdout.
3. **Modelo de lenguaje preentrenado en español** (por ejemplo, un codificador de oraciones pequeño, en CPU)
   en lugar de un modelo entrenado desde cero con 1,700 frases. Es el cambio con más probabilidad de
   cumplir las dos metas, pero agrega ~100–500 MB y hay que explicarlo en la defensa.
4. **Aceptarlo para el prototipo y decirlo en la defensa:** el sistema se equivoca hacia el lado seguro
   (manda al 911 de más, casi nunca de menos), y las falsas alarmas también alertan a coordinación.
No se propone subir el umbral del clasificador: reduce falsas alarmas a costa de sensibilidad.

## 3. Tiempos (laptop Ryzen, CPU 16 hilos; `voice/eval/results/timings.csv`)
| Paso | Tiempo |
|---|---|
| Respuesta con el nivel (texto: reglas + clasificador) | 0.1–0.2 s |
| Whisper, nota de 10 s | ≈ 2 s |
| Whisper, nota de 30 s | ≈ 4.4 s |
| Whisper, nota de 60 s | 8–13 s (varía con la carga de la laptop) |
| Reporte del LLM, nota corta | 12–15 s |
| Reporte del LLM, nota larga (176 palabras) | 24–57 s |
La pantalla del 911 no espera al LLM. Las notas de prueba de Whisper son voz sintética (espeak-ng): sirven para
medir tiempo, no exactitud.

## 4. Reportes para el médico (criterio A8)
`voice/eval/results/reports_review.md`: 20 reportes generados por `qwen3:8b`; los 20 válidos, ninguno con
frases prohibidas ni nombres de enfermedades (búsqueda automática). Falta la **revisión humana** del equipo
(casillas en el archivo). Defensas: instrucción sin diagnósticos, esquema JSON, validación con Pydantic,
filtro de diagnóstico, recomendación y «no es emergencia», y el nivel siempre lo pone el sistema.

## 5. Sesgo de reconocimiento de voz
- **Equipo:** procedimiento en `voice/eval/README.md` (15 frases del conjunto externo por integrante, con
  consentimiento, en `voice/eval/audio/`, que Git ignora). `bias_wer.py` mide el WER y cada emergencia perdida
  por un error de transcripción. Probado con voz sintética (WER 0.14, 0 emergencias perdidas).
- **Common Voice:** desde octubre de 2025 ya no está en Hugging Face; solo en Mozilla Data Collective (cuenta
  y aceptar condiciones). No se pudo descargar aquí; el script queda listo para `voice/eval/audio/cv-es/`.

## 6. Cambios del 21 nov 2026 (después de la revisión)
- **Línea de la Vida.** Si la regla que se activó es `self_harm`, la pantalla roja muestra también la Línea de
  la Vida, **800 911 2000** (gratuita, las 24 horas). Número verificado el 21 nov 2026 en la página oficial de
  CONASAMA, Secretaría de Salud: https://www.gob.mx/conasama/articulos/linea-de-la-vida-800-911-2000.
  Está en `config/emergency_rules.yaml` (`support_lines`), con su fuente; no está escrito en el código.
- **Bandeja del médico:** primero lo no revisado, dentro de eso lo más grave y luego lo más reciente; filtro
  «Sin revisar» (activo por omisión) y «Todos», con el conteo pendiente.
- **`scripts/reset_demo.py`:** deja la operación limpia para la defensa (reportes de voz, alertas, avisos,
  escenarios de demostración y visitas en vivo pendientes) sin tocar la semilla ni `audit_log`. La semilla
  queda intacta porque las acciones de demostración solo cambian visitas pendientes y toda la semilla es
  historial pasado; se comprobó comparando la base con los CSV de `database/seed/`. Está en la guía, en
  «Día de la defensa».
- **Plantilla del equipo:** `data/voice/team_phrases_template.csv` e instructivo
  `data/voice/INSTRUCTIVO_frases_equipo.md` (20 frases por integrante, a ciegas). Serán el cuarto conjunto.

## 7. Prueba intermitente (sin causa encontrada)
Una vez falló `test_without_classifier_rules_only_and_human_review` con `KeyError: 'level'`: la segunda
petición (la de emergencia) respondió un error en lugar del resultado. **No se pudo reproducir** en más de
150 corridas: suites completas seguidas, después de reiniciar o reconstruir la API, con notas reales y
reportes del LLM en curso, con una ráfaga de 400 notificaciones en tiempo real y durante el reinicio de datos.
Se descartó con evidencia: el límite de intentos de login (se reinicia en cada prueba), un 403 por alcance
(no quedó en `audit_log`), un error de PostgreSQL (no hay nada en su registro a esa hora), consentimientos
duplicados (no hay) y estado guardado en la sesión (el token no guarda estado).
Quedó instrumentado: todas las pruebas de voz envían con `send()`, que muestra el código y el cuerpo de la
respuesta si falla. Además se corrigió una fragilidad real (no era la causa): `test_rule_hit…` leía «la
alerta más reciente» y podía tomar una alerta real creada al mismo tiempo; ahora lee solo la de su transacción.

**Otra fragilidad encontrada antes del PR (22 nov 2026, no relacionada con la voz):** cuatro pruebas antiguas
(`test_operations`, `test_privacy`, `test_contingency`) suponían un calendario vacío y fallaban cuando el worker
ya había creado las visitas reales del día (62 a las 13:30). Ahora apartan las visitas vivas del cuidador dentro
de su propia transacción (`free_caregiver`, se deshace al terminar) y el conteo de pacientes del médico se lee de
la base. Las aserciones siguen igual de estrictas. Esto no explica la falla de la voz: una nota de voz no crea
visitas ni toca `assignments`.
