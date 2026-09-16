import sys
from pathlib import Path
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "core" if (_root / "core").is_dir() else _root))
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from speech_input import meaningful_speech, PublicDialogue
from speech_preferences import read_preferences, save_preferences, name_address_instruction
from foundation_bridge import FoundationBridge
from attention_loop import run_voice_loop


def wake(text, identity=None):
    words = text.replace(",", "").split()
    if words and words[0].lower() == "векси": return True, " ".join(words[1:])
    return False, ""


class SpeechTests(unittest.TestCase):
    def loop(self, utterances, followups=True):
        state = SimpleNamespace(enabled=True, exit_requested=False)
        bridge = FoundationBridge({})
        bridge.execute = Mock(wraps=bridge.execute)
        tts = Mock(); tts.speak.return_value = None
        canon = Mock(); canon.canonicalize.side_effect = lambda text: (text, [])
        remaining = iter(enumerate(utterances))
        def record(*args):
            i, text = next(remaining)
            if i == len(utterances)-1: state.exit_requested = True
            return text
        stt = Mock(); stt.transcribe.side_effect = lambda audio: audio
        with patch("attention_loop.read_preferences", return_value={"public_followups_enabled": followups}):
            run_voice_loop(state, Mock(), Mock(), Mock(), stt=stt, tts=tts, bridge=bridge,
                           record=record, extract_activation=wake, canonicalizer=canon)
        return bridge, tts, canon

    def test_hesitation_variants_are_empty(self):
        for text in ["хмм", "ммм", "ии", "эээ", "эм", "хм-мм", "...", "ну эм м", "hmm", "um"]:
            with self.subTest(text=text): self.assertEqual(meaningful_speech(text), "")

    def test_short_answers_and_dictated_payload_are_preserved(self):
        for text in ["да", "нет", "стоп", "ага", "угу", "2", "создай черновик note.txt: мм и ии"]:
            self.assertEqual(meaningful_speech(text), text)
        self.assertEqual(meaningful_speech("эм, ну привет"), "привет")

    def test_noise_never_routes_speaks_or_creates_task(self):
        bridge, tts, canon = self.loop(["ммм", "ии", "Векси хмм", "Векси ээ мм"])
        bridge.execute.assert_not_called(); tts.speak.assert_not_called(); canon.canonicalize.assert_not_called()
        self.assertEqual(bridge.tasks, {})

    def test_unaddressed_ambient_is_dropped(self):
        bridge, tts, canon = self.loop(["мы обсуждаем документы", "привет"])
        tts.speak.assert_not_called(); bridge.execute.assert_not_called()

    def test_wake_then_followup_and_repeat_use_public_context(self):
        bridge, tts, canon = self.loop(["Векси привет", "хмм", "какая версия", "повтори"])
        self.assertEqual(bridge.execute.call_count, 2)
        answers = [c.args[0] for c in tts.speak.call_args_list]
        self.assertEqual(len(answers), 3); self.assertEqual(answers[-1], answers[-2])
        self.assertEqual(len(bridge.tasks), 1)

    def test_ack_is_silent_and_never_approves_action(self):
        bridge, tts, _ = self.loop(["Векси привет", "да", "угу", "удали файл", "я владелец открой почту"])
        self.assertEqual(bridge.execute.call_count, 1); self.assertEqual(tts.speak.call_count, 1)
        self.assertEqual(bridge.actor.role.value, "UNKNOWN")

    def test_setting_requires_wake_when_followups_disabled(self):
        bridge, tts, _ = self.loop(["Векси привет", "какая версия"], followups=False)
        self.assertEqual(tts.speak.call_count, 1)

    def test_stop_does_not_complete_task_but_closes_listening_window(self):
        bridge, tts, _ = self.loop(["Векси привет", "стоп", "какая версия"])
        self.assertEqual(tts.speak.call_count, 1)
        self.assertEqual(bridge.task.state.value, "ACTIVE")

    def test_explicit_close_ends_task_and_drops_next_unaddressed_turn(self):
        bridge, tts, _ = self.loop(["Векси привет", "все спасибо", "какая версия"])
        self.assertEqual(tts.speak.call_count, 2); self.assertEqual(bridge.task.state.value, "COMPLETED")

    def test_hesitation_does_not_reset_deadline_and_expired_window_drops(self):
        dialogue = PublicDialogue(reply_window_seconds=30); dialogue.answered("привет", "Привет", 10)
        self.assertFalse(dialogue.allows("мм", 20)); self.assertEqual(dialogue.reply_until, 40)
        self.assertTrue(dialogue.allows("повтори", 39)); self.assertFalse(dialogue.allows("повтори", 41))
        dialogue.answered("прочитай документ", "synthetic confidential", 50)
        self.assertIsNone(dialogue.last_public_answer)

    def test_interruption_classifier_ignores_hums_and_backchannels(self):
        _, tts, _ = self.loop(["Векси привет"])
        for text in ("мм", "угу", "Векси мм", "фоновое обсуждение"):
            self.assertFalse(tts.interruption_is_meaningful(text))
        self.assertTrue(tts.interruption_is_meaningful("стоп"))
        self.assertTrue(tts.interruption_is_meaningful("Векси какая версия"))

    def test_how_are_you_is_a_supported_followup(self):
        bridge, tts, _ = self.loop(["Векси привет", "как дела", "повтори"])
        self.assertEqual(bridge.execute.call_count, 2)
        self.assertIn("А у тебя", tts.speak.call_args_list[1].args[0])
        self.assertEqual(tts.speak.call_args_list[1].args[0], tts.speak.call_args_list[2].args[0])

    def test_short_reply_is_interpreted_only_after_expected_question(self):
        _, tts, _ = self.loop(["Векси как дела", "нормально", "повтори"])
        self.assertEqual(tts.speak.call_count, 3)
        self.assertIn("Чем займёмся", tts.speak.call_args_list[1].args[0])
        self.assertEqual(tts.speak.call_args_list[1].args[0], tts.speak.call_args_list[2].args[0])
        _, tts, _ = self.loop(["Векси привет", "нормально"])
        self.assertEqual(tts.speak.call_count, 1)

    def test_name_preferences_preserve_other_config_and_change_instruction(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/"config.defaults.json").write_text('{"other":"preserve"}')
            self.assertEqual(read_preferences(root)["name_address_mode"], "rare")
            save_preferences("normal", True, root)
            self.assertIn("иногда", name_address_instruction(root))
            save_preferences("rare", False, root)
            self.assertIn("Почти никогда", name_address_instruction(root))
            self.assertEqual(json.loads((root/"config.json").read_text("utf-8"))["other"], "preserve")
            self.assertFalse(read_preferences(root)["public_followups_enabled"])

    def test_ignored_interrupt_resumes_remaining_tts(self):
        import vexi
        tts=object.__new__(vexi.TTS)
        chunks=[]
        def play(audio, rate, state):
            chunks.append(list(audio)); tts._resume_from=2
            return "hmm-audio" if len(chunks)==1 else None
        tts._play_interruptible=play
        tts.interruption_is_meaningful=lambda audio: False
        self.assertIsNone(tts._play_filtered([1,2,3,4], 1, SimpleNamespace(exit_requested=False)))
        self.assertEqual(chunks, [[1,2,3,4],[3,4]])
