"""host_sc.py - PC side of the S-Core UART protocol (see fpga/host_bridge.v).

Library part: encode commands, decode replies.  Two uses:
  * simulation: build a command script (script_*), run the Verilated board, decode the reply stream
  * real board: Board(port) talks to the Tang Nano 20K through pyserial (pip install pyserial)
"""
import struct, time

LEN = {'V': 8, 'C': 56, 'Q': 22}

def cmd_V():                 return b'V'
def cmd_C():                 return b'C'
def cmd_R():                 return b'R'
def cmd_W(addr, word):       return b'W' + struct.pack('<HI', addr, word & 0xFFFFFFFF)
def cmd_P(tid, code, lw, crit=0, prog=0): return b'P' + struct.pack('<HHBBB', tid, code, lw, crit, prog)
def cmd_Q(tid):              return b'Q' + struct.pack('<H', tid)

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

DEC = {'V': dec_V, 'Q': dec_Q, 'C': dec_C}

def split_replies(stream, order):
    """stream: bytes received; order: list of reply letters in the order they were requested."""
    out, pos = [], 0
    for c in order:
        n = LEN[c]
        if pos + n > len(stream): raise ValueError('reply stream too short at %s: have %d bytes' % (c, len(stream) - pos))
        out.append(DEC[c](stream[pos:pos + n])); pos += n
    return out

class Board:
    """Real board over a serial port.  115200 8N1 by default (must equal BAUD_DIV in the build)."""
    def __init__(self, port, baud=115200):
        import serial
        self.s = serial.Serial(port, baud, timeout=2)
    def _rd(self, n):
        b = self.s.read(n)
        if len(b) != n: raise IOError('board did not answer (%d of %d bytes). Is the bitstream loaded and the port right?' % (len(b), n))
        return b
    def version(self):  self.s.write(cmd_V()); return dec_V(self._rd(8))
    def counters(self): self.s.write(cmd_C()); return dec_C(self._rd(56))
    def task(self, tid): self.s.write(cmd_Q(tid)); return dec_Q(self._rd(22))
    def reset(self):    self.s.write(cmd_R()); time.sleep(0.05)
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
