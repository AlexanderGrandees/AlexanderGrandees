"""Pre-release public-topic conversation. No arbitrary data classification fallback.

Only complete, bounded grammar matches enter the model. No tools, files, owner
memory, transcript logs or remote endpoint. Extend topics explicitly with tests.
"""
import json
import hashlib
import queue
import re
import threading
import time
from urllib.parse import urlsplit
import requests
from speech_input import phrase
from vexi_foundation.dialogue_context import DialogueContext
from vexi_foundation.contracts import Actor, Scope, DataClass
from vexi_foundation.policy import (CapabilityPolicy, OwnerAuthority, Capability,
                                    PrivacyContext, PermissionRequest, PolicyDecision)


TOPICS = ("космос", "космосе", "звезды", "звездах", "черные дыры", "черных дырах",
          "искусственный интеллект", "искусственном интеллекте", "роботы", "роботах",
          "музыка", "музыке", "кино", "книги", "книгах", "игры", "играх",
          "сталкер", "сталкере", "природа", "природе", "океан", "океане")
_TOPIC = "(?:" + "|".join(re.escape(t) for t in TOPICS) + ")"
_START = re.compile(r"(?:(?:расскажи|поговорим|давай поговорим)(?: мне)? (?:про|о|об) " + _TOPIC +
                    r"|объясни (?:как работает искусственный интеллект|почему небо голубое)"
                    r"|почему небо голубое"
                    r"|(?:предложи|придумай)(?: мне)? (?:два|три|2|3) варианта (?:отдыха|вечера|досуга)(?: дома)?"
                    r"|(?:чем заняться|как отдохнуть)(?: вечером)?(?: дома)?)")
_FOLLOW = re.compile(r"(?:(?:а )?(?:первый|второй|третий)(?: вариант)?(?: подробнее)?"
                     r"|(?:расскажи|объясни)(?: это)? (?:подробнее|проще|короче)"
                     r"|подробнее|проще|короче|приведи пример|еще пример|другой пример"
                     r"|(?:а )?почему|(?:а )?как это работает|что это значит"
                     r"|(?:нет )?(?:лучше )?дома|(?:а )?подешевле|без денег|без компьютера"
                     r"|другие варианты|еще варианты|продолжай рассказ|продолжим разговор)")
FORGET = {"забудь разговор", "забудь этот разговор", "очисти разговор"}
NEW = {"новая тема", "сменим тему"}
CHAT_START = {"давай поговорим", "поговорим"}
HELP = "Можем поговорить о космосе, музыке, кино, играх или придумать варианты отдыха дома. О чём поговорим?"
UNAVAILABLE = "Локальная модель сейчас недоступна. Тему сохранила; попробуй повторить вопрос позже."
_CLAIM = re.compile(r"\b(?:я\s+)?(?:открыл[аи]?|удалил[аи]?|сохранил[аи]?|отправил[аи]?|запустил[аи]?|переместил[аи]?|переименовал[аи]?)\b", re.I)


def public_start(text):
    return bool(_START.fullmatch(phrase(text)))


def public_followup(text):
    return bool(_FOLLOW.fullmatch(phrase(text)))


class LocalModelError(Exception):
    """Static reason only, never payload or server response."""


class LocalConversationClient:
    def __init__(self, url="http://127.0.0.1:11434", model="qwen3:4b-instruct-2507-q4_K_M", deadline=60):
        parsed = urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or
                parsed.port != 11434 or parsed.username or parsed.password or
                parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ValueError("local_endpoint_required")
        if not isinstance(model, str) or not re.fullmatch(r"[\w.:-]{1,100}", model):
            raise ValueError("invalid_model")
        self.url = "http://127.0.0.1:11434/api/chat"
        self.model = model
        self.deadline = max(1, min(float(deadline), 60))
        self._lock = threading.Lock()

    def generate(self, messages, *, cancelled=lambda: False):
        if len(messages) > 27 or sum(len(m["content"]) for m in messages) > 15000:
            raise LocalModelError("input_limit")
        if not self._lock.acquire(blocking=False):
            raise LocalModelError("busy")
        result = queue.Queue(maxsize=1)
        stop = threading.Event()
        def worker():
            try:
                # No inherited proxy, redirect, automatic server start or model download.
                with requests.Session() as session:
                    session.trust_env = False
                    with session.post(self.url, json={"model": self.model, "messages": messages,
                            "stream": False, "keep_alive": "5m", "options": {
                                "temperature": .2, "num_ctx": 6144, "num_predict": 256}},
                            timeout=(2, 60), allow_redirects=False, stream=True) as response:
                        if response.status_code != 200:
                            raise LocalModelError("server_unavailable")
                        body = bytearray()
                        for chunk in response.iter_content(4096):
                            if stop.is_set(): raise LocalModelError("cancelled")
                            body.extend(chunk)
                            if len(body) > 32768: raise LocalModelError("response_limit")
                        data = json.loads(body)
                        answer = data["message"]["content"]
                        if (data.get("done") is not True or data.get("done_reason") == "length" or
                                data["message"].get("tool_calls") or not isinstance(answer, str) or
                                not answer.strip() or len(answer) > 4000):
                            raise LocalModelError("invalid_response")
                        if not stop.is_set(): result.put((True, answer.strip()))
            except Exception:
                if not stop.is_set(): result.put((False, "model_unavailable"))
            finally:
                self._lock.release()
        threading.Thread(target=worker, daemon=True, name="vexi-local-dialogue").start()
        end = time.monotonic() + self.deadline
        try:
            while time.monotonic() < end:
                if cancelled(): raise LocalModelError("cancelled")
                try:
                    ok, value = result.get(timeout=.05)
                except queue.Empty:
                    continue
                if not ok: raise LocalModelError(value)
                return value
            raise LocalModelError("deadline")
        finally:
            stop.set()


class LocalDialogue:
    def __init__(self, config, client=None):
        self.context = DialogueContext()
        self.client = client
        self.config = config
        self.reply_until = 0
        self.last_answer = None
        self.options = {}
        self.policy = CapabilityPolicy(OwnerAuthority())
        self.actor = Actor("public-dialogue", self.context._session)

    @property
    def active(self):
        return bool(self.context.objective)

    def allows(self, text, now):
        return (self.active and 0 < now <= self.reply_until and
                (public_followup(text) or phrase(text) in FORGET | NEW))

    def handled(self, text):
        return public_start(text) or phrase(text) in FORGET | NEW | CHAT_START or (self.active and public_followup(text))

    def pause(self):
        self.reply_until = 0
        self.context.pause()

    def forget(self):
        self.context.close()
        self.context = DialogueContext()
        self.actor = Actor("public-dialogue", self.context._session)
        self.reply_until = 0
        self.last_answer = None
        self.options = {}

    def answer(self, text, *, name_mode="rare", cancelled=lambda: False):
        key = phrase(text)
        if key in FORGET:
            self.forget(); return "Контекст этого разговора очищен."
        if key in NEW:
            self.forget(); return HELP
        if key in CHAT_START: return HELP
        if not self.handled(text): return None
        if public_start(text):
            # An explicit new topic replaces conversation context, not executor tasks.
            self.forget()
            self.context.set_objective(key)
        ticket = self.context.begin_turn(key)
        privacy = PrivacyContext(frozenset({DataClass.PUBLIC}), "public_conversation",
            frozenset({"LOCAL_MODEL"}), "session_RAM", "explicit_close_or_process_exit",
            "not-applicable", "bounded_public_grammar", "loopback")
        request = PermissionRequest(str(ticket.revision), self.actor, Scope("local", "public-dialogue"),
            Capability.PUBLIC_QUESTION, "ollama:local-public-chat", hashlib.sha256(key.encode()).hexdigest(),
            str(ticket.revision), privacy, "LOCAL_MODEL", target_public=True)
        if self.policy.evaluate(request, time.monotonic()) != PolicyDecision.ALLOW:
            self.context.cancel()
            return "Локальный диалог недоступен по текущим разрешениям."
        prompt = ("You are Vexi. Reply only in natural Russian, using 1-3 short sentences. "
                  "Use plain literal language, no poetic imagery or metaphors. "
                  "Answer the latest question using the conversation; keep the same activity when elaborating. "
                  "You have no tools or access to files or devices. Never claim you performed an action. "
                  "Do not invent personal details or address the user by a name. "
                  "Suggest ordinary practical activities. Do not repeat an answer verbatim: adapt it to the new constraint. "
                  "Game discussions refer to fictional worlds.")
        model_messages = self.context.messages(ticket)
        wanted_options = (3 if re.search(r"\b(?:три|3)\b", key) else 2) if key.startswith(("предложи", "придумай")) else 0
        if wanted_options:
            prompt += f" Дай ровно {wanted_options} варианта. Каждый отдельной строкой: 1) текст, 2) текст. Без вводного текста."
        selected = next((i for word, i in (("первый", 1), ("второй", 2), ("третий", 3)) if word in key.split()), None)
        if selected is not None:
            if selected not in self.options:
                self.context.cancel()
                return "Не могу однозначно определить этот вариант. Назови его словами или попроси новые варианты."
            model_messages[-1]["content"] = (key + ". Раскрой именно этот ранее предложенный вариант: " +
                                              self.options[selected] + ". Не заменяй его другим занятием.")
        try:
            if self.client is None:
                self.client = LocalConversationClient(self.config.get("ollama_url", "http://127.0.0.1:11434"),
                                                      self.config.get("llm_model", "qwen3:4b-instruct-2507-q4_K_M"))
            answer = self.client.generate([{"role": "system", "content": prompt}] + model_messages,
                                          cancelled=cancelled)
            if cancelled():
                self.context.cancel(); return None
            if _CLAIM.search(answer) or "<think>" in answer:
                self.context.cancel()
                return "Ответ модели не прошёл проверку. Попробуй переформулировать вопрос."
            if wanted_options:
                matches = re.findall(r"(?:^|\n)\s*([1-3])[).]\s*(.+?)(?=\n\s*[1-3][).]|$)", answer, re.S)
                options = {int(i): value.strip() for i, value in matches}
                if set(options) != set(range(1, wanted_options + 1)):
                    self.context.cancel()
                    return "Модель не разделила варианты достаточно чётко. Попроси варианты ещё раз."
                self.options = options
            if not self.context.commit(ticket, answer): return None
            self.last_answer = answer
            return answer
        except (LocalModelError, ValueError):
            self.context.cancel()
            return None if cancelled() else UNAVAILABLE
