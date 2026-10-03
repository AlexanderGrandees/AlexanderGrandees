(() => {
  const api = (typeof browser !== 'undefined') ? browser : chrome;
  const clean = s => (s || '').replace(/\s+/g,' ').trim();
  const visible = el => {
    if (!el) return false; const r=el.getBoundingClientRect(); const s=getComputedStyle(el);
    return r.width>1 && r.height>1 && s.display!=='none' && s.visibility!=='hidden' && r.bottom>=0 && r.right>=0 && r.top<=innerHeight && r.left<=innerWidth;
  };
  const rect = el => { const r=el.getBoundingClientRect(); return {x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)}; };
  const hrefAbs = el => { try { return el.href || new URL(el.getAttribute('href')||'',location.href).href; } catch(_) { return ''; } };
  const hostname = () => location.hostname.replace(/^www\./,'').toLowerCase();
  function siteAndType(){
    const h=hostname(),p=location.pathname;
    if(h.endsWith('youtube.com')){
      if(p==='/'||p==='')return ['youtube','HOME']; if(p==='/results')return ['youtube','SEARCH_RESULTS']; if(p==='/watch')return ['youtube','VIDEO'];
      if(p.startsWith('/shorts/'))return ['youtube','SHORTS']; if(p.startsWith('/@')||p.startsWith('/channel/')||p.startsWith('/c/'))return ['youtube','CHANNEL'];
      if(p==='/playlist')return ['youtube','PLAYLIST']; if(p.includes('history'))return ['youtube','HISTORY']; if(p.includes('feed/subscriptions'))return ['youtube','SUBSCRIPTIONS']; return ['youtube','OTHER'];
    }
    if(h==='google.com'||h.endsWith('.google.com'))return ['google','PAGE']; if(h==='github.com')return ['github','PAGE']; if(h==='mail.google.com')return ['gmail','PAGE'];
    if(h==='notion.so'||h.endsWith('.notion.site'))return ['notion','PAGE']; if(h.endsWith('tradingview.com'))return ['tradingview','PAGE']; if(h.endsWith('steampowered.com'))return ['steam','PAGE'];
    return [h||'unknown','PAGE'];
  }
  function searchBox(){
    const candidates=[...document.querySelectorAll('input:not([type="password"]), textarea, [role="searchbox"], [contenteditable="true"]')];
    const scored=[];
    for(const el of candidates){ if(!visible(el))continue; const type=(el.getAttribute('type')||'').toLowerCase(); if(type && !['text','search','url',''].includes(type))continue;
      const label=clean([el.getAttribute('aria-label'),el.getAttribute('placeholder'),el.getAttribute('name'),el.id].filter(Boolean).join(' ')).toLowerCase(); let score=0;
      if(el.matches('#search, input[name="search_query"], yt-searchbox input'))score+=10; if(el.getAttribute('role')==='searchbox'||type==='search')score+=6; if(/search|поиск|найти/.test(label))score+=4;
      if(score)scored.push([score,el]); }
    scored.sort((a,b)=>b[0]-a[0]); return scored.length?scored[0][1]:null;
  }
  function ytVideoId(href){
    try { const u=new URL(href,location.href); return u.pathname==='/watch' ? (u.searchParams.get('v')||'') : ''; } catch(_) { return ''; }
  }
  function ytCardContainer(a){
    return a.closest([
      'ytd-rich-item-renderer','ytd-video-renderer','ytd-grid-video-renderer',
      'ytd-compact-video-renderer','ytd-playlist-video-renderer','ytd-rich-grid-media',
      'yt-lockup-view-model','ytm-shorts-lockup-view-model','ytd-reel-item-renderer'
    ].join(',')) || a.closest('div[class*="lockup"],div[class*="video"]') || a.parentElement;
  }
  function ytTitle(container,a){
    const selectors=[
      '#video-title','a#video-title','[id="video-title"]','h3 a[href*="/watch"]',
      'a.yt-lockup-metadata-view-model__title','.yt-lockup-metadata-view-model__title',
      'yt-lockup-metadata-view-model a[href*="/watch"]','a[href*="/watch"][title]',
      'a[href*="/watch"][aria-label]'
    ];
    for(const sel of selectors){
      const el=container?.querySelector?.(sel); if(!el)continue;
      const t=clean(el.getAttribute?.('title')||el.getAttribute?.('aria-label')||el.textContent); if(t)return t;
    }
    let t=clean(a.getAttribute('title')||a.getAttribute('aria-label')||a.textContent); if(t)return t;
    const heading=container?.querySelector?.('h1,h2,h3,h4,[role="heading"]');
    t=clean(heading?.getAttribute?.('aria-label')||heading?.textContent); if(t)return t;
    return '';
  }
  function ytChannel(container){
    const selectors=[
      'ytd-channel-name a','#channel-name a','#text.ytd-channel-name','.ytd-channel-name',
      'a[href^="/@"]','yt-content-metadata-view-model a[href^="/@"]',
      '.yt-content-metadata-view-model__metadata-row a[href^="/@"]'
    ];
    for(const sel of selectors){const el=container?.querySelector?.(sel);const t=clean(el?.textContent||el?.getAttribute?.('aria-label'));if(t)return t;}
    return '';
  }
  function ytDuration(container){
    const selectors=['ytd-thumbnail-overlay-time-status-renderer','#time-status','.ytd-thumbnail-overlay-time-status-renderer','badge-shape .yt-badge-shape__text','.yt-badge-shape__text'];
    for(const sel of selectors){const el=container?.querySelector?.(sel);const t=clean(el?.textContent);if(t&&/^\d{1,2}:\d{2}(?::\d{2})?$/.test(t))return t;}
    return '';
  }
  function ytCards(){
    // YouTube changes DOM frequently. Do not depend on one renderer/title selector.
    // Start from every watch link, then resolve the semantic card around it.
    const anchors=[...document.querySelectorAll('a[href*="/watch"]')];
    const byId=new Map();
    for(const a of anchors){
      const href=hrefAbs(a),videoId=ytVideoId(href); if(!videoId)continue;
      const container=ytCardContainer(a); if(!visible(container||a))continue;
      const title=ytTitle(container,a); if(!title)continue;
      const r=rect(container||a);
      const item={element_id:'',semantic_type:'video',role:'link',text:title,title,channel:ytChannel(container),duration:ytDuration(container),href,visible:true,rect:r,video_id:videoId};
      const old=byId.get(videoId);
      // Prefer candidates with richer metadata / larger visible card bounds.
      const score=x=>(x.title?10:0)+(x.channel?3:0)+(x.duration?2:0)+Math.min(3,(x.rect?.width||0)/200);
      if(!old||score(item)>score(old))byId.set(videoId,item);
    }
    const out=[...byId.values()].sort((a,b)=>((a.rect?.y||0)-(b.rect?.y||0))||((a.rect?.x||0)-(b.rect?.x||0)));
    out.forEach((x,i)=>{x.position=i+1;x.element_id=`yt-video-${i+1}`;});
    return out;
  }
  function genericElements(limit=160){ const out=[]; for(const el of document.querySelectorAll('a[href],button,input:not([type="password"]),textarea,[role="button"],[role="link"],[role="menuitem"],[role="searchbox"]')){
      if(out.length>=limit||!visible(el))continue; if(el.matches('input[type="password"]'))continue; const role=el.getAttribute('role')||el.tagName.toLowerCase();
      const text=clean(el.getAttribute('aria-label')||el.getAttribute('title')||el.innerText||el.value); const href=el.tagName==='A'?hrefAbs(el):''; if(!text&&!href)continue;
      out.push({element_id:`generic-${out.length+1}`,semantic_type:(el===searchBox()?'search_box':'element'),role,text,accessible_name:clean(el.getAttribute('aria-label')),href,visible:true,rect:rect(el)}); } return out; }
  function mediaState(){ const v=document.querySelector('video'); if(!v)return null; return {paused:v.paused,current_time:v.currentTime||0,duration:Number.isFinite(v.duration)?v.duration:0,volume:v.volume,muted:v.muted,playback_rate:v.playbackRate,fullscreen:!!document.fullscreenElement}; }
  function snapshot(){ const [site,page_type]=siteAndType(); const sb=searchBox(); let els=site==='youtube'?ytCards():genericElements(); if(sb)els.unshift({element_id:'search-box',semantic_type:'search_box',role:sb.getAttribute('role')||sb.tagName.toLowerCase(),text:clean(sb.value||sb.textContent),accessible_name:clean(sb.getAttribute('aria-label')||sb.getAttribute('placeholder')),visible:true,rect:rect(sb)});
    return {url:location.href,title:document.title,site,page_type,visibility:document.visibilityState,viewport:{width:innerWidth,height:innerHeight},elements:els,media:mediaState(),timestamp:Date.now()}; }
  function nativeSet(el,value){ if(el instanceof HTMLInputElement){const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')?.set;s?s.call(el,value):el.value=value;} else if(el instanceof HTMLTextAreaElement){const s=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value')?.set;s?s.call(el,value):el.value=value;} else if(el.isContentEditable){el.textContent=value;} else el.value=value; el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true})); }
  async function inputText(p){ const el=searchBox(); if(!el)throw new Error('search_box_not_found'); el.focus(); nativeSet(el,String(p.text||'')); let submitted=false;
    if(p.submit){ const ev={key:'Enter',code:'Enter',keyCode:13,which:13,bubbles:true,cancelable:true}; el.dispatchEvent(new KeyboardEvent('keydown',ev));el.dispatchEvent(new KeyboardEvent('keypress',ev));el.dispatchEvent(new KeyboardEvent('keyup',ev));
      const form=el.closest('form'); if(form?.requestSubmit){try{form.requestSubmit();submitted=true;}catch(_){}} const btn=document.querySelector('button#search-icon-legacy,button[aria-label="Search"],button[aria-label="Поиск"],button[title="Search"]'); if(!submitted&&btn){btn.click();submitted=true;} }
    return {ok:clean(el.value||el.textContent)===clean(String(p.text||'')),value:el.value||el.textContent||'',submitted}; }
  function findHref(href){ for(const a of document.querySelectorAll('a[href]')){try{if(a.href===href)return a;}catch(_){}}return null; }
  async function mediaAction(p){ const v=document.querySelector('video'); if(!v)throw new Error('media_not_found'); const op=p.op; let ok=false;
    if(op==='play'){await v.play();ok=!v.paused;} else if(op==='pause'){v.pause();ok=v.paused;} else if(op==='toggle'){if(v.paused)await v.play();else v.pause();ok=true;}
    else if(op==='seek_relative'){v.currentTime=Math.max(0,Math.min(v.duration||1e9,v.currentTime+Number(p.seconds||0)));ok=true;}
    else if(op==='set_volume'){const val=Math.max(0,Math.min(1,Number(p.value)));v.volume=val;ok=Math.abs(v.volume-val)<.03;}
    else if(op==='change_volume'){v.volume=Math.max(0,Math.min(1,v.volume+Number(p.delta||0)));ok=true;}
    else if(op==='set_rate'){const val=Math.max(.25,Math.min(2,Number(p.value)));v.playbackRate=val;ok=Math.abs(v.playbackRate-val)<.02;}
    else if(op==='mute'){v.muted=true;ok=v.muted;} else if(op==='unmute'){v.muted=false;ok=!v.muted;}
    else if(op==='set_fullscreen'){const desired=!!p.value; if(!!document.fullscreenElement===desired)ok=true; else if(desired){const b=document.querySelector('.ytp-fullscreen-button'); if(b)b.click(); else if(v.requestFullscreen)await v.requestFullscreen();} else {if(document.fullscreenElement&&document.exitFullscreen)await document.exitFullscreen(); else {const b=document.querySelector('.ytp-fullscreen-button');if(b)b.click();}} await new Promise(r=>setTimeout(r,180));ok=(!!document.fullscreenElement===desired);}
    else if(op==='captions'){const b=document.querySelector('.ytp-subtitles-button');if(b){b.click();ok=true;}} else if(op==='next'){const b=document.querySelector('.ytp-next-button');if(b){b.click();ok=true;}} else if(op==='miniplayer'){const b=document.querySelector('.ytp-miniplayer-button');if(b){b.click();ok=true;}}
    return {ok,media:mediaState()}; }
  async function execute(action,p){ if(action==='input_text')return inputText(p); if(action==='open_href'){const a=findHref(p.href);if(a){a.click();return {ok:true,detail:'clicked'}} if(p.href){location.href=p.href;return {ok:true,detail:'navigated'}} throw new Error('href_missing');}
    if(action==='navigate'){if(!p.url)throw new Error('url_missing');location.href=p.url;return {ok:true};} if(action==='read_media'){const m=mediaState();return {ok:!!m,media:m};} if(action==='media_action')return mediaAction(p); if(action==='snapshot')return {ok:true,snapshot:snapshot()}; throw new Error('unsupported_content_action'); }
  let lastJson='',lastAt=0,timer=null;
  async function post(force=false){ if(document.visibilityState!=='visible')return; const s=snapshot(),j=JSON.stringify(s); if(!force&&j===lastJson&&Date.now()-lastAt<1800)return;lastJson=j;lastAt=Date.now();try{await api.runtime.sendMessage({type:'vexi_snapshot',snapshot:s});}catch(_){} }
  api.runtime.onMessage.addListener((msg,_sender,sendResponse)=>{ if(!msg||msg.type!=='vexi_execute')return; (async()=>{try{const r=await execute(msg.action,msg.payload||{});sendResponse({ok:!!r.ok,...r,url:location.href,title:document.title,media:mediaState()});setTimeout(()=>post(true),220);}catch(e){sendResponse({ok:false,detail:String(e?.message||e),url:location.href,title:document.title,media:mediaState()});}})(); return true; });
  const schedule=()=>{clearTimeout(timer);timer=setTimeout(()=>post(false),160);}; new MutationObserver(schedule).observe(document.documentElement,{subtree:true,childList:true,attributes:false}); document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')post(true);}); setInterval(()=>post(false),1000); post(true);
})();
