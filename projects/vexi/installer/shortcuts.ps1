param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = 'Stop'
$pythonExe = Join-Path $Target '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { $pythonExe = Join-Path $Target 'venv\Scripts\pythonw.exe' }
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
foreach ($item in @(@('Vexi Dev4.lnk','vexi.py',''), @('Vexi Diagnostics.lnk','settings_ui.py',' --tab diagnostics'))) {
    $shortcut = $shell.CreateShortcut((Join-Path $desktop $item[0]))
    $shortcut.TargetPath = $pythonExe
    $shortcut.Arguments = '"' + (Join-Path $Target $item[1]) + '"' + $item[2]
    $shortcut.WorkingDirectory = $Target
    $shortcut.Save()
}
exit 0
