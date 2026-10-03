param([switch]$NonInteractive)
$ErrorActionPreference='Stop'
$Browser='vivaldi'; $BrowserName='Vivaldi'; $Port=8767; $Version='0.1.2'
$Package=Split-Path -Parent $MyInvocation.MyCommand.Path
$Root=Join-Path $env:LOCALAPPDATA ('VexiBrowserPacks\'+$BrowserName)
$PluginDir=Join-Path $env:LOCALAPPDATA 'Vexi\plugins'
$Target='browser_pack/'+$Browser
$Utf8NoBom=New-Object System.Text.UTF8Encoding($false)
function Write-Utf8NoBom([string]$Path,[string]$Text){ [System.IO.File]::WriteAllText($Path,$Text,$Utf8NoBom) }
Write-Host "Vexi Browser Pack $BrowserName v$Version" -ForegroundColor Cyan
Write-Host 'Fix: resilient YouTube VideoCard extraction + semantic diagnostics.' -ForegroundColor DarkCyan
$py=$null
$pyCore='C:\Vexi\.venv\Scripts\python.exe'
if(Test-Path $pyCore){$py=$pyCore}else{$cmd=Get-Command python -ErrorAction SilentlyContinue;if($cmd){$py=$cmd.Source}else{$cmd=Get-Command py -ErrorAction SilentlyContinue;if($cmd){$py=$cmd.Source}}}
if(-not $py){throw 'Python 3.11+ not found. Install Vexi Core first.'}
New-Item -ItemType Directory -Force -Path $Root,$PluginDir | Out-Null
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -and $_.CommandLine.Contains('pack_service.py') -and $_.CommandLine.Contains('--browser '+$Browser) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 300
$BackupBase=Join-Path $env:LOCALAPPDATA ('VexiBrowserPacks\_backups\'+$BrowserName)
New-Item -ItemType Directory -Force -Path $BackupBase|Out-Null
$Backup=Join-Path $BackupBase (Get-Date -Format 'yyyyMMdd_HHmmss')
if(Test-Path (Join-Path $Root 'pack_service.py')){New-Item -ItemType Directory -Force -Path $Backup|Out-Null; Get-ChildItem $Root -Force | ForEach-Object { Copy-Item $_.FullName $Backup -Recurse -Force -ErrorAction SilentlyContinue }}
Copy-Item (Join-Path $Package 'payload\*') $Root -Recurse -Force
if(-not (Test-Path (Join-Path $Root '.venv\Scripts\pythonw.exe'))){ & $py -m venv (Join-Path $Root '.venv') }
$packPy=Join-Path $Root '.venv\Scripts\python.exe'
$token=& $packPy (Join-Path $Root 'credential_bootstrap.py') --target $Target
if(-not $token){throw 'Could not initialize Browser Pack credential'}
$bg=Get-Content (Join-Path $Root 'extension\background.template.js') -Raw -Encoding UTF8
$bg=$bg.Replace('__TOKEN__',(ConvertTo-Json ([string]$token) -Compress))
Write-Utf8NoBom (Join-Path $Root 'extension\background.js') $bg
$manifest=@{
 plugin_id=('vexi.browser.'+$Browser); type='browser_pack'; version=$Version; protocol=1; browser_ids=@($Browser);
 endpoint=('http://127.0.0.1:'+$Port); launcher=(Join-Path $Root 'run_hidden.vbs'); credential_target=$Target;
 install_root=$Root; extension_path=(Join-Path $Root 'extension'); capabilities=@('active_tab','structured_snapshot','text_input','element_select','media_control')
}|ConvertTo-Json -Depth 6
$ManifestPath=Join-Path $PluginDir ('vexi.browser.'+$Browser+'.json')
Write-Utf8NoBom $ManifestPath $manifest
Write-Host '[1/4] Registry manifest written UTF-8 without BOM.' -ForegroundColor Green
$validate=& $py (Join-Path $Package 'validate_install.py')
if($LASTEXITCODE -ne 0){throw ('Plugin registry validation failed: '+$validate)}
Write-Host ('[2/4] Registry/Core detection PASS: '+$validate) -ForegroundColor Green
$wsh=New-Object -ComObject WScript.Shell
$startup=[Environment]::GetFolderPath('Startup')
$lnk=Join-Path $startup ('Vexi Browser Pack - '+$BrowserName+'.lnk')
if(Test-Path $lnk){Remove-Item $lnk -Force}
$s=$wsh.CreateShortcut($lnk);$s.TargetPath='wscript.exe';$s.Arguments=('"'+(Join-Path $Root 'run_hidden.vbs')+'"');$s.WorkingDirectory=$Root;$s.Description=('Vexi Browser Pack '+$BrowserName+' '+$Version);$s.Save()
Start-Process wscript.exe -WindowStyle Hidden -ArgumentList ('"'+(Join-Path $Root 'run_hidden.vbs')+'"')
Start-Sleep -Milliseconds 900
try{$h=Invoke-RestMethod ('http://127.0.0.1:'+$Port+'/health') -TimeoutSec 2;if(-not $h.ok){throw 'health false'}}catch{throw 'Browser Pack service did not start'}
Write-Host "[3/4] Service PASS http://127.0.0.1:$Port v$($h.version) protocol=$($h.protocol)" -ForegroundColor Green
Write-Host '[4/4] Extension files updated. Reload the unpacked extension in Vivaldi.' -ForegroundColor Yellow
Write-Host "Extension folder: $(Join-Path $Root 'extension')" -ForegroundColor Yellow
$exe=$null
foreach($raw in @('%PROGRAMFILES%\Vivaldi\Application\vivaldi.exe','%PROGRAMFILES(x86)%\Vivaldi\Application\vivaldi.exe','%LOCALAPPDATA%\Vivaldi\Application\vivaldi.exe')){ $p=[Environment]::ExpandEnvironmentVariables($raw); if(Test-Path $p){$exe=$p;break} }
if($exe){Start-Process $exe 'vivaldi://extensions'}
Write-Host 'On vivaldi://extensions click Reload on Vexi Browser Pack, then Ctrl+R the active YouTube tab.' -ForegroundColor Cyan
Write-Host 'After that run DIAGNOSE_BROWSER_PACK.bat. Connected=true + site=youtube is the gate.' -ForegroundColor Cyan
if (-not $NonInteractive) { Read-Host 'Press Enter to close' }

