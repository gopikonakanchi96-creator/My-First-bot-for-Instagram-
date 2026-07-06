param(
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutLog = Join-Path $ProjectRoot 'uvicorn.out.log'
$ErrLog = Join-Path $ProjectRoot 'uvicorn.err.log'

$ExistingListener = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($ExistingListener) {
    Write-Host "Bot appears to already be running on http://127.0.0.1:$Port"
    Write-Host "Check status at http://127.0.0.1:$Port/status"
    exit 0
}

Write-Host "Starting bot scheduler on http://127.0.0.1:$Port ..."
Write-Host "Output log: $OutLog"
Write-Host "Error log:  $ErrLog"

$Arguments = @(
    '-m',
    'uvicorn',
    'ai_social_bot.app.main:app',
    '--host',
    '127.0.0.1',
    '--port',
    "$Port"
)

Start-Process `
    -FilePath 'python' `
    -ArgumentList $Arguments `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -WindowStyle Hidden

$Status = $null
for ($Attempt = 1; $Attempt -le 10; $Attempt++) {
    Start-Sleep -Seconds 2
    try {
        $Status = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/status" -TimeoutSec 10
        break
    } catch {
        if ($Attempt -eq 10) {
            Write-Host "Bot process was started, but status check failed. Check the log files above."
            exit 1
        }
    }
}

Write-Host "Bot started. Scheduler running: $($Status.scheduler.running)"
Write-Host "Scheduled jobs:"
foreach ($Job in $Status.scheduler.jobs) {
    Write-Host "  $($Job.id) -> $($Job.next_run_time)"
}
