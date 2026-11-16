"""Simulation test of the SDRAM controller (fpga/sdram_ctl.v) against the checking model (fpga/sdram_model.v) through the whole UART path.
Runs: version/info, single word write+read, the on-chip test in all four modes, a configuration sweep with NEGATIVE controls (a wrong capture
delay or a wrong CAS latency must be caught), and a refresh test (a long idle between write and read).  Needs iverilog."""
import os, subprocess, sys, shutil
import sdt_host as H

HERE = os.path.dirname(os.path.abspath(__file__))
FPGA = os.path.join(HERE, 'fpga')
SRC = ['tb_top_sdt.v', 'sc_top_sdt.v', 'sdt_bridge.v', 'sdt_selftest.v', 'sdram_ctl.v', 'sdram_model.v', 'uart.v']

def build(tag='sdt'):
    if not shutil.which('iverilog'): print('SKIP: iverilog not installed'); sys.exit(1)      # a skipped suite must not look like a pass
    exe = os.path.join(HERE, tag + '.vvp')
    subprocess.run(['iverilog', '-g2012', '-o', exe] + [os.path.join(FPGA, f) for f in SRC], check=True)
    return exe

def _hx(t):
    try: return int(t, 16)
    except ValueError: return 0xEE        # a byte with z/x bits: the model's bus was undriven when sampled (only possible in simulation)

def run(exe, seq, tag='sdt', maxcyc=40_000_000):
    cf, of = os.path.join(HERE, tag + '.cmds'), os.path.join(HERE, tag + '.rx')
    with open(cf, 'w') as f:
        for kind, v in seq:
            if kind == 'B':
                for b in v: f.write('B %02x\n' % b)
            else: f.write('D %x\n' % v)
    p = subprocess.run(['vvp', exe, '+cmds=' + cf, '+out=' + of, '+maxcyc=%d' % maxcyc], capture_output=True, text=True, check=True)
    errs = [l for l in p.stdout.splitlines() if 'SDRAM MODEL ERROR' in l]
    rx = bytes(_hx(l) for l in open(of).read().split())
    for x in (cf, of):
        try: os.remove(x)
        except OSError: pass
    return rx, errs

INIT = ('D', 0x3000)           # > 5400 clocks of power-up wait

def cfg(cl, dly, inv): return [('B', H.c_K(cl, dly, inv)), ('D', 0x3000)]

def test_seq(mode, lg, count, seed=1, base=0, wait=None):
    wait = wait if wait is not None else 28 * count + 0x2000
    return [('B', H.c_T(mode, lg, base, count, seed)), ('D', wait), ('B', H.c_Q()), ('D', 0x1000)]

def main():
    exe = build()
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-62s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)

    # 1 version, info, single words
    seq = [INIT, ('B', H.c_V()), ('D', 0x400), ('B', H.c_I()), ('D', 0x400)]
    words = {5: 0xCAFEBABE, 6: 0x12345678, 0x1FFFFF: 0xA5A5F00F, 0x080000: 0x01020304, 0x100123: 0xFEEDFACE}   # last words of banks / rows too
    for a, d in words.items(): seq += [('B', H.c_w(a, d)), ('D', 0x500)]
    for a in words:            seq += [('B', H.c_r(a)), ('D', 0x500)]
    rx, errs = run(exe, seq)
    v, i = H.dec_V(rx[0:8]), H.dec_I(rx[8:12])
    check('version reply, init done', v['version'] == 1 and v['init_done'] == 1 and v['words'] == H.WORDS, str(v))
    check('default settings cl 2 dly 1 inv 0', (i['cl'], i['dly'], i['inv']) == (2, 1, 0), str(i))
    got = [H.dec_r(rx[12 + 4 * k: 16 + 4 * k]) for k in range(len(words))]
    check('single words written and read back (all 4 banks, rows)', got == list(words.values()), ' '.join('%08x' % g for g in got))
    check('model reports no timing violations', not errs, errs[:2].__repr__())

    # 2 the on-chip test, every mode
    for mode in range(4):
        rx, errs = run(exe, [INIT] + test_seq(mode, 10, 1024, seed=7 + mode))
        q = H.dec_Q(rx[-25:])
        check('on-chip test mode %d (1024 words)' % mode, q['done'] and q['errors'] == 0 and not errs, 'wclk %d rclk %d' % (q['write_clocks'], q['read_clocks']))
    # a test that covers the top of the address space, in scattered order
    rx, errs = run(exe, [INIT] + test_seq(1, 12, 4096, base=0x1FF000), maxcyc=60_000_000)
    q = H.dec_Q(rx[-25:]); check('scattered test at the top of memory (base 0x1FF000)', q['done'] and q['errors'] == 0 and not errs)

    # 3 refresh: write, idle for well over the 64 ms/4096 refresh interval's worth of clocks, read back.  (model demands a refresh every 20 us)
    seq = [INIT, ('B', H.c_w(0x1234, 0x0BADF00D)), ('D', 0x500), ('D', 0x40000), ('D', 0x40000), ('B', H.c_r(0x1234)), ('D', 0x600)]
    rx, errs = run(exe, seq)
    check('data survives 0.5 million idle clocks (refresh works)', H.dec_r(rx[-4:]) == 0x0BADF00D and not errs)

    # 4 negative controls: the test must CATCH a wrong read-capture delay and a controller/model CAS-latency mismatch
    for (cl, dly, inv, expect_ok) in [(2, 1, 0, True), (2, 0, 0, False), (2, 2, 0, False), (3, 1, 0, True), (3, 2, 0, False), (3, 0, 0, False), (3, 0, 1, True), (2, 0, 1, True)]:
        rx, errs = run(exe, [INIT] + cfg(cl, dly, inv) + test_seq(0, 8, 256))
        q = H.dec_Q(rx[-25:])
        passed = q['done'] and q['errors'] == 0
        check('sweep cl %d dly %d inv %d: %s' % (cl, dly, inv, 'must pass' if expect_ok else 'must FAIL (negative control)'), passed == expect_ok,
              'errors %d first %08x exp %08x got %08x' % (q['errors'], q['first_addr'], q['expected'], q['got']))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
