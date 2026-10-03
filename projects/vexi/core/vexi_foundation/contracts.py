"""Shared wire vocabulary. No OS, model, microphone or database dependencies."""
from dataclasses import dataclass
from enum import Enum


class AttentionClass(str, Enum):
    DIRECTED = "DIRECTED"
    CONTEXTUAL = "CONTEXTUAL"
    AMBIENT = "AMBIENT"
    UNKNOWN = "UNKNOWN"


class SpeakerRole(str, Enum):
    OWNER = "OWNER"
    GUEST = "GUEST"
    UNKNOWN = "UNKNOWN"


class ExecutionState(str, Enum):
    CONFIRMED_SUCCESS = "CONFIRMED_SUCCESS"
    SENT_NOT_CONFIRMED = "SENT_NOT_CONFIRMED"
    ALREADY_SATISFIED = "ALREADY_SATISFIED"
    NOT_FOUND = "NOT_FOUND"
    BLOCKED = "BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"
    AMBIGUOUS = "AMBIGUOUS"


class ActionRiskClass(str, Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    UNKNOWN = "UNKNOWN"


class DataClass(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    PERSONAL = "PERSONAL"
    SPECIAL_CATEGORY = "SPECIAL_CATEGORY"
    RESTRICTED_CASE = "RESTRICTED_CASE"
    SECRET = "SECRET"


@dataclass(frozen=True)
class Scope:
    tenant: str
    project: str

    def __post_init__(self):
        if not self.tenant or not self.project:
            raise ValueError("scope_required")


@dataclass(frozen=True)
class Actor:
    """Issued by a trusted ingress adapter, never parsed from utterance/model JSON."""
    subject: str
    session: str
    role: SpeakerRole = SpeakerRole.UNKNOWN


@dataclass(frozen=True)
class Evidence:
    operation_id: str
    target_id: str
    observed_hash: str
    check: str


@dataclass(frozen=True)
class Result:
    state: ExecutionState
    code: str
    evidence: Evidence | None = None

    def __post_init__(self):
        if self.state in (ExecutionState.CONFIRMED_SUCCESS,
                          ExecutionState.ALREADY_SATISFIED) and self.evidence is None:
            raise ValueError("success_requires_evidence")
