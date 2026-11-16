"""Far RAM in the whole-board simulation (fpga/sc_top_pool13.v: cores + the onboard SDRAM through a copy engine) against the checking SDRAM model.
Needs iverilog.  Checks: shared RAM -> far RAM -> shared RAM round trip; protections (default window blocks everything; far range outside the window;
near range past the end) refuse the copy, move nothing and leave the far word untouched; far RAM contents and window survive a core reset (R);
a program stored in far RAM is block-copied into the code store and RUNS (result equals the independent ISS); a copy running while a core
executes a job does not disturb the job's result; the model sees no timing violation."""
import os, sys, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import sched_tests as st, host_sc as hs, sdt_host as H
rt = st.rt
DIV = 8
FPGA = os.path.join(HERE, 'fpga')

def build(tag='far', seq=False):
    if not shutil.which('iverilog'): print('SKIP: iverilog not installed'); sys.exit(1)
    exe = os.path.join(HERE, tag + '.vvp')
    files = ('tb_top_seq.v', 'sc_top_pool14.v', 'host_bridge_v8.v', 'batch_seq.v', 'far_copy.v', 'sdram_ctl.v', 'sdram_model.v', 'uart.v') if seq else ('tb_top_far.v', 'sc_top_pool13.v', 'host_bridge_v7.v', 'far_copy.v', 'sdram_ctl.v', 'sdram_model.v', 'uart.v')
    srcs = [os.path.join(FPGA, f) for f in files] + [os.path.join(HERE, 'sc_sys_v12.v'), os.path.join(HERE, 'uc_core_v2v.v')]
    subprocess.run(['iverilog', '-g2012', '-o', exe] + srcs, check=True)
    return exe

class Script:
    def __init__(s): s.seq, s.reps = [], []
    def send(s, b, reply=0, kind=None, extra=0):
        s.seq.append(('B', b))
        if reply: s.reps.append((kind, reply)); s.seq.append(('D', reply * 10 * DIV + 4 * DIV * 10 + extra))
        elif extra: s.seq.append(('D', extra))
    def wait(s, n): s.seq.append(('D', n))
def _hx(t):
    try: return int(t, 16)
    except ValueError: return 0xEE        # x/z bits in simulation

def run(exe, sc, tag='far', maxcyc=60_000_000):
    cf, of = os.path.join(HERE, tag + '.cmds'), os.path.join(HERE, tag + '.rx')
    with open(cf, 'w') as f:
        for kind, v in sc.seq:
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

def main():
    exe = build(); bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-70s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    pat = [(0xA5000000 + 0x01030507 * i) & 0xFFFFFFFF for i in range(16)]
    prog = rt.assemble(st.k_sum(60)); want = rt.iss(prog)['x'][10]
    far_prog = 0x180; far_pat = 0x110; far_task = 0x1C0
    s = Script(); s.wait(0x3000)
    s.send(hs.cmd_V(), 8, 'V'); s.send(H.c_I(), 4, 'I')
    s.send(H.c_F(0, 0, far_pat, 4), 0, extra=0x400); s.send(H.c_N(), 12, 'N')                    # 0: default window (length 0) blocks every copy
    s.send(H.c_D(0x100, 0x100))
    for i, w in enumerate(pat): s.send(hs.cmd_M(i, w), extra=0x100)
    s.send(H.c_F(0, 0, far_pat, 16), 0, extra=0x1000); s.send(H.c_N(), 12, 'N')                    # 1: shared -> far
    for i in range(16): s.send(hs.cmd_M(i, 0), extra=0x100)                                         # wipe the shared RAM
    s.send(H.c_F(1, 0x20, far_pat, 16), 0, extra=0x1000); s.send(H.c_N(), 12, 'N')                 # 2: far -> shared, to a different place
    for i in range(16): s.send(hs.cmd_L(0x20 + i), 4, 'L')
    s.send(hs.cmd_L(3), 4, 'L')                                                                       # untouched (wiped) word
    s.send(H.c_N(), 12, 'N')
    s.send(H.c_w(0xFF, 0x11111111), extra=0x200); s.send(H.c_w(0x1FF, 0x22222222), extra=0x200)    # sentinels just outside / at the edge of the window
    s.send(H.c_F(0, 0, 0xFF, 2), 0, extra=0x400); s.send(H.c_N(), 12, 'N')                         # 3: starts below the window
    s.send(H.c_F(0, 0, 0x1FF, 2), 0, extra=0x400); s.send(H.c_N(), 12, 'N')                        # 4: crosses the end of the window
    s.send(H.c_F(1, 0xFF, far_pat, 2), 0, extra=0x400); s.send(H.c_N(), 12, 'N')                   # 5: near range past the shared RAM
    s.send(H.c_F(2, 0x7F, far_pat, 2), 0, extra=0x400); s.send(H.c_N(), 12, 'N')                   # 6: near range past the code store
    s.send(H.c_r(0xFF), 4, 'r'); s.send(H.c_r(0x1FF), 4, 'r'); s.send(H.c_r(0x200), 4, 'r')
    s.send(b'R', 0, extra=0x400)                                                                       # a core reset must not touch the far RAM or its window
    s.send(H.c_r(far_pat + 5), 4, 'r'); s.send(H.c_F(0, 0, far_pat, 1), 0, extra=0x400); s.send(H.c_N(), 12, 'N')   # 7: window survived R
    # program in far RAM -> code store -> runs
    for i, w in enumerate(prog): s.send(H.c_w(far_prog + i, w), extra=0x100)
    s.send(H.c_F(2, 0, far_prog, len(prog)), 0, extra=0x1000 + 40 * len(prog)); s.send(H.c_N(), 12, 'N')   # 8
    s.send(hs.cmd_P(0, 0, 0, 0, 0)); s.wait(250000)
    s.send(hs.cmd_Q(0), 22, 'Q')
    # a copy while a core runs a job: the job's result must be right and the copy complete
    s.send(hs.cmd_P(1, 0, 0, 0, 0)); s.wait(300)
    s.send(H.c_F(0, 0x10, far_task, 32), 0, extra=0x1800); s.send(H.c_N(), 12, 'N')                   # 9
    s.wait(250000); s.send(hs.cmd_Q(1), 22, 'Q')
    s.send(H.c_F(1, 0x40, far_task + 16, 16), 0, extra=0x1000); s.send(H.c_N(), 12, 'N')                # 10: read the same words back
    for i in range(16): s.send(hs.cmd_L(0x40 + i), 4, 'L')
    s.wait(2000)
    rx, errs = run(exe, s)
    pos = 0; got = []
    for kind, n in s.reps:
        got.append((kind, rx[pos:pos + n])); pos += n
    if pos != len(rx): print('reply bytes: used %d of %d' % (pos, len(rx)))
    it = iter(got)
    def nxt(k):
        kk, b = next(it); assert kk == k, (kk, k); return b
    v = hs.dec_V(nxt('V')); i_ = H.dec_I(nxt('I'))
    check('board version 10, far RAM up, default settings 2/1/0', v['version'] == 10 and i_['init_done'] == 1 and (i_['cl'], i_['dly'], i_['inv']) == (2, 1, 0), str(i_))
    n0 = H.dec_N(nxt('N')); check('copy with the default (empty) window is refused: err 1, nothing moved', n0['err'] == 1 and n0['moved'] == 0 and n0['done'] and not n0['busy'], str(n0))
    n1 = H.dec_N(nxt('N')); check('shared -> far: 16 words moved, no error', n1['err'] == 0 and n1['moved'] == 16 and n1['done'], 'clocks %d (%.1f per word)' % (n1['clocks'], n1['clocks'] / 16))
    n2 = H.dec_N(nxt('N')); check('far -> shared: 16 words moved, no error', n2['err'] == 0 and n2['moved'] == 16 and n2['done'], 'clocks %d (%.1f per word)' % (n2['clocks'], n2['clocks'] / 16))
    back = [int.from_bytes(nxt('L'), 'little') for _ in range(16)]
    check('round trip: the 16 words come back exactly (shared -> far -> shared)', back == pat, ' '.join('%08x' % x for x in back[:4]) + ' ...')
    check('a shared word that was not copied stays wiped', int.from_bytes(nxt('L'), 'little') == 0)
    nn = H.dec_N(nxt('N')); check('status still reports the last copy', nn['moved'] == 16 and nn['err'] == 0)
    for name, want_err in (('far range starts below the window', 1), ('far range crosses the end of the window', 1), ('near range past the end of the shared RAM', 2), ('near range past the end of the code store', 2)):
        n = H.dec_N(nxt('N')); check('refused: ' + name, n['err'] == want_err and n['moved'] == 0 and n['done'] and not n['busy'], str(n))
    r1, r2, r3 = [H.dec_r(nxt('r')) for _ in range(3)]
    check('refused copies wrote nothing (sentinels just outside the window intact)', (r1, r2, r3) == (0x11111111, 0x22222222, r3) and r3 != 0x11111111, '%08x %08x %08x' % (r1, r2, r3))
    r = H.dec_r(nxt('r')); n7 = H.dec_N(nxt('N'))
    check('far RAM contents and the window survive a core reset (R)', r == pat[5] and n7['err'] == 0 and n7['moved'] == 1, '%08x' % r)
    n8 = H.dec_N(nxt('N')); check('program image far -> code store: %d words' % len(prog), n8['err'] == 0 and n8['moved'] == len(prog), str(n8))
    q0 = hs.dec_Q(nxt('Q'))
    check('the program loaded from far RAM runs and gives the right result', q0['state'] == 3 and not q0['trap'] and q0['a0'] == want, 'a0 %d expect %d' % (q0['a0'], want))
    n9 = H.dec_N(nxt('N')); q1 = hs.dec_Q(nxt('Q'))
    check('a copy during a running job completes', n9['err'] == 0 and n9['moved'] == 32, '%d clocks' % n9['clocks'])
    check('... and the job result is still right', q1['state'] == 3 and not q1['trap'] and q1['a0'] == want, 'a0 %d' % q1['a0'])
    n10 = H.dec_N(nxt('N')); last = [int.from_bytes(nxt('L'), 'little') for _ in range(16)]
    check('words copied while the job ran read back exactly (shared 0x20..0x2F via far and back)', n10['err'] == 0 and last == pat, ' '.join('%08x' % x for x in last[:4]))
    d0, d1 = q0['end'] - q0['start'], q1['end'] - q1['start']
    check('the copy did not slow the job: same clocks with and without a copy running', d0 == d1, 'idle board %d, with a copy running %d clocks' % (d0, d1))
    check('SDRAM model reports no timing violations over the whole run', not errs, repr(errs[:2]))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
