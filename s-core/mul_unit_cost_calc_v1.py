"""mul_unit_cost_calc_v1.py - turns the clock counts of batches/mul_unit_cost.score into the cost of one multiply WITH the unit (ledger #1584).
Usage: python3 mul_unit_cost_calc_v1.py A B C LW     A = 40 words arg 0xFFFFFFFF, B = 80 words same, C = 80 words arg 1 (clocks of block 0), LW = 0 or 5 (run it once for each).
Clocks per word = (B - A) / 40.  The loop around the multiply costs (instructions per word - the multiply's) clocks too, so the unit's own cost is the word cost minus an
ordinary loop word; that is estimated with the host reference core (jobiss) by counting instructions and using the clocks per instruction measured in #1575/#1577
(about 137 at lw 0, 9 at lw 5).  The software numbers for comparison are the measured ones of #1577: 30,900 clocks (lw 0) and 2,010 (lw 5) per 32-bit multiply."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
SOFT = {0: 30900.0, 5: 2010.0}; CPI = {0: 137.0, 5: 9.0}
def main(a):
    A, B, C, LW = float(a[0]), float(a[1]), float(a[2]), int(a[3])
    if LW not in SOFT: print('LW must be 0 or 5'); return 2
    import jobio_ext_v1 as X, jobio as J, jobiss, progs
    X.install(1); progs.register('vmul32l', 'programs/vmul32l.s', expect='programs.examples_v4:vmul32_ref', out='same', replace=True)
    def steps(n, arg):
        j = J.Job(0, 'vmul32l', list(range(1000, 1000 + n)), n, arg=arg); lk = J.build_link([j]); return jobiss.reference(lk, j)[3]
    s40, s80 = steps(40, 0xFFFFFFFF), steps(80, 0xFFFFFFFF); ipw = (s80 - s40) / 40.0
    word = (B - A) / 40.0
    print('lw %d: clocks per word with the unit = (B-A)/40 = %.1f   (instructions per word on the interpreter: %.1f, so %.1f clocks per instruction; %.0f is the ordinary figure)' % (LW, word, ipw, word / ipw, CPI[LW]))
    print('   the software multiply (#1577) cost %.0f clocks per word (arg 0xFFFFFFFF, loop included): the unit is about %.0f times cheaper per word' % (SOFT[LW], SOFT[LW] / word))
    print('   start-up per run (B minus 80 words) = %.0f clocks; C (arg 1) is a cross-check: its per-word cost should equal this build\'s word cost, i.e. C - start-up = %.0f for 80 words (expected %.0f)' % (B - 80 * word, C - (B - 80 * word), 80 * word))
    return 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]) if len(sys.argv) == 5 else print(__doc__) or 2)
