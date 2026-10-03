"""Vexi v0.1.5.dev3 headless DOCX field/text provider with hybrid approval.

This module is deliberately narrow:
- no Microsoft Office dependency;
- no arbitrary XML or shell operations;
- exact text/field replacement only;
- no structural table/section/image mutation yet;
- low-risk automatic mutation is allowed only for trusted-schema fields;
- every applied mutation creates/ensures a pre-edit recovery checkpoint;
- business-material/high-risk/unknown edits require an external trusted approval verifier.

The model must never be allowed to set ``trusted_schema=True`` or install the
approval verifier. Those are trusted-runtime inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import PurePosixPath
from typing import Callable
import copy
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET

from .contracts import Scope
from .integrity import Materiality
from .diagnostics import emit_event
from .document_lifecycle import (
    DocumentState,
    LifecycleError,
    LocalDocumentLifecycleStore,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_NS = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("w", W_NS)
ET.register_namespace("r", R_NS)

_W = "{%s}" % W_NS
_REL = "{%s}" % REL_NS


class DocxError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class StoryScope(str, Enum):
    MAIN = "MAIN"
    HEADERS = "HEADERS"
    FOOTERS = "FOOTERS"
    ALL = "ALL"


class FieldKind(str, Enum):
    # AUTO only when trusted_schema=True.
    COSMETIC_TEXT = "COSMETIC_TEXT"
    NON_MATERIAL_TEXT = "NON_MATERIAL_TEXT"

    # Confirmation required in this release.
    GENERAL_TEXT = "GENERAL_TEXT"
    PERSON_NAME = "PERSON_NAME"
    COMPANY_NAME = "COMPANY_NAME"
    ADDRESS = "ADDRESS"
    DATE = "DATE"
    AMOUNT = "AMOUNT"
    QUANTITY = "QUANTITY"
    PAYMENT_TERM = "PAYMENT_TERM"
    BANK_DETAILS = "BANK_DETAILS"
    CONTRACT_CLAUSE = "CONTRACT_CLAUSE"
    SIGNATURE = "SIGNATURE"
    UNKNOWN = "UNKNOWN"


class ApprovalRequirement(str, Enum):
    AUTO_WITH_RECOVERY = "AUTO_WITH_RECOVERY"
    OWNER_CONFIRMATION = "OWNER_CONFIRMATION"


@dataclass(frozen=True)
class DocxLimits:
    max_package_bytes: int = 32 * 1024 * 1024
    max_members: int = 2048
    max_total_uncompressed: int = 128 * 1024 * 1024
    max_xml_part_bytes: int = 16 * 1024 * 1024
    max_compression_ratio: float = 250.0


@dataclass(frozen=True)
class ReplaceTextCommand:
    old_text: str
    new_text: str
    expected_occurrences: int
    field_kind: FieldKind = FieldKind.UNKNOWN
    story_scope: StoryScope = StoryScope.MAIN
    change_summary: str = ""

    def __post_init__(self):
        if not self.old_text:
            raise ValueError("old_text_required")
        if self.old_text == self.new_text:
            raise ValueError("replacement_must_change")
        if self.expected_occurrences <= 0:
            raise ValueError("expected_occurrences_positive")
        for value in (self.old_text, self.new_text):
            if any(ord(ch) < 0x20 for ch in value):
                raise ValueError("control_char_unsupported")


@dataclass(frozen=True)
class ParagraphTarget:
    part: str
    paragraph_index: int
    occurrences: int
    before_hash: str
    after_hash: str


@dataclass(frozen=True)
class DocxInspection:
    package_hash: str
    story_parts: tuple[str, ...]
    paragraph_count: int
    table_count: int
    external_relationships: int
    signed: bool
    macro_enabled: bool
    tracked_changes: bool


@dataclass(frozen=True)
class DocxEditPlan:
    source_hash: str
    command_hash: str
    fingerprint: str
    occurrence_count: int
    targets: tuple[ParagraphTarget, ...]
    materiality: Materiality
    approval: ApprovalRequirement


@dataclass(frozen=True)
class DocxEditResult:
    code: str
    plan: DocxEditPlan
    state: DocumentState | None
    approval_fingerprint: str
    post_version_id: str | None = None


ApprovalVerifier = Callable[[str, str], bool]
SchemaTrustResolver = Callable[[str, Scope, ReplaceTextCommand], bool]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _safe_zip_name(name: str) -> bool:
    if not name or "\x00" in name or "\\" in name or name.startswith("/"):
        return False
    p = PurePosixPath(name)
    if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        return False
    if ":" in p.parts[0]:
        return False
    return True


def _story_parts(names: set[str], scope: StoryScope) -> tuple[str, ...]:
    result: list[str] = []
    if scope in (StoryScope.MAIN, StoryScope.ALL) and "word/document.xml" in names:
        result.append("word/document.xml")
    if scope in (StoryScope.HEADERS, StoryScope.ALL):
        result.extend(sorted(n for n in names if re.fullmatch(r"word/header\d+\.xml", n)))
    if scope in (StoryScope.FOOTERS, StoryScope.ALL):
        result.extend(sorted(n for n in names if re.fullmatch(r"word/footer\d+\.xml", n)))
    return tuple(result)


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.iter(_W + "t"))


def _contains_field_code(paragraph: ET.Element) -> bool:
    return any(node.tag in {_W + "fldChar", _W + "instrText"} for node in paragraph.iter())


def _contains_tracked_change(root: ET.Element) -> bool:
    return any(node.tag in {_W + "ins", _W + "del", _W + "moveFrom", _W + "moveTo"} for node in root.iter())


def _replace_in_paragraph(paragraph: ET.Element, old: str, new: str) -> tuple[int, str]:
    nodes = list(paragraph.iter(_W + "t"))
    values = [node.text or "" for node in nodes]
    combined = "".join(values)
    starts: list[int] = []
    pos = 0
    while True:
        idx = combined.find(old, pos)
        if idx < 0:
            break
        starts.append(idx)
        pos = idx + len(old)
    if not starts:
        return 0, combined

    # Character span for every w:t in original text.
    spans: list[tuple[int, int]] = []
    cursor = 0
    for value in values:
        spans.append((cursor, cursor + len(value)))
        cursor += len(value)

    for start in reversed(starts):
        end = start + len(old)
        affected = [i for i, (a, b) in enumerate(spans) if b > start and a < end]
        if not affected:
            raise DocxError("replacement_mapping")
        first, last = affected[0], affected[-1]
        first_a, _ = spans[first]
        last_a, _ = spans[last]
        first_text = nodes[first].text or ""
        last_text = nodes[last].text or ""
        start_off = start - first_a
        end_off = end - last_a
        if first == last:
            nodes[first].text = first_text[:start_off] + new + first_text[end_off:]
        else:
            prefix = first_text[:start_off]
            suffix = last_text[end_off:]
            nodes[first].text = prefix + new
            for i in affected[1:-1]:
                nodes[i].text = ""
            nodes[last].text = suffix
        for i in affected:
            text = nodes[i].text or ""
            if text[:1].isspace() or text[-1:].isspace():
                nodes[i].set("{%s}space" % XML_NS, "preserve")
    return len(starts), _paragraph_text(paragraph)


class HeadlessDocxProvider:
    def __init__(self, limits: DocxLimits | None = None):
        self.limits = limits or DocxLimits()

    def _read_package(self, source: bytes) -> tuple[list[zipfile.ZipInfo], dict[str, bytes]]:
        if len(source) > self.limits.max_package_bytes:
            raise DocxError("package_too_large")
        if not zipfile.is_zipfile(BytesIO(source)):
            raise DocxError("not_docx_zip")
        try:
            zf = zipfile.ZipFile(BytesIO(source), "r")
        except zipfile.BadZipFile as exc:
            raise DocxError("bad_zip") from exc
        with zf:
            infos = zf.infolist()
            if len(infos) > self.limits.max_members:
                raise DocxError("too_many_members")
            names = [i.filename for i in infos]
            if len(set(names)) != len(names):
                raise DocxError("duplicate_member")
            if any(not _safe_zip_name(name) for name in names):
                raise DocxError("unsafe_member_path")
            total = 0
            data: dict[str, bytes] = {}
            for info in infos:
                if info.flag_bits & 0x1:
                    raise DocxError("encrypted_member")
                total += info.file_size
                if total > self.limits.max_total_uncompressed:
                    raise DocxError("uncompressed_limit")
                if info.filename.endswith(".xml") and info.file_size > self.limits.max_xml_part_bytes:
                    raise DocxError("xml_part_too_large")
                if info.file_size > 1024 * 1024:
                    ratio = info.file_size / max(1, info.compress_size)
                    if ratio > self.limits.max_compression_ratio:
                        raise DocxError("compression_ratio")
                try:
                    data[info.filename] = zf.read(info)
                except (RuntimeError, zipfile.BadZipFile, OSError) as exc:
                    raise DocxError("member_read_failed") from exc
        required = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
        if not required.issubset(data):
            raise DocxError("required_part_missing")
        macro = any(n.lower().endswith("vbaproject.bin") or n.lower().endswith("vbadata.xml") for n in data)
        signed = any(n.lower().startswith("_xmlsignatures/") for n in data)
        if macro:
            raise DocxError("macro_enabled_unsupported")
        if signed:
            raise DocxError("signed_document_unsupported")
        return infos, data

    @staticmethod
    def _parse_xml(raw: bytes) -> ET.Element:
        head = raw[:4096].upper()
        if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
            raise DocxError("dtd_entity_unsupported")
        try:
            return ET.fromstring(raw)
        except ET.ParseError as exc:
            raise DocxError("xml_parse") from exc

    def inspect(self, source: bytes) -> DocxInspection:
        _, data = self._read_package(source)
        names = set(data)
        parts = _story_parts(names, StoryScope.ALL)
        paragraph_count = table_count = 0
        tracked = False
        for part in parts:
            root = self._parse_xml(data[part])
            paragraph_count += sum(1 for _ in root.iter(_W + "p"))
            table_count += sum(1 for _ in root.iter(_W + "tbl"))
            tracked = tracked or _contains_tracked_change(root)
        external = 0
        for name, raw in data.items():
            if name.endswith(".rels"):
                root = self._parse_xml(raw)
                external += sum(1 for rel in root.iter(_REL + "Relationship")
                                if rel.attrib.get("TargetMode") == "External")
        return DocxInspection(
            package_hash=_sha(source), story_parts=parts,
            paragraph_count=paragraph_count, table_count=table_count,
            external_relationships=external, signed=False, macro_enabled=False,
            tracked_changes=tracked,
        )

    @staticmethod
    def classify(field_kind: FieldKind, *, trusted_schema: bool) -> tuple[Materiality, ApprovalRequirement]:
        if trusted_schema and field_kind == FieldKind.COSMETIC_TEXT:
            return Materiality.COSMETIC, ApprovalRequirement.AUTO_WITH_RECOVERY
        if trusted_schema and field_kind == FieldKind.NON_MATERIAL_TEXT:
            return Materiality.CONTENT, ApprovalRequirement.AUTO_WITH_RECOVERY
        if field_kind in {FieldKind.BANK_DETAILS, FieldKind.CONTRACT_CLAUSE, FieldKind.SIGNATURE}:
            return Materiality.HIGH_RISK, ApprovalRequirement.OWNER_CONFIRMATION
        if field_kind in {FieldKind.PERSON_NAME, FieldKind.COMPANY_NAME, FieldKind.ADDRESS,
                          FieldKind.DATE, FieldKind.AMOUNT, FieldKind.QUANTITY,
                          FieldKind.PAYMENT_TERM}:
            return Materiality.BUSINESS_MATERIAL, ApprovalRequirement.OWNER_CONFIRMATION
        if field_kind == FieldKind.GENERAL_TEXT:
            return Materiality.CONTENT, ApprovalRequirement.OWNER_CONFIRMATION
        return Materiality.UNKNOWN, ApprovalRequirement.OWNER_CONFIRMATION

    def plan(self, source: bytes, command: ReplaceTextCommand, *, trusted_schema: bool = False) -> DocxEditPlan:
        _, data = self._read_package(source)
        names = set(data)
        parts = _story_parts(names, command.story_scope)
        if not parts:
            raise DocxError("story_part_missing")
        targets: list[ParagraphTarget] = []
        total = 0
        for part in parts:
            root = self._parse_xml(data[part])
            if _contains_tracked_change(root):
                raise DocxError("tracked_changes_unsupported")
            for idx, paragraph in enumerate(root.iter(_W + "p")):
                before = _paragraph_text(paragraph)
                count = before.count(command.old_text)
                if not count:
                    continue
                if _contains_field_code(paragraph):
                    raise DocxError("word_field_unsupported")
                # Calculate predicted result without persisting XML.
                clone = ET.fromstring(ET.tostring(paragraph, encoding="utf-8"))
                replaced, after = _replace_in_paragraph(clone, command.old_text, command.new_text)
                if replaced != count:
                    raise DocxError("replacement_count_internal")
                total += count
                targets.append(ParagraphTarget(part, idx, count,
                                               _sha(before.encode("utf-8")),
                                               _sha(after.encode("utf-8"))))
        if total != command.expected_occurrences:
            raise DocxError("occurrence_mismatch")
        materiality, approval = self.classify(command.field_kind, trusted_schema=trusted_schema)
        cmd = {
            "old_sha": _sha(command.old_text.encode("utf-8")),
            "new_sha": _sha(command.new_text.encode("utf-8")),
            "expected_occurrences": command.expected_occurrences,
            "field_kind": command.field_kind.value,
            "story_scope": command.story_scope.value,
        }
        command_hash = _sha(_canon(cmd))
        fp = _sha(_canon({
            "source": _sha(source), "command": command_hash,
            "targets": [t.__dict__ for t in targets],
            "materiality": materiality.value, "approval": approval.value,
        }))
        return DocxEditPlan(_sha(source), command_hash, fp, total, tuple(targets), materiality, approval)

    def apply(self, source: bytes, command: ReplaceTextCommand, plan: DocxEditPlan, *, trusted_schema: bool = False) -> bytes:
        fresh = self.plan(source, command, trusted_schema=trusted_schema)
        if fresh != plan:
            raise DocxError("plan_stale")
        infos, data = self._read_package(source)
        targeted = {t.part for t in plan.targets}
        for part in targeted:
            root = self._parse_xml(data[part])
            paragraphs = list(root.iter(_W + "p"))
            target_map = {t.paragraph_index: t for t in plan.targets if t.part == part}
            for idx, target in target_map.items():
                if idx >= len(paragraphs):
                    raise DocxError("paragraph_moved")
                paragraph = paragraphs[idx]
                before = _paragraph_text(paragraph)
                if _sha(before.encode("utf-8")) != target.before_hash:
                    raise DocxError("paragraph_changed")
                count, after = _replace_in_paragraph(paragraph, command.old_text, command.new_text)
                if count != target.occurrences or _sha(after.encode("utf-8")) != target.after_hash:
                    raise DocxError("replacement_verify_prewrite")
            data[part] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        out = BytesIO()
        with zipfile.ZipFile(out, "w") as zf:
            for info in infos:
                cloned = copy.copy(info)
                # zipfile recalculates CRC/sizes. Preserve method and metadata.
                zf.writestr(cloned, data[info.filename])
        result = out.getvalue()
        if result == source:
            raise DocxError("mutation_no_effect")

        # Re-open and verify exact targeted paragraph hashes.
        _, verify_data = self._read_package(result)
        for part in targeted:
            root = self._parse_xml(verify_data[part])
            paragraphs = list(root.iter(_W + "p"))
            for target in (t for t in plan.targets if t.part == part):
                if target.paragraph_index >= len(paragraphs):
                    raise DocxError("postwrite_paragraph_missing")
                text = _paragraph_text(paragraphs[target.paragraph_index])
                if _sha(text.encode("utf-8")) != target.after_hash:
                    raise DocxError("postwrite_readback_mismatch")
        return result


class HybridDocxEditController:
    """Connects the headless provider to dev2 lifecycle/recovery.

    The controller mutates the lifecycle working blob, not an arbitrary filesystem
    path. Export/sync to a user-visible workspace file is a separate provider.
    """
    def __init__(self, store: LocalDocumentLifecycleStore,
                 provider: HeadlessDocxProvider | None = None,
                 approval_verifier: ApprovalVerifier | None = None,
                 schema_trust_resolver: SchemaTrustResolver | None = None):
        self.store = store
        self.provider = provider or HeadlessDocxProvider()
        self.approval_verifier = approval_verifier
        # Installed by trusted orchestration / Template Registry adapter. Never model-controlled.
        self.schema_trust_resolver = schema_trust_resolver

    @staticmethod
    def _approval_fingerprint(document_id: str, scope: Scope, generation: int,
                              plan: DocxEditPlan) -> str:
        return _sha(_canon({
            "document_id": document_id,
            "tenant": scope.tenant,
            "project": scope.project,
            "generation": generation,
            "plan": plan.fingerprint,
        }))

    def execute(self, document_id: str, scope: Scope, command: ReplaceTextCommand, *,
                expected_generation: int, approval_token: str | None = None,
                now: float | None = None) -> DocxEditResult:
        state = self.store.load(document_id, scope)
        if state.generation != expected_generation:
            raise LifecycleError("generation_conflict")
        if state.record.stale:
            raise DocxError("stale_document")
        if state.record.document_type.upper() != "DOCX":
            raise DocxError("document_type_not_docx")

        trusted_schema = False
        if self.schema_trust_resolver is not None:
            try:
                trusted_schema = bool(self.schema_trust_resolver(document_id, scope, command))
            except Exception as exc:
                raise DocxError("schema_trust_resolution_failed") from exc

        source = self.store.read_working(document_id, scope)
        plan = self.provider.plan(source, command, trusted_schema=trusted_schema)
        approval_fp = self._approval_fingerprint(document_id, scope, expected_generation, plan)
        emit_event("docx_edit_planned", component="headless_docx", document_id=document_id,
                   generation=expected_generation, materiality=plan.materiality.value,
                   approval=plan.approval.value, field_kind=command.field_kind.value,
                   story_scope=command.story_scope.value, occurrences=plan.occurrence_count,
                   source_hash=plan.source_hash)
        if plan.approval == ApprovalRequirement.OWNER_CONFIRMATION:
            if not approval_token or self.approval_verifier is None:
                emit_event("docx_edit_waiting_approval", component="headless_docx", document_id=document_id,
                           generation=expected_generation, materiality=plan.materiality.value,
                           approval=plan.approval.value, state="AWAITING_APPROVAL")
                return DocxEditResult("awaiting_approval", plan, None, approval_fp)
            if not self.approval_verifier(approval_token, approval_fp):
                raise DocxError("approval_invalid")

        # Ensure exact current working content is recoverable before mutation.
        recovery = self.store.checkpoint(
            document_id, scope, expected_generation=state.generation,
            materiality=Materiality.UNKNOWN,
            change_summary="pre-docx-edit recovery checkpoint", now=now)
        state = recovery.state
        recovery_version_id = None if recovery.version is None else recovery.version.version_id
        if recovery_version_id is None:
            # Current bytes were already versioned; choose the newest matching immutable version.
            matches = [v.version_id for v in state.versions if v.content_hash == plan.source_hash]
            if not matches:
                raise DocxError("recovery_checkpoint_missing")
            recovery_version_id = matches[-1]

        # Re-read after checkpoint. Bytes should be identical, but this verifies blob integrity.
        source = self.store.read_working(document_id, scope)
        if _sha(source) != plan.source_hash:
            raise DocxError("source_changed_after_checkpoint")
        output = self.provider.apply(source, command, plan, trusted_schema=trusted_schema)

        mutated = False
        try:
            state = self.store.autosave(
                document_id, scope, content=output, expected_generation=state.generation,
                change_summary=command.change_summary or "docx exact replacement", now=now)
            mutated = True
            readback = self.store.read_working(document_id, scope)
            if readback != output:
                raise DocxError("lifecycle_readback_mismatch")
            # Re-open and validate the new DOCX package after lifecycle persistence.
            self.provider.inspect(readback)

            post_version_id = None
            if plan.approval == ApprovalRequirement.OWNER_CONFIRMATION:
                post = self.store.checkpoint(
                    document_id, scope, expected_generation=state.generation,
                    materiality=plan.materiality,
                    change_summary=command.change_summary or "approved docx edit", now=now)
                state = post.state
                post_version_id = None if post.version is None else post.version.version_id
            emit_event("docx_edit_verified", component="headless_docx", document_id=document_id,
                       generation=state.generation, materiality=plan.materiality.value,
                       approval=plan.approval.value, state="CONFIRMED_SUCCESS",
                       recovery=True, rollback=False, result_hash=state.record.content_hash)
            return DocxEditResult("confirmed_success", plan, state, approval_fp, post_version_id)
        except Exception as exc:
            if mutated:
                try:
                    latest = self.store.load(document_id, scope)
                    self.store.restore_as_working(
                        document_id, scope, version_id=recovery_version_id,
                        expected_generation=latest.generation,
                        change_summary="automatic recovery after failed docx verification", now=now)
                except Exception as recovery_exc:
                    emit_event("docx_recovery_failed", component="headless_docx", incident=True, severity="CRITICAL",
                               document_id=document_id, generation=latest.generation, state="FAILED",
                               recovery=False, rollback=False, error_type=type(recovery_exc).__name__)
                    raise DocxError("edit_failed_recovery_failed") from recovery_exc
                emit_event("docx_edit_recovered", component="headless_docx", incident=True, severity="ERROR",
                           document_id=document_id, generation=latest.generation, state="RECOVERED",
                           recovery=True, rollback=True, error_type=type(exc).__name__)
                raise DocxError("edit_failed_recovered") from exc
            raise
