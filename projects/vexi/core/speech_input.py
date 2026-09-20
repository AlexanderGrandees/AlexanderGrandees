"""Local, volatile speech filtering. No logging, storage, or model calls."""
import re
from dataclasses import dataclass

_WORDS = re.compile(r"[\w]+", re.UNICODE)
_HESITATION = re.compile(r"(?:м+|х+м+|э+м*|а+|и+|m+|h+m+|u+h+|u+m+|e+r+m*)", re.I)
_FILLERS = {"ну", "ээ", "эм", "хм", "мм", "ммм", "мгм"}


def is_hesitation(word):
    return word.lower() in _FILLERS or bool(_HESITATION.fullmatch(word))


def meaningful_speech(text):
    """Drop pure hesitations; trim only a leading hesitation, never dictated content.

    Short words like да/нет/ага/угу/стоп and numeric answers remain meaningful.
    Content after the first meaningful token is preserved byte-for-character.
    """
    words = list(_WORDS.finditer(text or ""))
    for word in words:
        if not is_hesitation(word.group()):
            return text[word.start():].strip()
    return ""


def phrase(text):
    return " ".join(_WORDS.findall(text.lower().replace("ё", "е")))


SMALL_TALK = {
    "как дела": "Всё в порядке, я на связи. А у тебя?",
    "как у тебя дела": "Всё в порядке, я на связи. А у тебя?",
    "как ты": "Я на связи и готова помочь. Как у тебя дела?",
    "как настроение": "Готова помочь. А у тебя как настроение?",
    "что делаешь": "Слушаю тебя. Чем помочь?",
    "чем занята": "Слушаю тебя. Чем помочь?",
    "что ты умеешь": "Могу поддержать короткий разговор, назвать время и версию, повторить ответ и управлять подключённым публичным видео. Остальные команды ещё подключаются.",
}
WELLBEING_QUESTIONS = {"как дела", "как у тебя дела", "как ты", "как настроение"}
_SMALL_TALK_ALIASES = {
    "как твои дела": "как дела", "как у тебя": "как дела", "как у тебя настроение": "как настроение",
    "что ты делаешь": "что делаешь", "чем ты занята": "чем занята",
    "чем занимаешься": "чем занята", "чем ты занимаешься": "чем занята",
}


def small_talk_key(text):
    """Normalize complete public conversational utterances, never command substrings."""
    key = phrase(text)
    # Whisper punctuation and common spoken lead-ins must not turn chat into an action.
    key = re.sub(r"^(?:(?:ну|а|привет|скажи|расскажи|пожалуйста)\s+){1,3}", "", key)
    key = re.sub(r"\s+пожалуйста$", "", key)
    key = _SMALL_TALK_ALIASES.get(key, key)
    return key if key in SMALL_TALK else None
WELLBEING_REPLIES = {"нормально": "Хорошо. Чем займёмся?", "норм": "Хорошо. Чем займёмся?",
                     "хорошо": "Хорошо. Чем займёмся?", "все хорошо": "Хорошо. Чем займёмся?",
                     "отлично": "Отлично. Чем займёмся?", "так себе": "Понимаю. Чем могу помочь?",
                     "плохо": "Понимаю. Чем могу помочь?", "устал": "Можем продолжить позже. Скажи, если нужна помощь."}
PUBLIC_QUESTIONS = set(SMALL_TALK) | {"привет", "здравствуй", "ты тут", "ты здесь", "ты на связи",
                    "какая версия", "твоя версия", "версия", "который час", "сколько времени"}
ACKNOWLEDGEMENTS = {"да", "ага", "угу", "понял", "понятно", "хорошо", "ок", "окей", "спасибо"}
REPEAT = {"повтори", "повтори ответ", "что ты сказала", "не расслышал", "еще раз"}
STOP = {"стоп", "хватит", "не говори", "замолчи"}
CLOSE = {"все спасибо", "задача завершена", "заверши задачу", "закрой диалог", "отдыхай"}
PUBLIC_CONTEXT = {"не сработало", "не отображается", "ничего не произошло",
                  "пауза", "поставь видео на паузу", "продолжи видео", "продолжи",
                  "весь экран", "убери видео из полноэкранного режима", "сверни это видео",
                  "тише", "сделай видео тише", "громче", "сделай видео громче"}


@dataclass
class PublicDialogue:
    """Volatile public reply context; never speaker authentication or action approval.

    Without a wake word only listed public queries and dialogue controls are accepted.
    Files/private data are excluded. Public media still runs its fresh-target capability gates.
    """
    enabled: bool = True
    reply_until: float = 0
    reply_window_seconds: float = 90
    last_public_answer: str | None = None
    expected_response: str | None = None

    def allows(self, text, now):
        return (self.enabled and 0 < now <= self.reply_until and
                (small_talk_key(text) is not None or phrase(text) in PUBLIC_QUESTIONS | PUBLIC_CONTEXT | ACKNOWLEDGEMENTS | REPEAT | STOP | CLOSE | {"нет"}
                 or (self.expected_response == "wellbeing" and phrase(text) in WELLBEING_REPLIES)))

    def answered(self, command, answer, now, *, public_answer=False):
        if phrase(command) not in REPEAT:
            self.expected_response = "wellbeing" if phrase(command) in WELLBEING_QUESTIONS else None
        if public_answer or phrase(command) in PUBLIC_QUESTIONS:
            self.last_public_answer = answer
        # Non-public output must never become a repeatable public answer.
        elif phrase(command) not in REPEAT:
            self.last_public_answer = None
        self.reply_until = now + self.reply_window_seconds

    def close(self):
        self.reply_until = 0
        self.last_public_answer = None
        self.expected_response = None
