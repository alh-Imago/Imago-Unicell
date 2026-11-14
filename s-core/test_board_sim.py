"""Whole-board simulation test: the same bytes the PC would send over the UART go into the Verilated sc_top_tang;
the reply bytes are decoded with host_sc.py and every task's a0 is compared with the independent ISS."""
import sys, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import sched_tests as st, host_sc as hs
rt = st.rt
POOL = os.environ.get('POOL') in ('1', '2')   # POOL=1: simulate the v5 pool top (sc_top_pool), POOL=2: the v6 pool top (sc_top_pool6), instead of sc_top_tang
POOL6 = os.environ.get('POOL') == '2'

PROGS = [('sum', st.k_sum(60)), ('fib', st.k_fib(40)), ('crc', st.k_crc(0x1234567, 2)),
         ('gcd', st.k_gcd(1071, 462)), ('mul', st.k_mul(4321, 8765)), ('sort', st.k_sort(8, 99999))]

def build(S=8, QD=16, IMW=256, DMW=64, PROF=64, DIV=8, LONGEST=1, FINE=0, tag='board'):
    d = os.path.join(HERE, 'vl_%s%s_S%d_D%d' % (tag, ('Q' if POOL6 else 'P') if POOL else '', S, DMW))
    f = os.path.join(HERE, 'fpga')
    r = subprocess.run(['verilator', '--binary', '--timing', '-Wno-fatal', '-Wno-lint', '-Wno-WIDTH', '-Wno-UNOPTFLAT', '-Wno-INITIALDLY',
        '-Wno-BLKSEQ', '-Wno-CASEINCOMPLETE', '-Wno-MULTIDRIVEN', '-Wno-BLKANDNBLK', '--top-module', 'tb_top_tang', *(['-DPOOLTOP'] if POOL else []), *(['-DPOOL6TOP'] if POOL6 else []),
        '-GS=%d' % S, '-GQD=%d' % QD, '-GIMW=%d' % IMW, '-GDMW=%d' % DMW, '-GPROF=%d' % PROF, '-GDIV=%d' % DIV, '-GLONGEST=%d' % LONGEST, '-GFINE=%d' % FINE,
        '-O2', '--Mdir', d, '-o', 'simv', f + '/tb_top_tang.v', f + ('/sc_top_pool6.v' if POOL6 else '/sc_top_pool.v' if POOL else '/sc_top_tang.v'), f + '/host_bridge.v', f + '/uart.v',
        os.path.join(HERE, 'sc_sys_v6.v' if POOL6 else 'sc_sys_v5.v' if POOL else 'sc_sys_v4.v'), os.path.join(HERE, 'uc_core_v2s.v' if POOL else 'uc_core_fp.v')], capture_output=True, text=True)
    if r.returncode: print(r.stdout[-1500:], r.stderr[-1500:]); sys.exit(1)
    return os.path.join(d, 'simv')

def fit_progs(imem_words):
    """kernels that fit in the instruction memory, in order (greedy)"""
    out, used = [], 0
    for name, src in PROGS:
        n = len(rt.assemble(src))
        if used + n <= imem_words: out.append(name); used += n
    return out

def script(tids_kinds, lw, crit_set, wait_clocks, imem_words=256, div=8):
    """returns (bytes_to_send_with_waits, reply_order, expected a0 per tid)"""
    seq, bases, words_all, exp = [], {}, [], {}
    for name, src in PROGS:
        if name not in fit_progs(imem_words): continue
        w = rt.assemble(src); bases[name] = len(words_all); words_all += w; exp[name] = rt.iss(w)['x'][10]
    assert len(words_all) <= imem_words, 'programs do not fit the instruction memory'
    rep_wait = lambda n: ('D', n * 10 * div + 4 * div * 10)   # reply bytes x bit-times, plus slack
    seq.append(('B', hs.cmd_V())); order = ['V']; seq.append(rep_wait(8))
    for i, w in enumerate(words_all): seq.append(('B', hs.cmd_W(i, w)))
    for tid, kind in enumerate(tids_kinds):
        seq.append(('B', hs.cmd_P(tid, bases[kind], lw, int(tid in crit_set), [n for n, _ in PROGS].index(kind))))
    seq.append(('D', wait_clocks))
    seq.append(('B', hs.cmd_C())); order.append('C'); seq.append(rep_wait(56))
    for tid in range(len(tids_kinds)): seq.append(('B', hs.cmd_Q(tid))); order.append('Q'); seq.append(rep_wait(22))
    return seq, order, {t: exp[k] for t, k in enumerate(tids_kinds)}

def run(exe, seq, tag='board'):
    cf, of = os.path.join(HERE, tag + '.cmds'), os.path.join(HERE, tag + '.rx')
    with open(cf, 'w') as f:
        for kind, v in seq:
            if kind == 'B':
                for b in v: f.write('B %02x\n' % b)
            else: f.write('D %x\n' % v)
    subprocess.run([exe, '+cmds=' + cf, '+out=' + of], check=True, capture_output=True)
    return bytes(int(l, 16) for l in open(of).read().split())

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--S', type=int, default=1); ap.add_argument('--imw', type=int, default=128)
    ap.add_argument('--dmw', type=int, default=16); ap.add_argument('--lw', type=int, default=0)
    ap.add_argument('--wait', type=int, default=1200000); ap.add_argument('--div', type=int, default=8)
    a = ap.parse_args()
    exe = build(S=a.S, IMW=a.imw, DMW=a.dmw, DIV=a.div, tag='board%d' % a.div)
    kinds = fit_progs(a.imw) * 2
    seq, order, exp = script(kinds, lw=a.lw, crit_set={4, 9}, wait_clocks=a.wait, imem_words=a.imw, div=a.div)
    rx = run(exe, seq, tag='board%d' % a.div)
    rep = hs.split_replies(rx, order)
    ver, cnt, tasks = rep[0], rep[1], rep[2:]
    print('version reply:', ver); print('counters:', cnt)
    bad = 0
    for tid, t in enumerate(tasks):
        ok = (t['state'] == 3 and not t['trap'] and t['a0'] == exp[tid])
        bad += not ok
        print('task %2d %-4s state %d slot %d start %6d end %6d clocks %6d a0 %08x expect %08x pred_known %d  %s' %
              (tid, kinds[tid], t['state'], t['slot'], t['start'], t['end'], t['end'] - t['start'], t['a0'], exp[tid], t['pred_known'], 'ok' if ok else 'FAIL'))
    print('done', cnt['done'], 'launch_err', cnt['launch_err'], 'RESULT', 'PASS' if (not bad and cnt['done'] == len(kinds) and cnt['launch_err'] == 0) else 'FAIL')
