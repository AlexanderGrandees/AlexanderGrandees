import json
import secrets
from pathlib import Path

BASE = Path(__file__).resolve().parent
existing_path = BASE / 'config.json'
defaults_path = BASE / 'config.defaults.json'

def deep_merge(existing, defaults):
    if not isinstance(existing, dict):
        existing = {}
    out = dict(existing)
    for k, v in defaults.items():
        if k not in out:
            out[k] = v
        elif isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
    return out

defaults = json.loads(defaults_path.read_text(encoding='utf-8'))
if existing_path.exists():
    try:
        existing = json.loads(existing_path.read_text(encoding='utf-8'))
    except Exception:
        existing = {}
else:
    existing = {}
merged = deep_merge(existing, defaults)
merged['version'] = '0.1.4'
merged['release_channel'] = 'public-preview'
merged['tts_engine'] = 'silero'
merged['silero_language'] = 'ru'
merged['silero_model'] = 'v5_ru'
merged['silero_speaker'] = 'xenia'
merged['speak_answers'] = True
merged['name_address_mode'] = merged.get('name_address_mode') or 'occasional'
existing_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
print('CONFIG MERGED:', existing_path)
