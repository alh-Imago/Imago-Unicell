"""scwin_v7.py (clone of test_scwin_v6.py, ledger #1543): the browser window for the Kintex card, against a FAKE board in this process (no card, no simulator): the page and its API, the prompt (colours, Tab),
the shell commands, the refusal of pages from other sites, and the live cores panel driven through the real monitor hook in scblocks.run.
The fake board answers the card's commands (V, O, A, T, r ...) but does NOT run the jobs: far RAM reads are zeros, so a run reports wrong answers (that is expected here).
What this cannot show: that the real card's T/A replies look like the fake's (they are decoded with the same host_sc / scbatch code the real run uses).  python3 test_scwin_v7.py"""
import os, sys, json, time, struct, threading, http.client
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, scblocks, scwin_v7 as W
bad = 0
def check(name, cond):
    global bad
    print('%-110s %s' % (name, 'ok' if cond else 'FAIL'), file=sys.__stdout__); bad += (not cond)      # not sys.stdout: scblocks.main redirects it while a run is going

# ---- the pure parts
check('ansi_html: green word becomes a span with class c32, text escaped', W.ansi_html('\033[32mok <b>\033[0m x') == '<span class="c32">ok &lt;b&gt;</span> x')
check('plain strips the codes', W.plain('\033[1;32mscore> \033[0mhi') == 'score> hi')

# ---- a fake board
PLANS = []
_plan_blocks = scblocks.plan_blocks
def spy(*a, **k):
    r = _plan_blocks(*a, **k); PLANS[:] = r; return r
scblocks.plan_blocks = spy
class FakeS:
    def __init__(self): self.rx = bytearray(); self.sel = 0; self.t0 = {}
    def write(self, b):
        b = bytes(b); c = b[:1]
        if c == b'O': self.sel = b[1]
        elif c == b'J': self.t0[self.sel] = time.time()
        elif c == b'A': self.rx += self.reply_A()
        elif c == b'T': self.rx += self.reply_T()
        elif c == b'Z': self.rx += struct.pack('<HBB', 512, 9, 16)      # this fake board has 512 shared words per block
        elif c == b'r': self.rx += bytes(4)
    def flush(self): pass
    def read(self, n):
        out = bytes(self.rx[:n]); del self.rx[:n]; return out
    def reset_input_buffer(self): self.rx.clear()
    def close(self): pass
    def running(self): return self.sel in self.t0 and time.time() - self.t0[self.sel] < 1.5
    def reply_A(self):
        tag = next((bp.plan.tag for bp in PLANS if bp.block == self.sel), 0)
        busy = self.running(); b = bytearray(24); b[0] = 1 if busy else 2; b[2:4] = (3 if busy else 9).to_bytes(2, 'little'); b[4:8] = tag.to_bytes(4, 'little')
        b[8:12] = (1000 if busy else 54321).to_bytes(4, 'little'); return bytes(b)
    def reply_T(self):
        b = bytearray(8 + 4 * 4); b[0:7] = struct.pack('<HHBBB', 1, 2, 3, 2, 0)
        # slices: 0..1 a fused pair (leader 0, class 1, task 7), 2 a single job (class 2, task 8), 3 idle
        for i, (fl, cls, tid) in enumerate([(3, 1, 7), (1, 0, 0), (3, 2, 8), (0, 0, 0)]): b[8 + 4 * i: 12 + 4 * i] = struct.pack('<BBH', fl, cls, tid)
        return bytes(b)
class FakeBoard(hs.Board):
    def __init__(self, port): self.s = FakeS()
    def version(self): return dict(version=12, S=4, imem_words=128)
hs.Board = FakeBoard

# ---- the server
web = W.make_web(); port = 18776
srv = W.serve(web, port); threading.Thread(target=srv.serve_forever, daemon=True).start()
def req(method, path, body=None, headers=None, host=None):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=10); h = {'Host': host or 'localhost:%d' % port}; h.update(headers or {})
    c.request(method, path, body=json.dumps(body) if body is not None else None, headers=h); r = c.getresponse(); d = r.read(); c.close(); return r.status, d
def api(path): return json.loads(req('GET', path)[1])
def ex(line): return json.loads(req('POST', '/api/exec', {'line': line}, {'X-Score': '1'})[1])
def wait_idle(t=30):
    t0 = time.time()
    while time.time() - t0 < t:
        if not api('/api/state?since=0')['busy']: return True
        time.sleep(0.1)
    return False
try:
    st, body = req('GET', '/'); check('the page is served', st == 200 and b'S-Core window' in body and b'id="inp"' in body)
    check('a request with a foreign Host header is refused (DNS rebinding)', req('GET', '/', host='evil.example')[0] == 403)
    check('a POST without the X-Score header is refused (a page on another site cannot send it)', req('POST', '/api/exec', {'line': 'list'})[0] == 403)
    check('a POST from another origin is refused', req('POST', '/api/exec', {'line': 'list'}, {'X-Score': '1', 'Origin': 'http://evil.example'})[0] == 403)
    # the prompt
    t = api('/api/tokens?line=' + 'add%20vsum%201%20arg%3D3')
    check('tokens: add is a command, vsum a kind, 1 a number, arg=3 an option', [x[0] for x in t if x[0] != 'ws'] == ['command', 'kind', 'number', 'option'])
    check('tokens: an unknown command is marked bad', api('/api/tokens?line=foo')[0][0] == 'badcommand')
    c = api('/api/complete?line=ad'); check('Tab: "ad" offers add and addbig', c['items'] == ['add', 'addbig'])
    c = api('/api/complete?line=add%20vs'); check('Tab: kinds after add', 'vsum' in c['items'] and 'vscale' in c['items'] and 'vmax' not in c['items'])
    # commands
    check('exec returns no error', ex('add vsum 1 2 3 4')['error'] == ''); wait_idle()
    ex('add vmax seq 5 80 3'); wait_idle(); ex('add vxor 1 2 3 arg=255 lw=1'); wait_idle()
    s = api('/api/state?since=0')
    check('the log shows the typed lines and the answers', any('score&gt;' in h for n, h in s['lines']) or any('score>' in h for n, h in s['lines']))
    check('jobs panel: 3 jobs with the right answers', [j['expect'] for j in s['jobs']] == ['[10]', '[242]', '[254, 253, 252]'] and s['jobs'][2]['lw'] == 1)
    ex('make zzw_demo add 5 xor arg then sum'); wait_idle(); s = api('/api/state?since=0')
    check('make works from the window and the kind is listed', 'zzw_demo' in s['made'])
    ex('add zzw_demo 1 2 3 arg=255'); wait_idle(); s = api('/api/state?since=0'); check('the made kind gives its answer in the jobs panel', s['jobs'][-1]['expect'] == '[744]')
    ex('set blocks 1; plan'); wait_idle(); s = api('/api/state?since=0')
    check('plan panel: block 0 with its batches parsed (jobs, code and shared words)', len(s['plan']['blocks']) == 1 and s['plan']['batches'] and s['plan']['batches'][0]['imem'] == 128 and s['plan']['batches'][0]['dsh'] == 256)
    check('settings panel shows blocks = 1', s['settings']['blocks'] == '1')
    # a run on the fake board, watched live
    ex('set lw 0'); wait_idle()
    r = ex('run'); check('run starts', r['error'] == '')
    time.sleep(0.2); check('a second command while the run is going is refused with a reason', 'busy' in ex('list')['error'])
    seen = None; t0 = time.time()
    while time.time() - t0 < 15:
        s = api('/api/state?since=0')
        if s['cores'] and s['cores']['blocks'] and s['cores']['blocks'][0]['groups'] and s['cores']['active']: seen = s['cores']; break
        time.sleep(0.1)
    check('live cores: block 0 seen while running, 4 slices drawn as 3 boxes (a fused pair, one single, one idle)', seen is not None and [g['width'] for g in seen['blocks'][0]['groups']] == [2, 1, 1] and [g['state'] for g in seen['blocks'][0]['groups']] == ['running', 'running', 'idle'])
    if seen: g = seen['blocks'][0]['groups'][0]; check('live cores: the fused group carries class 1 and task 7; the queue line is read', (g['cls'], g['tid']) == (1, 7) and seen['blocks'][0]['queue']['bulk'] == 2 and seen['blocks'][0]['seq']['busy'] == 1)
    check('the run finishes', wait_idle(30)); s = api('/api/state?since=0')
    check('the host asked the board for its shared RAM size (512 on the fake) and planned with it', s['plan']['batches'] and s['plan']['batches'][0]['dsh'] == 512 and any('read from the board' in h for n, h in api('/api/state?since=0')['lines']))
    check('after the run: the board line and the clocks of block 0 were read from the output (54321 clocks)', s['board'] and s['board']['slices'] == 4 and s['clocks'].get('0', {}).get('clocks') == 54321)
    check('after the run: the cores panel stays (finished), not active', s['cores'] is not None and s['cores']['active'] is False)
    check('run count of this job set is 1 on the first run', s['runs']['no'] == 1)
    # (v4 checks on the old box labels / dimming removed: the boxes are replaced by squares in v5, ledger #1541; the dimming is kept as class sq.last, checked below)
    # (v4 checks on the old box labels / dimming removed: the boxes are replaced by squares in v5, ledger #1541; the dimming is kept as class sq.last, checked below)
    e1 = api('/api/state?since=0')['cores']['elapsed']; time.sleep(0.35); e2 = api('/api/state?since=0')['cores']['elapsed']; check('after the finish the elapsed time stops counting (ledger #1438)', e1 == e2)
    check('after the run: one "window timing" line says how many polls ran, when the first reached the card and the run time (ledger #1435)', any('window timing:' in h and 'polls;' in h and 'first poll answered' in h and 'the card says the run took' in h and 'one status read takes' in h for n, h in api('/api/state?since=0')['lines']))
    ex('run'); wait_idle(30); s = api('/api/state?since=0'); check('the same job set run again is run 2 (warm)', s['runs']['no'] == 2)
    ex('add vsum 9'); wait_idle(); ex('run'); wait_idle(30); s = api('/api/state?since=0'); check('a changed job set starts counting again at run 1', s['runs']['no'] == 1)
    check('quit does not stop the window', (ex('quit'), wait_idle())[1] and api('/api/state?since=0')['busy'] is False)

    # ---- the builds panel (ledger #1538): a store folder with fake builds, use and load from the window with a fake loader
    import tempfile, types, shutil, make_manifest_v2 as M, score_store_v1 as ST
    sd = tempfile.mkdtemp(prefix='scwin_store_'); os.environ['SCORE_SHELL_CONFIG'] = os.path.join(sd, 'cfg.json')
    HDR = '    WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints      WHS(ns)      THS(ns)  THS Failing Endpoints  THS Total Endpoints\n    -------\n'
    def mk(nb, s, ulw, imem, slack):
        p, m = M.write(nb, s, ulw, 1, imem, outdir=sd); n = m['build']; os.makedirs(os.path.join(sd, 'vivado_out_' + n), exist_ok=True)
        open(os.path.join(sd, 'vivado_out_%s' % n, n + '.bit'), 'w').write('x')
        open(os.path.join(sd, 'vivado_out_%s' % n, 'timing_summary.txt'), 'w').write(HDR + '   %.3f   0.000   %d   1000   %.3f   0.000   0   1000\n' % (slack, 0 if slack > 0 else 3, 0.04)); return n
    gb = mk(2, 8, 0, 128, 0.4); fb = mk(2, 8, 4, 128, -0.2)
    b0 = api('/api/state?since=0')['builds']; check('builds panel: the state has the repo builds (hk8s32u32n1i1024 among them), nothing chosen', any(r['name'] == 'hk8s32u32n1i1024' for r in b0['rows']) and b0['current'] is None)
    ex('store ' + sd); wait_idle(); time.sleep(0.05); web._bs = None; b1 = api('/api/state?since=0')['builds']; rows = {r['name']: r for r in b1['rows']}
    check('builds panel: after `store FOLDER` the store\'s builds appear with fit, setup slack, bit found; the failed-timing one is flagged', gb in rows and fb in rows and rows[gb]['bit'] and rows[gb]['setup'] == 0.4 and rows[fb]['timing_ok'] is False and b1['store'] == sd)
    calls = []
    def fr(cmd, **kw):
        calls.append(list(cmd))
        if cmd[0].endswith('fakeloader'): return types.SimpleNamespace(returncode=0, stdout='done 1\n', stderr='')
        return types.SimpleNamespace(returncode=0, stdout="board version {'version': 12, 'S': 8, 'imem_words': 128}\nread order 5 7 0 5 0 gave: B C A B A\nhealthy B C A B A | x\n", stderr='')
    fl = os.path.join(sd, 'fakeloader'); open(fl, 'w').write('x'); web.sh.runner = fr; web.sh.set['loader'] = fl
    ex('use ' + gb); wait_idle(); s = api('/api/state?since=0')
    check('use from the window: the chosen build shows in the panel and the settings follow it', s['builds']['current'] == gb and s['settings']['blocks'] == '2' and s['settings']['slices'] == '8' and s['settings']['imem'] == '128')
    ex('load ' + fb); wait_idle(); check('load of a failed-timing build from the window is refused and the loader is not called', not calls and any('refused: timing failed' in h for n, h in api('/api/state?since=0')['lines']))
    ex('load ' + gb); wait_idle(); check('load of the good build runs the loader (SRAM, ft232) and the first-read check, and the board matches', calls and calls[0][1:3] == ['-c', 'ft232'] and any('first-read test healthy' in h for n, h in api('/api/state?since=0')['lines']))
    check('the page has the builds panel with use and load buttons', 'id="buildsb"' in W.PAGE and "cmd(\\'use '" in W.PAGE and "cmd(\\'load '" in W.PAGE)
    check('page: a pasted list of commands is split into lines and sent one at a time, waiting while a command is going (page text only, not run in a browser)', "addEventListener('paste'" in W.PAGE and "split(/\\r?\\n/)" in W.PAGE and 'if(!s.busy)break' in W.PAGE)
    check('page: the chosen build is sorted to the top of the builds panel and the builds, cores and settings boxes have height limits so jobs and plan stay visible (page text only)', 'b.rows.sort(' in W.PAGE and '#builds{flex:0 0 auto;max-height:22vh}' in W.PAGE and '.row2{flex:1 1 150px;min-height:150px}' in W.PAGE)
    # ---- batch from the window and the squares-only cores panel (ledger #1541)
    def batch(text, keep=False): return json.loads(req('POST', '/api/batch', {'text': text, 'keep': keep}, {'X-Score': '1'})[1])
    check('batch: an empty batch is refused with a reason', 'empty' in batch('# nothing\n')['error'])
    check('batch: a POST without the X-Score header is refused', req('POST', '/api/batch', {'text': 'list'})[0] == 403)
    web.sh.jobs = []; web.sh.programs = {}
    r = batch('# design and run\nadd vsum 1 2 3 4\nadd vmax 7 99 42 13\nset blocks 1; set lw 0\nrun\nset lw 1\nrun\n', True); check('batch: starts', r['error'] == '')
    time.sleep(0.2); check('batch: a second batch while one is going is refused (busy)', 'busy' in batch('list')['error'])
    check('batch (fake board gives wrong answers, so keep-going is on): finishes', wait_idle(60)); s = api('/api/state?since=0'); logs = ' '.join(h for n, h in s['lines'])
    import re as _re; txt = _re.sub('<[^>]+>', '', logs).replace('&gt;', '>')
    check('batch: the log shows each command as it starts, both runs, and the summary line "batch: 7 commands, 2 runs"', 'batch 5> run' in txt and 'batch: 7 commands, 2 runs' in txt)
    check('batch: the run state of the window follows the last run in the batch (clocks of block 0 read, plan refilled by the second run)', s['clocks'].get('0', {}).get('clocks') == 54321 and s['plan']['batches'])
    ex('add vsum 1'); wait_idle(); ex('set lw 0'); wait_idle()
    bf = os.path.join(sd, 'win.score'); open(bf, 'w').write('add vsum 4 5\nbogus\nadd vsum 6\n'); n0 = len(web.sh.jobs)
    ex('batch ' + bf); wait_idle(); logs = ' '.join(h for n, h in api('/api/state?since=0')['lines'])
    check('`batch FILE` at the window prompt works and stops at the error (one job added, not two)', len(web.sh.jobs) == n0 + 1 and 'stopped at line 2' in logs)
    batch('add vsum 7\nbogus\nadd vsum 8\n', True); wait_idle(); check('batch with keep-going: goes on after the error', len(web.sh.jobs) == n0 + 3)
    # cores panel: squares, "used" for slices seen busy
    web.live = dict(active=False, S=4, version=12, nb=1, t0=time.time(), tend=time.time(), blocks={0: dict(ids=[0], seen={2}, a=None, T=dict(waiting_critical=0, waiting_bulk=0, running=0, hold=0, slices=[dict(leader=0, allocated=0, cls=0, tid=0)] * 4))})
    g = api('/api/state?since=0')['cores']['blocks'][0]['groups']; check('cores: an idle slice that was seen busy is reported as used, the others idle', [x['state'] for x in g] == ['idle', 'idle', 'used', 'idle'])
    check('page: the cores panel draws only squares (class sq), no per-block text, and the old box labels are gone', 'class="sq ' in W.PAGE and 'class="crow"' in W.PAGE and "waiting: '" not in W.PAGE and 'sequencer: ' not in W.PAGE)
    check('page: the Batch box has a text area, a run button, a keep-going tick and a file chooser (page text only, not run in a browser)', all(k in W.PAGE for k in ('id="batchtxt"', 'id="bgo"', 'id="bkeep"', 'id="bfile"', "'/api/batch'")))
    check('page: panels are redrawn only when their html changed (setIf), the square size comes from the column width not from the cores box, and the boxes keep a stable scrollbar gutter (page text only, not seen in a browser)', "function setIf(id,html)" in W.PAGE and "setIf('coresb',cores(s.cores,s.layout))" in W.PAGE and "$('coresb').innerHTML=" not in W.PAGE and "$('cores').parentElement.clientWidth" in W.PAGE and 'scrollbar-gutter:stable' in W.PAGE)
    # ---- the cores panel never changes size (ledger #1543)
    s = api('/api/state?since=0'); lay = s['layout']
    check('layout: the state gives the rows (blocks asked for) and the squares per row (slices) for the idle picture', lay['nb'] == int(s['settings']['blocks']) and lay['S'] >= 1)
    web.live = dict(active=False, S=4, version=12, nb=1, t0=time.time(), tend=time.time(), blocks={0: dict(ids=[0], a=None, T=None)})
    ex('set lw 0'); wait_idle(); ex('set blocks 1; run'); time.sleep(0.15)
    mid = api('/api/state?since=0'); check('the picture of the last run is kept (not cleared) at the start of the next run, so the panel does not shrink', mid['cores'] is not None or mid['busy'] is False)
    wait_idle(60)
    check('page: the cores panel draws one row per block asked for from the layout, also before any run (idle squares), same size every time (page text only, not seen in a browser)', 'function cores(c,lay)' in W.PAGE and "setIf('coresb',cores(s.cores,s.layout))" in W.PAGE and 'No run yet' not in W.PAGE.split('function cores')[1].split('function jobs')[0])
    shutil.rmtree(sd, ignore_errors=True)
    # `-f FILE`: the page is served at once and the file's commands run while it is open (ledger #1442)
    import tempfile
    ff = tempfile.NamedTemporaryFile('w', suffix='.score', delete=False); ff.write('\n'.join(['set margin 0.1'] * 300) + '\n'); ff.close()
    port2 = 18777
    threading.Thread(target=W.main, args=(['--no-browser', '--port', str(port2), '-f', ff.name],), daemon=True).start()
    def req2(path):
        c = http.client.HTTPConnection('127.0.0.1', port2, timeout=5); c.request('GET', path, headers={'Host': 'localhost:%d' % port2}); r = c.getresponse(); d = r.read(); c.close(); return r.status, d
    t0 = time.time(); first = None
    while time.time() - t0 < 20:
        try:
            st2, body2 = req2('/api/state?since=0'); sj = json.loads(body2); n2 = sum(1 for n, h in sj['lines'] if 'score&gt;' in h)
            if first is None: first = n2
            if n2 >= 300 and not sj['busy']: break
        except Exception: pass
        time.sleep(0.02)
    check('main -f: the page answers while the file is still running (%s of 300 lines done at the first answer), and all 300 commands then run' % first, first is not None and first < 300 and n2 >= 300)
    os.remove(ff.name)
finally:
    srv.shutdown()
    import glob
    for f in glob.glob(os.path.join(HERE, 'programs', 'made', 'zzw_*')): os.remove(f)
print('FAILED %d' % bad if bad else 'ALL PASSED', file=sys.__stdout__); sys.exit(1 if bad else 0)
