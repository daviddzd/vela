# Enlace público, presentar en la escuela y día del coloquio {#cap-defensa}

## En una frase

!!! frase "En una frase"
    **El día del coloquio la laptop corre todo, el sínodo entra por {{ ops.public_url }} con un QR, y la exposición sigue la
    presentación y el guion de `docs/presentacion/`: 10 minutos con la demostración en vivo a la mitad y 5 de preguntas.
    Todo el equipo defiende todo.**

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

### 1. Enlace público fijo y QR

La app tiene una dirección que no cambia: **`https://enlaza.zenthinks.com`**. Es un [[túnel|túnel con nombre]] de
Cloudflare (`enlaza`) que lleva esa dirección a `http://127.0.0.1:8080` de la laptop. Funciona desde cualquier celular
**mientras la laptop esté encendida, con la sesión de Windows iniciada y con internet**. La raíz `zenthinks.com` no apunta a nada.

Todo arranca solo al iniciar sesión en Windows:

| Pieza | Cómo arranca |
|---|---|
| Túnel | servicio de Windows `cloudflared` (automático, desde que prende la laptop), con `--protocol http2` para que funcione también en el hotspot de un celular |
| Reconexión del túnel | tareas «Enlaza - túnel»: al cambiar de red o al despertar la laptop reinician el túnel; cada 2 min revisan que esté conectado con Cloudflare y, si no, lo reinician. Vuelve solo en menos de un minuto |
| Docker Desktop | «Start Docker Desktop when you sign in» |
| Contenedores | `restart: unless-stopped` y la tarea «Enlaza - arranque» (`scripts/autostart.sh`), que repara los que Docker levantó antes de que Ubuntu estuviera listo |
| Ollama | acceso directo en la carpeta Inicio de Windows |
| Reloj de WSL | tarea «Enlaza - reloj de WSL»: copia la hora de Windows al iniciar sesión, al despertar y cada media hora (evita el «Inicia sesión para continuar») |

El QR fijo ya está hecho (`docs/privado/qr_enlaza.png` y `qr_enlaza_diapositiva.png`, fuera de Git); se regenera con
`uv run scripts/make_qr.py`.

**Comprobar que el túnel está arriba** (Ubuntu, en la carpeta del proyecto):

```bash
bash scripts/enlaza.sh estado            # túnel CONECTADO con Cloudflare, contenedores y sus archivos, Ollama, localhost, dirección pública, reloj
uv run scripts/check_public_url.py       # prueba completa por https: 12 de 12 (crea una solicitud: luego reset_demo.py)
```

En PowerShell, `Get-Service cloudflared` debe decir `Running`; en el panel de Cloudflare (Networks → Tunnels) el túnel
`enlaza` aparece como **HEALTHY**.

**Si falla**: @ref(cap-planb). En corto: error 502 → la app no corre (`bash scripts/autostart.sh`); error 1033 → el
túnel está desconectado de Cloudflare (pasa al cambiar de wifi a hotspot; las tareas lo reconectan solas en menos de un minuto).

!!! cuidado "Si la página da error 1033"
    **Si la página da error 1033: PowerShell como administrador → `Restart-Service cloudflared`.**
    Desde Ubuntu sirve igual `bash scripts/enlaza.sh reconectar`. En unos segundos `bash scripts/enlaza.sh estado` debe decir
    «Conexión con Cloudflare: CONECTADO».

Si no se arregla en dos minutos, **plan B: túnel rápido** (también con `--protocol http2`, para que funcione en el hotspot):

```bash
bash scripts/enlaza.sh rapido                                        # da https://palabras-al-azar.trycloudflare.com
# sin Ubuntu, en PowerShell: cloudflared tunnel --protocol http2 --url http://localhost:8080
uv run scripts/make_qr.py https://palabras-al-azar.trycloudflare.com   # QR de respaldo → docs/privado/qr_rapido*.png
```

**Apagar todo** al terminar: `bash scripts/backup_db.sh defensa` y `bash scripts/enlaza.sh apagar`. Al reiniciar la laptop
todo vuelve a encender solo. Solo el túnel, en PowerShell como
administrador: `Stop-Service cloudflared` / `Start-Service cloudflared`.

### 2. Presentar en la escuela

| Qué | Cómo |
|---|---|
| Proyector | resolución 1280 × 720 o mayor; las pantallas se probaron a ese tamaño; usar «Modo presentación» en `/simulacion` |
| Pantallas | una ventana del navegador por rol, ya con la sesión iniciada: Dirección (`/demo`, `/simulacion`), Coordinación (`/tablero`), Familia (`/familia`, `/voz`), Médico (`/reportes-voz`) |
| Red | la app corre en la laptop; internet solo hace falta para el enlace público y las calles del mapa |
| Energía | laptop conectada; suspensión en «Nunca» |
| Respaldo | video grabado de la demo completa y `http://localhost:8080` |

### 3. Día del coloquio, minuto a minuto

Lo hace todo el equipo; el checklist detallado (1 hora antes, 15 minutos antes, justo antes y al terminar) está en el guion.

| Cuándo | Qué |
|---|---|
| Día anterior | ensayo general con cronómetro; `bash scripts/backup_db.sh ensayo_general`; `python3 scripts/reset_demo.py`; (opcional) recrear la base y `rebase_dates.py` |
| −60 min | conectar la corriente; prender la laptop e iniciar sesión (todo arranca solo); `bash scripts/enlaza.sh estado` |
| −50 min | `ollama run qwen3:8b "hola"` (lo deja cargado: el primer reporte tarda {{ mod.llm_gpu_frio }} en frío) |
| −45 min | `python3 scripts/verify_db.py`; `bash scripts/backup_db.sh antes_coloquio`; `python3 scripts/reset_demo.py` |
| −40 min | `uv run scripts/check_public_url.py` ({{ hist.prueba_publica }}); probar el QR con un celular con datos móviles; `reset_demo.py` |
| −15 min | abrir las ventanas de cada rol con su sesión; probar la frase de emergencia; `reset_demo.py` de nuevo |
| 0 | exposición de 10 minutos (presentación y guion) |
| +10 | preguntas del sínodo (5 min), con la diapositiva de «Gracias» en pantalla |
| Al terminar | `python3 scripts/reset_demo.py` (y antes, si se quiere guardar cómo quedó, `bash scripts/backup_db.sh coloquio`) |

### 4. La presentación y el guion

Todo lo del coloquio vive en **`docs/presentacion/`** y se regenera con `bash scripts/build_presentacion.sh` (los números salen
del mismo script que este libro):

| Archivo | Qué es |
|---|---|
| `enlaza_coloquio.pptx` y `.pdf` | la presentación 16:9, con texto editable y el guion en las notas del orador |
| `guion_coloquio.md` y `.pdf` | minuto a minuto (quién habla, qué dice, qué se ve), la demostración paso a paso con cuentas y ventanas, el plan B de cada paso, las 20 preguntas más probables, el **checklist** del día y el guion del video de respaldo |
| `README.md` | cómo se genera y qué fuentes instalar en Windows |

La versión que está en Git dice «Persona 1–4». **La versión con los nombres del equipo**, la que se proyecta, se genera en
**`docs/privado/coloquio/`** (`enlaza_coloquio.pptx` y `.pdf`) a partir de `docs/biblia/equipo.yaml`; esa carpeta no se sube a
Git. En el guion los papeles siguen como «Persona 1–4»: reparten el tiempo de exposición, pero cualquiera responde cualquier
pregunta.

La presentación sigue lo mismo que este libro: la simulación **nos dijo cómo asignar** (@ref(cap-sirag)), la voz se presenta con
sus falsas alarmas (@ref(cap-voz)) y el escenario recomendado siempre con su condición (@ref(cap-negocio)).

!!! cuidado "Frase de voz ensayada"
    En la demostración se usa **exactamente**: «Mi mamá no puede respirar y tiene los labios morados.» (activa la regla de
    dificultad grave para respirar: pantalla roja). Rutina, si piden otra: «Mi papá amaneció de buen humor, desayunó completo y ya
    se tomó sus pastillas.» **Evitar** «Hoy mi mamá comió bien y durmió su siesta», que el clasificador marca como emergencia
    (aviso ámbar). Si sale un ámbar inesperado, no es un error del guion: es el momento de explicar los dos niveles.

**Las preguntas más probables** (spec 10): por qué datos sintéticos, qué pasa si falla el internet, cómo se evita que una
institución vea a otra, qué pasa con una falsa alarma, cuánto cuesta operar y cómo se validó la simulación. Las respuestas modelo
están en la Guía rápida y en cada capítulo.

## Dónde está en el código

| Qué | Dónde |
|---|---|
| Presentación, guion y checklist | `docs/presentacion/` (versión con nombres: `docs/privado/coloquio/`) |
| Cómo se generan | `scripts/build_presentacion.sh`, `docs/presentacion/build/` |
| Guion original y criterios | `docs/spec/10_plan_demo_y_criterios.md` |
| Panel de demostración | `/demo` (`frontend/src/pages/DemoPage.tsx`) |
| Preparación detallada | `docs/00_preparar_laptop_y_github.md`, secciones «Enlace fijo» y «Día de la defensa» |
| Operación del túnel | `scripts/enlaza.sh`, `scripts/autostart.sh`, `scripts/check_public_url.py`, `scripts/make_qr.py`, `scripts/windows/` |

## Números clave

{{ tabla doc.peso_exposicion doc.rub_oral man.evento_tunel_s man.deteccion_contingencia_demo voz.t_llm_short }}

## Limitaciones honestas

- El enlace fijo depende de la laptop, de su internet y de Cloudflare; si se suspende la laptop, se cae. El túnel rápido de
  respaldo no garantiza disponibilidad: por eso también el video y `localhost`.
- Tras reiniciar, Docker Desktop suele levantar los contenedores antes que Ubuntu y salen sin archivos; la tarea de arranque
  lo repara en el primer minuto, pero conviene revisar `enlaza.sh estado` antes de presentar.
- El modelo de lenguaje tarda; el reporte del médico puede aparecer después de que termine ese minuto del guion.
- La contingencia de demostración tarda en detectarse hasta el siguiente minuto del worker.

## Preguntas que te pueden hacer

!!! pregunta "¿Lo que vemos es en vivo o está grabado?"
    En vivo: la laptop corre todo y ustedes pueden entrar por el QR. Las acciones del panel de demostración solo cambian datos de
    entrada; lo demás lo hace el sistema como en la operación real.
