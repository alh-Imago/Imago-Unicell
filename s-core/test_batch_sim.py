"""Batch script handler in the whole-board simulation with the far RAM (fpga/sc_top_pool13.v, SDRAM model).  Needs iverilog.
 1. rules, in plain Python: every step round-trips through encode/decode; a code or region change with jobs still in flight is refused (InFlight);
    a script that jumps to another script is followed; a script without END runs into the step limit;
 2. the two-phase chain of batch_demo.py runs on the simulated board: the host only writes the images to far RAM and opens the copy window; the executor
    then walks the scripts it reads from far RAM (REGION / WINDOW / LOAD_CODE / LOAD_DATA / SUBMIT / WAIT / SAVE / JUMP / END).  Phase 2 REPLACES the code
    store and the class regions with different programs, so a right answer from phase 2 proves the new code was loaded and used;
 3. the results of all four jobs, gathered in one block of far RAM, equal the Python answer; no job trapped; the word past the block is untouched."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, batch as B, batch_demo as D
import test_farram_sim as F

def rules(check):
    s = B.Script(); s.region(1, 20, 30, 16).window(1, 0, 28).load_code(5, 0x2200, 107).submit(3, 46, 1, lw=2, crit=1).wait(7).jump(0x2100).library(4, 20).save(1, 2, 3).load_data(4, 5, 6).end(0x600D)
    names = [B.decode(st)[0] for st in s.steps]
    check('all ten steps decode back to the right names', names == ['REGION', 'WINDOW', 'LOAD_CODE', 'SUBMIT', 'WAIT', 'JUMP', 'LIBRARY', 'SAVE', 'LOAD_DATA', 'END'], ' '.join(names))
    sub = B.decode(s.steps[3])[1]
    check('SUBMIT fields survive packing (tid 3, entry 46, class 1, lw 2, crit 1)', sub == dict(tid=3, code=46, prog=1, lw=2, crit=1), str(sub))
    class Rec:
        def __init__(self): self.sent = []
        def send(self, c, r=0, kind=None, extra=0): self.sent.append(c)
        def wait(self, n): self.sent.append(('wait', n))
    def mem(*scripts):
        m = {}
        for at, sc in scripts:
            for i, w in enumerate(sc.words()): m[at + i] = w
        return lambda a: m.get(a, 0xEEEEEEEE)
    bad = B.Script().submit(0, 20, 0).load_code(0, 0x2200, 10).end()
    try: B.PlanExec(Rec(), mem((0x100, bad))).run(0x100); ok = False
    except B.InFlight: ok = True
    check('LOAD_CODE with a job in flight is refused', ok)
    good = B.Script().submit(0, 20, 0).wait().load_code(0, 0x2200, 10).end(7)
    r = Rec(); tag = B.PlanExec(r, mem((0x100, good))).run(0x100)
    check('the same after a WAIT is accepted and END returns its tag', tag == 7 and len(r.sent) == 3)
    a, b2 = B.Script().jump(0x200), B.Script().end(9)
    pe = B.PlanExec(Rec(), mem((0x100, a), (0x200, b2))); tag = pe.run(0x100)
    check('JUMP continues in the script it points to', tag == 9 and [x[1] for x in pe.log] == ['JUMP', 'END'])
    try: B.PlanExec(Rec(), mem((0x100, B.Script().jump(0x100))), step_limit=50).run(0x100); ok = False
    except RuntimeError: ok = True
    check('a script that never reaches END stops at the step limit', ok)

def main():
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-92s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    rules(check)
    d = D.build(); img = d['layout'].image
    exe = F.build('batch')
    s = F.Script(); s.wait(0x3000)
    s.send(hs.cmd_V(), 8, 'V')
    s.send(H.c_D(*D.COPY_WINDOW))
    for a in sorted(img): s.send(H.c_w(a, img[a]), extra=0x40)                               # the host writes the images into far RAM
    pe = B.PlanExec(s, lambda a: img.get(a, 0xEEEEEEEE))
    tag = pe.run(d['entry'])
    check('executor reached END with the tag from the script', tag == D.TAG, '%x' % tag)
    s.wait(2000)
    for tid in range(4): s.send(hs.cmd_Q(tid), 22, 'Q')
    n = len(d['expected'])
    for k in range(n + 1): s.send(H.c_r(d['results'] + k), 4, 'r')
    rx, errs = F.run(exe, s, tag='batch', maxcyc=120_000_000)
    pos = 0; got = []
    for kind, m in s.reps: got.append((kind, rx[pos:pos + m])); pos += m
    it = iter(got)
    def nxt(k):
        kk, b = next(it); assert kk == k, (kk, k); return b
    check('board version 10', hs.dec_V(nxt('V'))['version'] == 10)
    qs = [hs.dec_Q(nxt('Q')) for _ in range(4)]
    check('all four jobs finished, none trapped', all(q['state'] == 3 and not q['trap'] for q in qs), ' '.join('%d/%d' % (q['state'], q['trap']) for q in qs))
    block = [H.dec_r(nxt('r')) for _ in range(n)]; after = H.dec_r(nxt('r'))
    check('results of both phases, gathered in one far-RAM block (%d words), equal the Python answer' % n, block == d['expected'], ' '.join('%x' % x for x in block[:3]) + ' ...')
    first_bad = next((i for i in range(n) if block[i] != d['expected'][i]), None)
    if first_bad is not None: check('first differing word', False, 'index %d got %x want %x' % (first_bad, block[first_bad], d['expected'][first_bad]))
    n1 = len(d['jobs'][0].expected()) + len(d['jobs'][1].expected())
    check('phase 2 (new code store, new regions) gave the right words: its results are the last %d' % (n - n1), block[n1:] == d['expected'][n1:])
    check('the word past the block was not written', after == 0xEEEEEEEE, '%08x' % after)
    check('SDRAM model reports no timing violations', not errs, repr(errs[:2]))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
