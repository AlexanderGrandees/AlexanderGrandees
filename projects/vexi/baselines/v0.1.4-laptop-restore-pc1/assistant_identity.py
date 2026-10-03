import json
import os
import re
import time
from pathlib import Path


class AssistantIdentity:
    """Persistent assistant display/wake identity.

    User policy for v0.1.3: a newly assigned assistant name fully replaces the
    previous wake identity. Recovery is always available from the local Settings UI.
    """

    def __init__(self, default_name="Векси", data_dir=None):
        root = Path(data_dir or (Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Vexi" / "data"))
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "assistant_identity.json"
        self.default_name = self._clean_name(default_name) or "Векси"
        self._mtime = None
        self._data = None
        self._load(force=True)

    @staticmethod
    def _clean_name(value):
        value = re.sub(r"\s+", " ", str(value or "")).strip(" .,!?:;\"'«»")
        if not value or len(value) > 32:
            return ""
        if any(ch in value for ch in "\\/<>|{}[]"):
            return ""
        return value

    def _default(self):
        return {
            "display_name": self.default_name,
            "wake_names": [self.default_name],
            "updated_at": time.time(),
            "source": "default",
        }

    def _load(self, force=False):
        try:
            mtime = self.path.stat().st_mtime if self.path.exists() else None
        except OSError:
            mtime = None
        if not force and self._data is not None and mtime == self._mtime:
            return
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                data = self._default()
        else:
            data = self._default()
            self._write(data)
        name = self._clean_name(data.get("display_name")) or self.default_name
        wakes = [self._clean_name(x) for x in (data.get("wake_names") or [])]
        wakes = [x for x in wakes if x]
        if not wakes:
            wakes = [name]
        self._data = dict(data, display_name=name, wake_names=wakes)
        self._mtime = mtime

    def _write(self, data):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        self._mtime = self.path.stat().st_mtime
        self._data = data

    def display_name(self):
        self._load()
        return self._data.get("display_name") or self.default_name

    def wake_names(self):
        self._load()
        return list(self._data.get("wake_names") or [self.display_name()])

    def set_name(self, name, source="user_voice"):
        name = self._clean_name(name)
        if not name:
            return False, "Имя не подходит. Выбери короткое имя без специальных символов."
        old = self.display_name()
        data = {
            "display_name": name,
            "wake_names": [name],
            "previous_name": old,
            "updated_at": time.time(),
            "source": source,
        }
        self._write(data)
        return True, name

    def reset(self):
        data = self._default()
        data["source"] = "user_reset"
        self._write(data)
        return self.default_name
