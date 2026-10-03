import json
import logging
import os
import re
import winreg
from difflib import SequenceMatcher
from pathlib import Path

BASE = Path(__file__).resolve().parent
CACHE = BASE / "app_cache.json"

BLOCKED_TOKENS = (
    "uninstall", "unins", "remove", "setup", "installer", "repair",
    "удаление", "удалить", "деинстал", "деинсталлятор",
)

KNOWN_ALIASES = {
    "steam": ["steam", "стим"],
    "vivaldi": ["vivaldi", "вивальди", "браузер", "мой браузер"],
    "chrome": ["chrome", "google chrome", "хром", "гугл хром"],
    "edge": ["edge", "microsoft edge", "эдж"],
    "brave": ["brave", "брейв"],
    "opera": ["opera", "опера"],
    "firefox": ["firefox", "mozilla firefox", "фаерфокс", "мозилла"],
    "telegram": ["telegram", "телеграм", "телега"],
    "discord": ["discord", "дискорд"],
    "code": ["visual studio code", "vs code", "vscode", "вс код"],
    "obs": ["obs", "obs studio", "обс"],
    "explorer": ["проводник", "explorer", "файлы"],
    "notepad": ["блокнот", "notepad"],
    "calculator": ["калькулятор", "кальк"],
    "taskmgr": ["диспетчер задач", "task manager"],
}

TRUSTED_PATHS = {
    "vivaldi": [
        r"%LOCALAPPDATA%\Vivaldi\Application\vivaldi.exe",
        r"%ProgramFiles%\Vivaldi\Application\vivaldi.exe",
        r"%ProgramFiles(x86)%\Vivaldi\Application\vivaldi.exe",
    ],
    "chrome": [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    ],
    "edge": [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    ],
    "brave": [
        r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
    ],
    "opera": [
        r"%LOCALAPPDATA%\Programs\Opera\opera.exe",
        r"%ProgramFiles%\Opera\launcher.exe",
    ],
    "firefox": [
        r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
        r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
    ],
    "telegram": [
        r"%APPDATA%\Telegram Desktop\Telegram.exe",
        r"%LOCALAPPDATA%\Programs\Telegram Desktop\Telegram.exe",
    ],
    "discord": [
        r"%LOCALAPPDATA%\Discord\Update.exe",
    ],
    "code": [
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
        r"%ProgramFiles%\Microsoft VS Code\Code.exe",
    ],
    "obs": [
        r"%ProgramFiles%\obs-studio\bin\64bit\obs64.exe",
        r"%ProgramFiles(x86)%\obs-studio\bin\32bit\obs32.exe",
    ],
}

SPECIAL_COMMANDS = {
    "explorer": "explorer.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "taskmgr": "taskmgr.exe",
}

PROCESS_HINTS = {
    "steam": ["steam.exe"],
    "vivaldi": ["vivaldi.exe"],
    "chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "brave": ["brave.exe"],
    "opera": ["opera.exe"],
    "firefox": ["firefox.exe"],
    "telegram": ["telegram.exe"],
    "discord": ["discord.exe"],
    "code": ["code.exe"],
    "obs": ["obs64.exe", "obs32.exe"],
    "explorer": ["explorer.exe"],
    "notepad": ["notepad.exe"],
    "calculator": ["calculatorapp.exe", "calculator.exe"],
    "taskmgr": ["taskmgr.exe"],
}

BROWSERS = {"vivaldi", "chrome", "edge", "brave", "opera", "firefox"}


def norm(value):
    value = (value or "").lower().strip().replace("ё", "е")
    value = re.sub(r"[^\w\s\-.:/\\]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def blocked(*values):
    text = " ".join(str(v or "") for v in values).lower()
    return any(token in text for token in BLOCKED_TOKENS)


def first_existing(paths):
    for raw in paths:
        path = os.path.expandvars(raw)
        if path and os.path.isfile(path) and not blocked(path):
            return path
    return None


def similarity(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def steam_executable():
    candidates = [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamExe"),
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ]
    for hive, key_path, value_name in candidates:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                value = str(winreg.QueryValueEx(key, value_name)[0] or "").replace("/", "\\")
                if not value:
                    continue
                exe = value if value.lower().endswith("steam.exe") else os.path.join(value, "steam.exe")
                if os.path.isfile(exe) and not blocked(exe):
                    return exe
        except OSError:
            pass
    return first_existing([r"%ProgramFiles(x86)%\Steam\steam.exe", r"%ProgramFiles%\Steam\steam.exe"])


class AppRegistry:
    def __init__(self):
        self.entries = {}
        self.load_cache()
        self.seed_trusted()

    def load_cache(self):
        try:
            if CACHE.exists():
                data = json.loads(CACHE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.entries = data
        except Exception:
            self.entries = {}

    def save(self):
        try:
            CACHE.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logging.debug("App cache save failed: %s", exc)

    def add(self, name, path=None, shortcut=None, exe_name=None, aliases=None, trusted=False):
        key = norm(name)
        if not key or blocked(name, path, shortcut, exe_name):
            return
        item = self.entries.get(key, {})
        if item.get("trusted") and not trusted:
            path = shortcut = exe_name = None
        if trusted:
            item["trusted"] = True
        if path and os.path.isfile(path) and not blocked(path):
            item["path"] = path
        if shortcut and os.path.isfile(shortcut) and not blocked(shortcut):
            item["shortcut"] = shortcut
        if exe_name and not blocked(exe_name):
            item["exe_name"] = exe_name.lower()
        names = set(item.get("aliases", []))
        names.add(key)
        for alias in aliases or []:
            a = norm(alias)
            if a and not blocked(a):
                names.add(a)
        item["aliases"] = sorted(names)
        item["display_name"] = name
        self.entries[key] = item

    def seed_trusted(self):
        steam = steam_executable()
        if steam:
            self.add("steam", path=steam, exe_name="steam.exe", aliases=KNOWN_ALIASES["steam"], trusted=True)
        for key, aliases in KNOWN_ALIASES.items():
            if key in SPECIAL_COMMANDS:
                self.add(key, exe_name=SPECIAL_COMMANDS[key], aliases=aliases, trusted=True)
            path = first_existing(TRUSTED_PATHS.get(key, []))
            if path:
                exe_name = os.path.basename(path)
                # Discord's Update.exe is only a launcher, not the runtime process name.
                if key == "discord" and exe_name.lower() == "update.exe":
                    exe_name = "discord.exe"
                self.add(key, path=path, exe_name=exe_name, aliases=aliases, trusted=True)

    def scan_shortcuts(self):
        roots = [
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            os.path.expandvars(r"%OneDrive%\Desktop"),
            os.path.expandvars(r"%PUBLIC%\Desktop"),
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
        ]
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _, files in os.walk(root):
                for filename in files:
                    if not filename.lower().endswith(".lnk"):
                        continue
                    full = os.path.join(dirpath, filename)
                    name = Path(filename).stem
                    if blocked(name, full):
                        continue
                    self.add(name, shortcut=full, aliases=[name])

    def refresh(self):
        self.seed_trusted()
        self.scan_shortcuts()
        self.seed_trusted()  # trusted entries win after discovery
        self.save()

    def find(self, query):
        q = norm(query)
        if not q:
            return None
        for key, aliases in KNOWN_ALIASES.items():
            if q == key or q in [norm(x) for x in aliases]:
                item = self.entries.get(key)
                if item:
                    return item
        best, score = None, 0.0
        for key, item in self.entries.items():
            if blocked(item.get("path"), item.get("shortcut"), item.get("display_name")):
                continue
            for alias in item.get("aliases", []) + [key, item.get("display_name", "")]:
                a = norm(alias)
                if not a:
                    continue
                current = similarity(q, a)
                if q == a:
                    return item
                if q in a or a in q:
                    current = max(current, 0.88)
                if current > score:
                    score, best = current, item
        return best if score >= 0.72 else None

    def targets_in_text(self, text):
        t = norm(text)
        found = []
        for key, aliases in KNOWN_ALIASES.items():
            for alias in [key] + aliases:
                a = norm(alias)
                if re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", t):
                    found.append(key)
                    break
        return sorted(set(found))

    def process_names(self, key):
        return PROCESS_HINTS.get(key, [])

    def is_browser(self, key):
        return key in BROWSERS

    def preferred_browser(self, configured="Vivaldi"):
        q = norm(configured)
        configured_key = None
        for key, aliases in KNOWN_ALIASES.items():
            if key in BROWSERS and (q == key or q in [norm(a) for a in aliases]):
                configured_key = key
                break
        if configured_key and self.entries.get(configured_key):
            return configured_key
        # Clean installs must not default to Vivaldi when only Chrome/Edge/etc. exists.
        for key in ("chrome", "edge", "vivaldi", "brave", "opera", "firefox"):
            if self.entries.get(key):
                return key
        return configured_key or "chrome"
