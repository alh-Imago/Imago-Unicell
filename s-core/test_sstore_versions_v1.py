"""test_sstore_versions_v1.py - does each dispatcher version lose a shared store when a fused unit stores twice in quick succession?  (ledger #1588; the question left open in #1531)
Runs the program `sstore` of test_sys21p.py (three consecutive stores to shared words 20, 21, 22, then loads them back; expected a0 = 187) on sc_sys_v16 ... v22 for lw 0 up to the unit width.
Versions 16 to 18 only build units up to 16 lanes, so every version is run at S = 16, ULW = 4, at S = 32, ULW = 4 as well, and the versions from 19 also at S = 32, ULW = 5.  v22 is the fix, so it must pass.
Usage: python3 test_sstore_versions_v1.py"""
import os, sys, subprocess, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import runtests as R
src = open(os.path.join(HERE, 'test_sys21p.py')).read()
SSTORE = re.search(r"SSTORE = '''(.*?)'''", src, re.S).group(1)
words = R.assemble(SSTORE)
wd0 = '/tmp/sstore_versions'; os.makedirs(wd0, exist_ok=True)
open(wd0 + '/prog.hex', 'w').write('\n'.join('%08x' % w for w in words) + '\n')
def one(v, S, ULW):
    W = 1 << ULW; wd = '%s/v%d_S%d' % (wd0, v, S); os.makedirs(wd, exist_ok=True)
    srcs = ['tb_sys%d.v' % v, 'sc_sys_v%d.v' % v, 'fit_search_tree.v', 'uc_core_v2v.v', 'uc_unitw%d.v' % W, 'uc_unith%d.v' % W]
    pars = ['-P', 'tb_sys%d.S=%d' % (v, S), '-P', 'tb_sys%d.ULW=%d' % (v, ULW), '-P', 'tb_sys%d.FZ=1' % v] + (['-P', 'tb_sys%d.NU=1' % v] if v >= 17 else [])
    r = subprocess.run(['iverilog', '-g2012'] + pars + ['-o', wd + '/sim'] + [os.path.join(HERE, f) for f in srcs], capture_output=True, text=True)
    if r.returncode: return 'did not compile: ' + r.stderr[-160:].replace('\n', ' ')
    row = []
    for lw in range(0, ULW + 1):
        open(wd + '/tasks.hex', 'w').write('%08x\n%08x\n%08x\n' % (0, 0, lw))
        subprocess.run(['vvp', wd + '/sim', '+prog=' + wd0 + '/prog.hex', '+tasks=' + wd + '/tasks.hex', '+ntasks=1', '+out=' + wd + '/out.txt'], capture_output=True, text=True)
        L = open(wd + '/out.txt').read().splitlines(); t = [l.split() for l in L if l.startswith('t ')]
        row.append((lw,) + ((int(t[0][2]), int(t[0][3])) if t else (-1, -1)))
    return row
v22ok = True
for S, ULW, versions in ((16, 4, range(16, 23)), (32, 4, range(16, 23)), (32, 5, range(19, 23))):
    print('S = %d, ULW = %d (widths lw 0 to %d):' % (S, ULW, ULW))
    for v in versions:
        row = one(v, S, ULW)
        if isinstance(row, str): print('  v%d: %s' % (v, row)); continue
        fails = [(lw, a0) for lw, a0, tr in row if not (a0 == 187 and tr == 0)]
        print('  v%d: %s' % (v, 'correct at every width' if not fails else 'WRONG at ' + ', '.join('lw %d (a0 %#x)' % f for f in fails)))
        if v == 22 and fails: v22ok = False
print('RESULT v22 (the fix) %s' % ('correct' if v22ok else 'WRONG')); sys.exit(0 if v22ok else 1)
