"""F1 of the fusion plan: uc_core_v2w (width chosen at run time: unfused W=1 / fused W=2) against (a) the independent RV32I reference simulator of runtests.py and
(b) uc_core_v2 built at W=1 and W=2: the SAME results and the SAME clock count are required (ledger #1354).  Needs iverilog.  About 1 minute."""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import runtests as R

CORE = 'uc_core_v2w'      # or give another module/file name (without .v) as the first argument: python3 test_fz.py uc_core_v2w2

def build(wd, fz):
    exe = os.path.join(wd, 'sim_fz%d' % fz)
    tbf = os.path.join(wd, 'tb_fz_%s.v' % CORE)        # the testbench with the module name of the core under test
    open(tbf, 'w').write(open(os.path.join(HERE, 'tb_fz.v')).read().replace('uc_core_v2w dut', CORE + ' dut'))
    r = subprocess.run(['iverilog', '-g2012', '-P', 'tb_fz.FZ=%d' % fz, '-o', exe, tbf, os.path.join(HERE, CORE + '.v')], capture_output=True, text=True)
    if r.returncode: print(r.stderr); sys.exit(1)
    return exe

def run_fz(exe, words, tag, wd):
    hexf = os.path.join(wd, tag + '.hex'); outf = os.path.join(wd, '%s_%s.out' % (os.path.basename(exe), tag))
    open(hexf, 'w').write('\n'.join('%08x' % x for x in words) + '\n')
    subprocess.run(['vvp', '-n', exe, '+prog=' + hexf, '+out=' + outf], check=True, capture_output=True)
    res = dict(x=[0] * 32, dm=[0] * R.DM_WORDS)
    for line in open(outf):
        p = line.split()
        if p[0] == 'r': res['x'][int(p[1])] = int(p[2])
        elif p[0] == 'm': res['dm'][int(p[1])] = int(p[2])
        else: res[p[0]] = int(p[1])
    return res

def main(nrand=40):
    wd = tempfile.mkdtemp(prefix='fz_')
    ex = {0: build(wd, 0), 1: build(wd, 1)}
    for W in (1, 2):
        r = subprocess.run(['iverilog', '-g2012', '-DCORE=uc_core_v2', '-P', 'tb.W=%d' % W, '-o', os.path.join(wd, 'sim_uc_core_v2_%d' % W), os.path.join(HERE, 'tb.v'), os.path.join(HERE, 'uc_core_v2.v')], capture_output=True, text=True)
        if r.returncode: print(r.stderr); sys.exit(1)
    progs = [(n, R.assemble(t)) for n, t in R.PROGRAMS.items()] + [('rand%03d' % s, R.gen_random(s)) for s in range(nrand)]
    fails = runs = 0; cyc = {}
    for name, words in progs:
        ref = R.iss(words)
        for fz in (0, 1):
            W = 1 + fz
            hw = run_fz(ex[fz], words, name, wd)
            old = R.run_hw(W, words, name, wd, 'uc_core_v2')
            errs = R.compare(ref, hw); runs += 1
            if hw['cycles'] != old['cycles']: errs.append('cycles %d, uc_core_v2 W=%d has %d' % (hw['cycles'], W, old['cycles']))
            for i in range(32):
                if hw['x'][i] != old['x'][i]: errs.append('x%d differs from uc_core_v2' % i); break
            if errs: fails += 1; print('FAIL %-14s fz=%d %s' % (name, fz, '; '.join(errs[:4])))
            cyc.setdefault(name, {})[fz] = (hw['cycles'], hw['instret'])
    print('%d/%d runs: results equal to the reference simulator and to uc_core_v2, clock counts equal to uc_core_v2 at W=1 (fz=0) and W=2 (fz=1)' % (runs - fails, runs))
    for n in R.PROGRAMS: print('%-14s CPI fz=0 %6.2f  fz=1 %6.2f' % (n, cyc[n][0][0] / cyc[n][0][1], cyc[n][1][0] / cyc[n][1][1]))
    print('RESULT:', 'PASS' if not fails else 'FAIL (%d)' % fails)
    return 1 if fails else 0
if __name__ == '__main__':
    if len(sys.argv) > 1: CORE = sys.argv[1]
    sys.exit(main())
