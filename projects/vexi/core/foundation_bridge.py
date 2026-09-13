"""V0.1.5 ingress facade. Voice never inherits the logged-in owner's permissions.

Legacy Router is intentionally not reachable from this candidate's voice path.
Only typed, individually permissioned routes below can execute.
"""
import json
import logging
import re
import time
import uuid
from urllib.parse import urlparse, parse_qs
from vexi_foundation.attention import (
    AttentionGate, AttentionSignals, ConversationSession, TaskSession, TaskState,
)
from vexi_foundation.contracts import Actor, Scope, SpeakerRole, DataClass, Evidence, Result, ExecutionState as E
from vexi_foundation.policy import (
    OwnerAuthority, CapabilityPolicy, Capability, PrivacyContext, PermissionRequest, PolicyDecision,
)
from vexi_foundation.workspace import (
    WorkspacePolicy, LocalDraftWorkspace, DocumentCommand, WorkspaceOperation, digest,
)


PUBLIC = PrivacyContext(frozenset({DataClass.PUBLIC}), "public_assistance",
                        frozenset({"LOCAL_TOOL", "LOCAL_MODEL"}), "volatile", "turn_end",
                        "not-applicable", "none", "local")


class MetadataOnlyFilter(logging.Filter):
    def filter(self, record):
        # Suppress legacy free-form logging, exception payloads and model/STT text.
        return (not record.exc_info and record.name == "vexi.foundation"
                and record.msg in {"ATTENTION class=%s decision=%s code=%s",
                                   "EXECUTION state=%s code=%s",
                                   "RUNTIME event=%s"})


class FoundationBridge:
    def __init__(self, config, pack=None, workspace=None):
        self.actor = Actor("voice-unknown", uuid.uuid4().hex, SpeakerRole.UNKNOWN)
        self.scope = Scope("local", "personal")
        self.conversation = ConversationSession()
        self.task = None
        self.tasks = {}
        self.authority = OwnerAuthority()
        self.policy = CapabilityPolicy(self.authority)
        self.gate = AttentionGate()
        self.pack = pack
        self.browser = config.get("browser_name", "Chrome").lower()
        self.workspace = workspace
        self.log = logging.getLogger("vexi.foundation")

    def accept(self, addressed, *, actor=None, continuation_bound=False, ambient=False, now=None):
        actor = actor or self.actor
        now = time.monotonic() if now is None else now
        task = self.tasks.get(actor)
        decision = self.gate.evaluate(AttentionSignals(
            actor, addressed, ambient, continuation_bound, task.task_id if task else None),
            self.conversation, task, now)
        audit = decision.audit()
        self.log.info("ATTENTION class=%s decision=%s code=%s",
                      audit["class"], audit["decision"], audit["code"])
        if decision.accept:
            self.conversation.activate(actor)
        return decision.accept

    def close_task(self, actor=None):
        actor = actor or self.actor
        task = self.tasks.get(actor)
        if task and task.state not in {TaskState.COMPLETED, TaskState.CANCELLED}:
            task.transition(TaskState.COMPLETED, explicit=True)
        self.conversation.close()

    def _task(self, actor):
        task = self.tasks.get(actor)
        if task is None or task.state in {TaskState.COMPLETED, TaskState.CANCELLED}:
            task = TaskSession(uuid.uuid4().hex, actor, self.scope, "local_interaction")
            self.tasks[actor] = task
        self.task = task
        return self.task

    def _result(self, result, actor):
        if result.evidence:
            self._task(actor).record(result.evidence.operation_id, result.evidence.target_id, result)
        self.log.info("EXECUTION state=%s code=%s", result.state.value, result.code)
        phrases = {E.CONFIRMED_SUCCESS: "Готово, результат проверен.",
                   E.ALREADY_SATISFIED: "Уже в нужном состоянии.",
                   E.BLOCKED: "Для этой операции нужен разрешённый маршрут и подтверждение владельца.",
                   E.UNSUPPORTED: "Эта операция ещё не подключена в сборке A+B+C.",
                   E.NOT_FOUND: "Подходящий объект не найден.",
                   E.AMBIGUOUS: "Состояние неоднозначно; действие не подтверждено.",
                   E.FAILED: "Действие не удалось.",
                   E.SENT_NOT_CONFIRMED: "Команда отправлена, результат не подтверждён."}
        return True, phrases[result.state]

    def execute(self, text, *, actor=None, now=None):
        actor = actor or self.actor
        now = time.monotonic() if now is None else now
        t = re.sub(r"\s+", " ", text.lower().replace("ё", "е")).strip(" .!?,")
        self._task(actor)
        if t in {"привет", "здравствуй", "ты тут", "ты здесь", "ты на связи"}:
            return True, "Привет, я здесь."
        if t in {"какая версия", "твоя версия", "версия"}:
            from version import __version__, __channel__
            return True, f"Vexi {__version__}, {__channel__}."
        if t in {"который час", "сколько времени"}:
            return True, time.strftime("Сейчас %H:%M.")
        if t in {"все спасибо", "задача завершена", "заверши задачу", "закрой диалог", "отдыхай"}:
            self.close_task(actor)
            return True, "Хорошо, задача завершена."
        if t in {"не сработало", "не отображается", "ничего не произошло"}:
            self.task.last_target_ref = None
            self.task.verified_result = None
            self.task.transition(TaskState.AWAITING_INPUT)
            return True, "Результат больше не считаю подтверждённым. Уточни объект и нужное действие."
        # Full-string grammar prevents compound-command permission laundering.
        media = {"пауза": ("pause", None), "поставь видео на паузу": ("pause", None),
                 "продолжи видео": ("play", None), "продолжи": ("play", None),
                 "весь экран": ("set_fullscreen", True),
                 "убери видео из полноэкранного режима": ("set_fullscreen", False),
                 "сверни это видео": ("set_fullscreen", False),
                 "тише": ("change_volume", -0.1), "сделай видео тише": ("change_volume", -0.1),
                 "громче": ("change_volume", 0.1), "сделай видео громче": ("change_volume", 0.1)}
        if t in media:
            return self._result(self._media(*media[t], actor, now), actor)
        # Local draft text grammar is intentionally explicit and never uses a global disk search.
        match = re.fullmatch(r"создай черновик ([\w -]+\.(?:txt|md)): (.*)", text, re.I | re.S)
        if match:
            if self.workspace is None:
                return self._result(Result(E.BLOCKED, "workspace_unconfigured"), actor)
            name, content = match.groups()
            payload = content.encode("utf-8")
            privacy = PrivacyContext(frozenset({DataClass.CONFIDENTIAL}), "local_draft",
                                     frozenset({"LOCAL_STORAGE"}), "workspace-owner-managed",
                                     "owner_delete", "not-applicable", "none", "local")
            req = PermissionRequest(uuid.uuid4().hex, actor, self.scope, Capability.WORKSPACE_CREATE,
                                    name, digest(payload), "ABSENT", privacy, "LOCAL_STORAGE")
            provider = LocalDraftWorkspace(self.workspace, self.policy)
            return self._result(provider.execute(DocumentCommand(req, WorkspaceOperation.CREATE,
                                                                 name, payload), now), actor)
        # No speculative LLM fallback before a public-data classifier is connected.
        # The typed core supports PUBLIC_QUESTION; voice free-form classification is pending.
        return self._result(Result(E.BLOCKED, "unclassified_or_protected"), actor)

    def _media(self, op, value, actor, now):
        if self.pack is None:
            from browser_pack_client import BrowserPackClient
            self.pack = BrowserPackClient()
        status = self.pack.status(self.browser)
        if not status.get("connected") or status.get("site") != "youtube":
            return Result(E.NOT_FOUND, "public_media_unavailable")
        before = self.pack.snapshot(self.browser, max_age=2.0)
        if not before or before.get("site") != "youtube" or before.get("page_type") != "VIDEO":
            return Result(E.NOT_FOUND, "fresh_video_required")
        url = before.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"www.youtube.com", "youtube.com"}:
            return Result(E.BLOCKED, "public_target_required")
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if not video_id:
            return Result(E.BLOCKED, "media_identity_unresolved")
        state = before.get("media") or {}
        if op == "change_volume":
            if not isinstance(state.get("volume"), (int, float)):
                return Result(E.AMBIGUOUS, "volume_unobserved")
            op, value = "set_volume", max(0, min(1, state["volume"] + value))
        cap = (Capability.MEDIA_VOLUME if op == "set_volume" else Capability.MEDIA_FULLSCREEN
               if op == "set_fullscreen" else Capability.MEDIA_PLAY_PAUSE)
        payload = {"op": op}
        if value is not None:
            payload["value"] = value
        target = "youtube:" + video_id
        version = digest(json.dumps(state, sort_keys=True).encode())
        req = PermissionRequest(uuid.uuid4().hex, actor, self.scope, cap, target,
                                digest(json.dumps(payload, sort_keys=True).encode()), version,
                                PUBLIC, target_public=True)
        if self.policy.evaluate(req, now) != PolicyDecision.ALLOW:
            return Result(E.BLOCKED, "media_policy")
        # Second read catches target switches before dispatch. Bridge protocol v1 has
        # no atomic expected-tab/version command; concurrent switches remain a field gate.
        current = self.pack.snapshot(self.browser, max_age=2.0)
        if not current or current.get("url") != url or current.get("media") != before.get("media"):
            return Result(E.BLOCKED, "stale_media")
        result, _ = self.pack.issue(self.browser, "media_action", payload, timeout=3.5)
        if result in {"FAILED", "BLOCKED", "UNSUPPORTED"}:
            return Result(E(result), "media_dispatch")
        def verified(snap):
            if snap.get("url") != url:
                return False
            m = snap.get("media") or {}
            if op == "pause": return m.get("paused") is True
            if op == "play": return m.get("paused") is False
            if op == "set_fullscreen": return m.get("fullscreen") is value
            if op == "set_volume":
                return isinstance(m.get("volume"), (int, float)) and abs(m["volume"] - value) < .02
            return False
        after = self.pack.wait_for(self.browser, verified, timeout=3.0)
        if not after or not verified(after):
            return Result(E.SENT_NOT_CONFIRMED, "media_readback_unconfirmed")
        return Result(E.CONFIRMED_SUCCESS, "media_readback",
                      Evidence(req.operation_id, target,
                               digest(json.dumps(after["media"], sort_keys=True).encode()), "media_state"))
