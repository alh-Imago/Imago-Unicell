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
import host_sc as hs, sdt_host as H, batch as B, jobcomp as C
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

def plan_blocks(tasks, nb, imem=128, dsh=256, far_words=1 << 16, far_base=0x2000, wait_k=0xFFFF, weights=None):
    """one jobcomp plan per block that has jobs, each in its own far-RAM area; areas do not overlap and all lie below far_words"""
    groups = split(tasks, nb, weights); plans = []; base = far_base
    for k, ids in enumerate(groups):
        if not ids: continue
        p = C.compile([tasks[i] for i in ids], imem=imem, dsh=dsh, far_base=base, wait_k=wait_k)
        end = p.window[0] + p.window[1]
        if end > far_words: raise C.JobCompError('block %d: its far-RAM area ends at %#x, past the far RAM (%#x words)' % (k, end, far_words))
        plans.append(BlockPlan(k, ids, p)); base = (end + 15) & ~15
    return plans

def report(tasks, plans):
    l = []
    for bp in plans:
        p = bp.plan
        l.append('block %d: %d jobs (%s), far RAM %#x to %#x, entry %#x' % (bp.block, len(bp.task_ids), ' '.join(str(i) for i in bp.task_ids), p.script_addrs[0], p.window[0] + p.window[1], p.entry))
        l.extend('  ' + x for x in p.report().split('\n')[1:])
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

def run(port, tasks, nb, io=None, out=None, imem=None, dsh=None, far_words=None, poll_timeout=600.0, say=print, weights=None):
    b = io if io is not None else hs.Board(port)
    clk_hz = 50_000_000 if str(port).startswith('jtag') else 27_000_000
    far_words = far_words or ((1 << 16) if str(port).startswith('jtag') else (1 << 21))
    v = b.version(); say('board version %d, %d slices per block, %d code words; %d blocks asked for' % (v['version'], v['S'], v['imem_words'], nb))
    if v['version'] < 11: say('Need a board with the hardware sequencer (version 11 or 12).'); return 2
    plans = plan_blocks(tasks, nb, imem=imem or v['imem_words'], dsh=dsh or 256, far_words=far_words, weights=weights); say(report(tasks, plans))
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
    ap.add_argument('--plan', metavar='JOBS'); ap.add_argument('--blocks', type=int, default=2); ap.add_argument('--out'); ap.add_argument('--lw', type=int, help='run every job at this width (2**lw slices fused); default: the job\'s own "lw" field, 0 if none')
    ap.add_argument('--imem', type=int, default=128); ap.add_argument('--dsh', type=int, default=256); ap.add_argument('--far-words', type=int); ap.add_argument('--weights', help='cost per window word by kind, e.g. crc32=19,vgain=1 (others 1)')
    a = ap.parse_args(argv)
    wts = dict((k, float(v)) for k, v in (x.split('=') for x in a.weights.split(','))) if a.weights else None
    if a.plan:
        t = load_jobs(a.plan); print(report(t, plan_blocks(t, a.blocks, imem=a.imem, dsh=a.dsh, far_words=a.far_words or 1 << 16, weights=wts))); return 0
    if not a.port or not a.jobs: ap.print_help(); return 2
    tasks = load_jobs(a.jobs)
    if a.lw is not None:
        for t in tasks: t.lw = a.lw
    return run(a.port, tasks, a.blocks, out=a.out, imem=a.imem, dsh=a.dsh, far_words=a.far_words, weights=wts)

if __name__ == '__main__': sys.exit(main())
