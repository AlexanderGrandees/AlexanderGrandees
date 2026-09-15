"""Voice ingress with no transcript/audio persistence and no legacy Router bypass."""
import logging
import time
from vexi_foundation.attention import ConversationState
from version import __version__
from speech_input import (meaningful_speech, phrase, PublicDialogue, PUBLIC_QUESTIONS,
                          ACKNOWLEDGEMENTS, REPEAT, STOP, CLOSE, WELLBEING_REPLIES)
from speech_preferences import read_preferences


def run_voice_loop(state, overlay, tray, identity, *, stt, tts, bridge, record,
                   extract_activation, canonicalizer):
    log = logging.getLogger("vexi.foundation")
    pending = None
    dialogue = PublicDialogue(enabled=getattr(bridge, "public_followups_enabled", True))
    def interruption_is_meaningful(audio):
        candidate = meaningful_speech(stt.transcribe(audio))
        if not candidate or phrase(candidate) in ACKNOWLEDGEMENTS:
            return False
        directed, tail = extract_activation(candidate, identity)
        if directed:
            return not tail or bool(meaningful_speech(tail))
        return phrase(candidate) in STOP or dialogue.allows(candidate, time.monotonic())
    tts.interruption_is_meaningful = interruption_is_meaningful
    log.info("RUNTIME event=%s", "voice_components_ready")
    overlay.show("Готова", f"Vexi {__version__} — гостевой голосовой режим")
    while not state.exit_requested:
        if not state.enabled:
            bridge.conversation.mute()
            dialogue.close()
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
            text = meaningful_speech(text)
            if not text:
                continue
            # Wake detection is local and volatile; canonicalization cannot log ambient text.
            addressed, command = extract_activation(text, identity)
            dialogue.enabled = read_preferences()["public_followups_enabled"]
            # A wake word followed only by hesitation is not a request. Do not
            # activate/extend the conversation, mutate task state, or speak.
            if addressed and command:
                command = meaningful_speech(command)
                if not command:
                    text = None
                    continue
            # A public dialogue turn does not establish speaker identity or grant
            # capability authority. Unaddressed action commands remain excluded.
            public_followup = not addressed and dialogue.allows(text, time.monotonic())
            if public_followup:
                command = text
                log.info("ATTENTION class=%s decision=%s code=%s", "CONTEXTUAL", "ACCEPT", "public_reply")
            accepted = public_followup or bridge.accept(addressed, continuation_bound=False)
            if not accepted:
                text = command = None
                continue
            command, _ = canonicalizer.canonicalize(command)
            text = None
            key = phrase(command)
            wellbeing_reply = dialogue.expected_response == "wellbeing" and key in WELLBEING_REPLIES
            if key in ACKNOWLEDGEMENTS and not wellbeing_reply:
                dialogue.reply_until = time.monotonic() + dialogue.reply_window_seconds
                command = None
                continue  # Acknowledgement is not an approval or a reason to chatter.
            if key in STOP:
                dialogue.close()
                bridge.conversation.close()
                command = None
                continue  # Stop speech without completing the unresolved task.
            if wellbeing_reply:
                answer = WELLBEING_REPLIES[key]
            elif key in REPEAT:
                answer = dialogue.last_public_answer or "Пока нет ответа, который можно повторить."
            elif key == "нет":
                answer = "Что нужно уточнить?"
            elif not command:
                answer = "Да?"
            else:
                _, answer = bridge.execute(command)
            if key in CLOSE:
                dialogue.close()
            overlay.show("Говорю", answer)
            tray.set_kind("speaking")
            bridge.conversation.speaking()
            public_answer = key in PUBLIC_QUESTIONS | REPEAT or wellbeing_reply or key == "нет"
            last_answer = answer if public_answer else ""
            try:
                pending = tts.speak(answer, state)
            finally:
                answer = None
                bridge.conversation.speech_finished(time.monotonic())
                if pending is not None:
                    bridge.conversation.barge_in()
            if key not in CLOSE:
                # Only deterministic public answers may be repeated without a wake word.
                dialogue.answered(command, last_answer, time.monotonic(), public_answer=public_answer)
            last_answer = None
            command = None
            tray.set_kind("idle")
        except Exception:
            dialogue.close()
            # Exception repr/tracebacks may contain user payloads or private paths.
            log.info("RUNTIME event=%s", "voice_recovery")
            bridge.conversation.state = ConversationState.RECOVERY
            overlay.show("Ошибка", "Ошибка голосового контура; повторное подключение.")
            tray.set_kind("error")
            time.sleep(.75)
