// page.h -- the web page served by unicell_unit_web.ino (HTML, CSS and JavaScript in one string).
// It lives in a header ON PURPOSE: the Arduino IDE scans the .ino for C++ functions to make prototypes, and it mistakes the page's JavaScript
// (`function msg(...)`, `async function api(...)`) for C++ and injects junk lines INTO the string, which breaks the page (seen on the real board, 9 Oct 2026).
// Headers are not scanned, so the page is safe here. Do not move it back into the .ino.
#pragma once
#include <Arduino.h>

static const char PAGE[] PROGMEM = R"HTML(<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>UniCell unit</title>
<style>
:root{--bg:#10151c;--card:#1a222d;--ink:#e6edf5;--dim:#8fa3b8;--ok:#3fb950;--bad:#f85149;--acc:#58a6ff;--line:#2b3644}
@media (prefers-color-scheme:light){:root{--bg:#f4f6f9;--card:#fff;--ink:#14202e;--dim:#5b6b7e;--line:#d8dee6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0 2px}p.sub{margin:0 0 14px;color:var(--dim)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:0 0 14px}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);margin:0 0 10px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.tile{border:1px solid var(--line);border-radius:8px;padding:8px 10px}.tile b{display:block;font-size:12px;color:var(--dim);font-weight:600}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;background:var(--dim)}.ok{background:var(--ok)}.bad{background:var(--bad)}
select{width:100%;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px;font:14px system-ui,sans-serif}label{display:block;font-size:12px;color:var(--dim)}
textarea,input{width:100%;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px;font:14px ui-monospace,monospace}
textarea{min-height:110px}.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}.row>*{flex:1 1 120px}
button{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:10px 14px;font:600 14px system-ui;cursor:pointer}button.alt{background:transparent;color:var(--ink);border:1px solid var(--line)}
button:disabled{opacity:.5}table{width:100%;border-collapse:collapse;margin-top:10px;font:14px ui-monospace,monospace}td,th{text-align:right;padding:5px 8px;border-bottom:1px solid var(--line)}th{color:var(--dim);font-weight:600}
#msg{min-height:1.4em;margin-top:8px;color:var(--dim)}#msg.bad{color:var(--bad)}small{color:var(--dim)}
</style></head><body><main>
<h1>UniCell unit</h1><p class="sub" id="design"></p>
<div class="card"><h2>Status</h2><div class="tiles" id="tiles"></div></div>
<div class="card"><h2>Setup</h2>
<small>Which design is loaded on the FPGA (it must match the bitstream on the Tang) and which sensor feeds each input. Kept in the ESP32.</small>
<div class="row"><label>Design<select id="cfgdesign"></select></label></div>
<div class="row" id="cfglanes"></div>
<div class="row"><button class="alt" id="cfgsave">Save setup</button></div></div>
<div class="card"><h2>Run</h2>
<small id="lanehint"></small>
<textarea id="items" spellcheck="false"></textarea>
<div class="row"><button id="run">Run through the design</button><button class="alt" id="ex">Example</button></div>
<table id="res" hidden><thead><tr><th>#</th><th>input</th><th>result</th></tr></thead><tbody></tbody></table></div>
<div class="card"><h2>Live sensors</h2>
<small id="livehint">Reads the sensors listed in sensors.h and feeds them to the design, one sample at a time.</small>
<div class="row"><button class="alt" id="livebtn">Start live feed</button></div>
<table id="livetab" hidden><thead><tr><th style="text-align:left">sensor</th><th>loc</th><th>amount</th></tr></thead><tbody></tbody></table>
<div id="liveres"></div>
<div class="row"><label>Plot<select id="plotmode"><option value="strips">Strip chart: one band per input, plus the result</option><option value="xy">X-Y: input 1 across, input 2 up</option></select></label><label>Scale<select id="plotscale"><option value="auto">Auto (zoom to the data)</option><option value="full">Full range (0 to 65535)</option></select></label></div>
<canvas id="plot" height="260" style="width:100%;height:260px;margin-top:8px;border:1px solid var(--line);border-radius:8px" hidden></canvas></div>
<div class="card"><h2>Direct sensors (no ESP32 in the path)</h2>
<small>Wire a digital sensor (PIR or tilt switch, signal to Tang pin 72 for input 1, pin 71 for input 2; GND to GND; the pins are pulled low). The Tang then feeds the design itself, about once a millisecond, and this page only reads the result out. LED5 lights for one active sensor, LED4 for two.</small>
<div class="row"><button class="alt" id="dirbtn">Switch direct mode on</button></div>
<div id="dirout"></div></div>
<div class="card"><h2>SD card (raw blocks)</h2>
<small>Blocks below 16 are refused. Saving overwrites raw blocks on the card.</small>
<div class="row"><input id="blk" type="number" min="16" value="64" aria-label="start block"><input id="nb" type="number" min="1" max="8" value="1" aria-label="blocks"></div>
<div class="row"><button class="alt" id="sload">Load blocks into the unit</button><button class="alt" id="ssave">Save results to blocks</button><button class="alt" id="sinit">Re-init card</button></div></div>
<div class="card"><h2>Files on the ESP32's own card</h2>
<small id="fhint"></small>
<table id="ftab"><tbody></tbody></table>
<div class="row"><input id="fup" type="file"><button class="alt" id="fsend">Upload</button></div></div>
<div id="msg"></div><p><small>Design and simulate on your own computer: <a href="https://github.com/alh-Imago/Imago-Unicell" target="_blank" rel="noopener">github.com/alh-Imago/Imago-Unicell</a>, then <code>python3 nano/frontend_v1.py</code> (needs internet only to fetch it; this unit works without).</small></p></main>
<script>
const $=id=>document.getElementById(id);let lanes=1;
function msg(t,bad){const m=$('msg');m.textContent=t;m.className=bad?'bad':''}
async function api(path,body){const o=body?{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(body)}:{};
 const c=new AbortController();const tm=setTimeout(()=>c.abort(),8000);o.signal=c.signal;let r;try{r=await fetch(path,o)}catch(e){throw new Error(e.name==='AbortError'?'no answer from the ESP32 (8 s)':e.message)}finally{clearTimeout(tm)}const j=await r.json().catch(()=>({ok:false,error:'bad reply'}));if(!r.ok||j.ok===false)throw new Error(j.error||('HTTP '+r.status));return j}
function tile(l,v,ok){return '<div class="tile"><b>'+l+'</b><span class="dot '+(ok===true?'ok':ok===false?'bad':'')+'"></span>'+v+'</div>'}
async function status(){try{const s=await api('/api/status');lanes=s.lanes;$('design').textContent=s.design;$('lanehint').textContent='One item per line, '+s.laneNames+' (whole numbers, negatives allowed).';
 $('tiles').innerHTML=tile('Unit link',s.idOk?'answers (ID '+s.id+')':'no answer',s.idOk)+tile('SD card',s.sdReady&&!s.sdError?'ready':(s.sdError?'error '+s.errCode+' (cmd '+s.errCmd+', rx 0x'+s.errRx.toString(16)+')':'not ready'),s.sdReady&&!s.sdError)
 +(s.idOk?tile('Design on the Tang',s.match?'matches the Setup ('+s.loaded+')':'MISMATCH: the Tang has '+s.loaded+', Setup says '+s.design+(s.loadedKey?' -- <a href="#" id="fixd">use '+s.loadedKey+'</a>':' -- load the right bitstream'),s.match?true:(s.loadedKey?false:null)):'')+tile('Results waiting',s.capCount,null)+tile('Network',s.ip+' ('+s.rssi+' dBm)',null)+tile('Uptime',Math.floor(s.uptime/1000)+' s',null);if($('fixd'))$('fixd').onclick=async ev=>{ev.preventDefault();const c=window.CFG;const b={design:s.loadedKey};for(let i=0;i<4;i++)b['s'+i]=c.laneSensor[i];try{await api('/api/config',b);location.reload()}catch(x){msg(x.message,true)}}}catch(e){$('tiles').innerHTML=tile('Link',e.message,false)}}
$('ex').onclick=()=>{$('items').value=EXAMPLE};
$('run').onclick=async()=>{$('run').disabled=true;msg('Running...');try{const txt=$('items').value;const r=await api('/api/run',{items:txt});
 const rows=txt.trim().split(/\n+/);$('res').hidden=false;$('res').tBodies[0].innerHTML=r.results.map((v,i)=>'<tr><td>'+(i+1)+'</td><td>'+(rows[i]||'')+'</td><td>'+v+'</td></tr>').join('');msg(r.results.length+' result(s)')}catch(e){msg(e.message,true)}$('run').disabled=false;status()};
async function sd(op){if(op==='save'&&!confirm('Overwrite raw card blocks starting at '+$('blk').value+'?'))return;try{if(op==='init'){await api('/api/sdinit',{x:1})}else{await api('/api/sd',{op:op,block:$('blk').value,n:$('nb').value})}msg('SD '+op+' done')}catch(e){msg(e.message,true)}status()}
async function files(){try{const f=await api('/api/files');$('fhint').textContent=f.card?(f.used+' of '+f.total+' kB used. Names: letters, digits . - _ and space.'):'No SD card in the ESP32 (the ESP32 reads its own card on start-up: insert it and press its reset).';
 $('ftab').tBodies[0].innerHTML=f.files.map(x=>'<tr><td style="text-align:left">'+x.name+'</td><td>'+x.size+' B</td><td><a href="/files?name='+encodeURIComponent(x.name)+'">download</a></td><td><a href="#" data-del="'+x.name+'">delete</a></td></tr>').join('')}catch(e){$('fhint').textContent=e.message}}
$('ftab').onclick=async e=>{const n=e.target.dataset&&e.target.dataset.del;if(!n)return;e.preventDefault();if(!confirm('Delete '+n+'?'))return;try{await api('/api/filedel',{name:n});files()}catch(x){msg(x.message,1)}};
$('fsend').onclick=async()=>{const f=$('fup').files[0];if(!f){msg('choose a file first',1);return}msg('Uploading '+f.name+'...');try{const fd=new FormData();fd.append('file',f,f.name);const r=await fetch('/api/upload',{method:'POST',body:fd});const j=await r.json().catch(()=>({ok:false,error:'bad reply'}));if(!r.ok||j.ok===false)throw new Error(j.error||('HTTP '+r.status));msg('Uploaded '+j.bytes+' bytes');files()}catch(x){msg(x.message,1)}};
let dirOn=false;
async function dirTick(){try{const d=await api('/api/direct');dirOn=d.on;$('dirbtn').textContent=d.on?'Switch direct mode off':'Switch direct mode on';const u=d.result>>>0;
 $('dirout').innerHTML=d.on?'sensor pins: input 1 '+((d.pins&1)?'HIGH':'low')+', input 2 '+((d.pins&2)?'HIGH':'low')+'<br>design result: '+d.result+' = word amount '+(u>>>16)+' ('+((u>>>16)/8192)+' sensor(s) active), location '+(u&65535)+'<br><small>'+d.count+' results since switching on (the Tang computes them by itself)</small>':'<small>Direct mode is off.</small>'}catch(e){$('dirout').textContent=e.message}}
$('dirbtn').onclick=async()=>{try{await api('/api/direct',{on:dirOn?0:1})}catch(e){msg(e.message,true)}dirTick()};
setInterval(()=>{if(!liveOn)dirTick()},800);dirTick();
let liveOn=false,liveT=null;const HN=240,HIST=[[],[],[],[]],RES=[];
const COL=['#58a6ff','#3fb950','#d29922','#f778ba'];
const AUTO=()=>$('plotscale').value==='auto';function rng(d,min){let lo=0,hi=65535;if(d.length&&(min===1||AUTO())){lo=Math.min(...d);hi=Math.max(...d);if(hi-lo<min){const m=(hi+lo)/2;lo=m-min/2;hi=m+min/2}}return[lo,hi]}
function plot(){const cv=$('plot');if(cv.hidden)return;const dpr=window.devicePixelRatio||1,W=cv.clientWidth,H=260;cv.width=W*dpr;cv.height=H*dpr;const g=cv.getContext('2d');g.scale(dpr,dpr);const cs=getComputedStyle(document.body),ink=cs.color,dim=cs.getPropertyValue('--dim')||'#888',line=cs.getPropertyValue('--line')||'#444';g.clearRect(0,0,W,H);g.font='11px system-ui';g.lineWidth=1.5;
 const L=Math.min(lanes||1,4);
 if($('plotmode').value==='xy'&&L>=2){const a=HIST[0],b=HIST[1],n=Math.min(a.length,b.length),P=28;g.strokeStyle=line;g.strokeRect(P,6,W-P-6,H-P-6);g.fillStyle=dim;g.fillText('input 1 ->',W-70,H-6);g.fillText('input 2',2,12);
  const[ax,bx]=rng(a,200),[ay,by]=rng(b,200);const X=v=>P+(W-P-6)*(v-ax)/(bx-ax),Y=v=>6+(H-P-6)*(1-(v-ay)/(by-ay));g.fillStyle=dim;g.fillText(Math.round(ax)+' to '+Math.round(bx),P+4,H-P+10);g.fillText(Math.round(ay)+' to '+Math.round(by),P+4,20);g.beginPath();for(let i=0;i<n;i++){const x=X(a[a.length-n+i]),y=Y(b[b.length-n+i]);i?g.lineTo(x,y):g.moveTo(x,y)}g.strokeStyle=COL[0];g.stroke();
  if(n){g.fillStyle=COL[2];g.beginPath();g.arc(X(a[a.length-1]),Y(b[b.length-1]),4,0,7);g.fill()}return}
 const bands=L+1,bh=(H-4)/bands;for(let k=0;k<bands;k++){const y0=2+k*bh,d=k<L?HIST[k]:RES;let[lo,hi]=rng(d,k===L?1:200);
  g.strokeStyle=line;g.strokeRect(0.5,y0+0.5,W-1,bh-3);g.fillStyle=dim;g.fillText((k<L?'input '+(k+1):'result')+'   '+Math.round(lo)+' to '+Math.round(hi),4,y0+11);
  g.beginPath();for(let i=0;i<d.length;i++){const x=W*(i+HN-d.length)/(HN-1),y=y0+bh-5-(bh-9)*(d[i]-lo)/(hi-lo);i?g.lineTo(x,y):g.moveTo(x,y)}g.strokeStyle=COL[k%4];g.stroke()}}
$('plotmode').onchange=plot;$('plotscale').onchange=plot;addEventListener('resize',plot);
async function liveTick(){if(!liveOn)return;try{const j=await api('/api/live');$('livetab').hidden=false;$('plot').hidden=false;j.readings.forEach((r,i)=>{HIST[i].push(r.amount);if(HIST[i].length>HN)HIST[i].shift()});{const u=j.result>>>0;RES.push(/CORDIC/.test($('design').textContent)?j.result:(u>>>16));if(RES.length>HN)RES.shift()}plot();$('livetab').tBodies[0].innerHTML=j.readings.map(r=>'<tr><td style="text-align:left">'+r.name+'</td><td>'+r.loc+'</td><td>'+r.amount+'</td></tr>').join('');const u=j.result>>>0;$('liveres').textContent='design result: '+j.result+(/CORDIC/.test($('design').textContent)?'':'  = word amount '+(u>>>16)+', location '+(u&65535))+'  ('+j.ms+' ms)'}catch(e){$('liveres').textContent=e.message;liveOn=false;$('livebtn').textContent='Start live feed';return}liveT=setTimeout(liveTick,200)}
$('livebtn').onclick=()=>{liveOn=!liveOn;$('livebtn').textContent=liveOn?'Stop live feed':'Start live feed';if(liveOn)liveTick();else clearTimeout(liveT)};
$('sload').onclick=()=>sd('load');$('ssave').onclick=()=>sd('save');$('sinit').onclick=()=>sd('init');
async function loadCfg(){try{const c=await api('/api/config');window.CFG=c;$('cfgdesign').innerHTML=c.designs.map(d=>'<option value="'+d.key+'"'+(d.key===c.design?' selected':'')+'>'+d.name+'</option>').join('');drawLanes()}catch(e){msg(e.message,true)}}
function drawLanes(){const c=window.CFG;if(!c)return;const d=c.designs.find(x=>x.key===$('cfgdesign').value)||c.designs[0];let h='';for(let i=0;i<d.lanes;i++){h+='<label>Input '+(i+1)+' sensor<select id="cfgs'+i+'">'+c.sensors.map((n,k)=>'<option value="'+k+'"'+(c.laneSensor[i]===k?' selected':'')+'>'+n+'</option>').join('')+'</select></label>'}$('cfglanes').innerHTML=h}
$('cfgdesign').onchange=drawLanes;
$('cfgsave').onclick=async()=>{const c=window.CFG;if(!c)return;const d=c.designs.find(x=>x.key===$('cfgdesign').value);const b={design:d.key};for(let i=0;i<d.lanes;i++)b['s'+i]=$('cfgs'+i).value;try{await api('/api/config',b);msg('Saved');location.reload()}catch(e){msg(e.message,true)}};
let EXAMPLE='';fetch('/api/status').then(r=>r.json()).then(s=>{EXAMPLE=s.example;$('items').value=s.example});
status();setInterval(status,3000);files();loadCfg();
</script></body></html>)HTML";
