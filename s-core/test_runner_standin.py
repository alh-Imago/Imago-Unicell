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
        return dict(state=2 if s.polls[t] == 1 and t >= 10 else 3, trap=0, a0=0, start=10, end=1010)
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

if __name__ == '__main__':
    rc = R.main('x', io=Fake()); print()
    rc |= jobio_main()
    sys.exit(rc)
