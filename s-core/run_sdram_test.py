#!/usr/bin/env python3
"""Run the SDRAM test on the Tang Nano 20K (bitstream fpga/sdt/sc_top_sdt.fs, built by fpga/build_sdt.sh).
  python3 run_sdram_test.py --port /dev/ttyUSB1
Steps: check the build, sweep the read-capture settings (CAS latency 2/3, clock inversion, capture delay 0..3) with a quick test of each,
then run the full 8 MB test with the settings that passed and report the speed.  Exit code 0 only if the full test had no errors."""
import argparse, sys, time
import sdt_host as H

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', required=True, help='serial port of the board (the second BL616 port: /dev/ttyUSB1 on Linux)')
    ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--quick', type=int, default=4096, help='words per sweep test (power of two)')
    ap.add_argument('--keep', default='', help='use this setting without sweeping, as cl,dly,inv (e.g. 2,1,0)')
    a = ap.parse_args()
    b = H.SdtBoard(a.port, a.baud)
    try: v = b.version()
    except (ValueError, IOError) as e:
        print('Cannot talk to the SDRAM test build: %s' % e); return 2
    print('SDRAM test build version %d, %d words (%d MB), init_done=%d' % (v['version'], v['words'], v['words'] * 4 >> 20, v['init_done']))
    lgq = a.quick.bit_length() - 1
    passed = []
    if a.keep:
        cl, dly, inv = [int(x) for x in a.keep.split(',')]; passed = [(cl, dly, inv)]
    else:
        print('\nsweep: %d words, scattered order, hashed data, at the start of memory' % a.quick)
        print(' cl dly inv   result')
        for cl in (2, 3):
            for inv in (0, 1):
                for dly in range(4):
                    if not b.config(cl, dly, inv): print(' %d  %d   %d    controller did not finish power-up' % (cl, dly, inv)); continue
                    q = b.test(1, lgq, 0, a.quick, 0x1234)
                    ok = q['errors'] == 0
                    print(' %d  %d   %d    %s' % (cl, dly, inv, 'PASS' if ok else 'fail (%d wrong, first at %06x: wanted %08x got %08x)' % (q['errors'], q['first_addr'], q['expected'], q['got'])))
                    if ok: passed.append((cl, dly, inv))
    if not passed:
        print('\nNo setting passed. The in-package SDRAM did not answer in any of the tried ways: nothing is wrong with the board by this alone,'); print('send me this output.'); return 1
    # prefer a setting in the middle of a passing run (most margin): for each (cl, inv) the passing delays; pick the median one of the first group
    cl, dly, inv = passed[len(passed) // 2]
    print('\n%d setting(s) passed.  Using cl %d dly %d inv %d for the full test.' % (len(passed), cl, dly, inv))
    b.config(cl, dly, inv)
    bad = 0
    for name, mode, seed in (('in order, hashed data', 0, 0xC0FFEE), ('scattered order (bank/row hopping), hashed data', 1, 0xBEEF), ('in order, address-pattern data', 2, 0), ('scattered, address-pattern data', 3, 0)):
        t0 = time.time(); q = b.test(mode, 21, 0, H.WORDS, seed, timeout=120); dt = time.time() - t0
        sp = H.speed(q, H.WORDS)
        print('full 8 MB, %-46s %s  write %.1f MB/s (%.1f clk/word)  read %.1f MB/s (%.1f clk/word)  [%.1f s]' % (name, 'PASS' if q['errors'] == 0 else 'FAIL %d wrong, first at %06x wanted %08x got %08x' % (q['errors'], q['first_addr'], q['expected'], q['got']),
              sp['write_MBps'], sp['write_clk_per_word'], sp['read_MBps'], sp['read_clk_per_word'], dt))
        bad += q['errors'] != 0
    print('\nRESULT:', 'PASS - all 8 MB written and read back correctly, 4 ways' if not bad else 'FAIL')
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
