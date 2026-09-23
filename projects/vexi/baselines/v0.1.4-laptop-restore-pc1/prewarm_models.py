from __future__ import annotations

import sys


def main() -> int:
    print('[models 1/2] faster-whisper small: checking/downloading...')
    from faster_whisper import WhisperModel
    WhisperModel('small', device='cpu', compute_type='int8')
    print('[models 1/2] faster-whisper small: PASS')

    print('[models 2/2] Silero ru v5: checking/downloading...')
    from silero import silero_tts
    model, _ = silero_tts(language='ru', speaker='v5_ru')
    if model is None:
        raise RuntimeError('Silero model did not initialize')
    print('[models 2/2] Silero ru v5: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
