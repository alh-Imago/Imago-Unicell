"""jobcomp_v2.py - jobcomp.py with two additions (ledger #1406).  jobcomp.py stays as proven; this file re-uses everything from it except Task, PJob and compile.

  * a job can carry a CRITICAL flag (Task(..., crit=1); job file "crit": 1): it goes in the SUBMIT step (bit 12 of w2) to the dispatcher's critical queue,
    which is served first (sc_sys_v17: after MAXPASS bulk launches past a blocked critical head, bulk is held back);
  * compile(..., order='kind'|'width'): the order of the SUBMIT steps inside a batch.  'kind' = the order of jobcomp.py (by kind, then job number: nothing changes);
    'width' = widest first, then the biggest window, then job number (the dispatcher does not skip a head that does not fit, so wide jobs go first);
    'auto' = 'width' for a batch whose jobs have different widths, 'kind' for a batch of equal widths (so batches of equal widths are exactly as before).
Everything else is the compile() of jobcomp.py, copied unchanged (task ids stay the job's position in the batch; only the order of the steps changes)."""
import jobio as J, batch as B
from jobcomp import *            # JobCompError, TAG, pack, need, kind_cost, Plan, Task/PJob (replaced below), compile (replaced below)
from jobcomp import Task as _Task, PJob as _PJob

class Task(_Task):
    def __init__(self, *a, crit=0, **k):
        super().__init__(*a, **k)
        if crit not in (0, 1, True, False): raise JobCompError('crit must be 0 or 1, got %r' % (crit,))
        self.crit = int(crit)

class PJob(_PJob):
    def __init__(self, *a, crit=0, **k): super().__init__(*a, **k); self.crit = crit

def submit_sequence(jobs, order='kind'):
    """-> [(task id, job)] in the order the SUBMIT steps are written; the task id is the job's position in the batch in every case"""
    seq = list(enumerate(jobs))
    if order == 'auto': order = 'width' if len({j.lw for j in jobs}) > 1 else 'kind'      # mixed widths: widest first; equal widths: as before
    if order == 'kind': return seq
    if order == 'width': return sorted(seq, key=lambda tj: (-tj[1].lw, -tj[1].window_words, tj[0]))
    raise JobCompError("order must be 'kind', 'width' or 'auto', got %r" % (order,))

def compile(tasks, imem=128, dsh=256, max_jobs=16, far_base=0x2000, wait_k=0xFFFF, order='kind'):
    if not tasks: raise JobCompError('no tasks')
    if any(t.lw == 'auto' for t in tasks): raise JobCompError('a job has lw "auto": resolve it first (scblocks.resolve_auto: needs the unit width and the slices per block)')
    batches = pack(tasks, imem, dsh, max_jobs)
    # jobs and links per batch
    built = []
    for b in batches:
        pad = {}
        for i in b: pad[tasks[i].kind] = max(pad.get(tasks[i].kind, 0), tasks[i].window_words)
        first, jobs = {}, []
        for cid, i in enumerate(b):
            t = tasks[i]
            jobs.append(PJob(cid, t.kind, t.inputs, t.out_len, arg=t.arg, clone_of=first.get(t.kind), pad=pad[t.kind], lw=t.lw, crit=getattr(t, 'crit', 0)))
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
            for tid, j in submit_sequence(jobs, order): sc.submit(tid, lk.classes[j.cid]['entry'], j.cid, j.lw, j.crit)
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
    p.steps = sum(len(s.steps) for s in scripts); p.script_addrs = addrs
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
