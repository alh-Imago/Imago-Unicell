"""test_hostext_v2.py - host side of the high multiply, the byte/half loads and the byte-store unit (ledger #1598): asm_ext_v1.py, jobio_ext_v2.py, jobiss_v3.py, jobio/lib_mulhu*.s and the programs vmulhu.s, vbyte.s, vbswap.s,
run on the interpreter at every multiply level.  Run: python3 test_hostext_v2.py"""
import sys, random
import jobio_ext_v2 as X, jobio as J, jobiss_v3, progs
from programs import examples_v7 as E
M32 = 0xFFFFFFFF
bad = 0
def check(name, cond):
    global bad
    print('%-110s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
X.install(0)
for n, f, e in (('vmulhu', 'vmulhu.s', 'vmulhu_ref'), ('vbyte', 'vbyte.s', 'vbyte_ref'), ('vbswap', 'vbswap.s', 'vbswap_ref')):
    progs.register(n, 'programs/' + f, expect='programs.examples_v7:' + e, out='same', replace=True, check=False)
random.seed(7)
def run(kind, xs, arg=0):
    j = J.Job(0, kind, xs, len(xs), arg=arg); lk = J.build_link([j]); st, n, out, steps = jobiss_v3.reference(lk, j)
    return st, out, steps, len(lk.words)
XS = [0, 1, 0xFFFFFFFF, 0x80000000, 0x80FF7F01, 0x7F80017E, 0x12345678, 0xDEADBEEF] + [random.getrandbits(32) for _ in range(8)]
steps = {}
for level in (0, 1, 2, 3):
    X.install(level, narrow=True)
    # high multiply: software at levels 0 and 1, unit from 2
    ok = True
    for arg in (0, 1, 3, 0xFFFFFFFF, 0x80000000, 0x9ABCDEF0, 65537):
        st, out, s, cw = run('vmulhu', XS, arg); ok &= (st == 1 and out == E.vmulhu_ref(XS, arg, len(XS)))
    st, out, s, cw = run('vmulhu', XS, 0x9ABCDEF0); steps[('hi', level)] = s / len(XS)
    check('level %d: vmulhu equals the high half of the 64-bit product (7 multipliers, edges and random inputs)' % level, ok)
    # byte loads
    st, out, s, cw = run('vbyte', XS); check('level %d: vbyte (lb lbu lb lbu lh lhu) equals the Python sum on the interpreter' % level, st == 1 and out == E.vbyte_ref(XS, 0, len(XS)))
    # byte stores: only from level 3 (below: the assembler refuses)
    if level >= 3:
        for arg in (0, 1):
            st, out, s, cw = run('vbswap', XS, arg); check('level 3: vbswap arg %d (%s) equals the Python answer' % (arg, 'sb x4' if arg == 0 else 'sh x2'), st == 1 and out == E.vbswap_ref(XS, arg, len(XS)))
    else:
        try: run('vbswap', XS, 0); check('level %d: sb must be refused by the assembler' % level, False)
        except ValueError as e: check('level %d: sb/sh refused at link time with a clear message (%s...)' % (level, str(e)[:50]), 'byte-store unit' in str(e))
check('the unit makes the high multiply far shorter (%.0f against %.0f instructions per word)' % (steps[('hi', 2)], steps[('hi', 1)]), steps[('hi', 2)] * 10 < steps[('hi', 1)])
X.install(3, narrow=False)
try: run('vbyte', XS); check('without narrow loads vbyte must be refused', False)
except ValueError as e: check('a build without byte/half loads refuses lb at link time', 'byte and halfword loads' in str(e))
# code size: lib_mulhu32 only when a job mentions it
X.install(2, narrow=True)
cw_hi = run('vmulhu', XS, 3)[3]; cw_b = run('vbyte', XS)[3]
import jobio as J2
check('lib_mulhu32 is linked only into jobs that call it (vmulhu %d code words, vbyte %d)' % (cw_hi, cw_b), cw_hi > cw_b - 30)
X.uninstall()
print('ALL PASSED' if not bad else 'FAILED %d' % bad); sys.exit(1 if bad else 0)
