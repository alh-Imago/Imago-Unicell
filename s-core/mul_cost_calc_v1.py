"""mul_cost_calc_v1.py - turns the three clock counts of batches/mul_cost.score into the cost of a shift-and-add multiply (ledger #1574).
Usage: python3 mul_cost_calc_v1.py A B C        A = 40 words gain 255, B = 80 words gain 255, C = 80 words gain 1 (clocks of block 0, one width).
Instruction counts come from the host reference core (jobiss), so the answer is clocks per instruction on THIS build at THIS width.
  (B-A)/40 clocks per word at gain 255 / instructions per word  = clocks per instruction (start-up cancels)
  (B-C)/80 clocks per word saved by gain 1             / instructions per word saved = the same figure from a different pair (a check)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

def instructions(n, gain):
    import progs, jobio as J, jobiss
    try: progs.register('zvg_mc', 'programs/vgain.s', expect='programs.examples:vgain_ref', check=False, replace=True)
    except Exception: pass
    j = J.Job(0, 'zvg_mc', list(range(1000, 1000 + n)), n, arg=gain)
    st, nout, out, steps = jobiss.reference(J.build_link([j]), j)
    if st != 1: raise SystemExit('the reference core gave status %s for n=%d gain=%d' % (st, n, gain))
    return steps

def calc(a, b, c, steps=instructions):
    ia, ib, ic = steps(40, 255), steps(80, 255), steps(80, 1)
    cpi1 = (b - a) / float(ib - ia)
    cpi2 = (b - c) / float(ib - ic)
    mul8 = 57 * cpi1
    return dict(instr=(ia, ib, ic), per_word_255=(ib - ia) / 40.0, cpi_from_BA=cpi1, cpi_from_BC=cpi2, clocks_8bit_mul=mul8, ms_8bit_mul=mul8 / 50000.0)

if __name__ == '__main__':
    if len(sys.argv) != 4: raise SystemExit(__doc__)
    a, b, c = [float(x) for x in sys.argv[1:]]
    r = calc(a, b, c)
    print('instructions on the reference core: A %d, B %d, C %d (%.1f per word at gain 255)' % (r['instr'] + (r['per_word_255'],)))
    print('clocks per instruction: %.1f (from B-A), %.1f (from B-C; the two should agree within a few percent)' % (r['cpi_from_BA'], r['cpi_from_BC']))
    print('one 8-bit shift-and-add multiply (57 instructions): about %.0f clocks = %.3f ms at 50 MHz' % (r['clocks_8bit_mul'], r['ms_8bit_mul']))
