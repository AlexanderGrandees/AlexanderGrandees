import logging

print("Preload: Faster-Whisper small...")
try:
    from faster_whisper import WhisperModel
    WhisperModel("small", device="cpu", compute_type="int8")
    print("Whisper small: OK")
except Exception as e:
    print("Whisper preload skipped:", e)

print("Preload: Silero ru/xenia...")
try:
    from silero import silero_tts
    model, _ = silero_tts(language="ru", speaker="v5_ru")
    print("Silero: OK")
except Exception as e:
    print("Silero preload skipped:", e)
