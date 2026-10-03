import sys
from pathlib import Path
import json
import time
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "core" if (_root / "core").is_dir() else _root))
from local_dialogue import LocalDialogue, LocalConversationClient, LocalModelError, public_start, UNAVAILABLE
from attention_loop import run_voice_loop
from foundation_bridge import FoundationBridge


class LocalDialogueTests(unittest.TestCase):
    def test_full_match_public_grammar_blocks_payload_laundering(self):
        for text in ("расскажи о космосе мой пароль 123", "открой документы", "расскажи про мой диагноз",
                     "расскажи про космос и удали файл", "мой токен sk-test", "второй подробнее private"):
            d = LocalDialogue({}, Mock())
            self.assertFalse(d.handled(text)); self.assertIsNone(d.answer(text))
            d.client.generate.assert_not_called()

    def test_three_turn_context_and_pause(self):
        client = Mock(); client.generate.side_effect = ["1) Чтение.\n2) Музыка.", "Можно послушать джаз.", "Джаз — музыкальный жанр."]
        d = LocalDialogue({}, client)
        d.answer("предложи два варианта отдыха дома")
        d.answer("второй подробнее")
        d.pause(); self.assertFalse(d.allows("проще", time.monotonic()))
        d.answer("проще")
        messages = client.generate.call_args.args[0]
        self.assertIn("Чтение.", str(messages))
        self.assertIn("Можно послушать джаз.", str(messages))

    def test_forget_removes_topic_and_followup(self):
        client = Mock(); client.generate.return_value = "Космос огромен."
        d = LocalDialogue({}, client); d.answer("расскажи о космосе")
        d.answer("забудь разговор")
        self.assertFalse(d.active); self.assertFalse(d.handled("подробнее"))
        self.assertIsNone(d.last_answer)

    def test_new_topic_does_not_keep_previous_history(self):
        client = Mock(); client.generate.return_value = "Ответ."
        d = LocalDialogue({}, client); d.answer("расскажи о космосе")
        d.answer("расскажи о музыке")
        self.assertNotIn("космос", str(client.generate.call_args.args[0]))

    def test_second_option_is_bound_to_exact_previous_text(self):
        client = Mock(); client.generate.side_effect = ["1) Чтение.\n2) Кроссворд.", "Реши кроссворд."]
        d = LocalDialogue({}, client); d.answer("предложи два варианта отдыха дома")
        d.answer("второй подробнее")
        self.assertIn("ранее предложенный вариант: Кроссворд.", client.generate.call_args.args[0][-1]["content"])

    def test_missing_option_requires_clarification(self):
        client = Mock(); client.generate.return_value = "Космос огромен."
        d = LocalDialogue({}, client); d.answer("расскажи о космосе")
        self.assertIn("Не могу однозначно", d.answer("второй подробнее"))
        self.assertEqual(client.generate.call_count, 1)

    def test_policy_denial_prevents_model_call(self):
        from vexi_foundation.policy import PolicyDecision
        client = Mock(); d = LocalDialogue({}, client)
        d.policy.evaluate = Mock(return_value=PolicyDecision.DENY)
        self.assertIn("разрешениям", d.answer("расскажи о космосе"))
        client.generate.assert_not_called()

    def test_unavailable_retains_goal_not_failed_turn(self):
        client = Mock(); client.generate.side_effect = LocalModelError("offline")
        d = LocalDialogue({}, client)
        self.assertEqual(d.answer("почему небо голубое"), UNAVAILABLE)
        self.assertTrue(d.active); self.assertEqual(d.context._turns, [])

    def test_cancelled_reply_not_spoken_or_remembered(self):
        client = Mock(); client.generate.return_value = "Ответ."
        d = LocalDialogue({}, client)
        self.assertIsNone(d.answer("почему небо голубое", cancelled=lambda: True))
        self.assertEqual(d.context._turns, [])

    def test_action_claim_is_not_committed(self):
        client = Mock(); client.generate.return_value = "Я удалила файлы."
        d = LocalDialogue({}, client); answer = d.answer("расскажи об играх")
        self.assertNotIn("удалила", answer); self.assertEqual(d.context._turns, [])

    def test_endpoint_restrictions(self):
        for url in ("http://example.com:11434", "http://localhost:11434", "http://127.0.0.1:80",
                    "http://user@127.0.0.1:11434", "http://127.0.0.1:11434/redirect", "http://127.0.0.1:11434?x=1"):
            with self.assertRaises(ValueError): LocalConversationClient(url)

    def response(self, data=None, status=200, chunks=None):
        response = Mock(); response.__enter__ = Mock(return_value=response); response.__exit__ = Mock(return_value=False)
        response.status_code = status
        response.iter_content.return_value = chunks if chunks is not None else [json.dumps(data).encode()]
        session = Mock(); session.__enter__ = Mock(return_value=session); session.__exit__ = Mock(return_value=False)
        session.post.return_value = response
        return session

    def test_transport_has_no_redirect_proxy_or_tools(self):
        session = self.response({"done": True, "message": {"content": "Ответ"}})
        with patch("local_dialogue.requests.Session", return_value=session):
            self.assertEqual(LocalConversationClient().generate([{"role":"user", "content":"public"}]), "Ответ")
        self.assertFalse(session.trust_env)
        self.assertFalse(session.post.call_args.kwargs["allow_redirects"])
        self.assertNotIn("tools", session.post.call_args.kwargs["json"])

    def test_redirect_invalid_oversize_and_truncated_fail(self):
        for session in (self.response(status=302), self.response(chunks=[b"x" * 33000]),
                        self.response({"done": True, "done_reason": "length", "message": {"content": "partial"}}),
                        self.response({"done": True, "message": {"content": "ok", "tool_calls": [1]}})):
            with patch("local_dialogue.requests.Session", return_value=session):
                with self.assertRaises(LocalModelError): LocalConversationClient().generate([])

    def test_deadline_is_bounded_even_when_worker_waits(self):
        session = self.response({"done": True, "message": {"content": "late"}})
        def slow(*args, **kwargs):
            time.sleep(1.3)
            return [b'{}']
        session.post.return_value.iter_content.side_effect = slow
        client = LocalConversationClient(deadline=1)
        with patch("local_dialogue.requests.Session", return_value=session):
            start = time.monotonic()
            with self.assertRaisesRegex(LocalModelError, "deadline"): client.generate([])
            self.assertLess(time.monotonic() - start, 1.25)

    def voice_loop(self, utterances, followups=True):
        state = SimpleNamespace(enabled=True, exit_requested=False)
        bridge = FoundationBridge({"local_dialogue_enabled": True})
        bridge.execute = Mock(wraps=bridge.execute)
        tts = Mock(); tts.speak.return_value = None
        remaining = iter(utterances)
        def record(*args):
            try: return next(remaining)
            except StopIteration: state.exit_requested=True; return None
        def wake(text, identity):
            if text.startswith("Векси "): return True, text[6:]
            return False, ""
        stt = Mock(); stt.transcribe.side_effect = lambda audio: audio
        canon = Mock(); canon.canonicalize.side_effect = lambda text: (text, [])
        with patch("local_dialogue.LocalConversationClient.generate", return_value="1) Чтение.\n2) Музыка.") as model, \
                patch("attention_loop.read_preferences", return_value={"public_followups_enabled": followups,
                      "local_dialogue_enabled": True, "name_address_mode": "rare"}):
            run_voice_loop(state, Mock(), Mock(), Mock(), stt=stt, tts=tts, bridge=bridge,
                           record=record, extract_activation=wake, canonicalizer=canon)
        return model, bridge, tts

    def test_voice_context_noise_stop_resume_and_forget(self):
        model, bridge, tts = self.voice_loop(["Векси предложи два варианта отдыха дома", "ммм", "второй подробнее",
            "стреляй в него", "стоп", "подробнее", "Векси продолжим разговор", "забудь разговор", "подробнее"])
        self.assertEqual(model.call_count, 3)
        self.assertEqual(tts.speak.call_count, 4)
        bridge.execute.assert_not_called()

    def test_voice_protected_action_never_routes_through_model(self):
        model, bridge, tts = self.voice_loop(["Векси открой личные документы"])
        model.assert_not_called(); self.assertEqual(bridge.execute.call_count, 1)

    def test_voice_requires_wake_with_followups_disabled(self):
        model, bridge, tts = self.voice_loop(["Векси расскажи о космосе", "подробнее", "Векси подробнее"], False)
        self.assertEqual(model.call_count, 2)


if __name__ == "__main__": unittest.main()
