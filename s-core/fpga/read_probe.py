#!/usr/bin/env python3
"""read_probe.py - read and explain the report of bram_probe_top.

Usage:   python3 read_probe.py [serial-port]        (default /dev/ttyUSB1, 115200 baud)
         python3 read_probe.py --line 'P0000...'    (decode a line you already have)
"""
import sys

NAMES = ['V0 as in sc_sys_v5 (inputs straight from the core)', 'V1 same, inputs re-registered on the FALLING clock edge', 'V2 no-change mode, inputs re-registered on the falling edge']

def fields(h):
    pos = [0]
    def take(n):
        v = int(h[pos[0]:pos[0] + n], 16); pos[0] += n; return v
    r = dict(cntA=take(4), cntB=take(4), fstep=take(8), fra=take(3), frb=take(3), fbits=take(1),
             orA=take(3), andA=take(3), orB=take(3), andB=take(3), flags=take(1))
    return r

def addr(a): return 'x%d bit %d' % (a >> 5, a & 31)

def explain(name, r, steps, is_dm=False):
    print('  %s' % name)
    if r['cntA'] == 0 and r['cntB'] == 0:
        print('     OK: no wrong read in %d core steps' % steps); return True
    print('     WRONG READS: port A %d, port B %d (out of %d core steps)' % (r['cntA'], r['cntB'], steps))
    if is_dm:
        print('     first wrong read at step %d, data bit address %d (word %d bit %d)' % (r['fstep'], r['fra'], r['fra'] >> 5, r['fra'] & 31))
        return False
    eA, aA, eB, aB = (r['fbits'] >> 3) & 1, (r['fbits'] >> 2) & 1, (r['fbits'] >> 1) & 1, r['fbits'] & 1
    print('     first one at step %d:  port A %s  port B %s' % (r['fstep'], addr(r['fra']), addr(r['frb'])))
    print('       expected/actual bit: A %d/%d   B %d/%d' % (eA, aA, eB, aB))
    for tag, o, a, c in (('A', r['orA'], r['andA'], r['cntA']), ('B', r['orB'], r['andB'], r['cntB'])):
        if c == 0: continue
        const1 = [i for i in range(10) if (a >> i) & 1]       # address bits that were 1 in EVERY failing address
        const0 = [i for i in range(10) if not (o >> i) & 1]   # address bits that were 0 in EVERY failing address
        print('       port %s failing addresses: bits always 1 = %s, always 0 = %s  (address bit 9..5 = register, 4..0 = bit)' % (tag, const1 or 'none', const0 or 'none'))
    f = r['flags']
    if f & 0b1010: print('       the first wrong read was of the address written in the LAST step (read straight after write)' if f & 0b1000 or f & 0b0010 else '')
    if f & 0b0101: print('       ... or of the address written one step before that')
    return False

def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--line': line = sys.argv[2]
    else:
        import serial
        port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB1'
        s = serial.Serial(port, 115200, timeout=2)
        s.reset_input_buffer()
        line = ''; seen = []
        import time; t_end = time.time() + 20
        while time.time() < t_end:
            raw = s.readline()
            t = raw.decode('ascii', 'ignore').strip()
            seen.append(raw)
            if len(seen) > 40: seen.pop(0)
            if t.startswith('P') and len(t) == 153:
                sys.exit('This is the OLD probe (first version, report starts with P, 153 characters): the board is still running the old bitstream.\n'
                         'Unplug the Tang USB lead for 5 seconds, plug it back, then:  openFPGALoader -b tangnano20k build_probe/bram_probe_top.fs  and run this again.')
            if t.startswith('Q') and len(t) == 189: line = t; break
        if not line:
            print('no complete report line received. What arrived (last lines of %d reads; factory-demo text such as Memtest means our design is not running):' % len(seen))
            for r in seen[-6:]: print('  %3d bytes: %r' % (len(r), r[:90]))
            sys.exit('(a good report is 189 characters starting with Q; empty reads mean nothing is being sent)')
    h = line.strip()[1:]
    assert len(h) == 188, 'expected 188 hex digits, got %d' % len(h)
    steps = int(h[:8], 16); recs = [fields(h[8 + 36 * i: 8 + 36 * (i + 1)]) for i in range(5)]
    print('core steps so far: %d   (about %.1f instructions)' % (steps, steps / 66.0))
    print('Register file in block RAM, three codings, compared with the LUT-RAM copy the core actually uses:')
    ok = [explain(NAMES[i], recs[i], steps) for i in range(3)]
    print('Data memory in block RAM:')
    okd = explain('D  as in sc_sys_v5', recs[3], steps, is_dm=True)
    okn = explain('N  inputs re-registered on the falling edge', recs[4], steps, is_dm=True)
    print()
    if all(ok) and okd and okn: print('VERDICT: all codings read correctly here -> the fault is NOT the block-RAM mechanics; look at the full system around it.')
    elif not any(ok): print('VERDICT: every register-file coding fails -> see the failing-address pattern above.')
    else:
        print('VERDICT: these register-file variants read correctly: ' + (', '.join(NAMES[i].split()[0] for i in range(3) if ok[i]) or 'none'))
        if not ok[0] and (ok[1] or ok[2]): print('         -> the failure is a hold-time race at the block-RAM inputs; falling-edge input registers fix it.')

main()
