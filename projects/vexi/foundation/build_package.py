"""Deterministic source-only development ZIP; excludes legacy public installers."""
from pathlib import Path
import hashlib
import json
import zipfile

project = Path(__file__).resolve().parents[1]
release = project / "releases" / "v0.1.5-development"
files = {}
for path in (project / "core").rglob("*.py"):
    if "__pycache__" not in path.parts:
        files[path.relative_to(project).as_posix()] = path.read_bytes()
for name in ("config.defaults.json", "requirements_v014.txt"):
    files["core/" + name] = (project / "core" / name).read_bytes()
for path in (project / "foundation" / "tests").glob("*.py"):
    files[path.relative_to(project).as_posix()] = path.read_bytes()
files["ENGINEERING_ABC.md"] = (project / "foundation" / "ENGINEERING_ABC.md").read_bytes()
files["README_RU.md"] = (release / "README_RU.md").read_bytes()
files["EVIDENCE.json"] = (release / "evidence.json").read_bytes()
manifest = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
files["MANIFEST.json"] = json.dumps(manifest, indent=2).encode()
output = release / "Vexi_0.1.5-dev1_ABC_Source.zip"
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for name, data in sorted(files.items()):
        info = zipfile.ZipInfo(name, date_time=(2026, 9, 13, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, data)
checksum = hashlib.sha256(output.read_bytes()).hexdigest()
(release / "SHA256SUMS.txt").write_text(checksum + "  " + output.name + "\n", encoding="utf-8")
print(json.dumps({"archive": str(output), "sha256": checksum, "files": len(files)}))
