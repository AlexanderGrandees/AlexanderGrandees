import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class BrowserBridge:
    """Local localhost bridge between Vexi and the optional browser extension.

    The bridge never reads browser credentials/cookies. The extension sends a
    semantic snapshot of the visible active page and polls for typed commands.
    """

    def __init__(self, host="127.0.0.1", port=8765, token="", enabled=True):
        self.host = host
        self.port = int(port)
        self.token = token or ""
        self.enabled = bool(enabled)
        self._lock = threading.RLock()
        self._snapshot = None
        self._snapshot_at = 0.0
        self._pending = None
        self._results = {}
        self._seq = 0
        self._server = None
        self._thread = None
        if self.enabled:
            self.start()

    def start(self):
        if self._server is not None:
            return
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "VexiBridge/0.1.2"

            def log_message(self, fmt, *args):
                logging.debug("BrowserBridge: " + fmt, *args)

            def _cors(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Vexi-Token")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

            def _ok(self, payload, code=200):
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self._cors()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _authorized(self):
                if not bridge.token:
                    return True
                return self.headers.get("X-Vexi-Token", "") == bridge.token

            def do_OPTIONS(self):
                self.send_response(204)
                self._cors()
                self.end_headers()

            def do_GET(self):
                u = urlparse(self.path)
                if u.path == "/health":
                    self._ok({"ok": True, "version": "0.1.2", "snapshot": bridge.snapshot(max_age=5.0) is not None})
                    return
                if not self._authorized():
                    self._ok({"error": "unauthorized"}, 401)
                    return
                if u.path == "/snapshot":
                    self._ok({"snapshot": bridge.snapshot(max_age=15.0)})
                    return
                if u.path == "/poll":
                    self._ok({"command": bridge._take_pending()})
                    return
                self._ok({"error": "not_found"}, 404)

            def do_POST(self):
                if not self._authorized():
                    self._ok({"error": "unauthorized"}, 401)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length) if length else b"{}"
                    data = json.loads(body.decode("utf-8"))
                except Exception:
                    self._ok({"error": "bad_json"}, 400)
                    return
                u = urlparse(self.path)
                if u.path == "/snapshot":
                    bridge.update_snapshot(data)
                    self._ok({"ok": True})
                    return
                if u.path == "/result":
                    bridge.set_result(data)
                    self._ok({"ok": True})
                    return
                self._ok({"error": "not_found"}, 404)

        try:
            self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        except OSError as exc:
            logging.warning("BrowserBridge could not bind %s:%s: %s", self.host, self.port, exc)
            self.enabled = False
            return
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True, name="VexiBrowserBridge")
        self._thread.start()
        logging.info("BrowserBridge ready http://%s:%s", self.host, self.port)

    def stop(self):
        srv = self._server
        self._server = None
        if srv:
            try:
                srv.shutdown()
                srv.server_close()
            except Exception:
                pass

    def update_snapshot(self, data):
        if not isinstance(data, dict):
            return
        if data.get("visibility") not in (None, "visible"):
            return
        data = dict(data)
        data["received_at"] = time.time()
        with self._lock:
            self._snapshot = data
            self._snapshot_at = time.time()

    def snapshot(self, max_age=3.0):
        with self._lock:
            if not self._snapshot:
                return None
            if time.time() - self._snapshot_at > float(max_age):
                return None
            return dict(self._snapshot)

    def status(self):
        snap = self.snapshot(max_age=3.0)
        return {
            "enabled": self.enabled,
            "connected": bool(snap),
            "url": (snap or {}).get("url"),
            "title": (snap or {}).get("title"),
            "site": (snap or {}).get("site"),
            "page_type": (snap or {}).get("page_type"),
        }

    def _take_pending(self):
        with self._lock:
            if not self._pending:
                return None
            # Keep command available for up to 3 seconds to survive one missed poll.
            if time.time() - self._pending.get("created_at", 0) > 3.0:
                self._pending = None
                return None
            if self._pending.get("delivered_at"):
                return None
            self._pending["delivered_at"] = time.time()
            return {k: v for k, v in self._pending.items() if k not in {"created_at", "delivered_at"}}

    def set_result(self, data):
        if not isinstance(data, dict):
            return
        cid = str(data.get("id", ""))
        if not cid:
            return
        with self._lock:
            self._results[cid] = dict(data)
            if self._pending and str(self._pending.get("id")) == cid:
                self._pending = None

    def issue(self, action, payload=None, timeout=4.0):
        if not self.enabled:
            return "UNSUPPORTED", {"detail": "bridge_disabled"}
        if not self.snapshot(max_age=5.0):
            return "UNSUPPORTED", {"detail": "extension_not_connected"}
        payload = dict(payload or {})
        with self._lock:
            self._seq += 1
            cid = str(self._seq)
            self._results.pop(cid, None)
            self._pending = {"id": cid, "action": action, "payload": payload, "created_at": time.time()}
        deadline = time.monotonic() + float(timeout)
        while time.monotonic() < deadline:
            time.sleep(0.05)
            with self._lock:
                if cid in self._results:
                    result = self._results.pop(cid)
                    ok = bool(result.get("ok"))
                    return ("CONFIRMED_SUCCESS" if ok else "FAILED"), result
        with self._lock:
            if self._pending and str(self._pending.get("id")) == cid:
                self._pending = None
        return "SENT_NOT_CONFIRMED", {"detail": "bridge_timeout"}

    def wait_for(self, predicate, timeout=5.0):
        deadline = time.monotonic() + float(timeout)
        while time.monotonic() < deadline:
            snap = self.snapshot(max_age=2.0)
            if snap:
                try:
                    if predicate(snap):
                        return snap
                except Exception:
                    pass
            time.sleep(0.10)
        return None
