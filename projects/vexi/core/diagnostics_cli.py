import argparse
import json
from pathlib import Path
from version import __version__, __channel__, __build__
from vexi_foundation.diagnostics import DiagnosticsManager, SelfTestMode, default_diagnostics_root


def main():
    ap = argparse.ArgumentParser(description="Vexi safe diagnostics")
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("selftest"); st.add_argument("--mode", choices=[m.value for m in SelfTestMode], default="FAST")
    sub.add_parser("export"); sub.add_parser("status"); sub.add_parser("folder")
    args = ap.parse_args()
    manager = DiagnosticsManager(default_diagnostics_root())
    if args.cmd == "selftest":
        project_root = Path(__file__).resolve().parent
        if not (project_root / "foundation" / "tests").exists():
            project_root = project_root.parent
        result = manager.run_selftest(SelfTestMode(args.mode), project_root=project_root)
        print(json.dumps({"status": result["status"], "mode": result["mode"], "summary": result["summary"]}, ensure_ascii=False))
        return 0 if result["status"] == "PASS" else 1
    elif args.cmd == "export":
        path, sha = manager.export_bundle(version=__version__, channel=__channel__, build=__build__)
        print(path); print(sha)
    elif args.cmd == "status":
        print(json.dumps(manager.status().__dict__, ensure_ascii=False, indent=2))
    else:
        print(manager.root)

if __name__ == "__main__": raise SystemExit(main())
