#!/usr/bin/env python3
"""scwin.py - a simple window for the S-Core board.  It runs a small web page on your own PC (nothing leaves the machine).

    python3 scwin.py /dev/ttyUSB1            then open http://localhost:8765 (the program tries to open it for you)

The page has four parts:
  1. COMMANDS - the scheduler commands, one per line (the same as sccli.py: load, send, run, hold, go, wait ...).
  2. DATA     - words to put into the shared RAM before the run, one line per block:  ADDRESS  VALUE VALUE ...   (numbers may be 0x..)
  3. RESULTS  - which shared RAM words to read back after the run (address and count), and the table of jobs.
  4. CORES    - a live picture of every core while it runs: idle or running, which program and job, its load, and the queues.
Press RUN: the data is written to the RAM, the commands are carried out, and the result words are read back.
Needs a board built with --pool 7 or --pool 8 (the live core picture needs --pool 8, version 9)."""
import sys, os, json, time, threading, argparse, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import host_sc as hs
import sccli

DEFAULT_COMMANDS = """# the demo system: library + five programs (see cli_demo/)
load cli_demo/demo.scs
send
hold
run spin 3
run fib
run sum 2
run bad
go
wait
"""
DEFAULT_DATA = "# the sum program adds the first 16 words of the shared RAM\n0  1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16\n"

class App:
    def __init__(self, session, base_dir):
        self.S, self.lock = session, threading.Lock()
        self.log, self.running, self.error = [], False, ''
        self.ram = {'addr': 0, 'words': []}
        self.last_usage = None; self.recent = None
        self.shell = sccli.Shell(session, keep_going=False)
        self.base = base_dir
        session.out = self.log.append
        session.sleep = self._sleep                  # let the live view talk to the board while a `wait` is going on
        self.t_start = time.time()

    def _sleep(self, t):
        self.lock.release()
        try: time.sleep(t)
        finally: self.lock.acquire()

    # ---- the run
    def start_run(self, req):
        if self.running: return False, 'a run is already going'
        self.running = True; self.error = ''; self.log.clear(); self.ram = {'addr': 0, 'words': []}
        threading.Thread(target=self._run, args=(req,), daemon=True).start()
        return True, ''

    def _run(self, req):
        try:
            with self.lock:
                os.chdir(self.base)
                if self.S.v is None: self.S.connect()
                # commands first up to and including `send` need the board reset before data goes in: data is written after the first `send`
                lines = [l.split('#', 1)[0].strip() for l in req.get('commands', '').splitlines()]
                lines = [l for l in lines if l]
                data = self._parse_data(req.get('data', ''))
                wrote = False
                for l in lines:
                    for part in [p.strip() for p in l.split(';') if p.strip()]:
                        self.log.append('> ' + part)
                        if self.shell.onecmd(part): raise sccli.CliError('stopped at: ' + part)
                        if self.shell.failed: raise sccli.CliError('error in: ' + part)
                        if part.split()[0] == 'send' and not wrote:
                            self._write_data(data); wrote = True
                if not wrote and data: self._write_data(data)
                a, n = num(req.get('read_addr', 0)), num(req.get('read_n', 0))
                if n > 0:
                    self.ram = {'addr': a, 'words': self.S.b.shared_read(a, n)}
                    self.log.append('read back %d words from %d' % (n, a))
        except (sccli.CliError, IOError, OSError, ValueError) as e:
            self.error = str(e); self.log.append('ERROR: ' + str(e))
        finally:
            self.shell.failed = 0; self.running = False

    @staticmethod
    def _parse_data(text):
        out = []
        for l in text.splitlines():
            l = l.split('#', 1)[0].replace(':', ' ').replace(',', ' ').split()
            if not l: continue
            out.append((num(l[0]), [num(x) & 0xFFFFFFFF for x in l[1:]]))
        return out

    def _write_data(self, data):
        for a, ws in data:
            if ws: self.S.poke(a, ws)

    # ---- live state (called by the page about twice a second)
    def state(self):
        S = self.S
        st = dict(running=self.running, error=self.error, log=list(self.log), ram=self.ram, board=None, cores=None, queue=None, jobs=[], note='')
        with self.lock:
            if S.v is not None:
                st['board'] = dict(S=S.v['S'], version=S.v['version'], code=S.v['imem_words'], shared=S.info['shared_words'] if S.info else 0)
            jobs = []
            for j, r in sorted(S.jobs.items()):
                q = r['q']; w = r.get('why')
                jobs.append(dict(job=j, name=r['name'], tid=r['tid'], state=r['state'], a0=(q['a0'] if q and r['state'] == 'done' else None),
                                 slice=(q['slot'] if q else None), clocks=((q['end'] - q['start']) & 0xFFFFFFFF if q else None), why=(w['why'] if w else None)))
            st['jobs'] = jobs
            if S.v is not None and S.v['version'] >= 9:
                try:
                    t = S.b.status(); u = S.b.usage()
                    last = self.last_usage; self.last_usage = u
                    cores = []; bytid = {r['tid']: j for j, r in S.jobs.items() if r['state'] in ('queued', 'running')}
                    for x in t['slices']:
                        i = x['slice']; tot = 100.0 * u['busy'][i] / u['cyc'] if u['cyc'] else 0.0
                        rec = None
                        if last and u['cyc'] > last['cyc']: rec = 100.0 * (u['busy'][i] - last['busy'][i]) / (u['cyc'] - last['cyc'])
                        cores.append(dict(slice=i, state='running' if x['leader'] else ('part' if x['allocated'] else 'idle'),
                                          prog=S.name_of(x['cls']) if x['leader'] else None, job=bytid.get(x['tid']) if x['leader'] else None, total=tot, recent=rec))
                    st['cores'] = cores
                    st['queue'] = dict(critical=t['waiting_critical'], bulk=t['waiting_bulk'], running=t['running'], hold=t['hold'])
                except (IOError, OSError) as e: st['note'] = 'board did not answer: %s' % e
            elif S.v is not None: st['note'] = 'the live core view needs a --pool 8 build (board version 9); this board is version %d' % S.v['version']
        return st

def num(s): return sccli.num(s)

PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>S-Core</title><style>
body{font:15px system-ui,sans-serif;margin:0;background:#f4f5f7;color:#1c2330}
header{background:#1c2330;color:#fff;padding:10px 18px;display:flex;gap:18px;align-items:baseline}
header b{font-size:18px} header span{opacity:.75}
main{display:grid;grid-template-columns:minmax(320px,1fr) minmax(360px,1.2fr);gap:14px;padding:14px}
section{background:#fff;border:1px solid #d9dde4;border-radius:8px;padding:12px}
h2{margin:0 0 8px;font-size:14px;text-transform:uppercase;letter-spacing:.06em;color:#51607a}
textarea{width:100%;box-sizing:border-box;font:13px ui-monospace,Menlo,Consolas,monospace;border:1px solid #c5ccd8;border-radius:6px;padding:6px}
button{font:inherit;padding:8px 22px;border-radius:6px;border:0;background:#1f6feb;color:#fff;cursor:pointer}
button:disabled{background:#9aa7bd;cursor:wait}
.row{display:flex;gap:10px;align-items:center;margin:8px 0} input{font:inherit;width:90px;padding:4px 6px;border:1px solid #c5ccd8;border-radius:6px}
#cores{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}
.core{border:1px solid #c5ccd8;border-radius:8px;padding:8px;background:#f7f8fa}
.core.running{background:#e6f6ea;border-color:#38a169}.core.part{background:#fff6dd;border-color:#d69e2e}
.core b{display:block;margin-bottom:2px}.bar{height:6px;background:#dfe4ec;border-radius:3px;margin-top:6px}.bar i{display:block;height:6px;background:#1f6feb;border-radius:3px}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:3px 6px;border-bottom:1px solid #edf0f5}
.trap{color:#b42318;font-weight:600}.done{color:#067647}
pre{margin:0;max-height:180px;overflow:auto;font:12px ui-monospace,Menlo,Consolas,monospace;background:#0f1520;color:#d7e0f0;padding:8px;border-radius:6px}
.err{color:#b42318;margin-top:6px}.q{margin:6px 0;color:#51607a}
</style></head><body>
<header><b>S-Core</b><span id="board">connecting…</span></header>
<main>
<div>
<section><h2>1 &middot; Commands</h2><textarea id="cmds" rows="12"></textarea></section>
<section style="margin-top:14px"><h2>2 &middot; Data into the shared RAM</h2><textarea id="data" rows="5"></textarea>
<div style="color:#51607a;font-size:12px">one block per line: address, then the values. Written right after the <code>send</code> command.</div></section>
<section style="margin-top:14px"><h2>3 &middot; Results to read back</h2>
<div class="row">from word <input id="ra" value="0"> count <input id="rn" value="8"> <button id="run">Run</button></div>
<div class="err" id="err"></div><div id="ram"></div></section>
</div>
<div>
<section><h2>Cores</h2><div class="q" id="queue"></div><div id="cores"></div><div class="q" id="note"></div></section>
<section style="margin-top:14px"><h2>Jobs</h2><table id="jobs"></table></section>
<section style="margin-top:14px"><h2>Log</h2><pre id="log"></pre></section>
</div></main>
<script>
const $=id=>document.getElementById(id);
$('cmds').value=__CMDS__; $('data').value=__DATA__;
let busy=false;
async function poll(){
  try{ const s=await (await fetch('/api/state')).json(); draw(s);}catch(e){ $('board').textContent='no connection to scwin.py'; }
  setTimeout(poll, busy?400:1000);
}
function draw(s){
  busy=s.running; $('run').disabled=s.running; $('run').textContent=s.running?'Running…':'Run';
  if(s.board) $('board').textContent=s.board.S+' cores · '+s.board.code+' code words · '+s.board.shared+' shared RAM words · board version '+s.board.version;
  $('err').textContent=s.error||''; $('note').textContent=s.note||'';
  const q=s.queue; $('queue').textContent=q?(q.running+' running · waiting: '+q.critical+' critical, '+q.bulk+' bulk'+(q.hold?' · ON HOLD':'')):'';
  $('cores').innerHTML=(s.cores||[]).map(c=>'<div class="core '+c.state+'"><b>core '+c.slice+'</b>'+(c.state=='running'?c.prog+(c.job?' · job '+c.job:''):c.state=='part'?'part of a wide job':'idle')+
     '<div class="bar"><i style="width:'+(c.recent!=null?c.recent:c.total).toFixed(0)+'%"></i></div><small>load '+(c.recent!=null?c.recent.toFixed(0)+'% now · ':'')+c.total.toFixed(0)+'% total</small></div>').join('');
  $('jobs').innerHTML='<tr><th>job</th><th>program</th><th>state</th><th>result (a0)</th><th>core</th><th>clocks</th></tr>'+s.jobs.map(j=>'<tr><td>'+j.job+'</td><td>'+j.name+'</td><td class="'+(j.state=='trap'?'trap':j.state=='done'?'done':'')+'">'+j.state+(j.why?' – '+j.why:'')+'</td><td>'+(j.a0!=null?j.a0+' (0x'+j.a0.toString(16)+')':'')+'</td><td>'+(j.slice!=null?j.slice:'')+'</td><td>'+(j.clocks!=null?j.clocks:'')+'</td></tr>').join('');
  $('log').textContent=s.log.join('\n'); $('log').scrollTop=1e9;
  const w=s.ram.words; $('ram').innerHTML=w.length?('<table><tr><th>word</th><th>value</th><th>hex</th></tr>'+w.map((v,i)=>'<tr><td>'+(s.ram.addr+i)+'</td><td>'+v+'</td><td>0x'+v.toString(16).padStart(8,'0')+'</td></tr>').join('')+'</table>'):'';
}
$('run').onclick=async()=>{ busy=true; $('run').disabled=true;
  await fetch('/api/run',{method:'POST',body:JSON.stringify({commands:$('cmds').value,data:$('data').value,read_addr:$('ra').value,read_n:$('rn').value})}); };
poll();
</script></body></html>"""

def make_handler(app):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, body, ctype):
            b = body if isinstance(body, bytes) else body.encode()
            self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(b))); self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            p = urlparse(self.path).path
            if p == '/': self._send(200, PAGE.replace('__CMDS__', json.dumps(DEFAULT_COMMANDS)).replace('__DATA__', json.dumps(DEFAULT_DATA)), 'text/html; charset=utf-8')
            elif p == '/api/state': self._send(200, json.dumps(app.state()), 'application/json')
            else: self._send(404, 'not found', 'text/plain')
        def do_POST(self):
            if urlparse(self.path).path == '/api/run':
                n = int(self.headers.get('Content-Length', 0)); req = json.loads(self.rfile.read(n) or b'{}')
                ok, msg = app.start_run(req); self._send(200 if ok else 409, json.dumps(dict(ok=ok, message=msg)), 'application/json')
            else: self._send(404, 'not found', 'text/plain')
    return H

def serve(app, port, host='127.0.0.1'):
    srv = ThreadingHTTPServer((host, port), make_handler(app)); return srv

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0]); ap.add_argument('port'); ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--http', type=int, default=8765, help='web page port (default 8765)'); ap.add_argument('--queue', type=int, default=16)
    ap.add_argument('--no-browser', action='store_true')
    a = ap.parse_args()
    S = sccli.Session(hs.Board(a.port, a.baud), queue=a.queue)
    app = App(S, HERE)
    try: S.connect()
    except Exception as e: sys.exit('cannot talk to the board: %s' % e)
    srv = serve(app, a.http); url = 'http://localhost:%d' % a.http
    print('S-Core window at', url, ' (Ctrl-C to stop)')
    if not a.no_browser:
        try: webbrowser.open(url)
        except Exception: pass
    try: srv.serve_forever()
    except KeyboardInterrupt: pass

if __name__ == '__main__': main()
