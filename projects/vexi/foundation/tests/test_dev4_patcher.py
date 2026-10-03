# Shared imports work in both source (core/) and installed flat layouts.
import sys as _sys
from pathlib import Path as _Path
_root = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_root / "core" if (_root / "core").is_dir() else _root))
from pathlib import Path
import importlib.util
import unittest

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("apply_dev4", HERE/"apply_dev4.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class Dev4PatcherTests(unittest.TestCase):
    def test_vexi_patch_compiles(self):
        src='''import logging\nfrom pathlib import Path\nfrom version import __version__, __channel__, __build__\nfrom foundation_bridge import FoundationBridge, MetadataOnlyFilter\nBASE=Path(".")\nfor _handler in logging.getLogger().handlers:\n    _handler.addFilter(MetadataOnlyFilter())\n'''
        out=mod.patch_vexi(src)
        self.assertIn("install_default_diagnostics",out)
        compile(out,"vexi.py","exec")

    def test_settings_patch_compiles(self):
        src='''import argparse\nimport tkinter as tk\nfrom tkinter import ttk, messagebox\nfrom assistant_identity import AssistantIdentity\nfrom credential_store import CredentialStore\nfrom plugin_manager import PluginManager\nfrom service_registry import ServiceRegistry\nfrom version import __version__, __channel__\n\ndef run(initial_tab="security"):\n    root=tk.Tk(); nb=ttk.Notebook(root)\n    identity=AssistantIdentity(); creds=CredentialStore(); plugins=PluginManager(); services=ServiceRegistry()\n    tab_map={"assistant":0,"plugins":1,"security":2}\n    nb.select(tab_map.get(initial_tab,2)); root.mainloop()\n'''
        out=mod.patch_settings(src)
        self.assertIn('text="Диагностика"',out)
        self.assertIn('"diagnostics":3',out)
        compile(out,"settings_ui.py","exec")

    def test_patch_version_identifies_dev4(self):
        out=mod.patch_version('anything')
        self.assertIn('0.1.5.dev4',out); self.assertIn('diagnostics-selftest-docx-hybrid',out)


    def test_semantic_baseline_accepts_line_ending_independent_version(self):
        text='__version__ = "0.1.5.dev1"\r\n__channel__ = "development"\r\n__build__ = "attention-guest-workspace-abc"\r\n'
        mod._validate_semantic_baseline("version.py", text)

    def test_git_blob_sha_known_vector(self):
        import hashlib
        data=b"hello\n"
        expected=hashlib.sha1(b"blob 6\0"+data).hexdigest()
        self.assertEqual(mod.git_blob_sha(data),expected)

if __name__=='__main__': unittest.main()
