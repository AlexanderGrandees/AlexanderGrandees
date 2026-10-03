import json
import logging
import os
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen


class PluginManager:
    PROTOCOL = 1
    def __init__(self, plugin_dir=None):
        self.dir = Path(plugin_dir or (Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Vexi" / "plugins"))
        self.dir.mkdir(parents=True, exist_ok=True)

    def manifests(self):
        out=[]
        for p in sorted(self.dir.glob("*.json")):
            try:
                # utf-8-sig accepts both normal UTF-8 and legacy PowerShell UTF-8 BOM manifests.
                d=json.loads(p.read_text(encoding="utf-8-sig")); d["_path"]=str(p)
                out.append(d)
            except Exception as exc:
                logging.warning("PLUGIN_MANIFEST_ERROR file=%s reason=%s", p, type(exc).__name__)
                continue
        return out

    def browser_pack(self, browser):
        b=str(browser or "").lower()
        for m in self.manifests():
            if m.get("type") == "browser_pack" and b in [str(x).lower() for x in m.get("browser_ids",[])]:
                return m
        return None

    @staticmethod
    def _health_url(manifest):
        ep=str(manifest.get("endpoint") or "").rstrip("/")
        return ep + "/health" if ep else ""

    def health(self, manifest, timeout=0.8):
        if not manifest:
            return {"ok":False,"detail":"not_installed"}
        url=self._health_url(manifest)
        if not url:
            return {"ok":False,"detail":"no_endpoint"}
        try:
            with urlopen(url, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            return {"ok":False,"detail":"offline"}

    def ensure_running(self, manifest, wait=2.5):
        h=self.health(manifest)
        if h.get("ok"):
            return h
        launcher=os.path.expandvars(str(manifest.get("launcher") or ""))
        if launcher and Path(launcher).exists():
            try:
                if launcher.lower().endswith('.vbs'):
                    subprocess.Popen(["wscript.exe", launcher], creationflags=0x08000000 if os.name=='nt' else 0)
                else:
                    subprocess.Popen([launcher], creationflags=0x08000000 if os.name=='nt' else 0)
            except Exception:
                pass
        deadline=time.monotonic()+wait
        while time.monotonic()<deadline:
            time.sleep(.15)
            h=self.health(manifest)
            if h.get("ok"):
                return h
        return h
