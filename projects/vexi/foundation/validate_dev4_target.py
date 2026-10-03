from pathlib import Path
import sys

ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
PINNED="216484d1aa54ec2bfcd29f2753a0a629f8923fb25b91df99b1aea5a4eb7afdba"
marker=ROOT/".dev1-source.sha256"
failed=False
if not marker.exists() or marker.read_text(encoding="ascii",errors="ignore").strip().lower()!=PINNED:
 print("MISMATCH verified source marker"); failed=True
else:
 print("OK verified source archive marker")
checks={
 "core/vexi.py":("from foundation_bridge import FoundationBridge, MetadataOnlyFilter","MetadataOnlyFilter()"),
 "core/settings_ui.py":("from version import __version__, __channel__",'tab_map={"assistant":0,"plugins":1,"security":2}'),
 "core/version.py":('__version__ = "0.1.5.dev1"','__build__ = "attention-guest-workspace-abc"'),
}
for rel,anchors in checks.items():
 p=ROOT/rel
 if not p.exists(): print("MISSING",rel); failed=True; continue
 raw=p.read_bytes(); text=raw.decode("utf-8-sig",errors="strict").replace("\r\n","\n").replace("\r","\n")
 dev4=(rel.endswith("vexi.py") and "install_default_diagnostics" in text) or (rel.endswith("settings_ui.py") and "Диагностика" in text) or (rel.endswith("version.py") and "0.1.5.dev4" in text)
 ok=dev4 or all(a in text for a in anchors)
 print("OK" if ok else "MISMATCH",rel,"dev4" if dev4 else "semantic baseline")
 failed=failed or not ok
for rel in ("core/vexi_foundation/diagnostics.py","core/vexi_foundation/document_lifecycle.py","core/vexi_foundation/docx_provider.py"):
 if not (ROOT/rel).exists(): print("MISSING",rel); failed=True
raise SystemExit(1 if failed else 0)
