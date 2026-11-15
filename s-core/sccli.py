#!/usr/bin/env python3
"""sccli.py - a command line scheduler for the S-Core pool on the Tang Nano 20K.

    python3 sccli.py /dev/ttyUSB1                 interactive
    python3 sccli.py /dev/ttyUSB1 -f demo.sccli   run a script of commands, then stay in (or leave with -q)
    python3 sccli.py /dev/ttyUSB1 -c "load cli_demo/demo.scs; send; run sum 4; wait; jobs"

The host side keeps the books: which program is which class, which task slot (tid) each job uses, what has finished.  The board does the
scheduling of jobs onto slices; this program gives it jobs by NAME and shows what came back.  Type `help` for the commands.

A "system file" (.scs) describes the programs and where their memory goes (lines; # starts a comment; paths are relative to the file):
    shared 256                               # shared data words (default: asked from the board)
    library lib.s                            # code every class may call (optional)
    class 0 sum.s name=sum data=16 stack=private        # class id, source file, options
    class 2 fib.s name=fib stack=shared stack_words=48
    clone 12 2 name=fib2                     # a second id with the same code and its own shared window
    preload 0 1 2 3 4                        # shared RAM words from address 0
Class options: name= stack=private|shared stack_words= data= (shared data words before the stack) dlen= (private data limit) win= (shared window base)
Source files are assembly with a `main:` label that ends in `ret` and leaves its result in a0 (see sclink.py)."""
import sys, os, cmd, time, shlex, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import host_sc as hs
import sclink

class CliError(Exception): pass

def num(s):
    try: return int(str(s), 0)
    except ValueError: raise CliError('not a number: %r' % s)

def parse_system(path, shared_words, private_words, code_words):
    """-> (Link, names {name: class id}).  Raises CliError with a line number on a mistake."""
    base = os.path.dirname(os.path.abspath(path))
    L = sclink.Linker(shared_words=shared_words, private_words=private_words, code_words=code_words)
    names, plain = {}, {}
    def src(f): 
        p = f if os.path.isabs(f) else os.path.join(base, f)
        try: return open(p).read()
        except OSError as e: raise CliError('cannot read %s' % p)
    for n, line in enumerate(open(path), 1):
        line = line.split('#', 1)[0].strip()
        if not line: continue
        w = shlex.split(line); kw = {}; pos = []
        for t in w[1:]:
            if '=' in t: k, v = t.split('=', 1); kw[k] = v
            else: pos.append(t)
        try:
            if w[0] == 'shared': L.shared_words = num(pos[0])
            elif w[0] == 'library': L.library(src(pos[0]))
            elif w[0] == 'class':
                cid = num(pos[0])
                extra = {k: v for k, v in kw.items() if k not in ('name', 'stack', 'stack_words', 'data', 'dlen', 'win', 'share')}
                if extra: raise CliError('unknown option %s' % ', '.join(extra))
                L.add_class(cid, src(pos[1]), stack=kw.get('stack', 'private'), stack_words=num(kw.get('stack_words', 0)), data_words=num(kw.get('data', 0)),
                            win_base=num(kw['win']) if 'win' in kw else None, dlen=num(kw['dlen']) if 'dlen' in kw else None,
                            share_window_of=num(kw['share']) if 'share' in kw else None)
                nm = kw.get('name', os.path.splitext(os.path.basename(pos[1]))[0])
                if nm in names: raise CliError('name %s used twice' % nm)
                names[nm] = cid
            elif w[0] == 'clone':
                L.clone_class(num(pos[0]), num(pos[1]), win_base=num(kw['win']) if 'win' in kw else None)
                nm = kw.get('name', 'c%d' % num(pos[0]))
                if nm in names: raise CliError('name %s used twice' % nm)
                names[nm] = num(pos[0])
            elif w[0] == 'preload': L.preload_shared(num(pos[0]), [num(x) for x in pos[1:]])
            else: raise CliError('unknown line type %r' % w[0])
        except (CliError, ValueError, IndexError, KeyError) as e:
            raise CliError('%s line %d: %s' % (os.path.basename(path), n, e if str(e) else 'bad line'))
    try: return L.link(), names
    except Exception as e: raise CliError('link failed: %s' % e)

class Session:
    def __init__(self, board, out=print, sleep=time.sleep, queue=16):
        self.b, self.out, self.sleep, self.QD = board, out, sleep, queue
        self.v = self.info = None
        self.link = None; self.names = {}; self.sent = False
        self.jobs = {}; self.next_job = 1; self.free = list(range(queue)); self.held = False

    # ---- board
    def connect(self):
        self.v = self.b.version()
        hs.check_design(self.v, None, 8, 'the library window (a --pool 7 build)')
        self.info = self.b.shared_info()
        self.out('board: %d slices, %d code words, %d private data words, %d shared words' % (self.v['S'], self.v['imem_words'], self.v['dmem_words'], self.info['shared_words']))

    def need_board(self):
        if self.v is None: raise CliError('not connected')

    # ---- programs
    def load(self, path):
        self.need_board()
        self.link, self.names = parse_system(path, self.info['shared_words'], self.v['dmem_words'], self.v['imem_words'])
        if len(self.link.words) > self.v['imem_words']: raise CliError('the programs need %d code words, the board has %d' % (len(self.link.words), self.v['imem_words']))
        self.sent = False
        self.out(self.link.report()); self.out('programs: ' + ', '.join('%s=%d' % kv for kv in sorted(self.names.items(), key=lambda kv: kv[1])))

    def send(self):
        """reset the board (this forgets every job) and download code, regions, windows and shared preloads"""
        self.need_board()
        if self.link is None: raise CliError('nothing loaded: use `load FILE.scs` first')
        self.b.reset(); self.jobs.clear(); self.free = list(range(self.QD)); self.held = False
        self.link.apply(self.b); self.sent = True
        self.out('sent %d code words, %d classes' % (len(self.link.words), len(self.link.classes)))

    # ---- jobs
    def hold(self): self.need_board(); self.b.hold(); self.held = True; self.out('hold: jobs queue up but do not start')
    def go(self): self.need_board(); self.b.go(); self.held = False; self.out('go')

    def _alloc(self, timeout=30):
        t0 = time.time()
        while not self.free:
            if self.held: raise CliError('the queue is full (%d jobs) and the board is on hold: `go` first' % self.QD)
            self.poll(); 
            if not self.free:
                if time.time() - t0 > timeout: raise CliError('no free task slot after %ds' % timeout)
                self.sleep(0.05)
        return self.free.pop(0)

    def run(self, name, count=1, crit=0, width=0):
        self.need_board()
        if not self.sent: raise CliError('send the programs to the board first (`send`)')
        if name not in self.names: raise CliError('no program called %r (have: %s)' % (name, ', '.join(sorted(self.names)) or 'none'))
        cid = self.names[name]; made = []
        for _ in range(count):
            tid = self._alloc()
            self.b.submit(tid, self.link.classes[cid]['entry'], width, crit, cid); self.b.s.flush()
            j = self.next_job; self.next_job += 1
            self.jobs[j] = dict(name=name, cid=cid, tid=tid, state='queued', q=None, crit=crit); made.append(j)
        self.out('job%s %s: %s' % ('s' if len(made) > 1 else '', ', '.join(map(str, made)), name))
        return made

    def poll(self):
        for j, r in self.jobs.items():
            if r['state'] in ('done', 'trap'): continue
            q = self.b.task(r['tid'])
            if q['state'] == 3:
                r['q'] = q; r['state'] = 'trap' if q['trap'] else 'done'; self.free.append(r['tid'])
            elif q['state'] == 2: r['state'] = 'running'
            else: r['state'] = 'queued'

    def wait(self, timeout=60):
        t0 = time.time()
        while True:
            self.poll()
            if all(r['state'] in ('done', 'trap') for r in self.jobs.values()): return True
            if self.held: self.out('(the board is on hold: `go` to start the queued jobs)'); return False
            if time.time() - t0 > timeout: self.out('timeout: some jobs are still not finished'); return False
            self.sleep(0.1)

    @staticmethod
    def line(j, r):
        q = r['q']
        if q is None: return 'job %3d  %-10s tid %2d  %s' % (j, r['name'], r['tid'], r['state'])
        res = 'stopped by a protection check' if r['state'] == 'trap' else 'a0=%d (0x%08x)' % (q['a0'], q['a0'])
        return 'job %3d  %-10s tid %2d  %-5s %s  slice %d  %d clocks%s' % (j, r['name'], r['tid'], r['state'].upper() if r['state'] == 'trap' else r['state'],
            res, q['slot'], (q['end'] - q['start']) & 0xFFFFFFFF, '' if not r['crit'] else '  critical')

    def show_jobs(self, only=None):
        self.poll()
        rows = [(j, r) for j, r in sorted(self.jobs.items()) if only is None or j in only]
        if not rows: self.out('no jobs')
        for j, r in rows: self.out(self.line(j, r))
        n = {}
        for _, r in rows: n[r['state']] = n.get(r['state'], 0) + 1
        if rows: self.out('  ' + ', '.join('%d %s' % (v, k) for k, v in sorted(n.items())))

    def result(self, j):
        self.poll()
        if j not in self.jobs: raise CliError('no job %d' % j)
        r = self.jobs[j]; self.out(self.line(j, r))

    # ---- shared RAM and counters
    def peek(self, addr, n=1):
        self.need_board()
        if addr < 0 or addr + n > self.info['shared_words']: raise CliError('shared RAM has %d words (0..%d)' % (self.info['shared_words'], self.info['shared_words'] - 1))
        w = self.b.shared_read(addr, n)
        for i in range(0, n, 4): self.out('%4d: ' % (addr + i) + ' '.join('%08x' % x for x in w[i:i + 4]))
        return w

    def poke(self, addr, vals):
        self.need_board()
        if addr < 0 or addr + len(vals) > self.info['shared_words']: raise CliError('shared RAM has %d words' % self.info['shared_words'])
        self.b.shared_write(addr, vals); self.out('wrote %d word%s at %d' % (len(vals), 's' if len(vals) > 1 else '', addr))

    def counters(self):
        self.need_board(); c = self.b.counters()
        for k, v in c.items(): self.out('  %-18s %d' % (k, v))
        busy = c['busy_slice_cycles']; tot = c['cyc'] * self.v['S']
        if tot: self.out('  slice utilisation  %.1f%%' % (100.0 * busy / tot))

class Shell(cmd.Cmd):
    prompt = 'score> '
    intro = 'S-Core scheduler.  `help` lists the commands.'
    def __init__(self, session, keep_going=False):
        super().__init__(); self.S = session; self.failed = 0; self.keep_going = keep_going; self.scripted = False
    def onecmd(self, line):
        try: return super().onecmd(line)
        except CliError as e: self.S.out('error: %s' % e); self.failed += 1; return self.scripted and not self.keep_going
        except (IOError, OSError) as e: self.S.out('board error: %s' % e); self.failed += 1; return self.scripted and not self.keep_going
    def emptyline(self): pass
    def args(self, line): return shlex.split(line)

    def do_load(self, line):
        """load FILE.scs   read a system file: the programs, their classes and memory windows (see sccli.py)"""
        a = self.args(line)
        if len(a) != 1: raise CliError('usage: load FILE.scs')
        self.S.load(a[0])
    def do_send(self, line):
        """send   reset the board (forgets all jobs) and download the loaded programs, regions and windows"""
        self.S.send()
    def do_programs(self, line):
        """programs   list the loaded programs"""
        if self.S.link is None: raise CliError('nothing loaded')
        self.S.out(self.S.link.report())
        self.S.out('programs: ' + ', '.join('%s=%d' % kv for kv in sorted(self.S.names.items(), key=lambda kv: kv[1])))
    def do_run(self, line):
        """run NAME [COUNT] [critical] [width=N]   submit COUNT jobs (default 1) of a program; `critical` jumps the queue"""
        a = self.args(line)
        if not a: raise CliError('usage: run NAME [COUNT] [critical] [width=N]')
        cnt, crit, width = 1, 0, 0
        for t in a[1:]:
            if t == 'critical': crit = 1
            elif t.startswith('width='): width = num(t[6:])
            else: cnt = num(t)
        if cnt < 1: raise CliError('COUNT must be at least 1')
        self.S.run(a[0], cnt, crit, width)
    def do_hold(self, line):
        """hold   queue jobs without starting them (so a batch can be started together)"""
        self.S.hold()
    def do_go(self, line):
        """go   release the hold: the board starts the queued jobs"""
        self.S.go()
    def do_wait(self, line):
        """wait [SECONDS]   wait until every job has finished (default 60 s)"""
        a = self.args(line)
        if self.S.wait(num(a[0]) if a else 60): self.S.out('all %d jobs finished' % len(self.S.jobs))
    def do_jobs(self, line):
        """jobs   show every job: state, result in a0, slice, clocks used"""
        self.S.show_jobs()
    do_ps = do_jobs
    def do_result(self, line):
        """result JOB   show one job"""
        a = self.args(line)
        if len(a) != 1: raise CliError('usage: result JOB')
        self.S.result(num(a[0]))
    def do_peek(self, line):
        """peek ADDR [N]   read N shared RAM words (word addresses; 0x.. allowed)"""
        a = self.args(line)
        if not 1 <= len(a) <= 2: raise CliError('usage: peek ADDR [N]')
        self.S.peek(num(a[0]), num(a[1]) if len(a) > 1 else 1)
    def do_poke(self, line):
        """poke ADDR VALUE [VALUE ...]   write shared RAM words"""
        a = self.args(line)
        if len(a) < 2: raise CliError('usage: poke ADDR VALUE [VALUE ...]')
        self.S.poke(num(a[0]), [num(x) & 0xFFFFFFFF for x in a[1:]])
    def do_counters(self, line):
        """counters   the board's performance counters"""
        self.S.counters()
    def do_info(self, line):
        """info   what the board is"""
        self.S.need_board(); self.S.out('%s  %s' % (self.S.v, self.S.info))
    def do_sleep(self, line):
        """sleep SECONDS   pause (for scripts)"""
        a = self.args(line); self.S.sleep(float(a[0]) if a else 1)
    def do_echo(self, line):
        """echo TEXT   print text (for scripts)"""
        self.S.out(line)
    def do_quit(self, line):
        """quit   leave"""
        return True
    do_exit = do_quit; do_EOF = do_quit

def run_lines(sh, lines):
    sh.scripted = True
    try: return _run_lines(sh, lines)
    finally: sh.scripted = False

def _run_lines(sh, lines):
    for ln in lines:
        ln = ln.split('#', 1)[0].strip()
        for part in ln.split(';'):
            if part.strip():
                stop = sh.onecmd(part.strip())
                if stop: return False            # `quit`, or an error (without -k)
    return True

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0]); ap.add_argument('port'); ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--queue', type=int, default=16, help='task table size of the build (default 16)')
    ap.add_argument('-c', dest='cmds', help='commands to run first, separated by ;'); ap.add_argument('-f', dest='script', help='file of commands to run first')
    ap.add_argument('-q', action='store_true', help='quit after the -c / -f commands'); ap.add_argument('-k', action='store_true', help='keep going after an error')
    a = ap.parse_args()
    S = Session(hs.Board(a.port, a.baud), queue=a.queue)
    sh = Shell(S, keep_going=a.k)
    try: S.connect()
    except Exception as e: sys.exit('cannot talk to the board: %s' % e)
    ok = True
    if a.script: ok = run_lines(sh, open(a.script).read().splitlines()) and ok
    if a.cmds and ok: ok = run_lines(sh, [a.cmds])
    if a.q or not ok:
        sys.exit(1 if sh.failed else 0)
    sh.cmdloop()

if __name__ == '__main__': main()
