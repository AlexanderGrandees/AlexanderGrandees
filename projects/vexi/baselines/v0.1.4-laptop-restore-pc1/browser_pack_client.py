import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

from credential_store import CredentialStore
from plugin_manager import PluginManager


class BrowserPackClient:
    def __init__(self, plugin_manager=None):
        self.plugins = plugin_manager or PluginManager()
        self.credentials = CredentialStore()

    def manifest(self, browser):
        return self.plugins.browser_pack(browser)

    def _token(self, manifest):
        target=manifest.get("credential_target") if manifest else None
        return self.credentials.read(target) if target else None

    def _request(self, browser, path, method="GET", payload=None, timeout=3.0):
        m=self.manifest(browser)
        if not m:
            return None, {"detail":"browser_pack_not_installed"}
        self.plugins.ensure_running(m)
        endpoint=str(m.get("endpoint") or "").rstrip("/")
        token=self._token(m)
        if not endpoint or not token:
            return m, {"detail":"browser_pack_not_configured"}
        data=None
        headers={"X-Vexi-Token":token}
        if payload is not None:
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"]="application/json"
        req=Request(endpoint+path, data=data, method=method, headers=headers)
        try:
            with urlopen(req, timeout=timeout) as r:
                return m, json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return m, {"detail":"browser_pack_offline","error":type(e).__name__}

    def status(self, browser):
        m, data=self._request(browser,"/status",timeout=1.2)
        if not m:
            return {"installed":False,"connected":False,"detail":data.get("detail")}
        return {"installed":True, **data, "version":m.get("version"), "plugin_id":m.get("plugin_id")}

    def snapshot(self, browser, max_age=3.0):
        m, data=self._request(browser, f"/snapshot?max_age={float(max_age):.2f}", timeout=1.2)
        return data.get("snapshot") if isinstance(data,dict) else None

    def issue(self, browser, action, payload=None, timeout=5.0):
        m, data=self._request(browser,"/command",method="POST",payload={"action":action,"payload":payload or {},"timeout":float(timeout)},timeout=float(timeout)+2.0)
        if not m:
            return "UNSUPPORTED", data
        if not isinstance(data,dict):
            return "FAILED", {"detail":"bad_response"}
        return data.get("status","FAILED"), data.get("result") or data

    def wait_for(self, browser, predicate, timeout=5.0):
        deadline=time.monotonic()+float(timeout)
        while time.monotonic()<deadline:
            snap=self.snapshot(browser,max_age=2.0)
            if snap:
                try:
                    if predicate(snap): return snap
                except Exception: pass
            time.sleep(.10)
        return None
