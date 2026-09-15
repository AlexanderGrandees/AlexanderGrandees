"""Build a preassembled development installer; never patch installed source."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

NAME = "Vexi_0.1.5_dev4_FIX9_Installer"

def build(output):
    project = Path(__file__).resolve().parents[1]
    package = output / NAME
    package.mkdir(parents=True, exist_ok=False)
    payload = package / "payload"
    payload.mkdir()
    def copy_tree(source, target, extensions):
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix in extensions:
                if path.name in {"config.json", "app_cache.json", "runtime-ready.json"}: continue
                dest = target / path.relative_to(source)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
    for path in sorted((project / "core").iterdir()):
        if path.is_file() and (path.suffix == ".py" or path.name in {
                "config.defaults.json", "requirements_v014.txt", "requirements.lock.txt"}):
            shutil.copy2(path, payload / path.name)
    copy_tree(project / "core" / "vexi_foundation", payload / "vexi_foundation", {".py"})
    copy_tree(project / "foundation" / "tests", payload / "foundation" / "tests", {".py"})
    copy_tree(project / "foundation" / "samples", payload / "foundation" / "samples", {".docx"})
    for name in ("apply_dev4.py", "smoke_docx_dev3.py"):
        shutil.copy2(project / "foundation" / name, payload / "foundation" / name)
    manifest = {p.relative_to(payload).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(payload.rglob("*")) if p.is_file()}
    (payload / "payload-manifest.json").write_text(json.dumps({"version": "0.1.5.dev4",
        "build": "fix9", "files": manifest}, indent=2), encoding="utf-8")
    for name in ("install_engine.py", "install.ps1", "elevate.ps1", "stop_runtime.ps1",
                 "shortcuts.ps1", "INSTALL_VEXI.cmd", "RESTORE_PREVIOUS.cmd", "README_RU.md"):
        shutil.copy2(project / "installer" / name, package / name)
    archive = output / (NAME + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(package.rglob("*")):
            if p.is_file():
                info = zipfile.ZipInfo(p.relative_to(output).as_posix(), (2026, 9, 14, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / (archive.name + ".sha256")).write_text(checksum + "  " + archive.name + "\n")
    return {"zip": str(archive), "sha256": checksum, "payload_files": len(manifest)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("output", type=Path)
    print(json.dumps(build(ap.parse_args().output), indent=2))
