param([Parameter(Mandatory=$true)][string]$Target, [string]$DesktopPath = '')
$ErrorActionPreference = 'Stop'
$pythonExe = Join-Path $Target '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { $pythonExe = Join-Path $Target 'venv\Scripts\pythonw.exe' }
$shell = New-Object -ComObject WScript.Shell
$desktop = if ($DesktopPath) { [IO.Path]::GetFullPath($DesktopPath) } else { [Environment]::GetFolderPath('Desktop') }
$items = @(@('Vexi (Admin).lnk','vexi.py',''), @('Vexi Diagnostics.lnk','settings_ui.py',' --tab diagnostics'))
if (Test-Path -LiteralPath (Join-Path $desktop 'Vexi Dev4.lnk')) { $items += ,@('Vexi Dev4.lnk','vexi.py','') }
foreach ($item in $items) {
    $linkPath = Join-Path $desktop $item[0]
    $shortcut = $shell.CreateShortcut($linkPath)
    $shortcut.TargetPath = $pythonExe
    $shortcut.Arguments = '"' + (Join-Path $Target $item[1]) + '"' + $item[2]
    $shortcut.WorkingDirectory = $Target
    $shortcut.Save()
    # Shell Link RunAsUser flag: Windows requests elevation on each launch.
    $bytes = [IO.File]::ReadAllBytes($linkPath)
    if ([BitConverter]::ToUInt32($bytes,0) -ne 76) { throw 'Invalid shortcut header' }
    $flags = [BitConverter]::ToUInt32($bytes,20) -bor 0x2000
    [BitConverter]::GetBytes([uint32]$flags).CopyTo($bytes,20)
    [IO.File]::WriteAllBytes($linkPath,$bytes)
}
exit 0
