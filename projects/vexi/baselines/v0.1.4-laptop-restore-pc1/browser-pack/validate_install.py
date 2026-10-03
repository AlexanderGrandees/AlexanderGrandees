import json, os, sys
from pathlib import Path

browser='vivaldi'
local=Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
manifest_path=local/'Vexi'/'plugins'/f'vexi.browser.{browser}.json'
result={'manifest':str(manifest_path),'exists':manifest_path.exists()}
if not manifest_path.exists():
    print(json.dumps({**result,'ok':False,'detail':'manifest_missing'},ensure_ascii=False))
    raise SystemExit(2)
try:
    raw=manifest_path.read_bytes()
    result['bom']=raw.startswith(b'\xef\xbb\xbf')
    data=json.loads(raw.decode('utf-8'))
    result['plugin_id']=data.get('plugin_id')
    result['version']=data.get('version')
    result['protocol']=data.get('protocol')
except Exception as e:
    print(json.dumps({**result,'ok':False,'detail':'manifest_parse_failed','error':type(e).__name__},ensure_ascii=False))
    raise SystemExit(3)
if result['bom']:
    print(json.dumps({**result,'ok':False,'detail':'manifest_has_bom'},ensure_ascii=False))
    raise SystemExit(4)
core=Path(r'C:\Vexi')
if core.exists():
    sys.path.insert(0,str(core))
    try:
        from plugin_manager import PluginManager
        m=PluginManager().browser_pack(browser)
        result['core_detected']=bool(m)
        if not m:
            print(json.dumps({**result,'ok':False,'detail':'core_plugin_manager_did_not_detect'},ensure_ascii=False))
            raise SystemExit(5)
    except ImportError:
        result['core_detected']=None
result['ok']=True
print(json.dumps(result,ensure_ascii=False))
