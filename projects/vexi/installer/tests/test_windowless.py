"""Reproduce Torch download failure in actual pythonw, using only synthetic local bytes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CORE = Path(__file__).resolve().parents[2] / "core"


class WindowlessDownloadTests(unittest.TestCase):
    def run_download(self, bootstrap):
        with tempfile.TemporaryDirectory(prefix="Vexi windowless ") as directory:
            root = Path(directory)
            script = root / "probe.py"
            result = root / "result.json"
            script.write_text('''import sys, json
from pathlib import Path
root = Path(__file__).resolve().parent
missing_stderr = sys.stderr is None
sys.path.insert(0, sys.argv[1])
if sys.argv[2] == "fixed":
    from runtime_bootstrap import ensure_standard_streams
    ensure_standard_streams()
try:
    import torch.hub
    source = root / "synthetic.bin"
    source.write_bytes(b"synthetic model fixture" * 100)
    target = root / "download.bin"
    torch.hub.download_url_to_file(source.as_uri(), str(target))
    value = {"status":"PASS", "exact_bytes":target.read_bytes() == source.read_bytes()}
except Exception as exc:
    value = {"status":"FAIL", "error_type":type(exc).__name__}
value["started_without_stderr"] = missing_stderr
(root / "result.json").write_text(json.dumps(value))
''', encoding="utf-8")
            child = subprocess.run([str(Path(sys.executable).with_name("pythonw.exe")), str(script),
                str(CORE), "fixed" if bootstrap else "broken"], timeout=60)
            self.assertEqual(child.returncode, 0)
            return json.loads(result.read_text())

    def test_unfixed_pythonw_reproduces_torch_download_failure(self):
        value = self.run_download(False)
        self.assertTrue(value["started_without_stderr"])
        self.assertEqual(value["error_type"], "AttributeError")

    def test_fixed_pythonw_download_preserves_exact_bytes(self):
        value = self.run_download(True)
        self.assertTrue(value["started_without_stderr"])
        self.assertEqual(value["status"], "PASS")
        self.assertTrue(value["exact_bytes"])
