"""Synthetic public audio through actual TTS/STT/wake/canonicalizer/router, no mic."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.signal import resample_poly

root = Path(sys.argv[1]).resolve(); sys.path.insert(0, str(root))
import vexi
from foundation_bridge import FoundationBridge
from speech_input import meaningful_speech

stt = vexi.STT(); tts = vexi.TTS(); bridge = FoundationBridge({})
rows = []
for prompt in ("Векси, как дела?", "Векси, что делаешь?", "Векси, что ты делаешь?", "Векси, ну как у тебя дела?"):
    audio = tts.silero_model.apply_tts(text=prompt, speaker=tts.speaker, sample_rate=tts.rate)
    audio = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
    audio = resample_poly(audio, 16000, tts.rate).astype(np.float32)
    text = meaningful_speech(stt.transcribe(audio))
    addressed, command = vexi.extract_activation(text)
    command = meaningful_speech(command)
    command, changes = vexi.CANONICALIZER.canonicalize(command)
    answer = bridge.execute(command)[1] if addressed and command else "NO_ROUTE"
    rows.append({"synthetic_prompt": prompt, "synthetic_recognition": text,
                 "addressed": addressed, "command": command, "answer": answer})
Path(sys.argv[2]).write_text(json.dumps({"rows": rows, "microphone_field": "NOT_RUN"}, ensure_ascii=False, indent=2), "utf-8")
print("SYNTHETIC_SMALLTALK_COMPLETE")
