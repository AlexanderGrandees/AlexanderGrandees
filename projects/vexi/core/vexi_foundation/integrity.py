"""Generic change/reconciliation primitives; no legal-specific semantics."""
from dataclasses import dataclass
from enum import Enum
from .contracts import Scope


class Materiality(str, Enum):
    IDENTICAL = "IDENTICAL"
    COSMETIC = "COSMETIC"
    CONTENT = "CONTENT"
    BUSINESS_MATERIAL = "BUSINESS_MATERIAL"
    HIGH_RISK = "HIGH_RISK"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Change:
    source_id: str
    old_hash: str
    new_hash: str
    materiality: Materiality


class DependencyGraph:
    def __init__(self):
        self.edges: dict[str, set[str]] = {}
        self.stale: set[str] = set()
        self.history: list[tuple[Change, tuple[str, ...]]] = []

    def link(self, source: str, dependent: str):
        self.edges.setdefault(source, set()).add(dependent)

    def reconcile(self, change: Change) -> tuple[str, ...]:
        if change.old_hash == change.new_hash:
            return ()
        if change.materiality == Materiality.IDENTICAL:
            raise ValueError("hash_change_not_identical")
        if change.materiality == Materiality.COSMETIC:
            self.history.append((change, ()))
            return ()
        # Unknown semantics preserve uncertainty and gate dependents pending review.
        found, pending = {change.source_id}, [change.source_id]
        while pending:
            for dependent in self.edges.get(pending.pop(), set()):
                if dependent not in found:
                    found.add(dependent)
                    pending.append(dependent)
        affected = tuple(sorted(found))
        self.stale.update(found)
        self.history.append((change, affected))
        return affected


class SourceKind(str, Enum):
    CANONICAL_DB = "CANONICAL_DB"
    VERIFIED_INTEGRATION = "VERIFIED_INTEGRATION"
    APPROVED_DOCUMENT = "APPROVED_DOCUMENT"
    PARSED_FILE = "PARSED_FILE"
    USER_STATEMENT = "USER_STATEMENT"
    MODEL_INFERENCE = "MODEL_INFERENCE"


@dataclass(frozen=True)
class FieldSource:
    source_ref: str
    value_ref: str
    scope: Scope
    kind: SourceKind
    verified_at: float
    stale_after: float
    applicable: bool


@dataclass(frozen=True)
class SourceResolution:
    preferred: FieldSource | None
    conflict: tuple[FieldSource, ...]


class SourceHierarchy:
    def __init__(self, order: tuple[SourceKind, ...] = tuple(SourceKind)):
        if set(order) != set(SourceKind) or len(order) != len(SourceKind):
            raise ValueError("invalid_source_hierarchy")
        self.rank = {kind: i for i, kind in enumerate(order)}

    def resolve(self, sources: tuple[FieldSource, ...], scope: Scope,
                now: float) -> SourceResolution:
        valid = [s for s in sources if s.scope == scope and s.applicable
                 and 0 <= s.verified_at <= now < s.stale_after]
        if not valid:
            return SourceResolution(None, ())
        valid.sort(key=lambda s: (self.rank[s.kind], s.source_ref))
        conflict = tuple(valid) if len({s.value_ref for s in valid}) > 1 else ()
        # Preferred is an advisory candidate; conflict must block writes.
        return SourceResolution(valid[0], conflict)
