"""mul32_cost_calc_v1.py - turns the four clock counts of batches/mul32_cost.score into the cost of a 32-bit shift-and-add multiply (ledger #1576).
Usage: python3 mul32_cost_calc_v1.py A B C D     A = 40 words arg 0xFFFFFFFF, B = 80 words arg 0xFFFFFFFF, C = 80 words arg 1, D = 80 words arg 255
(clocks of block 0, ONE width: run it once for lw 0 and once for lw 5).  Instruction counts come from the host reference core (jobiss), so the answers are
clocks per instruction on this build at this width; the multiply part of a word is the instructions per word minus the 10 of the loop around it."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
LOOP = 10        # instructions per word outside the multiply (measured with arg 0: 10.5 per word at n 80, 10.9 at n 40, the rest is start-up)

def instructions(n, arg):
    import progs, jobio as J, jobiss
    progs.register('vmul32', 'programs/vmul32.s', expect='programs.examples_v4:vmul32_ref', out='same', replace=True)
    j = J.Job(0, 'vmul32', list(range(1000, 1000 + n)), n, arg=arg)
    st, nout, out, steps = jobiss.reference(J.build_link([j]), j)
    if st != 1: raise SystemExit('the reference core gave status %s for n=%d arg=%d' % (st, n, arg))
    return steps

def calc(a, b, c, d, steps=instructions):
    ia, ib, ic, id_ = steps(40, 0xFFFFFFFF), steps(80, 0xFFFFFFFF), steps(80, 1), steps(80, 255)
    pw = (ib - ia) / 40.0                      # instructions per word at arg 0xFFFFFFFF (start-up cancels)
    cpi_ba = (b - a) / float(ib - ia)
    cpi_bc = (b - c) / float(ib - ic)
    cpi_bd = (b - d) / float(ib - id_)
    cpi = (cpi_ba + cpi_bc + cpi_bd) / 3.0
    return dict(instr=(ia, ib, ic, id_), per_word=pw, cpi=(cpi_ba, cpi_bc, cpi_bd), cpi_mean=cpi, mul32_instr=pw - LOOP, mul32_clocks=(pw - LOOP) * cpi_ba,
                clocks_per_word_32=(b - a) / 40.0)

if __name__ == '__main__':
    if len(sys.argv) != 5: raise SystemExit(__doc__)
    a, b, c, d = [float(x) for x in sys.argv[1:]]
    r = calc(a, b, c, d)
    print('instructions on the reference core: A %d, B %d, C %d, D %d  (%.1f per word at arg 0xFFFFFFFF, of which %d are the loop around the multiply)' % (r['instr'] + (r['per_word'], LOOP)))
    print('clocks per instruction: %.1f (B-A), %.1f (B-C), %.1f (B-D); the three should agree within a few percent' % r['cpi'])
    print('one 32-bit shift-and-add multiply (about %.0f instructions): about %.0f clocks = %.3f ms at 50 MHz' % (r['mul32_instr'], r['mul32_clocks'], r['mul32_clocks'] / 50000.0))
    print('one whole word of the job (multiply plus the loop around it): %.0f clocks' % r['clocks_per_word_32'])
