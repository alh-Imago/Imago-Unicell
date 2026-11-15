"""host_sc.py - PC side of the S-Core UART protocol (see fpga/host_bridge.v).

Library part: encode commands, decode replies.  Two uses:
  * simulation: build a command script (script_*), run the Verilated board, decode the reply stream
  * real board: Board(port) talks to the Tang Nano 20K through pyserial (pip install pyserial)
"""
import struct, time

LEN = {'V': 8, 'C': 56, 'Q': 22, 'L': 4, 'Z': 4}

def cmd_V():                 return b'V'
def cmd_C():                 return b'C'
def cmd_R():                 return b'R'
def cmd_H():                 return b'H'      # hold: queue tasks but start none (board version >= 5)
def cmd_B(prog, cbase, clen, dlen): return b'B' + struct.pack('<BHHH', prog, cbase, clen, dlen)   # region of a program class (board version >= 6)
def cmd_G():                 return b'G'      # go: release the hold
def cmd_W(addr, word):       return b'W' + struct.pack('<HI', addr, word & 0xFFFFFFFF)
def cmd_P(tid, code, lw, crit=0, prog=0): return b'P' + struct.pack('<HHBBB', tid, code, lw, crit, prog)
def cmd_Q(tid):              return b'Q' + struct.pack('<H', tid)

def cmd_M(addr, word):       return b'M' + struct.pack('<HI', addr, word & 0xFFFFFFFF)   # write a word of the shared data RAM (board version >= 7)
def cmd_L(addr):             return b'L' + struct.pack('<H', addr)                      # read a word of the shared data RAM -> 4 bytes
def cmd_X(prog, base, length): return b'X' + struct.pack('<BHH', prog, base, length)    # shared window of a program class: words [base, base+length)
def cmd_Y(base, length):     return b'Y' + struct.pack('<HH', base, length)             # shared code library window: every program class may execute these code words (board version >= 8)
def cmd_Z():                 return b'Z'                                               # -> DSH(2) SHL(1) log2(DSH)(1)

def dec_L(b): return struct.unpack('<I', b[:4])[0]
def dec_Z(b): return dict(shared_words=struct.unpack('<H', b[0:2])[0], window_log2=b[2], addr_bits=b[3])

def dec_V(b):
    assert b[0:2] == b'SC', 'not an S-Core build: %r' % b
    return dict(version=b[2], S=b[3], imem_words=struct.unpack('<H', b[4:6])[0], dmem_words=struct.unpack('<H', b[6:8])[0])

def dec_Q(b):
    start, end, a0, arr, pred = struct.unpack('<IIIII', b[:20])
    fl, slot = b[20], b[21]
    return dict(start=start, end=end, a0=a0, arrival=arr, pred_known=bool(pred >> 24), pred=pred & 0xFFFFFF,
                trap=fl & 1, state=fl >> 1, slot=slot)

def dec_C(b):
    cyc, done, lerr, disp = struct.unpack('<IIII', b[:16])
    busy, blocked, tail, search, busy_l = struct.unpack('<QQQQQ', b[16:56])
    return dict(cyc=cyc, done=done, launch_err=lerr, dispatches=disp, busy_slice_cycles=busy,
                waste_blocked=blocked, waste_tail=tail, search_cycles=search, busy_leaders=busy_l)

DEC = {'V': dec_V, 'Q': dec_Q, 'C': dec_C, 'L': dec_L, 'Z': dec_Z}

def split_replies(stream, order):
    """stream: bytes received; order: list of reply letters in the order they were requested."""
    out, pos = [], 0
    for c in order:
        n = LEN[c]
        if pos + n > len(stream): raise ValueError('reply stream too short at %s: have %d bytes' % (c, len(stream) - pos))
        out.append(DEC[c](stream[pos:pos + n])); pos += n
    return out

def parse_expect(text):
    """'version=6,S=8,imem_words=64' -> dict of ints (keys as in the V reply: version, S, imem_words, dmem_words)"""
    out = {}
    for part in (text or '').split(','):
        if not part.strip(): continue
        k, _, val = part.partition('=')
        k = k.strip()
        if k not in ('version', 'S', 'imem_words', 'dmem_words') or not val.strip().lstrip('-').isdigit():
            raise SystemExit("--expect: use e.g. version=6,S=8,imem_words=64 (keys: version, S, imem_words, dmem_words); got %r" % part)
        out[k] = int(val)
    return out

def check_design(v, expect=None, need_version=0, need_what=''):
    """Stop with a plain message when the board is not running the design this test needs.
    v = the V reply.  expect = exact values wanted (see parse_expect).  need_version = lowest design version that has the feature."""
    problems = []
    if v['version'] < need_version:
        problems.append('this test needs %s (board design version %d or newer); the board reports version %d' % (need_what or 'a newer design', need_version, v['version']))
    for k, want in (expect or {}).items():
        if v[k] != want: problems.append('%s: the test expects %d, the board reports %d' % (k, want, v[k]))
    if problems:
        print('WRONG DESIGN on the board: ' + 'board reports version %d, S %d, imem_words %d, dmem_words %d' % (v['version'], v['S'], v['imem_words'], v['dmem_words']))
        for p in problems: print('  - ' + p)
        print('Most likely the Tang is still running the PREVIOUS design (a new load sometimes does not take). Unplug it for about 5 seconds, plug it in, load the right .fs file again, wait 5 seconds and rerun. If it is still wrong, the .fs file you loaded was built with different settings.')
        raise SystemExit(2)

class Board:
    """Real board over a serial port.  115200 8N1 by default (must equal BAUD_DIV in the build)."""
    def __init__(self, port, baud=115200):
        import serial
        self.s = serial.Serial(port, baud, timeout=2)
        self.flush_input()
    def _rd(self, n):
        b = self.s.read(n)
        if len(b) != n: raise IOError('board did not answer (%d of %d bytes). Is the bitstream loaded and the port right?' % (len(b), n))
        return b
    def version(self):  self.s.write(cmd_V()); return dec_V(self._rd(8))
    def counters(self): self.s.write(cmd_C()); return dec_C(self._rd(56))
    def task(self, tid): self.s.write(cmd_Q(tid)); return dec_Q(self._rd(22))
    def reset(self):    self.s.write(cmd_R()); time.sleep(0.05)
    def hold(self):     self.s.write(cmd_H()); self.s.flush()
    def region(self, prog, cbase, clen, dlen): self.s.write(cmd_B(prog, cbase, clen, dlen)); self.s.flush()
    def go(self):       self.s.write(cmd_G()); self.s.flush()
    def shared_info(self):  self.s.write(cmd_Z()); return dec_Z(self._rd(4))
    def shared_region(self, prog, base, length): self.s.write(cmd_X(prog, base, length)); self.s.flush()
    def shared_write(self, base, words):
        for i, w in enumerate(words): self.s.write(cmd_M(base + i, w))
        self.s.flush()
    def shared_write_map(self, m):
        for a, w in sorted(m.items()): self.s.write(cmd_M(a, w))
        self.s.flush()
    def library(self, base, length): self.s.write(cmd_Y(base, length)); self.s.flush()
    def shared_read(self, base, n):
        out = []
        for i in range(n): self.s.write(cmd_L(base + i)); out.append(dec_L(self._rd(4)))
        return out
    def flush_input(self):
        """throw away anything waiting on the port (the Tang's factory demo prints text at power-up)"""
        time.sleep(0.2); self.s.reset_input_buffer()
    def load(self, base, words):
        for i, w in enumerate(words): self.s.write(cmd_W(base + i, w))
        self.s.flush()
    def submit(self, tid, code, lw, crit=0, prog=0): self.s.write(cmd_P(tid, code, lw, crit, prog))
    def wait_done(self, n, timeout=60):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.counters()['done'] >= n: return True
            time.sleep(0.2)
        return False
