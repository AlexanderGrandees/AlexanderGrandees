import logging
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote_plus

from app_registry import AppRegistry, BROWSERS, KNOWN_ALIASES, norm
from audio_adapter import AudioAdapter
from browser_adapter import BrowserAdapter
from version import __version__, __channel__, __build__
from filesystem_adapter import FileSystemAdapter
from display_adapter import DisplayAdapter
from youtube_adapter import YouTubeAdapter
from memory import PersonalMemory
from assistant_identity import AssistantIdentity
from plugin_manager import PluginManager
from service_registry import ServiceRegistry
from policy_gate import PolicyGate
from steam_adapter import SteamAdapter
from window_manager import (
    active_window,
    close_process_windows,
    enum_windows,
    explorer_windows,
    focus_explorer_window,
    focus_processes,
    list_visible_windows,
    matching_processes,
    maximize_processes,
    minimize_processes,
    send_hotkey,
)

SITE_ALIASES = {
    "youtube": ["youtube", "ютуб", "ютьюб"],
    "tradingview": ["tradingview", "трейдингвью", "трейдинг вью"],
    "binance": ["binance", "бинанс"],
    "chatgpt": ["chatgpt", "чатгпт", "чат gpt", "чат джипити"],
    "github": ["github", "гитхаб"],
    "gmail": ["gmail", "джимейл", "почта gmail"],
    "calendar": ["google calendar", "гугл календарь", "календарь google"],
    "notion": ["notion", "ноушн"],
    "google": ["google", "гугл"],
    "steam_support": ["поддержка steam", "поддержку steam", "steam support", "поддержка стим", "поддержку стим"],
    "steam_site": ["сайт steam", "сайт стим", "steam сайт", "стим сайт"],
}

SITE_URLS = {
    "youtube": "https://www.youtube.com",
    "tradingview": "https://www.tradingview.com",
    "binance": "https://www.binance.com",
    "chatgpt": "https://chatgpt.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "calendar": "https://calendar.google.com",
    "notion": "https://www.notion.so",
    "google": "https://www.google.com",
    "steam_support": "https://help.steampowered.com/",
    "steam_site": "https://store.steampowered.com/",
}

OPEN_PATTERNS = [
    r"\bоткрой(?:те)?\b",
    r"\bоткрывай\b",
    r"\bоткрыть\b",
    r"\bоткроем\b",
    r"\bзапусти(?:те)?\b",
    r"\bзапускай\b",
    r"\bзапустить\b",
    r"\bможешь(?:\s+ли)?\s+(?:мне\s+)?открыть\b",
    r"\bне\s+могла\s+бы\s+(?:мне\s+)?открыть\b",
    r"\bдавай\s+откроем\b",
]

OPEN_STT_ALIASES = ("откроме", "открои", "аткрой", "кромнее")

REPORT_MARKERS = (
    "не открыл", "не открыла", "не открылось", "не открыто", "не произошло", "не сработал", "не сработала",
    "это не та команда", "не та команда", "я сам включил", "я сам открыл", "страница не открыта", "вкладка не открыта",
    "ничего не произошло", "ты опять не", "но проводник не открыт", "я открою",
)

CORRECTION_MARKERS = ("это не та команда", "неправильная команда", "не то", "я имел в виду", "я сказал")

FILLERS = {
    "мне", "пожалуйста", "просто", "сейчас", "давай", "ну", "хорошо", "ладно", "окей", "ок", "так", "все", "всё",
}


def site_targets(text):
    t = norm(text)
    found = []
    for key, aliases in SITE_ALIASES.items():
        for alias in [key] + aliases:
            a = norm(alias)
            if re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", t):
                found.append(key)
                break
    return sorted(set(found))


def contains_open(text):
    t = norm(text)
    if any(re.search(p, t) for p in OPEN_PATTERNS):
        return True
    tokens = t.split()
    # STT repair only around a known static app/site entity.
    known = bool(site_targets(t))
    if not known:
        for key, aliases in KNOWN_ALIASES.items():
            for alias in [key] + aliases:
                a = norm(alias)
                if re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", t):
                    known = True
                    break
            if known:
                break
    return bool(known and any(tok in OPEN_STT_ALIASES for tok in tokens))


def clean_query(text):
    words = [w for w in norm(text).split() if w not in FILLERS]
    return " ".join(words).strip()


class Router:
    def __init__(self, config, identity=None):
        self.cfg = config
        self.identity = identity or AssistantIdentity(config.get("assistant_name", "Векси"))
        self.plugins = PluginManager()
        self.services = ServiceRegistry()
        self.policy = PolicyGate()
        self.registry = AppRegistry()
        if config.get("auto_discover_apps", True):
            self.registry.refresh()
        self.memory = PersonalMemory()
        remembered_browser = norm(self.memory.preferred_browser() or "")
        preferred = self.registry.preferred_browser(remembered_browser or config.get("browser_name", "Vivaldi"))
        self.browser = BrowserAdapter(self.registry, preferred=preferred, config=config, plugin_manager=self.plugins)
        self.audio = AudioAdapter()
        self.display = DisplayAdapter()
        self.files = FileSystemAdapter()
        self.youtube = YouTubeAdapter(self.browser)
        self.steam = SteamAdapter(self.registry, self.memory)
        self.current_app = None
        self.current_site = None
        self.current_browser = preferred
        self.current_media = None
        self.last_action = None
        self.last_property = None
        self.last_launch_path = None
        self.last_target = None
        self.last_media_state = {}

    def onboarding_prompt(self):
        return self.memory.onboarding_prompt()

    def memory_context(self):
        return self.memory.prompt_context()

    def _log_result(self, source, intent, status, answer, entity=None):
        logging.info("INTENT action=%s entity=%s source=%s status=%s", intent, entity, source, status)
        logging.info("RESPONSE source=%s status=%s answer=%s", source, status, answer)
        self.last_action = intent
        return True, answer

    def _segment(self, text):
        # Keep explicit sequence connectors, but avoid splitting inside URLs.
        raw = re.sub(r"\s+", " ", text.strip())
        parts = re.split(
            r"(?<=[.!?;])\s+|\s+(?:теперь|затем|потом)\s+|\s+и\s+(?=(?:скажи|покажи|проверь|перечисли|открой|найди|поищи|включи|выключи|сделай|поставь|убери|выйди)\b)",
            raw, flags=re.I
        )
        return [p.strip(" ,.;") for p in parts if p.strip(" ,.;")]

    def _classify_clause(self, text):
        t = norm(text)
        raw = text.strip()
        if any(m in t for m in CORRECTION_MARKERS):
            return "CORRECTION"
        # Explicit questions win over declarative status/report wording.
        question = "?" in raw or any(t.startswith(x) for x in (
            "что ", "какое ", "какая ", "какие ", "где ", "сколько ",
            "ты видишь", "проверь", "открыт ли", "запущен ли", "работает ли",
        ))
        # Declarative app state is evidence/report, not a STATUS command.
        if not question and self.registry.targets_in_text(t):
            if re.search(r"\b(?:не\s+)?(?:открыт|открыта|открыто|запущен|запущена|работает)\b", t):
                if not contains_open(t):
                    return "REPORT"
        if any(m in t for m in REPORT_MARKERS) and not self._explicit_command_after_report(t):
            return "REPORT"
        if self._looks_like_command(t):
            return "COMMAND"
        if question:
            return "QUESTION"
        return "CONVERSATION"

    def _explicit_command_after_report(self, t):
        return any(x in t for x in ("теперь открой", "а теперь открой", "хорошо открой", "теперь сделай", "а теперь сделай"))

    def _looks_like_command(self, t):
        # Word-boundary patterns avoid treating nouns such as "продолжить просмотр есть"
        # or narrative fragments as imperative actions merely by substring overlap.
        patterns = (
            r"\bоткрой(?:те)?\b", r"\bоткрывай\b", r"\bоткрыть\b",
            r"\bзапусти(?:те)?\b", r"\bзапускай\b", r"\bзакрой(?:те)?\b",
            r"\bсверни\b", r"\bразверни\b", r"\bпокажи\b", r"\bвыведи\b",
            r"\bнайди\b", r"\bпоищи\b", r"\bзагугли\b", r"\bсделай\b",
            r"\bпоставь\b", r"\bувеличь\b", r"\bуменьши\b", r"\bубавь\b",
            r"\bприбавь\b", r"\bвыключи\b", r"\bвключи\b", r"\bпереключи\b",
            r"\bпауза\b", r"\bпродолжи\b", r"\bобнови\b", r"\bназад\b",
            r"\bвперед\b", r"\bвперёд\b", r"\bсоздай\b", r"\bперемести\b",
            r"\bскопируй\b", r"\bкопируй\b", r"\bудали\b", r"\bзапомни\b",
            r"\bзабудь\b", r"\bвыбери\b", r"\bсмени\b", r"\bубери\b", r"\bвыйди\b", r"\bверни\b", r"\bскажи\b", r"\bперечисли\b",
        )
        if any(re.search(p, t) for p in patterns):
            return True
        if any(x in t for x in (
            "новая вкладка", "закрой вкладку", "следующая вкладка", "предыдущая вкладка",
            "следующее видео", "предыдущее видео", "миниплеер", "мини плеер",
            "полный экран", "весь экран", "громче", "тише", "ярче", "темнее"
        )):
            return True
        if self.last_property and any(x in t for x in ("минимум", "максимум", "половин", "треть", "четверт", "как было")):
            return True
        if re.search(r"\b(?:включить|выключить|переключить|изменить|сменить)\b", t):
            return True
        if any(prop in t for prop in ("громк", "яркост")) and (
            re.search(r"\b\d{1,3}\s*%?\b", t) or any(x in t for x in ("минимум", "максимум", "половин", "треть", "четверт"))
        ):
            return True
        if re.search(r"\bможешь(?:\s+ли)?\s+.*(?:открыть|закрыть|сделать|показать|найти|поставить|изменить|увеличить|уменьшить|продолжить)\b", t):
            return True
        if site_targets(t) or self.registry.targets_in_text(t):
            if any(tok in t.split() for tok in OPEN_STT_ALIASES):
                return True
        return False

    def execute(self, text):
        logging.info("ROUTER input=%s current_app=%s current_site=%s current_browser=%s", text, self.current_app, self.current_site, self.current_browser)

        clauses = self._segment(text)

        # Onboarding handles only the onboarding answer; any additional explicit
        # commands in the same utterance continue through the normal router.
        if self.memory.pending_onboarding:
            onboarding_clause = clauses[0] if clauses else text
            remainder = clauses[1:] if len(clauses) > 1 else []
            if not remainder:
                t = norm(onboarding_clause)
                m = re.search(r"\b(открой|открывай|открыть|запусти|сделай|поставь|найди|поищи|увеличь|уменьши|выключи|включи|переключи)\b", t)
                if m and m.start() > 0:
                    prefix = onboarding_clause[:m.start()].strip(" ,.;")
                    suffix = onboarding_clause[m.start():].strip(" ,.;")
                    if prefix and suffix:
                        onboarding_clause, remainder = prefix, [suffix]
            handled, onboarding_answer, expects_more = self.memory.handle_onboarding(onboarding_clause)
            if handled:
                logging.info("INTENT action=ONBOARDING entity=None source=memory status=CONFIRMED_SUCCESS")
                outputs = []
                for clause in remainder:
                    kind = self._classify_clause(clause)
                    if kind in {"REPORT", "CORRECTION", "EXPLANATION", "CONVERSATION"}:
                        logging.info("ROUTER clause_class=%s no_execution text=%s", kind, clause)
                        continue
                    h, a = self._execute_clause(clause)
                    if h and a and a not in outputs:
                        outputs.append(a)
                if onboarding_answer:
                    outputs.append(onboarding_answer)
                answer = " ".join(outputs)
                logging.info("RESPONSE source=memory status=CONFIRMED_SUCCESS answer=%s", answer)
                return True, answer

        if len(clauses) > 1:
            outputs = []
            handled_any = False
            for clause in clauses:
                kind = self._classify_clause(clause)
                if kind in {"REPORT", "CORRECTION", "EXPLANATION", "CONVERSATION"}:
                    logging.info("ROUTER clause_class=%s no_execution text=%s", kind, clause)
                    continue
                handled, answer = self._execute_clause(clause)
                if handled:
                    handled_any = True
                    if answer and answer not in outputs:
                        outputs.append(answer)
            if handled_any:
                return True, " ".join(outputs)
            if any(self._classify_clause(c) in {"REPORT", "CORRECTION"} for c in clauses):
                return False, None

        kind = self._classify_clause(text)
        if kind in {"REPORT", "CORRECTION", "CONVERSATION"}:
            logging.info("ROUTER utterance_class=%s no_execution", kind)
            return False, None
        return self._execute_clause(text)

    def _open_settings(self, tab="security"):
        pyw = Path(__file__).resolve().parent / ".venv" / "Scripts" / "pythonw.exe"
        py = str(pyw if pyw.exists() else Path(os.sys.executable))
        try:
            subprocess.Popen([py, str(Path(__file__).resolve().parent / "settings_ui.py"), "--tab", tab], creationflags=0x08000000 if os.name == "nt" else 0)
            return "CONFIRMED_SUCCESS", "Открыла настройки."
        except Exception:
            return "FAILED", "Не удалось открыть настройки."

    def _identity_route(self, t):
        if any(x in t for x in ("как тебя зовут", "какое у тебя имя", "твое имя", "твоё имя")):
            return "CONFIRMED_SUCCESS", f"Сейчас меня зовут {self.identity.display_name()}."
        if any(x in t for x in ("сбрось имя ассистента", "верни имя векси", "верни имя по умолчанию")):
            name = self.identity.reset()
            return "CONFIRMED_SUCCESS", f"Имя сброшено. Теперь я {name}."
        patterns = (
            r"(?:теперь\s+тебя\s+зовут|смени\s+имя\s+на|поменяй\s+имя\s+на|твое\s+имя\s+теперь|твоё\s+имя\s+теперь|зови\s+себя)\s+(.+)$",
        )
        for p in patterns:
            m = re.search(p, t, flags=re.I)
            if m:
                candidate = m.group(1).strip(" .,!?:;\"'«»")
                ok, result = self.identity.set_name(candidate, source="user_voice")
                if ok:
                    return "CONFIRMED_SUCCESS", f"Хорошо. Теперь я {result}. Старое имя больше не является wake-именем."
                return "AMBIGUOUS", result
        return None

    def _security_route(self, t):
        if any(x in t for x in ("открой безопасность", "настройки безопасности", "открой настройки безопасности", "подключения сервисов")):
            return self._open_settings("security")
        if any(x in t for x in ("открой плагины", "покажи плагины", "настройки плагинов")):
            return self._open_settings("plugins")
        if any(x in t for x in ("открой настройки имени", "настройки ассистента")):
            return self._open_settings("assistant")
        # Secrets are UI-only by policy.
        if any(x in t for x in ("токен", "api key", "апи ключ", "пароль", "секретный ключ")) and any(x in t for x in ("сохрани", "запомни", "введи", "добавь", "установи")):
            self._open_settings("security")
            return "BLOCKED", "Секреты голосом не принимаю. Открыла вкладку безопасности — введи ключ там."
        return None

    def _memory_route(self, t, raw):
        if t.startswith("запомни") or t.startswith("помни"):
            handled, answer = self.memory.remember_statement(raw)
            return handled, answer
        if any(x in t for x in ("что ты обо мне помнишь", "что ты помнишь обо мне", "что ты запомнила обо мне")):
            return True, self.memory.summary()
        if any(x in t for x in ("выключи личную память", "отключи личную память", "не запоминай больше")):
            self.memory.set_consent(False)
            return True, "Личную долговременную память выключила."
        if any(x in t for x in ("включи личную память", "можешь запоминать", "разрешаю запоминать")):
            self.memory.set_consent(True)
            return True, "Личную память включила. Сохраняю только разрешённые данные локально."
        return False, None

    # ---------- audio ----------
    def _number_word_percent(self, t):
        absolute = {
            "наполовину": 50, "на половину": 50, "половина": 50,
            "на треть": 33.333, "одна треть": 33.333,
            "на четверть": 25, "четверть": 25,
            "на две трети": 66.667, "две трети": 66.667,
            "на три четверти": 75, "три четверти": 75,
            "на полную": 100, "на максимум": 100, "максимум": 100,
            "полная": 100, "на все сто": 100, "на все 100": 100,
            "минимум": 0, "на минимум": 0, "в минимум": 0,
            "в ноль": 0, "на ноль": 0,
        }
        for phrase, pct in absolute.items():
            if phrase in t:
                return pct
        m = re.search(r"(?:громкость|звук|яркость)?\s*(?:на|до|поставь|сделай)?\s*(\d{1,3})\s*%", t)
        if m:
            return max(0, min(100, int(m.group(1))))
        m = re.search(r"(?:громкость|звук|яркость)\s+(\d{1,3})(?:\s*процент(?:а|ов)?)?\b", t)
        if m:
            return max(0, min(100, int(m.group(1))))
        return None

    def _audio_route(self, t):
        system_scope = any(x in t for x in ("систем", "на ноут", "ноуте", "ноутбук", "компьютер", "на комп", "windows", "виндовс"))
        media_scope = self.current_media == "youtube_player" or self.last_target == "youtube_player"
        # Explicit video/player wording or an active media context wins unless the user names the system/laptop explicitly.
        if not system_scope and (
            (self.current_site == "youtube" and any(x in t for x in ("видео", "плеер", "youtube", "ютуб")))
            or (media_scope and any(x in t for x in ("громк", "звук", "тише", "громче", "mute", "мут", "на ноль", "минимум", "максимум")))
        ):
            return None
        audio_context = any(x in t for x in ("громк", "звук", "тише", "громче", "mute", "мут")) or self.last_property == "system_volume"
        if not audio_context:
            return None
        current = self.audio.get_volume()
        if current is None:
            return "UNSUPPORTED", "Системное управление громкостью сейчас недоступно."
        if any(x in t for x in ("какая громкость", "сколько громкость", "сколько сейчас звук")):
            return "CONFIRMED_SUCCESS", f"Системная громкость примерно {round(current*100)}%."
        if any(x in t for x in ("выключи звук", "без звука", "замуть", "mute")):
            status, actual = self.audio.set_mute(True)
            self.last_property = "system_volume"
            return status, "Звук выключен." if status == "CONFIRMED_SUCCESS" else "Команду выключить звук отправила, но точное состояние не подтверждено."
        if any(x in t for x in ("включи звук", "верни звук", "unmute")):
            status, actual = self.audio.set_mute(False)
            self.last_property = "system_volume"
            return status, "Звук включён." if status == "CONFIRMED_SUCCESS" else "Команду включить звук отправила, но точное состояние не подтверждено."
        if "верни" in t and ("как было" in t or "громк" in t or "звук" in t):
            status, actual = self.audio.restore_volume()
            self.last_property = "system_volume"
            if status == "NOT_FOUND":
                return status, "Предыдущее значение громкости ещё не сохранено."
            pct = round((actual if actual is not None else current) * 100)
            return status, f"Вернула громкость примерно на {pct}%." if status == "CONFIRMED_SUCCESS" else "Возврат громкости отправила, но состояние не подтверждено."

        target_pct = self._number_word_percent(t)
        relative = any(x in t for x in ("тише", "громче", "уменьши", "убавь", "увеличь", "прибавь"))
        if target_pct is not None and not relative:
            target = target_pct / 100.0
        elif "вдвое тише" in t or "в два раза тише" in t or "уменьши наполовину" in t or "убавь наполовину" in t:
            target = current * 0.5
        elif "уменьши на треть" in t or "убавь на треть" in t:
            target = current * (2/3)
        elif "увеличь на треть" in t or "прибавь на треть" in t:
            target = current * (4/3)
        else:
            m = re.search(r"на\s*(\d{1,3})\s*%?\s*(тише|громче)", t)
            if m:
                delta = int(m.group(1)) / 100.0
                target = current - delta if m.group(2) == "тише" else current + delta
            elif any(x in t for x in ("чуть чуть тише", "чуть-чуть тише")):
                target = current - 0.05
            elif any(x in t for x in ("чуть чуть громче", "чуть-чуть громче")):
                target = current + 0.05
            elif "чуть тише" in t:
                target = current - 0.10
            elif "чуть громче" in t:
                target = current + 0.10
            elif "тише" in t or "убавь" in t or "уменьши громкость" in t:
                target = current - 0.10
            elif "громче" in t or "прибавь" in t or "увеличь громкость" in t:
                target = current + 0.10
            elif target_pct is not None:
                target = target_pct / 100.0
            else:
                return None
        status, actual = self.audio.set_volume(target)
        self.last_property = "system_volume"
        pct = round((actual if actual is not None else max(0, min(1, target))) * 100)
        return status, f"Громкость {pct}%." if status == "CONFIRMED_SUCCESS" else f"Команду на громкость {pct}% отправила, но точное состояние не подтверждено."

    # ---------- display / personalization ----------
    def _display_route(self, t):
        if any(x in t for x in ("настройки экрана", "параметры экрана", "открой экранные настройки")):
            status = self.display.open_display_settings()
            return status, "Открываю настройки экрана." if status != "FAILED" else "Не смогла открыть настройки экрана."

        if "hdr" in t or "хдр" in t:
            if any(x in t for x in ("переключи", "переключить", "toggle")):
                status = self.display.toggle_hdr()
                if status == "SENT_NOT_CONFIRMED":
                    return status, "Переключила HDR через системную комбинацию Windows, но текущее состояние пока не умею подтвердить."
                return status, "Не смогла переключить HDR."
            if any(x in t for x in ("включи", "выключи", "включить", "выключить")):
                return "UNSUPPORTED", "Пока не переключаю HDR вслепую по команде включить/выключить: сначала добавлю чтение текущего HDR-состояния. Могу выполнить команду «переключи HDR»."
            return "UNSUPPORTED", "Чтение состояния HDR в этой версии ещё не подключено."

        if "яркост" in t or "ярче" in t or "темнее" in t:
            current = self.display.get_brightness()
            if any(x in t for x in ("какая яркость", "сколько яркость", "яркость сейчас")):
                if current is None:
                    return "UNSUPPORTED", "Системная яркость этого дисплея через WMI недоступна."
                return "CONFIRMED_SUCCESS", f"Яркость экрана примерно {current}%."
            if current is None:
                return "UNSUPPORTED", "Не могу управлять яркостью этого дисплея через системный интерфейс Windows."
            if "верни" in t and ("как было" in t or "яркост" in t):
                status, actual = self.display.restore_brightness()
                if status == "NOT_FOUND":
                    return status, "Предыдущее значение яркости ещё не сохранено."
                return status, f"Яркость {actual}%." if actual is not None else "Команду возврата яркости отправила."
            target_pct = self._number_word_percent(t)
            if target_pct is not None:
                target = target_pct
            elif "чуть ярче" in t:
                target = current + 10
            elif "чуть темнее" in t:
                target = current - 10
            elif "ярче" in t or "увеличь яркость" in t or "прибавь яркость" in t:
                target = current + 10
            elif "темнее" in t or "уменьши яркость" in t or "убавь яркость" in t:
                target = current - 10
            else:
                return None
            status, actual = self.display.set_brightness(target)
            pct = actual if actual is not None else max(0, min(100, int(round(target))))
            return status, f"Яркость {pct}%." if status == "CONFIRMED_SUCCESS" else f"Команду на яркость {pct}% отправила, но точное состояние не подтверждено."

        if "обои" in t or "wallpaper" in t:
            if "верни" in t and "обои" in t:
                status, actual = self.display.restore_wallpaper()
                if status == "NOT_FOUND":
                    return status, "Предыдущие обои в этой сессии не сохранены."
                return status, "Вернула предыдущие обои." if status == "CONFIRMED_SUCCESS" else "Команду возврата обоев отправила, но результат не подтверждён."
            if any(x in t for x in ("какие обои", "что на обоях", "путь обоев")):
                current = self.display.get_wallpaper()
                return ("CONFIRMED_SUCCESS", f"Текущие обои: {current}.") if current else ("NOT_FOUND", "Путь текущих обоев определить не удалось.")
            if any(x in t for x in ("поставь", "смени", "сделай", "установи")):
                path = None
                if self.files.last_found and self.files.last_found.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                    if any(x in t for x in ("его", "ее", "её", "этот файл", "эту картинку", "найденн")):
                        path = self.files.last_found
                if path is None:
                    m = re.search(r"(?:обои|wallpaper)(?:\s+на|\s+из|\s+)?\s*[\"']?([a-z]:\\[^\"']+|[^\"']+\.(?:jpg|jpeg|png|bmp|webp))[\"']?", t, flags=re.I)
                    if m:
                        path = m.group(1).strip()
                if path is None:
                    return "AMBIGUOUS", "Не поняла, какую картинку поставить на обои. Сначала найди файл или укажи путь."
                status, actual = self.display.set_wallpaper(path)
                if status == "CONFIRMED_SUCCESS":
                    return status, "Обои поменяла."
                if status == "NOT_FOUND":
                    return status, "Файл для обоев не найден."
                if status == "BLOCKED":
                    return status, "Этот тип файла не использую как обои."
                return status, "Команду смены обоев отправила, но результат не подтверждён."
        return None

    # ---------- apps/windows ----------
    def _processes(self, key):
        return matching_processes(self.registry.process_names(key))

    def _app_open(self, key):
        if self.registry.is_browser(key):
            status, state = self.browser.open_browser(key)
            title = state.get("active_tab_title") or ""
            if status in {"CONFIRMED_SUCCESS", "ALREADY_SATISFIED"}:
                self.current_app = key
                self.current_browser = key
            if status == "ALREADY_SATISFIED":
                answer = f"Вижу открытый {key}."
                if title:
                    answer += f" Активная вкладка — {title}."
                else:
                    answer += " Название активной вкладки подтвердить не удалось."
                return status, answer
            if status == "CONFIRMED_SUCCESS":
                answer = f"Открыла {key}."
                if title:
                    answer += f" Активная вкладка — {title}."
                else:
                    answer += " Название активной вкладки подтвердить не удалось."
                return status, answer
            if status == "NOT_FOUND":
                return status, f"Не нашла установленный {key}."
            return status, f"Команду открыть {key} отправила, но видимое окно не подтверждено."

        if key == "explorer":
            wins = explorer_windows()
            if wins:
                fg = active_window()
                already_foreground = bool(fg and any(w["hwnd"] == fg.get("hwnd") for w in wins))
                ok = already_foreground or focus_explorer_window()
                if ok:
                    self.current_app = "explorer"
                    return ("ALREADY_SATISFIED" if already_foreground else "CONFIRMED_SUCCESS"), (
                        "Проводник уже открыт." if already_foreground else "Проводник уже открыт. Вывела окно вперёд."
                    )
                return "SENT_NOT_CONFIRMED", "Окно Проводника вижу, но фокус подтвердить не смогла."
            try:
                subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
            except Exception:
                return "FAILED", "Не смогла запустить Проводник."
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                time.sleep(0.20)
                wins = explorer_windows()
                if wins:
                    focus_explorer_window()
                    self.current_app = "explorer"
                    return "CONFIRMED_SUCCESS", "Открыла Проводник."
            return "SENT_NOT_CONFIRMED", "Запуск Проводника отправила, но отдельное окно Проводника не подтвердилось."

        if key == "steam":
            state = self.steam.inspect()
            if state["process_running"] and state["account_picker_detected"]:
                self.current_app = "steam"
                profiles = state.get("available_saved_profiles") or []
                suffix = f" Вижу варианты: {', '.join(profiles[:4])}." if profiles else ""
                return "ALREADY_SATISFIED", "Steam уже запущен и ждёт выбора аккаунта." + suffix

        procs = self._processes(key)
        if procs:
            wins = enum_windows([p.pid for p in procs])
            if wins:
                ok = focus_processes(procs)
                if ok:
                    self.current_app = key
                return ("CONFIRMED_SUCCESS" if ok else "SENT_NOT_CONFIRMED"), (f"{key} уже открыт. Вывела окно вперёд." if ok else f"{key} запущен, но фокус окна не подтверждён.")

        item = self.registry.find(key)
        if not item:
            return "NOT_FOUND", f"Не нашла приложение {key}."
        try:
            if item.get("path"):
                path = item["path"]
                if key == "discord" and path.lower().endswith("update.exe"):
                    subprocess.Popen([path, "--processStart", "Discord.exe"])
                else:
                    subprocess.Popen([path])
                self.last_launch_path = path
            elif item.get("shortcut"):
                os.startfile(item["shortcut"])
                self.last_launch_path = item["shortcut"]
            elif item.get("exe_name"):
                subprocess.Popen([item["exe_name"]])
                self.last_launch_path = item["exe_name"]
            else:
                return "NOT_FOUND", f"Не нашла безопасный путь запуска {key}."
        except Exception as exc:
            logging.exception("launch app failed %s: %s", key, exc)
            return "FAILED", f"Не смогла запустить {key}."

        deadline = time.monotonic() + 7
        while time.monotonic() < deadline:
            time.sleep(0.2)
            if key == "steam":
                state = self.steam.inspect()
                if state["account_picker_detected"]:
                    self.current_app = key
                    return "CONFIRMED_SUCCESS", "Steam запущен. Вижу окно выбора аккаунта — скажи, какой профиль выбрать."
            procs = self._processes(key)
            if procs:
                wins = enum_windows([p.pid for p in procs])
                if wins or key in {"steam", "telegram", "discord"}:
                    self.current_app = key
                    return "CONFIRMED_SUCCESS", f"Открыла {key}."
        return "SENT_NOT_CONFIRMED", f"Запуск {key} отправила, но состояние пока не подтверждено."

    def _window_status(self, t):
        if any(x in t for x in ("какое окно активно", "какое у меня активное окно", "что сейчас активно", "активное окно")):
            w = active_window()
            if not w:
                return "NOT_FOUND", "Не смогла определить активное окно."
            return "CONFIRMED_SUCCESS", f"Сейчас активно: {w['title'] or w['process']}."
        if any(x in t for x in ("какие окна открыты", "что у меня открыто", "что сейчас открыто", "что ты видишь открытым")):
            wins = list_visible_windows(15)
            if not wins:
                return "NOT_FOUND", "Видимых окон не нашла."
            names = []
            for w in wins:
                label = w['title'] or w['process']
                if label and label not in names:
                    names.append(label)
            return "CONFIRMED_SUCCESS", "Открыты: " + "; ".join(names[:8]) + "."
        if "ты видишь браузер" in t or "какой браузер открыт" in t:
            found = []
            for b in BROWSERS:
                s = self.browser.state(b)
                if s["visible_windows"]:
                    found.append((b, s))
            if not found:
                return "NOT_FOUND", "Открытого окна браузера сейчас не вижу."
            b, s = found[0]
            ans = f"Вижу открытый {b}."
            if s.get("active_tab_title"):
                ans += f" Активная вкладка — {s['active_tab_title']}."
            else:
                ans += " Название активной вкладки подтвердить не удалось."
            return "CONFIRMED_SUCCESS", ans
        if any(x in t for x in ("какая вкладка активна", "какая вкладка открыта", "что открыто в браузере")):
            b = self.current_browser or self.browser.preferred
            s = self.browser.state(b)
            if not s["visible_windows"]:
                return "NOT_FOUND", f"Окно {b} сейчас не вижу."
            title = s.get("active_tab_title")
            if not title:
                return "SENT_NOT_CONFIRMED", f"{b} открыт, но название активной вкладки подтвердить не удалось."
            return "CONFIRMED_SUCCESS", f"В {b} активная вкладка — {title}."
        return None

    def _browser_controls(self, t):
        action = None
        if "новая вкладка" in t or "открой вкладку" in t:
            action = "new_tab"
        elif "закрой вкладку" in t:
            action = "close_tab"
        elif "следующая вкладка" in t or "следующую вкладку" in t:
            action = "next_tab"
        elif "предыдущая вкладка" in t or "предыдущую вкладку" in t:
            action = "prev_tab"
        elif "открой загрузки браузера" in t or "покажи загрузки браузера" in t:
            action = "downloads"
        elif "открой историю браузера" in t or "покажи историю браузера" in t:
            action = "history"
        elif "обнови страницу" in t or t == "обнови":
            action = "refresh"
        elif t in {"назад", "вернись назад"} or "страницу назад" in t:
            action = "back"
        elif t in {"вперед", "вперёд"} or "страницу вперед" in t or "страницу вперёд" in t:
            action = "forward"
        elif "масштаб 100" in t or "сбрось масштаб" in t:
            action = "zoom_reset"
        elif "увеличь страницу" in t or "увеличь масштаб" in t:
            action = "zoom_in"
        elif "уменьши страницу" in t or "уменьши масштаб" in t:
            action = "zoom_out"
        if not action:
            return None
        status, state = self.browser.hotkey(action, self.current_browser)
        friendly = {
            "new_tab": "новую вкладку", "close_tab": "закрытие вкладки", "next_tab": "следующую вкладку",
            "prev_tab": "предыдущую вкладку", "downloads": "загрузки браузера", "history": "историю браузера",
            "refresh": "обновление страницы", "back": "переход назад", "forward": "переход вперёд", "zoom_reset": "масштаб 100%",
            "zoom_in": "увеличение страницы", "zoom_out": "уменьшение страницы",
        }[action]
        if status == "SENT_NOT_CONFIRMED":
            return status, f"Команду на {friendly} отправила, но точное состояние вкладки пока не подтверждаю."
        if status == "CONFIRMED_SUCCESS":
            return status, f"Выполнила: {friendly}."
        return status, f"Не смогла выполнить: {friendly}."

    def _observe_surface_route(self, t):
        tab_question = any(x in t for x in (
            "какая активная вкладка", "какая вкладка открыта", "что за вкладка", "какой сайт открыт",
            "что открыто в браузере", "активная вкладка"
        ))
        observe = any(x in t for x in (
            "что ты видишь", "что ты там видишь", "что ты здесь видишь", "что видишь", "что там видишь", "что здесь видишь", "что там есть",
            "что здесь есть", "что на странице", "что на вкладке", "что отображается", "что на ней отображается",
            "проверь что на ней отображается", "проверь что отображается", "какие видео", "какие ролики",
            "покажи список видео", "перечисли видео", "что передо мной"
        ))
        if not (tab_question or observe):
            return None
        browser = self.current_browser or self.browser.preferred
        snap = self.browser.structured_snapshot(browser, max_age=3.0)
        if not snap:
            return "UNSUPPORTED", "Не получаю свежие данные активной вкладки. Проверь Browser Pack для этого браузера."
        self.current_browser = browser
        self.current_app = browser
        self.current_site = snap.get("site") or self.current_site
        if snap.get("site") == "youtube":
            self.current_media = "youtube_player" if snap.get("page_type") == "VIDEO" else "youtube"
        if tab_question and not observe:
            title = (snap.get("title") or "").strip() or "без названия"
            return "CONFIRMED_SUCCESS", f"Активная вкладка: {title}."
        if snap.get("site") == "youtube":
            status, vids, err = self.youtube.list_visible(limit=8, browser=browser)
            if status == "CONFIRMED_SUCCESS" and vids:
                parts = [f"{i}. {v['title']}" + (f" — {v['channel']}" if v.get('channel') else "") for i, v in enumerate(vids, 1)]
                self.last_target = "youtube_collection"
                return status, "В активной вкладке YouTube вижу: " + "; ".join(parts) + "."
            if snap.get("page_type") == "VIDEO":
                title = (snap.get("title") or "видео").replace(" - YouTube", "").strip()
                media = snap.get("media") or {}
                self.last_media_state = dict(media)
                self.last_target = "youtube_player"
                return "CONFIRMED_SUCCESS", f"Открыто видео «{title}»."
            return status, err or "YouTube открыт, но список видимых видео сейчас не получен."
        title = (snap.get("title") or "").strip() or (snap.get("site") or "страница")
        return "CONFIRMED_SUCCESS", f"В активной вкладке открыта страница «{title}»."

    def _fullscreen_route(self, t):
        if not any(x in t for x in ("полный экран", "весь экран", "fullscreen", "фуллскрин")):
            return None
        browser = self.current_browser or self.browser.preferred
        if "видео" in t or "плеер" in t:
            ok, state = self.browser.ensure_foreground(browser)
            if not ok:
                return "FAILED", "Не смогла вывести браузер с видео на передний план."
            send_hotkey("F")
            self.current_media = "browser_media"
            return "SENT_NOT_CONFIRMED", "Команду полноэкранного режима видео отправила, но состояние плеера пока не умею проверить точно."
        # Browser fullscreen by default when browser context/foreground exists.
        state = self.browser.state(browser)
        fg = active_window()
        if state["visible_windows"] or (fg and any(x in (fg.get('process') or '').lower() for x in ('vivaldi','chrome','msedge','brave','opera','firefox'))):
            status, _ = self.browser.hotkey("fullscreen", browser)
            return status, "Переключила полноэкранный режим браузера." if status == "CONFIRMED_SUCCESS" else "Команду полноэкранного режима браузера отправила; точную проверку режима пока не подтверждаю."
        return "AMBIGUOUS", "Не вижу активного браузера. Скажи, какое окно нужно развернуть или какой браузер перевести на весь экран."

    def _youtube_route(self, t):
        snap = self.youtube.snapshot(self.current_browser)
        if snap:
            self.current_site = "youtube"
            self.current_media = "youtube_player" if snap.get("page_type") == "VIDEO" else "youtube"
            if snap.get("page_type") == "VIDEO":
                self.last_target = "youtube_player"
                self.last_media_state = dict(snap.get("media") or {})

        explicit_youtube = any(x in t for x in ("youtube", "ютуб", "ютьюб"))

        # Ensure/reuse YouTube tab. Existing tab is activated; a new one is created only when none exists.
        if contains_open(t) and explicit_youtube and not any(x in t for x in ("видео", "ролик", "канал")):
            status, _ = self.youtube.ensure_site(self.current_browser)
            if status in {"CONFIRMED_SUCCESS", "ALREADY_SATISFIED", "SENT_NOT_CONFIRMED"}:
                self.current_site = "youtube"
                self.current_app = self.current_browser
                self.last_target = "youtube"
            answer = "YouTube уже открыт — использую существующую вкладку." if status == "ALREADY_SATISFIED" else ("Открыла YouTube." if status == "CONFIRMED_SUCCESS" else "Команду открыть YouTube отправила, но активную вкладку пока не подтверждаю.")
            return status, answer

        # Search uses the active YouTube search box through Browser Pack. Only degraded fallback opens a results URL.
        m = re.search(r"(?:найди|поищи)\s+(?:мне\s+)?(?:на|в)\s+(?:youtube|ютубе|ютуб)\s+(.+)$", t)
        if not m and self.current_site == "youtube" and re.search(r"\b(?:найди|поищи)\b", t) and not any(x in t for x in ("файл", "папк", "в браузере", "в интернете", "гугл")):
            m = re.search(r"(?:найди|поищи)\s+(?:мне\s+)?(.+)$", t)
        if m:
            q = m.group(1).strip()
            q = re.sub(r"^(?:видео|ролик|канал)\s+", "", q).strip()
            status, _ = self.youtube.search_in_page(q, self.current_browser)
            if status in {"CONFIRMED_SUCCESS", "SENT_NOT_CONFIRMED"}:
                self.current_site = "youtube"; self.current_media = "youtube"; self.last_target = "youtube_collection"
            return status, (f"Нашла результаты YouTube по «{q}»." if status == "CONFIRMED_SUCCESS" else f"Поиск YouTube «{q}» отправила, но результаты пока не подтверждаю.")

        if self.current_site != "youtube":
            return None

        if any(x in t for x in ("какие видео", "что за видео", "что ты видишь на странице", "что видишь на странице", "что видишь на ютуб", "что ты видишь на ютуб", "что здесь есть", "какие ролики", "покажи список видео", "перечисли видео")):
            status, vids, err = self.youtube.list_visible(limit=8, browser=self.current_browser)
            if status != "CONFIRMED_SUCCESS": return status, err or "Не удалось получить список видимых видео."
            self.last_target = "youtube_collection"
            parts=[f"{i}. {v['title']}" + (f" — {v['channel']}" if v.get('channel') else "") for i,v in enumerate(vids,1)]
            return status, "Вижу: " + "; ".join(parts) + "."

        ord_words={"первое":1,"первый":1,"первую":1,"второе":2,"второй":2,"вторую":2,"третье":3,"третий":3,"третью":3,"четвертое":4,"четвертый":4,"пятое":5,"пятый":5,"шестое":6,"шестой":6,"седьмое":7,"седьмой":7,"восьмое":8,"восьмой":8}
        ordinal=next((n for w,n in ord_words.items() if re.search(r"\b"+w+r"\b",t)),None)
        if ordinal is not None and any(x in t for x in ("видео","ролик","открой","выбери")):
            status,video,_=self.youtube.open_video(ordinal=ordinal,browser=self.current_browser)
            if status=="CONFIRMED_SUCCESS":
                self.current_media="youtube_player"; self.last_target="youtube_player"; self.last_media_state=self.youtube.media_state(self.current_browser) or {}
                return status,f"Открыла {ordinal}-е видео: {video.get('title','видео')}."
            return status,"Не смогла подтвердить открытие выбранного видео."

        if any(x in t for x in ("слева","справа","снизу","сверху","по центру","центральное","центральный")) and any(x in t for x in ("открой","выбери","видео","ролик")):
            status,video,_=self.youtube.open_video(spatial=t,browser=self.current_browser)
            if status=="CONFIRMED_SUCCESS":
                self.current_media="youtube_player"; self.last_target="youtube_player"; self.last_media_state=self.youtube.media_state(self.current_browser) or {}
                return status,f"Открыла: {video.get('title','видео')}."
            return status,"Не смогла однозначно выбрать видео по положению."

        m=re.search(r"(?:открой|выбери)\s+(?:мне\s+)?(?:видео|ролик)\s+(.+)$",t)
        if m:
            q=m.group(1).strip(); channel=None; cm=re.search(r"(.+?)\s+(?:от|с канала)\s+(.+)$",q)
            if cm:q,channel=cm.group(1).strip(),cm.group(2).strip()
            status,video,candidates=self.youtube.open_video(query=q,channel=channel,browser=self.current_browser)
            if status=="CONFIRMED_SUCCESS":
                self.current_media="youtube_player"; self.last_target="youtube_player"; self.last_media_state=self.youtube.media_state(self.current_browser) or {}
                return status,f"Открыла видео «{video.get('title','')}»"+(f" от {video.get('channel')}" if video.get('channel') else "")+"."
            if status=="AMBIGUOUS": return status,"Вижу несколько похожих: "+"; ".join(v.get('title','') for v in candidates[:3])+". Уточни, какое открыть."
            if status=="NOT_FOUND":
                sq=q+(f" {channel}" if channel else ""); s2,_=self.youtube.search_in_page(sq,self.current_browser); return "SENT_NOT_CONFIRMED" if s2!="FAILED" else s2,f"На текущей странице совпадения не нашла. Ищу на YouTube «{sq}»."
            return status,"Не вижу структурный список этой страницы. Проверь Browser Pack."

        # Pronoun follow-up after a referenced list item/title.
        if re.search(r"\bоткрой\s+(?:его|это|это видео)\b",t) and self.youtube.last_selected:
            status,video,_=self.youtube.open_video(query=self.youtube.last_selected.get('title',''),browser=self.current_browser)
            if status=="CONFIRMED_SUCCESS":
                self.current_media="youtube_player"; self.last_target="youtube_player"; self.last_media_state=self.youtube.media_state(self.current_browser) or {}
            return status, "Открыла видео." if status=="CONFIRMED_SUCCESS" else "Не смогла подтвердить открытие видео."

        # Player scope wins over browser/system scope while a VIDEO page is active.
        page_type=(self.youtube.snapshot(self.current_browser) or {}).get("page_type")
        player_context=page_type=="VIDEO" or self.current_media=="youtube_player" or self.last_target=="youtube_player"
        exit_fullscreen = player_context and (
            any(x in t for x in ("выйди из полного", "выйди из полноэкран", "убери полный экран", "убери полноэкран", "не на весь экран", "обычный режим", "верни обычный режим"))
            or ("сверни" in t and any(x in t for x in ("видео", "плеер", "это видео")))
            or ("убери" in t and any(x in t for x in ("видео", "плеер")) and ("экран" in t or "режим" in t))
        )
        enter_fullscreen = player_context and any(x in t for x in ("полный экран", "весь экран", "fullscreen", "фуллскрин")) and not exit_fullscreen
        if exit_fullscreen or enter_fullscreen:
            desired = not exit_fullscreen
            status,state=self.youtube.media_action("set_fullscreen",desired,browser=self.current_browser)
            if isinstance(state,dict): self.last_media_state=dict(state)
            self.current_media="youtube_player"; self.last_target="youtube_player"
            if status in {"CONFIRMED_SUCCESS","ALREADY_SATISFIED"}: return status,("Видео на весь экран." if desired else "Вышла из полноэкранного режима видео.")
            return status,"Команду полноэкранного режима видео отправила, но состояние не подтверждаю."
        if t in {"пауза","поставь на паузу"} or "пауза видео" in t:
            status,state=self.youtube.media_action("pause",browser=self.current_browser); self.last_target="youtube_player"; self.last_media_state=dict(state or {}) if isinstance(state,dict) else {}; return status,"Поставила видео на паузу." if status=="CONFIRMED_SUCCESS" else "Команду паузы отправила."
        if t in {"продолжи","продолжай","включи видео","продолжи видео"}:
            status,state=self.youtube.media_action("play",browser=self.current_browser); self.last_target="youtube_player"; self.last_media_state=dict(state or {}) if isinstance(state,dict) else {}; return status,"Продолжила воспроизведение." if status=="CONFIRMED_SUCCESS" else "Команду продолжить видео отправила."

        system_scope = any(x in t for x in ("систем", "на ноут", "ноуте", "ноутбук", "компьютер", "на комп", "windows", "виндовс"))
        if player_context and not system_scope and any(x in t for x in ("выключи звук", "замуть", "mute", "без звука")):
            status,state=self.youtube.media_action("mute",browser=self.current_browser); self.last_target="youtube_player"; self.last_media_state=dict(state or {}) if isinstance(state,dict) else {}; return status,"Выключила звук видео." if status=="CONFIRMED_SUCCESS" else "Команду mute видео отправила."
        if player_context and not system_scope and any(x in t for x in ("включи звук", "верни звук", "unmute")):
            status,state=self.youtube.media_action("unmute",browser=self.current_browser); self.last_target="youtube_player"; self.last_media_state=dict(state or {}) if isinstance(state,dict) else {}; return status,"Включила звук видео." if status=="CONFIRMED_SUCCESS" else "Команду unmute видео отправила."
        seek=self.youtube.parse_seek(t)
        if seek and player_context:
            seconds,direction=seek; signed=seconds if direction=="forward" else -seconds; status,state=self.youtube.media_action("seek_relative",signed,browser=self.current_browser); self.last_target="youtube_player"; self.last_media_state=dict(state or {}) if isinstance(state,dict) else {}; return status,f"Перемотала на {seconds} секунд {'вперёд' if direction=='forward' else 'назад'}." if status=="CONFIRMED_SUCCESS" else "Команду перемотки отправила."
        if player_context and not system_scope and (any(x in t for x in ("видео громче","громче видео","плеер громче")) or t in {"громче","чуть громче"}):
            status,state=self.youtube.media_action("change_volume",.10,browser=self.current_browser); self.last_target="youtube_player"; self.last_media_state=dict(state or {}) if isinstance(state,dict) else {}; pct=round(float((state or {}).get('volume',0))*100) if status=="CONFIRMED_SUCCESS" else None; return status,f"Громкость видео {pct}%." if pct is not None else "Команду сделать видео громче отправила."
        if player_context and not system_scope and (any(x in t for x in ("видео тише","тише видео","плеер тише","сделай видео тише")) or t in {"тише","чуть тише"}):
            status,state=self.youtube.media_action("change_volume",-.10,browser=self.current_browser); self.last_target="youtube_player"; self.last_media_state=dict(state or {}) if isinstance(state,dict) else {}; pct=round(float((state or {}).get('volume',0))*100) if status=="CONFIRMED_SUCCESS" else None; return status,f"Громкость видео {pct}%." if pct is not None else "Команду сделать видео тише отправила."
        m=re.search(r"(?:громкость\s+видео|видео\s+громкость|звук\s+видео|сделай\s+видео)\s*(?:на\s*)?(\d{1,3})\s*%?",t)
        if not m and player_context and not system_scope and any(x in t for x in ("громк", "звук", "на ноль", "минимум", "максимум")):
            pct=self._number_word_percent(t)
            if pct is not None:
                m=(pct,)
        if m and player_context and not system_scope:
            value=(max(0,min(100,int(m.group(1))))/100) if hasattr(m,'group') else max(0,min(100,float(m[0])))/100
            status,state=self.youtube.media_action("set_volume",value,browser=self.current_browser); self.last_target="youtube_player"; self.last_media_state=dict(state or {}) if isinstance(state,dict) else {}; return status,f"Громкость видео {round(value*100)}%." if status=="CONFIRMED_SUCCESS" else "Команду громкости видео отправила."
        m=re.search(r"скорост(?:ь|и)\s*(?:видео\s*)?(?:на\s*)?(0[.,]25|0[.,]5|1(?:[.,](?:25|5|75))?|2)",t)
        if m and player_context:
            value=float(m.group(1).replace(',','.')); status,state=self.youtube.media_action("set_rate",value,browser=self.current_browser); self.last_target="youtube_player"; self.last_media_state=dict(state or {}) if isinstance(state,dict) else {}; return status,f"Скорость видео {value:g}x." if status=="CONFIRMED_SUCCESS" else "Команду скорости видео отправила."
        return None

    def _filesystem_route(self, t):
        if any(x in t for x in ("рабочий стол", "загрузки", "документы", "картинки", "изображения")) and contains_open(t):
            msg = self.files.open_known_folder(t)
            if msg:
                return "SENT_NOT_CONFIRMED", msg
        m = re.search(r"(?:найди|поищи)\s+(?:мне\s+)?файл\s+(.+)$", t)
        if m:
            status, best, msg = self.files.find_file(m.group(1).strip())
            return status, msg
        m = re.search(r"(?:открой|открыть)\s+(?:мне\s+)?файл\s+(.+)$", t)
        if m:
            return self.files.open_file(m.group(1).strip())
        m = re.search(r"создай\s+папку\s+(.+?)(?:\s+(?:в|на)\s+(.+))?$", t)
        if m:
            return self.files.create_folder(m.group(1), m.group(2) or '')
        if ("скопируй" in t or "копируй" in t) and self.files.last_found:
            return self.files.move_last_found(t, copy=True)
        if "перемести" in t and self.files.last_found:
            return self.files.move_last_found(t, copy=False)
        if any(x in t for x in ("в корзину", "отправь в корзину")) and self.files.last_found:
            return self.files.trash_last_found()
        return None

    def _execute_clause(self, raw):
        t = norm(raw)
        if not t:
            return False, None

        if any(x in t for x in ("какая у тебя версия", "какая версия", "версия векси", "твоя версия", "что за версия")):
            return self._log_result("runtime", "VERSION", "CONFIRMED_SUCCESS", f"Сейчас запущена Vexi v{__version__}, канал {__channel__}, сборка {__build__}.", __version__)
        if any(x in t for x in ("статус browser bridge", "статус браузер бридж", "browser bridge работает", "бридж браузера работает")):
            st = self.browser.bridge_status()
            if st.get("connected"):
                return self._log_result("browser", "BRIDGE_STATUS", "CONFIRMED_SUCCESS", f"Browser Pack подключён к активной вкладке. Сайт: {st.get('site') or 'неизвестно'}, страница: {st.get('page_type') or 'неизвестно'}.")
            return self._log_result("browser", "BRIDGE_STATUS", "NOT_FOUND", "Browser Pack не подключён к активной вкладке. Открой Настройки → Плагины и проверь пакет браузера.")

        guard = self.policy.guard_text(t)
        if guard:
            return self._log_result("policy", "BLOCKED_HIGH_RISK", guard[0], guard[1])

        ir = self._identity_route(t)
        if ir:
            return self._log_result("identity", "ASSISTANT_IDENTITY", ir[0], ir[1], self.identity.display_name())

        sr = self._security_route(t)
        if sr:
            return self._log_result("security", "SECURITY_SETTINGS", sr[0], sr[1])

        handled, answer = self._memory_route(t, raw)
        if handled:
            return self._log_result("memory", "MEMORY", "CONFIRMED_SUCCESS", answer)

        ws = self._window_status(t)
        if ws:
            return self._log_result("window", "STATUS", ws[0], ws[1])

        obs = self._observe_surface_route(t)
        if obs:
            return self._log_result("browser", "OBSERVE_ACTIVE_SURFACE", obs[0], obs[1], self.current_site or self.current_browser)

        ar = self._audio_route(t)
        if ar:
            return self._log_result("audio", "SET_PROPERTY", ar[0], ar[1], "system_volume")

        dr = self._display_route(t)
        if dr:
            return self._log_result("display", "DISPLAY_CONTROL", dr[0], dr[1], "display")

        fs = self._filesystem_route(t)
        if fs:
            return self._log_result("filesystem", "FILESYSTEM", fs[0], fs[1])

        yt = self._youtube_route(t)
        if yt:
            return self._log_result("youtube", "SERVICE_ACTION", yt[0], yt[1], "youtube")

        full = self._fullscreen_route(t)
        if full:
            return self._log_result("browser", "FULLSCREEN", full[0], full[1], self.current_browser)

        bc = self._browser_controls(t)
        if bc:
            return self._log_result("browser", "BROWSER_CONTROL", bc[0], bc[1], self.current_browser)

        # Steam account picker commands.
        if self.current_app == "steam" and ("выбери" in t or "аккаунт" in t or "профиль" in t):
            m = re.search(r"(?:выбери|аккаунт|профиль)\s+(?:steam\s+)?(.+)$", t)
            requested = m.group(1).strip() if m else ("основной" if "основ" in t else "")
            status, msg = self.steam.choose_profile(requested)
            return self._log_result("steam", "SELECT_PROFILE", status, msg, requested)

        # Known direct site / web resource.
        sites = site_targets(t)
        apps = self.registry.targets_in_text(t)
        open_intent = contains_open(t)

        # Browser role phrase: "Steam в Vivaldi" means Steam website in browser.
        if open_intent and "steam" in apps and any(b in apps for b in BROWSERS) and re.search(r"\bв\b", t):
            browser = next((b for b in apps if b in BROWSERS), self.current_browser)
            status, _ = self.browser.open_url(SITE_URLS["steam_site"], browser)
            self.current_browser = browser
            self.current_site = "steam_site"
            return self._log_result("browser", "OPEN_SITE", status, f"Открываю Steam в {browser}." if status == "CONFIRMED_SUCCESS" else f"Команду открыть Steam в {browser} отправила, но страницу пока не подтверждаю.", "steam_site")

        if open_intent and sites:
            # Steam support/resource takes precedence over generic Steam app.
            key = "steam_support" if "steam_support" in sites else sites[0]
            browser = next((a for a in apps if a in BROWSERS), self.current_browser)
            status, _ = self.browser.ensure_site(key, SITE_URLS[key], browser)
            self.current_browser = browser
            self.current_app = browser
            self.current_site = key
            answer = f"Открыла {key} в {browser}." if status == "CONFIRMED_SUCCESS" else f"Команду открыть {key} в {browser} отправила, но страницу пока не подтверждаю."
            return self._log_result("browser", "OPEN_SITE", status, answer, key)

        # Explicit web search.
        m = re.search(r"(?:найди|поищи|загугли)\s+(?:мне\s+)?(?:в\s+браузере\s+)?(.+)$", t)
        if m and not any(x in t for x in ("файл", "папк")):
            q = m.group(1).strip()
            status, _ = self.browser.open_url("https://www.google.com/search?q=" + quote_plus(q), self.current_browser)
            self.current_site = "google"
            return self._log_result("browser", "WEB_SEARCH", status, f"Ищу: {q}." if status == "CONFIRMED_SUCCESS" else f"Поиск «{q}» отправила, но страницу пока не подтверждаю.", q)

        # App window controls.
        app_target = None
        if len(apps) == 1:
            app_target = apps[0]
        elif not apps and any(x in t.split() for x in ("его", "ее", "её")) and self.current_app:
            app_target = self.current_app

        if "сверни" in t:
            if not app_target:
                return self._log_result("window", "MINIMIZE", "AMBIGUOUS", "Не поняла, какое приложение нужно свернуть.")
            procs = self._processes(app_target)
            if not procs:
                return self._log_result("window", "MINIMIZE", "NOT_FOUND", f"{app_target} сейчас не запущен.", app_target)
            ok = minimize_processes(procs)
            return self._log_result("window", "MINIMIZE", "CONFIRMED_SUCCESS" if ok else "SENT_NOT_CONFIRMED", f"Свернула {app_target}." if ok else f"Команду свернуть {app_target} отправила, но состояние не подтверждено.", app_target)

        if "разверни" in t:
            if not app_target:
                return self._log_result("window", "MAXIMIZE", "AMBIGUOUS", "Не поняла, какое приложение нужно развернуть.")
            procs = self._processes(app_target)
            if not procs:
                return self._log_result("window", "MAXIMIZE", "NOT_FOUND", f"{app_target} сейчас не запущен.", app_target)
            ok = maximize_processes(procs)
            return self._log_result("window", "MAXIMIZE", "CONFIRMED_SUCCESS" if ok else "SENT_NOT_CONFIRMED", f"Развернула {app_target}." if ok else f"Команду развернуть {app_target} отправила, но состояние не подтверждено.", app_target)

        if any(x in t for x in ("покажи", "выведи", "переключись на")):
            if not app_target:
                return self._log_result("window", "FOCUS", "AMBIGUOUS", "Не поняла, какое приложение нужно показать.")
            procs = self._processes(app_target)
            if not procs:
                return self._log_result("window", "FOCUS", "NOT_FOUND", f"{app_target} сейчас не запущен.", app_target)
            ok = focus_processes(procs)
            if ok:
                self.current_app = app_target
            return self._log_result("window", "FOCUS", "CONFIRMED_SUCCESS" if ok else "SENT_NOT_CONFIRMED", f"Вывела {app_target} вперёд." if ok else f"{app_target} запущен, но фокус окна не подтверждён.", app_target)

        if "заверши" in t:
            if not app_target:
                return self._log_result("app", "TERMINATE", "AMBIGUOUS", "Не поняла, какой процесс завершить.")
            procs = self._processes(app_target)
            if not procs:
                return self._log_result("app", "TERMINATE", "NOT_FOUND", f"{app_target} не запущен.", app_target)
            for p in procs:
                try:
                    p.terminate()
                except Exception:
                    pass
            return self._log_result("app", "TERMINATE", "SENT_NOT_CONFIRMED", f"Команду завершить {app_target} отправила.", app_target)

        if re.search(r"\bзакрой\b", t):
            if not app_target:
                return self._log_result("app", "CLOSE_WINDOW", "AMBIGUOUS", "Не поняла, какое приложение нужно закрыть.")
            procs = self._processes(app_target)
            if not procs:
                return self._log_result("app", "CLOSE_WINDOW", "NOT_FOUND", f"{app_target} уже не запущен.", app_target)
            ok = close_process_windows(procs)
            return self._log_result("app", "CLOSE_WINDOW", "SENT_NOT_CONFIRMED" if ok else "NOT_FOUND", f"Команду закрыть окно {app_target} отправила." if ok else f"Обычного окна {app_target} не нашла.", app_target)

        # Status of a known app.
        if apps and any(x in t for x in ("открыт", "запущен", "работает")) and not open_intent:
            key = apps[0]
            if key == "explorer":
                wins = explorer_windows()
                return self._log_result("app", "STATUS", "CONFIRMED_SUCCESS", "Проводник открыт." if wins else "Окно Проводника не открыто.", key)
            procs = self._processes(key)
            if not procs:
                return self._log_result("app", "STATUS", "CONFIRMED_SUCCESS", f"{key} не запущен.", key)
            wins = enum_windows([p.pid for p in procs])
            return self._log_result("app", "STATUS", "CONFIRMED_SUCCESS", f"{key} открыт." if wins else f"{key} запущен в фоне.", key)

        # Multi-open apps only when explicit coordination exists.
        if open_intent and len(apps) > 1 and " и " in t and not any(b in apps for b in BROWSERS):
            msgs = []
            for key in apps:
                status, msg = self._app_open(key)
                msgs.append(msg)
            return self._log_result("planner", "MULTI_OPEN", "CONFIRMED_SUCCESS", " ".join(msgs), ",".join(apps))
        if open_intent and len(apps) > 1 and " и " in t:
            # If all are independent app targets, execute all. Role phrases with "в <browser>" were handled above.
            if not re.search(r"\bв\s+(?:vivaldi|вивальди|chrome|хром|edge|эдж|brave|opera|firefox)\b", t):
                msgs = []
                for key in apps:
                    status, msg = self._app_open(key)
                    msgs.append(msg)
                return self._log_result("planner", "MULTI_OPEN", "CONFIRMED_SUCCESS", " ".join(msgs), ",".join(apps))

        if open_intent and app_target:
            status, msg = self._app_open(app_target)
            return self._log_result("app", "OPEN_APP", status, msg, app_target)

        # Direct domain/url.
        if open_intent:
            m = re.search(r"(?:открой|открыть|открывай)\s+(?:мне\s+)?(.+)$", t)
            if m:
                q = clean_query(m.group(1))
                if re.match(r"^https?://", q):
                    status, _ = self.browser.open_url(q, self.current_browser)
                    return self._log_result("browser", "OPEN_URL", status, "Открыла адрес." if status == "CONFIRMED_SUCCESS" else "Команду открыть адрес отправила, но страницу не подтверждаю.", q)
                if re.match(r"^[\w\-]+\.(com|net|org|de|io|ai|app|dev|ru|ua)(/.*)?$", q):
                    status, _ = self.browser.open_url("https://" + q, self.current_browser)
                    return self._log_result("browser", "OPEN_URL", status, f"Открыла {q}." if status == "CONFIRMED_SUCCESS" else f"Команду открыть {q} отправила, но страницу не подтверждаю.", q)
            return self._log_result("router", "OPEN", "AMBIGUOUS", "Не поняла, что именно нужно открыть.")

        if any(x in t for x in ("где я", "моя геолокация", "мое местоположение", "моё местоположение")):
            return self._log_result("location", "STATUS", "UNSUPPORTED", "Location Adapter пока не включён. Геолокацию Windows не запрашиваю.")
        if any(x in t for x in ("окулус", "quest", "квест 3", "квест 3s")):
            return self._log_result("device", "STATUS", "UNSUPPORTED", "Quest Device Adapter пока не включён. На гарнитуре ничего не выполняю.")

        # Incomplete known-entity phrase: ask instead of guessing.
        if apps or sites:
            entities = apps + sites
            return self._log_result("router", "INCOMPLETE", "AMBIGUOUS", "Что сделать с " + ", ".join(entities) + "?")

        # PC-like request with unsupported capability must never fall through as fake success.
        if self._looks_like_command(t):
            return self._log_result("router", "UNSUPPORTED", "UNSUPPORTED", "Эту команду управления ПК я пока не умею выполнять. Ничего не сделала.")

        return False, None
