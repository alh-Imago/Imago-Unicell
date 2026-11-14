#!/usr/bin/env python3
"""read_char.py - read and explain the report of bram_char_top (block-RAM characterisation).

Usage:   python3 read_char.py [serial-port]       (default /dev/ttyUSB1, 115200 baud)
         python3 read_char.py --line 'C0000...'   (decode a line you already have)
"""
import sys, time

UNITS = [  # (name, width, address bits, shared-address single port?)
    ('u0  1 bit x 1024, single port, one address shared by read and write (the register file as built)', 1, 10),
    ('u1  4 bit x 256,  single port, shared address', 4, 8),
    ('u2  9 bit x 256,  single port, shared address', 9, 8),
    ('u3 18 bit x 256,  single port, shared address', 18, 8),
    ('u4 32 bit x 32,   single port, shared address (a word-wide register file)', 32, 5),
    ('u5 16 bit x 256,  single port, shared address', 16, 8),
    ('u6 18 bit x 512,  single port, shared address (a full block)', 18, 9),
]

def rec(h):
    p = [0]
    def t(n):
        v = int(h[p[0]:p[0] + n], 16); p[0] += n; return v
    return dict(nz=t(4), errSeq=t(4), m0=t(4), m1=t(4), m2=t(4), errR=t(4), faddr=t(4), fexp=t(8), fact=t(8))

def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--line': line = sys.argv[2]
    else:
        import serial
        port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB1'
        s = serial.Serial(port, 115200, timeout=2); s.reset_input_buffer()
        line = ''; seen = []; t_end = time.time() + 20
        while time.time() < t_end:
            raw = s.readline(); t = raw.decode('ascii', 'ignore').strip(); seen.append(raw)
            if len(seen) > 40: seen.pop(0)
            if t.startswith('C') and len(t) == 317: line = t; break
            if t.startswith('Q') or (t.startswith('P') and len(t) == 153):
                sys.exit('The board is running the earlier bram_probe design, not bram_char_top. Load build_char/bram_char_top.fs.')
        if not line:
            print('no complete report line received. Last lines (factory-demo text means our design is not running):')
            for r in seen[-6:]: print('  %3d bytes: %r' % (len(r), r[:90]))
            sys.exit(1)
    h = line.strip()[1:]
    assert len(h) == 316, 'expected 316 hex digits, got %d' % len(h)
    tick = int(h[:8], 16); print('clocks since start: %d  (%.1f s)' % (tick, tick / 27e6))
    allok = True
    for i, (name, W, AB) in enumerate(UNITS):
        r = rec(h[8 + 44 * i: 8 + 44 * (i + 1)]); N = 1 << AB
        ok = r['nz'] == 0 and r['errSeq'] == 0 and r['errR'] == 0 and r['m1'] == N
        allok &= ok
        print('\n%s: %s' % (name, 'PASS' if ok else 'FAIL'))
        print('   at power-up, words not zero: %d of %d     plain write-all / read-all: %d wrong of %d' % (r['nz'], N, r['errSeq'], N))
        lat = 'read data arrives 1 clock after the address (normal synchronous read)' if r['m1'] == N else \
              ('read data looks ASYNCHRONOUS (follows the current address)' if r['m0'] > 0.9 * N and W > 1 else
               ('read data looks 2 clocks late' if r['m2'] > 0.9 * N and W > 1 else 'read latency unclear'))
        print('   latency check (matches at 1 clock / this clock / 2 clocks): %d / %d / %d of %d  -> %s' % (r['m1'], r['m0'], r['m2'], N, lat))
        if r['errR'] == 0: print('   random core-style accesses vs LUT-RAM copy: no differences')
        else: print('   random core-style accesses: %d DIFFERENCES; first at read address %d: expected %x, got %x' % (r['errR'], r['faddr'], r['fexp'], r['fact']))
    print()
    print('ALL PASS' if allok else 'Some shapes fail; compare which ones pass.')

main()
