import json
from pathlib import Path
BASE=Path(__file__).resolve().parent
cfg=json.loads((BASE/'config.json').read_text(encoding='utf-8'))
port=int(cfg.get('browser_bridge_port',8765))
token=str(cfg.get('browser_bridge_token',''))
p=BASE/'browser_extension'/'config.js'
p.write_text(f'window.VEXI_BRIDGE_PORT = {port};\nwindow.VEXI_BRIDGE_TOKEN = {json.dumps(token)};\n',encoding='utf-8')
print('BROWSER EXTENSION CONFIGURED:', p)
