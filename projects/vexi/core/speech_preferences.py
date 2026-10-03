"""Local conversation preferences; no speaker identity or capability authority."""
import json
import os
from pathlib import Path
import uuid


def read_preferences(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    path = root / "config.json"
    if not path.exists(): path = root / "config.defaults.json"
    try:
        data = json.loads(path.read_text("utf-8-sig"))
        return {"name_address_mode": "normal" if data.get("name_address_mode") in {"normal", "occasional"} else "rare",
                "public_followups_enabled": data.get("public_followups_enabled", True) is True,
                "local_dialogue_enabled": data.get("local_dialogue_enabled", False) is True}
    except (OSError, ValueError, TypeError):
        return {"name_address_mode": "rare", "public_followups_enabled": False, "local_dialogue_enabled": False}


def save_preferences(mode, followups, root=None, *, local_dialogue=None):
    if mode not in {"normal", "rare"} or type(followups) is not bool: raise ValueError("invalid_preference")
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    path = root / "config.json"
    source = path if path.exists() else root / "config.defaults.json"
    data = json.loads(source.read_text("utf-8-sig"))
    data.update(name_address_mode=mode, public_followups_enabled=followups)
    if local_dialogue is not None:
        if type(local_dialogue) is not bool: raise ValueError("invalid_preference")
        data["local_dialogue_enabled"] = local_dialogue
    stage = root / (".speech-prefs-" + uuid.uuid4().hex + ".tmp")
    try:
        stage.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(stage, path)
    finally:
        stage.unlink(missing_ok=True)


def name_address_instruction(root=None):
    if read_preferences(root)["name_address_mode"] == "normal":
        return "Обращайся к собеседнику по имени иногда, когда это естественно, но не в каждом ответе. Не придумывай имя."
    return "Почти никогда не обращайся к собеседнику по имени. Используй имя только по его прямой просьбе или для необходимого различения собеседников. Не придумывай имя."
