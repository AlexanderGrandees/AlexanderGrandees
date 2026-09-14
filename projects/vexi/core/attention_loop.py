"""Voice ingress with no transcript/audio persistence and no legacy Router bypass."""
import logging
import time
from vexi_foundation.attention import ConversationState
from version import __version__


def run_voice_loop(state, overlay, tray, identity, *, stt, tts, bridge, record,
                   extract_activation, canonicalizer):
    log = logging.getLogger("vexi.foundation")
    pending = None
    log.info("RUNTIME event=%s", "voice_components_ready")
    overlay.show("Готова", f"Vexi {__version__} — гостевой голосовой режим")
    while not state.exit_requested:
        if not state.enabled:
            bridge.conversation.mute()
            pending = None
            time.sleep(.2)
            continue
        if bridge.conversation.state == ConversationState.MUTED:
            bridge.conversation.close()
        try:
            audio = pending if pending is not None else record(state, None)
            pending = None
            if audio is None:
                continue
            try:
                text = stt.transcribe(audio)
            finally:
                # Release buffers; Python cannot promise forensic memory zeroisation.
                audio = None
            if not text:
                continue
            # Wake detection is local and volatile; canonicalization cannot log ambient text.
            addressed, command = extract_activation(text, identity)
            # No diarization/binding proof is present in the v0.1.4 microphone adapter.
            # Do not equate a reply timeout or interrupted TTS with such proof.
            accepted = bridge.accept(addressed, continuation_bound=False)
            if not accepted:
                text = command = None
                continue
            command, _ = canonicalizer.canonicalize(command)
            text = None
            if not command:
                answer = "Да?"
            else:
                _, answer = bridge.execute(command)
            command = None
            overlay.show("Говорю", answer)
            tray.set_kind("speaking")
            bridge.conversation.speaking()
            try:
                pending = tts.speak(answer, state)
            finally:
                answer = None
                bridge.conversation.speech_finished(time.monotonic())
                if pending is not None:
                    bridge.conversation.barge_in()
            tray.set_kind("idle")
        except Exception:
            # Exception repr/tracebacks may contain user payloads or private paths.
            log.info("RUNTIME event=%s", "voice_recovery")
            bridge.conversation.state = ConversationState.RECOVERY
            overlay.show("Ошибка", "Ошибка голосового контура; повторное подключение.")
            tray.set_kind("error")
            time.sleep(.75)
