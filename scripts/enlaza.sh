#!/usr/bin/env bash
# Day-of-defense operations, from Ubuntu (WSL). Output in Spanish because the team reads it.
#
#   bash scripts/enlaza.sh estado     # what is running: tunnel service, Docker, Ollama, local and public address, clock
#   bash scripts/enlaza.sh encender   # start everything (asks for admin permission for the tunnel service)
#   bash scripts/enlaza.sh apagar     # stop everything (the tunnel service comes back on the next boot)
#   bash scripts/enlaza.sh rapido     # backup: quick tunnel with a random https://….trycloudflare.com link
#   bash scripts/enlaza.sh reloj      # copy the Windows time into WSL now (the 401 after sleeping)
#
# The named tunnel "enlaza" runs as the Windows service "cloudflared" (installed with a token from the Cloudflare
# panel) and serves https://enlaza.zenthinks.com → http://localhost:8080.
set -uo pipefail
cd "$(dirname "$0")/.."

PUBLIC_URL="${PUBLIC_URL:-https://enlaza.zenthinks.com}"
DISTRO="${WSL_DISTRO_NAME:-Ubuntu-24.04}"

ps() { powershell.exe -NoProfile -Command "$1" 2>&1 | tr -d '\r'; }
admin() {   # run a PowerShell command elevated (Windows shows the admin permission prompt)
  ps "Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList '-NoProfile','-Command','$1'"
}
health() { curl -sS -m 10 "$1/api/health" 2>&1 | head -c 200; echo; }

case "${1:-estado}" in
  estado)
    echo "== Túnel (servicio de Windows «cloudflared»)"
    ps "Get-Service cloudflared -ErrorAction SilentlyContinue | ForEach-Object { 'Estado: ' + \$_.Status + ' - arranque: ' + \$_.StartType }; if (-not (Get-Service cloudflared -ErrorAction SilentlyContinue)) { 'NO está instalado' }"
    echo "== Docker"
    docker compose ps --format 'table {{.Service}}\t{{.Status}}' 2>&1
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
    echo "Encendiendo Docker (servicios de la app)…"; docker compose up -d
    echo "Encendiendo Ollama…"
    ps "if (-not (Get-Process 'ollama app' -ErrorAction SilentlyContinue)) { Start-Process \"\$env:LOCALAPPDATA\\Programs\\Ollama\\ollama app.exe\" }"
    echo "Encendiendo el túnel (Windows pedirá permiso de administrador)…"; admin "Start-Service cloudflared"
    sleep 5; "$0" estado
    ;;
  apagar)
    echo "Apagando el túnel (Windows pedirá permiso de administrador)…"; admin "Stop-Service cloudflared"
    echo "Apagando la app…"; docker compose stop
    echo "Cerrando Ollama…"; ps "Get-Process 'ollama app','ollama' -ErrorAction SilentlyContinue | Stop-Process"
    echo "Listo. Al reiniciar la laptop todo vuelve a encender solo."
    ;;
  rapido)
    echo "Túnel rápido (respaldo): copia el enlace https://….trycloudflare.com que aparece abajo. Ctrl+C lo cierra."
    "/mnt/c/Program Files (x86)/cloudflared/cloudflared.exe" tunnel --url http://localhost:8080
    ;;
  reloj)
    e=$(ps "[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()")
    wsl.exe -d "$DISTRO" -u root -- date -u -s "@$e" | tr -d '\r\0'
    ;;
  *)
    sed -n 2,9p "$0"; exit 2 ;;
esac
