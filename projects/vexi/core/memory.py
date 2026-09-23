import os
import re
from pathlib import Path

from memory_store import MemoryStore

SECRET_WORDS = ("пароль", "password", "токен", "token", "steam guard", "код восстановления", "recovery code", "2fa")


class PersonalMemory:
    def __init__(self, base_dir=None):
        root = Path(base_dir or (Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Vexi" / "data"))
        self.store = MemoryStore(root / "memory.db")
        self.session = {}
        self.pending_onboarding = None
        if self.consent() is True:
            self.touch_session()


    def touch_session(self):
        import time
        now = time.time()
        if self.store.get("meta", "first_met_at") is None:
            self.store.set("meta", "first_met_at", now, source="runtime", user_confirmed=False)
        count = int(self.store.get("meta", "session_count", 0) or 0) + 1
        self.store.set("meta", "session_count", count, source="runtime", user_confirmed=False)
        self.store.set("meta", "last_seen_at", now, source="runtime", user_confirmed=False)

    def consent(self):
        return self.store.get("system", "memory_consent", None)

    def set_consent(self, value):
        self.store.set("system", "memory_consent", bool(value), source="user_explicit", user_confirmed=True)

    def profile_name(self):
        return self.store.get("identity", "preferred_name")

    def preferred_browser(self):
        return self.store.get("preference", "preferred_browser")

    def onboarding_prompt(self):
        consent = self.consent()
        if consent is None:
            self.pending_onboarding = "consent"
            return "Привет, я Векси. Я могу запоминать твои предпочтения локально на этом устройстве. Разрешаешь включить личную память?"
        if consent and not self.profile_name():
            self.pending_onboarding = "name"
            return "Как мне к тебе обращаться?"
        return None

    def handle_onboarding(self, text):
        if self.pending_onboarding == "consent":
            t = text.lower()
            yes = any(x in t for x in ("да", "разреш", "можно", "включ", "ок", "конечно"))
            no = any(x in t for x in ("нет", "не надо", "не разреш", "выключ"))
            if yes:
                self.set_consent(True)
                self.touch_session()
                self.pending_onboarding = "name"
                return True, "Хорошо. Как мне к тебе обращаться?", True
            if no:
                self.set_consent(False)
                self.pending_onboarding = None
                return True, "Хорошо. Долговременную личную память не включаю.", False
            return True, "Скажи просто: да, можно запоминать, или нет.", True
        if self.pending_onboarding == "name":
            name = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE).strip()
            name = re.sub(r"^(?:меня зовут|зови меня|можешь звать меня|я)\s+", "", name, flags=re.I).strip()
            if 1 <= len(name) <= 40:
                if self.consent():
                    self.store.set("identity", "preferred_name", name, source="onboarding", user_confirmed=True)
                self.session["preferred_name"] = name
                self.pending_onboarding = None
                return True, f"Приятно познакомиться, {name}. Я запомнила.", False
            return True, "Не расслышала имя. Как к тебе обращаться?", True
        return False, None, False

    def prompt_context(self):
        items = []
        name = self.profile_name() or self.session.get("preferred_name")
        if name:
            items.append(f"Имя/обращение владельца: {name}")
        browser = self.preferred_browser()
        if browser:
            items.append(f"Предпочитаемый браузер: {browser}")
        style = self.store.get("preference", "response_style")
        if style:
            items.append(f"Предпочтение по ответам: {style}")
        if not items:
            return ""
        return "\nИз локальной памяти пользователя:\n- " + "\n- ".join(items)

    def remember_statement(self, text):
        t = text.strip()
        low = t.lower()
        if any(secret in low for secret in SECRET_WORDS):
            return True, "Секреты, пароли и коды я в личную память не сохраняю."
        if not self.consent():
            return True, "Личная память сейчас выключена. Сначала разреши мне сохранять предпочтения локально."
        body = re.sub(r"^(?:запомни(?:,| что)?|помни(?:,| что)?)\s*", "", t, flags=re.I).strip(" .")
        m = re.search(r"(?:мой|основной)\s+браузер\s+(?:это\s+)?(.+)$", body, flags=re.I)
        if m:
            value = m.group(1).strip(" .")
            self.store.set("preference", "preferred_browser", value, source="user_explicit", user_confirmed=True)
            return True, f"Запомнила: основной браузер — {value}."
        m = re.search(r"(?:зови меня|обращайся ко мне как)\s+(.+)$", body, flags=re.I)
        if m:
            value = m.group(1).strip(" .")
            self.store.set("identity", "preferred_name", value, source="user_explicit", user_confirmed=True)
            return True, f"Хорошо, буду обращаться: {value}."
        self.store.set("note", f"user_note_{abs(hash(body))}", body, source="user_explicit", user_confirmed=True)
        return True, "Запомнила."

    def summary(self):
        rows = [r for r in self.store.all_active(50) if r["kind"] not in {"system"}]
        if not rows:
            return "Пока долговременных воспоминаний о тебе нет."
        parts = []
        for r in rows[:12]:
            if r["kind"] == "identity" and r["key"] == "preferred_name":
                parts.append(f"обращаться к тебе как {r['value']}")
            elif r["kind"] == "preference" and r["key"] == "preferred_browser":
                parts.append(f"основной браузер: {r['value']}")
            elif r["kind"] == "note":
                parts.append(str(r["value"]))
        return "Я помню: " + "; ".join(parts) + "." if parts else "Пока полезных долговременных воспоминаний нет."
