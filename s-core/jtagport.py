"""jtagport.py - the host side of the Kintex card's JTAG byte link (fpga/jtag_link_v1.v).  It looks like a serial port (write / read / flush /
reset_input_buffer / close / timeout) so host_sc.Board, sdt_host, batch and scbatch work unchanged:   Board('jtag')  or  Board('jtag:HOST:PORT').

How it talks: OpenOCD (the same one k7_tree4_jtag used) holds the cable; this module sends it `irscan` / `drscan` commands over OpenOCD's TCL port.
    'jtag'            start openocd here with s-core/k7/openocd_ft232h.cfg (needs openocd on PATH: `nix shell nixpkgs#openocd`), then connect to it
    'jtag:HOST:PORT'  connect to an OpenOCD that is already running (it must have `tcl_port PORT` and the card's tap named xc7.tap)
Each exchange is one scan of USER1 (IR 0x02) of W = 16 + 8*K bits: see the header of fpga/jtag_link_v1.v for the word layout.  Rules this module follows:
  * a word shifted in is acted on by the design only at the START OF THE NEXT scan, so write() data needs one more scan to take effect (flush() does it);
  * an ack (we have taken the window we were shown) is also acted on one scan late, so the response to a scan that carries an ack shows the old window:
    its payload is ignored here;
  * bytes are only sent while the design's last response said ready;
  * every response must carry the marker 4'h5 in bits 15:12, otherwise the link is not what we think it is and an error is raised."""
import os, socket, subprocess, time, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
K = 32
W = 16 + 8 * K
IR_USER1 = 0x02
DEFAULT_CFG = os.path.join(HERE, 'k7', 'openocd_ft232h.cfg')


class LinkError(IOError):
    pass


class OpenOcdScanner:
    """scan(width, value) -> value, through OpenOCD's TCL port (commands end with 0x1a, so do replies)."""
    def __init__(self, port='jtag', cfg=None, tap='xc7.tap', startup_timeout=15.0):
        self.tap, self.proc, self.sock = tap, None, None
        host, tcl = '127.0.0.1', 6666
        if port.startswith('jtag:'):
            parts = port.split(':')
            host = parts[1] or host
            if len(parts) > 2: tcl = int(parts[2])
        else:
            exe = shutil.which('openocd')
            if not exe: raise LinkError("openocd not found: run `nix shell nixpkgs#openocd` first (or start OpenOCD yourself and use 'jtag:127.0.0.1:6666')")
            cfg = cfg or DEFAULT_CFG
            self.log = tempfile.NamedTemporaryFile('w+', suffix='.openocd.log', delete=False)
            self.proc = subprocess.Popen([exe, '-f', cfg, '-c', 'tcl_port %d' % tcl, '-c', 'telnet_port disabled', '-c', 'gdb_port disabled', '-c', 'init'],
                                         stdout=self.log, stderr=subprocess.STDOUT)
        t0 = time.time()
        while True:
            try:
                self.sock = socket.create_connection((host, tcl), timeout=2); break
            except OSError:
                if self.proc and self.proc.poll() is not None: raise LinkError('openocd exited; see %s' % self.log.name)
                if time.time() - t0 > startup_timeout: raise LinkError('cannot reach OpenOCD on %s:%d' % (host, tcl))
                time.sleep(0.2)
        self.sock.settimeout(10)
        self.cmd('irscan %s 0x%02x' % (self.tap, IR_USER1))

    def cmd(self, c):
        self.sock.sendall(c.encode() + b'\x1a')
        buf = b''
        while not buf.endswith(b'\x1a'):
            ch = self.sock.recv(65536)
            if not ch: raise LinkError('OpenOCD closed the connection')
            buf += ch
        return buf[:-1].decode().strip()

    def scan(self, width, value):
        fields, shift, left = [], 0, width
        while left > 0:
            w = min(32, left)
            fields.append('%d 0x%x' % (w, (value >> shift) & ((1 << w) - 1))); shift += w; left -= w
        out = self.cmd('drscan %s %s' % (self.tap, ' '.join(fields))).split()
        if len(out) * 1 != len(fields): raise LinkError('unexpected drscan answer: %r' % out)
        res, shift, left = 0, 0, width
        for t in out:
            w = min(32, left); res |= int(t, 16) << shift; shift += w; left -= w
        return res

    def close(self):
        try:
            if self.sock: self.cmd('shutdown')
        except Exception: pass
        try:
            if self.sock: self.sock.close()
        except Exception: pass
        if self.proc:
            try: self.proc.wait(timeout=3)
            except Exception: self.proc.kill()


class JtagSerial:
    """serial.Serial look-alike over the JTAG link.  `scanner` is anything with scan(width, value) -> value (tests pass a model)."""
    def __init__(self, port='jtag', timeout=2, scanner=None):
        self.timeout = timeout
        self.sc = scanner if scanner is not None else OpenOcdScanner(port)
        self.txq, self.rxq = bytearray(), bytearray()
        self.ready, self.ack_pending = True, False
        self.scans = 0
        self.exchange(); self.exchange()           # settle: the first scans only prime the pipeline

    # ---- one scan
    def exchange(self):
        send = bytes(self.txq[:K]) if self.ready else b''
        word = len(send) | (1 << 8 if self.ack_pending else 0) | (0xA << 12)
        for i, b in enumerate(send): word |= b << (16 + 8 * i)
        was_ack = self.ack_pending
        v = self.sc.scan(W, word)
        self.scans += 1
        if (v >> 12) & 0xF != 0x5: raise LinkError('the JTAG link answered with a wrong marker (%#x): is the Kintex S-Core bitstream loaded?' % ((v >> 12) & 0xF))
        del self.txq[:len(send)]
        nout, self.ready = v & 0xFF, bool((v >> 8) & 1)
        if nout > K: raise LinkError('window of %d bytes (more than %d)' % (nout, K))
        self.ack_pending = False
        if not was_ack and nout:
            self.rxq += bytes((v >> (16 + 8 * i)) & 0xFF for i in range(nout))
            self.ack_pending = True

    # ---- serial-like API
    def write(self, b):
        self.txq += bytes(b); return len(b)

    def flush(self):
        """get everything written so far to the design and acted on (two scans per K bytes, plus one to make the last word take effect)"""
        n = 0
        while self.txq and n < 100000: self.exchange(); n += 1
        self.exchange()

    def read(self, n):
        t0 = time.time()
        while len(self.rxq) < n:
            self.exchange()
            if time.time() - t0 > self.timeout: break
        out = bytes(self.rxq[:n]); del self.rxq[:n]; return out

    @property
    def in_waiting(self): return len(self.rxq)

    def reset_input_buffer(self):
        for _ in range(4): self.exchange()
        self.rxq.clear()

    def close(self):
        if hasattr(self.sc, 'close'): self.sc.close()
