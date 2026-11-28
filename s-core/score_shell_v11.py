#!/usr/bin/env python3
"""score_shell_v11.py - score_shell_v10.py plus the MULTIPLY LIBRARY (ledger #1582: lib_mul32 and the multiply-unit count in job header word 7, through jobio_ext_v1.py; 0 units on every build today, so every program behaves as before), and before that score_shell_v10.py: score_shell_v9.py plus a clear BATCH START and BATCH END banner line around every batch (ledger #1578), and before that score_shell_v9.py: score_shell_v8.py plus ONE NAMED OPENOCD and better link advice (ledger #1568): `set openocd PATH` (saved in ~/.score_shell.json) puts that openocd first on PATH for the shell and everything it starts, so a second openocd on the machine is never picked by mistake (default: the nix build proven on this card, see openocd_path_v1.py); `card` and the run pre-flight say which openocd and version; link_check_v2.py gives specific advice for the all-ones read (header board), "unable to claim usb device" and "no device found"; after a failed read the remembered label is shown as last known and not confirmed.  Before that, v8: score_shell_v7.py with two message fixes found by Alan unplugging the header board in the middle (ledger #1566): when `card` cannot read the card it now says WHY (the helper's own error and what to check, not always "start inside nix shell"), and what the shell remembers says where it learned it (the label read earlier, or loaded in this session).  Before that, v7: score_shell_v6.py plus a LINK CHECK (ledger #1564): before `run` the shell checks that the USB adapter is on the bus and has not dropped since the last check, and pings the card; before `load` and `card` it checks the adapter; a failure stops with a plain sentence (link_check_v2.py), and a LinkError in the middle of a command is followed by what to look at; `set linkcheck off` skips it.  Before that: score_shell_v5.py plus a LABEL IN THE CARD (ledger #1556): after a successful `load` the shell writes the build name, blocks, slices, lanes, units and code words into far RAM (card_label_v1.py) and counts the card's blocks; `card` reads them back, so a new shell or window learns what is on the card without having loaded it; `card stamp BUILD` records a build loaded by hand after checking the board; `run` is refused when the label names another build than the chosen one or the settings ask for more blocks than the card has. score_shell_v5.py was score_shell_v4.py plus the SHELL KNOWS WHAT IT PUT ON THE CARD (ledger #1552): `use` only sets the host's settings and says so; `load` puts a bitstream on the card and the shell remembers which one (`card` command shows it); `run` refuses when the chosen build is not the one loaded in this session, instead of running a design with the wrong block count. score_shell_v4.py was score_shell_v3.py plus WAVES for designs too big for one run (ledger #1547; v1 to v3 are left as proven): `run` splits a design that does not fit the card at once into waves (many jobs, or a huge data set cut by addbig), runs them one after the other and puts the answers together; a job can read the answers of earlier jobs (`add KIND from=J argfrom=J`), which makes a pipeline run stage by stage; `waves` shows the plan without a card. score_shell_v3.py was score_shell_v2.py plus batch scripts (ledger #1541; v1 and v2 are left as proven): command `batch FILE [continue]`, and `-f FILE` / `-c CMDS` now stop at the first error and exit with code 1 (`-k` goes on). A batch is a file of the same commands you type (make, add, open, set, use, load, run ...), one per line or separated by ;, # starts a comment: design the jobs and run them in one go. score_shell_v2.py was score_shell_v1.py plus the build store (ledger #1534): commands store, builds, target, fit, use, load; settings imem. An interactive shell for S-Core jobs (the Kintex card, JTAG, job files): type jobs in, save them, plan, run, compare.

    python3 score_shell_v11.py                         interactive (plan and check work with no card)
    nix shell nixpkgs#openocd --command python3 score_shell_v11.py        interactive with the card (run needs openocd)
    python3 score_shell_v11.py -f session.score -q     run a file of commands, then leave
    python3 score_shell_v11.py -c "add vsum 1 2 3; show"

Type `help` for the commands (the same list is in SHELL_v11.md).  The jobs you type are kept in the same JSON format the other tools read (scblocks.py, ledger #1419):
`save mine.json` writes a job file, `open mine.json` reads one.  Colours: errors red, results green, names cyan, numbers yellow; set NO_COLOR=1 or start with --plain
for none.  While you type: Tab completes commands, kinds, settings and file names; with the optional package prompt_toolkit installed the line is also coloured as you type
(a known command green, an unknown one red).  Without it everything works, only the live colouring is missing (SCORE_SHELL_NO_PT=1 switches it off).
score_shell_v11.py was new in ledger #1420; sccli.py (the Tang Nano scheduler shell) is unchanged."""
import scwaves_v1 as WV
import card_label_v1 as CL
import link_check_v2 as LC
import jobio_ext_v1 as JX
import openocd_path_v1 as OP
import time
import re, os, sys, io, json, glob, shlex, tempfile, argparse, contextlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import score_store_v2 as ST, make_manifest_v2 as M

# ---------------------------------------------------------------- colours
C_ON = False
def paint(code, s): return '\033[%sm%s\033[0m' % (code, s) if C_ON else s
def red(s): return paint('31', s)
def green(s): return paint('32', s)
def cyan(s): return paint('36', s)
def yellow(s): return paint('33', s)
def dim(s): return paint('2', s)
def bold(s): return paint('1', s)

# ---------------------------------------------------------------- the library of ready programs (needs no writing)
LIBRARY = {   # kind: (source, expect, out)
    'crc32':   ('programs/crc32.s',   'programs.examples:crc32_ref',   1),
    'vgain':   ('programs/vgain.s',   'programs.examples:vgain_ref',   'same'),
    'vmax':    ('programs/vmax.s',    'programs.examples:vmax_ref',    1),
    'vprefix': ('programs/vprefix.s', 'programs.examples:vprefix_ref', 'same'),
    'vmin':    ('programs/vmin.s',    'programs.examples_v2:vmin_ref', 1),
    'vxor':    ('programs/vxor.s',    'programs.examples_v2:vxor_ref', 'same'),
    'vcount':  ('programs/vcount.s',  'programs.examples_v3:vcount_ref', 1),
}
BUILTIN_KINDS = ('vsum', 'vscale', 'vstress')
MADE = os.path.join(HERE, 'programs', 'made')
def made_names():
    """kinds made earlier with `make` (kept in programs/made/, they survive the shell)"""
    return sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(MADE, '*.json')))
SETTINGS = {  # name: (default, help)
    'blocks':   (1,      'how many blocks of the card to use'),
    'lw':       (None,   'width for every job: 0..5 (2**lw slices fused), auto, or none (each job keeps its own)'),
    'order':    ('auto', 'submit order inside a batch: auto, kind or width'),
    'profile':  (None,   'card profile (sc_calibrate_v1) for auto width, or none'),
    'estimate': (False,  'on: choose a width per job from its length (needs profile and lw auto)'),
    'margin':   (0.10,   'the estimate keeps a mix of widths only if it beats the best single width by this much'),
    'dsh':      (None,   'shared RAM words per block of the build: none = ask the card on run (256 for plan); set it to plan for a bigger build'),
    'far-words': (None,  'far RAM words (65536 on the block-RAM card build): set it to plan for a DDR3 build'),
    'slices':   (None,   'slices per block (only for plan with auto width; a real run asks the board)'),
    'loader':   (None,   'path of the openFPGALoader program; none = the nix one proven on this card, else the one on PATH'),
    'imem':     (None,   'code words per block of the build (the build store sets it with `use`; none = the planner assumes 128)'),
    'unit-lw':  (None,   'log2 of the lanes of a fusion unit on the loaded build (3 on the 2x8)'),
    'linkcheck': (True,  'on: before run (and load, card) check the USB adapter and ping the card, and explain link failures in plain words; off: skip the checks'),
    'openocd':  (None,   'path of the openocd program to use (saved for next time); none = your saved path, SCORE_OPENOCD, the nix build proven on this card, then PATH'),
    'port':     ('jtag', 'the link to the card: jtag, or a serial device'),
    'out':      ('shell_results.json', 'where run writes the results'),
}

class ShellError(Exception): pass

def num(s):
    try: return int(str(s), 0)
    except ValueError: raise ShellError('not a number: %r' % s)

class Shell:
    def __init__(self, out=None):
        self.out = out or sys.stdout
        self.programs = {}        # name -> {"name","source","expect","out"}  (what the job file's "programs" part will hold)
        self.jobs = []            # list of job dicts in job-file format
        self.set = {k: v[0] for k, v in SETTINGS.items()}
        JX.install(0); self.cfg = ST.load_config(); self.build = None; self.card_build = None; self.card_src = None; self.card_info = None; self._learned = False; self.watch = LC.Watch(); self.set['openocd'] = self.cfg.get('openocd'); self.pick_openocd(self.set['openocd']); self.label_written = False; self.label_check = True; self.runner = subprocess.run
        self.name = None; self.dirty = False; self.quit = False
        self.errors = 0; self.runlog = []; self.depth = 0       # batch bookkeeping (ledger #1541)
        self.cmds = {}
        for name, (fn, usage, text) in COMMANDS.items(): self.cmds[name] = (getattr(self, 'do_' + fn), usage, text)
    # -------- output
    def say(self, s=''): print(s, file=self.out)
    def err(self, s): self.errors += 1; print(red('error: ' + s), file=self.out)
    def before_command(self, cmd): pass       # the browser window hooks in here to clear its panels at the start of each command, also inside a batch
    # -------- the job set as a job file
    def _tasks_of(self, joblist):
        import scbatch
        fd, path = tempfile.mkstemp(prefix='score_shell_', suffix='.json', dir=HERE); os.close(fd)
        d = {'jobs': joblist}
        if self.programs: d['programs'] = list(self.programs.values())
        json.dump(d, open(path, 'w'))
        try: return scbatch.load_jobs(path)
        finally: os.remove(path)
    def resolve_all(self, jobs):
        """the jobs with every `from` / `argfrom` filled in from the REFERENCE answers (the Python answers of the earlier jobs): used to plan, to check and to show; the card is fed its own answers (run_waves)"""
        if not WV.has_refs(jobs): return jobs
        try: lv = WV.levels(jobs)
        except WV.WaveError as e: raise ShellError(str(e))
        got = {}; out = [None] * len(jobs)
        for ids in lv:
            res = [WV.resolve(jobs[i], got) for i in ids]
            for i, r, tk in zip(ids, res, self._tasks_of(res)): out[i] = r; got[i] = tk.expected()
        return out
    def doc(self, resolved=False):
        d = {'jobs': self.resolve_all(self.jobs) if resolved else self.jobs}
        if self.programs: d['programs'] = list(self.programs.values())
        return d
    def tmpfile(self):
        fd, path = tempfile.mkstemp(prefix='score_shell_', suffix='.json', dir=HERE); os.close(fd)
        json.dump(self.doc(True), open(path, 'w')); return path
    def tasks(self):
        import scbatch
        p = self.tmpfile()
        try: return scbatch.load_jobs(p)
        finally: os.remove(p)
    # -------- dispatch
    def execute(self, line):
        line = line.strip()
        if not line or line.startswith('#'): return
        try: parts = shlex.split(line, comments=True)
        except ValueError as e: return self.err(str(e))
        if not parts: return
        cmd = parts[0].lower()
        if cmd not in self.cmds:
            near = [c for c in self.cmds if c.startswith(cmd[:2])][:4]
            return self.err('unknown command %r%s (type help)' % (cmd, ('; did you mean: ' + ', '.join(near)) if near else ''))
        self.before_command(cmd)
        try: self.cmds[cmd][0](parts[1:])
        except ShellError as e:
            self.err(str(e))
            if 'nothing was sent' not in str(e) and 'not on the USB bus' not in str(e): self.explain_link(str(e))      # a failed load names the loader's own words; the pre-flight messages already explain themselves
        except Exception as e:
            self.err('%s: %s' % (type(e).__name__, e)); self.explain_link('%s: %s' % (type(e).__name__, e))
    def run_lines(self, text):
        for ln in text.split('\n'):
            for piece in ln.split(';'):
                self.execute(piece)
                if self.quit: return
    def run_script(self, text, stop=True, label='batch'):
        """run a batch (ledger #1541): the lines of `text` as commands. Stops at the first command that reports an error unless stop is False.
        Prints each command as it starts, and at the end how many commands ran and what each run gave. Returns True when no command reported an error."""
        e0, r0, n, stopped = self.errors, len(self.runlog), 0, None
        ncmd = sum(len([p for p in ln.split(';') if p.strip()]) for ln in text.split('\n') if ln.strip() and not ln.strip().startswith('#'))
        self.say(bold(cyan('=' * 8 + ' BATCH START: %s (%d commands) ' % (label, ncmd) + '=' * 8)))
        for lineno, ln in enumerate(text.split('\n'), 1):
            if not ln.strip() or ln.strip().startswith('#'): continue
            for piece in ln.split(';'):
                if not piece.strip(): continue
                self.say(dim('%s %d> %s' % (label, lineno, piece.strip())))
                e1 = self.errors; self.execute(piece); n += 1
                if self.quit: stopped = 'quit'; break
                if stop and self.errors > e1: stopped = 'line %d' % lineno; break
            if stopped: break
        runs = self.runlog[r0:]
        for i, r in enumerate(runs, 1):
            ok = r['finished'] and r['correct'] == r['total']
            self.say('  run %d: %s of %s jobs correct%s%s%s' % (i, r['correct'] if r['correct'] is not None else '?', r['total'], (', slowest block %d clocks' % r['slowest']) if r['slowest'] else '',
                     (', lw %s' % r['lw']) if r['lw'] is not None else '', ((', %d waves' % r['waves']) if r.get('waves', 1) > 1 else '') + ('' if ok else '  <-- not all correct')))
        bad = self.errors - e0
        line = '%s: %d commands, %d runs, %d errors%s' % (label, n, len(runs), bad, ('; stopped at %s' % stopped) if stopped else '')
        good = bad == 0 and all(r['finished'] and r['correct'] == r['total'] for r in runs)
        self.say(green(line) if good else red(line))
        self.say(bold(green('=' * 8 + ' BATCH END: %s, all good ' % label + '=' * 8) if good else red('=' * 8 + ' BATCH END: %s, NOT ALL GOOD (%d errors%s) ' % (label, bad, ', stopped at %s' % stopped if stopped else '') + '=' * 8)))
        return bad == 0
    def do_batch(self, a):
        if not a: raise ShellError('usage: batch FILE [continue]   (a file of shell commands, one per line or separated by ;; # starts a comment; stops at the first error unless you add continue)')
        if self.depth >= 4: raise ShellError('batch files nested too deep (4)')
        try: text = open(os.path.expanduser(a[0])).read()
        except OSError as e: raise ShellError('cannot read %s: %s' % (a[0], e.strerror))
        self.depth += 1
        try: self.run_script(text, stop=('continue' not in a[1:]), label=os.path.basename(a[0]))
        finally: self.depth -= 1
    # -------- library programs and registering
    def ensure_kind(self, kind):
        import progs
        if kind in BUILTIN_KINDS or kind in self.programs: return
        if kind in LIBRARY:
            src, exp, out = LIBRARY[kind]; self.programs[kind] = {'name': kind, 'source': src, 'expect': exp, 'out': out}; return
        if kind in made_names():
            rec = json.load(open(os.path.join(MADE, kind + '.json')))
            self.programs[kind] = {'name': kind, 'source': 'programs/made/%s.s' % kind, 'expect': 'programs.made.%s:ref' % kind, 'out': rec['out']}; return
        raise ShellError('unknown kind %r (built in: %s; library: %s; made: %s; or `make` / `register` your own)' % (kind, ', '.join(BUILTIN_KINDS), ', '.join(LIBRARY), ', '.join(made_names()) or 'none'))
    def validate(self, jobs, programs=None):
        """build real tasks from a job list (the registry and the compiler check everything): returns the tasks"""
        import scbatch
        saved = (self.jobs, self.programs)
        self.jobs = jobs
        if programs is not None: self.programs = programs
        try: return self.tasks()
        except Exception as e: raise ShellError(str(e))
        finally: self.jobs, self.programs = saved
    # -------- commands
    def do_add(self, a):
        if not a: raise ShellError('usage: add KIND [numbers... | seq START COUNT STEP] [arg=N] [lw=N|auto] [crit] [out=N]')
        kind, rest = a[0], a[1:]
        self.ensure_kind(kind)
        job = {'kind': kind}; nums = []; i = 0
        while i < len(rest):
            w = rest[i]
            if w == 'seq':
                if i + 3 >= len(rest) and len(rest) - i < 4: raise ShellError('seq needs START COUNT STEP')
                job['inputs'] = {'seq': [num(rest[i + 1]), num(rest[i + 2]), num(rest[i + 3])]}; i += 4; continue
            if w == 'crit': job['crit'] = 1
            elif '=' in w:
                k, v = w.split('=', 1)
                if k == 'arg': job['arg'] = num(v)
                elif k == 'lw': job['lw'] = 'auto' if v == 'auto' else num(v)
                elif k == 'out': job['out_len'] = num(v)
                elif k in ('from', 'argfrom'): job[k] = num(v)
                else: raise ShellError('unknown option %r (arg= lw= out= from= argfrom= crit)' % k)
            else: nums.append(num(w))
            i += 1
        if 'inputs' in job and nums: raise ShellError('give either numbers or seq, not both')
        if 'from' in job and ('inputs' in job or nums): raise ShellError('a job with from=J takes its inputs from the answers of job J: no numbers or seq')
        for k in ('from', 'argfrom'):
            if k in job and not (0 <= job[k] < len(self.jobs)): raise ShellError('%s=%d: no such earlier job (there are %d jobs; a job can only read from a job already added)' % (k, job[k], len(self.jobs)))
        if 'inputs' not in job and 'from' not in job: job['inputs'] = nums
        t = self.validate(self.jobs + [job], dict(self.programs))[-1]
        self.jobs.append(job); self.dirty = True
        self.say('%s job %d: %s %s%s  ->  %s' % (green('added'), len(self.jobs) - 1, cyan(kind), self._short(t.inputs), (' arg=%d' % t.arg) if t.arg else '', yellow(self._short(t.expected()))))
        try:
            import jobcomp
            dsh = self.set['dsh'] or 256; c, d = jobcomp.need([t], 128, dsh)
            if d > dsh: self.say(yellow('warning: this job needs %d shared words in the card\'s shared RAM and a build has %d (setting dsh): `plan` will refuse it on this size. A job is 8 header words + its data + its output (at most %d data words with a one-word answer).' % (d, dsh, dsh - 9)))
        except Exception: pass
    def do_many(self, a):
        if len(a) < 6 or a[2] != 'seq': raise ShellError('usage: many N KIND seq START COUNT STEP [stride=K] [arg=N] [lw=N|auto] [crit]   (N jobs of the same kind, job i starts at START + i*K; K defaults to COUNT, so the data does not repeat)')
        n = num(a[0]); kind = a[1]; st, cnt, step = num(a[3]), num(a[4]), num(a[5])
        if n < 1 or n > 100000: raise ShellError('N must be 1 to 100000')
        stride = cnt; opts = {}
        for w in a[6:]:
            if w == 'crit': opts['crit'] = 1
            elif w.startswith('stride='): stride = num(w[7:])
            elif w.startswith('arg='): opts['arg'] = num(w[4:])
            elif w.startswith('lw='): opts['lw'] = 'auto' if w[3:] == 'auto' else num(w[3:])
            else: raise ShellError('unknown option %r (stride= arg= lw= crit)' % w)
        self.ensure_kind(kind)
        new = [dict(kind=kind, inputs={'seq': [(st + i * stride) & 0xFFFFFFFF, cnt, step]}, **opts) for i in range(n)]
        self.validate(self.jobs + new, dict(self.programs))                  # checked once for all of them (adding one at a time re-checks every job each time)
        self.jobs += new; self.dirty = True
        self.say('%s %d jobs of %s (jobs %d to %d), %d words each' % (green('added'), n, cyan(kind), len(self.jobs) - n, len(self.jobs) - 1, cnt))
    def _newbig_id(self): return 1 + max([(j.get('big') or {}).get('id', -1) for j in self.jobs] + [-1])
    def do_addbig(self, a):
        import bigjobs_v1 as BG, jobcomp
        if len(a) < 2: raise ShellError('usage: addbig KIND DATA [arg=N] [chunk=N] [lw=N] [crit] [combine=RULE]   (data longer than one job can hold)')
        kind, rest = a[0], a[1:]; self.ensure_kind(kind)
        opts = {}; nums = []; inputs = None; i = 0
        while i < len(rest):
            w = rest[i]
            if w == 'seq':
                if len(rest) - i < 4: raise ShellError('seq needs START COUNT STEP')
                st, cnt, step = num(rest[i + 1]), num(rest[i + 2]), num(rest[i + 3]); inputs = [(st + k * step) & 0xFFFFFFFF for k in range(cnt)]; i += 4; continue
            if w == 'crit': opts['crit'] = 1
            elif '=' in w:
                k, v = w.split('=', 1)
                if k in ('arg', 'chunk'): opts[k] = num(v)
                elif k == 'lw': opts['lw'] = 'auto' if v == 'auto' else num(v)
                elif k == 'combine': opts['combine'] = v
                else: raise ShellError('unknown option %r (arg= chunk= lw= combine= crit)' % k)
            else: nums.append(num(w))
            i += 1
        if inputs is not None and nums: raise ShellError('give either numbers or seq, not both')
        data = [x & 0xFFFFFFFF for x in (inputs if inputs is not None else nums)]
        if not data: raise ShellError('no data')
        try: rule, pair = BG.rule_for(kind, opts.get('combine'))
        except BG.BigError as e: raise ShellError(str(e))
        if opts.get('combine') and kind in self.programs and kind in made_names():
            try: pair = BG.rule_for(kind)[1]
            except BG.BigError: pair = False
        dsh = self.set['dsh'] or 256
        if 'chunk' in opts and opts['chunk'] < 1: raise ShellError('chunk must be at least 1')
        chunk = opts.get('chunk') or BG.default_chunk(None, dsh)
        try: parts = BG.split(data, chunk, pair)
        except BG.BigError as e: raise ShellError(str(e))
        gid = self._newbig_id(); new = []
        for k, p in enumerate(parts):
            j = {'kind': kind, 'inputs': p, 'big': {'id': gid, 'part': k, 'of': len(parts), 'rule': rule, 'pair': pair, 'words': len(data)}}
            for key in ('arg', 'lw', 'crit'):
                if key in opts: j[key] = opts[key]
            new.append(j)
        tasks = self.validate(self.jobs + new, dict(self.programs))
        mine = tasks[len(self.jobs):]
        too_big = [j for j in mine if jobcomp.need([j], 128, dsh)[1] > dsh]
        if too_big: raise ShellError('a piece of %d words is still too big for %d shared words: use a smaller chunk=' % (max(len(j.inputs) for j in too_big), dsh))
        want = self.big_expected(kind, data, pair, opts.get('arg', 0), rule, mine, parts)
        self.jobs += new; self.dirty = True
        self.say('%s long job %d: %s, %d words in %d pieces of at most %d (jobs %d to %d); the whole answer is %s' % (green('added'), gid, cyan(kind), len(data), len(parts), chunk, len(self.jobs) - len(new), len(self.jobs) - 1, yellow(self._short(want))))
    def big_expected(self, kind, data, pair, arg, rule, mine, parts):
        """the answer for the whole data: asked of the kind's own Python answer on all the data; if that cannot be done, combined from the pieces' answers"""
        import jobcomp
        try: return jobcomp.Task(kind, data, None, arg).expected()
        except Exception: return __import__('bigjobs_v1').combine(rule, [t.expected() for t in mine], parts)
    def big_groups(self):
        g = {}
        for i, j in enumerate(self.jobs):
            b = j.get('big')
            if b: g.setdefault(b['id'], []).append(i)
        return g
    def check_big(self, path):
        """after a run: combine the pieces' answers from the result file and compare with the answer for the whole data"""
        import bigjobs_v1 as BG
        groups = self.big_groups()
        if not groups: return
        got = {r['job']: r['result'] for r in json.load(open(path))}
        tasks = self.tasks()
        for gid, idx in sorted(groups.items()):
            b = self.jobs[idx[0]]['big']; kind = self.jobs[idx[0]]['kind']
            parts = [self.jobs[i]['inputs'] for i in idx]; arg = self.jobs[idx[0]].get('arg', 0)
            data = BG.whole(parts, b['pair'])
            want = self.big_expected(kind, data, b['pair'], arg, b['rule'], [tasks[i] for i in idx], parts)
            if any(i not in got for i in idx): self.say('long job %d: %s  results missing' % (gid, red('DIFFERENT'))); continue
            have = BG.combine(b['rule'], [got[i] for i in idx], parts)
            ok = have == want
            self.say('long job %d (%s, %d words in %d pieces) -> combined %s   should be %s   %s' % (gid, kind, len(data), len(idx), self._short(have), self._short(want), green('MATCH') if ok else red('DIFFERENT')))
    def _short(self, v):
        v = list(v); return str(v) if len(v) <= 8 else '[%s ... %s] (%d words)' % (', '.join(map(str, v[:4])), ', '.join(map(str, v[-2:])), len(v))
    def do_list(self, a):
        if not self.jobs: return self.say(dim('no jobs yet (add KIND numbers, or open FILE)'))
        seen = set()
        for i, j in enumerate(self.jobs):
            if j.get('big'):                                           # one line for a long job (its pieces are jobs too: `show` and the result file list them)
                if j['big']['id'] in seen: continue
                seen.add(j['big']['id']); idx = [k for k, x in enumerate(self.jobs) if (x.get('big') or {}).get('id') == j['big']['id']]
                self.say('%3d-%-3d %-8s long job %d: %d words in %d pieces, answers combine by %s%s' % (idx[0], idx[-1], cyan(j['kind']), j['big']['id'], j['big']['words'], len(idx), j['big']['rule'], dim(''.join(' %s=%s' % (k, j[k]) for k in ('arg', 'lw') if k in j))))
                continue
            ins = j.get('inputs'); shown = ('answer of job %d' % j['from']) if 'from' in j else (('seq %s' % ins['seq']) if isinstance(ins, dict) else self._short(ins))
            extra = ''.join(' %s=%s' % (k, j[k]) for k in ('arg', 'argfrom', 'lw', 'out_len') if k in j) + (' crit' if j.get('crit') else '')
            if j.get('big'): extra += ' (piece %d of %d of long job %d, answers combine by %s)' % (j['big']['part'] + 1, j['big']['of'], j['big']['id'], j['big']['rule'])
            self.say('%3d  %-8s %s%s' % (i, cyan(j['kind']), shown, dim(extra)))
        self.say(dim('%d job(s)%s%s' % (len(self.jobs), ', file ' + self.name if self.name else '', ' (not saved)' if self.dirty else '')))
    def do_show(self, a):
        tasks = self.tasks()
        if not tasks: return self.say(dim('no jobs yet'))
        for i, t in enumerate(tasks): self.say('%3d  %-8s %s%s  ->  %s' % (i, cyan(t.kind), self._short(t.inputs), (' arg=%d' % t.arg) if t.arg else '', yellow(self._short(t.expected()))))
    def do_remove(self, a):
        if len(a) != 1: raise ShellError('usage: remove N')
        n = num(a[0])
        if not 0 <= n < len(self.jobs): raise ShellError('no job %d (0..%d)' % (n, len(self.jobs) - 1))
        big = self.jobs[n].get('big')
        if big:                                                  # one piece of a long job: the whole group goes (a missing piece would give a wrong answer)
            gone = [i for i, j in enumerate(self.jobs) if (j.get('big') or {}).get('id') == big['id']]
            self.jobs = [j for i, j in enumerate(self.jobs) if i not in gone]; self.dirty = True
            return self.say('%s long job %d: its %d pieces (jobs %s)' % (green('removed'), big['id'], len(gone), ' '.join(map(str, gone))))
        self.jobs.pop(n); self.dirty = True; self.say('%s job %d' % (green('removed'), n))
    def do_dup(self, a):
        if not a: raise ShellError('usage: dup N [TIMES]')
        n = num(a[0]); k = num(a[1]) if len(a) > 1 else 1
        if not 0 <= n < len(self.jobs): raise ShellError('no job %d' % n)
        if self.jobs[n].get('big'): raise ShellError('job %d is a piece of a long job: use addbig again instead of dup' % n)
        for _ in range(k): self.jobs.append(json.loads(json.dumps(self.jobs[n])))
        self.dirty = True; self.say('%s job %d %d time(s); now %d jobs' % (green('copied'), n, k, len(self.jobs)))
    def do_clear(self, a):
        self.jobs = []; self.dirty = True; self.say(green('job list cleared') + dim(' (registered programs kept)'))
    def do_new(self, a):
        self.jobs = []; self.programs = {}; self.name = None; self.dirty = False; self.say(green('new empty job set'))
    def do_save(self, a):
        path = a[0] if a else self.name
        if not path: raise ShellError('usage: save FILE.json')
        if not path.endswith('.json'): path += '.json'
        self.validate(self.jobs, dict(self.programs))
        d = self.doc(); dest = os.path.dirname(os.path.abspath(path))
        if 'programs' in d:                                   # sources are relative to the job file: rewrite them for where it is saved
            d['programs'] = [dict(p, source=p['source'] if os.path.isabs(p['source']) else os.path.relpath(os.path.join(HERE, p['source']), dest)) for p in d['programs']]
        json.dump(d, open(path, 'w'), indent=1); self.name = path; self.dirty = False
        self.say('%s %d job(s) to %s' % (green('saved'), len(self.jobs), cyan(path)))
    def do_open(self, a):
        if len(a) != 1: raise ShellError('usage: open FILE.json')
        d = json.load(open(a[0])); progs_ = {p['name']: p for p in d.get('programs', [])}
        base = os.path.dirname(os.path.abspath(a[0]))
        for p in progs_.values():                       # keep sources relative to the file they were written next to
            if not os.path.isabs(p['source']) and os.path.abspath(base) != HERE: p['source'] = os.path.relpath(os.path.join(base, p['source']), HERE)
        self.validate(d['jobs'], progs_)
        self.jobs, self.programs, self.name, self.dirty = d['jobs'], progs_, a[0], False
        self.say('%s %d job(s) from %s' % (green('opened'), len(self.jobs), cyan(a[0])))
    def do_programs(self, a):
        self.say(bold('built in:  ') + ', '.join(cyan(k) for k in BUILTIN_KINDS))
        self.say(bold('library:   ') + ', '.join(cyan(k) + (green('*') if k in self.programs else '') for k in LIBRARY) + dim('   (* = in this job set; `add` brings one in by itself)'))
        made = made_names()
        self.say(bold('made:      ') + (', '.join(cyan(k) + (green('*') if k in self.programs else '') for k in made) if made else dim('none (see `make`)')))
        mine = [k for k in self.programs if k not in LIBRARY and k not in made]
        self.say(bold('yours:     ') + (', '.join(cyan(k) for k in mine) if mine else dim('none (see `register`)')))
    def do_register(self, a):
        if len(a) < 2: raise ShellError('usage: register NAME FILE.s [expect=module:function|iss] [out=N|same]')
        name, src = a[0], a[1]; expect, out = 'iss', 1
        for w in a[2:]:
            if w.startswith('expect='): expect = w[7:]
            elif w.startswith('out='): v = w[4:]; out = 'same' if v == 'same' else num(v)
            else: raise ShellError('unknown option %r (expect= out=)' % w)
        if name in BUILTIN_KINDS: raise ShellError('%r is a built-in kind' % name)
        if not os.path.exists(src) and not os.path.exists(os.path.join(HERE, src)): raise ShellError('no such file: %s' % src)
        src = os.path.relpath(os.path.abspath(src if os.path.exists(src) else os.path.join(HERE, src)), HERE)       # kept relative to this folder (save rewrites it for the file's own folder)
        p = {'name': name, 'source': src, 'expect': expect, 'out': out}
        self.validate(self.jobs, {**self.programs, name: p})
        self.programs[name] = p; self.dirty = True
        self.say('%s %s from %s (checked: assembles, fits, runs on the interpreter%s)' % (green('registered'), cyan(name), src, '' if expect == 'iss' else ', agrees with its Python answer'))
    def do_make(self, a):
        import jobmaker_v2 as J, importlib
        if not a:
            self.say(bold('make NAME STEP... [then ENDING]') + '  builds a new job kind from a recipe; nothing to write.')
            self.say('  steps    ' + ', '.join(cyan(x) + ' N' for x in J.STEP1) + ', ' + cyan('not') + dim('      (N is a number, or arg = the job\'s own arg)'))
            self.say('  endings  ' + ', '.join(cyan('then ' + x) for x in J.REDUCE) + dim('   (one word out; without an ending: one word out per word in)'))
            self.say('  example  ' + yellow('make bump add 5 xor arg shl 1 then sum') + dim('   then   add bump 1 2 3 arg=255'))
            return
        name, words = a[0], a[1:]
        if name in BUILTIN_KINDS or name in LIBRARY: raise ShellError('%r is already a kind (built in or library); pick another name' % name)
        try: src, ref, out = J.build(name, words)
        except J.RecipeError as e: raise ShellError(str(e))
        files = {n: os.path.join(MADE, name + ext) for n, ext in (('s', '.s'), ('py', '.py'), ('json', '.json'))}
        if os.path.exists(files['s']):
            if [w.lower() for w in json.load(open(files['json']))['words']] == [w.lower() for w in words]:         # same recipe (made by v1 or v2): reuse
                self.programs.pop(name, None); self.ensure_kind(name); self.say('%s %s already made with this recipe; ready to use' % (green('ok'), cyan(name))); return
            raise ShellError('%r was made earlier with a different recipe (%s). Made kinds are never changed: use another name, e.g. %s2' % (name, ' '.join(json.load(open(files['json']))['words']), name))
        os.makedirs(MADE, exist_ok=True)
        for k, text in (('s', src), ('py', ref), ('json', json.dumps({'name': name, 'words': words, 'out': out}, indent=1) + '\n')): open(files[k], 'w').write(text)
        importlib.invalidate_caches()
        try:
            self.do_register([name, 'programs/made/%s.s' % name, 'expect=programs.made.%s:ref' % name, 'out=%s' % out])
        except Exception:
            for f in files.values():
                if os.path.exists(f): os.remove(f)
            self.programs.pop(name, None); raise
        steps, red = J.parse(words)
        try: nruns = J.verify(name, steps, red)
        except Exception as e:
            for f in files.values():
                if os.path.exists(f): os.remove(f)
            self.programs.pop(name, None); raise ShellError(str(e))
        self.say('%s %s: %s' % (green('made'), cyan(name), J.describe(steps, red)))
        self.say(dim('  checked on the interpreter: %d runs (0..17 words, random data and arg) agree with the recipe' % nruns))
        self.say(dim('  code: programs/made/%s.s (`code %s` shows it). Use it:  add %s 1 2 3%s' % (name, name, name, ' arg=N' if any(v == 'arg' for _, v in steps) else '')))
    def do_code(self, a):
        if len(a) != 1: raise ShellError('usage: code KIND   (shows the program of a made or library kind)')
        k = a[0]
        if k in LIBRARY: path = os.path.join(HERE, LIBRARY[k][0])
        elif k in made_names(): path = os.path.join(MADE, k + '.s')
        elif k in self.programs: path = os.path.join(HERE, self.programs[k]['source'])
        else: raise ShellError('no program source for %r (library: %s; made: %s)' % (k, ', '.join(LIBRARY), ', '.join(made_names()) or 'none'))
        for ln in open(path).read().rstrip('\n').split('\n'): self.say(dim(ln) if ln.lstrip().startswith('#') else ln)
    def do_set(self, a):
        if not a: return self.do_settings([])
        if len(a) != 2: raise ShellError('usage: set NAME VALUE   (settings lists the names)')
        k, v = a[0], a[1]
        if k not in SETTINGS: raise ShellError('unknown setting %r (%s)' % (k, ', '.join(SETTINGS)))
        if k in ('blocks', 'slices', 'unit-lw', 'imem', 'dsh', 'far-words'): val = None if v == 'none' else num(v)
        elif k == 'lw': val = None if v == 'none' else ('auto' if v == 'auto' else num(v))
        elif k == 'order':
            if v not in ('auto', 'kind', 'width'): raise ShellError('order: auto, kind or width')
            val = v
        elif k == 'openocd':
            if v == 'none': val = None; self.cfg.pop('openocd', None)
            else:
                pth = os.path.expanduser(v)
                if not (os.path.isfile(pth) and os.access(pth, os.X_OK)): raise ShellError('no executable openocd at %s' % v)
                val = pth; self.cfg['openocd'] = pth
            ST.save_config(self.cfg); self.pick_openocd(val); self.say(green('saved in the config; ' + (self.openocd_line or 'no openocd found'))); self.set[k] = val; return
        elif k == 'linkcheck':
            if v not in ('on', 'off'): raise ShellError('linkcheck: on or off')
            val = (v == 'on')
        elif k == 'estimate':
            if v not in ('on', 'off'): raise ShellError('estimate: on or off')
            val = (v == 'on')
        elif k == 'margin': val = float(v)
        elif k == 'profile': val = None if v == 'none' else v
        else: val = v
        self.set[k] = val; self.say('%s %s = %s' % (green('set'), cyan(k), yellow(str(val))))
    def do_settings(self, a):
        for k, (d, h) in SETTINGS.items(): self.say('%-9s %-22s %s' % (cyan(k), yellow(str(self.set[k])), dim(h)))
    def scargs(self, tmp, plan):
        s = self.set; args = ['--plan', tmp] if plan else [s['port'], tmp]
        args += ['--blocks', str(s['blocks']), '--submit-order', s['order']]
        if s['lw'] is not None: args += ['--lw', str(s['lw'])]
        if s['profile']: args += ['--profile', s['profile']]
        if s['estimate']: args += ['--estimate', '--estimate-margin', str(s['margin'])]
        if s['slices'] is not None: args += ['--slices', str(s['slices'])]
        if s['unit-lw'] is not None: args += ['--unit-lw', str(s['unit-lw'])]
        if s['imem'] is not None: args += ['--imem', str(s['imem'])]
        if s['dsh'] is not None: args += ['--dsh', str(s['dsh'])]
        if s['far-words'] is not None: args += ['--far-words', str(s['far-words'])]
        if not plan: args += ['--out', s['out']]
        return args
    def _call_scblocks(self, args):
        import scblocks
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): rc = scblocks.main(args)
        return rc, buf.getvalue()
    def do_plan(self, a):
        if not self.jobs: raise ShellError('no jobs yet')
        self.validate(self.jobs, dict(self.programs)); tmp = self.tmpfile()
        try: rc, text = self._call_scblocks(self.scargs(tmp, True))
        finally: os.remove(tmp)
        for ln in text.rstrip().split('\n'): self.say(ln)
        if rc: self.err('plan stopped (code %d)' % rc)
    def _fits_fn(self):
        """-> fits(ids): can these jobs be planned as ONE run on the build the settings describe? (host-side planner; the card is not touched)"""
        import scblocks, jobcomp_v2 as C
        s = self.set; tasks = self._tasks_of(self.resolve_all(self.jobs))
        if isinstance(s['lw'], int):
            for tk in tasks: tk.lw = s['lw']
        far = s['far-words'] or (1 << 16)
        def fits(ids):
            try:
                scblocks.plan_blocks([tasks[i] for i in ids], s['blocks'], imem=s['imem'] or 128, dsh=s['dsh'] or 256, far_words=far, slices=s['slices'], unit_lw=s['unit-lw'], say=lambda *x, **k: None, order=s['order'])
                return True
            except C.JobCompError as e: fits.last = str(e); return False
        fits.last = ''
        return fits
    @staticmethod
    def _ranges(ids):
        out, i = [], 0
        while i < len(ids):
            j = i
            while j + 1 < len(ids) and ids[j + 1] == ids[j] + 1: j += 1
            out.append(str(ids[i]) if i == j else '%d-%d' % (ids[i], ids[j])); i = j + 1
        return ','.join(out)
    def _plan_waves(self):
        self.validate(self.jobs, dict(self.programs)); fits = self._fits_fn()
        try: return WV.plan_waves(self.jobs, fits)
        except WV.WaveError as e: raise ShellError('%s%s' % (e, (' (' + fits.last + ')') if fits.last else ''))
    def do_waves(self, a):
        if not self.jobs: raise ShellError('no jobs yet')
        waves = self._plan_waves(); lv = len({l for l, _ in waves})
        self.say('%s %d jobs in %d wave%s%s (planned for blocks %d, %s code words, %s shared words, far RAM %s words; the card is not touched)' % (bold('wave plan:'), len(self.jobs), len(waves), '' if len(waves) == 1 else 's',
                 (', %d stages (a job reads the answers of earlier jobs)' % lv) if WV.has_refs(self.jobs) else '', self.set['blocks'], self.set['imem'] or 128, self.set['dsh'] or 256, self.set['far-words'] or 65536))
        for n, (l, ids) in enumerate(waves, 1): self.say('  wave %d%s: jobs %s (%d)' % (n, (' (stage %d)' % (l + 1)) if lv > 1 else '', self._ranges(ids), len(ids)))
    def run_waves(self, why=None):
        """run the design in waves: each wave is an ordinary run of the jobs that fit; the answers are read back between waves and a later wave is fed from them"""
        import collections
        waves = collections.deque(self._plan_waves()); total = len(waves); got, done_w = {}, 0
        self.say('%s %d jobs in %d wave%s%s' % (yellow('waves:'), len(self.jobs), total, '' if total == 1 else 's', (' (' + why + ')') if why else ''))
        correct = clocks = 0; slowest_sum = 0; n_jobs = 0
        while waves:
            lvl, ids = waves.popleft(); done_w += 1
            try: wjobs = [WV.resolve(self.jobs[i], got) for i in ids]
            except WV.WaveError as e: raise ShellError(str(e))
            fd, tmp = tempfile.mkstemp(prefix='score_shell_', suffix='.json', dir=HERE); os.close(fd)
            fd, outp = tempfile.mkstemp(prefix='score_shell_', suffix='.out.json', dir=HERE); os.close(fd)
            d = {'jobs': wjobs}
            if self.programs: d['programs'] = list(self.programs.values())
            json.dump(d, open(tmp, 'w'))
            args = self.scargs(tmp, False); args[args.index('--out') + 1] = outp
            try:
                rc, text = self._call_scblocks(args)
                res = json.load(open(outp)) if os.path.getsize(outp) else []
            finally:
                os.remove(tmp); os.remove(outp)
            if rc and 'far-RAM area ends' in text and len(ids) > 1:        # the host plan was too hopeful: halve this wave and go on
                h = len(ids) // 2; waves.appendleft((lvl, ids[h:])); waves.appendleft((lvl, ids[:h])); total += 1; done_w -= 1
                self.say(yellow('  wave of %d jobs did not fit far RAM on the card; split into %d and %d' % (len(ids), h, len(ids) - h))); continue
            m = re.search(r'(\d+) of (\d+) jobs correct', text); ck = [int(x) for x in re.findall(r'(\d+) clocks = ', text)]
            self.say('  wave %d%s: jobs %s (%d): %s%s' % (done_w, (' (stage %d)' % (lvl + 1)) if WV.has_refs(self.jobs) else '', self._ranges(ids), len(ids),
                     (m.group(0) if m else 'no result line'), (', slowest block %d clocks' % max(ck)) if ck else ''))
            if rc or not m or len(res) != len(ids):
                for ln in text.rstrip().split('\n')[-12:]: self.say(ln)
                self.runlog.append(dict(correct=correct, total=len(self.jobs), slowest=slowest_sum or None, clocks=clocks or None, lw=self.set['lw'], blocks=self.set['blocks'], build=(self.build or {}).get('name'), finished=False, waves=done_w))
                raise ShellError('wave %d did not finish cleanly (code %d); the earlier waves\' answers are kept in memory only, nothing was compared' % (done_w, rc))
            for r in res: got[ids[r['job']]] = r['result']
            correct += int(m.group(1)); n_jobs += int(m.group(2)); clocks += sum(ck); slowest_sum += max(ck) if ck else 0
        out = [{'job': i, 'kind': self.jobs[i]['kind'], 'result': got[i]} for i in range(len(self.jobs))]
        json.dump(out, open(self.set['out'], 'w')); self.say('results of all %d jobs written to %s' % (len(out), self.set['out']))
        self.say('%d of %d jobs correct (all waves; each wave checked against the answers of the data it was fed)' % (correct, n_jobs))
        self.runlog.append(dict(correct=correct, total=n_jobs, slowest=slowest_sum or None, clocks=clocks or None, lw=self.set['lw'], blocks=self.set['blocks'], build=(self.build or {}).get('name'), finished=True, waves=total))
        self.do_check([self.set['out']]); self.check_big(self.set['out'])
    def do_run(self, a):
        if not self.jobs: raise ShellError('no jobs yet')
        self.link_preflight(ping=True)
        self.check_card()
        self.validate(self.jobs, dict(self.programs))
        if WV.has_refs(self.jobs): return self.run_waves('a job reads the answers of earlier jobs')
        tmp = self.tmpfile()
        try: rc, text = self._call_scblocks(self.scargs(tmp, False))
        finally: os.remove(tmp)
        if rc and 'far-RAM area ends' in text: return self.run_waves('the design does not fit the far RAM in one run')
        m = re.search(r'(\d+) of (\d+) jobs correct', text); ck = [int(x) for x in re.findall(r'(\d+) clocks = ', text)]
        self.runlog.append(dict(correct=int(m.group(1)) if m else None, total=int(m.group(2)) if m else len(self.jobs), slowest=max(ck) if ck else None, clocks=sum(ck) if ck else None,
                                lw=self.set['lw'], blocks=self.set['blocks'], build=(self.build or {}).get('name'), finished=(rc == 0 and m is not None)))
        for ln in text.rstrip().split('\n'):
            self.say(green(ln) if 'jobs correct' in ln and ln.split()[0] == ln.split()[2] else ln)
        if rc: return self.err('the run did not finish cleanly (code %d); nothing to compare' % rc)
        self.do_check([self.set['out']])
        self.check_big(self.set['out'])
    def do_check(self, a):
        if len(a) != 1: raise ShellError('usage: check RESULT.json   (the file run wrote)')
        import ladder_show
        tmp = self.tmpfile()
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf): rc = ladder_show.main([tmp, a[0]])
        finally: os.remove(tmp)
        for ln in buf.getvalue().rstrip().split('\n'): self.say(ln.replace('MATCH', green('MATCH')).replace('DIFFERENT', red('DIFFERENT')))
    def do_profile(self, a):
        import sc_calibrate_v1 as K
        if not a:
            names = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(K.PROFILE_DIR, '*.json')))
            return self.say(bold('profiles: ') + (', '.join(cyan(n) for n in names) or dim('none')))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): K.show(K.load_profile(a[0]))
        self.say(buf.getvalue().rstrip())
        try:
            import lengthest_v1 as E
            m = E.fit_model(K.load_profile(a[0]))
            self.say('%s %.1f clocks per instruction (crc32), kinds measured: %s' % (bold('length model:'), m.cpi, m.kind_cpi or 'none'))
        except Exception as e: self.say(dim('(no length model: %s)' % e))
    # -------- the build store (ledger #1534)
    def store_dir(self):
        return self.cfg.get('store')
    def do_store(self, a):
        if a:
            p = os.path.abspath(os.path.expanduser(a[0]))
            if not os.path.isdir(p): raise ShellError('no such folder: %s' % p)
            self.cfg['store'] = p; ST.save_config(self.cfg); self.say('%s %s' % (green('store'), cyan(p)))
        else:
            self.say('store: %s' % (cyan(self.cfg['store']) if self.cfg.get('store') else dim('not set (set one with: store FOLDER)')))
        self.say(dim('searched: ' + ', '.join(ST.search_dirs(self.cfg.get('store')))))
    def do_builds(self, a):
        bl = ST.find_builds(self.cfg.get('store'))
        if not bl: return self.say(dim('no builds found'))
        self.say(bold('%-20s %-9s %-7s %-5s %-9s %-8s %-9s %-8s %s' % ('build', 'blocks x S', 'lanes', 'imem', 'LUTs', 'setup ns', 'Kintex', 'bitfile', 'card')))
        for b in bl:
            f = b['fits']['kintex_xc7k480t']; ok, _ = ST.timing_verdict(b)
            fit = f['fit']; fc = green if fit == 'recommended' else (yellow if fit in ('tight', 'possible') else red)
            tm = ('%+.3f' % b['timing']['setup']) if b['timing'] else '?'
            self.say('%-20s %-9s %-7s %-5d %-9s %-8s %s %-8s %s' % (cyan(b['name']), '%d x %d' % (b['blocks'], b['slices']), str(b['lanes'] or '-'), b['imem'],
                     ('%d' % b['luts']) if b['luts'] else (('~%d' % b['predicted']) if b['predicted'] else '?'), (red(tm) if ok is False else tm).ljust(8),
                     fc(fit.ljust(9)), green('yes') if b['bit'] else dim('no'), dim((b['card'] or '')[:46])))
    def do_target(self, a):
        tg = json.load(open(os.path.join(HERE, 'targets_v1.json')))
        for k, t in tg.items():
            if k.startswith('_'): continue
            self.say('%s  %s' % (cyan(k), t['name']))
            self.say('    %d %s, %s MHz, working target %d %% = %d LUTs%s' % (t['luts'], t['lut_kind'], t['clock_mhz'], int(100 * t['target_fraction']), int(t['target_fraction'] * t['luts']),
                     '' if t.get('s_core_builds_measured') else '; ' + yellow('no S-Core pool has been built for this board, so fit is unknown')))
        self.say(dim('`fit NB S ULW NU IMEM` says what a design size would need; `builds` shows the fit of each known build'))
    def do_fit(self, a):
        if len(a) < 4: raise ShellError('usage: fit BLOCKS SLICES ULW UNITS [IMEM]   (ULW: log2 of the lanes of a fusion unit, 0 = none; example: fit 8 32 5 1 1024)')
        nb, s, ulw, nu = [num(x) for x in a[:4]]; imem = num(a[4]) if len(a) > 4 else 128
        m = M.manifest(nb, s, ulw, nu, imem)
        p = m['predicted_luts']
        self.say('%s %d blocks of %d slices = %d slices, %s, %d code words' % (bold('design:'), nb, s, nb * s, ('fusion units of %d lanes, %d per block' % (1 << ulw, nu)) if ulw else 'no fusion units', imem))
        self.say('predicted LUTs: %s (%s)' % (('%d' % p['low'] if p['low'] == p['high'] else '%d to %d' % (p['low'], p['high'])) if p['low'] else 'not known', p['basis']))
        for k, r in m['targets'].items():
            fc = green if r['fit'] == 'recommended' else (yellow if r['fit'] in ('tight', 'possible') else red if r['fit'] == 'no' else dim)
            self.say('  %-18s %s  %s%s' % (k, fc(r['fit'].ljust(11)), ('%.0f %%  ' % (100 * r['lut_fraction'][1])) if 'lut_fraction' in r else '', dim(r['why'])))
    def do_use(self, a):
        if len(a) != 1: raise ShellError('usage: use BUILD   (builds lists them)')
        try: b = ST.get_build(self.cfg.get('store'), a[0])
        except KeyError as e: raise ShellError(str(e.args[0]))
        for k, v in ST.host_settings(b).items(): self.set[k] = v
        self.build = b; JX.install(int(b.get('mul_units') or 0))
        self.say('%s %s: blocks %d, slices %d, unit-lw %s, imem %d' % (green('using'), cyan(b['name']), b['blocks'], b['slices'], self.set['unit-lw'], b['imem']))
        ok, text = ST.timing_verdict(b)
        self.say('timing: %s' % (green(text) if ok else red(text) if ok is False else yellow(text)))
        if not b['bit']: self.say(yellow('no bitstream for it in the store; plan works, load and run need one'))
        self.card_note(b)
    def card_note(self, b):
        """say whether the build just chosen is the one on the card (use only changes the host's settings)"""
        if self.card_build == b['name']: self.say(green('this build is on the card (%s)' % ('loaded in this session' if self.card_src == 'loaded' else 'its label is on the card')))
        elif self.card_build: self.say(yellow('host settings only: the card still holds %s. `load %s` puts this one on the card.' % (self.card_build, b['name'])))
        else: self.say(yellow('host settings only: the shell does not know what is on the card (nothing loaded in this session, no label read yet: `card` reads it). `load %s` puts this one there.' % b['name']))
    def _card_run(self, args):
        """run card_label_v1.py through the shell's runner (needs the card link) -> (return code, parsed report, text)"""
        r = self.runner([sys.executable, os.path.join(HERE, 'card_label_v1.py')] + list(args), capture_output=True, text=True, cwd=HERE)
        text = (r.stdout or '') + (r.stderr or '')
        return r.returncode, CL.parse_report(r.stdout or ''), text
    @staticmethod
    def _label_ok(d):
        """is the label on the card believable: it must agree with what the board reports -> (ok, why not)"""
        lab, bd = d.get('label'), d.get('board')
        if not lab: return False, d.get('why') or 'no label'
        if bd and (lab['slices'] != bd['S'] or lab['imem'] != bd['imem']): return False, 'the label says %d slices and %d code words, the board reports %d and %d' % (lab['slices'], lab['imem'], bd['S'], bd['imem'])
        if d.get('blocks') is not None and lab['blocks'] != d['blocks']: return False, 'the label says %d blocks, the probe counted %d' % (lab['blocks'], d['blocks'])
        return True, ''
    def _take(self, d):
        """remember what a report said; trust the label only when it agrees with the board"""
        self.card_info = dict(board=d.get('board'), blocks=d.get('blocks'), label=d.get('label'), why=d.get('why'), t=time.time())
        ok, why = self._label_ok(d)
        self.card_info['label_ok'] = ok; self.card_info['label_why'] = why
        return ok, why
    def label_step(self, b):
        """after a successful load or a stamp: write the label, count the blocks, compare with the build.  False = the card does not match the build"""
        args = ['write', b['name'], str(b['blocks']), str(b['slices']), str(b['lanes'] or 0), str(b['units'] if b['lanes'] else 0), str(b['imem']), '0']
        try: rc, d, text = self._card_run(args)
        except Exception as e: rc, d, text = 1, CL.parse_report(''), str(e)
        self._learned = True
        if d.get('blocks') is not None: self.card_info = dict(board=d.get('board'), blocks=d['blocks'], label=d.get('label'), why=None, t=time.time(), label_ok=bool(d.get('label')), label_why='')
        if d.get('blocks') is not None and d['blocks'] != b['blocks']:
            self.err('the card reports %d blocks but the build %s has %d' % (d['blocks'], b['name'], b['blocks']))
            self.card_build = None; self.card_src = None; return False
        if rc == 0 and d.get('written'): self.label_written = True; self.say(green('label written on the card (far RAM 0x0100): %s, the card has %s blocks' % (b['name'], d['blocks'])))
        else:
            last = [l for l in text.strip().split('\n') if l.strip()][-1:] or ['no answer']
            self.say(yellow('could not write the label on the card (%s); the load itself is fine, and the shell remembers it for this session' % last[0][:120]))
        return True
    def learn_card(self):
        """read the card's report and label; take the label as what is on the card when it agrees with the board"""
        self._card_err = ''
        try: rc, d, text = self._card_run(['read'])
        except Exception as e: self._card_err = str(e); return None
        if rc != 0 or not d.get('board'): self._card_err = text; return None       # a failed read is not 'learned': the next run or card tries again
        self._learned = True
        ok, why = self._take(d)
        if ok and self.card_build != d['label']['name']: self.card_build = d['label']['name']; self.card_src = 'label'
        return d
    def pick_openocd(self, user=None):
        """choose, apply and remember which openocd this shell uses (openocd_path_v1.py)"""
        self.openocd_path, self.openocd_line = OP.choose(user)
    def _unread_reason(self):
        """why a card read failed, in the helper's own words plus what to check"""
        text = getattr(self, '_card_err', '') or ''
        last = [l for l in text.strip().split('\n') if l.strip()][-1:]
        d = LC.diagnose(text)
        return ((last[0][:140] + '. ') if last else 'no answer. ') + (d if d else 'check that the header board and the USB lead are seated, that the card is powered and that a build is loaded')
    def link_preflight(self, ping=False):
        """ledger #1564: before sending to the card, check the USB adapter (and with ping=True the card's answer).  Stops with a plain sentence when the link is not sound."""
        if not self.set.get('linkcheck'): return
        st, msg = self.watch.check()
        if st == 'missing': raise ShellError(msg)
        if st == 'dropped': self.say(yellow(msg))
        if not ping: return
        try: r = self.runner([sys.executable, os.path.join(HERE, 'link_check_v2.py'), 'ping'], capture_output=True, text=True, cwd=HERE)
        except Exception as e: raise ShellError('the link check could not run: %s' % e)
        text = (r.stdout or '') + (r.stderr or '')
        if r.returncode != 0:
            bad = [l for l in text.strip().split('\n') if l.startswith('PING FAILED')] or [l for l in text.strip().split('\n') if l.strip()][-1:] or ['no answer']
            raise ShellError('the link to the card failed its check, nothing was sent: %s%s' % (bad[0][:160], ('. ' + LC.diagnose(text)) if LC.diagnose(text) else '. Reseat the header board and the USB lead, then try again'))
        self.say(dim('link checked: the board answers' + ('' if st != 'dropped' else ' (but see the adapter warning above)') + ((' [' + self.openocd_line + ']') if getattr(self, 'openocd_line', None) else '')))
    def explain_link(self, text):
        """after an error: if it looks like a link problem say what to look at, and whether the adapter dropped off USB"""
        d = LC.diagnose(text)
        if not d: return
        self.say(yellow('what to check: ' + d))
        if self.set.get('linkcheck'):
            st, msg = self.watch.check()
            if st in ('dropped', 'missing'): self.say(yellow(msg))
    def do_card(self, a):
        if a and a[0] == 'stamp': return self.card_stamp(a[1:])
        if a: raise ShellError('usage: card   or   card stamp BUILD')
        cur = (self.build or {}).get('name')
        self.link_preflight(ping=False)
        if getattr(self, 'openocd_line', None): self.say(dim(self.openocd_line))
        d = self.learn_card()
        if d is None:
            self.say(yellow('could not read the card: %s; last known, NOT confirmed now:' % self._unread_reason()))
            if self.card_build: self.say('  %s: %s' % ('on the card by the label read earlier' if self.card_src == 'label' else 'loaded in this session', green(self.card_build)))
            else: self.say(yellow('  nothing was loaded in this session'))
        else:
            b = d['board']; self.say('the card reports: version %d, %s blocks, %d slices per block, %d code words, shared RAM %d words' % (b['version'], d['blocks'], b['S'], b['imem'], b['shared']))
            ci = self.card_info
            if d.get('label'):
                lab = d['label']; when = time.strftime('%H:%M:%S %d %b', time.localtime(lab['time']))
                if ci['label_ok']: self.say('label on the card: %s (written %s; %s blocks, %d slices, %d lanes, %d code words)' % (green(lab['name']), when, lab['blocks'], lab['slices'], lab['lanes'], lab['imem']))
                else: self.say(yellow('label on the card names %s but it is not trusted: %s' % (lab['name'], ci['label_why'])))
            else:
                self.say(yellow('no label on the card (%s): it was loaded by hand or never by this shell since power-up. `card stamp BUILD` records one after checking the board.' % (d.get('why') or 'none')))
                if self.card_build and self.label_written: self.say(yellow('this session loaded %s, so the card was probably reloaded by hand since: the shell no longer says what is on it' % self.card_build)); self.card_build = None; self.card_src = None; self.label_written = False
            if not (d.get('label') and ci['label_ok']) and self.card_src == 'label': self.card_build = None; self.card_src = None
        self.say('chosen for the host settings: %s' % (cyan(cur) if cur else 'none'))
        if self.card_build and cur and cur != self.card_build: self.say(red('they differ: run will refuse. `load %s` or `use %s`' % (cur, self.card_build)))
        elif not self.card_build: self.say(yellow('what is on the card is not known to the shell: run does not check the build, only the block count'))
    def card_stamp(self, a):
        if len(a) != 1: raise ShellError('usage: card stamp BUILD   (after loading a build by hand: checks the board against the build, then writes the label)')
        try: b = ST.get_build(self.cfg.get('store'), a[0])
        except KeyError as e: raise ShellError(str(e.args[0]))
        rc, d, text = self._card_run(['read'])
        if rc != 0 or not d.get('board'): self._card_err = text; raise ShellError('could not read the card: %s' % self._unread_reason())
        bad = []
        if d['board']['S'] != b['slices']: bad.append('the board has %d slices per block, %s has %d' % (d['board']['S'], b['name'], b['slices']))
        if d['board']['imem'] != b['imem']: bad.append('the board has %d code words, %s has %d' % (d['board']['imem'], b['name'], b['imem']))
        if d['blocks'] != b['blocks']: bad.append('the card has %s blocks, %s has %d' % (d['blocks'], b['name'], b['blocks']))
        if bad:
            for m in bad: self.err(m)
            self.say(dim('nothing was written; the card does not match that build')); return
        self.card_build = b['name']; self.card_src = 'loaded'
        if self.label_step(b):
            self.set.update(ST.host_settings(b)); self.build = b; JX.install(int(b.get('mul_units') or 0))
            self.say(green('now on the card: %s (stamped; the board matches the build)' % b['name']))
    def check_card(self):
        if self.card_build is None and self.label_check and not self._learned: self.learn_card()
        cur = (self.build or {}).get('name')
        if self.card_build and cur and cur != self.card_build:
            raise ShellError('the card holds %s but the settings are for %s: `load %s` first, or `use %s` to plan for what is on the card' % (self.card_build, cur, cur, self.card_build))
        ci = self.card_info
        if ci and ci.get('blocks') and self.set['blocks'] and int(self.set['blocks']) > ci['blocks']:
            raise ShellError('the settings ask for %s blocks but the card has %d: `set blocks %d`, or `use` a build with that many' % (self.set['blocks'], ci['blocks'], ci['blocks']))
    def do_load(self, a):
        if not a: raise ShellError('usage: load BUILD [confirm]   (loads the bitstream into the card SRAM, then runs the first-read test and checks the board against the build)')
        confirm = 'confirm' in a[1:]
        self.link_preflight(ping=False)
        try: b = ST.get_build(self.cfg.get('store'), a[0])
        except KeyError as e: raise ShellError(str(e.args[0]))
        loader = ST.find_loader({'loader': self.set['loader']} if self.set['loader'] else self.cfg)
        ok, msg = ST.load_bitstream(b, confirm=confirm, loader=loader, runner=self.runner)
        if not ok: raise ShellError(msg)
        self.say(green(msg))
        self.card_build = b['name']; self.card_src = 'loaded'; self.label_written = False; self._learned = False      # the bitstream is in the card's SRAM now (the checks below may still fault it)
        for k, v in ST.host_settings(b).items(): self.set[k] = v
        self.build = b; JX.install(int(b.get('mul_units') or 0))
        info, text = ST.first_read(runner=self.runner)
        bad = ST.compare_board(b, info)
        if bad:
            for m in bad: self.err(m)
            self.card_build = None; self.card_src = None; self.say(yellow('the card does not match the build: the shell no longer says what is on it'))
            self.say(dim(text.strip()[-400:])); return
        self.say(green('first-read test healthy; the board reports %s slices per block and %s code words, as the build says' % (info.get('S'), info.get('imem_words'))))
        if not self.label_step(b): return
        self.say(green('now on the card: %s (loaded in this session)' % b['name']))
        self.say('settings now: blocks %d, unit-lw %s, imem %d' % (self.set['blocks'], self.set['unit-lw'], self.set['imem']))
    def do_help(self, a):
        if a:
            c = a[0].lower()
            if c not in self.cmds: raise ShellError('no command %r' % c)
            _, usage, text = self.cmds[c]; self.say(bold(usage)); self.say(text); return
        w = max(len(u) for _, u, _ in self.cmds.values())
        for group, names in GROUPS:
            self.say(bold(group))
            for n in names:
                _, usage, text = self.cmds[n]; self.say('  %s  %s' % (cyan(usage.ljust(w)), text.split('\n')[0]))
        self.say(dim('`help COMMAND` for more; Tab completes; `quit` leaves.'))
    def do_quit(self, a):
        if self.dirty and self.jobs and not getattr(self, 'quit_warned', False):
            self.quit_warned = True; return self.say(yellow('the job list is not saved (save FILE.json); type quit again to leave anyway'))
        self.quit = True

# (command name -> (method suffix, usage line, help text)); the order here is the order of SHELL_v11.md
COMMANDS = {
    'add':      ('add', 'add KIND DATA [arg=N] [lw=N|auto] [crit] [from=J] [argfrom=J]', 'add a job. DATA is numbers (hex ok) or `seq START COUNT STEP`. The expected answer is shown at once.\nExamples:  add vsum 1 2 3 4     add vmax seq 5 80 3     add vxor 1 2 3 arg=255\nKinds: built in vsum vscale vstress; library crc32 vgain vmax vprefix vmin vxor vcount (brought in by themselves); or your own (register).'),
    'addbig':   ('addbig', 'addbig KIND DATA [arg=N] [chunk=N] [lw=N] [crit] [combine=RULE]', 'add a job whose data is longer than one job can hold (about 247 words at 256 shared words): the data is cut into pieces, each piece is an ordinary job, and run puts the answers back together and compares them with the answer for the whole data.\nExamples:  addbig vsum seq 1 1000 1     addbig vgain seq 1 500 1 arg=128 chunk=60     addbig mymax seq 5 800 7 combine=max\nFor per-word kinds the answers are joined; for totals (sum min max xor or and) the totals of the pieces are totalled again; vprefix carries the running sum across. crc32 and recipes with diff / prefix cannot be split.'),
    'list':     ('list', 'list', 'the jobs typed so far, numbered.'),
    'show':     ('show', 'show', 'the jobs with the answers they should give (computed on this computer).'),
    'remove':   ('remove', 'remove N', 'delete job number N.'),
    'dup':      ('dup', 'dup N [TIMES]', 'copy job N (once or TIMES times) at the end of the list.'),
    'clear':    ('clear', 'clear', 'delete all jobs (registered programs stay).'),
    'new':      ('new', 'new', 'start again: no jobs, no registered programs.'),
    'save':     ('save', 'save FILE.json', 'write the jobs as a job file (the same format scblocks.py reads). Checks everything first.'),
    'open':     ('open', 'open FILE.json', 'read a job file (checks it) and replace the current jobs.'),
    'many':     ('many', 'many N KIND seq START COUNT STEP [stride=K] [arg=N] [lw=N|auto] [crit]', 'add N jobs of one kind at once (a big design in one line): job i has COUNT words starting at START + i*K (K defaults to COUNT, so the data does not repeat). Checked once for all N.\nExample: many 500 vsum seq 1 40 1'),
    'waves':    ('waves', 'waves', 'show how the whole design would be run in waves on the build the settings describe (blocks, imem, dsh, far-words, slices, lw), without touching the card. A design that fits in one run is one wave. `run` does this by itself when the design does not fit far RAM in one run, or when a job reads the answers of earlier jobs.'),
    'batch':    ('batch', 'batch FILE [continue]', 'run a file of shell commands in one go: design the jobs (make, add, open), choose the build (use, load), set options and run, as many times as you like. One command per line or separated by ;, # starts a comment. Stops at the first error unless you add continue; at the end it lists every run (jobs correct, slowest block, lw). A batch file may call another batch (up to 4 deep).'),
    'programs': ('programs', 'programs', 'the kinds you can use: built in, library, yours.'),
    'register': ('register', 'register NAME FILE.s [expect=module:function|iss] [out=N|same]', 'make your own program a kind (see PROGRAMS.md). It is checked at once: assembles, fits, runs on the interpreter, agrees with your Python answer.'),
    'make':     ('make', 'make NAME STEP... [then ENDING]', 'build a NEW job kind from a recipe, no program to write. Steps: add sub xor and or shl shr (each with a number or arg) and not. Ending (optional): then sum|xor|or|and|min|max.\nExamples:  make bump add 5 xor arg shl 1 then sum     make flip not     make top16 shr 16 then max\nIt writes the program and the right answer, checks both on the interpreter, and keeps the kind (programs/made/) for later sessions. A made kind is never changed: use a new name.'),
    'code':     ('code', 'code KIND', 'show the program (assembly) of a made, library or registered kind.'),
    'settings': ('settings', 'settings', 'the settings and their values.'),
    'set':      ('set', 'set NAME VALUE', 'change a setting: blocks, lw (0..4 | auto | none), order, profile, estimate on|off, margin, slices, unit-lw, port, out.\nExample: set lw auto   set profile example_2x8_nu3_v2   set estimate on'),
    'plan':     ('plan', 'plan', 'what the host would do with these jobs and settings: batches, widths, submit order. No card needed.'),
    'run':      ('run', 'run', 'run the jobs on the card; a design too big for one run, or a pipeline (a job with from=J / argfrom=J reads the answers of job J), runs in waves by itself (needs the link; start the shell with `nix shell nixpkgs#openocd --command python3 score_shell_v11.py`), then compare with the right answers.'),
    'check':    ('check', 'check RESULT.json', 'compare a result file from the card with the right answers (run does this by itself).'),
    'profile':  ('profile', 'profile [NAME]', 'list the card profiles, or show one with its length model.'),
    'store':    ('store', 'store [FOLDER]', 'the folder where your generated Verilog, manifests, bitstreams and timing reports live (kept between sessions). Without a folder: show it. The k7 folder of this checkout is always searched too.'),
    'builds':   ('builds', 'builds', 'the builds known: size, lanes, code words, LUTs (measured, or ~predicted), setup slack, whether it fits the Kintex card (recommended = within the 80 % working target, tight = over it, no = does not fit), whether the bitstream is in the store, and what the card showed.'),
    'target':   ('target', 'target', 'the boards known (Kintex card, Tang Nano 20K) with their size and working target; says which have S-Core builds measured.'),
    'fit':      ('fit', 'fit BLOCKS SLICES ULW UNITS [IMEM]', 'what a design size would cost and which boards it fits (no build needed). ULW = log2 of the lanes of a fusion unit (0 = none, 4 = 16 lanes, 5 = 32 lanes).\nExample: fit 8 32 5 1 1024'),
    'card':     ('card', 'card [stamp BUILD]', 'read the card: what it reports (blocks counted, slices, code words) and the label the shell wrote there after a load; says whether it is the chosen build. `card stamp BUILD` writes the label for a build loaded by hand, after checking that the board matches it.'),
    'use':      ('use', 'use BUILD', 'choose a build: sets blocks, slices, unit-lw and imem to the build\'s own, and shows its timing.'),
    'load':     ('load', 'load BUILD [confirm]', 'load the build\'s bitstream into the card SRAM (never the flash), then run the first-read test and check the board against the build. Refuses a build whose timing failed; a build whose timing is unknown needs the word confirm. Needs the shell started inside `nix shell nixpkgs#openocd`.'),
    'help':     ('help', 'help [COMMAND]', 'this list, or the help for one command.'),
    'quit':     ('quit', 'quit', 'leave (warns once if the jobs are not saved).'),
}
GROUPS = [('Jobs', ['add', 'many', 'addbig', 'list', 'show', 'remove', 'dup', 'clear', 'new', 'save', 'open']),
          ('Programs', ['programs', 'make', 'code', 'register']),
          ('Settings', ['settings', 'set']),
          ('Builds and card', ['store', 'builds', 'target', 'fit', 'use', 'load', 'card']),
          ('Run', ['plan', 'waves', 'run', 'batch', 'check', 'profile']),
          ('Other', ['help', 'quit'])]

# ---------------------------------------------------------------- completion and live colouring
def completions(sh, line):
    """the words that could come next after `line` (used by Tab and by the live prompt)"""
    try: parts = shlex.split(line)
    except ValueError: return []
    ended = line.endswith(' ') or not line
    if not parts or (len(parts) == 1 and not ended): return sorted(sh.cmds)
    cmd = parts[0].lower(); cur = '' if ended else parts[-1]; nparts = len(parts) - (0 if ended else 1)
    if cmd in ('add', 'addbig') and nparts == 1: return sorted(set(BUILTIN_KINDS + tuple(LIBRARY) + tuple(made_names()) + tuple(k for k in sh.programs if k not in LIBRARY)))
    if cmd == 'many' and nparts == 2: return list(BUILTIN_KINDS) + list(LIBRARY)
    if cmd == 'many' and nparts == 3: return ['seq']
    if cmd == 'add': return ['seq', 'arg=', 'lw=', 'lw=auto', 'crit', 'out=', 'from=', 'argfrom=']
    if cmd == 'addbig': return ['seq', 'arg=', 'chunk=', 'lw=', 'lw=auto', 'crit', 'combine=']
    if cmd == 'make' and nparts >= 2:
        import jobmaker_v2 as J
        return list(J.STEP1) + list(J.STEP0) + ['pair', 'then', 'arg'] if parts[-1 if ended else -2] != 'then' else list(J.REDUCE)
    if cmd == 'code' and nparts == 1: return sorted(set(tuple(LIBRARY) + tuple(made_names()) + tuple(sh.programs)))
    if cmd == 'set' and nparts == 1: return sorted(SETTINGS)
    if cmd == 'set' and nparts == 2:
        k = parts[1]
        return {'lw': ['auto', 'none', '0', '1', '2', '3'], 'order': ['auto', 'kind', 'width'], 'estimate': ['on', 'off'], 'profile': ['none'] + profile_names()}.get(k, [])
    if cmd == 'profile' and nparts == 1: return profile_names()
    if cmd in ('use', 'load') and nparts == 1: return [b['name'] for b in ST.find_builds(sh.cfg.get('store'))]
    if cmd == 'load' and nparts == 2: return ['confirm']
    if cmd == 'card' and nparts == 1: return ['stamp']
    if cmd == 'card' and nparts == 2 and parts[0] == 'stamp': return [b['name'] for b in ST.find_builds(sh.cfg.get('store'))]
    if cmd == 'store' and nparts == 1: return sorted(glob.glob(cur + '*'))
    if cmd == 'help' and nparts == 1: return sorted(sh.cmds)
    if cmd == 'batch' and nparts == 2: return ['continue']
    if cmd in ('save', 'open', 'check', 'register', 'batch') and (nparts == 1 or (cmd == 'register' and nparts == 2)):
        return sorted(glob.glob(cur + '*'))
    if cmd == 'register' and nparts > 2: return ['expect=', 'expect=iss', 'out=', 'out=same']
    return []

def profile_names():
    try:
        import sc_calibrate_v1 as K
        return sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(K.PROFILE_DIR, '*.json')))
    except Exception: return []

def tokenize(sh, line):
    """[(style, text)] for colouring a line as it is typed: styles command, badcommand, kind, number, option, text, ws"""
    out = []; first = True; i = 0; kindpos = False
    import re
    for m in re.finditer(r'(\s+)|(\S+)', line):
        ws, w = m.group(1), m.group(2)
        if ws: out.append(('ws', ws)); continue
        if first:
            out.append(('command' if w.lower() in sh.cmds else 'badcommand', w)); first = False; kindpos = (w.lower() in ('add', 'addbig')); continue
        if kindpos:
            known = w in BUILTIN_KINDS or w in LIBRARY or w in sh.programs or w in made_names()
            out.append(('kind' if known else 'badcommand', w)); kindpos = False; continue
        if re.fullmatch(r'-?(0x[0-9a-fA-F]+|\d+)', w): out.append(('number', w))
        elif '=' in w or w in ('seq', 'crit'): out.append(('option', w))
        else: out.append(('text', w))
    return out

ANSI = {'command': '32', 'badcommand': '31', 'kind': '36', 'number': '33', 'option': '35', 'text': '0', 'ws': '0'}
def render(sh, line):
    """the line as typed, coloured with ANSI codes (what live colouring shows)"""
    return ''.join(('\033[%sm%s\033[0m' % (ANSI[s], t)) if s != 'ws' else t for s, t in tokenize(sh, line))

def read_loop(sh):
    hist = os.path.expanduser('~/.score_shell_history')
    try:
        if os.environ.get('SCORE_SHELL_NO_PT'): raise ImportError('prompt_toolkit switched off')
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import Completer, Completion
        from prompt_toolkit.lexers import Lexer
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.formatted_text import ANSI as PTANSI, FormattedText
        class L(Lexer):
            def lex_document(self, document):
                def get(n):
                    line = document.lines[n]
                    return [({'command': 'ansigreen', 'badcommand': 'ansired', 'kind': 'ansicyan', 'number': 'ansiyellow', 'option': 'ansimagenta'}.get(s, ''), t) for s, t in tokenize(sh, line)]
                return get
        class Cp(Completer):
            def get_completions(self, document, complete_event):
                text = document.text_before_cursor; word = '' if text.endswith(' ') or not text else text.split()[-1]
                for c in completions(sh, text):
                    if c.startswith(word): yield Completion(c, start_position=-len(word))
        ses = PromptSession(lexer=L(), completer=Cp(), history=FileHistory(hist), complete_while_typing=True)
        def ask(): return ses.prompt(FormattedText([('ansigreen bold', 'score> ')]))
        mode = 'live colours (prompt_toolkit)'
    except Exception:
        try:
            import readline
            def comp(text, state):
                opts = [c for c in completions(sh, readline.get_line_buffer()[:readline.get_endidx()]) if c.startswith(text)]
                return opts[state] if state < len(opts) else None
            readline.set_completer(comp); readline.set_completer_delims(' \t\n;'); readline.parse_and_bind('bind ^I rl_complete' if 'libedit' in (readline.__doc__ or '') else 'tab: complete')
            try: readline.read_history_file(hist)
            except OSError: pass
            import atexit; atexit.register(lambda: readline.write_history_file(hist))
        except Exception: pass
        def ask(): return input((('\001\033[1;32m\002score> \001\033[0m\002') if C_ON else 'score> '))
        mode = 'Tab completion (install prompt_toolkit for live colours)'
    sh.say(dim('S-Core shell, %s. Type help.' % mode))
    while not sh.quit:
        try: line = ask()
        except EOFError: break
        except KeyboardInterrupt: sh.say(); continue
        sh.execute_line = line
        sh.run_lines(line)

def help_markdown():
    """SHELL_v11.md, generated from the command table so the help file and the shell cannot disagree"""
    sh = Shell(out=io.StringIO()); L = ['# The S-Core shell (`score_shell_v11.py`): commands', '',
        'Start: `python3 score_shell_v11.py` (plan and check need no card), or with the card: `nix shell nixpkgs#openocd --command python3 score_shell_v11.py`.',
        'Type `help` inside for this list, `help COMMAND` for one command. Tab completes commands, kinds, settings and file names. With the optional package',
        '`prompt_toolkit` the line is coloured as you type (known command green, unknown red, kinds cyan, numbers yellow, options magenta). `NO_COLOR=1` or `--plain` turns colour off.',
        'Several commands on one line are separated by `;`. A line starting with `#` is a comment. Files of commands: `python3 score_shell_v11.py -f FILE.score`.', '',
        '*This file is generated: `python3 score_shell_v11.py --write-help`. A test checks it matches the shell.*', '']
    for group, names in GROUPS:
        L += ['## ' + group, '']
        for n in names:
            _, usage, text = sh.cmds[n]; L += ['### `%s`' % usage, '', text, '']
    L += ['## Settings', '', '| name | default | meaning |', '|---|---|---|'] + ['| `%s` | %s | %s |' % (k, '`%s`' % (d,) if d is not None else '`none`', h) for k, (d, h) in SETTINGS.items()] + ['']
    L += ['## A first session', '', '```', 'add vsum 1 2 3 4', 'add vmax seq 5 80 3', 'show', 'save first.json', 'set blocks 1', 'plan', 'run          # with the card', '```', '']
    return '\n'.join(L)

def main(argv=None):
    global C_ON
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('-f', metavar='FILE', help='run a batch file of commands (stops at the first error, exit code 1)'); ap.add_argument('-c', metavar='CMDS', help='run these commands (separated by ;)')
    ap.add_argument('-k', '--keep-going', action='store_true', help='with -f / -c / piped input: go on after an error')
    ap.add_argument('-q', action='store_true', help='leave after -f / -c'); ap.add_argument('--plain', action='store_true', help='no colours')
    ap.add_argument('--write-help', action='store_true', help='write SHELL_v11.md from the command table')
    a = ap.parse_args(argv)
    if a.write_help: open(os.path.join(HERE, 'SHELL_v11.md'), 'w').write(help_markdown()); print('SHELL_v11.md written'); return 0
    C_ON = sys.stdout.isatty() and not a.plain and not os.environ.get('NO_COLOR')
    sh = Shell()
    ok = True
    if a.f: ok = sh.run_script(open(a.f).read(), stop=not a.keep_going, label=os.path.basename(a.f)) and ok
    if a.c and (ok or a.keep_going): ok = sh.run_script(a.c, stop=not a.keep_going, label='-c') and ok
    if (a.f or a.c) and a.q: return 0 if ok else 1
    if not sys.stdin.isatty() and not (a.f or a.c): return 0 if sh.run_script(sys.stdin.read(), stop=not a.keep_going, label='input') else 1
    read_loop(sh); return 0

if __name__ == '__main__':
    sys.exit(main())
