# Prepare a task for the currently signed-in Windows user. -Install enables it.
param(
    [string]$At = '08:00',
    [string]$Python = 'python',
    [switch]$Install
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pythonPath = (Get-Command $Python -CommandType Application -ErrorAction Stop).Source
$job = Join-Path $PSScriptRoot 'daily.py'
$when = [datetime]::ParseExact($At, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument ('"{0}"' -f $job) -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At $when
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::FromHours(1))
$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'AgentOS Lite: collect, filter, then write a daily report'
$output = Join-Path $root 'outputs\schedule\AgentOSLiteDaily.xml'
New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
Export-ScheduledTask -InputObject $task | Set-Content -Path $output -Encoding Unicode
Write-Host "Prepared: $output"
if ($Install) {
    # No -Force: never replace an existing task silently. No password is stored.
    Register-ScheduledTask -TaskName 'AgentOSLiteDaily' -InputObject $task | Out-Null
    Write-Host "Installed AgentOSLiteDaily; next scheduled time $At. No immediate run requested."
} else {
    Write-Host 'Not installed. Add -Install only when you want to enable the task.'
}
