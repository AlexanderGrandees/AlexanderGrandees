"""Prebuilt, transactional Windows installer. No source patching or code downloads.

All swaps/backups are siblings of one validated target on the same volume.
User data and environments are copied to staging, not modified in the backup.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
import uuid
import venv


class InstallError(RuntimeError):
    pass


def marker_matches_launch(data, launch_id):
    # Windows venv pythonw redirects to a child PID. Correlate the launch, not the wrapper PID.
    return bool(launch_id) and data.get("launch_id") == launch_id and data.get("version") == "0.1.5.dev4"


def acquire_lock(target):
    # Windows releases the byte lock after process death; no stale PID lockout.
    import msvcrt
    path = target.with_name(target.name + ".install.lock")
    reject_links(path)
    handle = path.open("a+b")
    handle.seek(0, 2)
    if handle.tell() == 0:
        handle.write(b"0"); handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        raise InstallError("INSTALL_LOCKED: another installation is running")
    return handle


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def reject_links(path):
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            st = item.lstat()
            if item.is_symlink() or getattr(st, "st_file_attributes", 0) & 0x400:
                raise InstallError("REPARSE_TARGET: junction/symlink targets are unsupported")


def validate_target(target):
    target = Path(os.path.abspath(target))
    if target == Path(target.anchor) or target.name.lower() not in {"vexi", "vexidev4"}:
        raise InstallError("INVALID_TARGET: choose a dedicated Vexi or VexiDev4 folder")
    reject_links(target)
    if target.exists() and any(target.iterdir()):
        if not (target / "vexi.py").is_file() or not (target / "version.py").is_file():
            raise InstallError("UNRELATED_TARGET: folder is not a Vexi runtime")
    return target


def verify_payload(payload):
    manifest = json.loads((payload / "payload-manifest.json").read_text("utf-8"))
    expected = manifest["files"]
    for name, checksum in expected.items():
        rel = PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts or ":" in name or "\\" in name:
            raise InstallError("INVALID_MANIFEST_PATH")
        path = payload.joinpath(*rel.parts)
        reject_links(path)
        if not path.is_file() or sha(path) != checksum:
            raise InstallError("PAYLOAD_HASH_MISMATCH: " + name)
    actual = {p.relative_to(payload).as_posix() for p in payload.rglob("*") if p.is_file()}
    if actual != set(expected) | {"payload-manifest.json"}:
        raise InstallError("UNEXPECTED_PAYLOAD_FILES")
    return manifest


class Installer:
    def __init__(self, payload, target, log):
        self.payload = Path(payload).resolve()
        self.target = validate_target(target)
        if self.payload == self.target or self.payload.is_relative_to(self.target):
            raise InstallError("PAYLOAD_INSIDE_TARGET")
        self.log = Path(log)
        tag = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
        self.stage = self.target.with_name(self.target.name + ".stage-" + tag)
        self.backup = self.target.with_name(self.target.name + ".backup-" + tag)
        self.failed = self.target.with_name(self.target.name + ".failed-" + tag)
        self.swapped = False
        self.backed_up = False
        self.journal = self.target.with_name(self.target.name + ".transaction.json")
        self.mode = "UPGRADE" if self.target.exists() and any(self.target.iterdir()) else "CLEAN_INSTALL"

    def event(self, event, **fields):
        self.log.parent.mkdir(parents=True, exist_ok=True)
        row = {"utc": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
        with self.log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
        print("[Vexi] " + event, flush=True)

    def stage_payload(self):
        verify_payload(self.payload)
        self.event("PAYLOAD_VERIFIED", mode=self.mode)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.payload, self.stage)
        if self.mode == "UPGRADE":
            # Unknown source files remain in backup. Never merge old executable code.
            for name in (".venv", "venv", "models", "model", "voices", "assets", "data",
                         "workspace", "workspaces", "documents"):
                source = self.target / name
                if source.exists():
                    reject_links(source)
                    # Do not follow hidden reparse points inside preserved stores.
                    for child in source.rglob("*"): reject_links(child)
                    shutil.copytree(source, self.stage / name)
            for name in ("config.json", "vexi.ico", "app_cache.json"):
                source = self.target / name
                if source.is_file():
                    reject_links(source); shutil.copy2(source, self.stage / name)
        defaults = json.loads((self.stage / "config.defaults.json").read_text("utf-8-sig"))
        config = self.stage / "config.json"
        if config.exists(): defaults.update(json.loads(config.read_text("utf-8-sig")))
        defaults.update(version="0.1.5.dev4", release_channel="development")
        config.write_text(json.dumps(defaults, indent=2, ensure_ascii=False), encoding="utf-8")
        self.event("STAGE_READY")

    def swap(self, validate, stop=lambda: None):
        # validate callback runs all pre-swap checks before existing runtime is stopped.
        validate(self.stage)
        self.event("PRE_SWAP_CHECKS_PASSED")
        stop()
        reject_links(self.target)
        self.journal.write_text(json.dumps({"target": str(self.target), "backup": str(self.backup),
            "stage": str(self.stage), "state": "SWITCHING"}), encoding="utf-8")
        if self.target.exists():
            self.target.rename(self.backup); self.backed_up = True
        try:
            self.stage.rename(self.target); self.swapped = True
            self.event("RUNTIME_SWITCHED")
        except Exception:
            self.rollback()
            raise

    def rollback(self):
        # All paths were derived as checked siblings; no recursive deletion.
        for p in (self.target, self.backup, self.failed):
            if p.parent != self.target.parent: raise InstallError("ROLLBACK_BOUNDARY")
            reject_links(p)
        if self.swapped and self.target.exists():
            self.target.rename(self.failed)
        if self.backed_up and self.backup.exists():
            self.backup.rename(self.target)
        self.swapped = False
        self.journal.write_text(json.dumps({"state": "ROLLED_BACK"}), encoding="utf-8")
        self.event("ROLLBACK_COMPLETE", old_runtime_restored=self.backed_up)


def run_checked(argv, cwd, log, timeout=600):
    # CLI output contains synthetic self-test results only; never dump config/env.
    result = subprocess.run(argv, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace",
                            timeout=timeout, env={**os.environ, "PYTHONIOENCODING": "utf-8",
                            "PYTHONDONTWRITEBYTECODE": "1"})
    with log.open("a", encoding="utf-8") as f:
        f.write(result.stdout); f.write(result.stderr)
    if result.returncode:
        raise InstallError("COMMAND_FAILED: " + Path(argv[-1]).name + " exit=" + str(result.returncode))
    return result


def runtime_python(root):
    for relative in (".venv/Scripts/python.exe", "venv/Scripts/python.exe"):
        path = root / relative
        if path.is_file(): return path
    raise InstallError("RUNTIME_PYTHON_MISSING")


def prepare_environment(installer):
    try: py = runtime_python(installer.stage)
    except InstallError:
        installer.event("CREATING_PYTHON_ENVIRONMENT")
        venv.EnvBuilder(with_pip=True).create(installer.stage / ".venv")
        py = runtime_python(installer.stage)
    installer.event("CHECKING_RUNTIME_DEPENDENCIES")
    probe = subprocess.run([str(py), "runtime_check.py", "--imports-only"], cwd=installer.stage,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode:
        installer.event("INSTALLING_RUNTIME_DEPENDENCIES_INTERNET_REQUIRED")
        # Stream visible progress; pip is invoked as a module so moved venv scripts are irrelevant.
        result = subprocess.run([str(py), "-m", "pip", "install", "-r", "requirements_v014.txt"],
                                cwd=installer.stage, timeout=3600)
        if result.returncode: raise InstallError("DEPENDENCY_INSTALL_FAILED")
    return py


def stop_runtime(root, package):
    script = package / "stop_runtime.ps1"
    run_checked(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                 "-Target", str(root)], package, package / "process-control.log", timeout=30)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=Path("C:/Vexi"))
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--verify-package", action="store_true")
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--no-shortcuts", action="store_true", help="Isolated engineering validation only")
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    logdir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "VexiInstaller"
    logdir.mkdir(parents=True, exist_ok=True)
    logfile = logdir / "install-latest.log"
    logfile.write_text("", encoding="utf-8")
    instance = None
    lock = None
    try:
        if args.verify_package:
            verify_payload(package / "payload"); print("PAYLOAD_VERIFIED"); return 0
        if args.restore:
            journal = Path(os.path.abspath(args.target)).with_name(args.target.name + ".transaction.json")
            pending = json.loads(journal.read_text("utf-8")) if journal.exists() else {}
            receipt = (pending if pending.get("state") == "SWITCHING"
                       else json.loads((logdir / "last-install.json").read_text("utf-8")))
            target = validate_target(receipt["target"]); backup = Path(receipt["backup"])
            journal = target.with_name(target.name + ".transaction.json")
            if backup.parent != target.parent or not backup.name.startswith(target.name + ".backup-"):
                raise InstallError("RESTORE_BOUNDARY")
            reject_links(backup)
            if not (backup / "vexi.py").is_file(): raise InstallError("NO_PREVIOUS_RUNTIME")
            lock = acquire_lock(target)
            stop_runtime(target, package)
            failed = target.with_name(target.name + ".manual-restore-" + uuid.uuid4().hex[:8])
            if target.exists(): target.rename(failed)
            try: backup.rename(target)
            except Exception:
                if failed.exists(): failed.rename(target)
                raise
            journal.write_text(json.dumps({"state": "ROLLED_BACK"}), encoding="utf-8")
            print("PREVIOUS_VEXI_RESTORED"); return 0
        instance = Installer(package / "payload", args.target, logfile)
        if Path(sys.executable).resolve().is_relative_to(instance.target):
            raise InstallError("INSTALLER_INSIDE_TARGET: run INSTALL_VEXI.cmd using base Python")
        if instance.journal.exists() and json.loads(instance.journal.read_text("utf-8")).get("state") == "SWITCHING":
            raise InstallError("RECOVERY_REQUIRED: run RESTORE_PREVIOUS.cmd first")
        instance.target.parent.mkdir(parents=True, exist_ok=True)
        lock = acquire_lock(instance.target)
        instance.stage_payload()
        prepare_environment(instance)
        def validate(root):
            py = runtime_python(root)
            run_checked([str(py), "runtime_check.py"], root, logfile)
            run_checked([str(py), "diagnostics_cli.py", "selftest", "--mode", "REGRESSION"], root, logfile)
        instance.swap(validate, stop=lambda: stop_runtime(instance.target, package))
        validate(instance.target)
        receipt = {"target": str(instance.target), "backup": str(instance.backup),
                   "mode": instance.mode, "version": "0.1.5.dev4", "build": "fix8",
                   "voice_field": "NOT_RUN"}
        (logdir / "last-install.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        if not args.no_shortcuts:
            run_checked(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(package / "shortcuts.ps1"), "-Target", str(instance.target)], package, logfile, timeout=30)
        instance.event("INSTALLED", mode=instance.mode)
        if args.launch:
            py = runtime_python(instance.target)
            pyw = py.with_name("pythonw.exe")
            ready = instance.target / "runtime-ready.json"
            if ready.exists(): ready.unlink()
            launch_id = uuid.uuid4().hex
            proc = subprocess.Popen([str(pyw if pyw.exists() else py), str(instance.target / "vexi.py")], cwd=instance.target,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                     env={**os.environ, "VEXI_LAUNCH_ID": launch_id})
            instance.event("LAUNCH_REQUESTED", pid=proc.pid)
            # Liveness alone is not READY. Cold STT/TTS can take minutes.
            for _ in range(30):
                if proc.poll() is not None: raise InstallError("RUNTIME_EXITED_BEFORE_READY")
                if ready.exists():
                    data = json.loads(ready.read_text("utf-8"))
                    if marker_matches_launch(data, launch_id) and data.get("state") == "STARTUP_FAILED":
                        raise InstallError("VOICE_COMPONENT_STARTUP_FAILED")
                    if (marker_matches_launch(data, launch_id)
                            and data.get("state") == "MICROPHONE_READY"):
                        instance.event("VOICE_READY", field="NOT_RUN"); break
                time.sleep(1)
            else: instance.event("VOICE_STARTUP_PENDING", field="NOT_RUN")
        instance.journal.write_text(json.dumps({"state": "COMMITTED"}), encoding="utf-8")
        print("Log: " + str(logfile)); return 0
    except Exception as exc:
        # Installer errors include actionable stage/message; runtime privacy logger is separate.
        with logfile.open("a", encoding="utf-8") as f:
            f.write("INSTALL_FAILED " + type(exc).__name__ + ": " + str(exc) + "\n")
        print("[Vexi] INSTALL_FAILED: " + str(exc), file=sys.stderr)
        if instance and (instance.swapped or instance.backed_up):
            try:
                stop_runtime(instance.target, package); instance.rollback()
            except Exception as recovery:
                print("ROLLBACK_FAILED: " + str(recovery), file=sys.stderr)
        print("Log: " + str(logfile)); return 1
    finally:
        if lock is not None:
            lock.close()


if __name__ == "__main__": raise SystemExit(main())
