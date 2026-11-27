# One-time setup of the Windows service "cloudflared" (the named tunnel behind https://enlaza.zenthinks.com).
# Needs ADMINISTRATOR, once. Run it from PowerShell opened "as administrator":
#
#   powershell -ExecutionPolicy Bypass -File configure_tunnel_service.ps1          (apply; safe to run again)
#   powershell -ExecutionPolicy Bypass -File configure_tunnel_service.ps1 -Undo    (go back to the original setup)
#
# What it changes, and why:
#   1. --protocol http2: the tunnel talks to Cloudflare over TCP 443-style HTTP/2 instead of QUIC (UDP 7844).
#      Phone hotspots and some school networks block or break UDP 7844; that left the tunnel "Running" but
#      disconnected (error 1033 on the public address) after switching the laptop to a hotspot.
#   2. --metrics 127.0.0.1:20241: fixes the local status port, so "bash scripts/enlaza.sh estado" and the watchdog
#      task can ask cloudflared /ready how many connections to Cloudflare it has (0 = disconnected).
#   3. Lets the signed-in user start/stop/restart ONLY this service, so the watchdog task
#      ("Enlaza - túnel", install_tunnel_task.ps1) can restart it without asking for administrator every time.
# The token stays where the installer put it (--token-file); this script never reads or prints it.
param([switch]$Undo, [string]$User = "$env:USERDOMAIN\$env:USERNAME")

$ErrorActionPreference = "Stop"
$svcKey = "HKLM:\SYSTEM\CurrentControlSet\Services\cloudflared"
$flags = "--protocol http2 --metrics 127.0.0.1:20241"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Write-Output "Hay que abrir PowerShell como administrador."; exit 1 }
if (-not (Test-Path $svcKey)) { Write-Output "El servicio cloudflared NO está instalado."; exit 1 }

# --- 1 and 2: command line of the service --------------------------------------------------------------------
$path = (Get-ItemProperty $svcKey).ImagePath
if ($Undo) {
    $new = $path.Replace(" $flags", "")
} elseif ($path -match "--protocol") {
    $new = $path   # already configured
} else {
    $new = $path -replace '\stunnel\s', " tunnel $flags "
}
if ($new -ne $path) { Set-ItemProperty $svcKey -Name ImagePath -Value $new }
Write-Output "Comando del servicio: $new"

# --- 3: service permissions for the user ---------------------------------------------------------------------
# SDDL rights: CC query config, LC query status, SW list dependents, RP start, WP stop, DT pause, LO interrogate,
# CR user control, RC read permissions. Nothing else (the user cannot change or delete the service).
$sid = (New-Object Security.Principal.NTAccount($User)).Translate([Security.Principal.SecurityIdentifier]).Value
$ace = "(A;;CCLCSWRPWPDTLOCRRC;;;$sid)"
$sddl = ((sc.exe sdshow cloudflared) -join "").Trim()
if ($Undo) {
    $newSddl = $sddl.Replace($ace, "")
} elseif ($sddl.Contains($sid)) {
    $newSddl = $sddl
} elseif ($sddl.Contains("S:")) {
    $newSddl = $sddl.Replace("S:", "$ace" + "S:")
} else {
    $newSddl = $sddl + $ace
}
if ($newSddl -ne $sddl) { sc.exe sdset cloudflared $newSddl | Out-Null }
Write-Output "Permiso de reiniciar el túnel para ${User}: $(if ($Undo) { 'quitado' } else { 'sí' })"

# --- Restart and confirm -------------------------------------------------------------------------------------
Restart-Service cloudflared
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try { $r = Invoke-RestMethod -TimeoutSec 3 http://127.0.0.1:20241/ready } catch { $r = $null }
    if ($r -and $r.readyConnections -gt 0) { break }
}
if ($r -and $r.readyConnections -gt 0) {
    Write-Output "Túnel CONECTADO con Cloudflare: $($r.readyConnections) conexiones (en $($i + 1) s)."
} else {
    Write-Output "El túnel todavía no se conecta. Revisa el internet y corre: bash scripts/enlaza.sh estado"
}
