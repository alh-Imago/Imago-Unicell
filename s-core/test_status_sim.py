"""v12 read-out in the whole-board simulation (POOL=8): status snapshot (T), per-slice usage (U), trap cause and address (E).
Usage: python3 test_status_sim.py [S]   (default 4)
Phase 1: S+2 critical and 3 bulk long-running jobs: while they run, T must show S slices running, 2 critical + 3 bulk waiting, tids 0..S-1;
         after they finish T must show an idle board and the per-slice usage must add up to the board's own busy counter.
Phase 2: one job per violation kind plus a good job: E must give the right cause and address for each, 0 for the good one."""
import os, sys
os.environ['POOL'] = '8'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import test_board_sim as tbs, host_sc as hs, status_cases as sc

def main(S=4, div=8):
    SPIN = 1500; lk = sc.link(SPIN)
    exe = tbs.build(S=S, QD=16, IMW=128, DMW=16, DIV=div, tag='sta', DSH=256)
    seq, order, tags = [], [], []
    def B(b): seq.append(('B', b))
    def D(n): seq.append(('D', n))
    def rd(cmdb, kind, nbytes, tag):
        B(cmdb); order.append(kind); tags.append(tag); D(nbytes * 10 * div + 4 * div * 10)
    rd(hs.cmd_V(), 'V', 8, 'V')
    for c in lk.commands(): B(c)
    B(hs.cmd_H())
    n_crit = S + 2
    for t in range(n_crit): B(hs.cmd_P(t, lk.classes[1]['entry'], 0, 1, 1))
    for t in range(n_crit, n_crit + 3): B(hs.cmd_P(t, lk.classes[1]['entry'], 0, 0, 1))
    D(2000); rd(hs.cmd_T(), 'T', 8 + 4 * S, 'T_hold')       # on hold: everything waits
    B(hs.cmd_G()); D(20000)
    rd(hs.cmd_T(), 'T', 8 + 4 * S, 'T_run'); rd(hs.cmd_U(), 'U', 8 + 8 * S, 'U_run')
    rounds = -(-(n_crit + 3) // S)
    D(rounds * 450000 + 100000)
    rd(hs.cmd_T(), 'T', 8 + 4 * S, 'T_idle'); rd(hs.cmd_U(), 'U', 8 + 8 * S, 'U_end'); rd(hs.cmd_C(), 'C', 56, 'C_end')
    for t in range(n_crit + 3): rd(hs.cmd_Q(t), 'Q', 22, 'Q%d' % t)
    # phase 2
    kinds = sc.WANT
    B(hs.cmd_H())
    for i, c in enumerate(kinds): B(hs.cmd_P(i, lk.classes[c]['entry'], 0, 0, c))
    B(hs.cmd_G()); D(60000)
    for i, c in enumerate(kinds): rd(hs.cmd_E(i), 'E', 5, 'E%d' % c); rd(hs.cmd_Q(i), 'Q', 22, 'P2Q%d' % c)
    D(10); rd(hs.cmd_T(), 'T', 8 + 4 * S, 'T_end')
    out = tbs.run(exe, seq, tag='sta')
    dec = {'V': lambda b: hs.dec_V(b), 'T': lambda b: hs.dec_T(b, S), 'U': lambda b: hs.dec_U(b, S), 'C': hs.dec_C, 'Q': hs.dec_Q, 'E': hs.dec_E}
    # split by sizes
    sizes = {'V': 8, 'T': 8 + 4 * S, 'U': 8 + 8 * S, 'C': 56, 'Q': 22, 'E': 5}
    res, pos = {}, 0
    for k, tg in zip(order, tags):
        res[tg] = dec[k](out[pos:pos + sizes[k]]); pos += sizes[k]
    chk0 = pos == len(out)
    if not chk0: print('reply bytes: used %d of %d' % (pos, len(out)))
    return sc.evaluate(res, S, n_crit, SPIN) and chk0

if __name__ == '__main__': sys.exit(0 if main(int(sys.argv[1]) if len(sys.argv) > 1 else 4) else 1)
