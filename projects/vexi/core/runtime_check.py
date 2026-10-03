"""Preflight checks without microphone/model loading or private config output."""
import argparse
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--imports-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    required = ("numpy", "requests", "sounddevice", "faster_whisper", "silero", "piper",
                "pystray", "PIL", "psutil", "pycaw", "comtypes", "pywinauto", "send2trash", "tkinter", "torch")
    failed = []
    for module in required:
        try: importlib.import_module(module)
        except Exception as exc: failed.append({"module": module, "error_type": type(exc).__name__})
    if failed:
        print(json.dumps({"status": "FAIL", "imports": failed})); return 1
    if args.imports_only: print('RUNTIME_IMPORTS_PASS'); return 0
    manifest = json.loads((root / "payload-manifest.json").read_text("utf-8"))
    for name, expected in manifest["files"].items():
        path = root / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            print(json.dumps({"status": "FAIL", "code": "MANIFEST", "module": name})); return 1
        if path.suffix == ".py": ast.parse(path.read_text("utf-8-sig"))
    config = json.loads((root / "config.json").read_text("utf-8-sig"))
    if config.get("version") != "0.1.5.dev4":
        print('CONFIG_VERSION_FAIL'); return 1
    import vexi
    if vexi.__version__ != "0.1.5.dev4": return 1
    from vexi_foundation.diagnostics import DiagnosticsManager, SelfTestMode
    result = DiagnosticsManager().run_selftest(SelfTestMode.FAST)
    print(json.dumps({"status": result["status"], "imports": "PASS", "manifest": "PASS",
                      "voice_field": "NOT_RUN"}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
