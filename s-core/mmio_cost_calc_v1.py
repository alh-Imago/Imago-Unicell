"""mmio_cost_calc_v1.py - what a memory-mapped multiply would cost, from the four clock counts of batches/mmio_cost.score (ledger #1580).
Usage: python3 mmio_cost_calc_v1.py M100 M300 C100 C300   (block-0 clocks for ONE width; M = vmmio.s, C = vnomem.s; N = 100 and 300)
Each pass of both programs is 7 instructions; vmmio makes 3 shared-RAM accesses (2 stores and 1 load) in every pass, vnomem makes none.
  per pass = (clocks at N=300 - clocks at N=100) / 200      (start-up cancels)
  an access to the shared RAM costs (per pass vmmio - per pass vnomem) / 3 clocks more than a register move
  a multiply through memory = the 3 accesses + the loop work around them is NOT counted: it is 3 instructions (sw, sw, lw) of that cost."""
import sys
PASS_INSTR = 7        # the loop of both programs: beqz, three accesses (or moves), addi, addi, j  (checked on the reference core: 7.0 per pass)

def calc(m100, m300, c100, c300):
    pm, pc = (m300 - m100) / 200.0, (c300 - c100) / 200.0
    cpi = pc / PASS_INSTR                      # clocks per instruction of the control loop
    extra = (pm - pc) / 3.0                    # extra clocks of one shared-RAM access over a register move
    access = cpi + extra                       # clocks of one shared-RAM access instruction
    mul_mem = 3 * access                       # sw, sw, lw
    return dict(per_pass_mmio=pm, per_pass_ctrl=pc, cpi=cpi, extra_per_access=extra, clocks_per_access=access, mul_via_memory=mul_mem)

if __name__ == '__main__':
    if len(sys.argv) != 5: raise SystemExit(__doc__)
    r = calc(*[float(x) for x in sys.argv[1:]])
    print('clocks per pass: vmmio %.1f, vnomem %.1f (7 instructions each)' % (r['per_pass_mmio'], r['per_pass_ctrl']))
    print('clocks per instruction of the control loop: %.1f' % r['cpi'])
    print('one shared-RAM access costs %.1f clocks (%.1f more than a register move)' % (r['clocks_per_access'], r['extra_per_access']))
    print('a multiply through memory (two stores and a load, unit latency NOT included): about %.0f clocks' % r['mul_via_memory'])
    for name, sw in (('32-bit software multiply, lw 0', 30900), ('32-bit software multiply, lw 5', 2010), ('8-bit software multiply, lw 0', 7940), ('8-bit software multiply, lw 5', 540)):
        print('   against the %s (%d clocks): %.0f times cheaper' % (name, sw, sw / r['mul_via_memory']))
