import logging
import os
import subprocess
import time
from urllib.parse import urlparse

from app_registry import BROWSERS, TRUSTED_PATHS, first_existing
from browser_pack_client import BrowserPackClient
from plugin_manager import PluginManager
from window_manager import active_window, enum_windows, focus_hwnd, matching_processes, send_hotkey


class BrowserAdapter:
    def __init__(self, registry, preferred="vivaldi", config=None, plugin_manager=None):
        self.registry=registry
        self.preferred=preferred if preferred in BROWSERS else "vivaldi"
        self.config=config or {}
        self.plugins=plugin_manager or PluginManager()
        self.pack=BrowserPackClient(self.plugins)

    def process_names(self,browser): return self.registry.process_names(browser)
    def processes(self,browser): return matching_processes(self.process_names(browser))
    def windows(self,browser):
        p=self.processes(browser); return enum_windows([x.pid for x in p]) if p else []
    def executable(self,browser):
        item=self.registry.find(browser)
        if item:
            p=item.get("path")
            if p and os.path.isfile(p): return p
        return first_existing(TRUSTED_PATHS.get(browser,[]))

    def bridge_status(self,browser=None):
        browser=browser or self.preferred
        st=self.pack.status(browser)
        snap=self.structured_snapshot(browser,max_age=3.0)
        return {**st,"connected":bool(st.get("extension_connected") and snap),"url":(snap or {}).get("url"),"title":(snap or {}).get("title"),"site":(snap or {}).get("site"),"page_type":(snap or {}).get("page_type")}

    def structured_snapshot(self,browser=None,max_age=3.0):
        return self.pack.snapshot(browser or self.preferred,max_age=max_age)

    def state(self,browser=None):
        browser=browser or self.preferred
        procs=self.processes(browser); wins=enum_windows([p.pid for p in procs]) if procs else []
        fg=active_window(); active=None
        for w in wins:
            if fg and w["hwnd"]==fg["hwnd"]: active=w; break
        if not active and wins: active=wins[0]
        tab_title=self._tab_title(browser,active.get("title","") if active else "")
        snap=self.structured_snapshot(browser,max_age=2.5)
        if snap and snap.get("title"): tab_title=str(snap.get("title") or "").strip()
        return {"browser":browser,"process_running":bool(procs),"visible_windows":wins,"active_window":active,
                "foreground":bool(active and fg and active["hwnd"]==fg["hwnd"]),"minimized":bool(active and active.get("minimized")),
                "maximized":bool(active and active.get("maximized")),"active_tab_title":tab_title,
                "active_tab_verified":bool(snap and snap.get("title")),"active_url":(snap or {}).get("url"),
                "page_type":(snap or {}).get("page_type"),"site":(snap or {}).get("site"),
                "bridge_connected":bool(snap),"window_count":len(wins)}

    def _tab_title(self,browser,title):
        if not title:return ""
        suffixes={"vivaldi":[" - Vivaldi"],"chrome":[" - Google Chrome"],"edge":[" - Microsoft Edge"],"brave":[" - Brave"],"opera":[" - Opera"],"firefox":[" — Mozilla Firefox"," - Mozilla Firefox"]}
        out=title
        for suffix in suffixes.get(browser,[]):
            if out.endswith(suffix): out=out[:-len(suffix)]; break
        out=out.strip(); generic={"vivaldi":{"vivaldi","new tab","новая вкладка"},"chrome":{"google chrome","new tab","новая вкладка"},"edge":{"microsoft edge","new tab","новая вкладка"},"brave":{"brave","new tab","новая вкладка"},"opera":{"opera","new tab","новая вкладка"},"firefox":{"mozilla firefox","firefox","new tab","новая вкладка"}}
        return "" if out.lower() in generic.get(browser,set()) else out

    def open_browser(self,browser=None):
        browser=browser or self.preferred; state=self.state(browser)
        if state["visible_windows"]:
            w=state["active_window"] or state["visible_windows"][0]
            if state["foreground"]: return "ALREADY_SATISFIED",state
            ok=focus_hwnd(w["hwnd"],restore_if_minimized=bool(w.get("minimized"))); after=self.state(browser)
            return ("CONFIRMED_SUCCESS" if ok and after["foreground"] else "SENT_NOT_CONFIRMED"),after
        exe=self.executable(browser)
        if not exe:return "NOT_FOUND",state
        try: subprocess.Popen([exe])
        except Exception as exc:
            logging.exception("Browser launch failed %s: %s",browser,exc); return "FAILED",state
        deadline=time.monotonic()+7
        while time.monotonic()<deadline:
            time.sleep(.2); after=self.state(browser)
            if after["visible_windows"]:
                w=after["active_window"] or after["visible_windows"][0]; focus_hwnd(w["hwnd"],restore_if_minimized=bool(w.get("minimized")))
                return "CONFIRMED_SUCCESS",self.state(browser)
        return "SENT_NOT_CONFIRMED",self.state(browser)

    def _structured_url_matches(self,url,browser=None):
        snap=self.structured_snapshot(browser or self.preferred,max_age=2.0)
        if not snap:return False
        try:
            a,b=urlparse(url),urlparse(snap.get("url") or "")
            return bool(a.hostname and b.hostname and a.hostname.replace("www.","")==b.hostname.replace("www.",""))
        except Exception:return False

    def ensure_site(self,site,url,browser=None):
        browser=browser or self.preferred
        status,result=self.pack.issue(browser,"ensure_site",{"site":site,"url":url},timeout=5.0)
        if status in {"CONFIRMED_SUCCESS","ALREADY_SATISFIED"}:
            snap=self.pack.wait_for(browser,lambda s: s.get("site")==site or self._host_eq(s.get("url"),url),timeout=6.0)
            if snap:return "CONFIRMED_SUCCESS",self.state(browser)
            return "SENT_NOT_CONFIRMED",self.state(browser)
        if status == "UNSUPPORTED":
            return self.open_url(url,browser)
        return status,self.state(browser)

    def open_url(self,url,browser=None):
        browser=browser or self.preferred
        if self._structured_url_matches(url,browser): return "ALREADY_SATISFIED",self.state(browser)
        exe=self.executable(browser)
        try:
            if exe: subprocess.Popen([exe,url])
            else: os.startfile(url)
            logging.info("ACTION browser.open_url browser=%s url=%s",browser,url)
        except Exception as exc:
            logging.exception("open_url failed: %s",exc); return "FAILED",self.state(browser)
        deadline=time.monotonic()+7
        while time.monotonic()<deadline:
            time.sleep(.2); state=self.state(browser)
            if self._structured_url_matches(url,browser): return "CONFIRMED_SUCCESS",state
            if state["visible_windows"] and not self.bridge_status(browser).get("installed"):
                return "SENT_NOT_CONFIRMED",state
        return "SENT_NOT_CONFIRMED",self.state(browser)

    @staticmethod
    def _host_eq(a,b):
        try:
            ha=(urlparse(a or "").hostname or "").replace("www.",""); hb=(urlparse(b or "").hostname or "").replace("www.","")
            return bool(ha and hb and ha==hb)
        except Exception:return False

    def ensure_foreground(self,browser=None):
        browser=browser or self.preferred; state=self.state(browser)
        if state["foreground"]: return True,state
        if not state["visible_windows"]:
            status,state=self.open_browser(browser)
            if status not in {"CONFIRMED_SUCCESS","ALREADY_SATISFIED"}: return False,state
        state=self.state(browser)
        if state["active_window"]:
            w=state["active_window"]; ok=focus_hwnd(w["hwnd"],restore_if_minimized=bool(w.get("minimized")))
            return bool(ok and self.state(browser)["foreground"]),self.state(browser)
        return False,state

    def hotkey(self,action,browser=None):
        browser=browser or self.preferred; ok,before=self.ensure_foreground(browser)
        if not ok:return "FAILED",before
        keys={"new_tab":("CTRL","T"),"close_tab":("CTRL","W"),"next_tab":("CTRL","TAB"),"prev_tab":("CTRL","SHIFT","TAB"),"downloads":("CTRL","J"),"history":("CTRL","H"),"refresh":("CTRL","R"),"back":("ALT","LEFT"),"forward":("ALT","RIGHT"),"fullscreen":("F11",),"zoom_in":("CTRL","PLUS"),"zoom_out":("CTRL","MINUS"),"zoom_reset":("CTRL","0")}
        if action not in keys:return "UNSUPPORTED",before
        send_hotkey(*keys[action]); time.sleep(.25); after=self.state(browser)
        logging.info("ACTION browser.%s browser=%s status=SENT_NOT_CONFIRMED",action,browser)
        return "SENT_NOT_CONFIRMED",after
