"""Metadata-only attention gate and independent task/conversation lifecycles."""
from dataclasses import dataclass, field
from enum import Enum
from .contracts import Actor, AttentionClass, Scope, Result, ExecutionState


class TaskState(str, Enum):
    ACTIVE = "ACTIVE"
    AWAITING_INPUT = "AWAITING_INPUT"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ConversationState(str, Enum):
    INACTIVE = "INACTIVE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"
    MUTED = "MUTED"
    RECOVERY = "RECOVERY"


@dataclass
class TaskSession:
    task_id: str
    actor: Actor
    scope: Scope
    goal_ref: str
    state: TaskState = TaskState.ACTIVE
    last_target_ref: str | None = None
    expected_response_ref: str | None = None
    recent_action_ref: str | None = None
    verified_result: Result | None = None
    revision: int = 0

    def transition(self, new: TaskState, *, explicit: bool = False):
        if self.state in (TaskState.COMPLETED, TaskState.CANCELLED):
            raise ValueError("terminal_task")
        if new in (TaskState.COMPLETED, TaskState.CANCELLED) and not explicit:
            raise ValueError("explicit_close_required")
        self.state = new
        self.revision += 1
        if new in (TaskState.COMPLETED, TaskState.CANCELLED):
            self.last_target_ref = self.expected_response_ref = None
            self.recent_action_ref = self.verified_result = None

    def record(self, action_ref: str, target_ref: str, result: Result):
        if self.state not in (TaskState.ACTIVE, TaskState.AWAITING_INPUT):
            raise ValueError("task_not_executable")
        self.recent_action_ref = action_ref
        if result.state in (ExecutionState.CONFIRMED_SUCCESS, ExecutionState.ALREADY_SATISFIED):
            if result.evidence.target_id != target_ref:
                raise ValueError("evidence_target_mismatch")
            self.last_target_ref = target_ref
            self.verified_result = result
        self.revision += 1


@dataclass
class ConversationSession:
    state: ConversationState = ConversationState.INACTIVE
    actor_session: str | None = None
    reply_until: float = 0
    reply_window_seconds: float = 30

    def activate(self, actor: Actor):
        if self.state == ConversationState.MUTED:
            return
        self.actor_session = actor.session
        self.state = ConversationState.LISTENING

    def speaking(self):
        if self.state == ConversationState.MUTED:
            raise ValueError("muted")
        self.state = ConversationState.SPEAKING
        self.reply_until = 0

    def speech_finished(self, now: float):
        if self.state != ConversationState.SPEAKING:
            raise ValueError("not_speaking")
        self.state = ConversationState.LISTENING
        self.reply_until = now + self.reply_window_seconds

    def barge_in(self):
        # Audio cancellation is orthogonal to permission to answer.
        if self.state == ConversationState.SPEAKING:
            self.state = ConversationState.LISTENING
            self.reply_until = 0

    def mute(self):
        self.state = ConversationState.MUTED
        self.reply_until = 0

    def close(self):
        self.state = ConversationState.INACTIVE
        self.actor_session = None
        self.reply_until = 0


@dataclass(frozen=True)
class AttentionSignals:
    """Trusted local classifier output. Deliberately has no transcript field.

    continuation_bound means ingress proved this is the expected speaker/turn;
    an open task, keyword overlap or an LLM assertion is insufficient.
    """
    actor: Actor
    addressed: bool = False
    ambient: bool = False
    continuation_bound: bool = False
    task_id: str | None = None


@dataclass(frozen=True)
class AttentionDecision:
    attention: AttentionClass
    accept: bool
    code: str

    def audit(self):
        return {"class": self.attention.value,
                "decision": "ACCEPT" if self.accept else "DROP", "code": self.code}


class AttentionGate:
    def evaluate(self, signals: AttentionSignals, conversation: ConversationSession,
                 task: TaskSession | None, now: float) -> AttentionDecision:
        if conversation.state == ConversationState.MUTED:
            return AttentionDecision(AttentionClass.UNKNOWN, False, "muted")
        if signals.ambient:
            return AttentionDecision(AttentionClass.AMBIENT, False, "ambient")
        if signals.addressed:
            return AttentionDecision(AttentionClass.DIRECTED, True, "addressed")
        if signals.continuation_bound:
            if (task and signals.task_id == task.task_id and signals.actor == task.actor
                    and task.state in (TaskState.ACTIVE, TaskState.AWAITING_INPUT)):
                return AttentionDecision(AttentionClass.CONTEXTUAL, True, "task_continuation")
            if (signals.task_id is None and signals.actor.session == conversation.actor_session
                    and conversation.state == ConversationState.LISTENING
                    and 0 < now <= conversation.reply_until):
                return AttentionDecision(AttentionClass.CONTEXTUAL, True, "conversation_reply")
        return AttentionDecision(AttentionClass.UNKNOWN, False, "not_addressed")


@dataclass(frozen=True)
class TargetObservation:
    target_ref: str
    scope: Scope
    version: str


class ContextResolver:
    def resolve(self, task: TaskSession, actor: Actor, scope: Scope,
                explicit: TargetObservation | None, active: TargetObservation | None,
                current_versions: dict[str, str]) -> str | None:
        if actor != task.actor or scope != task.scope:
            raise PermissionError("context_scope")
        if task.state not in (TaskState.ACTIVE, TaskState.AWAITING_INPUT):
            raise ValueError("context_inactive")
        # Explicit target wins; a stale explicit observation cannot silently fall back.
        candidate = explicit or active
        if candidate:
            if candidate.scope != scope:
                raise PermissionError("target_scope")
            if current_versions.get(candidate.target_ref) != candidate.version:
                raise ValueError("stale_target")
            return candidate.target_ref
        if task.last_target_ref and task.verified_result:
            ev = task.verified_result.evidence
            if current_versions.get(task.last_target_ref) != ev.observed_hash:
                raise ValueError("stale_target")
            return task.last_target_ref
        return None
