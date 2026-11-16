"""Harness for test_k7_sim.py: builds fpga/tb_k7.v with the Kintex top and runs a script of bytes through the simulated JTAG link.
A reply count in send() becomes a 'W n' line: the testbench keeps scanning the user register until n reply bytes have come back."""
import os, sys, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
FPGA = os.path.join(HERE, 'fpga')
def build(tag='k7'):
    if not shutil.which('iverilog'): print('SKIP: iverilog not installed'); sys.exit(1)
    exe = os.path.join(HERE, tag + '.vvp')
    files = ['tb_k7.v', 'sc_top_k7_v1.v', 'jtag_link_v1.v', 'host_bridge_v10.v', 'farram_bram_v1.v', 'batch_seq_v2.v', 'far_copy.v']
    srcs = [os.path.join(FPGA, f) for f in files] + [os.path.join(HERE, 'sc_sys_v12.v'), os.path.join(HERE, 'uc_core_v2v.v')]
    subprocess.run(['iverilog', '-g2012', '-o', exe] + srcs, check=True)
    return exe
class Script:
    def __init__(s): s.seq, s.reps = [], []
    def send(s, b, reply=0, kind=None, extra=0):
        s.seq.append(('B', b))
        if reply: s.reps.append((kind, reply)); s.seq.append(('W', reply))
        elif extra: s.seq.append(('D', max(extra // 8, 1)))
    def wait(s, n): s.seq.append(('D', n))
def _hx(t):
    try: return int(t, 16)
    except ValueError: return 0xEE
def run(exe, sc, tag='k7', maxcyc=60_000_000):
    cf, of = os.path.join(HERE, tag + '.cmds'), os.path.join(HERE, tag + '.rx')
    with open(cf, 'w') as f:
        for kind, v in sc.seq:
            if kind == 'B':
                for b in v: f.write('B %02x\n' % b)
            else: f.write('%s %x\n' % (kind, v))
    p = subprocess.run(['vvp', exe, '+cmds=' + cf, '+out=' + of, '+maxcyc=%d' % maxcyc], capture_output=True, text=True, check=True)
    bad = [l for l in p.stdout.splitlines() if 'TIMEOUT' in l or 'BAD' in l or 'maxcyc' in l]
    rx = bytes(_hx(l) for l in open(of).read().split())
    for x in (cf, of):
        try: os.remove(x)
        except OSError: pass
    return rx, bad
