"""Runs the command line scheduler (sccli.py) against the whole-board simulation (v11 design, UART pins).
The simulator cannot be talked to live, so every read of the board re-runs the simulation from reset with everything the program has
written so far plus a pause; the simulation is exact and repeatable, so each read gets the true reply.
Usage: python3 test_cli_sim.py [S]   (default 4)"""
import os, sys, io
os.environ.setdefault('POOL', '7')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import test_board_sim as tbs, host_sc as hs, sccli

class SimSerial:
    def __init__(self, exe, div):
        self.exe, self.div, self.seq, self.got, self.pend = exe, div, [], 0, b''
        self.runs = 0
    def write(self, b): self.seq.append(('B', bytes(b)))
    def flush(self): pass
    def reset_input_buffer(self): pass
    def pause(self, clocks): self.seq.append(('D', clocks))
    def read(self, n):
        self.pause(n * 10 * self.div + 4 * self.div * 10)               # time for the reply to be sent
        out = tbs.run(self.exe, self.seq, tag='cli'); self.runs += 1
        r = out[self.got:self.got + n]; self.got += len(r)
        return r

def make(S, queue=16):
    exe = tbs.build(S=S, QD=queue, IMW=128, DMW=16, DIV=8, tag='cli', DSH=256)
    ser = SimSerial(exe, 8)
    b = hs.Board.__new__(hs.Board); b.s = ser
    lines = []
    sess = sccli.Session(b, out=lines.append, sleep=lambda s: ser.pause(int(s * 2000000)), queue=queue)
    return sess, ser, lines

def main(S=4):
    sess, ser, lines = make(S)
    sh = sccli.Shell(sess, keep_going=True)
    script = open(os.path.join(HERE, 'cli_demo', 'demo.sccli')).read().splitlines()
    sess.connect()
    os.chdir(HERE)
    sccli.run_lines(sh, script)
    text = '\n'.join(lines); print(text); print('(%d simulation runs)' % ser.runs)
    jobs = sess.jobs; bad = []
    def chk(c, what):
        if not c: bad.append(what)
    chk(sh.failed == 0, 'a command reported an error')
    chk(len(jobs) == 8, '8 jobs, got %d' % len(jobs))
    for j, r in jobs.items():
        want = {'sum': ('done', 136), 'spin': ('done', 200), 'fib': ('done', 144), 'fib2': ('done', 144), 'bad': ('trap', None)}[r['name']]
        chk(r['state'] == want[0], 'job %d %s state %s, expected %s' % (j, r['name'], r['state'], want[0]))
        if want[1] is not None and r['q']: chk(r['q']['a0'] == want[1], 'job %d %s a0 %s, expected %d' % (j, r['name'], r['q']['a0'] if r['q'] else None, want[1]))
    chk('0: 00000001 00000002 00000003 00000004' in text, 'shared RAM words 0..3 not as preloaded')
    chk(any('slice utilisation' in l for l in lines), 'counters not shown')
    # error handling: unknown program, run before send is checked on a fresh session
    s2 = sccli.Session(hs.Board.__new__(hs.Board), out=lambda t: None); s2.b.s = ser
    try: s2.run('x'); bad.append('run without connection should fail')
    except sccli.CliError: pass
    try: sess.run('nosuch')
    except sccli.CliError as e: chk('no program called' in str(e), 'wrong error text')
    else: bad.append('unknown program should fail')
    print('RESULT', 'PASS' if not bad else 'FAIL'); [print('  ' + m) for m in bad]
    return not bad

def queue_test(S=2, queue=4):
    """more jobs than task slots: run must wait for slots to free up, and report a full queue while on hold"""
    sess, ser, lines = make(S, queue); os.chdir(HERE); bad = []
    sh = sccli.Shell(sess, keep_going=True)
    sess.connect(); sccli.run_lines(sh, ['load cli_demo/demo.scs', 'send', 'run spin 10', 'wait', 'jobs'])
    done = [r for r in sess.jobs.values() if r['state'] == 'done' and r['q'] and r['q']['a0'] == 200]
    if len(done) != 10: bad.append('10 jobs through a %d-slot table: %d finished right' % (queue, len(done)))
    if sh.failed: bad.append('errors: ' + '; '.join(l for l in lines if l.startswith('error')))
    sess.hold()
    try: sess.run('spin', 6); bad.append('a full queue on hold should be refused')
    except sccli.CliError as e:
        if 'on hold' not in str(e): bad.append('wrong message: %s' % e)
    print('queue test:', 'PASS' if not bad else 'FAIL'); [print('  ' + m) for m in bad]
    return not bad

if __name__ == '__main__':
    S = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    ok = main(S); ok = queue_test() and ok
    sys.exit(0 if ok else 1)
