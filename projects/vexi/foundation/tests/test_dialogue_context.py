import sys
from pathlib import Path
import unittest
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "core" if (_root / "core").is_dir() else _root))
from vexi_foundation.dialogue_context import DialogueContext, DialogueState


class DialogueContextTests(unittest.TestCase):
    def test_pause_preserves_task_and_history(self):
        c = DialogueContext(); c.set_objective("спланировать вечер")
        t = c.begin_turn("два варианта"); self.assertTrue(c.commit(t, "прогулка или кино"))
        c.pause(); t = c.begin_turn("второй подробнее")
        self.assertEqual(c.messages(t)[0]["content"], "Текущая задача: спланировать вечер")
        self.assertEqual(c.messages(t)[2]["content"], "прогулка или кино")

    def test_late_response_after_barge_in_is_rejected(self):
        c = DialogueContext(); old = c.begin_turn("первый вопрос")
        new = c.begin_turn("поправка")
        self.assertFalse(c.commit(old, "старый ответ"))
        self.assertTrue(c.commit(new, "новый ответ"))

    def test_pause_invalidates_generation(self):
        c = DialogueContext(); t = c.begin_turn("вопрос"); c.pause()
        self.assertFalse(c.commit(t, "поздний ответ"))

    def test_session_tickets_cannot_cross_sessions(self):
        a = DialogueContext(); b = DialogueContext()
        t = a.begin_turn("a"); b.begin_turn("b")
        self.assertFalse(b.commit(t, "answer"))

    def test_explicit_close_clears_all_content(self):
        c = DialogueContext(); c.set_objective("private goal")
        t = c.begin_turn("private text"); c.commit(t, "private answer"); c.close()
        self.assertEqual(c.objective, ""); self.assertEqual(c._turns, [])
        self.assertIsNone(c._pending); self.assertEqual(c.state, DialogueState.CLOSED)
        with self.assertRaises(ValueError): c.begin_turn("again")

    def test_eviction_preserves_objective(self):
        c = DialogueContext(max_pairs=1); c.set_objective("goal")
        for word in ("old", "new"):
            t = c.begin_turn(word); c.commit(t, word + " answer")
        t = c.begin_turn("continue")
        self.assertNotIn("old", str(c.messages(t)))
        self.assertIn("goal", str(c.messages(t)))
        self.assertIn("new", str(c.messages(t)))

    def test_correction_invalidates_old_response(self):
        c = DialogueContext(); c.set_objective("old goal"); t = c.begin_turn("request")
        c.set_objective("corrected goal")
        self.assertFalse(c.commit(t, "obsolete"))
        self.assertEqual(c.objective, "corrected goal")

    def test_repr_and_errors_do_not_contain_payload(self):
        c = DialogueContext(); c.set_objective("private goal")
        c.begin_turn("private text")
        self.assertNotIn("private", repr(c))
        with self.assertRaisesRegex(ValueError, "invalid_turn"):
            c.begin_turn("secret" * 3000)

    def test_invalid_answer_not_committed(self):
        c = DialogueContext(); t = c.begin_turn("question")
        self.assertFalse(c.commit(t, "")); self.assertEqual(c._turns, [])


if __name__ == "__main__": unittest.main()
