"""Vexi v0.1.5.dev4 safe diagnostics, self-test and export bundle.

Privacy contract:
- no transcripts, prompts, document bodies, secrets, tokens, paths or exception messages;
- only allow-listed structured metadata is persisted;
- arbitrary logging records are ignored by the diagnostics handler;
- DEEP mode adds safe metadata density, never raw payload capture;
- exports contain only managed diagnostic files and a SHA-256 manifest.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import platform
import re
import sys
import threading
import time
import unittest
import zipfile
from typing import Iterable


_SCHEMA = 1
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$")
_FORBIDDEN_KEYS = {
    "text", "transcript", "content", "body", "prompt", "response", "secret",
    "token", "password", "email", "message", "path", "filename", "file_path",
    "old_text", "new_text", "payload", "document_body", "exception", "traceback",
    "stack", "args", "kwargs", "memory", "query", "utterance", "recognized_text",
}
_SAFE_KEYS = {
    "state", "code", "decision", "attention_class", "capability", "risk_class",
    "operation_id", "task_id", "document_id", "workspace_id", "generation",
    "version_id", "revision_id", "content_hash", "source_hash", "result_hash",
    "materiality", "approval", "field_kind", "story_scope", "occurrences",
    "duration_ms", "count", "size_bytes", "mode", "test_id", "error_type",
    "lifecycle", "stale", "verified", "channel", "build", "version",
    "recovery", "rollback", "scope_hash", "target_hash", "bundle_hash",
    "tests_run", "failures", "errors", "skipped", "status", "phase",
    "provider", "component_version", "deep", "reason_code",
}


class DiagnosticsError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class SelfTestMode(str, Enum):
    FAST = "FAST"
    CORE = "CORE"
    DOCUMENT = "DOCUMENT"
    REGRESSION = "REGRESSION"


@dataclass(frozen=True)
class DiagnosticsStatus:
    root: str
    runtime_files: int
    incident_files: int
    total_bytes: int
    last_selftest_status: str
    last_selftest_mode: str
    deep_mode: bool
    latest_export: str


def _utc_iso(ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(time.time() if ts is None else ts, timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _stamp(ts: float | None = None) -> str:
    dt = datetime.fromtimestamp(time.time() if ts is None else ts, timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}-{threading.get_ident()}")
    with tmp.open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def default_diagnostics_root() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "Vexi" / "Diagnostics"
    return Path.home() / ".vexi" / "diagnostics"


def _safe_token(value: object, *, key: str) -> object:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise DiagnosticsError("unsafe_metadata_value")
        return round(value, 3)
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, str):
        if key.endswith("_hash"):
            if not re.fullmatch(r"[0-9a-f]{16,64}", value.lower()):
                raise DiagnosticsError("unsafe_hash")
            return value.lower()
        if key in {"operation_id", "task_id", "document_id", "workspace_id", "version_id", "revision_id", "test_id"}:
            if _SAFE_TOKEN.fullmatch(value):
                return value
            return "sha256:" + _sha(value.encode("utf-8"))[:24]
        if not _SAFE_TOKEN.fullmatch(value):
            raise DiagnosticsError("unsafe_metadata_value")
        return value
    raise DiagnosticsError("unsafe_metadata_type")


def _clean_metadata(metadata: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in metadata.items():
        k = str(key).lower()
        if k in _FORBIDDEN_KEYS or any(word in k for word in ("secret", "token", "password", "transcript", "prompt", "payload")):
            raise DiagnosticsError("forbidden_metadata_key")
        if k not in _SAFE_KEYS:
            raise DiagnosticsError("metadata_key_not_allowed")
        out[k] = _safe_token(value, key=k)
    return out


class DiagnosticsManager:
    def __init__(self, root: Path | None = None, *, retention_days: int = 7,
                 max_log_bytes: int = 200 * 1024 * 1024, segment_bytes: int = 5 * 1024 * 1024):
        self.root = Path(root or default_diagnostics_root())
        self.runtime_dir = self.root / "runtime"
        self.incident_dir = self.root / "incidents"
        self.selftest_dir = self.root / "selftests"
        self.state_dir = self.root / "state"
        self.exports_dir = self.root / "exports"
        self.retention_days = int(retention_days)
        self.max_log_bytes = int(max_log_bytes)
        self.segment_bytes = int(segment_bytes)
        self._write_lock = threading.RLock()
        self.ensure()

    def ensure(self) -> None:
        for folder in (self.runtime_dir, self.incident_dir, self.selftest_dir, self.state_dir, self.exports_dir):
            folder.mkdir(parents=True, exist_ok=True)

    def _segment(self, kind: str, now: float | None = None) -> Path:
        ts = time.time() if now is None else now
        day = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
        folder = self.incident_dir if kind == "incident" else self.runtime_dir
        prefix = "incidents" if kind == "incident" else "runtime"
        base = folder / f"{prefix}-{day}-p{os.getpid()}.jsonl"
        if not base.exists() or base.stat().st_size < self.segment_bytes:
            return base
        for i in range(1, 1000):
            candidate = folder / f"{prefix}-{day}-p{os.getpid()}-{i}.jsonl"
            if not candidate.exists() or candidate.stat().st_size < self.segment_bytes:
                return candidate
        raise DiagnosticsError("segment_exhausted")

    def emit(self, event: str, *, component: str = "runtime", severity: str = "INFO",
             incident: bool = False, now: float | None = None, **metadata: object) -> dict[str, object]:
        if not _SAFE_TOKEN.fullmatch(event) or not _SAFE_TOKEN.fullmatch(component):
            raise DiagnosticsError("unsafe_event_name")
        severity = severity.upper()
        if severity not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise DiagnosticsError("unsafe_severity")
        clean = _clean_metadata(metadata)
        record = {
            "schema": _SCHEMA,
            "ts": _utc_iso(now),
            "severity": severity,
            "component": component,
            "event": event,
            "meta": clean,
        }
        raw = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        with self._write_lock:
            path = self._segment("incident" if incident else "runtime", now)
            with path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(raw)
                stream.flush()
                if incident:
                    os.fsync(stream.fileno())
        return record

    def incident(self, event: str, *, component: str = "runtime", severity: str = "ERROR", **metadata: object) -> dict[str, object]:
        return self.emit(event, component=component, severity=severity, incident=True, **metadata)

    def write_environment(self, *, version: str, channel: str, build: str,
                          modules: Iterable[str] = ()) -> Path:
        safe_modules = []
        for module in modules:
            if _SAFE_TOKEN.fullmatch(str(module)):
                safe_modules.append(str(module))
        value = {
            "schema": _SCHEMA,
            "captured_at": _utc_iso(),
            "vexi": {"version": str(version), "channel": str(channel), "build": str(build)},
            "python": {"version": platform.python_version(), "implementation": platform.python_implementation()},
            "os": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
            "modules": sorted(set(safe_modules)),
        }
        path = self.state_dir / "environment.json"
        _atomic_json(path, value)
        return path

    def _deep_path(self) -> Path:
        return self.state_dir / "deep_mode.json"

    def set_deep_mode(self, enabled: bool, *, minutes: int = 60) -> bool:
        if enabled:
            minutes = max(1, min(int(minutes), 240))
            _atomic_json(self._deep_path(), {"schema": _SCHEMA, "expires_at": time.time() + minutes * 60})
        else:
            self._deep_path().unlink(missing_ok=True)
        self.emit("deep_mode_changed", component="diagnostics", mode="DEEP" if enabled else "SAFE", deep=enabled)
        return enabled

    def deep_mode_active(self, *, now: float | None = None) -> bool:
        path = self._deep_path()
        if not path.exists():
            return False
        try:
            raw = json.loads(path.read_text("utf-8"))
            active = float(raw.get("expires_at", 0)) > (time.time() if now is None else now)
        except Exception:
            active = False
        if not active:
            path.unlink(missing_ok=True)
        return active

    def enforce_retention(self, *, now: float | None = None) -> dict[str, int]:
        current = time.time() if now is None else now
        cutoff = current - self.retention_days * 86400
        deleted = 0
        managed = list(self.runtime_dir.glob("*.jsonl")) + list(self.incident_dir.glob("*.jsonl"))
        for path in managed:
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(); deleted += 1
            except FileNotFoundError:
                pass
        managed = [p for p in list(self.runtime_dir.glob("*.jsonl")) + list(self.incident_dir.glob("*.jsonl")) if p.exists()]
        total = sum(p.stat().st_size for p in managed)
        if total > self.max_log_bytes:
            for path in sorted(managed, key=lambda p: p.stat().st_mtime):
                if total <= self.max_log_bytes:
                    break
                size = path.stat().st_size
                path.unlink(missing_ok=True)
                total -= size; deleted += 1
        return {"deleted": deleted, "bytes": max(total, 0)}

    def _write_selftest(self, result: dict[str, object]) -> Path:
        history = self.selftest_dir / f"selftest-{_stamp()}.json"
        _atomic_json(history, result)
        _atomic_json(self.state_dir / "selftest-latest.json", result)
        return history

    def _fast_selftest(self) -> dict[str, object]:
        checks: list[dict[str, str]] = []
        def check(name: str, fn) -> None:
            try:
                fn(); checks.append({"id": name, "state": "PASS"})
            except Exception as exc:
                checks.append({"id": name, "state": "FAIL", "error_type": type(exc).__name__})

        def writable():
            p = self.state_dir / ".selftest-write"
            # Windows _commit/fsync requires a writable descriptor.
            with p.open("wb") as stream:
                stream.write(b"synthetic")
                stream.flush()
                os.fsync(stream.fileno())
            p.unlink(missing_ok=True)
        def redaction():
            try:
                _clean_metadata({"text": "synthetic"})
            except DiagnosticsError as exc:
                if exc.code == "forbidden_metadata_key": return
            raise AssertionError("redaction_gate")
        def safe_meta():
            cleaned = _clean_metadata({"state": "READY", "generation": 1})
            if cleaned != {"state": "READY", "generation": 1}: raise AssertionError("safe_meta")
        def deep_state():
            before = self.deep_mode_active(); self.set_deep_mode(True, minutes=1)
            if not self.deep_mode_active(): raise AssertionError("deep_on")
            self.set_deep_mode(before, minutes=1) if before else self.set_deep_mode(False)
        for name, fn in (("diagnostics_root_writable", writable), ("raw_text_rejected", redaction),
                         ("safe_metadata_roundtrip", safe_meta), ("deep_mode_state", deep_state)):
            check(name, fn)
        failed = sum(c["state"] != "PASS" for c in checks)
        return {"tests": checks, "run": len(checks), "failures": failed, "errors": 0, "skipped": 0,
                "status": "PASS" if failed == 0 else "FAIL"}

    def _suite_selftest(self, mode: SelfTestMode, project_root: Path) -> dict[str, object]:
        test_dir = project_root / "foundation" / "tests"
        if not test_dir.exists():
            return {"tests": [], "run": 0, "failures": 0, "errors": 0, "skipped": 0, "status": "NOT_RUN"}
        patterns = {
            SelfTestMode.CORE: ("test_foundation.py", "test_recovery.py", "test_speech_input.py"),
            SelfTestMode.DOCUMENT: ("test_document_lifecycle.py", "test_docx_runtime.py", "test_diagnostics.py"),
            SelfTestMode.REGRESSION: ("test_foundation.py", "test_recovery.py", "test_document_lifecycle.py", "test_docx_runtime.py", "test_diagnostics.py", "test_dev4_patcher.py", "test_speech_input.py"),
        }[mode]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        runtime_root = project_root / "core" if (project_root / "core").is_dir() else project_root
        if str(runtime_root) not in sys.path:
            sys.path.insert(0, str(runtime_root))
        suites = []
        loader = unittest.TestLoader()
        for pattern in patterns:
            suites.append(loader.discover(str(test_dir), pattern=pattern))
        suite = unittest.TestSuite(suites)

        class Result(unittest.TestResult):
            def __init__(self):
                super().__init__(); self.rows: list[dict[str, str]] = []
            def addSuccess(self, test):
                super().addSuccess(test); self.rows.append({"id": test.id(), "state": "PASS"})
            def addFailure(self, test, err):
                super().addFailure(test, err); self.rows.append({"id": test.id(), "state": "FAIL", "error_type": err[0].__name__})
            def addError(self, test, err):
                super().addError(test, err); self.rows.append({"id": test.id(), "state": "ERROR", "error_type": err[0].__name__})
            def addSkip(self, test, reason):
                super().addSkip(test, reason); self.rows.append({"id": test.id(), "state": "SKIP"})

        result = Result(); suite.run(result)
        status = "PASS" if result.testsRun and not result.failures and not result.errors else ("NOT_RUN" if not result.testsRun else "FAIL")
        return {"tests": result.rows, "run": result.testsRun, "failures": len(result.failures),
                "errors": len(result.errors), "skipped": len(result.skipped), "status": status}

    def run_selftest(self, mode: SelfTestMode | str = SelfTestMode.FAST, *, project_root: Path | None = None) -> dict[str, object]:
        mode = SelfTestMode(str(mode)) if not isinstance(mode, SelfTestMode) else mode
        started = time.time()
        payload = self._fast_selftest() if mode == SelfTestMode.FAST else self._suite_selftest(mode, Path(project_root or Path.cwd()))
        result = {
            "schema": _SCHEMA,
            "mode": mode.value,
            "started_at": _utc_iso(started),
            "finished_at": _utc_iso(),
            "status": payload["status"],
            "summary": {k: payload[k] for k in ("run", "failures", "errors", "skipped")},
            "tests": payload["tests"],
        }
        self._write_selftest(result)
        self.emit("selftest_finished", component="diagnostics", mode=mode.value, status=str(payload["status"]),
                  tests_run=int(payload["run"]), failures=int(payload["failures"]),
                  errors=int(payload["errors"]), skipped=int(payload["skipped"]))
        if payload["status"] == "FAIL":
            self.incident("selftest_failed", component="diagnostics", mode=mode.value,
                          failures=int(payload["failures"]), errors=int(payload["errors"]))
        return result

    def recent_files(self, limit: int = 30) -> list[dict[str, object]]:
        rows = []
        for kind, folder, pattern in (("runtime", self.runtime_dir, "*.jsonl"),
                                      ("incident", self.incident_dir, "*.jsonl"),
                                      ("selftest", self.selftest_dir, "*.json"),
                                      ("export", self.exports_dir, "*.zip")):
            for path in folder.glob(pattern):
                try:
                    st = path.stat()
                except FileNotFoundError:
                    continue
                rows.append({"kind": kind, "name": path.name, "size": st.st_size, "mtime": st.st_mtime})
        rows.sort(key=lambda x: float(x["mtime"]), reverse=True)
        return rows[:max(1, int(limit))]

    def status(self) -> DiagnosticsStatus:
        runtime = list(self.runtime_dir.glob("*.jsonl")); incidents = list(self.incident_dir.glob("*.jsonl"))
        total = sum(p.stat().st_size for p in runtime + incidents if p.exists())
        latest = self.state_dir / "selftest-latest.json"
        test_status = test_mode = "NEVER"
        if latest.exists():
            try:
                value = json.loads(latest.read_text("utf-8")); test_status = str(value.get("status", "UNKNOWN")); test_mode = str(value.get("mode", "UNKNOWN"))
            except Exception:
                test_status = "CORRUPT"; test_mode = "UNKNOWN"
        exports = sorted(self.exports_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        return DiagnosticsStatus(str(self.root), len(runtime), len(incidents), total, test_status, test_mode,
                                 self.deep_mode_active(), exports[0].name if exports else "")

    def export_bundle(self, *, version: str, channel: str = "development", build: str = "unknown",
                      max_bundle_input_bytes: int = 40 * 1024 * 1024) -> tuple[Path, str]:
        self.enforce_retention()
        self.write_environment(version=version, channel=channel, build=build,
                               modules=("diagnostics", "selftest", "safe-logging"))
        candidates: list[tuple[str, Path]] = []
        for prefix, folder, pattern in (("runtime", self.runtime_dir, "*.jsonl"),
                                        ("incidents", self.incident_dir, "*.jsonl"),
                                        ("selftests", self.selftest_dir, "*.json")):
            for path in folder.glob(pattern):
                candidates.append((f"{prefix}/{path.name}", path))
        for name in ("environment.json", "selftest-latest.json"):
            path = self.state_dir / name
            if path.exists(): candidates.append((f"state/{name}", path))
        candidates.sort(key=lambda item: item[1].stat().st_mtime, reverse=True)
        chosen: list[tuple[str, Path]] = []
        used = 0
        for arc, path in candidates:
            size = path.stat().st_size
            if used + size <= max_bundle_input_bytes:
                chosen.append((arc, path)); used += size
        summary = {
            "schema": _SCHEMA, "created_at": _utc_iso(), "version": version, "channel": channel,
            "build": build, "deep_mode": self.deep_mode_active(), "input_bytes": used,
            "files": len(chosen), "privacy": "metadata-only; no raw transcripts/document bodies/secrets by contract",
        }
        manifest: dict[str, dict[str, object]] = {}
        safe_version = re.sub(r"[^A-Za-z0-9._-]+", "_", str(version))[:64] or "unknown"
        output = self.exports_dir / f"Vexi_Diagnostics_{safe_version}_{_stamp()}.zip"
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            summary_raw = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            zf.writestr("bundle_summary.json", summary_raw)
            manifest["bundle_summary.json"] = {"sha256": _sha(summary_raw), "size": len(summary_raw)}
            for arc, path in chosen:
                raw = path.read_bytes()
                zf.writestr(arc, raw)
                manifest[arc] = {"sha256": _sha(raw), "size": len(raw)}
            manifest_raw = json.dumps({"schema": _SCHEMA, "files": manifest}, indent=2, sort_keys=True).encode("utf-8")
            zf.writestr("manifest.json", manifest_raw)
        bundle_hash = _sha(output.read_bytes())
        self.emit("diagnostic_bundle_created", component="diagnostics", size_bytes=output.stat().st_size,
                  bundle_hash=bundle_hash, version=version, channel=channel)
        return output, bundle_hash

    def clear_runtime_logs(self, *, keep_incidents: bool = True) -> int:
        deleted = 0
        for path in self.runtime_dir.glob("*.jsonl"):
            path.unlink(missing_ok=True); deleted += 1
        if not keep_incidents:
            for path in self.incident_dir.glob("*.jsonl"):
                path.unlink(missing_ok=True); deleted += 1
        return deleted


class SafeDiagnosticsHandler(logging.Handler):
    """Accept only structured diagnostics or the three legacy foundation templates."""
    FOUNDATION = {
        "ATTENTION class=%s decision=%s code=%s": ("attention", ("attention_class", "decision", "code")),
        "EXECUTION state=%s code=%s": ("execution", ("state", "code")),
        "RUNTIME event=%s": ("runtime", ("state",)),
    }
    def __init__(self, manager: DiagnosticsManager):
        super().__init__(level=logging.INFO); self.manager = manager
    def emit(self, record: logging.LogRecord) -> None:
        try:
            structured = getattr(record, "vexi_diag", None)
            if isinstance(structured, dict):
                event = structured.get("event"); component = structured.get("component", "runtime")
                metadata = structured.get("meta", {})
                if isinstance(event, str) and isinstance(component, str) and isinstance(metadata, dict):
                    self.manager.emit(event, component=component, severity=record.levelname, **metadata)
                return
            if record.name == "vexi.foundation" and record.msg in self.FOUNDATION:
                event, keys = self.FOUNDATION[record.msg]
                args = tuple(record.args) if isinstance(record.args, tuple) else (record.args,)
                if len(args) == len(keys):
                    self.manager.emit(event, component="foundation", severity=record.levelname,
                                      **dict(zip(keys, args)))
        except Exception:
            # Diagnostics must never crash the assistant or recursively log errors.
            return


_DEFAULT: DiagnosticsManager | None = None
_HOOKS_INSTALLED = False


def get_default_manager() -> DiagnosticsManager | None:
    return _DEFAULT


def emit_event(event: str, *, component: str, incident: bool = False, severity: str = "INFO", **metadata: object) -> None:
    manager = _DEFAULT
    if manager is None:
        return
    try:
        manager.emit(event, component=component, incident=incident, severity=severity, **metadata)
    except Exception:
        return


def install_default_diagnostics(*, version: str, channel: str, build: str,
                                root: Path | None = None, project_root: Path | None = None) -> DiagnosticsManager:
    global _DEFAULT, _HOOKS_INSTALLED
    if _DEFAULT is None:
        _DEFAULT = DiagnosticsManager(root)
        logging.getLogger().addHandler(SafeDiagnosticsHandler(_DEFAULT))
    manager = _DEFAULT
    manager.enforce_retention()
    manager.write_environment(version=version, channel=channel, build=build,
                              modules=("foundation", "document-lifecycle", "headless-docx", "diagnostics"))
    manager.emit("runtime_start", component="runtime", version=version, channel=channel, build=build,
                 mode="SAFE", deep=manager.deep_mode_active())
    if not _HOOKS_INSTALLED:
        original_sys = sys.excepthook
        def sys_hook(exc_type, exc, tb):
            try: manager.incident("unhandled_exception", component="runtime", error_type=exc_type.__name__)
            finally: original_sys(exc_type, exc, tb)
        sys.excepthook = sys_hook
        if hasattr(threading, "excepthook"):
            original_thread = threading.excepthook
            def thread_hook(args):
                try: manager.incident("thread_exception", component="runtime", error_type=args.exc_type.__name__)
                finally: original_thread(args)
            threading.excepthook = thread_hook
        _HOOKS_INSTALLED = True
    return manager
