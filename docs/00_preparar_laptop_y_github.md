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
  --description "Vela · cuidado coordinado — prototipo académico UNRC (datos sintéticos)"
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
compártelo o conviértelo en QR. Copia el enlace en `PUBLIC_BASE_URL` del `.env` y reinicia la API
(`docker compose restart api`).

Qué saber del túnel rápido:
- No necesita cuenta ni abrir puertos del módem.
- El enlace **cambia cada vez** que lo reinicias, y funciona mientras la ventana siga abierta y la laptop
  encendida y con internet.
- Límite de 200 peticiones simultáneas y no admite Server-Sent Events (por eso usamos WebSockets).
- Es para pruebas, sin garantía de disponibilidad.

**Enlace fijo (opcional):** con una cuenta gratuita de Cloudflare y un dominio propio se crea un túnel con
nombre (`cloudflared tunnel login`, `cloudflared tunnel create vela`, `cloudflared tunnel route dns vela demo.tudominio.mx`)
y el enlace ya no cambia.

### Día de la defensa
1. Laptop conectada a la corriente; desactiva suspensión (Configuración → Sistema → Energía → "Nunca").
2. 1 h antes: abrir Docker Desktop, `docker compose up -d`, abrir Ollama, `ollama run qwen3:8b "hola"` para
   cargar el modelo, abrir el túnel y generar el QR.
3. Probar el enlace desde un celular con datos móviles (no con el wifi de la escuela).
4. Respaldo: la demo funciona en `http://localhost:8080` sin internet (salvo el enlace público) y hay un video grabado.

## Problemas comunes
| Síntoma | Solución |
|---|---|
| `docker: command not found` en Ubuntu | Docker Desktop → Settings → Resources → WSL integration → activar Ubuntu |
| La API no alcanza a Ollama | En PowerShell `setx OLLAMA_HOST 0.0.0.0:11434`, reinicia Ollama y permite el acceso en el firewall solo para redes privadas |
| `verify_db.py` falla en conteos | `docker compose down -v` y volver a `up -d db` (la carga solo corre con el volumen vacío) |
| El enlace de Cloudflare da error 502 | La app no está corriendo en el puerto 8080: `docker compose ps` |
| Todo va lento | Cierra el navegador con muchas pestañas; usa el modelo `llama3.2:3b` |
