# Registers the Windows scheduled task "Enlaza - arranque" for the current user (no admin needed).
# At sign-in (after 45 s) it runs scripts/autostart.sh inside Ubuntu: waits for Docker Desktop, checks that every
# container sees its files (Docker Desktop may start them before Ubuntu is ready) and restarts the ones that do not.
#
#   powershell -ExecutionPolicy Bypass -File install_startup_task.ps1            (install or update)
#   powershell -ExecutionPolicy Bypass -File install_startup_task.ps1 -Remove    (uninstall)
param([string]$Distro = "Ubuntu-24.04", [string]$Project = "/home/david/proyectos/vela", [switch]$Remove)

$name = "Enlaza - arranque"
if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Tarea eliminada: $name"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "conhost.exe" `
    -Argument "--headless wsl.exe -d $Distro -- bash $Project/scripts/autostart.sh"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$trigger.Delay = "PT45S"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Al iniciar sesion: espera a Docker, revisa los montajes de cada contenedor y reinicia los vacios (Enlaza)." `
    -Force | Out-Null
Write-Output "Tarea registrada: $name"
