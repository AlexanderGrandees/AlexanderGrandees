param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = 'Stop'
$entry = [IO.Path]::GetFullPath((Join-Path $Target 'vexi.py'))
$pattern = '(?i)(?:^|["\s])' + [regex]::Escape($entry) + '(?:["\s]|$)'
$interpreters = @('.venv\Scripts\python.exe', '.venv\Scripts\pythonw.exe', 'venv\Scripts\python.exe', 'venv\Scripts\pythonw.exe') | ForEach-Object { [IO.Path]::GetFullPath((Join-Path $Target $_)) }
Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(w)?\.exe$' -and ($_.CommandLine -match $pattern -or
        ($interpreters -contains $_.ExecutablePath -and $_.CommandLine -match '(?i)(?:^|["\s])(?:\.\\)?vexi\.py(?:["\s]|$)'))
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop }
exit 0
