"""test_jobio_ext_v1.py - the multiply library and unit count of jobio_ext_v1 (ledger #1582, #1584): software path, unit path (modelled in jobiss_v2), header word 7, restore.  Run: python3 test_jobio_ext_v1.py"""
import sys
import jobio_ext_v1 as X, jobio as J, jobiss, jobiss_v2, progs
bad = 0
def check(name, cond):
    global bad
    print('%-100s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
orig_link, orig_prep, orig_run = J.build_link, J.prepare, jobiss.run_class
X.install(0)
progs.register('vmul32l', 'programs/vmul32l.s', expect='programs.examples_v4:vmul32_ref', out='same', replace=True)
data = [1000 + 7 * i for i in range(40)]
res = {}
for units in (0, 1):
    X.install(units)
    for arg in (0, 1, 255, 12345, 0xFFFFFFFF, 0x80000001):
        j = J.Job(0, 'vmul32l', data, 40, arg=arg); lk = J.build_link([j]); st, n, out, steps = jobiss.reference(lk, j)
        check('units %d arg %#x: status 1, 40 words, equal to (x*arg) mod 2^32' % (units, arg), st == 1 and n == 40 and out == [(x * arg) & 0xFFFFFFFF for x in data])
        res[(units, arg)] = steps
    j = J.Job(0, 'vmul32l', [5], 1, arg=3); lk = J.build_link([j])
    check('units %d: header word 7 holds the unit count' % units, J.prepare(lk, j)[J.window_base(lk, j) + J.F_SPARE] == units)
check('the unit path is much shorter than the software path (arg 0xFFFFFFFF: %d against %d instructions)' % (res[(1, 0xFFFFFFFF)], res[(0, 0xFFFFFFFF)]), res[(1, 0xFFFFFFFF)] * 10 < res[(0, 0xFFFFFFFF)])
X.uninstall()
check('uninstall restores jobio.build_link, jobio.prepare and jobiss.run_class', J.build_link is orig_link and J.prepare is orig_prep and jobiss.run_class is orig_run and jobiss_v2.UNITS[0] == 0)
print('ALL PASSED' if not bad else 'FAILED %d' % bad); sys.exit(1 if bad else 0)
