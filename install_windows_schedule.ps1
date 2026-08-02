param(
    [string]$Times = $env:POST_TIMES,
    [string]$TaskPrefix = 'AI Social Bot Publish'
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $ProjectRoot 'run_scheduled_publish.ps1'

if (-not $Times) {
    $EnvPath = Join-Path $ProjectRoot '.env'
    if (Test-Path $EnvPath) {
        $PostTimesLine = Get-Content $EnvPath | Where-Object { $_ -match '^POST_TIMES=' } | Select-Object -First 1
        if ($PostTimesLine) {
            $Times = $PostTimesLine.Substring('POST_TIMES='.Length).Trim()
        }
    }
}

if (-not $Times) {
    $Times = '09:00,11:00,13:00,15:00,17:00'
}

$TimeList = $Times.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }

foreach ($Time in $TimeList) {
    if ($Time -notmatch '^\d{1,2}:\d{2}$') {
        throw "Invalid time '$Time'. Use HH:MM format."
    }

    $TaskName = "$TaskPrefix $($Time.Replace(':', ''))"
    $Action = New-ScheduledTaskAction `
        -Execute 'powershell.exe' `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`""
    $Trigger = New-ScheduledTaskTrigger -Daily -At $Time
    $Settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -WakeToRun `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Publishes one AI Social Bot quote post." `
        -Force | Out-Null

    Write-Host "Registered $TaskName at $Time"
}
