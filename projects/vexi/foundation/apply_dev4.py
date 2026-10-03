"""Apply dev4 bootstrap/UI/version changes to an exact dev1 isolated source tree.

This is NOT a live production updater. It refuses unknown baselines and writes backups.
Run only after copying/overlaying the cumulative dev4 package into an isolated dev1 tree.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"
PINNED_DEV1_SOURCE_SHA256 = "216484d1aa54ec2bfcd29f2753a0a629f8923fb25b91df99b1aea5a4eb7afdba"
SOURCE_MARKER = ROOT / ".dev1-source.sha256"



def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".dev4tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def patch_vexi(text: str) -> str:
    if "install_default_diagnostics" in text:
        return text
    anchor = "from foundation_bridge import FoundationBridge, MetadataOnlyFilter\n"
    if anchor not in text: raise RuntimeError("vexi_import_anchor_missing")
    text = text.replace(anchor, anchor + "from vexi_foundation.diagnostics import install_default_diagnostics\n", 1)
    anchor2 = "for _handler in logging.getLogger().handlers:\n    _handler.addFilter(MetadataOnlyFilter())\n"
    if anchor2 not in text: raise RuntimeError("vexi_logging_anchor_missing")
    block = '''for _handler in logging.getLogger().handlers:\n    _handler.addFilter(MetadataOnlyFilter())\n\ntry:\n    _diag_project_root = BASE.parent if (BASE.parent / "foundation").exists() else BASE\n    DIAGNOSTICS = install_default_diagnostics(\n        version=__version__, channel=__channel__, build=__build__, project_root=_diag_project_root)\nexcept Exception:\n    # Diagnostics must never prevent Vexi from starting. No exception payload is logged here.\n    DIAGNOSTICS = None\n'''
    return text.replace(anchor2, block, 1)


def patch_settings(text: str) -> str:
    if 'text="Диагностика"' in text:
        return text
    text = text.replace("import argparse\nimport tkinter as tk\n", "import argparse\nimport os\nimport subprocess\nimport sys\nimport threading\nfrom pathlib import Path\nimport tkinter as tk\n", 1)
    anchor = "from version import __version__, __channel__\n"
    if anchor not in text: raise RuntimeError("settings_import_anchor_missing")
    text = text.replace(anchor, anchor + "from vexi_foundation.diagnostics import DiagnosticsManager, SelfTestMode, default_diagnostics_root\n", 1)
    anchor = "    identity=AssistantIdentity(); creds=CredentialStore(); plugins=PluginManager(); services=ServiceRegistry()\n"
    if anchor not in text: raise RuntimeError("settings_init_anchor_missing")
    text = text.replace(anchor, anchor + "    diagnostics=DiagnosticsManager(default_diagnostics_root())\n    project_root=Path(__file__).resolve().parent\n    if not (project_root / \"foundation\" / \"tests\").exists(): project_root=project_root.parent\n", 1)
    anchor = '    tab_map={"assistant":0,"plugins":1,"security":2}\n'
    if anchor not in text: raise RuntimeError("settings_tab_anchor_missing")
    block = r'''    # Diagnostics
    f_diag=ttk.Frame(nb); nb.add(f_diag,text="Диагностика")
    ttk.Label(f_diag,text="Логи, self-test и пакет для отправки",font=("Segoe UI",12,"bold")).pack(anchor="w",padx=16,pady=(18,4))
    ttk.Label(f_diag,text="Сохраняются только безопасные метаданные. Распознанная речь, тексты документов, промпты, пароли и токены не пишутся в диагностические логи.",wraplength=660).pack(anchor="w",padx=16,pady=(0,8))
    diag_path=tk.StringVar(value=str(diagnostics.root)); diag_status=tk.StringVar(value=""); diag_result=tk.StringVar(value="Self-test ещё не запускался")
    ttk.Label(f_diag,textvariable=diag_path,wraplength=660).pack(anchor="w",padx=16,pady=3)

    def open_diag_path(path):
        path=Path(path); path.mkdir(parents=True,exist_ok=True)
        try:
            if os.name=="nt": os.startfile(str(path))
            elif sys.platform=="darwin": subprocess.Popen(["open",str(path)])
            else: subprocess.Popen(["xdg-open",str(path)])
        except Exception as e: messagebox.showerror("Vexi",f"Не удалось открыть папку: {type(e).__name__}")

    controls=ttk.Frame(f_diag); controls.pack(fill="x",padx=16,pady=6)
    mode_var=tk.StringVar(value=SelfTestMode.FAST.value)
    ttk.Label(controls,text="Self-test:").pack(side="left")
    ttk.Combobox(controls,textvariable=mode_var,values=[m.value for m in SelfTestMode],state="readonly",width=14).pack(side="left",padx=(6,8))
    busy={"value":False}
    def finish_diag(message,refresh=True):
        busy["value"]=False; diag_result.set(message)
        if refresh: refresh_diag()
    def run_selftest():
        if busy["value"]: return
        busy["value"]=True; diag_result.set(f"{mode_var.get()} self-test выполняется...")
        def worker():
            try:
                result=diagnostics.run_selftest(SelfTestMode(mode_var.get()),project_root=project_root)
                summary=result["summary"]
                msg=f'{result["mode"]}: {result["status"]} | run={summary["run"]} fail={summary["failures"]} err={summary["errors"]}'
            except Exception as e: msg=f"Self-test error: {type(e).__name__}"
            root.after(0,lambda:finish_diag(msg))
        threading.Thread(target=worker,daemon=True).start()
    ttk.Button(controls,text="Запустить",command=run_selftest).pack(side="left")
    ttk.Button(controls,text="Открыть папку логов",command=lambda:open_diag_path(diagnostics.root)).pack(side="left",padx=8)
    ttk.Button(controls,text="Открыть exports",command=lambda:open_diag_path(diagnostics.exports_dir)).pack(side="left")

    export_row=ttk.Frame(f_diag); export_row.pack(fill="x",padx=16,pady=4)
    def export_diag():
        if busy["value"]: return
        busy["value"]=True; diag_result.set("Собираю безопасный ZIP...")
        def worker():
            try:
                path,sha=diagnostics.export_bundle(version=__version__,channel=__channel__,build="settings-ui")
                msg=f"Готово: {path.name} | SHA-256 {sha[:16]}..."
            except Exception as e: msg=f"Export error: {type(e).__name__}"
            root.after(0,lambda:finish_diag(msg))
        threading.Thread(target=worker,daemon=True).start()
    ttk.Button(export_row,text="Собрать ZIP для ChatGPT",command=export_diag).pack(side="left")
    deep_var=tk.BooleanVar(value=diagnostics.deep_mode_active())
    def toggle_deep():
        diagnostics.set_deep_mode(bool(deep_var.get()),minutes=60); refresh_diag()
    ttk.Checkbutton(export_row,text="DEEP diagnostics на 60 минут (без raw content)",variable=deep_var,command=toggle_deep).pack(side="left",padx=14)
    ttk.Label(f_diag,textvariable=diag_result).pack(anchor="w",padx=16,pady=(4,2))
    ttk.Label(f_diag,textvariable=diag_status).pack(anchor="w",padx=16,pady=(0,6))

    d_tree=ttk.Treeview(f_diag,columns=("kind","name","size","modified"),show="headings",height=9)
    for col,title,w in [("kind","Тип",80),("name","Файл",300),("size","Размер",90),("modified","Изменён",150)]: d_tree.heading(col,text=title); d_tree.column(col,width=w)
    d_tree.pack(fill="both",expand=True,padx=16,pady=6)
    def refresh_diag():
        st=diagnostics.status(); deep_var.set(st.deep_mode)
        diag_status.set(f"Логи: {st.total_bytes/1024/1024:.2f} MB | runtime={st.runtime_files} incident={st.incident_files} | last test={st.last_selftest_mode}/{st.last_selftest_status} | mode={'DEEP' if st.deep_mode else 'SAFE'}")
        for item in d_tree.get_children(): d_tree.delete(item)
        import time as _time
        for item in diagnostics.recent_files(25):
            d_tree.insert("","end",values=(item["kind"],item["name"],f'{item["size"]/1024:.1f} KB',_time.strftime("%Y-%m-%d %H:%M",_time.localtime(item["mtime"]))))
    ttk.Button(f_diag,text="Обновить список",command=refresh_diag).pack(anchor="e",padx=16,pady=(0,8)); refresh_diag()

    tab_map={"assistant":0,"plugins":1,"security":2,"diagnostics":3,"logs":3}
'''
    return text.replace(anchor, block, 1)


def patch_version(text: str) -> str:
    return '__version__ = "0.1.5.dev4"\n__channel__ = "development"\n__build__ = "diagnostics-selftest-docx-hybrid"\n__legacy_lineage__ = "v0.1.3-plugin-kernel"\n'


def _require_verified_source() -> None:
    if not SOURCE_MARKER.exists():
        raise RuntimeError("verified_source_marker_missing")
    marker = SOURCE_MARKER.read_text(encoding="ascii", errors="strict").strip().lower()
    if marker != PINNED_DEV1_SOURCE_SHA256:
        raise RuntimeError("verified_source_marker_mismatch")


def _validate_semantic_baseline(name: str, text: str) -> None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if name == "vexi.py":
        required = (
            "from foundation_bridge import FoundationBridge, MetadataOnlyFilter\n",
            "for _handler in logging.getLogger().handlers:\n    _handler.addFilter(MetadataOnlyFilter())\n",
        )
        if not all(anchor in normalized for anchor in required):
            raise RuntimeError("baseline_anchor_mismatch:vexi.py")
    elif name == "settings_ui.py":
        required = (
            "import argparse\nimport tkinter as tk\n",
            "from version import __version__, __channel__\n",
            "    identity=AssistantIdentity(); creds=CredentialStore(); plugins=PluginManager(); services=ServiceRegistry()\n",
            '    tab_map={"assistant":0,"plugins":1,"security":2}\n',
        )
        if not all(anchor in normalized for anchor in required):
            raise RuntimeError("baseline_anchor_mismatch:settings_ui.py")
    elif name == "version.py":
        required = (
            '__version__ = "0.1.5.dev1"',
            '__channel__ = "development"',
            '__build__ = "attention-guest-workspace-abc"',
        )
        if not all(anchor in normalized for anchor in required):
            raise RuntimeError("baseline_anchor_mismatch:version.py")


def main():
    _require_verified_source()
    backup = ROOT / ".dev4-backup"
    backup.mkdir(exist_ok=True)
    patchers = {"vexi.py": patch_vexi, "settings_ui.py": patch_settings, "version.py": patch_version}
    for name, fn in patchers.items():
        path = CORE / name
        if not path.exists():
            raise RuntimeError(f"baseline_file_missing:{name}")
        raw = path.read_bytes()
        already = (name == "vexi.py" and b"install_default_diagnostics" in raw) or (name == "settings_ui.py" and "Диагностика".encode("utf-8") in raw) or (name == "version.py" and b'0.1.5.dev4' in raw)
        if already:
            print(f"SKIP {name}: already dev4")
            continue
        text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        _validate_semantic_baseline(name, text)
        shutil.copy2(path, backup / name)
        patched = fn(text).encode("utf-8")
        atomic_write(path, patched)
        print(f"PATCHED {name}")
    print("DEV4_BOOTSTRAP_OK")

if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        code = str(exc).split(":", 1)[0] or "RuntimeError"
        print("DEV4_BOOTSTRAP_ERROR " + code, file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print("DEV4_BOOTSTRAP_ERROR " + type(exc).__name__, file=sys.stderr)
        raise SystemExit(3)
