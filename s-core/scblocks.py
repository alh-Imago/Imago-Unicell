#!/usr/bin/env python3
"""scblocks.py - run a job file on SEVERAL BLOCKS of the multi-block build (fpga/sc_top_k7_v8.v, host_bridge_v11).  The outer allocator, in software (ledger #1348).

    python3 scblocks.py --plan jobs.json --blocks 2        compile only: show which jobs go to which block and the far-RAM areas (no board needed)
    python3 scblocks.py jtag jobs.json --blocks 2           run on the card: every block runs its own chain at the same time, results are checked against the Python answer
    options: --out results.json, --imem 128 --dsh 256 (the blocks' sizes), --far-words N (size of the far RAM; default 65536 for 'jtag': the block-RAM build)

What it does: the jobs are split over the blocks (most expensive job first, each to the block with the least work so far; the "work" is the window size times a weight per kind of job, fitted from one
card run: crc32 counts about 19 times a vector job per word; a rough guide, not a measurement; --weights changes it).  Each block gets its own plan (jobcomp.compile) with its own area of far RAM (scripts, images, results) and its own copy
window, so a block cannot touch another block's areas.  Then: for every block select it (O), reset it (R), release its hold (G), set its window (D); write all
images; start each block's chain (J); poll every block's sequencer (A) until all are done; read the results back.  The number of blocks is NOT read from
the board (the V reply has no field for it): you give --blocks, and an O to a block number the build does not have is ignored by the board.
Jobs keep the order of the job file: the answers come back as one list in that order, whichever block ran them."""
import sys, os, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, batch as B, jobcomp_v2 as C
from scbatch import dec_A, a_len, SEQ_ERR, load_jobs, c_J

class BlockPlan:
    def __init__(self, block, task_ids, plan): self.block, self.task_ids, self.plan = block, task_ids, plan

# Cost weights per word of window, per kind of job.  FITTED FROM ONE CARD RUN (ledger #1350, two blocks, 4 slices): the four non-crc32 kinds were taken as one
# group (about 1,170 clocks per window word) and crc32 about 19 times that (about 22,000 per word).  Two equations, two unknowns: a rough guide, not a model;
# it ignores job length effects and the batch overhead.  Override with --weights crc32=19,vgain=1 or replace it with measured numbers.
KIND_WEIGHT = {'crc32': 19.0}
def cost(task, weights=None):
    w = KIND_WEIGHT if weights is None else weights
    return task.window_words * w.get(task.kind, 1.0)

def split(tasks, nb, weights=None):
    """-> list (one per block) of task-index lists.  Highest cost first (cost = window words x the kind's weight), each to the block with the least total so far (ties: lowest block)."""
    load = [0.0] * nb; out = [[] for _ in range(nb)]
    for i in sorted(range(len(tasks)), key=lambda i: (-cost(tasks[i], weights), i)):
        k = min(range(nb), key=lambda b: (load[b], b)); out[k].append(i); load[k] += cost(tasks[i], weights)
    return [sorted(o) for o in out]

def plan_blocks(tasks, nb, imem=128, dsh=256, far_words=1 << 16, far_base=0x2000, wait_k=0xFFFF, weights=None, profile=None, slices=None, unit_lw=None, say=print, order='kind', crit_mode=None):
    """one jobcomp plan per block that has jobs, each in its own far-RAM area; areas do not overlap and all lie below far_words"""
    groups = split(tasks, nb, weights); plans = []; base = far_base
    for k, ids in enumerate(groups):
        if not ids: continue
        gt = [tasks[i] for i in ids]
        if profile is not None: apply_profile(gt, slices, unit_lw, profile, imem, dsh, say, block=k)
        if crit_mode: apply_crit(gt, crit_mode, imem, dsh)
        p = C.compile(gt, imem=imem, dsh=dsh, far_base=base, wait_k=wait_k, order=order)
        end = p.window[0] + p.window[1]
        if end > far_words: raise C.JobCompError('block %d: its far-RAM area ends at %#x, past the far RAM (%#x words)' % (k, end, far_words))
        plans.append(BlockPlan(k, ids, p)); base = (end + 15) & ~15
    return plans

def resolve_auto(tasks, slices, unit_lw, min_cost=0.0, weights=None, say=print, profile=None):
    """Automatic width (OPTIONAL, ledger #1388; a job asks for it with "lw": "auto" or --lw auto).  Rule, from the card measurements of #1379..#1385: a job
    is run at the widest width the hardware can fuse, min(unit_lw, log2 slices); in every measured job set widening a job never made the set slower and widening
    everything was the fastest.  Jobs whose cost (window words x kind weight, see cost()) is below min_cost stay at lw 0.  Explicit widths are never changed.
    Also checks every width against the block size: a group wider than the block can never be placed (the job would not run)."""
    top = slices.bit_length() - 1
    if slices & (slices - 1): raise C.JobCompError('slices per block must be a power of two, got %d' % slices)
    w = min(unit_lw, top); n = 0
    for t in tasks:
        if t.lw == 'auto' and profile is None:
            t.lw = w if cost(t, weights) >= min_cost else 0; n += 1
    for i, t in enumerate(tasks):
        if t.lw != 'auto' and t.lw > top: raise C.JobCompError('job %d: lw %d needs %d slices but a block has %d' % (i, t.lw, 1 << t.lw, slices))
    if n: say('automatic width: %d job(s) set to lw %d (unit width 2**%d, %d slices per block)%s' % (n, w, unit_lw, slices, '' if not min_cost else ', jobs under cost %g stay at 0' % min_cost))
    return tasks

def profile_fits(profile, slices):
    """a profile is made for one build: refuse it on a board with another number of slices per block (ledger #1401).  Units and unit width are not
    reported by the board, so they cannot be checked: the user is responsible for loading the build the profile was made on."""
    if profile['card']['slices'] != slices:
        raise C.JobCompError('the profile %s was made for %d slices per block, this board has %d: run sc_calibrate_v1.py on this build' % (profile['name'], profile['card']['slices'], slices))

def apply_profile(tasks, slices, unit_lw, profile, imem, dsh, say=print, block=0):
    """OPTIONAL per-batch automatic width (ledger #1401): the jobs of one block are packed into batches exactly as jobcomp.compile will pack them (the width does not
    change the packing), and every job that asks for "auto" gets the width the card profile gives for a batch of that many jobs
    (sc_calibrate_v1.best_width), capped at the unit width and at the block.  Explicit widths are never changed.  Model: identical jobs; mixed lengths in one batch are not in it."""
    import sc_calibrate_v1 as K
    profile_fits(profile, slices)
    top = slices.bit_length() - 1; cap = min(unit_lw, top); parts = []
    for bi, b in enumerate(C.pack(tasks, imem, dsh, 16)):
        if not any(tasks[i].lw == 'auto' for i in b): continue
        w = min(K.best_width(profile, len(b)), cap)
        for i in b:
            if tasks[i].lw == 'auto': tasks[i].lw = w
        parts.append('batch %d: %d jobs -> lw %d' % (bi, len(b), w))
    if parts: say('profile %s, block %d: %s' % (profile['name'], block, '; '.join(parts)))

def apply_crit(tasks, mode, imem, dsh):
    """AUTOMATIC critical flag (ledger #1406; optional, --crit wide): in every batch whose jobs have different widths, the jobs of the widest width get
    the critical flag (the dispatcher's critical queue is served first, and holds bulk back after MAXPASS launches so a wide job can get its aligned group).
    A flag the user set in the job file ("crit": 1) is never removed.  Run after the widths are resolved."""
    if mode != 'wide': raise C.JobCompError("--crit must be 'wide' (or not given), got %r" % (mode,))
    for b in C.pack(tasks, imem, dsh, 16):
        ws = [tasks[i].lw for i in b]
        if len(set(ws)) > 1:
            for i in b:
                if tasks[i].lw == max(ws): tasks[i].crit = 1

def submit_lines(plans):
    """one line per batch that has mixed widths or a critical job: the SUBMIT steps in the order they will be sent (read back from the script)"""
    out = []
    for bp in plans:
        p = bp.plan
        for k, sc in enumerate(p.scripts):
            subs = [B.decode(st)[1] for st in sc.steps if st[0] == B.SUBMIT]
            if not subs or not (any(f['crit'] for f in subs) or len({f['lw'] for f in subs}) > 1): continue
            out.append('  block %d batch %d submit order: %s' % (bp.block, k, ', '.join('%s lw%d%s' % (p.class_kinds[k][f['prog']], f['lw'], ' CRIT' if f['crit'] else '') for f in subs)))
    return out

def report(tasks, plans):
    l = []
    for bp in plans:
        p = bp.plan
        l.append('block %d: %d jobs (%s), far RAM %#x to %#x, entry %#x' % (bp.block, len(bp.task_ids), ' '.join(str(i) for i in bp.task_ids), p.script_addrs[0], p.window[0] + p.window[1], p.entry))
        l.extend('  ' + x for x in p.report().split('\n')[1:])
    l.extend(submit_lines(plans))
    return '\n'.join(l)

# ---- the byte sequences (shared by the live runner and the simulation test, so the test checks the real commands)
def cmds_setup(plans, reset=True):
    """-> list of byte strings: per block O, R, G, D; then all images through block 0"""
    out = []
    for bp in plans:
        out.append(hs.cmd_O(bp.block))
        if reset: out += [hs.cmd_R()]
        out += [hs.cmd_G(), H.c_D(*bp.plan.window)]
    out.append(hs.cmd_O(0))
    for bp in plans:
        for a in sorted(bp.plan.image): out.append(H.c_w(a, bp.plan.image[a]))
    return out
def cmds_start(plans): return [x for bp in plans for x in (hs.cmd_O(bp.block), c_J(bp.plan.entry))]
def cmds_poll(bp): return [hs.cmd_O(bp.block), b'A']
def cmd_read(bp, a): return [hs.cmd_O(0), H.c_r(a)]

def verify_all(tasks, plans, far_r):
    """-> list of (job index, kind, why) over all blocks, in job-file numbering"""
    bad = []
    for bp in plans:
        for (li, kind, why) in bp.plan.verify(far_r): bad.append((bp.task_ids[li], kind, why))
    return sorted(bad)

def run(port, tasks, nb, io=None, out=None, imem=None, dsh=None, far_words=None, poll_timeout=600.0, say=print, weights=None, unit_lw=None, min_cost=0.0, profile=None, order='kind', crit_mode=None):
    b = io if io is not None else hs.Board(port)
    clk_hz = 50_000_000 if str(port).startswith('jtag') else 27_000_000
    far_words = far_words or ((1 << 16) if str(port).startswith('jtag') else (1 << 21))
    v = b.version(); say('board version %d, %d slices per block, %d code words; %d blocks asked for' % (v['version'], v['S'], v['imem_words'], nb))
    if v['version'] < 11: say('Need a board with the hardware sequencer (version 11 or 12).'); return 2
    if profile is not None and unit_lw is None: unit_lw = profile['card']['unit_lw']
    if any(t.lw == 'auto' for t in tasks) and unit_lw is None: say('A job asks for "auto" width: tell me the unit width with --unit-lw N (the unit has 2**N lanes; the card builds so far: 2 for 2x4, 3 for 2x8).'); return 2
    try:
        if profile is not None: profile_fits(profile, v['S'])
        resolve_auto(tasks, v['S'], unit_lw if unit_lw is not None else 0, min_cost, weights, say, profile)
        plans = plan_blocks(tasks, nb, imem=imem or v['imem_words'], dsh=dsh or 256, far_words=far_words, weights=weights, profile=profile, slices=v['S'], unit_lw=unit_lw, say=say, order=order, crit_mode=crit_mode)
    except C.JobCompError as e: say(str(e)); return 2
    say(report(tasks, plans))
    def put(c): b.s.write(c); b.s.flush()
    cs = cmds_setup(plans)
    # reset + go + window per block, then settle, then the images
    t0 = time.time()
    for c in cs:
        b.s.write(c)
        if c == hs.cmd_R(): b.s.flush(); time.sleep(0.2)                  # the reset of the selected block takes a few clocks: let it finish
    b.s.flush(); time.sleep(0.3)
    say('loaded %d words into far RAM in %.1f s' % (sum(len(bp.plan.image) for bp in plans), time.time() - t0))
    t0 = time.time()
    for c in cmds_start(plans): put(c)
    time.sleep(0.02); done = {}
    while len(done) < len(plans):
        for bp in plans:
            if bp.block in done: continue
            for c in cmds_poll(bp): put(c)
            a = dec_A(b._rd(a_len(v['version'])))
            if a['done'] and not a['busy']: done[bp.block] = a
        if time.time() - t0 > poll_timeout: say('blocks did not all finish in %.0f s (finished: %s)' % (poll_timeout, sorted(done))); return 1
        time.sleep(0.05)
    say('all %d blocks finished in %.2f s' % (len(plans), time.time() - t0))
    err = 0
    for bp in plans:
        a = done[bp.block]
        if a['err'] or a['tag'] != bp.plan.tag: say('block %d stopped: error %s (%s), end tag %s' % (bp.block, a['err'], SEQ_ERR.get(a['err'], '?'), a['tag'])); err = 1; continue
        if 'clk' in a: say('  block %d: %d jobs, %d steps, %d clocks = %.2f ms' % (bp.block, len(bp.task_ids), a['steps'], a['clk'], 1000.0 * a['clk'] / clk_hz))
    if err: return 1
    def far_r(a):
        for c in cmd_read(None, a): put(c)
        return H.dec_r(b._rd(4))
    bad = verify_all(tasks, plans, far_r)
    for i, kind, why in bad: say('  job %d (%s): %s' % (i, kind, why))
    say('%d of %d jobs correct' % (len(tasks) - len(bad), len(tasks)))
    if out:
        res = {}
        for bp in plans:
            for li, gi in enumerate(bp.task_ids):
                _, ra, n = bp.plan.results[li]; res[gi] = [far_r(ra + k) for k in range(n)]
        json.dump([{'job': i, 'kind': t.kind, 'result': res[i]} for i, t in enumerate(tasks)], open(out, 'w')); say('results written to %s' % out)
    return 1 if bad else 0

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0]); ap.add_argument('port', nargs='?'); ap.add_argument('jobs', nargs='?')
    ap.add_argument('--plan', metavar='JOBS'); ap.add_argument('--blocks', type=int, default=2); ap.add_argument('--out'); ap.add_argument('--lw', help='run every job at this width (0..4: 2**lw slices fused) or "auto"; default: the job\'s own "lw" field, 0 if none')
    ap.add_argument('--unit-lw', type=int, help='log2 of the lanes of a fusion unit (needed for auto width): 2 on the 2x4 card build, 3 on the 2x8')
    ap.add_argument('--slices', type=int, default=None, help='slices per block (only for --plan with auto width; a real run asks the board; default 4, or the profile\'s)')
    ap.add_argument('--submit-order', choices=['kind', 'width', 'auto'], default='kind', help="order of the SUBMIT steps in a batch: kind (default, as before), width (widest first) or auto (width for batches with mixed widths, kind for equal widths; ledger #1406, #1409)")
    ap.add_argument('--crit', choices=['wide'], help='critical flag on the widest jobs of every batch with mixed widths (ledger #1406); a "crit": 1 in the job file always counts')
    ap.add_argument('--profile', help='card profile made by sc_calibrate_v1.py (name or path): with --lw auto every batch gets the width the profile gives for that many jobs (ledger #1401)')
    ap.add_argument('--auto-min-cost', type=float, default=0.0, help='auto width: jobs cheaper than this (window words x kind weight) stay at lw 0')
    ap.add_argument('--imem', type=int, default=128); ap.add_argument('--dsh', type=int, default=256); ap.add_argument('--far-words', type=int); ap.add_argument('--weights', help='cost per window word by kind, e.g. crc32=19,vgain=1 (others 1)')
    a = ap.parse_args(argv)
    wts = dict((k, float(v)) for k, v in (x.split('=') for x in a.weights.split(','))) if a.weights else None
    prof = None
    if a.profile:
        import sc_calibrate_v1 as K
        if a.auto_min_cost: print('--profile and --auto-min-cost cannot be combined (the profile chooses the width per batch)'); return 2
        prof = K.load_profile(a.profile)
    if a.plan:
        t = load_jobs(a.plan)
        if a.lw is not None:
            for x in t: x.lw = 'auto' if a.lw == 'auto' else int(a.lw)
        sl = a.slices or (prof['card']['slices'] if prof else 4); ul = a.unit_lw if a.unit_lw is not None else (prof['card']['unit_lw'] if prof else 0)
        if prof is not None and not any(x.lw == 'auto' for x in t): print('note: a profile was given but no job asks for auto width (--lw auto): it is not used')
        try:
            if any(x.lw == 'auto' for x in t): resolve_auto(t, sl, ul, a.auto_min_cost, wts, profile=prof)
            print(report(t, plan_blocks(t, a.blocks, imem=a.imem, dsh=a.dsh, far_words=a.far_words or 1 << 16, weights=wts, profile=prof, slices=sl, unit_lw=ul, order=a.submit_order, crit_mode=a.crit)))
        except C.JobCompError as e: print(e); return 2
        return 0
    if not a.port or not a.jobs: ap.print_help(); return 2
    tasks = load_jobs(a.jobs)
    if a.lw is not None:
        for t in tasks: t.lw = 'auto' if a.lw == 'auto' else int(a.lw)
    return run(a.port, tasks, a.blocks, out=a.out, imem=a.imem, dsh=a.dsh, far_words=a.far_words, weights=wts, unit_lw=a.unit_lw, min_cost=a.auto_min_cost, profile=prof, order=a.submit_order, crit_mode=a.crit)

if __name__ == '__main__': sys.exit(main())
