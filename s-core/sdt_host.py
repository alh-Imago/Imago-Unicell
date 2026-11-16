"""Host side of the SDRAM test build (fpga/sc_top_sdt.v).  Command builders, reply decoders and a Board class for a real serial port.
The simulation test (test_sdram_sim.py) uses the same builders and decoders, so both talk the same protocol."""
import struct, time

WORDS = 1 << 21          # 2M words of 32 bits = 8 MB
CLK_HZ = 27_000_000

def c_V(): return b'V'
def c_I(): return b'I'
def c_Q(): return b'Q'
def c_K(cl, dly, inv): return b'K' + bytes([cl, dly, inv])
def c_w(a, d): return b'w' + struct.pack('<I', a)[:3] + struct.pack('<I', d)
def c_r(a):    return b'r' + struct.pack('<I', a)[:3]
def c_T(mode, lg, base, count, seed): return b'T' + bytes([mode, lg]) + struct.pack('<I', base)[:3] + struct.pack('<I', count)[:3] + struct.pack('<I', seed)

def dec_V(b):
    if len(b) != 8 or b[0:2] != b'SD': raise ValueError('not an SDRAM test build (reply %r)' % bytes(b))
    return dict(version=b[2], init_done=b[3], words=struct.unpack('<I', b[4:8])[0])
def dec_I(b): return dict(init_done=b[0], cl=b[1], dly=b[2], inv=b[3])
def dec_Q(b):
    f, err, fa, fe, fg, wc, rc = struct.unpack('<BIIIIII', bytes(b))
    return dict(running=f & 1, done=(f >> 1) & 1, errors=err, first_addr=fa, expected=fe, got=fg, write_clocks=wc, read_clocks=rc)
def dec_r(b): return struct.unpack('<I', bytes(b))[0]

def speed(q, count):
    """clocks per word and megabytes per second for the write phase and the read phase"""
    out = {}
    for k in ('write', 'read'):
        c = q[k + '_clocks']
        out[k + '_clk_per_word'] = c / count
        out[k + '_MBps'] = count * 4 / (c / CLK_HZ) / 1e6 if c else 0.0
    return out

class SdtBoard:
    def __init__(self, port, baud=115200):
        import serial
        self.s = serial.Serial(port, baud, timeout=2)
        self.s.reset_input_buffer()
    def _rd(self, n):
        b = self.s.read(n)
        if len(b) != n: raise IOError('board did not answer (%d of %d bytes). Is the SDRAM test bitstream loaded and the port right?' % (len(b), n))
        return b
    def version(self): self.s.write(c_V()); return dec_V(self._rd(8))
    def info(self):    self.s.write(c_I()); return dec_I(self._rd(4))
    def config(self, cl, dly, inv, timeout=2.0):
        self.s.write(c_K(cl, dly, inv)); self.s.flush()
        t0 = time.time()
        while time.time() - t0 < timeout:
            i = self.info()
            if i['init_done'] and (i['cl'], i['dly'], i['inv']) == (cl, dly, inv): return True
            time.sleep(0.01)
        return False
    def write(self, a, d): self.s.write(c_w(a, d)); self.s.flush()
    def read(self, a):     self.s.write(c_r(a)); return dec_r(self._rd(4))
    def test(self, mode, lg, base, count, seed, timeout=60.0):
        self.s.write(c_T(mode, lg, base, count, seed)); self.s.flush()
        t0 = time.time(); time.sleep(0.02)
        while time.time() - t0 < timeout:
            self.s.write(c_Q()); q = dec_Q(self._rd(25))
            if q['done'] and not q['running']: return q
            time.sleep(0.05)
        raise IOError('memory test did not finish in %.0f s' % timeout)

# ---- far RAM commands of the pool build (fpga/sc_top_pool13.v, host_bridge_v7, board version 10) ----
FAR_ERR = {0: 'none', 1: 'far range outside the allowed window', 2: 'near range past the end of the shared RAM / code store', 3: 'far RAM not ready', 4: 'bad direction', 5: 'timeout'}
def c_F(dir_, near, far, count): return b'F' + bytes([dir_]) + struct.pack('<H', near) + struct.pack('<I', far)[:3] + struct.pack('<H', count)
def c_N(): return b'N'
def c_D(base, length): return b'D' + struct.pack('<I', base)[:3] + struct.pack('<I', length)[:3]
def dec_N(b):
    fl, err, init, _, moved, clocks = struct.unpack('<BBBBII', bytes(b))
    return dict(busy=fl & 1, done=(fl >> 1) & 1, ignored=(fl >> 2) & 1, err=err, init_done=init, moved=moved, clocks=clocks)
