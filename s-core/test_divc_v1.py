"""test_divc_v1.py - divide by a constant with one multiply (ledger #1590): divconst_v1.py and programs/vdivc.s on the host interpreter, with the software multiply (0 units) and the unit model (1 unit).  Run: python3 test_divc_v1.py"""
import sys, random
import jobio_ext_v1 as X, jobio as J, jobiss, progs, divconst_v1 as D
bad = 0
def check(name, cond):
    global bad
    print('%-100s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
check('the worked example: 35 / 13 = 2 and 13 / 13 = 1 (a naive 0.0769 gives 0 for the second)', D.div(35, *D.best(13)[:2]) == 2 and D.div(13, *D.best(13)[:2]) == 1)
w = [d for d in list(range(1, 400)) + [1000, 4095, 65535, 65536, 1 << 20, (1 << 31) - 1] if D.check(d, *D.best(d)) is not None]
check('every divisor 1..399 and some large ones: the multiply and shift is exact over its whole stated range (edges brute-forced)', not w)
check('the stated range is at least 47,000 for every divisor up to 300', min(D.best(d)[2] for d in range(1, 301)) >= 47000)
X.install(0); progs.register('vdivc', 'programs/vdivc.s', expect='programs.examples_v6:vdivc_ref', out='same', replace=True)
random.seed(11); steps = {}
for units in (0, 1):
    X.install(units); ok = True
    for d in (1, 2, 3, 7, 10, 13, 100, 255, 1000, 4096, 65537):
        arg, xmax = D.pack(d)
        xs = [x for x in [0, 1, d - 1, d, d + 1, xmax, max(xmax - 1, 0)] if x <= xmax] + [random.randint(0, xmax) for _ in range(9)]
        j = J.Job(0, 'vdivc', xs, len(xs), arg=arg); lk = J.build_link([j]); st, n, out, s = jobiss.reference(lk, j)
        if not (st == 1 and out == [x // d for x in xs]): ok = False; print('   wrong for d =', d)
        steps[(units, d)] = s / len(xs)
    check('program vdivc.s on the interpreter, %d unit(s): equal to x // d for 11 divisors, edges and random x within the range' % units, ok)
check('with the unit the program is far shorter (d = 13: %.0f against %.0f instructions per word)' % (steps[(1, 13)], steps[(0, 13)]), steps[(1, 13)] * 5 < steps[(0, 13)])
X.uninstall()
print('ALL PASSED' if not bad else 'FAILED %d' % bad); sys.exit(1 if bad else 0)
