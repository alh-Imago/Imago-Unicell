#!/usr/bin/env python3
"""hexn_front_web_v1: THE FRONT END AS A WEB PAGE ON YOUR OWN PC (new file 1 Nov 2026; host side, no new hardware).
A small server (Python standard library only) that shows one page in your browser. You pick data files, say what to predict, choose the model or the real unit, press Run.
It does exactly what `tools/hexn_front_unit_v1.py` does on the command line (same fitting, same loading, same checks): nothing in the proven files is changed, this file only calls them.
Usage:  python3 tools/hexn_front_web_v1.py            then open http://127.0.0.1:8765 in a browser.   (--port-web N to change the page's port; --data DIR to list another data folder)
The server listens on THIS computer only (127.0.0.1), so nobody else on the network can reach it. One run at a time. The real unit is reached through the ESP32 gateway on a serial port (needs pyserial, as the command line does)."""
import sys, os, io, json, glob, time, tempfile, threading, argparse, traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from types import SimpleNamespace
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import numpy as np
import hexn_intake_v1 as I, hexn_c4_play_v1 as G4, hexn_front_unit_v2 as F          # v2 = v1 plus 'first_wrong' and the header warning; v1 itself is untouched

GAME = {}; GLOCK = threading.Lock()                                    # the Connect Four game of this page (one player, this PC)
LOCK = threading.Lock(); UPLOADS = tempfile.mkdtemp(prefix="hexn_web_"); DATA_DIRS = [os.path.join(ROOT, "docs", "hex-n", "data")]

def list_files():
    out = []
    for base in DATA_DIRS + [UPLOADS]:
        for ext in ("*.csv", "*.csv.gz"):
            out += glob.glob(os.path.join(base, "**", ext), recursive=True)
    return sorted(set(out))
def safe_paths(paths):
    ok = set(list_files()); bad = [p for p in paths if p not in ok]
    if bad: raise ValueError("not a listed data file: %s" % bad[0])
    if not paths: raise ValueError("choose at least one data file")
    return paths
def serial_ports():
    try:
        from serial.tools import list_ports; return sorted(p.device for p in list_ports.comports())
    except Exception: return None                                         # None = pyserial not installed
def jsonable(o):
    if isinstance(o, dict): return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [jsonable(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, float): return None if o != o else o
    return o
def inspect(paths):
    d, infos, Rl = I.load(safe_paths(paths))
    sens = [c for c in d.columns if Rl.get(c) == "sensor"]
    return {"rows": int(len(d)), "sensors": sens, "warnings": F.header_warnings(d.columns), "columns": [str(c) for c in d.columns if c != "_t"], "has_time": "_t" in d,
            "files": [{"path": os.path.basename(i["path"]), "rows": i["rows"]} for i in infos]}
def run(req):
    paths = safe_paths(req.get("files", [])); mode = req.get("task", "future")
    a = SimpleNamespace(label=None, rule=None, future=None, q=float(req.get("q", 0.9)), hours=float(req.get("hours", 6)), features="auto")
    if mode == "future": a.future = req.get("sensor") or None
    elif mode == "label": a.label = req.get("column") or None
    elif mode == "rule": a.rule = (req.get("rule") or "").strip() or None
    if not (a.future or a.label or a.rule): raise ValueError("choose the task: which sensor, column or rule")
    t0 = time.time(); pkg, rows, lab, exp = F.fit(paths, a); res = {"task": pkg["task"], "package": pkg, "fit_seconds": round(time.time() - t0, 1), "warnings": F.header_warnings(I.load(paths)[0].columns)}
    where = req.get("unit", "none")
    if where == "none": return res
    import hexn_open_host_v1 as H
    bias_b = req.get("bias_b"); bias_b = None if bias_b in (None, "", "null") else int(bias_b); max_rows = int(req.get("max_rows", 1000))
    if where == "model": import hexn_open_emu_v1 as E; link = E.EmuLink()
    else:
        port = req.get("port", "").strip()
        if not port: raise ValueError("type or choose the ESP32's serial port")
        link = H.SerialLink(port)
    try:
        u = H.OpenUnit(link); u.id(); t1 = time.time(); r = F.send_and_verify(u, pkg, rows, lab, exp, max_rows, bias_b)
    finally:
        if where != "model":
            try: link.s.close()
            except Exception: pass
    r["seconds"] = round(time.time() - t1, 1); r["where"] = "model" if where == "model" else "real unit on " + req.get("port", "")
    res["unit"] = r; return res

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(jsonable(body)).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path in ("/", "/index.html"): return self.send(200, PAGE.encode(), "text/html; charset=utf-8")
        if self.path == "/api/c4/state":
            with GLOCK:
                if "c4" not in GAME: GAME["c4"] = G4.Game(seed=int(time.time()) % 100000)
                return self.send(200, GAME["c4"].state())
        if self.path == "/api/files": return self.send(200, {"files": list_files(), "root": ROOT, "ports": serial_ports()})
        self.send(404, {"error": "not found"})
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = self.rfile.read(n)
        try:
            if self.path == "/api/upload":                                  # raw file body, name in the X-Filename header
                name = os.path.basename(self.headers.get("X-Filename", "upload.csv")) or "upload.csv"; p = os.path.join(UPLOADS, name); open(p, "wb").write(body)
                return self.send(200, {"path": p})
            req = json.loads(body or b"{}")
            if self.path in ("/api/c4/new", "/api/c4/move"):
                with GLOCK:
                    if "c4" not in GAME: GAME["c4"] = G4.Game(seed=int(time.time()) % 100000)
                    g = GAME["c4"]
                    if self.path == "/api/c4/move": g.human(int(req.get("col", -1)))
                    elif req.get("forget"): g.forget()
                    else: g.new()
                    return self.send(200, g.state())
            if self.path == "/api/inspect": return self.send(200, inspect(req.get("files", [])))
            if self.path == "/api/run":
                if not LOCK.acquire(blocking=False): return self.send(409, {"error": "another run is still going; wait for it to finish"})
                try: return self.send(200, run(req))
                finally: LOCK.release()
            self.send(404, {"error": "not found"})
        except SystemExit as e: self.send(400, {"error": str(e)})
        except Exception as e:
            traceback.print_exc(file=sys.stderr); self.send(400, {"error": "%s: %s" % (type(e).__name__, e)})

PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hex-N Front End</title>
<style>
:root{--bg:#f4f1ea;--panel:#fffdf8;--fg:#1f2a2e;--mute:#5d6a6e;--line:#d9d3c4;--acc:#0b6e69;--accfg:#fff;--ok:#1b7a3a;--bad:#b3261e;--chip:#e9e4d6;--boardbg:#2d4a73;--hole:#e8edf5;--xc:#c8352b;--oc:#e8b32a;--ghost:#e58a84}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14191b;--panel:#1b2225;--fg:#e6e9e6;--mute:#93a1a4;--line:#2d383c;--acc:#4fc3bb;--accfg:#06201e;--ok:#5fcf80;--bad:#ff8a80;--chip:#262f32;--boardbg:#1d3250;--hole:#0f1a28;--xc:#e0564b;--oc:#e8b32a;--ghost:#9a4a44;color-scheme:dark}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 60px;display:grid;gap:16px}
h1{font-size:1.5rem;margin:0}h1 small{display:block;font-size:.85rem;font-weight:400;color:var(--mute);margin-top:2px}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;min-width:0}
h2{font-size:.78rem;letter-spacing:.09em;text-transform:uppercase;color:var(--mute);margin:0 0 10px}
label{display:grid;gap:3px;font-size:.85rem;color:var(--mute)}input,select{font:inherit;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:7px 8px;min-width:0}
.row{display:flex;flex-wrap:wrap;gap:12px;align-items:end}.row>*{flex:1 1 170px}
button{font:inherit;border:0;border-radius:7px;padding:9px 16px;background:var(--acc);color:var(--accfg);cursor:pointer;font-weight:600}button.alt{background:var(--chip);color:var(--fg)}button:disabled{opacity:.5;cursor:wait}
.files{display:grid;gap:4px;max-height:200px;overflow:auto;border:1px solid var(--line);border-radius:6px;padding:8px;background:var(--bg)}.files label{display:flex;gap:8px;color:var(--fg);font-size:.85rem;align-items:center}
.msg{padding:9px 12px;border-radius:7px;background:var(--chip);color:var(--fg);overflow-wrap:anywhere}.msg.err{border-left:4px solid var(--bad)}
.big{font-size:1.25rem;font-weight:700}.ok{color:var(--ok)}.bad{color:var(--bad)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}.card{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--bg)}.card b{display:block;font-size:1.3rem}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.85rem}th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);white-space:nowrap}th{color:var(--mute);font-weight:600}
.mute{color:var(--mute);font-size:.85rem}
.tabs{display:flex;gap:8px;flex-wrap:wrap}.tabs button{background:var(--chip);color:var(--fg)}.tabs button.on{background:var(--acc);color:var(--accfg)}
.c4{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px;max-width:560px;margin:0 auto;background:var(--boardbg);padding:10px;border-radius:12px}
.c4col{display:grid;gap:6px;cursor:pointer;border-radius:8px;padding:2px}.c4col.off{cursor:default}.c4col.on:hover{outline:2px solid var(--acc)}
.c4bar{height:44px;border-radius:6px;background:var(--panel);position:relative;overflow:hidden;display:flex;align-items:flex-end;justify-content:center}
.c4bar i{position:absolute;left:0;right:0;bottom:0;background:var(--ghost);opacity:.8}.c4bar b{position:relative;font-size:.78rem;padding:2px 0;color:var(--fg)}
.cell{aspect-ratio:1;border-radius:50%;background:var(--hole);position:relative;border:3px solid transparent;box-sizing:border-box}
.cell.x{background:var(--xc)}.cell.o{background:var(--oc)}.cell.last::after{content:"";position:absolute;inset:34%;border-radius:50%;background:rgba(255,255,255,.75)}
.cell.ghost{border:3px dashed var(--xc)}.cell.win{border:3px solid var(--ok);box-shadow:0 0 0 3px var(--ok)}[hidden]{display:none!important}
</style></head><body><main>
<h1>Hex-N Front End<small>Data file → learn a table → fit it to the unit → check every answer. Runs on this PC only.</small></h1>
<div class="tabs"><button id="t_unit" class="on">Data → unit</button><button id="t_play">Play Connect Four</button></div>
<div id="tab_unit" style="display:grid;gap:16px;min-width:0">
<section><h2>1 · Data files</h2>
<div id="files" class="files">loading…</div>
<div class="row" style="margin-top:10px"><label>Add your own file (csv, csv.gz)<input type="file" id="up" multiple></label><div style="flex:0 0 auto"><button class="alt" id="load">Read the chosen files</button></div></div>
<div id="info" class="mute" style="margin-top:8px"></div><div id="warn" class="msg err" hidden style="margin-top:8px"></div></section>
<section><h2>2 · What to predict</h2>
<div class="row"><label style="flex-basis:290px">Task<select id="task"><option value="future">A sensor will cross a line soon</option><option value="label">An existing column is the answer</option><option value="rule">A rule I type</option></select></label>
<label id="l_sensor">Sensor<select id="sensor"></select></label><label id="l_col" hidden>Column<select id="column"></select></label><label id="l_rule" hidden>Rule (e.g. flow &gt; 30)<input id="rule"></label>
<label id="l_q">Line = percentile<input id="q" type="number" step="0.01" min="0.5" max="0.999" value="0.9"></label><label id="l_h">Within hours<input id="hours" type="number" step="0.5" min="0.25" value="6"></label></div></section>
<section><h2>3 · Where to run it</h2>
<div class="row"><label>Run on<select id="unit"><option value="model">Software model (no board)</option><option value="real">The real unit (through the ESP32)</option><option value="none">Fit only, do not send</option></select></label>
<label id="l_port" hidden>Serial port<input id="port" list="ports" placeholder="/dev/ttyUSB3"><datalist id="ports"></datalist></label>
<label>Rows to send (max)<input id="max_rows" type="number" min="1" value="1000"></label><label>Judge B bias (blank = one judge)<input id="bias_b" type="number" placeholder="-40"></label></div>
<div id="portnote" class="mute" hidden></div>
<div style="margin-top:12px"><button id="run">Run</button> <span id="status" class="mute"></span></div></section>
<div id="out"></div>
</div>
<div id="tab_play" hidden style="display:grid;gap:16px;min-width:0"><section><h2>Connect Four against the layer 3 / 4 models</h2>
<div class="mute">A software model running on this PC, not the board. The system plays red and moves first; you play yellow. Click a column to drop your counter.</div>
<div class="row" style="margin-top:10px"><div id="c4status" class="big" style="flex:2 1 260px"></div><div style="flex:0 0 auto;display:flex;gap:8px;flex-wrap:wrap"><button id="c4new">New game</button><button id="c4forget" class="alt">Forget what it learned</button></div></div>
<label style="display:flex;gap:8px;align-items:center;margin:10px 0;flex-direction:row;color:var(--fg)"><input type="checkbox" id="c4ov" checked> Show where the system is heading (bars and dashed rings)</label>
<div id="c4board"></div><div id="c4why" class="mute" style="margin-top:10px"></div><div id="c4stats" class="mute" style="margin-top:6px"></div></section></div>
</main><script>
const $=id=>document.getElementById(id);let selected=[];
async function api(p,body){const r=await fetch(p,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw new Error(j.error||r.status);return j}
function fill(sel,items){sel.innerHTML=items.map(x=>`<option>${x}</option>`).join('')}
async function refresh(keep){const j=await api('/api/files');const root=j.root+'/';$('files').innerHTML=j.files.length?j.files.map(f=>`<label><input type="checkbox" value="${f}" ${(keep||[]).includes(f)?'checked':''}>${f.startsWith(root)?f.slice(root.length):f}</label>`).join(''):'no data files found';
 if(j.ports===null){$('portnote').hidden=false;$('portnote').textContent='pyserial is not installed on this PC, so the real unit cannot be reached from here (the model still works).'}else{fill($('ports'),j.ports);if(j.ports.length&&!$('port').value)$('port').value=j.ports[j.ports.length-1]}}
function chosen(){return [...document.querySelectorAll('#files input:checked')].map(x=>x.value)}
$('up').onchange=async e=>{const keep=chosen();for(const f of e.target.files){const r=await fetch('/api/upload',{method:'POST',headers:{'X-Filename':f.name},body:await f.arrayBuffer()});const j=await r.json();keep.push(j.path)}await refresh(keep)};
$('load').onclick=async()=>{try{const f=chosen();const j=await api('/api/inspect',{files:f});selected=f;$('info').textContent=`${j.rows} rows · sensors: ${j.sensors.join(', ')}${j.has_time?'':' · no time column (rows treated as independent)'}`;fill($('sensor'),j.sensors);fill($('column'),j.columns);warn(j.warnings)}catch(e){$('info').textContent='Could not read: '+e.message}};
function layout(){const t=$('task').value;$('l_sensor').hidden=$('l_q').hidden=$('l_h').hidden=t!=='future';$('l_col').hidden=t!=='label';$('l_rule').hidden=t!=='rule';$('l_port').hidden=$('unit').value!=='real'}
$('task').onchange=$('unit').onchange=layout;layout();
function warn(w){$('warn').hidden=!(w&&w.length);$('warn').textContent=(w||[]).join(' ')}
const n=x=>x==null?'—':(+x).toFixed(4);
function counts(c){return `<table><tr><th>caught</th><th>missed</th><th>false alarms</th><th>correctly quiet</th></tr><tr><td>${c.caught}</td><td>${c.missed}</td><td>${c.false_alarms}</td><td>${c.correct_quiet}</td></tr></table>`}
function show(r){const p=r.package;warn(r.warnings);let h=`<section><h2>Result</h2><div class="msg">${r.task}</div><div class="cards" style="margin-top:12px"><div class="card">Training rows<b>${p.training_rows}</b></div><div class="card">Test rows<b>${p.test_rows}</b><span class="mute">${p.test_positives} positive</span></div>
<div class="card">AUC, whole-number table<b>${n(p.auc_whole_numbers)}</b><span class="mute">float, same detectors: ${n(p.auc_float_selected)}</span></div><div class="card">Detectors kept<b>${p.detectors.length} of ${p.detectors_available}</b></div></div>
<h2 style="margin-top:16px">Detectors in the 8 slots</h2><div class="tw"><table><tr><th>slot</th><th>detector</th><th>low edge</th><th>high edge</th></tr>${p.detectors.map(d=>`<tr><td>${d.slot}</td><td>${d.name}</td><td>${(+d.lo).toPrecision(4)}</td><td>${(+d.hi).toPrecision(4)}</td></tr>`).join('')}</table></div></section>`;
 if(r.unit){const u=r.unit,w=u.judge_A_wrong_vs_reference;h+=`<section><h2>Check on ${u.where==='model'?'the software model (NOT hardware)':u.where}</h2><div class="big ${w===0?'ok':'bad'}">${w===0?'Every answer matches the reference':w+' answers differ from the reference'}</div>
 <div class="mute">${u.rows_sent} rows sent (${u.positives} positive) in ${u.seconds} s · AUC from the unit's own answers ${n(u.auc_from_unit_results_A)}</div><h2 style="margin-top:12px">Judge A</h2>${counts(u.judge_A)}${u.judge_B?`<h2 style="margin-top:12px">Judge B (bias ${u.judge_B_bias})</h2>${counts(u.judge_B)}`:''}${u.first_wrong&&u.first_wrong.length?`<h2 style="margin-top:12px">First answers that differ (judge A)</h2><div class="tw"><table><tr><th>row</th><th>unit gave</th><th>reference says</th><th>bins sent (slots 0-7)</th></tr>${u.first_wrong.map(x=>`<tr><td>${x.row}</td><td>${x.got}</td><td>${x.want}</td><td>${x.bins.join(' ')}</td></tr>`).join('')}</table></div>`:''}</section>`}
 $('out').innerHTML=h}
$('run').onclick=async()=>{const f=chosen();$('run').disabled=true;$('status').textContent='working… (fitting takes a few seconds, sending to the real unit a little longer)';$('out').innerHTML='';
 try{const r=await api('/api/run',{files:f,task:$('task').value,sensor:$('sensor').value,column:$('column').value,rule:$('rule').value,q:$('q').value,hours:$('hours').value,unit:$('unit').value,port:$('port').value,max_rows:$('max_rows').value,bias_b:$('bias_b').value});$('status').textContent='done';show(r)}
 catch(e){$('status').textContent='';$('out').innerHTML=`<section><div class="msg err">${e.message}</div></section>`}finally{$('run').disabled=false}};

let c4=null,c4busy=false,c4err='';
function tab(t){$('tab_unit').hidden=t!=='unit';$('tab_play').hidden=t!=='play';$('t_unit').className=t==='unit'?'on':'';$('t_play').className=t==='play'?'on':'';if(t==='play'&&!c4)c4go('/api/c4/state')}
$('t_unit').onclick=()=>tab('unit');$('t_play').onclick=()=>tab('play');
async function c4go(path,body){c4busy=true;c4err='';c4draw();try{c4=await api(path,body)}catch(e){c4err=e.message}c4busy=false;c4draw()}
$('c4new').onclick=()=>c4go('/api/c4/new',{});$('c4forget').onclick=()=>c4go('/api/c4/new',{forget:true});$('c4ov').onchange=()=>c4draw();
function c4draw(){const b=$('c4board');if(!c4){b.innerHTML='<div class="mute">loading the game…</div>';$('c4status').textContent='';return}
 const show=$('c4ov').checked&&c4.status==='play'&&!c4busy,nx=c4.next||{},mx=Math.max(0,...Object.values(nx)),winSet=new Set((c4.win_cells||[]).map(x=>x[0]+','+x[1]));let h='<div class="c4">';
 for(let c=0;c<7;c++){const p=nx[c]||0,ok=c4.status==='play'&&!c4busy&&c4.legal.includes(c),height=c4.board[c].filter(v=>v).length;
  h+=`<div class="c4col ${ok?'on':'off'}" data-c="${c}"><div class="c4bar" title="chance the system plays column ${c+1} next">${show?`<i style="height:${Math.round(p*100)}%"></i><b>${Math.round(p*100)}%</b>`:''}</div>`;
  for(let r=5;r>=0;r--){const v=c4.board[c][r],cls=['cell',v===1?'x':v===2?'o':'',c4.last&&c4.last[0]===c&&c4.last[1]===r?'last':'',winSet.has(c+','+r)?'win':'',(show&&r===height&&p>=0.03)?'ghost':''].join(' ');
   h+=`<div class="${cls}" ${(show&&r===height&&p>=0.03)?`style="opacity:${(0.35+0.65*p/(mx||1)).toFixed(2)}"`:''}></div>`}
  h+='</div>'}
 b.innerHTML=h+'</div>';b.querySelectorAll('.c4col.on').forEach(e=>e.onclick=()=>c4go('/api/c4/move',{col:+e.dataset.c}));
 let st=c4busy?'The system is thinking…':c4.status==='play'?'Your turn (yellow)':c4.over==='human'?'You win!':c4.over==='system'?'The system wins':'A draw';if(c4err)st+=' · '+c4err;$('c4status').textContent=st;
 const lm=c4.last?` Its last move: column ${c4.moves.filter(m=>m[0]===1).slice(-1)[0][1]+1}${c4.note?' ('+c4.note+')':''}.`:'';
 $('c4why').textContent=c4.status==='play'?`Bars: the chance, in this model's estimate, that the system plays that column next, adding up what it would do after each reply you might make, weighted by how likely layer 3 thinks that reply is. ${c4.human_wins_chance>0.005?Math.round(c4.human_wins_chance*100)+'% of its guessed replies would win the game for you. ':''}Dashed rings mark where the counter would land.`+lm:lm;
 const s=c4.stats;$('c4stats').textContent=`Games this session: ${s.games} · system won ${s.system_wins} · you won ${s.human_wins} · draws ${s.draws}. It keeps what it learns about your moves from game to game until you press "Forget what it learned".`}
refresh();
</script></body></html>'''

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port-web", type=int, default=8765); ap.add_argument("--data", action="append", help="another folder to list data files from"); a = ap.parse_args()
    for d in a.data or []: DATA_DIRS.append(os.path.abspath(d))
    srv = ThreadingHTTPServer(("127.0.0.1", a.port_web), Handler); print("Hex-N front end: open http://127.0.0.1:%d in your browser (Ctrl+C to stop)" % a.port_web)
    try: srv.serve_forever()
    except KeyboardInterrupt: print("stopped")
if __name__ == "__main__": main()
