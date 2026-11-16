"""jtagport.py (host side of the Kintex JTAG byte link) against a Python model of fpga/jtag_link_v1.v.  No hardware, no iverilog.
The model follows the Verilog: a host word is acted on at the next capture, an ack empties the shown bank and switches banks at that capture, the response
to the scan that carries an ack shows the old window.  The same algorithm (host rule) passes in the Verilog simulation (test_k7_sim.py / fpga/tb_k7.v).
Checks: 5000 random bytes echoed back complemented in order for several write sizes; a burst longer than the design's FIFO; read timeout when nothing comes;
marker error is raised; the scan count stays near two scans per K bytes."""
import os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import jtagport as J

K, W = J.K, J.W

class LinkModel:
    """scan(width, value) like OpenOcdScanner; `device(byte) -> bytes` stands for the host bridge (instant)."""
    def __init__(self, device, rx_fifo=512, marker_bug=False):
        self.dev, self.rxcap, self.bug = device, rx_fifo, marker_bug
        self.prev = 0; self.banks = [bytearray(), bytearray()]; self.cur = 0; self.sealed = False; self.txf = bytearray(); self.rxf = bytearray(); self.scans = 0
    def _drain(self):
        # bridge side: bytes come out of the receive FIFO, replies go into the transmit FIFO, then fill the filling bank
        while self.rxf: self.txf += bytes(self.dev(self.rxf.pop(0)))
        fb = self.cur ^ 1 if self.sealed else self.cur
        while self.txf and len(self.banks[fb]) < K: self.banks[fb].append(self.txf.pop(0))
    def scan(self, width, value):
        assert width == W
        self.scans += 1; self._drain()
        host_ok = (self.prev >> 12) & 0xF == 0xA; ack = host_ok and (self.prev >> 8) & 1
        rx_ready = len(self.rxf) <= self.rxcap - 2 * K - 2
        if ack: self.banks[self.cur].clear(); self.cur ^= 1
        show = self.banks[self.cur]
        resp = len(show) | (int(rx_ready) << 8) | ((0x5 if not self.bug else 0x3) << 12)
        for i, b in enumerate(show): resp |= b << (16 + 8 * i)
        self.sealed = len(show) != 0
        if host_ok:
            n = min(self.prev & 0xFF, K)
            if n and rx_ready: self.rxf += bytes((self.prev >> (16 + 8 * i)) & 0xFF for i in range(n))
        self._drain_after = True
        self.prev = value
        self._drain()
        return resp

def make(device, **kw):
    m = LinkModel(device, **kw); return J.JtagSerial(scanner=m, timeout=2), m

def main():
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-84s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    r = random.Random(7)
    comp = lambda b: [b ^ 0xFF]
    for chunk in (1, 5, 32, 33, 200):
        s, m = make(comp); data = bytes(r.randrange(256) for _ in range(1500))
        for i in range(0, len(data), chunk): s.write(data[i:i + chunk]); s.flush() if chunk < 40 and i % 7 == 0 else None
        got = s.read(len(data)); s.flush()
        check('echo of 1500 bytes written in pieces of %d comes back complete and in order' % chunk, got == bytes(b ^ 0xFF for b in data), '%d scans' % m.scans)
    s, m = make(comp); data = bytes(r.randrange(256) for _ in range(5000)); s.write(data); got = s.read(len(data))
    check('one 5000-byte burst (more than the FIFO holds) is not lost or reordered', got == bytes(b ^ 0xFF for b in data), '%d scans, %.1f scans per 32 bytes' % (m.scans, m.scans / (len(data) / 32)))
    s, m = make(lambda b: [0x11] * 8 if b == 0x56 else [])
    s.write(b'\x56'); s.flush(); a = s.read(8); b = s.read(8)
    check('a request with an 8-byte reply: reply complete; asking again with nothing sent times out with no bytes', a == bytes([0x11] * 8) and b == b'', 'second read gave %d bytes' % len(b))
    s.reset_input_buffer(); check('reset_input_buffer leaves nothing waiting', s.in_waiting == 0)
    try:
        make(comp, marker_bug=True); check('a wrong marker is reported as an error', False)
    except J.LinkError as e:
        check('a wrong marker is reported as an error', 'marker' in str(e), str(e)[:60])
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
