"""Gate for the wide controller units (ledger #1359):  python3 test_wide.py uc_unitg8 3   (core module/file name, log2 of its widest width)
The core is run at EVERY width 1 .. 2**L (input lw = 0..L) against the independent RV32I reference simulator and uc_core_v2 built at the same width: same results and the SAME
clock counts are required.  Needs iverilog.  Optional third argument: number of random programs (default 40)."""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import runtests as R
from test_fz import run_fz

def main(core, L, nrand=40):
    wd = tempfile.mkdtemp(prefix='wide_'); W = 1 << L; ex = {}
    tbf = os.path.join(wd, 'tb_wide_%s.v' % core)
    open(tbf, 'w').write(open(os.path.join(HERE, 'tb_wide.v')).read().replace('uc_core_dut dut', core + ' dut'))
    for lw in range(L + 1):
        ex[lw] = os.path.join(wd, 'sim_w%d' % lw)
        r = subprocess.run(['iverilog', '-g2012', '-P', 'tb_wide.LW=%d' % lw, '-P', 'tb_wide.BW=%d' % W, '-o', ex[lw], tbf, os.path.join(HERE, core + '.v')], capture_output=True, text=True)
        if r.returncode: print(r.stderr); return 1
        r = subprocess.run(['iverilog', '-g2012', '-DCORE=uc_core_v2', '-P', 'tb.W=%d' % (1 << lw), '-o', os.path.join(wd, 'sim_uc_core_v2_%d' % (1 << lw)), os.path.join(HERE, 'tb.v'), os.path.join(HERE, 'uc_core_v2.v')], capture_output=True, text=True)
        if r.returncode: print(r.stderr); return 1
    progs = [(n, R.assemble(t)) for n, t in R.PROGRAMS.items()] + [('rand%03d' % s, R.gen_random(s)) for s in range(nrand)]
    fails = runs = 0; cyc = {}
    for name, words in progs:
        ref = R.iss(words)
        for lw in range(L + 1):
            hw = run_fz(ex[lw], words, name, wd); old = R.run_hw(1 << lw, words, name, wd, 'uc_core_v2')
            errs = R.compare(ref, hw); runs += 1
            if hw['cycles'] != old['cycles']: errs.append('cycles %d, uc_core_v2 W=%d has %d' % (hw['cycles'], 1 << lw, old['cycles']))
            for i in range(32):
                if hw['x'][i] != old['x'][i]: errs.append('x%d differs from uc_core_v2' % i); break
            if errs: fails += 1; print('FAIL %-14s lw=%d %s' % (name, lw, '; '.join(errs[:4])))
            cyc.setdefault(name, {})[lw] = (hw['cycles'], hw['instret'])
    print('%d/%d runs: results equal to the reference simulator and to uc_core_v2, clock counts equal to uc_core_v2 at W = %s' % (runs - fails, runs, ', '.join(str(1 << k) for k in range(L + 1))))
    for n in R.PROGRAMS: print('%-14s CPI ' % n + '  '.join('W=%-2d %6.2f' % (1 << lw, cyc[n][lw][0] / cyc[n][lw][1]) for lw in range(L + 1)))
    print('RESULT:', 'PASS' if not fails else 'FAIL (%d)' % fails)
    return 1 if fails else 0
if __name__ == '__main__':
    sys.exit(main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 40))
