#!/usr/bin/env bash
# Day-of-defense operations, from Ubuntu (WSL). Output in Spanish because the team reads it.
#
#   bash scripts/enlaza.sh estado      # what is running: tunnel (connected to Cloudflare?), Docker, Ollama, addresses, clock
#   bash scripts/enlaza.sh encender    # start everything
#   bash scripts/enlaza.sh apagar      # stop everything (the tunnel service comes back on the next boot)
#   bash scripts/enlaza.sh reconectar  # restart the tunnel service and wait until it is connected (the error 1033)
#   bash scripts/enlaza.sh rapido      # backup: quick tunnel with a random https://….trycloudflare.com link
#   bash scripts/enlaza.sh reloj       # copy the Windows time into WSL now (the 401 after sleeping)
#
# The named tunnel "enlaza" runs as the Windows service "cloudflared" (installed with a token from the Cloudflare
# panel) and serves https://enlaza.zenthinks.com → http://localhost:8080. scripts/windows/configure_tunnel_service.ps1
# (once, as administrator) makes it use HTTP/2, fixes its status port 127.0.0.1:20241 and lets this user restart it;
# the tasks "Enlaza - túnel" restart it when the network changes or it is disconnected (install_tunnel_task.ps1).
set -uo pipefail
cd "$(dirname "$0")/.."

PUBLIC_URL="${PUBLIC_URL:-https://enlaza.zenthinks.com}"
DISTRO="${WSL_DISTRO_NAME:-Ubuntu-24.04}"

ps() { powershell.exe -NoProfile -Command "$1" 2>&1 | tr -d '\r'; }
admin() {   # run a PowerShell command elevated (Windows shows the admin permission prompt)
  ps "Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList '-NoProfile','-Command','$1'"
}
service() { # Start/Stop/Restart-Service cloudflared: without admin if this user has the right, otherwise elevated
  ps "try { $1-Service cloudflared -ErrorAction Stop; 'ok' } catch { 'denied' }" | grep -q '^ok' && return
  echo "(sin permiso de usuario: Windows pedirá permiso de administrador)"; admin "$1-Service cloudflared"
}
# Connections between cloudflared and Cloudflare, from its local status page (0 = not connected).
ready() { ps "try { (Invoke-RestMethod -TimeoutSec 5 http://127.0.0.1:20241/ready).readyConnections } catch { 0 }" | tail -1; }
wait_ready() {
  for i in $(seq 1 45); do n=$(ready); [ "${n:-0}" -gt 0 ] 2>/dev/null && { echo "Túnel CONECTADO con Cloudflare en $i s ($n conexiones)."; return 0; }; sleep 1; done
  echo "El túnel NO se conectó en 45 s: revisa el internet; plan B: bash scripts/enlaza.sh rapido"; return 1
}
health() { curl -sS -m 10 "$1/api/health" 2>&1 | head -c 200; echo; }

case "${1:-estado}" in
  estado)
    echo "== Túnel (servicio de Windows «cloudflared»)"
    ps "Get-Service cloudflared -ErrorAction SilentlyContinue | ForEach-Object { 'Servicio: ' + \$_.Status + ' - arranque: ' + \$_.StartType }; if (-not (Get-Service cloudflared -ErrorAction SilentlyContinue)) { 'NO está instalado' }"
    n=$(ready)
    if [ "${n:-0}" -gt 0 ] 2>/dev/null; then echo "Conexión con Cloudflare: CONECTADO ($n conexiones)"
    else echo "Conexión con Cloudflare: NO CONECTADO → bash scripts/enlaza.sh reconectar (o PowerShell como administrador: Restart-Service cloudflared)"; fi
    cmd=$(ps "(Get-CimInstance Win32_Service -Filter \"Name='cloudflared'\").PathName")
    if echo "$cmd" | grep -q -- '--protocol http2'; then echo "Protocolo: http2 (funciona en hotspots)"
    else echo "Protocolo: automático/QUIC → falta scripts/windows/configure_tunnel_service.ps1 como administrador"; fi
    # PowerShell only returns plain data here (its console mangles accents); the Spanish text is written by bash.
    tasks=$(ps "(Get-ScheduledTask -TaskName 'Enlaza - t*nel*' -ErrorAction SilentlyContinue | ForEach-Object { \$_.State }) -join ' '")
    if [ -n "$tasks" ]; then echo "Reconexión automática: tareas «Enlaza - túnel» y «(red)»: $tasks"
    else echo "Reconexión automática: NO instalada → powershell.exe -ExecutionPolicy Bypass -File \"$(wslpath -w scripts/windows/install_tunnel_task.ps1)\""; fi
    log="$(wslpath "$(ps '$env:LOCALAPPDATA' | tail -1)")/Enlaza/tunel.log"
    echo "Último reinicio automático: $(tail -1 "$log" 2>/dev/null | sed 's/^\xEF\xBB\xBF//' | grep . || echo 'ninguno')"
    echo "== Docker"
    docker compose ps --format 'table {{.Service}}\t{{.Status}}' 2>&1
    echo "== Archivos dentro de los contenedores (reglas de emergencia, configuración, Caddyfile)"
    if docker compose exec -T api test -s /config/emergency_rules.yaml 2>/dev/null && docker compose exec -T worker test -s /config/simulation.yaml 2>/dev/null \
       && docker compose exec -T proxy test -s /etc/caddy/Caddyfile 2>/dev/null; then echo "bien"; else echo "FALTAN: bash scripts/autostart.sh"; fi
    echo "Último arranque: $(tail -1 "$HOME/.local/state/enlaza/arranque.log" 2>/dev/null || echo 'sin registro')"
    echo "== Ollama"
    ps "try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://127.0.0.1:11434/api/version).Content } catch { 'Ollama NO responde' }"
    echo "== App en la laptop (http://localhost:8080)"
    health http://localhost:8080
    echo "== Dirección pública ($PUBLIC_URL)"
    health "$PUBLIC_URL"
    echo "== Reloj (WSL contra Windows)"
    w=$(ps "[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()"); l=$(date -u +%s)
    echo "diferencia: $((l - w)) s (debe ser 0 o 1; si es grande: bash scripts/enlaza.sh reloj)"
    ;;
  encender)
    echo "Encendiendo Docker (servicios de la app)…"; bash scripts/autostart.sh | tail -2
    echo "Encendiendo Ollama…"
    ps "if (-not (Get-Process 'ollama app' -ErrorAction SilentlyContinue)) { Start-Process \"\$env:LOCALAPPDATA\\Programs\\Ollama\\ollama app.exe\" }"
    echo "Encendiendo el túnel…"; service Start; wait_ready
    "$0" estado
    ;;
  apagar)
    echo "Apagando el túnel…"; service Stop
    echo "Apagando la app…"; docker compose stop
    echo "Cerrando Ollama…"; ps "Get-Process 'ollama app','ollama' -ErrorAction SilentlyContinue | Stop-Process"
    echo "Listo. Al reiniciar la laptop todo vuelve a encender solo."
    ;;
  reconectar)
    echo "Reiniciando el túnel…"; service Restart; wait_ready
    health "$PUBLIC_URL"
    ;;
  rapido)
    echo "Túnel rápido (respaldo): copia el enlace https://….trycloudflare.com que aparece abajo. Ctrl+C lo cierra."
    "/mnt/c/Program Files (x86)/cloudflared/cloudflared.exe" tunnel --protocol http2 --metrics 127.0.0.1:20249 --url http://localhost:8080
    ;;
  reloj)
    e=$(ps "[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()")
    wsl.exe -d "$DISTRO" -u root -- date -u -s "@$e" | tr -d '\r\0'
    ;;
  *)
    sed -n 2,10p "$0"; exit 2 ;;
esac
