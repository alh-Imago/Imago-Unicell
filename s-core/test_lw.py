"""F2 step of the fusion plan: uc_core_v2w4 (width chosen at run time: lw = 0, 1, 2 -> W = 1, 2, 4) against the independent RV32I reference simulator and uc_core_v2 built at
W = 1, 2, 4: same results and the SAME clock counts are required (ledger #1357).  Optional argument: another core file/module name (default uc_core_v2w4).  Needs iverilog."""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import runtests as R
from test_fz import run_fz
CORE = 'uc_core_v2w4'

def build(wd, lw):
    exe = os.path.join(wd, 'sim_lw%d' % lw); tbf = os.path.join(wd, 'tb_lw_%s.v' % CORE)
    open(tbf, 'w').write(open(os.path.join(HERE, 'tb_lw.v')).read().replace('uc_core_v2w4 dut', CORE + ' dut'))
    r = subprocess.run(['iverilog', '-g2012', '-P', 'tb_lw.LW=%d' % lw, '-o', exe, tbf, os.path.join(HERE, CORE + '.v')], capture_output=True, text=True)
    if r.returncode: print(r.stderr); sys.exit(1)
    return exe

def main(nrand=40, widths=(0, 1, 2)):
    wd = tempfile.mkdtemp(prefix='lw_')
    ex = {lw: build(wd, lw) for lw in widths}
    for lw in widths:
        W = 1 << lw
        r = subprocess.run(['iverilog', '-g2012', '-DCORE=uc_core_v2', '-P', 'tb.W=%d' % W, '-o', os.path.join(wd, 'sim_uc_core_v2_%d' % W), os.path.join(HERE, 'tb.v'), os.path.join(HERE, 'uc_core_v2.v')], capture_output=True, text=True)
        if r.returncode: print(r.stderr); sys.exit(1)
    progs = [(n, R.assemble(t)) for n, t in R.PROGRAMS.items()] + [('rand%03d' % s, R.gen_random(s)) for s in range(nrand)]
    fails = runs = 0; cyc = {}
    for name, words in progs:
        ref = R.iss(words)
        for lw in widths:
            W = 1 << lw
            hw = run_fz(ex[lw], words, name, wd); old = R.run_hw(W, words, name, wd, 'uc_core_v2')
            errs = R.compare(ref, hw); runs += 1
            if hw['cycles'] != old['cycles']: errs.append('cycles %d, uc_core_v2 W=%d has %d' % (hw['cycles'], W, old['cycles']))
            for i in range(32):
                if hw['x'][i] != old['x'][i]: errs.append('x%d differs from uc_core_v2' % i); break
            if errs: fails += 1; print('FAIL %-14s lw=%d %s' % (name, lw, '; '.join(errs[:4])))
            cyc.setdefault(name, {})[lw] = (hw['cycles'], hw['instret'])
    print('%d/%d runs: results equal to the reference simulator and to uc_core_v2, clock counts equal to uc_core_v2 at W=1, 2, 4' % (runs - fails, runs))
    for n in R.PROGRAMS: print('%-14s CPI W=1 %6.2f  W=2 %6.2f  W=4 %6.2f' % ((n,) + tuple(cyc[n][lw][0] / cyc[n][lw][1] for lw in widths)))
    print('RESULT:', 'PASS' if not fails else 'FAIL (%d)' % fails)
    return 1 if fails else 0
if __name__ == '__main__':
    if len(sys.argv) > 1: CORE = sys.argv[1]
    sys.exit(main())
