"""Run only against the disposable clean-install fixture, including real Windows renames."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

package = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()
output = Path(sys.argv[3]).resolve()
if target.name != "Vexi" or target.parent.name != "Vexi_FIX7_Test":
    raise SystemExit("Disposable Vexi_FIX7_Test/Vexi fixture required")
output.mkdir(parents=True, exist_ok=True)
env = {**os.environ, "LOCALAPPDATA": str(target.parent / "isolated-appdata"),
       "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}

def fingerprint():
    h = hashlib.sha256(); count = 0
    for p in sorted(target.rglob("*")):
        if p.is_file():
            count += 1
            h.update(p.relative_to(target).as_posix().encode("utf-8") + b"\0")
            fh = hashlib.sha256()
            with p.open("rb") as f:
                for block in iter(lambda: f.read(1024 * 1024), b""): fh.update(block)
            h.update(fh.digest())
    return {"sha256": h.hexdigest(), "files": count}

log = Path(env["LOCALAPPDATA"]) / "VexiInstaller" / "install-latest.log"
def save_log(name, text):
    # Synthetic engineering log; remove machine-specific paths from the public copy.
    text = text.replace(str(target.parent), "<TEST_ROOT>")
    (output / name).write_text(text, encoding="utf-8")

save_log("clean_install.log", log.read_text("utf-8"))
before = fingerprint()
results = []
for name, flags in (("upgrade", ["--no-shortcuts"]), ("restore", ["--restore"])):
    result = subprocess.run([sys.executable, str(package / "install_engine.py"), "--target", str(target), *flags],
        cwd=package, env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=900)
    save_log(name + ".log", result.stdout + result.stderr + log.read_text("utf-8"))
    results.append({"check": name, "exit": result.returncode})
    if result.returncode: break
after = fingerprint()
evidence = {"utc": datetime.now(timezone.utc).isoformat(), "before": before, "after": after,
    "checks": results, "rollback_exact_bytes": before == after,
    "voice_field": "NOT_RUN", "uac": "NOT_RUN", "shortcuts": "NOT_RUN",
    "status": "PASS" if len(results) == 2 and all(r["exit"] == 0 for r in results) and before == after else "FAIL"}
(output / "upgrade_restore.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
print(json.dumps(evidence, indent=2))
raise SystemExit(0 if evidence["status"] == "PASS" else 1)
