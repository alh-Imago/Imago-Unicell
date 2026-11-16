"""Job I/O convention + gathering of results, in the whole-board simulation with the far RAM (fpga/sc_top_pool13.v, SDRAM model).  Needs iverilog.
 1. four jobs (vsum, vscale, a clone of vscale with other data, a clone of vsum told it has no output space) are given headers and inputs by the host,
    run, and their status / n_out are read; the clone told 'no output space' must REFUSE (status 2, n_out 0, nothing written);
 2. each job's n_out words are copied out of its window into ONE contiguous block of far RAM (stitch) and the block is compared with the answer computed in Python;
 3. a shared-RAM stress job runs alone and then again while a 256-word copy runs: same result, same clock count (the copy yields to the cores)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, jobio as J
import test_farram_sim as F

def main():
    exe = F.build('jobio'); bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-76s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    A = J.Job(0, 'vsum', [3 * i + 1 for i in range(12)], 1)
    B = J.Job(1, 'vscale', [100 + 7 * i for i in range(10)], 10)
    S = J.Job(2, 'vstress', [5, 6, 7, 8, 9, 10, 11, 12], 1, arg=12)
    C = J.Job(3, 'vscale', [0xFFFFFFF0 + i for i in range(10)], 10, clone_of=1)            # wraps around 32 bits
    D = J.Job(4, 'vsum', [9 + i for i in range(12)], 1, clone_of=0, hdr_out_len=0)         # told it has no output space
    jobs = [A, B, C, D]
    lk = J.build_link([A, B, S, C, D])
    print(lk.report().splitlines()[0])
    s = F.Script(); s.wait(0x3000)
    s.send(hs.cmd_V(), 8, 'V')
    for c in lk.commands(): s.send(c, extra=0x100 if c[:1] in (b'W', b'M') else 0)
    for j in jobs + [S]:
        for c in J.prepare_cmds(lk, j): s.send(c, extra=0x100)
    # 1. run the four jobs
    for tid, j in enumerate(jobs): s.send(hs.cmd_P(tid, lk.classes[j.cid]['entry'], 0, 0, j.cid))
    s.wait(200000)
    for j in jobs:
        b = J.window_base(lk, j)
        s.send(hs.cmd_L(b + J.F_STATUS), 4, 'L'); s.send(hs.cmd_L(b + J.F_NOUT), 4, 'L')
    for tid in range(len(jobs)): s.send(hs.cmd_Q(tid), 22, 'Q')
    # 2. stitch the outputs into one block of far RAM
    FAR = 0x1000
    s.send(H.c_D(FAR, 0x200))
    exp_n = [len(j.expected()) if j is not D else 0 for j in jobs]
    plan, total = J.stitch(lk, list(zip(jobs, exp_n)), FAR)
    for near, far, cnt in plan: s.send(H.c_F(0, near, far, cnt), 0, extra=0x1200); s.send(H.c_N(), 12, 'N')
    for k in range(total): s.send(H.c_r(FAR + k), 4, 'r')
    s.send(H.c_r(FAR + total), 4, 'r')                                                      # just past the block: must not be written
    # 3. stress job alone, then with a copy running
    sb = J.window_base(lk, S)
    s.send(hs.cmd_P(10, lk.classes[2]['entry'], 0, 0, 2)); s.wait(150000); s.send(hs.cmd_Q(10), 22, 'Q')
    s.send(hs.cmd_L(sb + S.out_off), 4, 'L')
    s.send(hs.cmd_M(sb + S.out_off, 0), extra=0x100)
    s.send(hs.cmd_P(11, lk.classes[2]['entry'], 0, 0, 2)); s.wait(300)
    s.send(H.c_F(0, 0, FAR + 0x40, 256), 0, extra=0x1800); s.send(H.c_N(), 12, 'N')
    s.wait(150000); s.send(hs.cmd_Q(11), 22, 'Q'); s.send(hs.cmd_L(sb + S.out_off), 4, 'L'); s.send(hs.cmd_L(sb + J.F_STATUS), 4, 'L')
    s.wait(2000)
    rx, errs = F.run(exe, s, tag='jobio', maxcyc=80_000_000)
    pos = 0; got = []
    for kind, n in s.reps: got.append((kind, rx[pos:pos + n])); pos += n
    it = iter(got)
    def nxt(k):
        kk, b = next(it); assert kk == k, (kk, k); return b
    v = hs.dec_V(nxt('V'))
    check('board version 10', v['version'] == 10)
    st = [(int.from_bytes(nxt('L'), 'little'), int.from_bytes(nxt('L'), 'little')) for _ in jobs]
    qs = [hs.dec_Q(nxt('Q')) for _ in jobs]
    for (j, name), (status, nout), q in zip(((A, 'vsum 12 words'), (B, 'vscale 10 words'), (C, 'vscale clone, wrapping data'), (D, 'vsum clone told: no output space')), st, qs):
        if j is D: check('%-34s refused: status 2, n_out 0' % name, status == 2 and nout == 0 and not q['trap'], 'status %d n_out %d a0 %d' % (status, nout, q['a0']))
        else:      check('%-34s finished: status 1, n_out %d' % (name, len(j.expected())), status == 1 and nout == len(j.expected()) and not q['trap'], 'status %d n_out %d' % (status, nout))
    for _ in plan: n = H.dec_N(nxt('N')); check('copy of a result into the far block: %d words' % n['moved'], n['err'] == 0 and n['moved'] > 0)
    block = [H.dec_r(nxt('r')) for _ in range(total)]; after = H.dec_r(nxt('r'))
    want = A.expected() + B.expected() + C.expected()
    check('stitched block in far RAM = %d words, one after another, equal to the Python answer' % total, block == want, ' '.join('%x' % x for x in block[:4]) + ' ...')
    check('the word just past the block was not written (a never-written word reads as unknown in the model)', after == 0xEEEEEEEE, '%08x' % after)
    q10 = hs.dec_Q(nxt('Q')); o10 = int.from_bytes(nxt('L'), 'little')
    nn = H.dec_N(nxt('N')); q11 = hs.dec_Q(nxt('Q')); o11 = int.from_bytes(nxt('L'), 'little'); s11 = int.from_bytes(nxt('L'), 'little')
    check('stress job alone: result right', q10['state'] == 3 and not q10['trap'] and o10 == S.expected()[0] and q10['a0'] == S.expected()[0], 'out %d expect %d' % (o10, S.expected()[0]))
    check('copy of 256 words completes while the stress job runs', nn['err'] == 0 and nn['moved'] == 256)
    check('stress job with the copy running: result right', q11['state'] == 3 and not q11['trap'] and o11 == S.expected()[0] and s11 == 1, 'out %d status %d' % (o11, s11))
    d10, d11 = q10['end'] - q10['start'], q11['end'] - q11['start']
    check('the copy did not slow a job that uses the shared RAM (within 4 clocks)', abs(d10 - d11) <= 4, 'alone %d clocks, with a copy %d clocks' % (d10, d11))
    check('SDRAM model reports no timing violations', not errs, repr(errs[:2]))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
