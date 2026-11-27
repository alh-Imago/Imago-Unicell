#!/usr/bin/env python3
"""scwin_v12.py - the S-Core window for the Kintex card: the shell (score_shell_v2.py) in a browser prompt, with panels for the builds, the cores, the jobs, the batch plan and the last run.
It is a clone of scwin_v11.py (ledger #1552: runs score_shell_v5, which remembers what `load` put on the card; the BUILDS panel says "on card" next to "chosen" and marks the row, so a `use` is no longer mistaken for a load, and the load button text says what it does), itself a clone of scwin_v10.py (ledger #1549: after a run has finished, every square of a block that ran steps shows as "used" (dim green); before, only a core caught busy by a poll was shown, and runs of 0.1 to 0.4 ms are never caught, so all squares stayed black), itself a clone of scwin_v9.py (ledger #1548: ONE polling loop; v9 started another loop at every Enter and every `run batch`, and two loops could fetch the same log lines, so a line could show twice, and each press added polling load), itself a clone of scwin_v8.py (ledger #1547: runs the shell of score_shell_v5.py, so `waves`, `run` in waves and jobs that read earlier answers work in the window too; while waves run the log shows one line per wave and the cores picture is the last wave), itself a clone of scwin_v7.py (ledger #1544, amended in #1545 before Alan had run it: the right column is a grid with four fixed-height rows (builds 22 vh, cores 34 vh, jobs and plan the rest, settings 12 vh), so no panel's content can change the size of another; the cores panel has a fixed pixel height worked out from the number of rows and the square size, so nothing below it can move; each row has a left bar that is green when that block's sequencer finished steps in the last run, so the blocks that ran show even when a short run leaves every square dark), itself a clone of scwin_v6.py (ledger #1543: the CORES panel keeps one fixed size, one row per block asked for and one square per slice, from the first moment: it is drawn as idle squares before any run, and the last picture stays (dimmed) while the next run of a batch is being planned and loaded instead of being cleared), itself a clone of scwin_v5.py (ledger #1542: the panels are only redrawn when their content changed, and the square size no longer depends on a box that changes size, which made the cores panel flicker open and shut and shook the right-hand column), itself a clone of scwin_v4.py (ledger #1541: the CORES panel is now only squares, one per core, coloured by what the core is doing; a BATCH box runs a pasted or loaded batch of shell commands in one go; `batch FILE` works at the prompt), itself a clone of scwin_v3.py (ledger #1540: pasted multi-line command lists run one command at a time; panel sizes so Jobs and Plan stay visible; the chosen build is listed first), itself a clone of scwin_v2.py (ledger #1538); scwin_v2.py, scwin_v3.py and scwin.py (the Tang Nano / serial window) are unchanged.
New in v3: the BUILDS panel (what is in your store folder, what fits the card, timing, bitstream found; buttons `use` and `load` type the same commands as the prompt, so every check of the shell applies).

    nix shell nixpkgs#openocd --command python3 scwin_v12.py        then open http://localhost:8766  (the program tries to open it for you)
    python3 scwin_v12.py                                           without the card: add, make, show, plan, save, open all work; run says openocd is missing

The page has:  PROMPT (left): the same commands as the shell (type `help`); the line is coloured as you type, Tab completes, Up/Down is the history.
               CORES: while a run is going, every slice of every block read from the card's status (T) and its sequencer (A): idle, running (a fused group is one wide box),
                      class and task number, the queues, steps and clocks so far.  The picture is a snapshot about four times a second, not a recording.
               JOBS: the job list with the right answers, and MATCH / DIFFERENT after a run.     PLAN: the batches (jobs, code and shared words).     SETTINGS and the last run.
The window talks only to this program on your own PC (127.0.0.1); pages from other sites are refused.  One command at a time: while a run is going, other commands wait."""
import os, sys, re, json, time, glob, hashlib, argparse, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import score_shell_v5 as S, score_store_v1 as ST

ANSI_RE = re.compile(r'\x1b\[([0-9;]*)m')
def esc(t): return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def ansi_html(line):
    """a line with ANSI colour codes -> HTML spans (class c31 red, c32 green, c33 yellow, c35 magenta, c36 cyan, c2 dim, c1 bold)"""
    out, pos, open_ = [], 0, False
    for m in ANSI_RE.finditer(line):
        out.append(esc(line[pos:m.start()])); pos = m.end()
        if open_: out.append('</span>'); open_ = False
        code = m.group(1)
        if code not in ('', '0'): out.append('<span class="c%s">' % code.replace(';', '_')); open_ = True
    out.append(esc(line[pos:]))
    if open_: out.append('</span>')
    return ''.join(out)
def plain(line): return ANSI_RE.sub('', line)

RE_VERDICT = re.compile(r'^job (\d+)\b.*\b(MATCH|DIFFERENT)\s*$')
RE_CORRECT = re.compile(r'(\d+) of (\d+) jobs (?:correct|match)')
RE_CLOCKS = re.compile(r'block (\d+): (\d+) jobs, (\d+) steps, (\d+) clocks = ([\d.]+) ms')
RE_BOARD = re.compile(r'board version (\d+), (\d+) slices per block, (\d+) code words; (\d+) blocks')
RE_BLOCK = re.compile(r'^block (\d+): (\d+) jobs \(([^)]*)\), far RAM')
RE_BATCH = re.compile(r'^batch (\d+):\s+(\d+) jobs \(([^)]*)\), code (\d+)/(\d+) words, shared (\d+)/(\d+) words')
RE_ORDER = re.compile(r'^block (\d+) batch (\d+) submit order: (.*)$')
JOB_CMDS = {'add', 'remove', 'dup', 'clear', 'new', 'open'}

class Log:
    """what the shell prints: kept as lines (HTML) with a running number, and read for the facts the panels show"""
    def __init__(self, web): self.web = web; self.buf = ''
    def write(self, s):
        self.buf += s
        while '\n' in self.buf:
            line, self.buf = self.buf.split('\n', 1); self.web.add_line(line)
    def flush(self): pass

class WebShell(S.Shell):
    def __init__(self, web):
        S.Shell.__init__(self, out=Log(web)); self.web = web
    def _call_scblocks(self, args):
        import scblocks, io, contextlib
        buf = io.StringIO()
        mon = None if '--plan' in args else self.web.monitor
        with contextlib.redirect_stdout(buf): rc = scblocks.main(args, monitor=mon)
        return rc, buf.getvalue()
    def before_command(self, cmd): self.web.reset_for(cmd)
    def do_quit(self, a): self.say('close the browser tab to leave; Ctrl-C in the terminal stops the window program')

class Web:
    def __init__(self):
        self.lock = threading.RLock()
        self.lines = []; self.n = 0
        self.busy = False; self.cmd = ''
        self.verdict = {}; self.summary = None; self.clocks = {}; self.board = None
        self.plan = {'blocks': [], 'batches': [], 'orders': []}
        self.live = None; self.tm = None; self.last_poll = {}; self.runs = {}; self.run_key = None; self.run_no = 0; self.run_started = None
        self.exp_cache = (None, [])
        self.sh = WebShell(self)
    # ---------------- what the shell printed
    def add_line(self, line):
        with self.lock:
            p = plain(line).strip()
            m = RE_VERDICT.match(p)
            if m: self.verdict[int(m.group(1))] = m.group(2)
            m = RE_CORRECT.search(p)
            if m: self.summary = (int(m.group(1)), int(m.group(2)))
            m = RE_CLOCKS.search(p)
            if m: self.clocks[int(m.group(1))] = dict(jobs=int(m.group(2)), steps=int(m.group(3)), clocks=int(m.group(4)), ms=float(m.group(5)))
            m = RE_BOARD.search(p)
            if m: self.board = dict(version=int(m.group(1)), slices=int(m.group(2)), code=int(m.group(3)), blocks=int(m.group(4)))
            m = RE_BLOCK.match(p)
            if m: self.plan['blocks'].append(dict(block=int(m.group(1)), jobs=int(m.group(2)), ids=m.group(3)))
            m = RE_BATCH.match(p)
            if m: self.plan['batches'].append(dict(batch=int(m.group(1)), jobs=int(m.group(2)), kinds=m.group(3), code=int(m.group(4)), imem=int(m.group(5)), shared=int(m.group(6)), dsh=int(m.group(7)), block=(self.plan['blocks'][-1]['block'] if self.plan['blocks'] else 0)))
            m = RE_ORDER.match(p)
            if m: self.plan['orders'].append(dict(block=int(m.group(1)), batch=int(m.group(2)), order=m.group(3)))
            self.n += 1; self.lines.append((self.n, ansi_html(line)))
            if len(self.lines) > 4000: del self.lines[:1000]
    # ---------------- commands
    def exec(self, line):
        """start a command in a thread; returns an error text or ''"""
        with self.lock:
            if self.busy: return 'busy: %s is still going; wait for it to finish' % (self.cmd or 'a command')
            self.busy = True; self.cmd = line.strip().split(' ')[0] if line.strip() else ''
        self.add_line(S.paint('1;32', 'score> ') + esc_keep(line))
        first = line.strip().split(None, 1)[0].lower() if line.strip() else ''
        with self.lock:
            if first in ('plan', 'run'): self.plan = {'blocks': [], 'batches': [], 'orders': []}
            if first == 'run': self.verdict = {}; self.summary = None; self.clocks = {}      # self.live is kept: the picture of the last run stays until the next plan replaces it (ledger #1543)
            elif first in JOB_CMDS: self.verdict = {}; self.summary = None
        def work():
            try: self.sh.run_lines(line)
            except Exception as e: self.add_line(S.red('error: %s: %s' % (type(e).__name__, e)))
            finally:
                with self.lock:
                    self.busy = False
                    if self.live: self.live['active'] = False; self.live.setdefault('tend', time.time())
        threading.Thread(target=work, daemon=True).start()
        return ''
    def reset_for(self, first):
        """clear the panels a command is about to refill; called for every command, also those inside a batch (ledger #1541)"""
        with self.lock:
            if first in ('plan', 'run'): self.plan = {'blocks': [], 'batches': [], 'orders': []}
            if first == 'run': self.verdict = {}; self.summary = None; self.clocks = {}      # self.live is kept: the picture of the last run stays until the next plan replaces it (ledger #1543)
            elif first in JOB_CMDS: self.verdict = {}; self.summary = None
    def exec_batch(self, text, keep=False):
        """run a batch of shell commands (the Batch box); one command at a time like exec. Returns an error text or ''"""
        n = len([l for l in text.split('\n') if l.strip() and not l.strip().startswith('#')])
        if not n: return 'the batch is empty'
        with self.lock:
            if self.busy: return 'busy: %s is still going; wait for it to finish' % (self.cmd or 'a command')
            self.busy = True; self.cmd = 'batch'
        self.add_line(S.paint('1;32', 'batch> ') + 'from the Batch box (%d lines)%s' % (n, ', keep going after errors' if keep else ''))
        def work():
            try: self.sh.run_script(text, stop=not keep, label='batch')
            except Exception as e: self.add_line(S.red('error: %s: %s' % (type(e).__name__, e)))
            finally:
                with self.lock:
                    self.busy = False
                    if self.live: self.live['active'] = False; self.live.setdefault('tend', time.time())
        threading.Thread(target=work, daemon=True).start()
        return ''
    # ---------------- the watcher called from scblocks.run during a run
    def monitor(self, event, **kw):
        now = time.time()
        if event == 'plan':
            v = kw['version']
            with self.lock:
                self.run_key = hashlib.md5(json.dumps([self.sh.doc(), {k: v2 for k, v2 in self.sh.set.items() if k != 'out'}], sort_keys=True, default=str).encode()).hexdigest()
                self.runs[self.run_key] = self.runs.get(self.run_key, 0) + 1; self.run_no = self.runs[self.run_key]
                self.run_started = now
                self.live = dict(active=True, S=v['S'], version=v['version'], nb=len(kw['plans']), blocks={bp.block: dict(ids=list(bp.task_ids)) for bp in kw['plans']}, t0=now)
            return
        if self.live is None: return
        if event == 'start': self.tm = dict(start=now, polls=[]); return          # timing of the run, for the line printed at the finish (ledger #1435)
        if event == 'poll':
            blk = kw['block']; a = kw['a']
            if getattr(self, 'tm', None) is not None: self.tm['polls'].append((now - self.tm['start'], blk, bool(a.get('busy')), bool(a.get('done'))))
            if now - self.last_poll.get(blk, 0) < 0.25: return
            self.last_poll[blk] = now
            t = kw['board'].status()                          # the card's status (T) for the block the poll just selected
            with self.lock:
                self.live['blocks'][blk].update(a=kw['a'], T=t, ts=now)
                if t:
                    sn = self.live['blocks'][blk].setdefault('seen', set())
                    for i_, x_ in enumerate(t['slices']):
                        if x_['leader'] or x_['allocated']: sn.add(i_)
        elif event == 'finish':
            with self.lock:
                for blk, a in kw['done'].items(): self.live['blocks'].setdefault(blk, {})['a'] = a
                self.live['active'] = False; self.live.setdefault('tend', now)
            self.timing_line(kw)
    def timing_line(self, kw):
        """one measured line after a run: when the polls reached the card against how long the run itself took"""
        tm = getattr(self, 'tm', None)
        if not tm or not tm['polls']: return
        try:
            t1 = time.time(); kw['board'].status(); rt = (time.time() - t1) * 1000.0               # one T read = one round trip to the card
            first = tm['polls'][0]; clk = [a.get('clk') for a in kw['done'].values() if a.get('clk') is not None]
            run_ms = (1000.0 * max(clk) / 50_000_000) if clk else None
            seen_busy = sum(1 for p in tm['polls'] if p[2])
            self.add_line(S.paint('2', 'window timing: %d polls; first poll answered %.0f ms after the start command and found it %s; polls that found it busy: %d; the card says the run took %s; one status read takes %.1f ms'
                          % (len(tm['polls']), first[0] * 1000.0, 'done' if first[3] and not first[2] else 'busy' if first[2] else 'not done and not busy', seen_busy, ('%.2f ms' % run_ms) if run_ms is not None else 'unknown', rt)))
        except Exception: pass
    # ---------------- state for the page
    def expected(self):
        if self.busy and self.exp_cache[0] is not None: return self.exp_cache[1]     # not while a command is running (it may be registering programs)
        key = json.dumps([self.sh.jobs, list(self.sh.programs)], sort_keys=True, default=str)
        if self.exp_cache[0] != key:
            rows = []
            try:
                for t in self.sh.tasks(): rows.append(t.expected())
            except Exception: rows = []
            self.exp_cache = (key, rows)
        return self.exp_cache[1]
    @staticmethod
    def short(ws, n=6):
        ws = list(ws); return ('[%s]' % ', '.join(str(x) for x in ws)) if len(ws) <= n else '[%s ... %s] (%d words)' % (', '.join(str(x) for x in ws[:3]), ', '.join(str(x) for x in ws[-2:]), len(ws))
    def jobs_state(self):
        exp = self.expected(); out = []
        for i, j in enumerate(self.sh.jobs):
            ins = j['inputs'] if isinstance(j.get('inputs'), list) else ([(j['inputs']['seq'][0] + k * j['inputs']['seq'][2]) & 0xFFFFFFFF for k in range(j['inputs']['seq'][1])] if isinstance(j.get('inputs'), dict) else [])
            out.append(dict(i=i, kind=j['kind'], lw=j.get('lw'), arg=j.get('arg'), crit=bool(j.get('crit')), inputs=self.short(ins), expect=self.short(exp[i]) if i < len(exp) else '', verdict=self.verdict.get(i)))
        return out
    def cores_state(self):
        L = self.live
        if not L: return None
        blocks = []
        for blk in sorted(L['blocks']):
            b = L['blocks'][blk]; t = b.get('T'); a = b.get('a'); sl = []
            groups = []
            ran = (not L['active']) and bool(a) and (a.get('steps') or 0) > 0 and not a.get('err')      # the block's own sequencer says it ran: the card does not keep which slices
            if ran and not t: groups = [dict(start=i, width=1, state='used', cls=None, tid=None) for i in range(int(L['S']))]
            if t:
                s = t['slices']; i = 0
                while i < len(s):
                    x = s[i]
                    if x['leader']:
                        j = i + 1
                        while j < len(s) and s[j]['allocated'] and not s[j]['leader']: j += 1
                        groups.append(dict(start=i, width=j - i, state='running', cls=x['cls'], tid=x['tid'])); i = j
                    elif x['allocated']: groups.append(dict(start=i, width=1, state='held', cls=None, tid=None)); i += 1
                    else: groups.append(dict(start=i, width=1, state=('used' if (i in b.get('seen', ()) or ran) else 'idle'), cls=None, tid=None)); i += 1
            blocks.append(dict(block=blk, jobs=len(b['ids']), groups=groups,
                               queue=(dict(critical=t['waiting_critical'], bulk=t['waiting_bulk'], running=t['running'], hold=t['hold']) if t else None),
                               seq=(dict(busy=a['busy'], done=a['done'], err=a['err'], steps=a['steps'], clk=a.get('clk')) if a else None)))
        return dict(active=L['active'], S=L['S'], version=L['version'], elapsed=round(L.get('tend', time.time()) - L['t0'], 1), blocks=blocks)
    def builds_state(self):
        """the builds panel: the store's builds with fit and timing (cached 3 s: it reads folders)"""
        now = time.time(); store = self.sh.cfg.get('store')
        c = getattr(self, '_bs', None)
        if c and c[0] == store and now - c[1] < 3: rows = c[2]
        else:
            rows = []
            for b in ST.find_builds(store):
                ok, text = ST.timing_verdict(b); f = b['fits']['kintex_xc7k480t']
                rows.append(dict(name=b['name'], blocks=b['blocks'], slices=b['slices'], lanes=b['lanes'], imem=b['imem'], luts=b['luts'], predicted=b['predicted'],
                                 setup=(round(b['timing']['setup'], 3) if b['timing'] else None), timing_ok=ok, fit=f['fit'], bit=bool(b['bit']), card=(b['card'] or '')[:60]))
            self._bs = (store, now, rows)
        cur = self.sh.build['name'] if self.sh.build else None
        return dict(store=store, current=cur, oncard=getattr(self.sh, 'card_build', None), rows=rows)
    def state(self, since):
        with self.lock:
            sh = self.sh
            return dict(busy=self.busy, cmd=self.cmd, n=self.n, lines=[(n, h) for n, h in self.lines if n > since], settings={k: ('none' if v is None else ('on' if v is True else 'off' if v is False else str(v))) for k, v in sh.set.items()},
                        name=sh.name, dirty=sh.dirty, jobs=self.jobs_state(), summary=self.summary, clocks=self.clocks, board=self.board, plan=self.plan,
                        builds=self.builds_state(), cores=self.cores_state(), layout=dict(nb=max(1, int(sh.set['blocks'] or 1)), S=int((self.board or {}).get('slices') or sh.set['slices'] or 1)), runs=dict(no=self.run_no), programs=list(sh.programs), made=S.made_names())
    # ---------------- helpers for the prompt
    def complete(self, line):
        items = S.completions(self.sh, line)
        word = '' if (not line or line.endswith(' ')) else line.split()[-1]
        return dict(word=word, items=sorted(x for x in set(items) if x.startswith(word)))
    def tokens(self, line): return [[s, t] for s, t in S.tokenize(self.sh, line)]

def esc_keep(line):
    """the typed line shown in the log with the colours the live prompt would give it"""
    return S.render(WEB_FOR_RENDER[0], line) if WEB_FOR_RENDER else line
WEB_FOR_RENDER = []

PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>S-Core window</title>
<style>
:root{color-scheme:dark;--bg:#10151c;--panel:#17202b;--line:#263344;--tx:#d7dee8;--dim:#7d8b9c;--g:#5fd38d;--r:#ff6b6b;--y:#e8c75a;--c:#5cc8e0;--m:#c792ea}
*{box-sizing:border-box} .box{scrollbar-gutter:stable} body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 ui-monospace,Menlo,Consolas,monospace}
header{display:flex;gap:16px;align-items:center;padding:8px 14px;border-bottom:1px solid var(--line)} header b{color:var(--g)} #st{color:var(--dim)} #busy{color:var(--y)}
main{display:grid;grid-template-columns:minmax(420px,1.15fr) minmax(380px,1fr);gap:10px;padding:10px;height:calc(100vh - 44px)}
.col{display:flex;flex-direction:column;gap:10px;min-height:0}
.box{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:8px 10px;min-height:0;overflow:auto} .box h2{font-size:12px;margin:0 0 6px;color:var(--dim);font-weight:normal;letter-spacing:.06em;text-transform:uppercase}
#term{flex:1;display:flex;flex-direction:column;overflow:hidden} #log{flex:1;overflow:auto;white-space:pre-wrap;word-break:break-word} #pw{position:relative;margin-top:6px;border-top:1px solid var(--line);padding-top:6px}
#hl,#inp{font:inherit;padding:0 0 0 70px;margin:0;border:0;width:100%;background:transparent;white-space:pre;outline:0} #hl{position:absolute;left:0;top:6px;pointer-events:none;color:var(--tx)} #inp{position:relative;color:transparent;caret-color:var(--tx)}
#ps{position:absolute;left:0;top:6px;color:var(--g);font-weight:bold} #cand{color:var(--dim);min-height:1.4em;white-space:pre-wrap}
.c31,.s-badcommand{color:var(--r)} .c32,.s-command{color:var(--g)} .c33,.s-number{color:var(--y)} .c35,.s-option{color:var(--m)} .c36,.s-kind{color:var(--c)} .c2{color:var(--dim)} .c1,.c1_32{font-weight:bold} .c1_32{color:var(--g)}
table{border-collapse:collapse;width:100%} td,th{padding:2px 6px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top} th{color:var(--dim);font-weight:normal}
.ok{color:var(--g)} .bad{color:var(--r)} .blk{margin-bottom:8px} .crow{display:flex;flex-wrap:wrap;gap:3px;margin-bottom:4px;border-left:3px solid transparent;padding-left:4px;overflow:hidden} .crow.ran{border-left-color:#3ddc84} .crow.err{border-left-color:#ff6b6b} .grp{display:inline-flex;gap:1px;margin-right:3px} .sq{display:block;border-radius:2px;background:#222d3b} .sq.running{background:#3ddc84} .sq.held{background:#e8c75a} .sq.used{background:#1f5c3d} .sq.err{background:#ff6b6b} .sq.last{opacity:.6} textarea#batchtxt{width:100%;background:#0d1219;color:var(--tx);border:1px solid var(--line);border-radius:4px;font:inherit;font-size:12px;padding:4px;resize:vertical} details#batchbox summary{cursor:pointer;color:var(--dim);font-size:12px;letter-spacing:.06em;text-transform:uppercase} .bar{display:flex;gap:3px;margin:4px 0}
.sl{height:34px;border-radius:4px;border:1px solid var(--line);display:flex;align-items:center;justify-content:center;font-size:11px;background:#0d1219;color:var(--dim);overflow:hidden;white-space:nowrap}
.sl.last{opacity:.4} .sl.running{background:#16402b;color:#baf5d1;border-color:#2f7a52} .sl.held{background:#3a3414;color:#f1dc8a;border-color:#7a6a2f}
.meter{height:6px;background:#0d1219;border-radius:3px;overflow:hidden;margin:2px 0} .meter i{display:block;height:100%;background:var(--c)} .meter i.sh{background:var(--m)}
.mut{color:var(--dim)} #rcol{display:grid;grid-template-rows:minmax(0,22vh) minmax(0,34vh) minmax(0,1fr) minmax(0,12vh);gap:10px;min-height:0} #rcol>.box,#rcol>.row2{min-height:0;overflow:auto} .row2{display:flex;gap:10px;min-height:0;overflow:hidden} .row2>.box{flex:1;min-width:0;min-height:0} button{font:inherit;font-size:12px;background:#0d1219;color:var(--tx);border:1px solid var(--line);border-radius:3px;cursor:pointer;padding:0 6px} button:disabled{opacity:.35;cursor:default} .row2{display:flex;gap:10px;min-height:0}.row2>.box{flex:1}
</style></head><body>
<header><b>S-Core window</b><span id="st">connecting...</span><span id="busy"></span><span class="mut" style="margin-left:auto">Kintex card via JTAG &middot; type <span class="c33">help</span></span></header>
<main>
<div class="col"><div class="box" id="term"><h2>Prompt</h2><div id="log"></div>
 <div id="cand"></div><div id="pw"><span id="ps">score&gt;</span><pre id="hl"></pre><input id="inp" autocomplete="off" spellcheck="false" autofocus></div></div>
 <details class="box" id="batchbox"><summary>Batch: design and run in one go</summary>
  <textarea id="batchtxt" rows="9" spellcheck="false" placeholder="# the same commands as the prompt, one per line (or separated by ;)&#10;use hk8s32u32n1i1024&#10;open ladder_6_eight_jobs.json&#10;set lw 0&#10;run&#10;set lw 5&#10;run"></textarea>
  <div style="margin-top:4px"><button id="bgo">run batch</button> <label class="mut"><input type="checkbox" id="bkeep"> keep going after an error</label> &nbsp; <input type="file" id="bfile" class="mut"></div>
 </details></div>
<div class="col" id="rcol">
 <div class="box" id="builds"><h2>Builds</h2><div id="buildsb" class="mut">looking...</div></div>
 <div class="box" id="cores"><h2 title="one square per core; the bar at the left of a row is green when that block ran steps in the last run (red = sequencer error). Squares: dark = idle, yellow = taken, waiting, green = running, dim green = was in use during the run (after a run: every core of a block that ran, since the card does not keep which cores a short run used), red = sequencer error. Fused cores touch. A picture taken about four times a second.">Cores</h2><div id="coresb" class="mut">No run yet. <span class="c33">add</span> some jobs, then <span class="c33">run</span>.</div></div>
 <div class="row2" style="flex:1"><div class="box"><h2>Jobs</h2><div id="jobs"></div></div><div class="box"><h2>Plan and last run</h2><div id="plan"></div></div></div>
 <div class="box"><h2>Settings</h2><div id="sett"></div></div>
</div></main>
<script>
const $=id=>document.getElementById(id); let since=0, hist=[], hi=-1, busy=false, seq=0;
try{hist=JSON.parse(localStorage.getItem('scwin_hist')||'[]')}catch(e){}
function setIf(id,html){ const el=$(id); if(el._h!==html){ el.innerHTML=html; el._h=html } }   // redraw a panel only when its content changed: no flicker, no re-layout (ledger #1542)
function h(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
async function get(u){const r=await fetch(u);return r.json()}
async function post(u,o){const r=await fetch(u,{method:'POST',headers:{'X-Score':'1','Content-Type':'application/json'},body:JSON.stringify(o)});return r.json()}
async function colour(){const my=++seq; const t=await get('/api/tokens?line='+encodeURIComponent($('inp').value)); if(my!==seq)return;
  $('hl').innerHTML=t.map(x=>x[0]==='ws'?h(x[1]):'<span class="s-'+x[0]+'">'+h(x[1])+'</span>').join('')}
$('inp').addEventListener('paste',async e=>{ const txt=(e.clipboardData||window.clipboardData).getData('text'); if(!/[\r\n]/.test(txt.trim())) return; e.preventDefault();
 const lines=txt.split(/\r?\n/).map(s=>s.trim()).filter(s=>s&&!s.startsWith('#'));
 for(const l of lines){ for(let k=0;k<12000;k++){ const s=await get('/api/state?since=999999999'); if(!s.busy)break; await new Promise(r=>setTimeout(r,100)) }
   hist.push(l); const r=await post('/api/exec',{line:l}); if(r.error){$('cand').innerHTML='<span class="c31">'+h(r.error)+'</span>'; break} await new Promise(r=>setTimeout(r,60)) } tick() });
$('bgo').addEventListener('click',async()=>{ const r=await post('/api/batch',{text:$('batchtxt').value,keep:$('bkeep').checked}); $('cand').innerHTML=r.error?'<span class="c31">'+h(r.error)+'</span>':''; tick() });
$('bfile').addEventListener('change',e=>{ const f=e.target.files[0]; if(!f)return; const rd=new FileReader(); rd.onload=()=>{ $('batchtxt').value=String(rd.result) }; rd.readAsText(f) });
$('inp').addEventListener('input',()=>{$('cand').textContent='';colour()});
$('inp').addEventListener('keydown',async e=>{
 if(e.key==='Enter'){const line=$('inp').value; $('inp').value=''; $('hl').innerHTML=''; $('cand').textContent='';
   if(line.trim()){hist.push(line); hist=hist.slice(-200); try{localStorage.setItem('scwin_hist',JSON.stringify(hist))}catch(x){}} hi=-1;
   const r=await post('/api/exec',{line}); if(r.error){$('cand').innerHTML='<span class="c31">'+h(r.error)+'</span>'; $('inp').value=line; colour();} tick(); e.preventDefault();}
 else if(e.key==='Tab'){e.preventDefault(); const v=$('inp').value; const c=await get('/api/complete?line='+encodeURIComponent(v));
   if(!c.items.length){$('cand').textContent='';return} let p=c.items[0]; for(const x of c.items){while(!x.startsWith(p))p=p.slice(0,-1)}
   const base=v.slice(0,v.length-c.word.length); $('inp').value=base+p+(c.items.length===1&&!p.endsWith('=')&&!p.endsWith('/')?' ':''); $('cand').textContent=c.items.length>1?c.items.join('   '):''; colour()}
 else if(e.key==='ArrowUp'){e.preventDefault(); if(hist.length){hi=hi<0?hist.length-1:Math.max(0,hi-1); $('inp').value=hist[hi]; colour()}}
 else if(e.key==='ArrowDown'){e.preventDefault(); if(hi>=0){hi++; $('inp').value=hi>=hist.length?'':hist[hi]; if(hi>=hist.length)hi=-1; colour()}}
});
function cores(c,lay){ const S=(c&&c.S)||lay.S, nb=Math.max(lay.nb,c?c.blocks.length:0);       // always one row per block asked for and one square per slice: the panel never changes size (ledger #1543)
 const w=$('cores').parentElement.clientWidth-40; const sq=Math.max(7,Math.min(16,Math.floor(w/(S*1.12)))); let o='';
 for(let k=0;k<nb;k++){ const b=c?c.blocks.find(x=>x.block===k):null; const er=b&&b.seq&&b.seq.err; const act=c&&c.active;
   o+='<div class="crow'+(b&&b.seq&&b.seq.err?' err':(b&&b.seq&&b.seq.done&&b.seq.steps>0?' ran':''))+'" style="height:'+(sq+4)+'px" title="block '+k+(b?': '+b.jobs+' jobs'+(b.seq&&b.seq.clk!=null?', '+b.seq.clk+' clocks':''):': no jobs')+'">';
   const groups=b?b.groups:Array.from({length:S},(_,i)=>({start:i,width:1,state:'idle'}));
   for(const g of groups){ o+='<span class="grp">'; for(let q=0;q<g.width;q++){ o+='<i class="sq '+(er?'err':g.state)+(act?'':' last')+'" style="width:'+sq+'px;height:'+sq+'px" title="block '+k+' slice '+(g.start+q)+': '+g.state+(g.state==='running'?' (class '+g.cls+' task '+g.tid+(g.width>1?', fused with '+g.width+' slices':'')+')':'')+'"></i>' } o+='</span>' }
   o+='</div>' }
 return '<div style="height:'+(nb*(sq+4))+'px">'+o+'</div>'}
function jobs(a){ if(!a.length) return '<span class="mut">no jobs yet</span>'; let o='<table><tr><th>#</th><th>kind</th><th>inputs</th><th>should give</th><th></th></tr>';
 for(const j of a) o+='<tr><td>'+j.i+'</td><td class="s-kind">'+h(j.kind)+(j.lw!=null?' <span class="mut">lw'+h(j.lw)+'</span>':'')+(j.arg!=null?' <span class="mut">arg '+j.arg+'</span>':'')+(j.crit?' <span class="c33">crit</span>':'')+'</td><td>'+h(j.inputs)+'</td><td>'+h(j.expect)+'</td><td>'+(j.verdict==='MATCH'?'<span class="ok">MATCH</span>':(j.verdict?'<span class="bad">'+j.verdict+'</span>':''))+'</td></tr>';
 return o+'</table>'}
function plan(s){ let o='';
 if(s.board) o+='<div class="mut">board version '+s.board.version+' &middot; '+s.board.slices+' slices per block &middot; '+s.board.code+' code words &middot; '+s.board.blocks+' blocks asked</div>';
 for(const b of s.plan.blocks){ o+='<div class="blk"><b>block '+b.block+'</b> <span class="mut">jobs '+h(b.ids)+'</span>';
   for(const t of s.plan.batches.filter(x=>x.block===b.block)){ o+='<div>batch '+t.batch+': '+t.jobs+' jobs <span class="s-kind">'+h(t.kinds)+'</span><div class="meter" title="code '+t.code+'/'+t.imem+'"><i style="width:'+Math.min(100,100*t.code/t.imem)+'%"></i></div><div class="meter" title="shared '+t.shared+'/'+t.dsh+'"><i class="sh" style="width:'+Math.min(100,100*t.shared/t.dsh)+'%"></i></div><span class="mut">code '+t.code+'/'+t.imem+' &middot; shared '+t.shared+'/'+t.dsh+'</span></div>'}
   o+='</div>'}
 for(const x of s.plan.orders) o+='<div class="mut">block '+x.block+' batch '+x.batch+' submit order: '+h(x.order)+'</div>';
 const ks=Object.keys(s.clocks); if(ks.length){o+='<div style="margin-top:6px"><b>last run</b>'; for(const k of ks){const c=s.clocks[k]; o+='<div>block '+k+': '+c.jobs+' jobs, '+c.steps+' steps, <span class="c33">'+c.clocks+'</span> clocks = '+c.ms+' ms</div>'}}
 if(s.summary) o+='<div class="'+(s.summary[0]===s.summary[1]?'ok':'bad')+'">'+s.summary[0]+' of '+s.summary[1]+' jobs correct</div>';
 if(s.runs.no) o+='<div class="mut">run '+s.runs.no+' of this job set in this window'+(s.runs.no===1?': the first run after a bitstream load is slower than a repeat (ledger #1417), so compare repeats with repeats':': a repeat, so the card has learned job lengths (warm)')+'</div>';
 return o||'<span class="mut">type <span class="c33">plan</span> or <span class="c33">run</span></span>'}
async function cmd(c){ await post('/api/exec',{line:c}); tick() }
function builds(b){ b.rows.sort((x,y)=>(y.name===b.current)-(x.name===b.current)); if(!b.rows.length) return '<span class="mut">no builds found. <span class="c33">store FOLDER</span> says where yours are.</span>';
 let o='<div class="mut">store: '+(b.store?h(b.store):'not set')+' &middot; chosen (host settings): '+(b.current?'<span class="ok">'+h(b.current)+'</span>':'none')+' &middot; on the card: '+(b.oncard?'<span class="ok">'+h(b.oncard)+'</span>':'<span class="c33">not known (nothing loaded in this session)</span>')+'</div><table><tr><th>build</th><th>size</th><th>lanes</th><th>code</th><th>LUTs</th><th>setup</th><th>Kintex</th><th>bit</th><th></th></tr>';
 for(const r of b.rows){ const fc=r.fit==='recommended'?'ok':(r.fit==='no'?'bad':'c33'); const tc=r.timing_ok===false?'bad':(r.timing_ok?'':'c33');
  o+='<tr'+(r.name===b.current?' style="background:#16402b55"':'')+' title="'+h(r.card)+'"><td class="s-kind">'+h(r.name)+(r.name===b.oncard?' <span class="ok" title="loaded on the card in this session">[on card]</span>':'')+'</td><td>'+r.blocks+'x'+r.slices+'</td><td>'+(r.lanes||'-')+'</td><td>'+r.imem+'</td><td>'+(r.luts?r.luts:(r.predicted?'~'+r.predicted:'?'))+'</td><td class="'+tc+'">'+(r.setup===null?'?':(r.setup>0?'+':'')+r.setup)+'</td><td class="'+fc+'">'+h(r.fit)+'</td><td>'+(r.bit?'<span class="ok">yes</span>':'<span class="mut">no</span>')+'</td>'+
  '<td><button onclick="cmd(\'use '+r.name+'\')">use</button> <button onclick="cmd(\'load '+r.name+'\')"'+(r.bit?'':' disabled')+'>load</button></td></tr>'}
 return o+'</table><div class="mut">use = only the host's settings (blocks, slices, lanes, code words); it does NOT touch the card. load = put its bitstream in the card (SRAM only), then check the card against it; a failed-timing build is refused.</div>'}
function sett(s){ let o='<span class="mut">'+(s.name?h(s.name):'no job file')+(s.dirty?' (not saved)':'')+'</span> &nbsp; '; for(const k in s.settings) o+='<span class="mut">'+k+'</span>=<span class="c33">'+h(s.settings[k])+'</span> &nbsp; '; return o}
let ticking=false, timer=null;
async function tick(){ if(ticking) return; ticking=true; clearTimeout(timer); try{ const s=await get('/api/state?since='+since); busy=s.busy; $('st').textContent='connected'; $('busy').textContent=s.busy?'running: '+s.cmd:'';
   const L=$('log'); const near=L.scrollHeight-L.scrollTop-L.clientHeight<60; for(const [n,t] of s.lines){ if(n<=since) continue; L.insertAdjacentHTML('beforeend','<div>'+t+'</div>'); since=n } if(near)L.scrollTop=L.scrollHeight;
   setIf('buildsb',builds(s.builds)); setIf('coresb',cores(s.cores,s.layout)); setIf('jobs',jobs(s.jobs)); setIf('plan',plan(s)); setIf('sett',sett(s));
 }catch(e){ $('st').textContent='no connection to scwin_v12.py' } ticking=false; timer=setTimeout(tick,busy?350:1000)}
tick(); colour();
</script></body></html>"""

def make_handler(web, port):
    hosts = {'localhost:%d' % port, '127.0.0.1:%d' % port}
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, body, ctype):
            b = body.encode() if isinstance(body, str) else body
            self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(b))); self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(b)
        def _ok_origin(self, post):
            if self.headers.get('Host', '') not in hosts: return False                  # DNS rebinding
            if post:
                o = self.headers.get('Origin')
                if o is not None and o not in ('http://' + h for h in hosts): return False
                if self.headers.get('X-Score') != '1': return False                      # a page on another site cannot set this without a preflight
            return True
        def do_GET(self):
            if not self._ok_origin(False): return self._send(403, 'refused', 'text/plain')
            u = urlparse(self.path); q = parse_qs(u.query)
            if u.path == '/': self._send(200, PAGE, 'text/html; charset=utf-8')
            elif u.path == '/api/state': self._send(200, json.dumps(web.state(int(q.get('since', ['0'])[0]))), 'application/json')
            elif u.path == '/api/complete': self._send(200, json.dumps(web.complete(q.get('line', [''])[0])), 'application/json')
            elif u.path == '/api/tokens': self._send(200, json.dumps(web.tokens(q.get('line', [''])[0])), 'application/json')
            else: self._send(404, 'not found', 'text/plain')
        def do_POST(self):
            if not self._ok_origin(True): return self._send(403, 'refused', 'text/plain')
            path = urlparse(self.path).path
            if path not in ('/api/exec', '/api/batch'): return self._send(404, 'not found', 'text/plain')
            try: req = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
            except ValueError: return self._send(400, '{"error":"bad request"}', 'application/json')
            err = web.exec_batch(str(req.get('text', '')), bool(req.get('keep'))) if path == '/api/batch' else web.exec(str(req.get('line', '')))
            self._send(200, json.dumps({'error': err}), 'application/json')
    return H

def make_web():
    """a Web with the colours switched on (the page turns the codes into colours)"""
    S.C_ON = True
    w = Web(); WEB_FOR_RENDER[:] = [w.sh]
    return w

def serve(web, port):
    srv = ThreadingHTTPServer(('127.0.0.1', port), make_handler(web, port)); srv.daemon_threads = True
    return srv

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--port', type=int, default=8766); ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('-f', metavar='FILE', help='run a file of shell commands first (the same format as score_shell_v5.py -f)')
    a = ap.parse_args(argv)
    web = make_web()
    srv = serve(web, a.port); url = 'http://localhost:%d' % a.port
    print('S-Core window at %s  (Ctrl-C here stops it)' % url)
    if not a.no_browser:
        try: webbrowser.open(url)
        except Exception: pass
    threading.Thread(target=srv.serve_forever, daemon=True).start()      # serve the page at once; the file's commands then run while the page is open (ledger #1442: it used to serve only after the file, and waited 0.2 s between commands)
    try:
        if a.f:
            for ln in open(a.f).read().split('\n'):
                for piece in ln.split(';'):
                    while web.busy: time.sleep(0.01)
                    if piece.strip() and not piece.strip().startswith('#'): web.exec(piece)
        while True: time.sleep(1)
    except KeyboardInterrupt: print('stopped')
    srv.shutdown()
    return 0

if __name__ == '__main__': sys.exit(main())
