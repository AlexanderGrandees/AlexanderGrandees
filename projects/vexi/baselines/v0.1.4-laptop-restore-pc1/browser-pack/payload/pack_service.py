import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from credential_store_local import CredentialStore

VERSION="0.1.2"
PROTOCOL=1

class State:
    def __init__(self,browser,port,credential_target):
        self.browser=browser; self.port=int(port); self.credential_target=credential_target
        self.lock=threading.RLock(); self.snapshot=None; self.snapshot_at=0.0
        self.extension_at=0.0; self.extension_meta={}; self.pending=None; self.results={}; self.seq=0
    def token(self): return CredentialStore().read(self.credential_target)
    def authorized(self,headers):
        t=self.token(); return bool(t and headers.get('X-Vexi-Token','')==t)
    def update_snapshot(self,data):
        if not isinstance(data,dict): return
        if data.get('visibility') not in (None,'visible'): return
        data=dict(data); data['received_at']=time.time(); data['browser']=self.browser
        with self.lock: self.snapshot=data; self.snapshot_at=time.time(); self.extension_at=time.time()
    def get_snapshot(self,max_age=3.0):
        with self.lock:
            if not self.snapshot or time.time()-self.snapshot_at>float(max_age): return None
            return dict(self.snapshot)
    def heartbeat(self,data):
        with self.lock: self.extension_at=time.time(); self.extension_meta=dict(data or {})
    def connected(self): return time.time()-self.extension_at < 5.0
    def take_pending(self):
        with self.lock:
            p=self.pending
            if not p:return None
            if time.time()-p.get('created_at',0)>8.0: self.pending=None; return None
            if p.get('delivered_at'):return None
            p['delivered_at']=time.time()
            return {k:v for k,v in p.items() if k not in {'created_at','delivered_at'}}
    def set_result(self,data):
        cid=str((data or {}).get('id') or '')
        if not cid:return
        with self.lock:
            self.results[cid]=dict(data)
            if self.pending and str(self.pending.get('id'))==cid:self.pending=None
    def issue(self,action,payload,timeout):
        if not self.connected():return 'UNSUPPORTED',{'detail':'extension_not_connected'}
        with self.lock:
            self.seq+=1; cid=str(self.seq); self.results.pop(cid,None)
            self.pending={'id':cid,'action':action,'payload':dict(payload or {}),'created_at':time.time()}
        deadline=time.monotonic()+float(timeout)
        while time.monotonic()<deadline:
            time.sleep(.04)
            with self.lock:
                if cid in self.results:
                    r=self.results.pop(cid); ok=bool(r.get('ok')); status=r.get('status') or ('CONFIRMED_SUCCESS' if ok else 'FAILED')
                    return status,r
        with self.lock:
            if self.pending and str(self.pending.get('id'))==cid:self.pending=None
        return 'SENT_NOT_CONFIRMED',{'detail':'command_timeout','id':cid}

def run(browser,port,credential_target):
    state=State(browser,port,credential_target)
    class Handler(BaseHTTPRequestHandler):
        server_version='VexiBrowserPack/0.1.2'
        def log_message(self,*args): pass
        def cors(self):
            self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Headers','Content-Type, X-Vexi-Token'); self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
        def reply(self,data,code=200):
            raw=json.dumps(data,ensure_ascii=False).encode('utf-8'); self.send_response(code); self.cors(); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def auth(self):
            if not state.authorized(self.headers): self.reply({'detail':'unauthorized'},401); return False
            return True
        def body(self):
            n=int(self.headers.get('Content-Length','0') or 0); raw=self.rfile.read(n) if n else b'{}'; return json.loads(raw.decode('utf-8'))
        def do_OPTIONS(self): self.send_response(204); self.cors(); self.end_headers()
        def do_GET(self):
            u=urlparse(self.path)
            if u.path=='/health': return self.reply({'ok':True,'component':'browser_pack','browser':browser,'version':VERSION,'protocol':PROTOCOL})
            if not self.auth():return
            if u.path=='/status':
                s=state.get_snapshot(5.0) or {}; return self.reply({'ok':True,'browser':browser,'version':VERSION,'protocol':PROTOCOL,'extension_connected':state.connected(),'site':s.get('site'),'page_type':s.get('page_type'),'url':s.get('url'),'title':s.get('title'),'snapshot_age':(time.time()-state.snapshot_at if state.snapshot_at else None)})
            if u.path=='/snapshot':
                q=parse_qs(u.query); age=float((q.get('max_age') or ['3'])[0]); return self.reply({'snapshot':state.get_snapshot(age)})
            if u.path=='/poll': return self.reply({'command':state.take_pending()})
            return self.reply({'detail':'not_found'},404)
        def do_POST(self):
            if not self.auth():return
            try:data=self.body()
            except Exception:return self.reply({'detail':'bad_json'},400)
            p=urlparse(self.path).path
            if p=='/heartbeat': state.heartbeat(data); return self.reply({'ok':True})
            if p=='/snapshot': state.update_snapshot(data); return self.reply({'ok':True})
            if p=='/result': state.set_result(data); return self.reply({'ok':True})
            if p=='/command':
                action=str(data.get('action') or ''); payload=data.get('payload') or {}; timeout=max(.3,min(12.0,float(data.get('timeout') or 5)))
                if not action:return self.reply({'status':'FAILED','result':{'detail':'missing_action'}},400)
                status,result=state.issue(action,payload,timeout); return self.reply({'status':status,'result':result})
            return self.reply({'detail':'not_found'},404)
    srv=ThreadingHTTPServer(('127.0.0.1',int(port)),Handler)
    print(f'Vexi Browser Pack {browser} v{VERSION} listening 127.0.0.1:{port}',flush=True)
    srv.serve_forever()

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--browser',required=True); ap.add_argument('--port',type=int,required=True); ap.add_argument('--credential-target',required=True); a=ap.parse_args(); run(a.browser,a.port,a.credential_target)
