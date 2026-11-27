# Registers the Windows scheduled tasks "Enlaza - túnel (red)" and "Enlaza - túnel" for the current user
# (no admin needed).
#
# Why: when the laptop changes network (wifi -> phone hotspot) or wakes up, the tunnel service keeps running but its
# connections to Cloudflare die, and https://enlaza.zenthinks.com shows error 1033 until someone restarts it.
# Both run tunnel_watchdog.ps1 (copied to %LOCALAPPDATA%\Enlaza so it works even before Ubuntu starts):
#   "(red)": when a network connects (NetworkProfile event 10000)    -> restart cloudflared,
#            when the laptop wakes up (Power-Troubleshooter event 1) -> restart cloudflared;
#   the other: every 2 minutes and at sign-in                       -> restart only if the tunnel is not connected.
# Requires configure_tunnel_service.ps1 once (as administrator), which lets this user restart that one service.
#
#   powershell -ExecutionPolicy Bypass -File install_tunnel_task.ps1            (install or update)
#   powershell -ExecutionPolicy Bypass -File install_tunnel_task.ps1 -Remove    (uninstall)
param([string]$PublicUrl = "https://enlaza.zenthinks.com", [switch]$Remove)

$name = "Enlaza - túnel"
if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Tarea eliminada: $name"
    exit 0
}

$dir = Join-Path $env:LOCALAPPDATA "Enlaza"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$script = Join-Path $dir "tunnel_watchdog.ps1"
Copy-Item -Force (Join-Path $PSScriptRoot "tunnel_watchdog.ps1") $script

function Action([string]$extra) {
    New-ScheduledTaskAction -Execute "conhost.exe" -Argument ("--headless powershell.exe -NoProfile -WindowStyle Hidden " +
        "-ExecutionPolicy Bypass -File `"$script`" -PublicUrl $PublicUrl $extra")
}
function EventTrigger([string]$log, [string]$provider, [int]$id, [string]$delay) {
    $class = Get-CimClass -ClassName MSFT_TaskEventTrigger -Namespace Root/Microsoft/Windows/TaskScheduler
    $t = New-CimInstance -CimClass $class -ClientOnly
    $t.Enabled = $true
    $t.Subscription = "<QueryList><Query Id=`"0`" Path=`"$log`"><Select Path=`"$log`">" +
        "*[System[Provider[@Name='$provider'] and EventID=$id]]</Select></Query></QueryList>"
    $t.Delay = $delay
    return $t
}

# Two tasks, because the action differs: "(red)" restarts unconditionally on network/wake events; the other one
# only checks. If both fire together, the check simply finds the tunnel already reconnecting or connected.
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

$onNetwork = EventTrigger "Microsoft-Windows-NetworkProfile/Operational" "Microsoft-Windows-NetworkProfile" 10000 "PT5S"
$onWake = EventTrigger "System" "Microsoft-Windows-Power-Troubleshooter" 1 "PT10S"
Register-ScheduledTask -TaskName "$name (red)" -Action (Action "-Restart") -Trigger @($onNetwork, $onWake) `
    -Settings $settings -Principal $principal -Force `
    -Description "Reinicia el servicio cloudflared al cambiar de red o al despertar (Enlaza)." | Out-Null

$every2 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 2)
$atLogon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
Register-ScheduledTask -TaskName $name -Action (Action "") -Trigger @($every2, $atLogon) `
    -Settings $settings -Principal $principal -Force `
    -Description "Cada 2 min revisa que el tunel este conectado con Cloudflare; si no, reinicia cloudflared (Enlaza)." | Out-Null
Write-Output "Tareas registradas: $name y $name (red). Registro: $dir\tunel.log"
