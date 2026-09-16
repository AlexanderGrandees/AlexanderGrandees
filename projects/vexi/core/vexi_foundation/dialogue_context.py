"""Volatile conversation context; no ingress classifier or capability authority.

Only trusted ingress may call begin_turn after attention and privacy gates.
Model output is data. It cannot change objective, evidence or permissions.
"""
from dataclasses import dataclass, field
from enum import Enum
import secrets


class DialogueState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class GenerationTicket:
    session: str
    revision: int


@dataclass(frozen=True, repr=False)
class Turn:
    user: str
    assistant: str


@dataclass(repr=False)
class DialogueContext:
    """Keep explicit objective until close, even when recent turns are evicted.

    Repr deliberately excludes all content. Bounds use characters, not tokens;
    model adapters must separately enforce their tokenizer/context limits.
    """
    max_pairs: int = 12
    max_chars: int = 12000
    state: DialogueState = field(default=DialogueState.IDLE, init=False)
    objective: str = field(default="", init=False)
    revision: int = field(default=0, init=False)
    _session: str = field(default_factory=lambda: secrets.token_hex(16), init=False)
    _turns: list[Turn] = field(default_factory=list, init=False)
    _pending: str | None = field(default=None, init=False)

    def __post_init__(self):
        if self.max_pairs < 1 or self.max_chars < 256:
            raise ValueError("invalid_context_bounds")

    def set_objective(self, text: str):
        """Trusted explicit user objective/correction, never model inference."""
        if self.state == DialogueState.CLOSED:
            raise ValueError("closed_session")
        if not isinstance(text, str) or not text.strip() or len(text) > min(2000, self.max_chars // 4):
            raise ValueError("invalid_objective")
        self.cancel()
        self.objective = text.strip()

    def begin_turn(self, text: str) -> GenerationTicket:
        if self.state == DialogueState.CLOSED:
            raise ValueError("closed_session")
        if not isinstance(text, str) or not text.strip() or len(text) > self.max_chars // 2:
            raise ValueError("invalid_turn")
        self.revision += 1
        self._pending = text.strip()
        self.state = DialogueState.THINKING
        return GenerationTicket(self._session, self.revision)

    def messages(self, ticket: GenerationTicket) -> list[dict[str, str]]:
        if not self._current(ticket):
            raise ValueError("stale_generation")
        available = self.max_chars - len(self._pending) - len(self.objective) - 16
        selected = []
        for turn in reversed(self._turns):
            size = len(turn.user) + len(turn.assistant)
            if size > available:
                break
            selected.append(turn)
            available -= size
        result = []
        # Objective remains user data, never promoted to system instructions.
        if self.objective:
            result.append({"role": "user", "content": "Текущая задача: " + self.objective})
        for turn in reversed(selected):
            result.extend([{"role": "user", "content": turn.user},
                           {"role": "assistant", "content": turn.assistant}])
        result.append({"role": "user", "content": self._pending})
        return result

    def _current(self, ticket):
        return (self.state == DialogueState.THINKING and self._pending is not None
                and ticket == GenerationTicket(self._session, self.revision))

    def commit(self, ticket: GenerationTicket, answer: str) -> bool:
        if not self._current(ticket):
            return False
        if not isinstance(answer, str) or not answer.strip() or len(answer) > self.max_chars // 2:
            self.cancel()
            return False
        self._turns.append(Turn(self._pending, answer.strip()))
        self._pending = None
        while (len(self._turns) > self.max_pairs or
               sum(len(t.user) + len(t.assistant) for t in self._turns) > self.max_chars):
            self._turns.pop(0)
        self.state = DialogueState.LISTENING
        return True

    def cancel(self):
        self.revision += 1
        self._pending = None
        if self.state != DialogueState.CLOSED:
            self.state = DialogueState.PAUSED

    def pause(self):
        self.cancel()  # Listening timeout does not erase objective or accepted turns.

    def close(self):
        self.cancel()
        self.objective = ""
        self._turns.clear()
        self.state = DialogueState.CLOSED

    def __repr__(self):
        return f"DialogueContext(state={self.state.value}, revision={self.revision})"
