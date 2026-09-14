import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

INSTALLER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSTALLER))
from install_engine import Installer, InstallError, verify_payload, validate_target, acquire_lock


class InstallerTests(unittest.TestCase):
    def test_lock_excludes_concurrent_install_and_releases_on_close(self):
        first = acquire_lock(self.target)
        try:
            with self.assertRaises(InstallError): acquire_lock(self.target)
        finally: first.close()
        acquire_lock(self.target).close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="vexi install ")
        self.root = Path(self.tmp.name)
        self.payload = self.root / "payload"
        self.payload.mkdir()
        for name, content in {"vexi.py": "# new runtime", "version.py": "# dev4",
                              "config.defaults.json": '{"version":"0.1.5.dev4"}'}.items():
            (self.payload / name).write_text(content, encoding="utf-8")
        self.manifest()
        self.target = self.root / "Vexi"

    def tearDown(self): self.tmp.cleanup()

    def manifest(self):
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.payload.iterdir() if p.name != "payload-manifest.json"}
        (self.payload / "payload-manifest.json").write_text(json.dumps({"files": files}), encoding="utf-8")

    def instance(self): return Installer(self.payload, self.target, self.root / "installer.log")

    def old(self):
        self.target.mkdir()
        (self.target / "vexi.py").write_text("# old")
        (self.target / "version.py").write_text("# 0.1.4")
        (self.target / "config.json").write_text('{"custom_preference":"preserved"}')
        (self.target / "models").mkdir()
        (self.target / "models" / "synthetic").write_bytes(b"model-fixture")

    def test_clean_install_does_not_require_C_Vexi(self):
        i = self.instance(); self.assertEqual(i.mode, "CLEAN_INSTALL")
        i.stage_payload(); i.swap(lambda root: None)
        self.assertEqual((self.target / "vexi.py").read_text(), "# new runtime")

    def test_upgrade_preserves_settings_and_models(self):
        self.old(); i = self.instance(); i.stage_payload(); i.swap(lambda root: None)
        self.assertEqual(json.loads((self.target / "config.json").read_text())["custom_preference"], "preserved")
        self.assertEqual((self.target / "models/synthetic").read_bytes(), b"model-fixture")
        self.assertEqual((i.backup / "vexi.py").read_text(), "# old")

    def test_staging_failure_never_stops_or_changes_old_runtime(self):
        self.old(); i = self.instance(); i.stage_payload()
        stopped = []
        def fail(root): raise InstallError("TEST_FAILURE")
        with self.assertRaises(InstallError): i.swap(fail, stop=lambda: stopped.append(True))
        self.assertEqual(stopped, [])
        self.assertEqual((self.target / "vexi.py").read_text(), "# old")

    def test_rollback_restores_exact_old_files(self):
        self.old()
        before = {p.relative_to(self.target).as_posix(): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}
        i = self.instance(); i.stage_payload(); i.swap(lambda root: None); i.rollback()
        after = {p.relative_to(self.target).as_posix(): p.read_bytes() for p in self.target.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertTrue(i.failed.exists())

    def test_clean_rollback_preserves_failed_candidate_without_fake_old(self):
        i = self.instance(); i.stage_payload(); i.swap(lambda root: None); i.rollback()
        self.assertFalse(self.target.exists()); self.assertTrue(i.failed.exists())

    def test_tampered_payload_rejected_before_staging(self):
        (self.payload / "vexi.py").write_text("changed")
        i = self.instance()
        with self.assertRaisesRegex(InstallError, "HASH_MISMATCH"): i.stage_payload()
        self.assertFalse(i.stage.exists()); self.assertFalse(self.target.exists())

    def test_unknown_payload_file_rejected(self):
        (self.payload / "extra.py").write_text("unexpected")
        with self.assertRaisesRegex(InstallError, "UNEXPECTED"): verify_payload(self.payload)

    def test_manifest_escape_rejected(self):
        (self.payload / "payload-manifest.json").write_text(json.dumps({"files": {"../outside": "bad"}}))
        with self.assertRaisesRegex(InstallError, "MANIFEST_PATH"): verify_payload(self.payload)

    def test_unrelated_target_and_root_are_rejected(self):
        self.target.mkdir(); (self.target / "private.txt").write_text("synthetic")
        with self.assertRaisesRegex(InstallError, "UNRELATED"): self.instance()
        with self.assertRaisesRegex(InstallError, "INVALID_TARGET"): validate_target(Path(self.root.anchor))

    def test_swap_failure_restores_old_directory(self):
        self.old(); i = self.instance(); i.stage_payload()
        original = Path.rename
        def rename(path, target):
            if path == i.stage: raise OSError("synthetic locked candidate")
            return original(path, target)
        with patch.object(Path, "rename", rename), self.assertRaises(OSError): i.swap(lambda root: None)
        self.assertEqual((self.target / "vexi.py").read_text(), "# old")


class PowerShellTests(unittest.TestCase):
    def test_real_windows_powershell_51_parser(self):
        if sys.platform != "win32": self.skipTest("Windows-only evidence")
        command = "$allErrors=@(); Get-ChildItem -LiteralPath $env:VEXI_SCRIPT_ROOT -Filter *.ps1 | ForEach-Object { $tokens=$null; $parseErrors=$null; [System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$parseErrors) | Out-Null; $allErrors+=@($parseErrors) }; if ($allErrors.Count) { $allErrors; exit 1 }; $PSVersionTable.PSVersion.ToString()"
        import os
        result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
            env={**os.environ, "VEXI_SCRIPT_ROOT": str(INSTALLER)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("5.1", result.stdout)


if __name__ == "__main__": unittest.main(verbosity=2)
