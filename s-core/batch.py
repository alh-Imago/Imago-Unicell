"""batch.py - the S-Core batch script: format, builder and reference executors (stage 3, step 2).

A batch script is a list of STEPS held in far RAM (the onboard SDRAM).  Each step is 4 words of 32 bits: w0 = opcode, w1..w3 = arguments.  A sequencer
(first the host-driven executor below, later a small state machine on the card) reads the steps one after another and does what the host does by hand today,
so a large run needs no host in between and the dispatcher is not touched.

  opcode  name       w1                  w2                      w3
  0       END        tag (reported)      -                       -            stop; the batch is complete
  1       LOAD_CODE  near (code word)    far (word address)      count        far RAM -> code store           (needs no job in flight)
  2       LOAD_DATA  near (shared word)  far                     count        far RAM -> shared RAM
  3       SAVE       near (shared word)  far                     count        shared RAM -> far RAM
  4       SUBMIT     tid | code<<16      prog | lw<<8 | crit<<12 -            submit a job (code = entry word address)
  5       WAIT       timeout/1024 clk    -                       -            wait until every job submitted since the last WAIT has finished
  6       JUMP       far address of the next script                           chain: continue there
  7       REGION     prog | cbase<<16    clen | dlen<<16         -            code/private-data region of a program class     (needs no job in flight)
  8       WINDOW     prog                base | len<<16          -            shared window of a program class                 (needs no job in flight)
  9       LIBRARY    base | len<<16      -                       -            shared code library window                         (needs no job in flight)

Rules (the same in every executor):  jobs are only submitted, never preempted; WAIT counts finished jobs against the board's done counter (a job that traps
counts as finished); LOAD_CODE / REGION / WINDOW / LIBRARY while jobs are in flight (submitted and not yet waited for) are REFUSED with error 7, so code is
never replaced under a running job; a copy the board refuses (protection window, range) stops the batch with the copy engine's error code (1..5).
Error codes: 0 ok, 1..5 copy engine (1 far range outside the allowed window, 2 near range past the end, 3 far RAM not ready, 4 bad direction, 5 timeout),
6 wait timed out, 7 code/region change with jobs in flight, 8 bad opcode, 9 script ran past its end without END (live executor: step limit)."""
import time
import host_sc as hs, sdt_host as H

END, LOAD_CODE, LOAD_DATA, SAVE, SUBMIT, WAIT, JUMP, REGION, WINDOW, LIBRARY = range(10)
NAMES = ['END', 'LOAD_CODE', 'LOAD_DATA', 'SAVE', 'SUBMIT', 'WAIT', 'JUMP', 'REGION', 'WINDOW', 'LIBRARY']
M32 = 0xFFFFFFFF
ERR_WAIT, ERR_INFLIGHT, ERR_OPCODE, ERR_RUNAWAY = 6, 7, 8, 9
DEFAULT_WAIT_K = 4096          # a WAIT with timeout 0 allows 4096 * 1024 clocks (about 0.16 s at 27 MHz)

class Script:
    """steps built in order; words() gives the 4*n words that go to far RAM"""
    def __init__(s): s.steps = []
    def _add(s, op, a=0, b=0, c=0): s.steps.append((op, a & M32, b & M32, c & M32)); return s
    def end(s, tag=0):                       return s._add(END, tag)
    def load_code(s, near, far, count):      return s._add(LOAD_CODE, near, far, count)
    def load_data(s, near, far, count):      return s._add(LOAD_DATA, near, far, count)
    def save(s, near, far, count):           return s._add(SAVE, near, far, count)
    def submit(s, tid, code, prog, lw=0, crit=0): return s._add(SUBMIT, tid | (code << 16), prog | (lw << 8) | (crit << 12))
    def wait(s, timeout_k=0):                return s._add(WAIT, timeout_k)
    def jump(s, far):                        return s._add(JUMP, far)
    def region(s, prog, cbase, clen, dlen):  return s._add(REGION, prog | (cbase << 16), clen | (dlen << 16))
    def window(s, prog, base, length):       return s._add(WINDOW, prog, base | (length << 16))
    def library(s, base, length):            return s._add(LIBRARY, base | (length << 16))
    def words(s): return [w for st in s.steps for w in st]
    def __len__(s): return 4 * len(s.steps)

def decode(w):
    """-> (name, fields dict) for one step of 4 words"""
    op, a, b, c = w
    if op == END: return 'END', dict(tag=a)
    if op in (LOAD_CODE, LOAD_DATA, SAVE): return NAMES[op], dict(near=a, far=b, count=c)
    if op == SUBMIT: return 'SUBMIT', dict(tid=a & 0xFFFF, code=a >> 16, prog=b & 0xFF, lw=(b >> 8) & 0xF, crit=(b >> 12) & 1)
    if op == WAIT: return 'WAIT', dict(timeout_k=a or DEFAULT_WAIT_K)
    if op == JUMP: return 'JUMP', dict(far=a)
    if op == REGION: return 'REGION', dict(prog=a & 0xFFFF, cbase=a >> 16, clen=b & 0xFFFF, dlen=b >> 16)
    if op == WINDOW: return 'WINDOW', dict(prog=a, base=b & 0xFFFF, length=b >> 16)
    if op == LIBRARY: return 'LIBRARY', dict(base=a & 0xFFFF, length=a >> 16)
    return 'BAD', dict(op=op)

class Layout:
    """hands out far RAM and remembers what must be written there before the batch starts"""
    def __init__(s, base): s.next, s.image = base, {}
    def put(s, words, at=None):
        a = s.next if at is None else at
        for i, w in enumerate(words): s.image[a + i] = w & M32
        if at is None: s.next += len(words)
        return a
    def reserve(s, n): a = s.next; s.next += n; return a

# ---------------------------------------------------------------- executors
class InFlight(Exception): pass

class PlanExec:
    """walks the script exactly as the live executor would and emits the host commands for the simulation harness (test_farram_sim.Script):
    waits are fixed delays here (a simulation cannot be asked questions halfway).  Raises on a rule violation, like the live executor does."""
    def __init__(s, sc, read_word, copy_extra=lambda n: 40 * n + 0x600, step_limit=10000):
        s.sc, s.read_word, s.copy_extra, s.limit = sc, read_word, copy_extra, step_limit
        s.pending = 0; s.log = []
    def run(s, pc):
        for _ in range(s.limit):
            w = [s.read_word(pc + i) for i in range(4)]; name, f = decode(w); s.log.append((pc, name, f)); pc += 4
            if name == 'END': return f['tag']
            elif name == 'JUMP': pc = f['far']
            elif name in ('LOAD_CODE', 'REGION', 'WINDOW', 'LIBRARY'):
                if s.pending: raise InFlight('%s with %d job(s) in flight' % (name, s.pending))
                if name == 'LOAD_CODE': s.sc.send(H.c_F(2, f['near'], f['far'], f['count']), 0, extra=s.copy_extra(f['count']))
                elif name == 'REGION': s.sc.send(hs.cmd_B(f['prog'], f['cbase'], f['clen'], f['dlen']), extra=0x200)
                elif name == 'WINDOW': s.sc.send(hs.cmd_X(f['prog'], f['base'], f['length']), extra=0x200)
                else: s.sc.send(hs.cmd_Y(f['base'], f['length']), extra=0x200)
            elif name == 'LOAD_DATA': s.sc.send(H.c_F(1, f['near'], f['far'], f['count']), 0, extra=s.copy_extra(f['count']))
            elif name == 'SAVE': s.sc.send(H.c_F(0, f['near'], f['far'], f['count']), 0, extra=s.copy_extra(f['count']))
            elif name == 'SUBMIT': s.sc.send(hs.cmd_P(f['tid'], f['code'], f['lw'], f['crit'], f['prog'])); s.pending += 1
            elif name == 'WAIT': s.sc.wait(f['timeout_k'] * 1024); s.pending = 0
            else: raise ValueError('bad opcode')
        raise RuntimeError('step limit')

class LiveExec:
    """runs a script on the real board from the host: reads each step out of far RAM (so the image written there is what is executed), does it, and
    reports (error code, tag, steps executed).  Needs the far RAM design (board version 10)."""
    def __init__(s, b, step_limit=10000, log=None):
        s.b, s.limit, s.log = b, step_limit, (log if log is not None else [])
        s.pending = 0; s.done_base = 0
    def put(s, cmd): s.b.s.write(cmd); s.b.s.flush()
    def far_r(s, a): s.put(H.c_r(a)); return H.dec_r(s.b._rd(4))
    def copy(s, dir_, near, far, count, timeout=10.0):
        s.put(H.c_F(dir_, near, far, count)); t0 = time.time(); time.sleep(0.005)
        while True:
            s.put(H.c_N()); n = H.dec_N(s.b._rd(12))
            if n['done'] and not n['busy']: return n['err']
            if time.time() - t0 > timeout: return 5
            time.sleep(0.005)
    def run(s, pc):
        steps = 0
        while steps < s.limit:
            w = [s.far_r(pc + i) for i in range(4)]; name, f = decode(w); s.log.append((pc, name, f)); pc += 4; steps += 1
            if name == 'END': return 0, f['tag'], steps
            if name == 'JUMP': pc = f['far']; continue
            if name in ('LOAD_CODE', 'REGION', 'WINDOW', 'LIBRARY') and s.pending: return ERR_INFLIGHT, None, steps
            if name in ('LOAD_CODE', 'LOAD_DATA', 'SAVE'):
                e = s.copy({'LOAD_CODE': 2, 'LOAD_DATA': 1, 'SAVE': 0}[name], f['near'], f['far'], f['count'])
                if e: return e, None, steps
            elif name == 'REGION': s.put(hs.cmd_B(f['prog'], f['cbase'], f['clen'], f['dlen']))
            elif name == 'WINDOW': s.put(hs.cmd_X(f['prog'], f['base'], f['length']))
            elif name == 'LIBRARY': s.put(hs.cmd_Y(f['base'], f['length']))
            elif name == 'SUBMIT':
                if s.pending == 0: s.done_base = s.b.counters()['done']
                s.put(hs.cmd_P(f['tid'], f['code'], f['lw'], f['crit'], f['prog'])); s.pending += 1
            elif name == 'WAIT':
                t_end = time.time() + max(5.0, 3 * f['timeout_k'] * 1024 / 27e6)
                while s.pending and s.b.counters()['done'] - s.done_base < s.pending:
                    if time.time() > t_end: return ERR_WAIT, None, steps
                    time.sleep(0.005)
                s.pending = 0
            else: return ERR_OPCODE, None, steps
        return ERR_RUNAWAY, None, steps
