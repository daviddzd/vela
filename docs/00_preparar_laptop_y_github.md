# Preparar la laptop, crear el repositorio y publicar el enlace

Laptop con procesador AMD Ryzen y Windows 11. Todo corre en la laptop; Cloudflare solo crea un enlace
público hacia ella. Tiempo estimado: 1.5–2 h la primera vez. Hazlo con la laptop conectada a la corriente.

---

## Parte A · Windows

### A1. Actualizar y activar virtualización
1. Windows Update al día (Configuración → Windows Update).
2. Comprueba que la virtualización está activa: Administrador de tareas → Rendimiento → CPU →
   "Virtualización: Habilitado". Si dice "Deshabilitado", actívala en la BIOS (opción *SVM Mode*).

### A2. Instalar WSL2 con Ubuntu 24.04
En **PowerShell como administrador**:
```powershell
wsl --install -d Ubuntu-24.04
```
Reinicia, abre "Ubuntu" desde el menú Inicio y crea tu usuario y contraseña de Linux.
Comprueba en PowerShell: `wsl -l -v` → debe decir `Ubuntu-24.04 … 2`.

### A3. Docker Desktop
1. Descarga e instala Docker Desktop para Windows desde https://www.docker.com/products/docker-desktop/
   (uso gratuito para fines educativos).
2. Settings → General: "Use the WSL 2 based engine" ✔.
3. Settings → Resources → WSL integration: activa **Ubuntu-24.04**.
4. Settings → Resources → Advanced: memoria para Docker ≈ la mitad de la RAM de la laptop.

### A4. Ollama (modelo de lenguaje local) con la GPU Radeon
1. Instala Ollama para Windows desde https://ollama.com/download.
2. Activa la GPU integrada. Ollama usa Vulkan para las Radeon, pero **descarta las GPU integradas por
   defecto**; en el log (`%LOCALAPPDATA%\Ollama\server.log`) aparece
   `dropping integrated GPU; to enable, set OLLAMA_IGPU_ENABLE=1`. Por eso hace falta esta variable
   (`OLLAMA_VULKAN` solo no basta). En PowerShell:
   ```powershell
   setx OLLAMA_VULKAN 1
   setx OLLAMA_IGPU_ENABLE 1
   ```
   Cierra Ollama desde el ícono de la bandeja y vuelve a abrirlo.
   > **Soporte no oficial.** La documentación de Ollama (docs.ollama.com/gpu) no menciona
   > `OLLAMA_IGPU_ENABLE` ni lista GPU integradas para Windows. En nuestra laptop (Ryzen AI 7 PRO 350,
   > Radeon 860M) funcionó, pero puede cambiar entre versiones de Ollama o dar respuestas raras en otros
   > equipos. Si pasa, quita la variable y se usa la CPU: `reg delete HKCU\Environment /v OLLAMA_IGPU_ENABLE /f`.
   > Medido con `qwen3:8b` en esa laptop: CPU ≈ 10.8 tokens/s, GPU integrada ≈ 14.5 tokens/s.
3. Descarga el modelo (≈5 GB) y pruébalo:
   ```powershell
   ollama pull qwen3:8b
   ollama run qwen3:8b "Resume en una frase: la paciente tiene tos desde ayer."
   ```
   Si la laptop tiene 16 GB de RAM o menos y va lento, usa `ollama pull llama3.2:3b` y cambia
   `OLLAMA_MODEL` en `.env`.
4. Comprueba que usa la GPU: `ollama ps` (columna PROCESSOR debe mencionar GPU). Si dice 100% CPU,
   revisa el paso 2 y el log; funciona igual, solo más lento.

### A5. Cloudflared (enlace público)
En PowerShell:
```powershell
winget install --id Cloudflare.cloudflared
```
Cierra y abre PowerShell y comprueba: `cloudflared --version`.

---

## Parte B · Ubuntu (WSL)
Abre la terminal "Ubuntu". Todo lo siguiente se escribe ahí.

### B1. Herramientas básicas
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl unzip build-essential python3-pip python3-venv
```

### B2. Node.js 22 (para el frontend)
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
node --version      # v22.x
```

### B3. Python con uv (entornos rápidos)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv python install 3.12
```

### B4. GitHub CLI
```bash
sudo apt install -y gh
git config --global user.name  "Tu Nombre"
git config --global user.email "tu-correo@ejemplo.com"
git config --global init.defaultBranch main
gh auth login          # GitHub.com → HTTPS → Login with a web browser
```

### B5. Claude Code
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
Abre una terminal nueva y comprueba con `claude --version`. La primera vez que ejecutes `claude` te pedirá
iniciar sesión con tu cuenta. Claude Code se instala y se usa **dentro de Ubuntu (WSL)**, no en PowerShell.

### B6. Comprobar Docker desde Ubuntu
```bash
docker run --rm hello-world
```

---

## Parte C · Proyecto y repositorio público

> **Importante:** trabaja dentro de Linux (`~/proyectos`), no en `/mnt/c/...`; es mucho más rápido.

### C1. Descomprimir el kit
Copia `vela-starter.zip` a Descargas de Windows y en Ubuntu:
```bash
mkdir -p ~/proyectos && cd ~/proyectos
unzip /mnt/c/Users/<TU_USUARIO_WINDOWS>/Downloads/vela-starter.zip
cd vela
```

### C2. Crear la configuración local (no se sube a GitHub)
```bash
cp .env.example .env
nano .env        # cambia las contraseñas y JWT_SECRET; guarda con Ctrl+O, Enter, Ctrl+X
```
Para generar un secreto: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.

### C3. Levantar la base de datos y verificar
```bash
docker compose up -d db
docker compose logs -f db        # espera "database system is ready to accept connections"; sal con Ctrl+C
python3 scripts/verify_db.py     # todo debe decir "ok"
```
Si cambias algo en la semilla y quieres recargar desde cero: `docker compose down -v && docker compose up -d db`.

### C4. Descargar datos oficiales (opcional, recomendado)
```bash
python3 scripts/download_reference_data.py --year 2025
```
Lo que no se pueda descargar se indica con instrucciones manuales; el sistema funciona igual con los datos calibrados.

### C5. Crear el repositorio público y subir todo
```bash
git init
git add .
git status                      # revisa: NO debe aparecer .env
git commit -m "Add starter kit: specs, synthetic data, SQL and config"
gh repo create vela --public --source=. --remote=origin --push \
  --description "Enlaza · cuidado coordinado — prototipo académico UNRC (datos sintéticos)"
```
Agrega a tus compañeros: GitHub → repositorio → Settings → Collaborators → Add people.
Cada compañero: `gh auth login` y luego `gh repo clone <tu-usuario>/vela ~/proyectos/vela`.

**Regla de equipo:** cada quien trabaja en una rama (`git switch -c voz`, `simulacion`, `tableros`, `operacion`)
y une con Pull Request; `main` siempre debe funcionar.

### C6. Empezar con Claude Code
```bash
cd ~/proyectos/vela
claude
```
Primer mensaje sugerido:
> Lee CLAUDE.md y docs/spec/00_indice.md. Empieza por el paso 1 del "Work order" y avísame cuando
> `scripts/verify_db.py` pase y la API responda en http://localhost:8080/api/health.

---

## Parte D · Enlace público con Cloudflare

Cuando la app ya responda en http://localhost:8080 (después del paso 4 del plan):

En **PowerShell** (o en Ubuntu si instalaste cloudflared ahí):
```powershell
cloudflared tunnel --url http://localhost:8080
```
Aparecerá un enlace del tipo `https://palabras-aleatorias.trycloudflare.com`. Ese es el enlace público;
compártelo o conviértelo en QR. No hace falta tocar `.env` ni reiniciar nada: la API detecta sola que el
visitante llegó por https (cabecera `Cf-Visitor` de Cloudflare) y marca la cookie de sesión como `Secure`.

**Comprobar el tiempo real por el enlace público** (criterio A4):
1. En la laptop, abre el enlace e inicia sesión como `coordinacion.a@ejemplo.test` → `/tablero`.
   Arriba a la derecha debe decir "● En vivo".
2. En un celular **con datos móviles**, abre el mismo enlace e inicia sesión como `fam-0001@ejemplo.test`.
3. En el celular toca "Solicitar servicio". En menos de 2 s, sin recargar, la solicitud aparece en la cola del
   tablero de la laptop (y en Aprobaciones, porque ese paciente es de prioridad alta).
4. Apaga el wifi de la laptop unos segundos (no cierres el túnel: al reabrirlo cambia el enlace): el tablero
   muestra "Reconectando…" y vuelve solo a "En vivo".

Si cambias `infra/Caddyfile`, recárgalo con `docker compose restart proxy` (`up -d` no lo recarga, porque
el archivo está montado y el contenedor no cambia).

Qué saber del túnel rápido:
- No necesita cuenta ni abrir puertos del módem.
- El enlace **cambia cada vez** que lo reinicias, y funciona mientras la ventana siga abierta y la laptop
  encendida y con internet.
- Límite de 200 peticiones simultáneas y no admite Server-Sent Events (por eso usamos WebSockets).
- Es para pruebas, sin garantía de disponibilidad.

### Enlace fijo: https://enlaza.zenthinks.com (túnel con nombre)

Desde el 25 nov 2026 la app tiene una dirección fija y un QR que no cambia. Funciona desde cualquier dispositivo
**mientras la laptop esté encendida, con sesión iniciada en Windows y con internet**.

| Pieza | Cómo quedó |
|---|---|
| Túnel `enlaza` | creado en el panel de Cloudflare (one.dash.cloudflare.com → Networks → Tunnels), ruta pública `enlaza.zenthinks.com` → `http://127.0.0.1:8080`. La raíz `zenthinks.com` no apunta a nada |
| Servicio de Windows `cloudflared` | instalado con `cloudflared.exe service install <token>` (PowerShell como administrador); arranque automático al prender la laptop |
| Docker Desktop | Settings → General → «Start Docker Desktop when you sign in» activado; los servicios del compose tienen `restart: unless-stopped` y vuelven solos |
| Ollama | arranca al iniciar sesión (acceso directo en la carpeta Inicio de Windows) |
| Reloj de WSL | tarea de Windows «Enlaza - reloj de WSL» (`scripts/windows/install_clock_task.ps1`): copia la hora de Windows a WSL al iniciar sesión, al despertar y cada 30 min |
| QR | `uv run scripts/make_qr.py` → `docs/privado/qr_enlaza.png` y `qr_enlaza_diapositiva.png` (Git los ignora) |

Por qué con token desde el panel y no con `cloudflared tunnel login/create/route`: el servicio de Windows corre
como cuenta del sistema; con el método de archivos necesita `config.yml` y las credenciales en
`C:\Windows\System32\config\systemprofile\.cloudflared`, que es donde más suele fallar. Con token todo va dentro del
servicio, y la regla «dirección → puerto 8080» vive en Cloudflare (se cambia sin tocar la laptop).

**El token es una llave**: no se sube a Git ni se comparte. Si se filtra, en el panel: túnel `enlaza` → *Refresh token*,
y volver a instalar el servicio (`cloudflared.exe service uninstall` y `service install <token nuevo>`).

**Comprobar que todo está arriba** (en Ubuntu, desde la carpeta del proyecto):
```bash
bash scripts/enlaza.sh estado                 # túnel, Docker, Ollama, localhost, dirección pública y reloj
uv run scripts/check_public_url.py            # prueba completa por https (crea una solicitud: luego reset_demo.py)
```
En PowerShell: `Get-Service cloudflared` debe decir `Running`. En el panel de Cloudflare el túnel aparece como **HEALTHY**.

**Encender y apagar a mano:**
```bash
bash scripts/enlaza.sh encender   # Docker, Ollama y el túnel (Windows pide permiso de administrador)
bash scripts/enlaza.sh apagar     # todo abajo; al reiniciar la laptop vuelve a encender solo
```
Solo el túnel, en PowerShell como administrador: `Stop-Service cloudflared` / `Start-Service cloudflared`. Para que no
arranque al prender la laptop: `Set-Service cloudflared -StartupType Manual` (y `Automatic` para regresarlo).

**Si la dirección fija falla, el respaldo es el túnel rápido** (no depende del panel ni del dominio):
```bash
bash scripts/enlaza.sh rapido                                    # o en PowerShell: cloudflared tunnel --url http://localhost:8080
uv run scripts/make_qr.py https://palabras-al-azar.trycloudflare.com   # QR de respaldo → docs/privado/qr_rapido*.png
```

### Día de la defensa
1. Laptop conectada a la corriente; desactiva suspensión (Configuración → Sistema → Energía → "Nunca").
2. 1 h antes: Docker, Ollama y el túnel ya arrancan solos al iniciar sesión en Windows. Comprobar con
   `bash scripts/enlaza.sh estado` (todo arriba, `https://enlaza.zenthinks.com` responde y el reloj con diferencia
   0 o 1 s) y `uv run scripts/check_public_url.py` (12 de 12). Cargar el modelo: `ollama run qwen3:8b "hola"`.
   El QR fijo ya está en `docs/privado/qr_enlaza_diapositiva.png`. Si la dirección fija no responde: «Si falla el
   enlace fijo» abajo.
3. **Base de la demo desde cero (el día anterior, antes del ensayo general).** Las pruebas automáticas usan su
   propia base (`vela_test`), así que ya no escriben en la bitácora de la demo. Pero la base de la demo todavía
   guarda la bitácora de las semanas de desarrollo. Para que la bitácora de `/privacidad` muestre solo el uso
   real de los ensayos y de la defensa, recrea la base desde la semilla:
   ```bash
   docker compose stop api worker web proxy db
   docker compose rm -f db
   docker volume rm vela_pgdata        # SOLO la base de la demo; el modelo de Whisper (whisper-cache) se queda
   docker compose up -d                # carga la semilla y corre las migraciones (1–2 min)
   python scripts/verify_db.py         # debe decir "Todo correcto"
   python scripts/create_test_db.py    # la base de pruebas vive en el mismo volumen: hay que crearla otra vez
   docker compose exec api pytest -q   # opcional: confirma que todo pasa (en vela_test, no en la demo)
   ```
   Después sigue con el paso 4 (fechas vivas). Usuarios y contraseña de demostración no cambian.
4. **Fechas vivas.** El historial sintético (solicitudes, asignaciones, consentimientos y lecturas de aire)
   termina el 19–20 de noviembre. Para que tableros y simulación muestren un historial que termina "ayer":
   ```bash
   python scripts/rebase_dates.py --dry-run   # muestra qué movería, sin guardar
   python scripts/rebase_dates.py             # lo aplica
   python scripts/verify_db.py                # debe seguir en "Todo correcto"
   ```
   Mueve todo por semanas completas (un lunes sigue siendo lunes, porque el tráfico y las visitas dependen
   del día), así que el historial termina entre 0 y 6 días antes de ayer. Se puede correr cuantas veces
   haga falta: si ya está al día, no hace nada. No toca la bitácora (`audit_log`) ni las visitas de hoy o
   futuras. Para ensayar el día de la defensa sin cambiar nada: `--today 2026-12-01 --dry-run`.
5. **Operación limpia.** Borra lo que dejaron los ensayos: reportes de voz, alertas, avisos a familias,
   escenarios de demostración (contingencias, tráfico, cuidadores fuera de servicio) y las visitas en vivo
   pendientes, solicitudes ARCO, y regresa a la semilla los consentimientos que se revocaron en un ensayo.
   **La semilla no se toca** y la bitácora (`audit_log`) tampoco: el reinicio queda registrado ahí.
   ```bash
   python scripts/reset_demo.py --dry-run   # muestra cuántas filas borraría, sin guardar
   python scripts/reset_demo.py             # lo aplica
   python scripts/verify_db.py              # debe seguir en "Todo correcto"
   ```
   En el siguiente minuto el worker vuelve a crear las visitas de hoy de los planes de cuidado, asignadas
   automáticamente. Córrelo **después** del ensayo general y **antes** de abrir el túnel.
6. Probar el enlace desde un celular con datos móviles (no con el wifi de la escuela), con la prueba de
   tiempo real de arriba.
7. Respaldo: la demo funciona en `http://localhost:8080` sin internet (salvo el enlace público) y hay un video grabado.

**Si falla el enlace fijo** (`https://enlaza.zenthinks.com` da error):
| Qué se ve | Qué hacer |
|---|---|
| Error 502 de Cloudflare | la app no corre: `docker compose ps`, `docker compose up -d` |
| Error 1033 (túnel caído) | `bash scripts/enlaza.sh encender`; en el panel el túnel debe volver a **HEALTHY** |
| No se arregla en 2 minutos | túnel rápido: `bash scripts/enlaza.sh rapido`, QR nuevo con `make_qr.py <enlace>` y proyectarlo |
| Sin internet en la escuela | seguir en `http://localhost:8080` en el proyector |

**Apagar todo al terminar:** `bash scripts/backup_db.sh defensa` y `bash scripts/enlaza.sh apagar`.

## Problemas comunes
| Síntoma | Solución |
|---|---|
| `docker: command not found` en Ubuntu | Docker Desktop → Settings → Resources → WSL integration → activar Ubuntu |
| La API no alcanza a Ollama | En PowerShell `setx OLLAMA_HOST 0.0.0.0:11434`, reinicia Ollama y permite el acceso en el firewall solo para redes privadas |
| `verify_db.py` falla en conteos | `docker compose down -v` y volver a `up -d db` (la carga solo corre con el volumen vacío) |
| El enlace de Cloudflare da error 502 | La app no está corriendo en el puerto 8080: `docker compose ps` |
| `enlaza.zenthinks.com` da error 1033 | El servicio del túnel no corre: `bash scripts/enlaza.sh estado` y `encender`; respaldo `bash scripts/enlaza.sh rapido` |
| El tablero se queda en "Reconectando…" | `curl localhost:8080/api/health` debe decir `"realtime":"ok"`; si dice `reconnecting`, revisa `docker compose logs api` y que `db` esté arriba |
| Te saca la sesión segundos después de entrar | El reloj de WSL2 se atrasó (sobre todo al despertar de la suspensión); la API tolera 60 s. La tarea «Enlaza - reloj de WSL» lo corrige sola; a mano: `bash scripts/enlaza.sh reloj`. Si sigue: en PowerShell `wsl --shutdown` y vuelve a abrir Ubuntu |
| Todo va lento | Cierra el navegador con muchas pestañas; usa el modelo `llama3.2:3b` |
