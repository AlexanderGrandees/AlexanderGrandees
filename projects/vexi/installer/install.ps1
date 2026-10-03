param([string]$Target = 'C:\Vexi', [switch]$VerifyOnly, [switch]$Restore)
$ErrorActionPreference = 'Stop'
try {
    $scriptFile = Join-Path $PSScriptRoot 'install_engine.py'
    $pythonExe = $null
    foreach ($candidate in @((Join-Path $Target '.venv\Scripts\python.exe'), (Join-Path $Target 'venv\Scripts\python.exe'), (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'))) {
        if (Test-Path -LiteralPath $candidate) { $pythonExe = $candidate; break }
    }
    $prefix = @()
    if (-not $pythonExe) {
        $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($launcher) { $pythonExe = $launcher.Source; $prefix = @('-3.11') }
    }
    if (-not $pythonExe) { throw 'Python 3.11 is required. Install Python 3.11 x64 and run again.' }
    & $pythonExe @prefix -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 x64 is required; selected interpreter is incompatible.' }
    # The installer must not run from the environment whose directory it will rename.
    $basePython = (& $pythonExe @prefix -c 'import sys; print(sys._base_executable)').Trim()
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $basePython)) { throw 'Base Python installation is missing.' }
    $pythonExe = $basePython
    $prefix = @()
    $invokeArgs = @($prefix) + @($scriptFile, '--target', $Target)
    if ($VerifyOnly) { $invokeArgs += '--verify-package' }
    elseif ($Restore) { $invokeArgs += '--restore' }
    else { $invokeArgs += '--launch' }
    & $pythonExe @invokeArgs
    exit $LASTEXITCODE
} catch {
    Write-Host ('[Vexi] ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
