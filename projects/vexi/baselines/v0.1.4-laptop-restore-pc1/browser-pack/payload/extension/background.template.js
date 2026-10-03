const VEXI_PORT=8767;
const VEXI_TOKEN=__TOKEN__;
const VEXI_BROWSER="vivaldi";
const BASE=`http://127.0.0.1:${VEXI_PORT}`;
const api=(typeof browser!=='undefined')?browser:chrome;
const headers={'Content-Type':'application/json','X-Vexi-Token':VEXI_TOKEN};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function http(path,opts={}){const o={...opts,headers:{...headers,...(opts.headers||{})}};const r=await fetch(BASE+path,o);if(!r.ok)throw new Error(`http_${r.status}`);return r.json();}
function hostOf(u){try{return new URL(u).hostname.replace(/^www\./,'').toLowerCase();}catch(_){return '';}}
async function activeTab(){const tabs=await api.tabs.query({active:true,currentWindow:true});return tabs&&tabs[0]?tabs[0]:null;}
async function ensureSite(p){const url=String(p.url||'');if(!url)throw new Error('url_missing');const target=hostOf(url);let tabs=await api.tabs.query({});let match=tabs.find(t=>hostOf(t.url||'')===target);let status='CONFIRMED_SUCCESS';
  if(match){const a=await activeTab();if(a&&a.id===match.id)status='ALREADY_SATISFIED';else {await api.tabs.update(match.id,{active:true}); if(match.windowId!=null)try{await api.windows.update(match.windowId,{focused:true});}catch(_){}}}
  else match=await api.tabs.create({url,active:true}); return {ok:true,status,tab_id:match.id,url:match.url||url};}
async function sendToActive(action,payload){const tab=await activeTab();if(!tab?.id)throw new Error('active_tab_missing');try{return await api.tabs.sendMessage(tab.id,{type:'vexi_execute',action,payload});}catch(e){throw new Error('content_script_unavailable');}}
async function handle(cmd){let out;try{if(cmd.action==='ensure_site')out=await ensureSite(cmd.payload||{}); else out=await sendToActive(cmd.action,cmd.payload||{});return {id:cmd.id,ok:!!out?.ok,status:out?.status||(out?.ok?'CONFIRMED_SUCCESS':'FAILED'),...out};}catch(e){return {id:cmd.id,ok:false,status:'FAILED',detail:String(e?.message||e)};}}
let polling=false;
async function cycle(){if(polling)return;polling=true;try{await http('/heartbeat',{method:'POST',body:JSON.stringify({browser:VEXI_BROWSER,ts:Date.now()})});const d=await http('/poll');if(d.command){const r=await handle(d.command);await http('/result',{method:'POST',body:JSON.stringify(r)});}}catch(e){console.warn('[Vexi] bridge cycle failed:',e?.message||e);}finally{polling=false;}}
api.runtime.onMessage.addListener((msg,sender)=>{if(msg?.type==='vexi_snapshot'){(async()=>{try{const tab=await activeTab();if(tab?.id&&sender?.tab?.id===tab.id)await http('/snapshot',{method:'POST',body:JSON.stringify({...msg.snapshot,browser:VEXI_BROWSER,tab_id:sender.tab.id})});}catch(e){console.warn('[Vexi] snapshot post failed:',e?.message||e);}})();}});
setInterval(cycle,350);cycle();
