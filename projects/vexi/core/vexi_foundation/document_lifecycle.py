"""Vexi v0.1.5.dev2 document identity, autosave, versioning and recovery primitives.

Local-first and provider-agnostic. This module does not grant authority and does not
promote a version to canonical truth by itself. Callers must pass the normal policy
and approval gates before invoking mutating methods.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid
from typing import Iterator

from .contracts import Scope
from .integrity import Materiality
from .workspace import DocumentRecord, digest
from .diagnostics import emit_event


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class DocumentLifecycle(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class LifecycleError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class WorkingRevision:
    revision_id: str
    parent_version: str | None
    content_hash: str
    created_at: float
    change_summary: str


@dataclass(frozen=True)
class DocumentVersion:
    version_id: str
    parent_version: str | None
    source_revision: str
    content_hash: str
    created_at: float
    change_summary: str
    materiality: Materiality


@dataclass(frozen=True)
class AuditEvent:
    kind: str
    at: float
    generation: int
    ref: str
    content_hash: str = ""


@dataclass(frozen=True)
class DocumentState:
    record: DocumentRecord
    generation: int
    working: WorkingRevision | None = None
    versions: tuple[DocumentVersion, ...] = ()
    events: tuple[AuditEvent, ...] = ()

    def version(self, version_id: str) -> DocumentVersion:
        for item in self.versions:
            if item.version_id == version_id:
                return item
        raise LifecycleError("version_not_found")


@dataclass(frozen=True)
class CheckpointResult:
    state: DocumentState
    version: DocumentVersion | None
    code: str


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _scope_to_dict(scope: Scope) -> dict[str, str]:
    return {"tenant": scope.tenant, "project": scope.project}


def _record_to_dict(record: DocumentRecord) -> dict[str, object]:
    return {
        "document_id": record.document_id,
        "scope": _scope_to_dict(record.scope),
        "relative_path": record.relative_path,
        "document_type": record.document_type,
        "object_refs": list(record.object_refs),
        "canonical_version": record.canonical_version,
        "working_revision": record.working_revision,
        "content_hash": record.content_hash,
        "lifecycle": record.lifecycle,
        "stale": record.stale,
    }


def _record_from_dict(value: dict[str, object]) -> DocumentRecord:
    scope = value["scope"]
    if not isinstance(scope, dict):
        raise LifecycleError("metadata_schema")
    return DocumentRecord(
        document_id=str(value["document_id"]),
        scope=Scope(str(scope["tenant"]), str(scope["project"])),
        relative_path=str(value["relative_path"]),
        document_type=str(value["document_type"]),
        object_refs=tuple(str(x) for x in value.get("object_refs", [])),
        canonical_version=(None if value.get("canonical_version") is None else str(value["canonical_version"])),
        working_revision=str(value.get("working_revision", "")),
        content_hash=str(value.get("content_hash", "")),
        lifecycle=str(value.get("lifecycle", DocumentLifecycle.DRAFT.value)),
        stale=bool(value.get("stale", False)),
    )


def _state_to_payload(state: DocumentState) -> dict[str, object]:
    return {
        "schema": 1,
        "record": _record_to_dict(state.record),
        "generation": state.generation,
        "working": None if state.working is None else {
            **asdict(state.working),
        },
        "versions": [
            {**asdict(v), "materiality": v.materiality.value}
            for v in state.versions
        ],
        "events": [asdict(e) for e in state.events],
    }


def _state_from_payload(payload: dict[str, object]) -> DocumentState:
    if payload.get("schema") != 1:
        raise LifecycleError("metadata_schema")
    record_raw = payload.get("record")
    if not isinstance(record_raw, dict):
        raise LifecycleError("metadata_schema")
    working_raw = payload.get("working")
    working = None
    if working_raw is not None:
        if not isinstance(working_raw, dict):
            raise LifecycleError("metadata_schema")
        working = WorkingRevision(
            revision_id=str(working_raw["revision_id"]),
            parent_version=None if working_raw.get("parent_version") is None else str(working_raw["parent_version"]),
            content_hash=str(working_raw["content_hash"]),
            created_at=float(working_raw["created_at"]),
            change_summary=str(working_raw.get("change_summary", "")),
        )
    versions_raw = payload.get("versions", [])
    events_raw = payload.get("events", [])
    if not isinstance(versions_raw, list) or not isinstance(events_raw, list):
        raise LifecycleError("metadata_schema")
    versions = tuple(DocumentVersion(
        version_id=str(v["version_id"]),
        parent_version=None if v.get("parent_version") is None else str(v["parent_version"]),
        source_revision=str(v["source_revision"]),
        content_hash=str(v["content_hash"]),
        created_at=float(v["created_at"]),
        change_summary=str(v.get("change_summary", "")),
        materiality=Materiality(str(v["materiality"])),
    ) for v in versions_raw if isinstance(v, dict))
    events = tuple(AuditEvent(
        kind=str(e["kind"]), at=float(e["at"]), generation=int(e["generation"]),
        ref=str(e["ref"]), content_hash=str(e.get("content_hash", ""))
    ) for e in events_raw if isinstance(e, dict))
    return DocumentState(
        record=_record_from_dict(record_raw),
        generation=int(payload["generation"]),
        working=working,
        versions=versions,
        events=events,
    )


class LocalDocumentLifecycleStore:
    """Atomic local metadata + immutable content-addressed blobs.

    Safety model:
    - one explicit store root controlled by the local owner/process;
    - immutable blobs keyed by SHA-256;
    - metadata uses checksum envelopes and atomic os.replace;
    - a per-document exclusive lock prevents two cooperating Vexi processes from
      committing the same generation concurrently;
    - every write also requires expected_generation for optimistic concurrency;
    - a crash can leave an orphan blob or lock but cannot silently promote it.

    A stale lock is never removed automatically. Recovery is an explicit operator
    decision through clear_stale_lock().
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.meta = self.root / "metadata"
        self.blobs = self.root / "blobs"
        self.locks = self.root / "locks"
        for folder in (self.meta, self.blobs, self.locks):
            folder.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_id(document_id: str) -> None:
        if not _ID_RE.fullmatch(document_id):
            raise LifecycleError("invalid_document_id")

    @staticmethod
    def _scope_key(scope: Scope) -> str:
        raw = f"{scope.tenant}\0{scope.project}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:32]

    def _meta_path(self, scope: Scope, document_id: str) -> Path:
        self._validate_id(document_id)
        folder = self.meta / self._scope_key(scope)
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{document_id}.json"

    def _lock_path(self, scope: Scope, document_id: str) -> Path:
        self._validate_id(document_id)
        folder = self.locks / self._scope_key(scope)
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{document_id}.lock"

    def _blob_path(self, scope: Scope, content_hash: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", content_hash):
            raise LifecycleError("invalid_hash")
        folder = self.blobs / self._scope_key(scope) / content_hash[:2]
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{content_hash}.bin"

    @contextmanager
    def _lock(self, scope: Scope, document_id: str) -> Iterator[None]:
        path = self._lock_path(scope, document_id)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise LifecycleError("document_locked") from exc
        try:
            body = _canonical_json({"pid": os.getpid(), "created_at": time.time()})
            os.write(fd, body)
            os.fsync(fd)
            os.close(fd)
            fd = -1
            yield
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def lock_age(self, document_id: str, scope: Scope, now: float | None = None) -> float | None:
        path = self._lock_path(scope, document_id)
        try:
            stat = path.stat()
        except FileNotFoundError:
            return None
        return max(0.0, (time.time() if now is None else now) - stat.st_mtime)

    def clear_stale_lock(self, document_id: str, scope: Scope, *, now: float, stale_after: float) -> bool:
        if stale_after <= 0:
            raise ValueError("stale_after_positive")
        path = self._lock_path(scope, document_id)
        try:
            age = max(0.0, now - path.stat().st_mtime)
        except FileNotFoundError:
            return False
        if age < stale_after:
            raise LifecycleError("lock_not_stale")
        path.unlink()
        return True

    def _put_blob(self, scope: Scope, content: bytes) -> str:
        content_hash = digest(content)
        path = self._blob_path(scope, content_hash)
        if path.exists():
            if digest(path.read_bytes()) != content_hash:
                raise LifecycleError("blob_integrity")
            return content_hash
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if digest(temp.read_bytes()) != content_hash:
                raise LifecycleError("blob_integrity")
            os.replace(temp, path)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
        return content_hash

    def _read_blob(self, scope: Scope, content_hash: str) -> bytes:
        path = self._blob_path(scope, content_hash)
        try:
            content = path.read_bytes()
        except FileNotFoundError as exc:
            raise LifecycleError("blob_missing") from exc
        if digest(content) != content_hash:
            raise LifecycleError("blob_integrity")
        return content

    def _encode_envelope(self, state: DocumentState) -> bytes:
        payload = _state_to_payload(state)
        payload_bytes = _canonical_json(payload)
        envelope = {"payload": payload, "payload_sha256": hashlib.sha256(payload_bytes).hexdigest()}
        return _canonical_json(envelope)

    def _decode_envelope(self, raw: bytes) -> DocumentState:
        try:
            envelope = json.loads(raw.decode("utf-8"))
            payload = envelope["payload"]
            checksum = str(envelope["payload_sha256"])
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise LifecycleError("metadata_corrupt") from exc
        if not isinstance(payload, dict):
            raise LifecycleError("metadata_corrupt")
        observed = hashlib.sha256(_canonical_json(payload)).hexdigest()
        if observed != checksum:
            raise LifecycleError("metadata_integrity")
        try:
            return _state_from_payload(payload)
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, LifecycleError):
                raise
            raise LifecycleError("metadata_schema") from exc

    def _write_new(self, state: DocumentState) -> None:
        path = self._meta_path(state.record.scope, state.record.document_id)
        raw = self._encode_envelope(state)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise LifecycleError("document_exists") from exc
        try:
            os.write(fd, raw)
            os.fsync(fd)
        finally:
            os.close(fd)

    def _replace(self, state: DocumentState) -> None:
        path = self._meta_path(state.record.scope, state.record.document_id)
        raw = self._encode_envelope(state)
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass

    def register(self, record: DocumentRecord, *, initial_content: bytes | None = None,
                 now: float | None = None) -> DocumentState:
        self._validate_id(record.document_id)
        if record.canonical_version is not None:
            raise LifecycleError("register_canonical_must_be_none")
        if record.lifecycle not in {x.value for x in DocumentLifecycle}:
            raise LifecycleError("invalid_lifecycle")
        at = time.time() if now is None else now
        working = None
        normalized = record
        if initial_content is not None:
            observed = self._put_blob(record.scope, initial_content)
            if record.content_hash and record.content_hash != observed:
                raise LifecycleError("initial_hash_mismatch")
            working = WorkingRevision("w000001", None, observed, at, "initial")
            normalized = replace(record, working_revision=working.revision_id, content_hash=observed)
        elif record.content_hash:
            raise LifecycleError("content_without_blob")
        state = DocumentState(
            record=normalized,
            generation=1,
            working=working,
            events=(AuditEvent("REGISTER", at, 1, record.document_id,
                               "" if working is None else working.content_hash),),
        )
        with self._lock(record.scope, record.document_id):
            self._write_new(state)
        emit_event("document_registered", component="document_lifecycle", document_id=record.document_id,
                   generation=state.generation, revision_id=(working.revision_id if working else "none"),
                   content_hash=(working.content_hash if working else "0"*64),
                   lifecycle=state.record.lifecycle, stale=state.record.stale)
        return state

    def load(self, document_id: str, scope: Scope) -> DocumentState:
        path = self._meta_path(scope, document_id)
        try:
            state = self._decode_envelope(path.read_bytes())
        except FileNotFoundError as exc:
            raise LifecycleError("document_not_found") from exc
        if state.record.document_id != document_id or state.record.scope != scope:
            raise LifecycleError("metadata_identity")
        return state

    def _load_for_update(self, document_id: str, scope: Scope,
                         expected_generation: int) -> DocumentState:
        state = self.load(document_id, scope)
        if state.generation != expected_generation:
            raise LifecycleError("generation_conflict")
        return state

    @staticmethod
    def _event(state: DocumentState, kind: str, at: float, ref: str,
               content_hash: str = "") -> tuple[AuditEvent, ...]:
        return state.events + (AuditEvent(kind, at, state.generation + 1, ref, content_hash),)

    def autosave(self, document_id: str, scope: Scope, *, content: bytes,
                 expected_generation: int, change_summary: str = "",
                 now: float | None = None) -> DocumentState:
        at = time.time() if now is None else now
        with self._lock(scope, document_id):
            state = self._load_for_update(document_id, scope, expected_generation)
            content_hash = self._put_blob(scope, content)
            if state.working is not None and state.working.content_hash == content_hash:
                return state
            revision_id = f"w{state.generation + 1:06d}"
            working = WorkingRevision(revision_id, state.record.canonical_version,
                                      content_hash, at, change_summary)
            new_state = replace(
                state,
                record=replace(state.record, working_revision=revision_id,
                               content_hash=content_hash),
                generation=state.generation + 1,
                working=working,
                events=self._event(state, "AUTOSAVE", at, revision_id, content_hash),
            )
            self._replace(new_state)
            emit_event("document_autosave", component="document_lifecycle", document_id=document_id,
                       generation=new_state.generation, revision_id=revision_id, content_hash=content_hash,
                       lifecycle=new_state.record.lifecycle, stale=new_state.record.stale)
            return new_state

    def checkpoint(self, document_id: str, scope: Scope, *, expected_generation: int,
                   materiality: Materiality, change_summary: str,
                   now: float | None = None) -> CheckpointResult:
        at = time.time() if now is None else now
        with self._lock(scope, document_id):
            state = self._load_for_update(document_id, scope, expected_generation)
            if state.working is None:
                raise LifecycleError("working_revision_required")
            if materiality == Materiality.IDENTICAL:
                return CheckpointResult(state, None, "identical_no_version")
            if materiality == Materiality.COSMETIC:
                return CheckpointResult(state, None, "cosmetic_kept_working")
            if state.versions and state.versions[-1].content_hash == state.working.content_hash:
                return CheckpointResult(state, None, "content_already_versioned")
            version_id = f"v{len(state.versions) + 1:06d}"
            version = DocumentVersion(
                version_id=version_id,
                parent_version=state.record.canonical_version,
                source_revision=state.working.revision_id,
                content_hash=state.working.content_hash,
                created_at=at,
                change_summary=change_summary,
                materiality=materiality,
            )
            new_state = replace(
                state,
                generation=state.generation + 1,
                versions=state.versions + (version,),
                events=self._event(state, "CHECKPOINT", at, version_id, version.content_hash),
            )
            self._replace(new_state)
            emit_event("document_checkpoint", component="document_lifecycle", document_id=document_id,
                       generation=new_state.generation, version_id=version.version_id,
                       content_hash=version.content_hash, materiality=materiality.value)
            return CheckpointResult(new_state, version, "version_created")

    def promote_canonical(self, document_id: str, scope: Scope, *, version_id: str,
                          expected_canonical: str | None, expected_generation: int,
                          now: float | None = None) -> DocumentState:
        at = time.time() if now is None else now
        with self._lock(scope, document_id):
            state = self._load_for_update(document_id, scope, expected_generation)
            if state.record.canonical_version != expected_canonical:
                raise LifecycleError("canonical_conflict")
            version = state.version(version_id)
            if state.record.stale and version.version_id == state.record.canonical_version:
                raise LifecycleError("stale_requires_revalidation")
            if state.working is None or version.source_revision != state.working.revision_id \
                    or version.content_hash != state.working.content_hash:
                raise LifecycleError("canonical_requires_current_checkpoint")
            new_state = replace(
                state,
                record=replace(state.record, canonical_version=version.version_id,
                               content_hash=version.content_hash, stale=False),
                generation=state.generation + 1,
                events=self._event(state, "PROMOTE_CANONICAL", at, version.version_id,
                                   version.content_hash),
            )
            self._replace(new_state)
            emit_event("canonical_promoted", component="document_lifecycle", document_id=document_id,
                       generation=new_state.generation, version_id=version.version_id,
                       content_hash=version.content_hash, stale=False)
            return new_state

    def restore_as_working(self, document_id: str, scope: Scope, *, version_id: str,
                           expected_generation: int, change_summary: str = "rollback",
                           now: float | None = None) -> DocumentState:
        at = time.time() if now is None else now
        with self._lock(scope, document_id):
            state = self._load_for_update(document_id, scope, expected_generation)
            version = state.version(version_id)
            # Verify the immutable blob before making it the working revision.
            self._read_blob(scope, version.content_hash)
            revision_id = f"w{state.generation + 1:06d}"
            working = WorkingRevision(revision_id, state.record.canonical_version,
                                      version.content_hash, at, change_summary)
            new_state = replace(
                state,
                record=replace(state.record, working_revision=revision_id,
                               content_hash=version.content_hash),
                generation=state.generation + 1,
                working=working,
                events=self._event(state, "RESTORE_WORKING", at, version.version_id,
                                   version.content_hash),
            )
            self._replace(new_state)
            emit_event("document_restored", component="document_lifecycle", document_id=document_id,
                       generation=new_state.generation, version_id=version.version_id,
                       revision_id=revision_id, content_hash=version.content_hash, rollback=True)
            return new_state

    def mark_stale(self, document_id: str, scope: Scope, *, expected_generation: int,
                   reason_ref: str, now: float | None = None) -> DocumentState:
        at = time.time() if now is None else now
        with self._lock(scope, document_id):
            state = self._load_for_update(document_id, scope, expected_generation)
            if state.record.stale:
                return state
            new_state = replace(
                state,
                record=replace(state.record, stale=True),
                generation=state.generation + 1,
                events=self._event(state, "MARK_STALE", at, reason_ref),
            )
            self._replace(new_state)
            emit_event("document_marked_stale", component="document_lifecycle", document_id=document_id,
                       generation=new_state.generation, stale=True, reason_code="source_changed")
            return new_state

    def transition_lifecycle(self, document_id: str, scope: Scope, *,
                             target: DocumentLifecycle, expected_generation: int,
                             now: float | None = None) -> DocumentState:
        allowed = {
            DocumentLifecycle.DRAFT: {DocumentLifecycle.REVIEW, DocumentLifecycle.ARCHIVED},
            DocumentLifecycle.REVIEW: {DocumentLifecycle.DRAFT, DocumentLifecycle.APPROVED,
                                       DocumentLifecycle.ARCHIVED},
            DocumentLifecycle.APPROVED: {DocumentLifecycle.REVIEW, DocumentLifecycle.ACTIVE,
                                         DocumentLifecycle.ARCHIVED},
            DocumentLifecycle.ACTIVE: {DocumentLifecycle.REVIEW, DocumentLifecycle.ARCHIVED},
            DocumentLifecycle.ARCHIVED: {DocumentLifecycle.DRAFT},
        }
        at = time.time() if now is None else now
        with self._lock(scope, document_id):
            state = self._load_for_update(document_id, scope, expected_generation)
            try:
                current = DocumentLifecycle(state.record.lifecycle)
            except ValueError as exc:
                raise LifecycleError("invalid_lifecycle") from exc
            if target == current:
                return state
            if target not in allowed[current]:
                raise LifecycleError("invalid_lifecycle_transition")
            if target in {DocumentLifecycle.APPROVED, DocumentLifecycle.ACTIVE}:
                if state.record.canonical_version is None or state.record.stale:
                    raise LifecycleError("canonical_required")
            new_state = replace(
                state,
                record=replace(state.record, lifecycle=target.value),
                generation=state.generation + 1,
                events=self._event(state, "LIFECYCLE", at, target.value),
            )
            self._replace(new_state)
            emit_event("document_lifecycle_changed", component="document_lifecycle", document_id=document_id,
                       generation=new_state.generation, lifecycle=target.value, stale=new_state.record.stale)
            return new_state

    def read_working(self, document_id: str, scope: Scope) -> bytes:
        state = self.load(document_id, scope)
        if state.working is None:
            raise LifecycleError("working_revision_required")
        return self._read_blob(scope, state.working.content_hash)

    def read_version(self, document_id: str, scope: Scope, version_id: str) -> bytes:
        state = self.load(document_id, scope)
        return self._read_blob(scope, state.version(version_id).content_hash)

    def verify(self, document_id: str, scope: Scope) -> DocumentState:
        state = self.load(document_id, scope)
        if state.working is not None:
            self._read_blob(scope, state.working.content_hash)
        for version in state.versions:
            self._read_blob(scope, version.content_hash)
        if state.working is not None and state.working.content_hash != state.record.content_hash:
            raise LifecycleError("working_hash_mismatch")
        if state.record.canonical_version is not None:
            version = state.version(state.record.canonical_version)
            self._read_blob(scope, version.content_hash)
        return state

    def list_orphan_blobs(self, scope: Scope) -> tuple[str, ...]:
        referenced: set[str] = set()
        meta_root = self.meta / self._scope_key(scope)
        for path in meta_root.glob("*.json"):
            try:
                state = self._decode_envelope(path.read_bytes())
            except LifecycleError:
                continue
            if state.record.scope != scope:
                continue
            if state.working is not None:
                referenced.add(state.working.content_hash)
            referenced.update(v.content_hash for v in state.versions)
        blob_root = self.blobs / self._scope_key(scope)
        found = {p.stem for p in blob_root.glob("*/*.bin") if re.fullmatch(r"[0-9a-f]{64}", p.stem)}
        return tuple(sorted(found - referenced))
