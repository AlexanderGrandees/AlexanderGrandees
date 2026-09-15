"""Real models, synthetic audio in RAM; never opens a microphone or speaker."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.signal import resample_poly

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
import vexi

stt = vexi.STT()
tts = vexi.TTS()
if tts.engine != "silero": raise SystemExit("SILERO_NOT_READY")
audio = tts.silero_model.apply_tts(text="Векси, привет.", speaker=tts.speaker, sample_rate=tts.rate)
audio = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
audio = resample_poly(audio, 16000, tts.rate).astype(np.float32)
text = stt.transcribe(audio)
print(json.dumps({"status": "PASS" if text.strip() else "FAIL", "stt_model": "small",
    "tts_engine": tts.engine, "synthetic_audio_seconds": round(len(audio)/16000, 2),
    "recognized_nonempty": bool(text.strip()), "microphone": "NOT_RUN",
    "speaker_playback": "NOT_RUN", "voice_field": "NOT_RUN"}))
raise SystemExit(0 if text.strip() else 1)
