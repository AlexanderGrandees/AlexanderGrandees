import ctypes
import json
import logging
import os
import re
import subprocess
import tempfile
import threading
import time
import wave
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import requests
import sounddevice as sd

from app_registry import norm
from ui import Overlay, Tray
from assistant_identity import AssistantIdentity
from speech_canonicalizer import SpeechCanonicalizer
from version import __version__, __channel__, __build__
from foundation_bridge import FoundationBridge, MetadataOnlyFilter

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / ("config.json" if (BASE / "config.json").exists() else "config.defaults.json")).read_text(encoding="utf-8-sig"))
IDENTITY = AssistantIdentity(CFG.get("assistant_name", "Векси"))
NAME = IDENTITY.display_name()
CANONICALIZER = SpeechCanonicalizer(enabled=bool(CFG.get("speech_canonicalizer_enabled", True)))

LOG_DIR = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "vexi.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)
for _handler in logging.getLogger().handlers:
    _handler.addFilter(MetadataOnlyFilter())

def base_system_prompt():
    name = IDENTITY.display_name()
    return f"""Ты {name}, локальный голосовой ассистент владельца Windows-ПК.
Говори естественно, спокойно и кратко. По умолчанию отвечай по-русски.
Ты находишься в продолжающемся разговоре и учитываешь предыдущие реплики.
Если пользователь отвечает коротко, это продолжение активного разговора.
Локальный Router выполняет поддерживаемые действия до обращения к тебе.
Никогда не утверждай, что действие на ПК выполнено, если runtime не подтвердил результат.
Если пользователь сообщает, что действие не сработало, воспринимай это как обратную связь, а не как новую команду.
Имя владельца из памяти используй редко и только когда это социально уместно.
"""




class State:
    def __init__(self):
        self.enabled = True
        self.speak_enabled = bool(CFG.get("speak_answers", True))
        self.exit_requested = False
        self.speaking = False


def acquire_single_instance():
    if os.name != "nt":
        return True
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, "VEXI_LOCAL_ASSISTANT_SINGLE_INSTANCE")
    if not handle:
        return False
    ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False
    return handle


def rms_int16(audio):
    if audio.size == 0:
        return 0.0
    x = audio.astype(np.float32)
    return float(np.sqrt(np.mean(x*x)))


def save_int16_wav(audio, rate=16000, prefix="vexi_barge_"):
    if audio is None or getattr(audio, "size", 0) == 0:
        return None
    # Legacy function name retained internally; microphone audio stays in RAM.
    return np.asarray(audio, dtype=np.float32) / 32768.0


def record_utterance(state, start_timeout=None):
    rate = 16000
    block_ms = 100
    block = int(rate * block_ms / 1000)
    threshold = float(CFG.get("energy_threshold", 420))
    silence_needed = float(CFG.get("silence_seconds", 0.9))
    min_speech = float(CFG.get("min_speech_seconds", 0.22))
    max_seconds = float(CFG.get("max_utterance_seconds", 18))

    started = False
    speech_time = 0.0
    silent_for = 0.0
    spoken_elapsed = 0.0
    chunks, preroll = [], []
    wait_started = time.monotonic()

    with sd.RawInputStream(samplerate=rate, blocksize=block, dtype="int16", channels=1) as stream:
        while not state.exit_requested:
            if not state.enabled:
                return None
            if not started and start_timeout is not None:
                if time.monotonic() - wait_started >= start_timeout:
                    return None

            raw, _ = stream.read(block)
            arr = np.frombuffer(raw, dtype=np.int16).copy()
            level = rms_int16(arr)
            dt = block_ms / 1000.0

            if not started:
                preroll.append(arr)
                if len(preroll) > 5:
                    preroll.pop(0)
                if level >= threshold:
                    started = True
                    chunks.extend(preroll)
                    speech_time += dt
            else:
                chunks.append(arr)
                spoken_elapsed += dt
                if level >= threshold:
                    speech_time += dt
                    silent_for = 0.0
                else:
                    silent_for += dt
                if speech_time >= min_speech and silent_for >= silence_needed:
                    break
                if spoken_elapsed >= max_seconds:
                    break

    if not started or speech_time < min_speech:
        return None

    return save_int16_wav(np.concatenate(chunks), rate)


class STT:
    def __init__(self):
        from faster_whisper import WhisperModel
        model_name = CFG.get("stt_model", "small")
        device = CFG.get("stt_device", "cpu")
        compute = CFG.get("stt_compute_type", "int8")
        logging.info("Loading STT %s %s %s", model_name, device, compute)
        try:
            self.model = WhisperModel(model_name, device=device, compute_type=compute)
        except Exception:
            self.model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def transcribe(self, path):
        segments, _ = self.model.transcribe(
            path,
            language=CFG.get("language") or None,
            vad_filter=True,
            beam_size=4,
            initial_prompt=((CFG.get("stt_initial_prompt") or "") + " " + IDENTITY.display_name() + ". " + CANONICALIZER.initial_prompt_terms()).strip() or None,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()


class TTS:
    def __init__(self):
        self.engine = None
        self.silero_model = None
        self.piper_voice = None
        self.speaker = CFG.get("silero_speaker", "xenia")
        self.rate = int(CFG.get("silero_sample_rate", 48000))

        try:
            from silero import silero_tts
            import torch
            self.silero_model, _ = silero_tts(
                language=CFG.get("silero_language", "ru"),
                speaker=CFG.get("silero_model", "v5_ru"),
            )
            self.silero_model.to(torch.device("cpu"))
            torch.set_num_threads(max(1, min(4, (os.cpu_count() or 4)//2)))
            self.engine = "silero"
            logging.info("Silero TTS ready: %s", self.speaker)
            return
        except Exception as e:
            logging.exception("Silero failed: %s", e)

        model_path = BASE / CFG.get("piper_model_path", "")
        try:
            from piper import PiperVoice
            self.piper_voice = PiperVoice.load(str(model_path))
            self.engine = "piper"
            logging.info("Piper fallback ready")
        except Exception as e:
            logging.exception("Piper failed: %s", e)

    def _record_barge_tail(self, stream, preroll, threshold, block, rate):
        chunks = list(preroll)
        speech = 0.0
        silent = 0.0
        max_seconds = float(CFG.get("barge_in_max_utterance_seconds", 8.0))
        silence_needed = float(CFG.get("barge_in_silence_seconds", 0.70))
        started = time.monotonic()
        while time.monotonic() - started < max_seconds:
            raw, _ = stream.read(block)
            arr = np.frombuffer(raw, dtype=np.int16).copy()
            chunks.append(arr)
            level = rms_int16(arr)
            dt = block / rate
            if level >= threshold:
                speech += dt
                silent = 0.0
            else:
                silent += dt
            if speech >= 0.20 and silent >= silence_needed:
                break
        if not chunks:
            return None
        return save_int16_wav(np.concatenate(chunks), rate=rate)

    def _play_interruptible(self, audio, rate, state):
        audio = np.asarray(audio)
        if audio.size == 0:
            return None
        enabled = bool(CFG.get("barge_in_enabled", True))
        if not enabled:
            sd.play(audio, rate); sd.wait(); return None

        mic_rate = int(CFG.get("barge_in_mic_rate", 16000))
        block_ms = int(CFG.get("barge_in_block_ms", 80))
        block = max(160, int(mic_rate * block_ms / 1000))
        energy = float(CFG.get("energy_threshold", 420))
        min_ms = float(CFG.get("barge_in_min_speech_ms", 300))
        arm_ms = float(CFG.get("barge_in_arm_ms", 220))
        echo_multiplier = float(CFG.get("barge_in_echo_multiplier", 2.0))
        preroll_blocks = max(2, int(600 / block_ms))
        duration = len(audio) / float(rate)
        started = time.monotonic()
        levels = []
        high_for = 0.0
        preroll = []

        try:
            sd.play(audio, rate, blocking=False)
            with sd.RawInputStream(samplerate=mic_rate, blocksize=block, dtype="int16", channels=1) as stream:
                while not state.exit_requested and time.monotonic() - started < duration + 0.12:
                    raw, _ = stream.read(block)
                    arr = np.frombuffer(raw, dtype=np.int16).copy()
                    level = rms_int16(arr)
                    preroll.append(arr)
                    if len(preroll) > preroll_blocks:
                        preroll.pop(0)
                    elapsed_ms = (time.monotonic() - started) * 1000.0
                    if elapsed_ms < arm_ms:
                        levels.append(level)
                        continue
                    baseline = float(np.median(levels)) if levels else energy
                    threshold = max(energy * 1.35, baseline * echo_multiplier)
                    if level >= threshold:
                        high_for += block_ms
                    else:
                        high_for = max(0.0, high_for - block_ms * 0.8)
                    if high_for >= min_ms:
                        logging.info("BARGE_IN detected level=%.1f threshold=%.1f baseline=%.1f", level, threshold, baseline)
                        sd.stop()
                        tail_threshold = max(energy * 1.10, baseline * 1.35)
                        return self._record_barge_tail(stream, preroll, tail_threshold, block, mic_rate)
            sd.stop()
            return None
        except sd.PortAudioError as e:
            logging.warning("Barge-in monitor unavailable; normal playback: %s", e)
            try:
                sd.stop(); sd.play(audio, rate); sd.wait()
            except Exception:
                pass
            return None

    def speak(self, text, state):
        if not state.speak_enabled or not text:
            return None
        state.speaking = True
        try:
            if self.engine == "silero":
                try:
                    audio = self.silero_model.apply_tts(text=text, speaker=self.speaker, sample_rate=self.rate)
                    if hasattr(audio, "detach"):
                        audio = audio.detach().cpu().numpy()
                    audio = np.asarray(audio, dtype=np.float32)
                    path = self._play_interruptible(audio, self.rate, state)
                    time.sleep(0.08)
                    return path
                except Exception as e:
                    logging.exception("Silero speak failed: %s", e)

            if self.piper_voice is not None:
                fd, path = tempfile.mkstemp(prefix="vexi_tts_", suffix=".wav")
                os.close(fd)
                try:
                    with wave.open(path, "wb") as wf:
                        self.piper_voice.synthesize_wav(text, wf)
                    with wave.open(path, "rb") as wf:
                        frames = wf.readframes(wf.getnframes())
                        ch = wf.getnchannels(); rate = wf.getframerate()
                    data = np.frombuffer(frames, dtype=np.int16)
                    if ch > 1:
                        data = data.reshape(-1, ch)
                    return self._play_interruptible(data, rate, state)
                finally:
                    try: os.remove(path)
                    except OSError: pass
            return None
        finally:
            state.speaking = False


class Brain:
    def __init__(self, memory_context_provider=None):
        self.url = CFG.get("ollama_url", "http://127.0.0.1:11434").rstrip("/")
        self.model = CFG.get("llm_model")
        self.history = []
        self.memory_context_provider = memory_context_provider

    def health(self):
        try:
            return requests.get(self.url + "/api/tags", timeout=2).ok
        except Exception:
            return False

    def ensure(self):
        if self.health():
            return
        try:
            CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(2)
        except Exception:
            pass

    def remember(self, u, a):
        self.history += [
            {"role": "user", "content": u},
            {"role": "assistant", "content": a},
        ]
        self.history = self.history[-int(CFG.get("history_turns", 12))*2:]

    def ask(self, text):
        self.ensure()
        memory_context = ""
        if self.memory_context_provider:
            try:
                memory_context = self.memory_context_provider() or ""
            except Exception:
                memory_context = ""
        messages = [{"role": "system", "content": base_system_prompt() + memory_context}] + self.history
        messages.append({"role": "user", "content": text})
        try:
            r = requests.post(
                self.url + "/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.55, "num_ctx": 6144},
                },
                timeout=180,
            )
            r.raise_for_status()
            ans = r.json()["message"]["content"].strip()
        except Exception as e:
            logging.exception("Ollama error: %s", e)
            return "Локальная модель сейчас недоступна."
        self.remember(text, ans)
        return ans


def activation_match(token, aliases):
    if token in aliases:
        return True
    th = float(CFG.get("activation_fuzzy_threshold", 0.72))
    return any(
        len(token) >= 4 and len(a) >= 4 and SequenceMatcher(None, token, a).ratio() >= th
        for a in aliases
    )


def extract_activation(text, identity=None):
    tokens = norm(text).split()
    identity = identity or IDENTITY
    aliases = [norm(x) for x in identity.wake_names()]
    limit = int(CFG.get("activation_scan_words", 4))
    for i, token in enumerate(tokens[:limit]):
        if activation_match(token, aliases):
            return True, " ".join(tokens[i+1:]).strip()
    return False, ""


def is_close_phrase(text):
    t = norm(text)
    return any(p in t for p in (
        "все спасибо", "все, спасибо", "можешь отдыхать", "отдыхай",
        "до связи", "закрой диалог", "чао", "chao", "chow"
    ))


def assistant_loop(state, overlay, tray, identity):
    from attention_loop import run_voice_loop
    try:
        stt, tts = STT(), TTS()
        bridge = FoundationBridge(CFG)
        run_voice_loop(state, overlay, tray, identity, stt=stt, tts=tts,
                       bridge=bridge, record=record_utterance,
                       extract_activation=extract_activation,
                       canonicalizer=CANONICALIZER)
    except Exception:
        logging.getLogger("vexi.foundation").info("RUNTIME event=%s", "startup_failed")
        overlay.show("Ошибка", "Не удалось запустить голосовые компоненты.")
        tray.set_kind("error")


def main():
    mutex = acquire_single_instance()
    if not mutex:
        return

    identity = IDENTITY
    state = State()
    overlay = Overlay(identity,
        enabled=bool(CFG.get("overlay_enabled", True)),
        duration=float(CFG.get("overlay_duration_seconds", 2.2)),
    )
    tray = Tray(state, overlay, identity)

    worker = threading.Thread(
        target=assistant_loop,
        args=(state, overlay, tray, identity),
        daemon=True
    )
    worker.start()

    while not state.exit_requested:
        time.sleep(0.3)


if __name__ == "__main__":
    main()
