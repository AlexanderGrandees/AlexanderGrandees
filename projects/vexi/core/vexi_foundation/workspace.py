"""Phase C protocol plus a small local draft provider for integration proofs.

Not a complete filesystem engine. Existing-file mutations remain UNSUPPORTED.
"""
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path, PureWindowsPath
from typing import Protocol
import hashlib
import os
import stat
from .contracts import Scope, Result, Evidence, ExecutionState as E
from .policy import (Capability, CapabilityPolicy, PermissionRequest, PolicyDecision)


class WorkspaceOperation(str, Enum):
    CREATE = "CREATE"
    SEARCH = "SEARCH"
    LIST = "LIST"
    COPY = "COPY"
    MOVE = "MOVE"
    RENAME = "RENAME"
    TRASH = "TRASH"
    ARCHIVE = "ARCHIVE"
    METADATA = "METADATA"
    WATCH = "WATCH"


@dataclass(frozen=True)
class WorkspacePolicy:
    workspace_id: str
    scope: Scope
    root: Path


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    scope: Scope
    relative_path: str
    document_type: str
    object_refs: tuple[str, ...]
    canonical_version: str | None
    working_revision: str
    content_hash: str
    lifecycle: str = "DRAFT"
    stale: bool = False


@dataclass(frozen=True)
class DocumentCommand:
    permission: PermissionRequest
    operation: WorkspaceOperation
    relative_path: str
    content: bytes = b""


class WorkspaceProtocol(Protocol):
    def execute(self, command: DocumentCommand, now: float,
                approval: str | None = None) -> Result: ...


class WorkspaceResolver:
    """Resolve indexed business references only within an authorized scope."""
    def resolve(self, records: tuple[DocumentRecord, ...], scope: Scope,
                document_type: str, object_ref: str) -> DocumentRecord:
        candidates = [r for r in records if r.scope == scope
                      and r.document_type == document_type and object_ref in r.object_refs]
        if not candidates:
            raise LookupError("not_found")
        if len(candidates) != 1:
            raise ValueError("ambiguous")
        record = candidates[0]
        if record.stale or not record.canonical_version:
            raise ValueError("canonical_unresolved")
        return record


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(policy: WorkspacePolicy, relative: str) -> Path:
    win = PureWindowsPath(relative)
    if (not relative or win.is_absolute() or win.drive or relative.startswith(("/", "\\"))
            or ":" in relative or "\x00" in relative):
        raise ValueError("unsafe_path")
    parts = relative.replace("\\", "/").split("/")
    if any(p in {"", ".", ".."} or p.endswith((" ", "."))
           or PureWindowsPath(p).is_reserved() for p in parts):
        raise ValueError("unsafe_path")
    root = policy.root.absolute()
    # Check ancestors including the configured root for Windows junctions/symlinks.
    for p in (*reversed(root.parents), root):
        _reject_link(p)
    target = root.joinpath(*parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("path_escape")
    for p in (target, *target.parents):
        _reject_link(p)
        if p == root:
            break
    return target


def _reject_link(path: Path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("reparse_point")


class LocalDraftWorkspace:
    """Exclusive-create only; caller provisions a private, owner-controlled root.

    Reparse checks are defense in depth, not a race-proof security boundary against
    a local attacker rewriting parent directories. Such roots are unsupported.
    """
    def __init__(self, workspace: WorkspacePolicy, policy: CapabilityPolicy):
        self.workspace = workspace
        self.policy = policy

    def execute(self, command: DocumentCommand, now: float,
                approval: str | None = None) -> Result:
        req = command.permission
        if req.scope != self.workspace.scope:
            return Result(E.BLOCKED, "scope_mismatch")
        required = (Capability.WORKSPACE_CREATE if command.operation == WorkspaceOperation.CREATE
                    else Capability.WORKSPACE_READ if command.operation in {
                        WorkspaceOperation.METADATA, WorkspaceOperation.LIST, WorkspaceOperation.SEARCH}
                    else Capability.WORKSPACE_MUTATE)
        if (req.capability != required or req.target_ref != command.relative_path
                or req.destination != "LOCAL_STORAGE"
                or req.payload_hash != digest(command.content)):
            return Result(E.BLOCKED, "command_binding")
        decision = self.policy.evaluate(req, now, approval)
        if decision != PolicyDecision.ALLOW:
            return Result(E.BLOCKED, decision.value.lower())
        if command.operation != WorkspaceOperation.CREATE:
            return Result(E.UNSUPPORTED, "provider_operation_unimplemented")
        if req.expected_version != "ABSENT":
            return Result(E.BLOCKED, "create_requires_absent")
        try:
            path = safe_path(self.workspace, command.relative_path)
            if path.suffix.lower() not in {".txt", ".md"}:
                return Result(E.UNSUPPORTED, "draft_format")
            # xb protects an existing file even if it appears after resolution.
            with path.open("xb") as stream:
                stream.write(command.content)
                stream.flush()
                os.fsync(stream.fileno())
            observed = digest(path.read_bytes())
            if observed != req.payload_hash:
                return Result(E.SENT_NOT_CONFIRMED, "readback_mismatch")
            return Result(E.CONFIRMED_SUCCESS, "created_and_readback",
                          Evidence(req.operation_id, req.target_ref, observed, "sha256_readback"))
        except FileExistsError:
            return Result(E.AMBIGUOUS, "target_exists")
        except (ValueError, PermissionError):
            return Result(E.BLOCKED, "unsafe_path_or_access")
        except OSError:
            # No exception repr: it may carry private filenames or payload data.
            return Result(E.FAILED, "local_io_error")
