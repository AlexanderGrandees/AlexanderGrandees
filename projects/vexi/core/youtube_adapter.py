import logging
import re
import time
from difflib import SequenceMatcher
from urllib.parse import quote_plus, urlparse
from window_manager import send_hotkey


def _norm(s): return re.sub(r"\s+"," ",(s or "").lower().replace("ё","е")).strip()


class YouTubeAdapter:
    HOME="https://www.youtube.com"
    def __init__(self,browser_adapter):
        self.browser=browser_adapter
        self.last_collection=[]
        self.last_selected=None

    def bridge_connected(self,browser=None):
        st=self.browser.bridge_status(browser); return bool(st.get("connected") and st.get("site")=="youtube")
    def snapshot(self,browser=None):
        s=self.browser.structured_snapshot(browser,max_age=3.0)
        return s if s and s.get("site")=="youtube" else None
    def ensure_site(self,browser=None): return self.browser.ensure_site("youtube",self.HOME,browser)

    def search_in_page(self,query,browser=None):
        browser=browser or self.browser.preferred
        status,_=self.ensure_site(browser)
        if status not in {"CONFIRMED_SUCCESS","ALREADY_SATISFIED","SENT_NOT_CONFIRMED"}:
            return status,{}
        if not self.bridge_connected(browser):
            # Direct URL is a truthful degraded fallback when Browser Pack is absent.
            return self.search_url(query,browser)
        status,result=self.browser.pack.issue(browser,"input_text",{"semantic_type":"search_box","text":query.strip(),"submit":True},timeout=4.0)
        if status != "CONFIRMED_SUCCESS": return status,result
        snap=self.browser.pack.wait_for(browser,lambda s: s.get("site")=="youtube" and (s.get("page_type")=="SEARCH_RESULTS" or "/results" in (s.get("url") or "")),timeout=7.0)
        if not snap:return "SENT_NOT_CONFIRMED",result
        self.refresh_collection(browser)
        logging.info("ACTION youtube.search_field query=%s status=CONFIRMED_SUCCESS",query)
        return "CONFIRMED_SUCCESS",snap

    def search_url(self,query,browser=None):
        url=self.HOME+"/results?search_query="+quote_plus(query.strip())
        status,state=self.browser.open_url(url,browser); logging.info("ACTION youtube.search_url query=%s status=%s",query,status); return status,state

    def visible_videos(self,browser=None):
        snap=self.snapshot(browser)
        if not snap:return []
        out=[]
        for el in snap.get("elements") or []:
            if el.get("semantic_type")!="video":continue
            href=el.get("href") or ""
            if "/watch?v=" not in href:continue
            out.append({"title":(el.get("title") or el.get("text") or "").strip(),"channel":(el.get("channel") or "").strip(),"duration":(el.get("duration") or "").strip(),"href":href,"position":int(el.get("position") or len(out)+1),"rect":el.get("rect") or {},"section":el.get("section") or ""})
        out.sort(key=lambda x:(x.get("rect",{}).get("y",0),x.get("rect",{}).get("x",0),x["position"]))
        for i,v in enumerate(out,1):v["ordinal"]=i
        return out

    def refresh_collection(self,browser=None):
        self.last_collection=self.visible_videos(browser); return self.last_collection
    def list_visible(self,limit=7,browser=None):
        vids=self.refresh_collection(browser)
        if not vids:return "UNSUPPORTED",[],"Не вижу структурный список видео. Проверь Browser Pack для активного браузера."
        return "CONFIRMED_SUCCESS",vids[:limit],None

    @staticmethod
    def _score(query,video,channel=None):
        q=_norm(query); title=_norm(video.get("title")); ch=_norm(video.get("channel")); score=0.0
        if q:
            seq=SequenceMatcher(None,q,title).ratio(); contains=1.0 if q in title or title in q else 0.0
            words=set(q.split()); twords=set(title.split()); overlap=len(words&twords)/max(1,len(words)); score+=0.60*max(seq,contains,overlap)
        if channel:
            c=_norm(channel); cseq=SequenceMatcher(None,c,ch).ratio(); ccontains=1.0 if c and (c in ch or ch in c) else 0.0; score+=0.32*max(cseq,ccontains)
        return score

    def resolve_video(self,query="",channel=None,ordinal=None,spatial=None,browser=None):
        vids=self.refresh_collection(browser)
        if not vids:return "UNSUPPORTED",None,[]
        if ordinal is not None:
            idx=int(ordinal)-1
            return ("CONFIRMED_SUCCESS",vids[idx],vids) if 0<=idx<len(vids) else ("NOT_FOUND",None,vids)
        if spatial:
            sp=_norm(spatial)
            if "слева" in sp:return "CONFIRMED_SUCCESS",min(vids,key=lambda v:v.get("rect",{}).get("x",0)),vids
            if "справа" in sp:return "CONFIRMED_SUCCESS",max(vids,key=lambda v:v.get("rect",{}).get("x",0)),vids
            if "снизу" in sp:return "CONFIRMED_SUCCESS",max(vids,key=lambda v:v.get("rect",{}).get("y",0)),vids
            if "сверху" in sp:return "CONFIRMED_SUCCESS",min(vids,key=lambda v:v.get("rect",{}).get("y",0)),vids
            if "центр" in sp or "централь" in sp:
                snap=self.snapshot(browser) or {}; vw=(snap.get("viewport") or {}).get("width",0)/2; vh=(snap.get("viewport") or {}).get("height",0)/2
                def d(v):
                    r=v.get("rect",{}); cx=r.get("x",0)+r.get("width",0)/2; cy=r.get("y",0)+r.get("height",0)/2; return (cx-vw)**2+(cy-vh)**2
                return "CONFIRMED_SUCCESS",min(vids,key=d),vids
        scored=sorted(((self._score(query,v,channel),v) for v in vids),key=lambda x:x[0],reverse=True)
        if not scored:return "NOT_FOUND",None,vids
        best_score,best=scored[0]; second=scored[1][0] if len(scored)>1 else 0.0
        threshold=.47 if channel else .42
        if best_score<threshold:return "NOT_FOUND",None,vids
        if len(scored)>1 and second>.38 and best_score-second<.08:return "AMBIGUOUS",None,[x[1] for x in scored[:3]]
        return "CONFIRMED_SUCCESS",best,vids

    def open_video(self,query="",channel=None,ordinal=None,spatial=None,browser=None):
        browser=browser or self.browser.preferred
        status,video,candidates=self.resolve_video(query,channel,ordinal,spatial,browser)
        if status!="CONFIRMED_SUCCESS" or not video:return status,video,candidates
        cmd_status,result=self.browser.pack.issue(browser,"open_href",{"href":video["href"]},timeout=3.5)
        if cmd_status=="FAILED":return "FAILED",video,candidates
        target_id=(urlparse(video["href"]).query or "")
        snap=self.browser.pack.wait_for(browser,lambda s:s.get("site")=="youtube" and s.get("page_type")=="VIDEO",timeout=7.0)
        if snap:
            self.last_selected=video; return "CONFIRMED_SUCCESS",video,candidates
        return "SENT_NOT_CONFIRMED",video,candidates

    def media_state(self,browser=None):
        browser=browser or self.browser.preferred; snap=self.snapshot(browser)
        if snap and snap.get("media"):return snap.get("media")
        status,result=self.browser.pack.issue(browser,"read_media",{},timeout=2.0)
        return result.get("media") if status=="CONFIRMED_SUCCESS" and isinstance(result,dict) else None

    def media_action(self,op,value=None,browser=None):
        browser=browser or self.browser.preferred
        if self.bridge_connected(browser):
            payload={"op":op}
            if op=="seek_relative":payload["seconds"]=float(value or 0)
            elif op in {"set_volume","set_rate"}:payload["value"]=float(value)
            elif op=="change_volume":payload["delta"]=float(value)
            elif op=="set_fullscreen":payload["value"]=bool(value)
            status,result=self.browser.pack.issue(browser,"media_action",payload,timeout=3.5)
            if status=="CONFIRMED_SUCCESS":
                time.sleep(.15); return status,self.media_state(browser) or (result.get("media") if isinstance(result,dict) else {}) or {}
            if status=="FAILED" and op!="set_fullscreen":return status,result
        # Fullscreen fallback is an OS key targeted at the player, then verified through DOM.
        if op=="set_fullscreen":
            desired=bool(value); state=self.media_state(browser) or {}
            if bool(state.get("fullscreen"))==desired:return "ALREADY_SATISFIED",state
            ok,_=self.browser.ensure_foreground(browser)
            if not ok:return "FAILED",state
            send_hotkey("F")
            snap=self.browser.pack.wait_for(browser,lambda s: bool((s.get("media") or {}).get("fullscreen"))==desired,timeout=3.0)
            return ("CONFIRMED_SUCCESS",(snap or {}).get("media") or {}) if snap else ("SENT_NOT_CONFIRMED",state)
        mapping={"toggle":"play_pause","mute_toggle":"mute","captions":"captions","next":"next","miniplayer":"miniplayer"}
        if op in mapping:return self.player_hotkey(mapping[op],browser)
        if op=="seek_relative" and value and abs(int(value))%10==0:
            return self.player_hotkey("seek_forward_10" if value>0 else "seek_back_10",browser,repeat=max(1,abs(int(value))//10))
        return "UNSUPPORTED",{}

    def player_hotkey(self,command,browser=None,repeat=1):
        ok,state=self.browser.ensure_foreground(browser)
        if not ok:return "FAILED",state
        mapping={"play_pause":("K",),"mute":("M",),"captions":("C",),"seek_back_10":("J",),"seek_forward_10":("L",),"volume_up_5":("UP",),"volume_down_5":("DOWN",),"speed_up":("SHIFT","PERIOD"),"speed_down":("SHIFT","COMMA"),"next":("SHIFT","N"),"previous":("SHIFT","P"),"miniplayer":("I",)}
        keys=mapping.get(command)
        if not keys:return "UNSUPPORTED",state
        for _ in range(max(1,int(repeat))):send_hotkey(*keys);time.sleep(.08)
        return "SENT_NOT_CONFIRMED",self.browser.state(browser)

    @staticmethod
    def parse_seek(text):
        t=text.lower().replace("ё","е"); m=re.search(r"(?:на\s+)?(\d+)\s*(?:секунд|секунды|сек|с)\s*(вперед|вперёд|назад)",t)
        if not m:return None
        return int(m.group(1)),("forward" if m.group(2) in {"вперед","вперёд"} else "back")
