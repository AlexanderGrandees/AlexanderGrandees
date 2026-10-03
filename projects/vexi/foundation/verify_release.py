"""Rehearse whole-module release and rollback in a NEW isolated output directory."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def hashes(root):
    return {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


def run(argv, cwd, stdin=None):
    result = subprocess.run(argv, cwd=cwd, input=stdin, capture_output=True,
                            encoding="utf-8", timeout=60,
                            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="rehearsal-", dir=output)).resolve()
    current, backup, stage, rejected = (root / n for n in ("current", "backup", "stage", "candidate-tested"))
    for p in (current, backup, stage, rejected):
        if not p.resolve().is_relative_to(root): raise ValueError("outside_rehearsal")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "logs", "config.json")
    shutil.copytree(args.baseline.resolve(), current / "core", ignore=ignore)
    before = hashes(current)
    # Preserve an untouched baseline before replacing a coherent directory.
    current.rename(backup)
    shutil.copytree(project / "core", stage / "core", ignore=ignore)
    shutil.copytree(project / "foundation" / "tests", stage / "foundation" / "tests", ignore=ignore)
    stage.rename(current)
    report = {"utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
              "baseline_hashes": before, "candidate_hashes": hashes(current),
              "field_voice": "NOT_RUN", "field_browser": "NOT_RUN"}
    try:
        files = list(current.rglob("*.py"))
        for path in files: ast.parse(path.read_text(encoding="utf-8-sig"))
        report["syntax"] = {"status": "PASS", "files": len(files)}
        report["regression_014"] = run([sys.executable, "regression_tests_v014.py"], current / "core")
        report["regression_015"] = run([sys.executable, "-m", "unittest", "discover", "-s", "foundation/tests", "-v"], current)
        if any(report[k]["exit_code"] for k in ("regression_014", "regression_015")):
            raise RuntimeError("regression_failed")
        workspace = root / "synthetic-documents"
        report["launch_owner_text"] = run([sys.executable, "foundation_console.py", "--owner-console",
            "--workspace", str(workspace)], current / "core", "создай черновик proof.txt: synthetic release proof\nexit\n")
        report["launch_guest_text"] = run([sys.executable, "foundation_console.py", "--workspace", str(workspace)],
            current / "core", "создай черновик denied.txt: synthetic guest proof\nexit\n")
        report["local_text_e2e"] = {"owner_file_verified": (workspace / "proof.txt").read_bytes() == b"synthetic release proof",
                                    "guest_file_absent": not (workspace / "denied.txt").exists()}
        if not all(report["local_text_e2e"].values()): raise RuntimeError("e2e_failed")
        if report["launch_owner_text"]["exit_code"] or report["launch_guest_text"]["exit_code"]:
            raise RuntimeError("launch_failed")
    except Exception as exc:
        report["failure"] = type(exc).__name__
    finally:
        current.rename(rejected)
        backup.rename(current)
        report["rollback"] = {"baseline_hashes_match": hashes(current) == before,
                              "candidate_retained": True}
        (output / "evidence.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"evidence": str(output / "evidence.json"), "failure": report.get("failure"),
                      "rollback": report["rollback"], "text_e2e": report.get("local_text_e2e")}, ensure_ascii=False))
    return 1 if report.get("failure") or not report["rollback"]["baseline_hashes_match"] else 0


if __name__ == "__main__": raise SystemExit(main())
