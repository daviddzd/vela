# Registers the Windows scheduled task "Enlaza - reloj de WSL" for the current user (no admin needed).
#
# Why: after the laptop sleeps, the clock of the WSL2 virtual machine can fall behind Windows. The API then sees
# session cookies "from the future" and answers 401 ("Inicia sesión para continuar"). All WSL2 distros and the
# Docker Desktop containers share ONE kernel clock, so copying the Windows time into Ubuntu fixes all of them.
#
# The task copies the Windows time (which Windows keeps in sync by itself) into WSL:
#   - when the user signs in,
#   - when the laptop wakes up (System log, Power-Troubleshooter event 1),
#   - and every 30 minutes, just in case.
# It runs hidden (conhost --headless) and only touches the clock.
#
#   powershell -ExecutionPolicy Bypass -File install_clock_task.ps1            (install or update)
#   powershell -ExecutionPolicy Bypass -File install_clock_task.ps1 -Remove    (uninstall)
param([string]$Distro = "Ubuntu-24.04", [switch]$Remove)

$name = "Enlaza - reloj de WSL"
if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Tarea eliminada: $name"
    exit 0
}

$command = '$e=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); wsl.exe -d ' + $Distro + ' -u root -- date -u -s "@$e"'
$action = New-ScheduledTaskAction -Execute "conhost.exe" `
    -Argument "--headless powershell.exe -NoProfile -WindowStyle Hidden -Command `"$command`""

$atLogon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$every30 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 30)
$eventClass = Get-CimClass -ClassName MSFT_TaskEventTrigger -Namespace Root/Microsoft/Windows/TaskScheduler
$onWake = New-CimInstance -CimClass $eventClass -ClientOnly
$onWake.Enabled = $true
$onWake.Subscription = '<QueryList><Query Id="0" Path="System"><Select Path="System">' +
    "*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]" +
    '</Select></Query></QueryList>'
$onWake.Delay = "PT20S"   # give the network and WSL a moment after waking up

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $name -Action $action -Trigger @($atLogon, $every30, $onWake) -Settings $settings `
    -Principal $principal -Description "Copia la hora de Windows a WSL ($Distro) al iniciar sesion, al despertar y cada 30 min (Enlaza)." `
    -Force | Out-Null
Write-Output "Tarea registrada: $name"
