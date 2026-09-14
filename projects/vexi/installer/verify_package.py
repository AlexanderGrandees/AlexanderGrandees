"""Evidence from an extracted package, without touching installed Vexi or microphone."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

def verify(archive, output):
    output.mkdir(parents=True, exist_ok=True)
    evidence = {"utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
                "zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "checks": [],
                "voice_field": "NOT_RUN", "uac": "NOT_RUN", "real_installation_changed": False}
    with tempfile.TemporaryDirectory(prefix="Vexi проверка с пробелами ") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(archive) as z: z.extractall(root)
        package = next(root.iterdir()); payload = package / "payload"
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
               "LOCALAPPDATA": str(root / "local-app-data")}
        def run(name, argv, cwd=payload, expected=0):
            result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True,
                encoding="utf-8", errors="replace", timeout=600)
            (output / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
            evidence["checks"].append({"check": name, "exit": result.returncode,
                "expected_exit": expected, "status": "PASS" if result.returncode == expected else "FAIL"})
        py = sys.executable
        run("manifest_before", [py, str(package / "install_engine.py"), "--verify-package"])
        files = list(payload.rglob("*.py"))
        for p in files: ast.parse(p.read_text("utf-8-sig"))
        evidence["syntax_files"] = len(files)
        run("full_suite", [py, "-m", "unittest", "discover", "-s", "foundation/tests", "-v"])
        for mode in ("FAST", "CORE", "DOCUMENT", "REGRESSION"):
            run("diagnostics_" + mode, [py, "diagnostics_cli.py", "selftest", "--mode", mode])
        run("docx_smoke", [py, "foundation/smoke_docx_dev3.py"])
        run("diagnostics_failure_exit", [py, "-c",
            "import sys; from unittest.mock import patch; import diagnostics_cli as c; "
            "sys.argv=['diagnostics_cli.py','selftest']; "
            "p=patch.object(c.DiagnosticsManager,'run_selftest',return_value={'status':'FAIL','mode':'FAST','summary':{}}); "
            "p.start(); raise SystemExit(c.main())"], expected=1)
        run("powershell51_package_verify", ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(package / "install.ps1"), "-VerifyOnly"], cwd=package)
        run("runtime_imports", [py, "runtime_check.py", "--imports-only"])
        (payload / "config.json").write_bytes((payload / "config.defaults.json").read_bytes())
        run("runtime_preflight", [py, "runtime_check.py"])
        (payload / "config.json").unlink()
        # Importing the entrypoint can create local runtime directories; verification above
        # already establishes the original extracted payload hashes. No user stores are used.
    evidence["status"] = "PASS" if all(c["status"] == "PASS" for c in evidence["checks"]) else "FAIL"
    (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["status"] == "PASS" else 1

if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("archive", type=Path); ap.add_argument("output", type=Path)
    args=ap.parse_args(); raise SystemExit(verify(args.archive, args.output))
