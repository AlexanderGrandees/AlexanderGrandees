# Shared imports work in both source (core/) and installed flat layouts.
import sys as _sys
from pathlib import Path as _Path
_root = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_root / "core" if (_root / "core").is_dir() else _root))
import json
import logging
from pathlib import Path
import tempfile
import time
import unittest
import zipfile

from vexi_foundation.diagnostics import (
    DiagnosticsError, DiagnosticsManager, SafeDiagnosticsHandler, SelfTestMode,
)


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manager = DiagnosticsManager(self.root, retention_days=7, max_log_bytes=1024 * 1024, segment_bytes=4096)
    def tearDown(self): self.tmp.cleanup()

    def lines(self, folder):
        rows=[]
        for p in folder.glob("*.jsonl"):
            rows.extend(json.loads(x) for x in p.read_text("utf-8").splitlines() if x.strip())
        return rows

    def test_safe_event_written(self):
        self.manager.emit("ready", component="runtime", state="READY", generation=1)
        row=self.lines(self.manager.runtime_dir)[0]
        self.assertEqual(row["event"], "ready"); self.assertEqual(row["meta"]["generation"], 1)

    def test_raw_text_key_rejected_without_persistence(self):
        with self.assertRaisesRegex(DiagnosticsError, "forbidden_metadata_key"):
            self.manager.emit("heard", component="runtime", text="private sentence")
        self.assertEqual(self.lines(self.manager.runtime_dir), [])

    def test_path_key_rejected(self):
        with self.assertRaises(DiagnosticsError):
            self.manager.emit("file", component="runtime", path="C:/Users/Alice/private.docx")

    def test_unsafe_identifier_is_pseudonymized(self):
        row=self.manager.emit("doc", component="runtime", document_id="Customer John Doe contract")
        self.assertTrue(row["meta"]["document_id"].startswith("sha256:"))
        self.assertNotIn("John", json.dumps(row))

    def test_incident_goes_to_incident_stream(self):
        self.manager.incident("recovery_failed", component="docx", error_type="DocxError")
        self.assertEqual(len(self.lines(self.manager.incident_dir)), 1)
        self.assertEqual(len(self.lines(self.manager.runtime_dir)), 0)

    def test_freeform_python_logging_is_ignored(self):
        logger=logging.getLogger("unsafe.test"); handler=SafeDiagnosticsHandler(self.manager); logger.addHandler(handler); logger.setLevel(logging.INFO)
        try: logger.info("PRIVATE %s", "secret-body")
        finally: logger.removeHandler(handler)
        self.assertEqual(self.lines(self.manager.runtime_dir), [])

    def test_foundation_templates_are_translated(self):
        logger=logging.getLogger("vexi.foundation"); handler=SafeDiagnosticsHandler(self.manager); logger.addHandler(handler); logger.setLevel(logging.INFO)
        try: logger.info("EXECUTION state=%s code=%s", "CONFIRMED_SUCCESS", "created_and_readback")
        finally: logger.removeHandler(handler)
        row=self.lines(self.manager.runtime_dir)[0]
        self.assertEqual(row["event"], "execution"); self.assertEqual(row["meta"]["state"], "CONFIRMED_SUCCESS")

    def test_deep_mode_expires(self):
        self.manager.set_deep_mode(True, minutes=1); self.assertTrue(self.manager.deep_mode_active())
        path=self.manager.state_dir/"deep_mode.json"; value=json.loads(path.read_text("utf-8")); value["expires_at"]=time.time()-1; path.write_text(json.dumps(value), encoding="utf-8")
        self.assertFalse(self.manager.deep_mode_active()); self.assertFalse(path.exists())

    def test_environment_contains_no_home_or_username(self):
        path=self.manager.write_environment(version="0.1.5.dev4", channel="development", build="synthetic", modules=("diagnostics",))
        raw=path.read_text("utf-8")
        self.assertNotIn(str(Path.home()), raw); self.assertNotIn("cwd", raw.lower())

    def test_fast_selftest_passes(self):
        result=self.manager.run_selftest(SelfTestMode.FAST)
        self.assertEqual(result["status"], "PASS"); self.assertGreaterEqual(result["summary"]["run"], 4)

    def test_missing_suite_is_not_run(self):
        result=self.manager.run_selftest(SelfTestMode.CORE, project_root=self.root/"missing")
        self.assertEqual(result["status"], "NOT_RUN")

    def test_export_manifest_matches_files(self):
        self.manager.emit("ready", component="runtime", state="READY")
        self.manager.run_selftest(SelfTestMode.FAST)
        path, sha=self.manager.export_bundle(version="0.1.5.dev4", build="synthetic")
        self.assertEqual(sha, __import__("hashlib").sha256(path.read_bytes()).hexdigest())
        with zipfile.ZipFile(path) as z:
            manifest=json.loads(z.read("manifest.json")); self.assertIn("bundle_summary.json", manifest["files"])
            for name, meta in manifest["files"].items():
                raw=z.read(name); self.assertEqual(meta["sha256"], __import__("hashlib").sha256(raw).hexdigest())

    def test_export_does_not_recursively_include_exports(self):
        first,_=self.manager.export_bundle(version="0.1.5.dev4", build="synthetic")
        second,_=self.manager.export_bundle(version="0.1.5.dev4", build="synthetic")
        with zipfile.ZipFile(second) as z:
            self.assertFalse(any(name.startswith("exports/") or name.endswith(first.name) for name in z.namelist()))

    def test_retention_removes_old_log_but_not_exports(self):
        self.manager.emit("old", component="runtime", state="READY", now=time.time()-10*86400)
        old=next(self.manager.runtime_dir.glob("*.jsonl")); old_time=time.time()-10*86400; __import__("os").utime(old,(old_time,old_time))
        exp=self.manager.exports_dir/"keep.zip"; exp.write_bytes(b"x"); __import__("os").utime(exp,(old_time,old_time))
        self.manager.enforce_retention(); self.assertFalse(old.exists()); self.assertTrue(exp.exists())

    def test_status_reports_last_selftest_and_export(self):
        self.manager.run_selftest(SelfTestMode.FAST); path,_=self.manager.export_bundle(version="0.1.5.dev4", build="synthetic")
        status=self.manager.status(); self.assertEqual(status.last_selftest_status,"PASS"); self.assertEqual(status.latest_export,path.name)

    def test_document_lifecycle_emits_metadata_only_event(self):
        import vexi_foundation.diagnostics as diag
        from vexi_foundation.contracts import Scope
        from vexi_foundation.workspace import DocumentRecord
        from vexi_foundation.document_lifecycle import LocalDocumentLifecycleStore
        previous=diag._DEFAULT; diag._DEFAULT=self.manager
        try:
            scope=Scope("tenant-a","project-a")
            store=LocalDocumentLifecycleStore(self.root/"doc-state")
            record=DocumentRecord("doc-1",scope,"synthetic.docx","DOCX",(),None,"","")
            store.register(record,initial_content=b"synthetic",now=1.0)
        finally:
            diag._DEFAULT=previous
        raw="\n".join(p.read_text("utf-8") for p in self.manager.runtime_dir.glob("*.jsonl"))
        self.assertIn("document_registered",raw)
        self.assertNotIn("synthetic.docx",raw)
        self.assertNotIn('"synthetic"',raw)


if __name__ == "__main__": unittest.main()
