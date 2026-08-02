param(
    [string]$LogName = 'scheduled_publish.log'
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogPath = Join-Path $ProjectRoot $LogName

Set-Location $ProjectRoot

"[$(Get-Date -Format o)] Starting scheduled publish" | Add-Content -Path $LogPath

try {
    $env:PYTHONIOENCODING = 'utf-8'
    python -m tools.publish_once 2>&1 | Add-Content -Path $LogPath
    $ExitCode = $LASTEXITCODE
} catch {
    $_ | Out-String | Add-Content -Path $LogPath
    $ExitCode = 1
}

"[$(Get-Date -Format o)] Scheduled publish finished with exit code $ExitCode" | Add-Content -Path $LogPath
exit $ExitCode
