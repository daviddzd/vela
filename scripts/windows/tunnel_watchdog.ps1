# Keeps the named tunnel connected (run by the scheduled task "Enlaza - túnel", install_tunnel_task.ps1).
#
#   tunnel_watchdog.ps1 -Restart    the network changed or the laptop woke up: restart cloudflared right away
#                                   (its old connections belong to the previous network and may look alive for minutes)
#   tunnel_watchdog.ps1             periodic check: restart only if the tunnel is NOT connected, meaning
#                                   cloudflared /ready reports 0 connections, or the public address answers
#                                   HTTP 530 (Cloudflare's code for error 1033, "tunnel disconnected").
#
# Restarting works without administrator once configure_tunnel_service.ps1 was run (it lets the user restart
# this one service). Log: %LOCALAPPDATA%\Enlaza\tunel.log (only restarts and problems, last 300 lines).
param([switch]$Restart, [string]$PublicUrl = "https://enlaza.zenthinks.com")

$logDir = Join-Path $env:LOCALAPPDATA "Enlaza"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "tunel.log"
$stamp = Join-Path $logDir "ultimo_reinicio.txt"   # when this script last restarted the tunnel
function Say([string]$msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    $old = @(Get-Content $log -ErrorAction SilentlyContinue | Select-Object -Last 299)
    Set-Content -Path $log -Value ($old + $line) -Encoding UTF8
}

# How many connections cloudflared has with Cloudflare (0 if it does not answer).
function ReadyConnections {
    try { return [int](Invoke-RestMethod -TimeoutSec 5 http://127.0.0.1:20241/ready).readyConnections } catch { return 0 }
}

# HTTP status of the public address; 0 if there is no internet (then restarting would not help).
function PublicStatus {
    try { return [int](Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 "$PublicUrl/api/health").StatusCode }
    catch { if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode } else { return 0 } }
}

$why = $null
if ($Restart) {
    # Windows logs "network connected" more than once per change (seen: two events 5 s apart). If this script
    # restarted cloudflared less than 30 s ago it is already reconnecting on the new network: a second restart only
    # adds a blip. (A normal user cannot read the start time of the SYSTEM process, hence the file.)
    $last = Get-Item $stamp -ErrorAction SilentlyContinue
    if ($last -and ((Get-Date) - $last.LastWriteTime).TotalSeconds -lt 30) { exit 0 }
    $why = "cambió la red o despertó la laptop"
} else {
    $n = ReadyConnections
    if ($n -eq 0) { $why = "0 conexiones con Cloudflare" }
    elseif ((PublicStatus) -eq 530) { $why = "la dirección pública da error 1033 (530)" }
}
if (-not $why) { exit 0 }   # connected: nothing to do, nothing to log

try {
    Set-Content -Path $stamp -Value (Get-Date -Format o)
    Restart-Service cloudflared -ErrorAction Stop
} catch {
    Say "NO se pudo reiniciar ($why): $($_.Exception.Message). Falta correr configure_tunnel_service.ps1 como administrador."
    exit 1
}
for ($i = 1; $i -le 45; $i++) {
    Start-Sleep -Seconds 1
    $n = ReadyConnections
    if ($n -gt 0) { Say "Reiniciado ($why): conectado en $i s, $n conexiones."; exit 0 }
}
Say "Reiniciado ($why): sin conexión después de 45 s (¿hay internet?). Se vuelve a revisar en 2 min."
