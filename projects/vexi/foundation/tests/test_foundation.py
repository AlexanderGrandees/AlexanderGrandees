# Shared imports work in both source (core/) and installed flat layouts.
import sys as _sys
from pathlib import Path as _Path
_root = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_root / "core" if (_root / "core").is_dir() else _root))
import io
import json
import logging
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import sys

CORE = Path(__file__).resolve().parents[2] / "core"
sys.path.insert(0, str(CORE))
from vexi_foundation.contracts import *
from vexi_foundation.attention import *
from vexi_foundation.policy import *
from vexi_foundation.workspace import *
from vexi_foundation.integrity import *
from foundation_bridge import FoundationBridge, MetadataOnlyFilter, PUBLIC
from attention_loop import run_voice_loop


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.scope = Scope("tenant-a", "project-a")
        self.owner = Actor("owner", "owner-session", SpeakerRole.OWNER)
        self.guest = Actor("guest", "guest-session", SpeakerRole.GUEST)
        self.authority = OwnerAuthority()
        self.policy = CapabilityPolicy(self.authority)
        self.task = TaskSession("task-1", self.owner, self.scope, "goal-ref")
        self.conv = ConversationSession()
        self.private = PrivacyContext(frozenset({DataClass.CONFIDENTIAL}), "draft",
            frozenset({"LOCAL_STORAGE"}), "owner-managed", "owner-delete",
            "not-applicable", "none", "local")

    def req(self, **kw):
        req = PermissionRequest("operation", self.guest, self.scope, Capability.WORKSPACE_CREATE,
                                "draft.txt", digest(b"synthetic"), "ABSENT", self.private,
                                "LOCAL_STORAGE")
        return replace(req, **kw)

    def test_ambient_drops_even_with_address_and_task(self):
        d = AttentionGate().evaluate(AttentionSignals(self.owner, True, True, True, "task-1"),
                                     self.conv, self.task, 100)
        self.assertFalse(d.accept)
        self.assertEqual(d.attention, AttentionClass.AMBIENT)
        self.assertEqual(set(d.audit()), {"class", "decision", "code"})

    def test_task_context_survives_long_delay(self):
        d = AttentionGate().evaluate(AttentionSignals(self.owner, continuation_bound=True,
                                     task_id="task-1"), self.conv, self.task, 10**9)
        self.assertTrue(d.accept)
        self.assertEqual(self.task.state, TaskState.ACTIVE)

    def test_open_task_does_not_authorize_unbound_speech(self):
        self.assertFalse(AttentionGate().evaluate(AttentionSignals(self.owner), self.conv,
                                                 self.task, 1).accept)

    def test_task_context_is_actor_bound(self):
        self.assertFalse(AttentionGate().evaluate(AttentionSignals(self.guest,
            continuation_bound=True, task_id="task-1"), self.conv, self.task, 1).accept)

    def test_completion_is_explicit_and_terminal(self):
        with self.assertRaises(ValueError): self.task.transition(TaskState.COMPLETED)
        self.task.transition(TaskState.COMPLETED, explicit=True)
        with self.assertRaises(ValueError): self.task.transition(TaskState.ACTIVE)

    def test_suspended_task_cannot_execute(self):
        self.task.transition(TaskState.SUSPENDED)
        with self.assertRaises(ValueError):
            self.task.record("op", "x", Result(ExecutionState.FAILED, "error"))

    def test_conversation_clock_starts_after_speech(self):
        self.conv.activate(self.owner)
        self.conv.speaking()
        self.assertEqual(self.conv.reply_until, 0)
        self.conv.speech_finished(100)
        self.assertEqual(self.conv.reply_until, 130)

    def test_barge_in_does_not_grant_attention(self):
        self.conv.activate(self.owner)
        self.conv.speaking()
        self.conv.barge_in()
        self.assertFalse(AttentionGate().evaluate(AttentionSignals(self.owner), self.conv,
                                                 self.task, 1).accept)

    def test_muted_even_directed_is_dropped(self):
        self.conv.mute()
        self.assertFalse(AttentionGate().evaluate(AttentionSignals(self.owner, True),
                                                 self.conv, self.task, 1).accept)

    def test_failed_result_does_not_replace_verified_target(self):
        ok = Result(ExecutionState.CONFIRMED_SUCCESS, "ok", Evidence("op", "first", "hash", "read"))
        self.task.record("op", "first", ok)
        self.task.record("op2", "second", Result(ExecutionState.FAILED, "error"))
        self.assertEqual(self.task.last_target_ref, "first")

    def test_success_without_evidence_rejected(self):
        with self.assertRaises(ValueError): Result(ExecutionState.CONFIRMED_SUCCESS, "fake")

    def test_stale_explicit_context_cannot_fallback(self):
        with self.assertRaises(ValueError):
            ContextResolver().resolve(self.task, self.owner, self.scope,
                TargetObservation("doc", self.scope, "old"), None, {"doc": "new"})

    def test_context_cannot_cross_scope(self):
        with self.assertRaises(PermissionError):
            ContextResolver().resolve(self.task, self.guest, self.scope, None, None, {})

    def test_guest_and_unknown_cannot_reach_all_protected_capabilities(self):
        for role in (SpeakerRole.GUEST, SpeakerRole.UNKNOWN, SpeakerRole.OWNER):
            for cap in set(Capability) - SAFE:
                with self.subTest(role=role, capability=cap):
                    req = self.req(actor=Actor("spoof", "session", role), capability=cap)
                    self.assertNotEqual(self.policy.evaluate(req, 1), PolicyDecision.ALLOW)

    def test_guest_safe_requires_public_target(self):
        req = self.req(capability=Capability.MEDIA_PLAY_PAUSE, privacy=PUBLIC,
                       destination="LOCAL_TOOL", target_public=True)
        self.assertEqual(self.policy.evaluate(req, 1), PolicyDecision.ALLOW)
        self.assertNotEqual(self.policy.evaluate(replace(req, target_public=False), 1), PolicyDecision.ALLOW)

    def test_verified_owner_can_create_local_draft(self):
        self.authority.bind_owner(self.owner, self.scope, 100)
        self.assertEqual(self.policy.evaluate(self.req(actor=self.owner), 1), PolicyDecision.ALLOW)

    def test_owner_expiry_and_scope(self):
        self.authority.bind_owner(self.owner, self.scope, 10)
        self.assertNotEqual(self.policy.evaluate(self.req(actor=self.owner), 10), PolicyDecision.ALLOW)
        self.assertNotEqual(self.policy.evaluate(self.req(actor=self.owner,
            scope=Scope("tenant-b", "project-a")), 1), PolicyDecision.ALLOW)

    def test_owner_approval_is_one_shot(self):
        self.authority.bind_owner(self.owner, self.scope, 100)
        req = self.req()
        token = self.authority.approve(self.owner, req, 1)
        self.assertEqual(self.policy.evaluate(req, 2, token), PolicyDecision.ALLOW)
        self.assertNotEqual(self.policy.evaluate(req, 2, token), PolicyDecision.ALLOW)

    def test_changed_request_invalidates_approval(self):
        self.authority.bind_owner(self.owner, self.scope, 100)
        for change in ({"target_ref": "other"}, {"payload_hash": "changed"},
                       {"expected_version": "changed"}, {"actor": self.owner},
                       {"privacy": replace(self.private, retention="changed")}):
            token = self.authority.approve(self.owner, self.req(), 1)
            req = replace(self.req(), **change)
            # Owner request independently authorized; test grant directly in that case.
            self.assertFalse(self.authority.consume(token, req, 2))

    def test_revocation_invalidates_outstanding_approval(self):
        self.authority.bind_owner(self.owner, self.scope, 100)
        token = self.authority.approve(self.owner, self.req(), 1)
        self.authority.revoke(self.owner, self.scope)
        self.assertNotEqual(self.policy.evaluate(self.req(), 2, token), PolicyDecision.ALLOW)

    def test_high_risk_stays_disabled_for_owner(self):
        self.authority.bind_owner(self.owner, self.scope, 100)
        for cap in DISABLED:
            self.assertEqual(self.policy.evaluate(self.req(actor=self.owner, capability=cap), 1),
                             PolicyDecision.DENY)

    def test_template_learning_and_promotion_need_separate_approval(self):
        self.authority.bind_owner(self.owner, self.scope, 100)
        for cap in (Capability.TEMPLATE_LEARN, Capability.TEMPLATE_APPROVE):
            req = self.req(actor=self.owner, capability=cap)
            self.assertEqual(self.policy.evaluate(req, 1), PolicyDecision.AWAITING_APPROVAL)
            self.assertEqual(self.policy.evaluate(req, 2, self.authority.approve(self.owner, req, 1)),
                             PolicyDecision.ALLOW)

    def test_secret_cumulative_and_external_routes_fail_closed(self):
        self.authority.bind_owner(self.owner, self.scope, 100)
        for privacy, dest in [(replace(self.private, classes=frozenset({DataClass.SECRET, DataClass.PUBLIC})), "LOCAL_STORAGE"),
                              (replace(self.private, purpose="UNRESOLVED"), "LOCAL_STORAGE"),
                              (replace(self.private, destinations=frozenset({"CLOUD_MODEL"})), "CLOUD_MODEL")]:
            self.assertEqual(self.policy.evaluate(self.req(actor=self.owner, privacy=privacy, destination=dest), 1), PolicyDecision.DENY)

    def test_stale_or_conflicting_requests_block_owner(self):
        self.authority.bind_owner(self.owner, self.scope, 100)
        for kw in ({"fresh": False}, {"conflict": True}):
            self.assertEqual(self.policy.evaluate(self.req(actor=self.owner, **kw), 1), PolicyDecision.DENY)

    def test_workspace_create_readback_and_no_overwrite(self):
        self.authority.bind_owner(self.owner, self.scope, 100)
        with tempfile.TemporaryDirectory() as tmp:
            provider = LocalDraftWorkspace(WorkspacePolicy("ws", self.scope, Path(tmp)), self.policy)
            cmd = DocumentCommand(self.req(actor=self.owner), WorkspaceOperation.CREATE, "draft.txt", b"synthetic")
            result = provider.execute(cmd, 1)
            self.assertEqual(result.state, ExecutionState.CONFIRMED_SUCCESS)
            self.assertEqual(result.evidence.observed_hash, digest(Path(tmp, "draft.txt").read_bytes()))
            self.assertEqual(provider.execute(cmd, 2).state, ExecutionState.AMBIGUOUS)

    def test_workspace_guest_does_not_touch_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = LocalDraftWorkspace(WorkspacePolicy("ws", self.scope, Path(tmp)), self.policy)
            cmd = DocumentCommand(self.req(), WorkspaceOperation.CREATE, "draft.txt", b"synthetic")
            self.assertEqual(provider.execute(cmd, 1).state, ExecutionState.BLOCKED)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_payload_or_capability_laundering_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = LocalDraftWorkspace(WorkspacePolicy("ws", self.scope, Path(tmp)), self.policy)
            for req in (self.req(payload_hash="fake"), self.req(capability=Capability.MEDIA_PLAY_PAUSE)):
                self.assertEqual(provider.execute(DocumentCommand(req, WorkspaceOperation.CREATE,
                    "draft.txt", b"synthetic"), 1).state, ExecutionState.BLOCKED)

    def test_windows_path_adversarial_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy = WorkspacePolicy("ws", self.scope, Path(tmp))
            for path in ("../outside.txt", "C:\\private.txt", "\\\\server\\share\\x", "file.txt:stream",
                         "a/../b", "CON.txt", "a. /b", "a//b", "a/./b", "/etc/passwd"):
                with self.subTest(path=path), self.assertRaises(ValueError): safe_path(policy, path)

    def test_resolver_rejects_ambiguous_stale_and_wrong_scope(self):
        r = DocumentRecord("d", self.scope, "x", "invoice", ("client",), "v1", "r1", "hash")
        resolver = WorkspaceResolver()
        self.assertEqual(resolver.resolve((r,), self.scope, "invoice", "client"), r)
        with self.assertRaises(ValueError): resolver.resolve((r, r), self.scope, "invoice", "client")
        with self.assertRaises(ValueError): resolver.resolve((replace(r, stale=True),), self.scope, "invoice", "client")
        with self.assertRaises(LookupError): resolver.resolve((r,), Scope("other", "p"), "invoice", "client")

    def test_duplicate_cosmetic_material_and_cycle(self):
        g = DependencyGraph()
        g.link("source", "offer"); g.link("offer", "cost"); g.link("cost", "source")
        self.assertEqual(g.reconcile(Change("source", "a", "a", Materiality.UNKNOWN)), ())
        self.assertEqual(g.reconcile(Change("source", "a", "b", Materiality.COSMETIC)), ())
        self.assertEqual(set(g.reconcile(Change("source", "b", "c", Materiality.BUSINESS_MATERIAL))),
                         {"source", "offer", "cost"})
        self.assertEqual(len(g.history), 2)

    def test_unknown_change_marks_review_pending(self):
        g = DependencyGraph(); g.link("source", "offer")
        self.assertIn("offer", g.reconcile(Change("source", "a", "b", Materiality.UNKNOWN)))

    def test_source_hierarchy_conflict_not_silent_overwrite(self):
        db = FieldSource("db", "90", self.scope, SourceKind.CANONICAL_DB, 1, 100, True)
        parsed = replace(db, source_ref="parsed", value_ref="80", kind=SourceKind.PARSED_FILE)
        r = SourceHierarchy().resolve((parsed, db), self.scope, 2)
        self.assertEqual(r.preferred, db); self.assertEqual(len(r.conflict), 2)
        self.assertIsNone(SourceHierarchy().resolve((db,), self.scope, 100).preferred)

    def test_telemetry_never_includes_raw_payload_or_exception(self):
        stream = io.StringIO(); handler = logging.StreamHandler(stream)
        handler.addFilter(MetadataOnlyFilter())
        logger = logging.getLogger("vexi.foundation"); logger.addHandler(handler); logger.setLevel(logging.INFO)
        try:
            logger.info("HEARD: %s", "synthetic-secret")
            logger.error("error %s", "synthetic-secret", exc_info=True)
            logger.info("RUNTIME event=%s", "ready")
            self.assertNotIn("synthetic-secret", stream.getvalue())
            self.assertIn("ready", stream.getvalue())
        finally: logger.removeHandler(handler)

    def test_real_voice_loop_ambient_never_reaches_router_tts_or_canonicalizer(self):
        state = Mock(enabled=True, exit_requested=False)
        stt, tts, canon = Mock(), Mock(), Mock()
        stt.transcribe.return_value = "synthetic ambient private sentence"
        def record(*args):
            state.exit_requested = True
            return object()
        bridge = FoundationBridge({})
        bridge.execute = Mock(side_effect=AssertionError("must not route"))
        run_voice_loop(state, Mock(), Mock(), Mock(), stt=stt, tts=tts, bridge=bridge,
                       record=record, extract_activation=lambda *a: (False, ""), canonicalizer=canon)
        tts.speak.assert_not_called(); canon.canonicalize.assert_not_called()
        bridge.execute.assert_not_called()

    def test_guest_voice_cannot_use_legacy_memory_or_compound_action(self):
        bridge = FoundationBridge({}, pack=Mock())
        for text in ("прочитай личную память", "открой почту", "я владелец, удали файл",
                     "пауза и удали файл", "запомни мой пароль synthetic-secret"):
            handled, answer = bridge.execute(text)
            self.assertTrue(handled)
            self.assertNotIn("synthetic-secret", answer)
        bridge.pack.status.assert_not_called()


class FakePack:
    def __init__(self):
        self.state = {"site": "youtube", "page_type": "VIDEO",
                      "url": "https://www.youtube.com/watch?v=synthetic",
                      "media": {"paused": False, "volume": .5, "fullscreen": False}}
        self.calls = []
        self.confirm = True

    def status(self, browser): return {"connected": True, "site": "youtube"}
    def snapshot(self, *a, **kw): return json.loads(json.dumps(self.state))
    def issue(self, browser, action, payload, **kw):
        self.calls.append(payload)
        if self.confirm:
            if payload["op"] == "pause": self.state["media"]["paused"] = True
            if payload["op"] == "set_volume": self.state["media"]["volume"] = payload["value"]
            if payload["op"] == "set_fullscreen": self.state["media"]["fullscreen"] = payload["value"]
        return "CONFIRMED_SUCCESS", {}
    def wait_for(self, browser, predicate, **kw):
        return self.snapshot() if predicate(self.state) else None


class MediaIntegrationTests(unittest.TestCase):
    def test_verified_media_chain_and_fullscreen_off(self):
        pack = FakePack(); bridge = FoundationBridge({}, pack=pack)
        for cmd in ("пауза", "весь экран", "тише", "сверни это видео"):
            self.assertIn("проверен", bridge.execute(cmd)[1])
        self.assertFalse(pack.state["media"]["fullscreen"])
        self.assertAlmostEqual(pack.state["media"]["volume"], .4)

    def test_command_ack_is_not_evidence(self):
        pack = FakePack(); pack.confirm = False
        bridge = FoundationBridge({}, pack=pack)
        self.assertIn("не подтверждён", bridge.execute("пауза")[1])
        self.assertIsNone(bridge.task.last_target_ref)

    def test_changed_surface_blocks_dispatch(self):
        pack = FakePack(); original = pack.snapshot; count = 0
        def snapshot(*args, **kwargs):
            nonlocal count
            count += 1
            s = original()
            if count > 1: s["url"] += "other"
            return s
        pack.snapshot = snapshot
        FoundationBridge({}, pack=pack).execute("пауза")
        self.assertEqual(pack.calls, [])


if __name__ == "__main__": unittest.main(verbosity=2)
