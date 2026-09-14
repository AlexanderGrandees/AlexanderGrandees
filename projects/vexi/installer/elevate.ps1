param([switch]$Restore)
$ErrorActionPreference = 'Stop'
try {
    $scriptFile = Join-Path $PSScriptRoot 'install.ps1'
    $launchArgs = '-NoProfile -ExecutionPolicy Bypass -File "' + $scriptFile + '"'
    if ($Restore) { $launchArgs += ' -Restore' }
    $proc = Start-Process powershell.exe -ArgumentList $launchArgs -Verb RunAs -Wait -PassThru
    exit $proc.ExitCode
} catch {
    Write-Host ('[Vexi] Elevation was not completed: ' + $_.Exception.Message)
    exit 1
}
