"""Exercises run_farram_board.py against a stand-in model of the board (NOT the hardware): catches mistakes in the runner's own logic before it is used on the card."""
import sys, struct, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import run_farram_board as R, sched_tests as st
rt = st.rt
class Fake:
    def __init__(s): s.far, s.sh, s.code, s.win, s.err, s.moved, s.buf, s.tasks, s.polls = {}, {}, {}, (0, 0), 0, 0, b'', {}, {}; s.s = s
    def write(s, c): s.h(c)
    def flush(s): pass
    def _rd(s, n): r, s.buf = s.buf[:n], s.buf[n:]; return r
    def version(s): return dict(version=10, S=5, imem_words=128, dmem_words=16)
    def task(s, t):
        s.polls[t] = s.polls.get(t, 0) + 1
        return dict(state=2 if s.polls[t] == 1 else 3, trap=0, a0=s.tasks[t], start=10, end=800400 + (t == 2))   # a job is "running" on its first look
    def h(s, c):
        k = chr(c[0])
        if k == 'I': s.buf += bytes([1, 2, 1, 0])
        elif k == 'D': s.win = (int.from_bytes(c[1:4], 'little'), int.from_bytes(c[4:7], 'little'))
        elif k == 'M': s.sh[struct.unpack('<H', c[1:3])[0]] = struct.unpack('<I', c[3:7])[0]
        elif k == 'L': s.buf += struct.pack('<I', s.sh.get(struct.unpack('<H', c[1:3])[0], 0))
        elif k == 'w': s.far[int.from_bytes(c[1:4], 'little')] = struct.unpack('<I', c[4:8])[0]
        elif k == 'r': s.buf += struct.pack('<I', s.far.get(int.from_bytes(c[1:4], 'little'), 0xDEADBEEF))
        elif k == 'F':
            d, near, far, cnt = c[1], struct.unpack('<H', c[2:4])[0], int.from_bytes(c[4:7], 'little'), struct.unpack('<H', c[7:9])[0]; lo, ln = s.win; s.moved = 0
            if not (ln and far >= lo and far + cnt <= lo + ln): s.err = 1
            elif near + cnt > (128 if d == 2 else 256): s.err = 2
            else:
                s.err = 0
                for i in range(cnt):
                    if d == 0: s.far[far + i] = s.sh.get(near + i, 0)
                    elif d == 1: s.sh[near + i] = s.far.get(far + i, 0)
                    else: s.code[near + i] = s.far.get(far + i, 0)
                s.moved = cnt
        elif k == 'N': s.buf += struct.pack('<BBBBII', 2, s.err, 1, 0, s.moved, 100)
        elif k == 'P':
            w = [s.code.get(i, 0) for i in range(7)]
            s.tasks[struct.unpack('<H', c[1:3])[0]] = rt.iss(w)['x'][10] if w == rt.assemble(st.k_sum(R.LOOP)) else 0

# ---- stand-in that also obeys the job I/O protocol, for run_jobio_board.py (computes each job's answer in Python from the header in the shared RAM) ----
class JobFake(Fake):
    def __init__(s): super().__init__(); s.cwin = {}; s.kind = {0: 'vsum', 1: 'vscale', 2: 'vstress', 3: 'vscale', 4: 'vsum'}
    def task(s, t):
        s.polls[t] = s.polls.get(t, 0) + 1
        return dict(state=2 if s.polls[t] == 1 and t >= 4 else 3, trap=0, a0=0, start=10, end=1010)
    def h(s, c):
        k = chr(c[0])
        if k == 'X': s.cwin[c[1]] = (struct.unpack('<H', c[2:4])[0], struct.unpack('<H', c[4:6])[0])
        elif k == 'P':
            cid = c[7]; base, n = s.cwin[cid]; g = lambda o: s.sh.get(base + o, 0)
            in_off, in_len, out_off, out_len, arg = g(0), g(1), g(2), g(3), g(6); ins = [g(in_off + i) for i in range(in_len)]; M = 0xFFFFFFFF
            kind = s.kind[cid]
            out = [sum(ins) & M] if kind == 'vsum' else [(2 * x + 1) & M for x in ins] if kind == 'vscale' else [(arg * sum(ins)) & M]
            if out_len < len(out): s.sh[base + 4] = 2; s.sh[base + 5] = 0
            else:
                for i, w in enumerate(out): s.sh[base + out_off + i] = w
                s.sh[base + 4] = 1; s.sh[base + 5] = len(out)
        else: super().h(c)

def jobio_main():
    import run_jobio_board as RJ
    return RJ.main('x', io=JobFake())

# ---- stand-in for run_batch_board.py: knows which program is in the code store (compares with the two demo links) and which class kinds each phase has ----
class BatchFake(JobFake):
    def __init__(s):
        import batch_demo as D
        super().__init__(); s.d = D.build(); s.nsub = 0
    def counters(s): return dict(done=s.nsub)
    def task(s, t): return dict(state=3, trap=0, a0=0, start=10, end=1010)
    def h(s, c):
        if chr(c[0]) == 'P':
            for ph, lk in enumerate(s.d['links']):
                if [s.code.get(i, 0) for i in range(len(lk.words))] == list(lk.words): s.kind = {j.cid: j.kind for j in s.d['jobs'][2 * ph:2 * ph + 2]}; break
            else: s.kind = {}
            s.nsub += 1
        super().h(c)

class SeqBatchFake(BatchFake):
    def __init__(s, ver=11): super().__init__(); s.sa = (0, 0, 0, 0); s.ver = ver
    def version(s): return dict(version=s.ver, S=4, imem_words=128, dmem_words=16)
    def h(s, c):
        k = chr(c[0])
        if k == 'J':
            import batch as B
            s.sa = (1,) + B.LiveExec(s).run(int.from_bytes(c[1:4], 'little'))
        elif k == 'A':
            s.buf += bytes([2, s.sa[1], s.sa[3] & 255, s.sa[3] >> 8]) + (s.sa[2] or 0).to_bytes(4, 'little')
            if s.ver >= 12: s.buf += (200000).to_bytes(4, 'little') + (30000).to_bytes(4, 'little') + (120000).to_bytes(4, 'little') + (0x2400).to_bytes(3, 'little') + bytes([0])
        else: super().h(c)

def seq_main():
    import run_seq_board as RS
    return RS.main('x', io=SeqBatchFake(), timeout_case=False) | RS.main('x', io=SeqBatchFake(12), timeout_case=False)

def batch_main():
    import run_batch_board as RB
    return RB.main('x', io=BatchFake())

# ---- stand-in for scbatch.py: the sequencer is emulated by the host executor running inside the fake; kinds per class come from the compiled plan ----
class SeqFake(JobFake):
    def __init__(s, tasks, ver=11):
        import jobcomp as C
        super().__init__(); s.plan = C.compile(tasks, imem=128, dsh=256, wait_k=0xFFFF); s.ver = ver; s.nsub = 0; s.sa = (0, 0, 0, 0); s.bad_code = False; s.regs = {}
    def version(s): return dict(version=s.ver, S=5, imem_words=128, dmem_words=16)
    def counters(s): return dict(done=s.nsub)
    def task(s, t): return dict(state=3, trap=0, a0=0, start=10, end=1010)
    def h(s, c):
        k = chr(c[0])
        if k == 'P':
            entry = struct.unpack('<H', c[3:5])[0]; s.kind = {}
            for lk, kinds in zip(s.plan.links, s.plan.class_kinds):
                kc = lk.classes.get(c[7])
                if kc and s.regs.get(c[7]) == (kc['cbase'], kc['clen']) and [s.code.get(i, 0) for i in range(len(lk.words))] == list(lk.words):
                    s.kind = {c[7]: next(kinds[cid] for cid, k in lk.classes.items() if k['entry'] == entry and cid in kinds)}; break
            else: s.bad_code = True
            s.nsub += 1
        elif k == 'B': s.regs[c[1]] = struct.unpack('<HH', c[2:6])
        elif k == 'J':
            import batch as B
            s.sa = (1,) + B.LiveExec(s).run(int.from_bytes(c[1:4], 'little'))
        elif k == 'A':
            s.buf += bytes([2, s.sa[1], s.sa[3] & 255, s.sa[3] >> 8]) + (s.plan.tag if s.sa[1] == 0 else 0).to_bytes(4, 'little')
            if s.ver >= 12: s.buf += (3_000_000).to_bytes(4, 'little') + (200000).to_bytes(4, 'little') + (2_500_000).to_bytes(4, 'little') + (s.plan.entry).to_bytes(3, 'little') + bytes([0])
        super().h(c)

def scbatch_main():
    import scbatch as SB
    rc = 0
    for host, ver in ((False, 11), (False, 12), (True, 10)):
        tasks = SB.demo_jobs(40); f = SeqFake(tasks, ver)
        print('--- scbatch, 40 jobs, %s' % ('host walks the scripts' if host else 'hardware sequencer (emulated)'))
        rc |= SB.run('x', tasks, host=host, io=f)
        if f.bad_code: print('FAIL: a job started with a code store that matches no compiled link'); rc |= 1
    f = SeqFake(SB.demo_jobs(5), 10)
    print('--- scbatch on a board without the sequencer must say so')
    rc |= (SB.run('x', SB.demo_jobs(5), host=False, io=f) != 2)
    return rc

if __name__ == '__main__':
    rc = R.main('x', io=Fake()); print()
    rc |= jobio_main()
    rc |= batch_main()
    rc |= seq_main()
    rc |= scbatch_main()
    sys.exit(rc)
