# Enlace público, presentar en la escuela y día de la defensa {#cap-defensa}

## En una frase

!!! frase "En una frase"
    **El día de la defensa la laptop corre todo, Cloudflare da un enlace público que el sínodo abre con un QR, y la
    demostración sigue un guion de 10 minutos que pasa por las seis materias y por un día normal y una contingencia.**

Defensa: {{ equipo.defensa.fecha }} · {{ equipo.defensa.hora }} · {{ equipo.defensa.lugar }}.

## Explicado sin tecnicismos

La defensa es un ensayo general que ya se hizo varias veces: misma laptop, mismos pasos, mismo orden, con el cronómetro
encendido. Lo que puede fallar (el internet de la escuela, el proyector, el modelo de lenguaje) tiene un plan B
(@ref(cap-planb)).

## Por qué lo hicimos así

- **Enlace público con QR**: el sínodo puede entrar desde su celular y ver el tablero moverse en vivo (criterio A4).
- **Guion fijo**: el PP califica la exposición oral y la demostración en tiempo real ({{ doc.rub_oral }} de la rúbrica); un guion
  ensayado evita pasarse de tiempo.
- **Un día normal y una contingencia**: lo pide el Plan General de SIE (sección 3) y es el incidente crítico del PP.

## Cómo funciona por dentro

### 1. Enlace público y QR

```powershell
cloudflared tunnel --url http://localhost:8080     # en PowerShell; NO cerrar esta ventana
```

Aparece `https://palabras-al-azar.trycloudflare.com`. Para el QR (en Ubuntu):

```bash
sudo apt install -y qrencode
qrencode -s 12 -o ~/qr_enlaza.png "https://palabras-al-azar.trycloudflare.com"
```

- El enlace **cambia** cada vez que se reinicia el túnel: generar el QR **después** de abrirlo y no cerrarlo.
- Probarlo con un celular **con datos móviles** (no con el wifi de la escuela): iniciar sesión, pedir un servicio y ver que
  aparece en el tablero de la laptop sin recargar.

### 2. Presentar en la escuela

| Qué | Cómo |
|---|---|
| Proyector | resolución 1280 × 720 o mayor; las pantallas se probaron a ese tamaño; usar «Modo presentación» en `/simulacion` |
| Pantallas | una ventana del navegador por rol, ya con la sesión iniciada: Dirección (`/demo`, `/simulacion`), Coordinación (`/tablero`), Familia (`/familia`, `/voz`), Médico (`/reportes-voz`) |
| Red | la app corre en la laptop; internet solo hace falta para el enlace público y las calles del mapa |
| Energía | laptop conectada; suspensión en «Nunca» |
| Respaldo | video grabado de la demo completa y `http://localhost:8080` |

### 3. Día de la defensa, minuto a minuto

| Cuándo | Qué | Quién |
|---|---|---|
| Día anterior | ensayo general con cronómetro; `bash scripts/backup_db.sh ensayo_general`; `python3 scripts/reset_demo.py`; (opcional) recrear la base y `rebase_dates.py` | ____ |
| −60 min | conectar la corriente; abrir Docker Desktop y Ollama; `docker compose up -d`; `curl localhost:8080/api/health` | ____ |
| −50 min | `ollama run` con el modelo de `OLLAMA_MODEL` y la frase «hola» (lo carga en memoria) | ____ |
| −45 min | `python3 scripts/verify_db.py`; `python3 scripts/reset_demo.py`; `bash scripts/backup_db.sh antes_defensa` | ____ |
| −40 min | abrir el túnel, generar el QR, probarlo con datos móviles | ____ |
| −30 min | abrir las ventanas de cada rol; probar una nota de voz rutinaria y una de emergencia; `reset_demo.py` de nuevo | ____ |
| −10 min | proyector, «Modo presentación», cronómetro listo | ____ |
| 0 | guion de 10 minutos | todos |
| +10 | preguntas (5 min) | todos |
| Después | `bash scripts/backup_db.sh defensa` | ____ |

### 4. Guion de la demostración (10 minutos)

Basado en `docs/spec/10_plan_demo_y_criterios.md`, con los cambios posteriores.

| Min | Responsable | Qué se dice | Qué se muestra |
|---|---|---|---|
| 0–1 | {{ equipo.materias.emprendimiento }} (Emprendimiento) | el problema y Enlaza en una frase; el público abre el QR | página `/` |
| 1–3 | {{ equipo.materias.sie }} (SIE) | transacción central, asignación automática, aprobación humana de lo alto, aislamiento | familia pide un servicio → asignado solo; una alta → `/aprobaciones` → aparece en el tablero |
| 3–5 | {{ equipo.materias.visualizacion }} (Visualización) | preguntas por tarjeta, contra qué se compara, «datos insuficientes», sin promedios engañosos | `/panorama` (población y operación) |
| 5–7 | {{ equipo.materias.simulacion }} (Modelado y Simulación) | contingencia en vivo: detecta, propone, coordinación aprueba; SIRAG-D y el hallazgo que cambió el producto | `/demo` → «Contingencia en el oriente» → `/contingencia` → «Aprobar todo»; `/simulacion` en modo presentación |
| 7–9 | {{ equipo.materias.computo_cognitivo }} (Cómputo Cognitivo) | reglas + clasificador, dos niveles, holdout honesto | nota rutinaria → reporte del médico con confianza; frase de emergencia → pantalla roja 911 |
| 9–10 | {{ equipo.materias.practica_profesional }} (Práctica Profesional) y {{ equipo.materias.emprendimiento }} | consentimiento (y asentimiento), bitácora, diagnóstico de campo; equilibrio y escenario recomendado; cierre | `/privacidad`; `/negocio` |

!!! cuidado "Frases de voz ensayadas"
    Usar **frases ya probadas**. Rutina: «Mi papá amaneció de buen humor, desayunó completo y ya se tomó sus pastillas.»
    Emergencia por regla: «Mi mamá no puede respirar, tiene los labios morados y casi no responde.» **Evitar** frases como «Hoy mi
    mamá comió bien y durmió su siesta», que el clasificador marca como emergencia (aviso ámbar). Si sale el ámbar, no es un error
    del guion: es el momento de explicar los dos niveles y la revisión humana.

**Las preguntas más probables** (spec 10): por qué datos sintéticos, qué pasa si falla el internet, cómo se evita que una
institución vea a otra, qué pasa con una falsa alarma, cuánto cuesta operar y cómo se validó la simulación. Las respuestas modelo
están en la Guía rápida y en cada capítulo.

## Dónde está en el código

| Qué | Dónde |
|---|---|
| Guion original y criterios | `docs/spec/10_plan_demo_y_criterios.md` |
| Panel de demostración | `/demo` (`frontend/src/pages/DemoPage.tsx`) |
| Preparación detallada | `docs/00_preparar_laptop_y_github.md`, sección «Día de la defensa» |

## Números clave

{{ tabla doc.peso_exposicion doc.rub_oral man.evento_tunel_s man.deteccion_contingencia_demo voz.t_llm_short }}

## Limitaciones honestas

- El túnel rápido de Cloudflare no garantiza disponibilidad: por eso el video y `localhost`.
- El modelo de lenguaje tarda; el reporte del médico puede aparecer después de que termine ese minuto del guion.
- La contingencia de demostración tarda en detectarse hasta el siguiente minuto del worker.

## Preguntas que te pueden hacer

!!! pregunta "¿Lo que vemos es en vivo o está grabado?"
    En vivo: la laptop corre todo y ustedes pueden entrar por el QR. Las acciones del panel de demostración solo cambian datos de
    entrada; lo demás lo hace el sistema como en la operación real.
