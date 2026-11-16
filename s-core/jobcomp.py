"""jobcomp.py - the job compiler (host side): turns a list of jobs of any length into a chain of batches for the batch sequencer.

    tasks = [jobcomp.Task('vsum', inputs), jobcomp.Task('vscale', inputs), ...]        (any number)
    plan  = jobcomp.compile(tasks, imem=128, dsh=256)
    plan.image      {far word address: word}  scripts, code images and window images; write it into far RAM, then open the copy window plan.window and start plan.entry
    plan.results    {task index: (status far address, output far address, n_out)}  filled in by the chain: read them back, plan.verify(read_word) checks them all

What it decides (the board only does what the script says):
  * splitting: tasks are packed into batches so that each batch fits the code store (library + one copy of each program) and the shared data RAM (one window
    per job; jobs running the same program are CLONES: shared code, own window, padded to the largest window of that program in the batch) and has at most
    max_jobs jobs (task ids 0..max_jobs-1, reused by every batch because each batch waits for its jobs before the next one starts);
  * linking: one link per batch; the next batch replaces the code store, the library window, the class regions and windows (the sequencer refuses to do that
    while a job is in flight, and every batch ends with a WAIT);
  * far RAM layout: scripts first (read by the sequencer directly), then code and window images, then a status block (status, n_out of every task: 2 words)
    and the results block (every task's output words, in the ORDER OF THE TASKS, whichever batch ran them);
  * every job's status and n_out are saved too, so a job that refused or trapped shows up in verify() instead of silently giving zeros.
Programs come from jobio.KINDS (assembly with the job I/O convention of jobio.py)."""
import jobio as J, batch as B

TAG = 0x600D
class JobCompError(Exception): pass

class Task:
    def __init__(self, kind, inputs, out_len=None, arg=0):
        if kind not in J.KINDS: raise JobCompError('unknown job kind %r (known: %s)' % (kind, ', '.join(sorted(J.KINDS))))
        self.kind, self.inputs, self.arg = kind, [w & J.M32 for w in inputs], arg
        self.out_len = out_len if out_len is not None else (len(inputs) if kind == 'vscale' else 1)
        if self.out_len < 1: raise JobCompError('a job needs at least one output word')
    @property
    def window_words(self): return J.HDR + len(self.inputs) + self.out_len
    def expected(self): return J.Job(0, self.kind, self.inputs, self.out_len, self.arg).expected()

class PJob(J.Job):
    """a Job whose window is padded to pad words, so that it can be a clone of a bigger one"""
    def __init__(self, *a, pad=0, **k): super().__init__(*a, **k); self.pad = pad
    @property
    def window_words(self): return max(self.pad, J.HDR + len(self.inputs) + self.out_len)

_kind_cost = {}
def kind_cost(kind, imem, dsh):
    """(library words, class words) of a program, measured by linking it once"""
    if (kind, imem, dsh) not in _kind_cost:
        lk = J.build_link([J.Job(0, kind, [1], 1)], shared_words=dsh, code_words=imem)
        _kind_cost[(kind, imem, dsh)] = (lk.lib[1], lk.classes[0]['clen'])
    return _kind_cost[(kind, imem, dsh)]

def need(members, imem, dsh):
    """(code words, shared words) a set of tasks needs in one batch"""
    kinds = {}
    for t in members: kinds[t.kind] = max(kinds.get(t.kind, 0), t.window_words)
    lib = max([kind_cost(k, imem, dsh)[0] for k in kinds] or [0])
    return lib + sum(kind_cost(k, imem, dsh)[1] for k in kinds), sum(w * sum(1 for t in members if t.kind == k) for k, w in kinds.items())

def pack(tasks, imem=128, dsh=256, max_jobs=16):
    """-> list of batches, each a list of task indices.  First fit, biggest windows first."""
    order = sorted(range(len(tasks)), key=lambda i: (-tasks[i].window_words, i))
    batches = []
    for i in order:
        t = tasks[i]
        c, d = need([t], imem, dsh)
        if c > imem or d > dsh: raise JobCompError('task %d (%s, %d window words) cannot fit the board on its own: needs %d code words (store %d) and %d shared words (RAM %d)' % (i, t.kind, t.window_words, c, imem, d, dsh))
        for b in batches:
            if len(b) < max_jobs:
                c, d = need([tasks[j] for j in b] + [t], imem, dsh)
                if c <= imem and d <= dsh: b.append(i); break
        else: batches.append([i])
    return [sorted(b, key=lambda i: (tasks[i].kind, i)) for b in batches]

class Plan: pass

def compile(tasks, imem=128, dsh=256, max_jobs=16, far_base=0x2000, wait_k=0xFFFF):
    if not tasks: raise JobCompError('no tasks')
    batches = pack(tasks, imem, dsh, max_jobs)
    # jobs and links per batch
    built = []
    for b in batches:
        pad = {}
        for i in b: pad[tasks[i].kind] = max(pad.get(tasks[i].kind, 0), tasks[i].window_words)
        first, jobs = {}, []
        for cid, i in enumerate(b):
            t = tasks[i]
            jobs.append(PJob(cid, t.kind, t.inputs, t.out_len, arg=t.arg, clone_of=first.get(t.kind), pad=pad[t.kind]))
            first.setdefault(t.kind, cid)
        built.append((b, jobs, J.build_link(jobs, shared_words=dsh, code_words=imem)))
    exp_len = [len(t.expected()) for t in tasks]
    def emit(img_base, script_addrs, st_base, res_base):
        lay = B.Layout(img_base); scripts = []
        res_at = [0] * len(tasks); r = res_base
        for i in range(len(tasks)): res_at[i] = r; r += exp_len[i]
        for k, (b, jobs, lk) in enumerate(built):
            sc = B.Script()
            if lk.lib[1]: sc.library(*lk.lib)
            for cid, c in sorted(lk.classes.items()):
                sc.region(cid, c['cbase'], c['clen'], c['dlen'])
                if c['win'] and c['win'][1]: sc.window(cid, *c['win'])
            sc.load_code(0, lay.put(lk.words), len(lk.words))
            for j in jobs:
                base = J.window_base(lk, j); im = [0] * j.window_words
                for a, v in J.prepare(lk, j).items(): im[a - base] = v
                sc.load_data(base, lay.put(im), j.window_words)
            for tid, j in enumerate(jobs): sc.submit(tid, lk.classes[j.cid]['entry'], j.cid)
            sc.wait(wait_k)
            for j, i in zip(jobs, b):
                base = J.window_base(lk, j)
                sc.save(base + J.F_STATUS, st_base + 2 * i, 2)
                sc.save(base + j.out_off, res_at[i], exp_len[i])
            if k + 1 < len(built): sc.jump(script_addrs[k + 1] if script_addrs else 0)
            else: sc.end(TAG)
            scripts.append(sc)
        return scripts, lay, res_at
    # pass 1 measures the scripts, pass 2 places everything
    scripts, _, _ = emit(0, None, 0, 0)
    addrs, a = [], far_base
    for sc in scripts: addrs.append(a); a += len(sc)
    img_start = a
    scripts, lay, res_at = emit(img_start, addrs, 0, 0)               # measure the images to place the status and results blocks after them
    st_base = lay.next; res_base = st_base + 2 * len(tasks)
    scripts, lay, res_at = emit(img_start, addrs, st_base, res_base)
    end = res_base + sum(exp_len)
    for sc, at in zip(scripts, addrs): lay.put(sc.words(), at=at)
    if end > 0x1FFFFF: raise JobCompError('does not fit the 8 MB far RAM')
    p = Plan()
    p.image, p.entry, p.window, p.tag = lay.image, addrs[0], (img_start, end - img_start), TAG
    p.batches, p.scripts, p.links = batches, scripts, [lk for _, _, lk in built]
    p.class_kinds = [{j.cid: j.kind for j in jobs} for _, jobs, _ in built]          # per batch: class id -> program name (used by stand-in boards)
    p.status_at = {i: st_base + 2 * i for i in range(len(tasks))}
    p.results = {i: (st_base + 2 * i, res_at[i], exp_len[i]) for i in range(len(tasks))}
    p.expected = [t.expected() for t in tasks]
    p.steps = sum(len(s.steps) for s in scripts)
    def verify(read_word):
        bad = []
        for i, (sa, ra, n) in p.results.items():
            st, nout = read_word(sa), read_word(sa + 1)
            out = [read_word(ra + k) for k in range(n)]
            if st != 1 or nout != n or out != p.expected[i]: bad.append((i, tasks[i].kind, 'status %d n_out %d (want 1, %d)' % (st, nout, n) if (st != 1 or nout != n) else 'wrong output'))
        return bad
    p.verify = verify
    def report():
        l = ['%d tasks -> %d batches, %d script steps, far RAM %d words (copy window %#x +%#x), entry %#x' % (len(tasks), len(batches), p.steps, end - far_base, p.window[0], p.window[1], p.entry)]
        for k, (b, jobs, lk) in enumerate(built):
            c, d = need([tasks[i] for i in b], imem, dsh)
            l.append('  batch %d: %2d jobs (%s), code %d/%d words, shared %d/%d words' % (k, len(b), ' '.join(sorted({tasks[i].kind for i in b})), len(lk.words), imem, d, dsh))
        return '\n'.join(l)
    p.report = report
    return p
