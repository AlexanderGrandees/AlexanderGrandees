"""Fail-closed capabilities. Authority is held by trusted runtime, not the router."""
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import secrets
from .contracts import Actor, SpeakerRole, Scope, DataClass, ActionRiskClass


class Capability(str, Enum):
    PUBLIC_QUESTION = "PUBLIC_QUESTION"
    MEDIA_PLAY_PAUSE = "MEDIA_PLAY_PAUSE"
    MEDIA_VOLUME = "MEDIA_VOLUME"
    MEDIA_FULLSCREEN = "MEDIA_FULLSCREEN"
    PUBLIC_NAVIGATE = "PUBLIC_NAVIGATE"
    ALLOWLISTED_APP = "ALLOWLISTED_APP"
    WORKSPACE_READ = "WORKSPACE_READ"
    WORKSPACE_CREATE = "WORKSPACE_CREATE"
    WORKSPACE_MUTATE = "WORKSPACE_MUTATE"
    OWNER_MEMORY = "OWNER_MEMORY"
    BUSINESS_DATABASE = "BUSINESS_DATABASE"
    COMMUNICATE = "COMMUNICATE"
    SECURITY = "SECURITY"
    LEGAL_FINANCE = "LEGAL_FINANCE"
    PERMANENT_DELETE = "PERMANENT_DELETE"
    TEMPLATE_LEARN = "TEMPLATE_LEARN"
    TEMPLATE_APPROVE = "TEMPLATE_APPROVE"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"


@dataclass(frozen=True)
class PrivacyContext:
    classes: frozenset[DataClass]
    purpose: str
    destinations: frozenset[str]
    retention: str
    deletion_trigger: str
    lawful_basis: str
    redaction: str
    encryption: str

    def permits(self, destination: str) -> bool:
        if not self.classes or DataClass.SECRET in self.classes:
            return False
        if destination not in self.destinations:
            return False
        if self.classes != frozenset({DataClass.PUBLIC}):
            fields = (self.purpose, self.retention, self.deletion_trigger,
                      self.lawful_basis, self.redaction, self.encryption)
            if any(not f or f.upper() in {"UNKNOWN", "UNRESOLVED"} for f in fields):
                return False
        # This phase has no approved external vendor route registry.
        return destination in {"LOCAL_STORAGE", "LOCAL_TOOL", "LOCAL_MODEL"} and not (
            destination == "LOCAL_MODEL" and self.classes != frozenset({DataClass.PUBLIC}))


@dataclass(frozen=True)
class PermissionRequest:
    operation_id: str
    actor: Actor
    scope: Scope
    capability: Capability
    target_ref: str
    payload_hash: str
    expected_version: str
    privacy: PrivacyContext
    destination: str = "LOCAL_TOOL"
    target_public: bool = False
    target_allowlisted: bool = False
    fresh: bool = True
    conflict: bool = False

    def fingerprint(self) -> str:
        # Approval is invalidated by any change in actor, target, data route or version.
        payload = [self.operation_id, self.actor.subject, self.actor.session,
                   self.actor.role.value, self.scope.tenant, self.scope.project,
                   self.capability.value, self.target_ref, self.payload_hash,
                   self.expected_version, sorted(c.value for c in self.privacy.classes),
                   self.privacy.purpose, sorted(self.privacy.destinations),
                   self.privacy.retention, self.privacy.deletion_trigger,
                   self.privacy.lawful_basis, self.privacy.redaction,
                   self.privacy.encryption, self.destination,
                   self.target_public, self.target_allowlisted, self.fresh, self.conflict]
        return hashlib.sha256(json.dumps(payload, ensure_ascii=True).encode()).hexdigest()


SAFE = frozenset({Capability.PUBLIC_QUESTION, Capability.MEDIA_PLAY_PAUSE,
                  Capability.MEDIA_VOLUME, Capability.MEDIA_FULLSCREEN,
                  Capability.PUBLIC_NAVIGATE, Capability.ALLOWLISTED_APP})
DISABLED = frozenset({Capability.COMMUNICATE, Capability.SECURITY,
                      Capability.LEGAL_FINANCE, Capability.PERMANENT_DELETE})
RISK = {c: ActionRiskClass.A3 for c in Capability}
RISK.update({c: ActionRiskClass.A1 for c in SAFE})
RISK.update({Capability.PUBLIC_QUESTION: ActionRiskClass.A0,
             Capability.WORKSPACE_READ: ActionRiskClass.A0,
             Capability.WORKSPACE_CREATE: ActionRiskClass.A2,
             Capability.ALLOWLISTED_APP: ActionRiskClass.A2})
RISK.update({c: ActionRiskClass.A4 for c in DISABLED})


class OwnerAuthority:
    """Private runtime service: bind only after OS-authenticated owner interaction.

    No voice/JSON transport exposes bind_owner or approve. Python process access is
    trusted; this object is not a sandbox against malicious in-process plugins.
    """
    def __init__(self):
        self._owners: dict[tuple[str, str, Scope], float] = {}
        self._grants: dict[str, tuple[str, float, tuple[str, str, Scope]]] = {}

    def bind_owner(self, actor: Actor, scope: Scope, expires: float):
        if actor.role != SpeakerRole.OWNER:
            raise ValueError("owner_role_required")
        self._owners[(actor.subject, actor.session, scope)] = expires

    def verified(self, actor: Actor, scope: Scope, now: float):
        return (actor.role == SpeakerRole.OWNER and
                self._owners.get((actor.subject, actor.session, scope), 0) > now)

    def revoke(self, actor: Actor, scope: Scope):
        self._owners.pop((actor.subject, actor.session, scope), None)

    def approve(self, owner: Actor, request: PermissionRequest, now: float, ttl: float = 60):
        if not self.verified(owner, request.scope, now) or ttl <= 0:
            raise PermissionError("verified_owner_required")
        token = secrets.token_urlsafe(32)
        key = (owner.subject, owner.session, request.scope)
        self._grants[token] = (request.fingerprint(), min(now + ttl, self._owners[key]), key)
        return token

    def consume(self, token: str | None, request: PermissionRequest, now: float):
        grant = self._grants.pop(token, None) if token else None
        return bool(grant and grant[0] == request.fingerprint() and now < grant[1]
                    and self._owners.get(grant[2], 0) > now)


class GuestSafePolicy:
    def allows(self, request: PermissionRequest):
        return (request.capability in SAFE and request.target_public
                and request.privacy.classes == frozenset({DataClass.PUBLIC})
                and (request.capability != Capability.ALLOWLISTED_APP
                     or request.target_allowlisted))


class CapabilityPolicy:
    def __init__(self, authority: OwnerAuthority):
        self.authority = authority
        self.guest = GuestSafePolicy()

    def evaluate(self, request: PermissionRequest, now: float,
                 approval: str | None = None) -> PolicyDecision:
        if (request.capability not in RISK or request.capability in DISABLED
                or not request.privacy.permits(request.destination)
                or not request.fresh or request.conflict
                or not request.target_ref or not request.payload_hash):
            return PolicyDecision.DENY
        if self.guest.allows(request):
            return PolicyDecision.ALLOW
        owner = self.authority.verified(request.actor, request.scope, now)
        # Learning and promotion always require an exact separate owner decision.
        if owner and request.capability not in {
                Capability.TEMPLATE_LEARN, Capability.TEMPLATE_APPROVE}:
            return PolicyDecision.ALLOW
        if self.authority.consume(approval, request, now):
            return PolicyDecision.ALLOW
        return PolicyDecision.AWAITING_APPROVAL
