import json
import os
import re
import time
from difflib import SequenceMatcher
from pathlib import Path


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").lower().replace("ё", "е")).strip()


class SpeechCanonicalizer:
    """Conservative STT term repair.

    Automatic correction is limited to known capability/entity vocabularies and
    only becomes permissive when the surrounding words support the same semantic
    family. Explicit user corrections are stored locally with the same family gate.
    """

    DEFAULT_ENTRIES = [
        {"canonical":"hdr", "family":"display", "variants":["хдр","эйч ди ар","эйчдиар","аш ди ар","hdr"],
         "context":["включи","выключи","переключи","экран","монитор","дисплей","изображение","комп","ноут"]},
        {"canonical":"youtube", "family":"service", "variants":["ютуб","ютьюб","youtube"],
         "context":["открой","найди","видео","канал","браузер","страниц"]},
        {"canonical":"vivaldi", "family":"browser", "variants":["вивальди","vivaldi"],
         "context":["открой","браузер","вкладк","страниц","закрой","сверни","разверни"]},
        {"canonical":"firefox", "family":"browser", "variants":["фаерфокс","firefox"],
         "context":["открой","браузер","вкладк","страниц"]},
        {"canonical":"chrome", "family":"browser", "variants":["хром","chrome"],
         "context":["открой","браузер","вкладк","страниц"]},
        {"canonical":"edge", "family":"browser", "variants":["эдж","edge"],
         "context":["открой","браузер","вкладк","страниц"]},
        {"canonical":"brave", "family":"browser", "variants":["брейв","brave"],
         "context":["открой","браузер","вкладк","страниц"]},
        {"canonical":"opera", "family":"browser", "variants":["опера","opera"],
         "context":["открой","браузер","вкладк","страниц"]},
        {"canonical":"steam", "family":"app", "variants":["стим","steam"], "context":["открой","запусти","аккаунт","игр"]},
        {"canonical":"telegram", "family":"app", "variants":["телеграм","telegram"], "context":["открой","запусти","закрой"]},
        {"canonical":"discord", "family":"app", "variants":["дискорд","discord"], "context":["открой","запусти","закрой"]},
        {"canonical":"github", "family":"service", "variants":["гитхаб","github"], "context":["открой","репозитор","браузер","страниц"]},
        {"canonical":"notion", "family":"service", "variants":["ноушн","notion"], "context":["открой","страниц","база","браузер"]},
        {"canonical":"gmail", "family":"service", "variants":["джимейл","gmail"], "context":["открой","почт","письм","браузер"]},
        {"canonical":"tradingview", "family":"service", "variants":["трейдингвью","трейдинг вью","tradingview"], "context":["открой","график","браузер"]},
        {"canonical":"quest", "family":"device", "variants":["квест","quest","окулус","oculus"], "context":["устройств","шлем","vr","подключ"]},
    ]

    def __init__(self, enabled=True, data_dir=None):
        self.enabled = bool(enabled)
        root = Path(data_dir or (Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Vexi" / "data"))
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "speech_corrections.json"
        self.entries = list(self.DEFAULT_ENTRIES)
        self.learned = self._load_learned()

    def _load_learned(self):
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self):
        self.path.write_text(json.dumps(self.learned, ensure_ascii=False, indent=2), encoding="utf-8")

    def initial_prompt_terms(self):
        vals = []
        for e in self.entries:
            vals.append(e["canonical"])
            vals.extend(e.get("variants") or [])
        return ". ".join(dict.fromkeys(vals)) + "."

    def _entry_for_canonical(self, value):
        n = _norm(value)
        for e in self.entries:
            if n == _norm(e["canonical"]) or n in {_norm(x) for x in e.get("variants", [])}:
                return e
        return None

    def observe_explicit_correction(self, text):
        t = _norm(text)
        # "HDR, а не CDR" => correct=HDR, wrong=CDR
        patterns = [
            r"^\s*([\w+.-]{2,30})\s*,?\s*а?\s*не\s+([\w+.-]{2,30})\s*[.!?]*$",
            r"^\s*не\s+([\w+.-]{2,30})\s*,?\s*а\s+([\w+.-]{2,30})\s*[.!?]*$",
        ]
        m = re.match(patterns[0], t, flags=re.I)
        if m:
            correct, wrong = m.group(1), m.group(2)
        else:
            m = re.match(patterns[1], t, flags=re.I)
            if not m:
                return None
            wrong, correct = m.group(1), m.group(2)
        entry = self._entry_for_canonical(correct)
        if not entry or _norm(wrong) == _norm(entry["canonical"]):
            return None
        rec = {
            "heard": _norm(wrong), "canonical": entry["canonical"], "family": entry["family"],
            "confirmed": True, "updated_at": time.time(),
        }
        self.learned = [x for x in self.learned if x.get("heard") != rec["heard"]]
        self.learned.append(rec)
        self._save()
        return rec

    @staticmethod
    def _has_context(text, entry):
        t = _norm(text)
        return any(c in t for c in entry.get("context", []))

    @staticmethod
    def _score(token, entry):
        token = _norm(token)
        forms = [entry["canonical"]] + list(entry.get("variants") or [])
        return max(SequenceMatcher(None, token, _norm(x)).ratio() for x in forms)

    def canonicalize(self, text):
        if not self.enabled or not text:
            return text, []
        # Correction utterances teach; they are not rewritten/executed.
        learned = self.observe_explicit_correction(text)
        if learned:
            return text, [{"kind":"learned", **learned}]

        original = text
        changes = []
        tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9+.-]+|\s+|[^\w\s]", text)
        for i, token in enumerate(tokens):
            if not re.match(r"^[A-Za-zА-Яа-яЁё0-9+.-]{2,}$", token):
                continue
            tn = _norm(token)
            # Confirmed user mapping still obeys its semantic family context.
            mapped = next((x for x in reversed(self.learned) if x.get("heard") == tn), None)
            if mapped:
                entry = self._entry_for_canonical(mapped.get("canonical"))
                if entry and self._has_context(original, entry):
                    tokens[i] = entry["canonical"]
                    changes.append({"heard":token, "canonical":entry["canonical"], "reason":"user_confirmed"})
                    continue

            scored = sorted(((self._score(token, e), e) for e in self.entries), key=lambda x:x[0], reverse=True)
            if not scored:
                continue
            best_score, best = scored[0]
            second = scored[1][0] if len(scored) > 1 else 0.0
            context_ok = self._has_context(original, best)
            exact_alias = tn in {_norm(x) for x in best.get("variants", [])}
            safe = exact_alias or best_score >= 0.91 or (context_ok and best_score >= 0.64 and best_score-second >= 0.12)
            if safe and tn != _norm(best["canonical"]):
                tokens[i] = best["canonical"]
                changes.append({"heard":token, "canonical":best["canonical"], "score":round(best_score,3), "family":best["family"]})
        return "".join(tokens), changes
