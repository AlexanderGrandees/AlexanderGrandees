$ErrorActionPreference='Continue'
$Browser='vivaldi'; $BrowserName='Vivaldi'; $Port=8767
$Root=Join-Path $env:LOCALAPPDATA 'VexiBrowserPacks\Vivaldi'
$Manifest=Join-Path $env:LOCALAPPDATA 'Vexi\plugins\vexi.browser.vivaldi.json'
Write-Host '=== VEXI BROWSER PACK DIAGNOSTICS ===' -ForegroundColor Cyan
Write-Host ('Root:      ' + $Root)
Write-Host ('Manifest:  ' + $Manifest)
Write-Host ('Registry:  ' + $(if(Test-Path $Manifest){'PRESENT'}else{'MISSING'}))
if(Test-Path $Manifest){
  $b=[IO.File]::ReadAllBytes($Manifest)
  $hasBom=($b.Length -ge 3 -and $b[0]-eq 0xEF -and $b[1]-eq 0xBB -and $b[2]-eq 0xBF)
  Write-Host ('UTF8 BOM:  ' + $hasBom)
}
try{$h=Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2; Write-Host ('Service:   PASS v'+$h.version+' protocol '+$h.protocol) -ForegroundColor Green}catch{Write-Host ('Service:   FAIL '+$_.Exception.Message) -ForegroundColor Red}
$py='C:\Vexi\.venv\Scripts\python.exe'
if(Test-Path $py){
  Push-Location C:\Vexi
  try{
    & $py -c "import json; from browser_pack_client import BrowserPackClient; print(json.dumps(BrowserPackClient().status('vivaldi'), ensure_ascii=False, indent=2))"
    & $py -c "import json,collections; from browser_pack_client import BrowserPackClient; s=BrowserPackClient().snapshot('vivaldi',3.0) or {}; e=s.get('elements') or []; c=collections.Counter(str(x.get('semantic_type')) for x in e); print(json.dumps({'snapshot_elements':len(e),'semantic_types':dict(c),'videos':[{'position':x.get('position'),'title':x.get('title'),'channel':x.get('channel')} for x in e if x.get('semantic_type')=='video'][:8]}, ensure_ascii=False, indent=2))"
  }finally{Pop-Location}
}else{Write-Host 'Core Python not found; skipping Core status.' -ForegroundColor Yellow}
Write-Host ('Extension: ' + (Join-Path $Root 'extension'))
