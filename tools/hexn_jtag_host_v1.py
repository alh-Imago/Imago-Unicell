"""Host side of the JTAG link (rtl/hexn_jtag_bridge_v1.v): turns 160-bit scans into the reliable byte stream the suites expect (link.write(bytes) / link.read(n), as the serial link of tools/hexn_tang_mem_v1.py), so hexn_mem_host_v1.suite and the write-rule tests run unchanged. Frame format and rules: see the header of the RTL file.
JtagLink(scan) needs scan(value_160bit) -> value_160bit captured. Executors: SimExec (the iverilog testbench through pipes, tools/hexn_jtag_check_v1.py), the card ones are added where the transport is known."""
import subprocess, os
def crc16(v144):
    c = 0xFFFF
    for i in range(143, -1, -1):
        fb = ((c >> 15) & 1) ^ ((v144 >> i) & 1); c = (c << 1) & 0xFFFF
        if fb: c ^= 0x1021
    return c
def pack(nsend, ack, seq, data=b""):
    hdr = nsend | (ack << 8) | (seq << 16); d = int.from_bytes(bytes(data).ljust(14, b"\0"), "little")
    return hdr | (crc16((hdr << 112) | d) << 32) | (d << 48)
def unpack(cap):
    hdr = cap & 0xFFFFFFFF; crc = (cap >> 32) & 0xFFFF; d = cap >> 48
    return dict(ok=crc16((hdr << 112) | d) == crc, nvalid=hdr & 255, pop=(hdr >> 8) & 255, echo=(hdr >> 16) & 255, rxfree=(hdr >> 24) & 255, data=d.to_bytes(14, "little"))
class JtagLink:
    def __init__(self, scan, maxpoll=200000):
        self.scan = scan; self.seq = 0; self.abs_got = 0; self.rxq = bytearray(); self.rxfree = 0; self.maxpoll = maxpoll
        self.scans = 0; self.bad = 0; self.resends = 0; self.synced = False
    def _sync(self):
        """A new link may meet a card that an earlier run left mid-stream (its byte counter pop_total and last seq are not zero, and the card only drops bytes when the ack is ahead of its own counter). Read the card's counters first, line up with them, and throw away whatever stale bytes it still holds."""
        self.synced = True
        for _ in range(self.maxpoll):
            cap = unpack(self.scan(pack(0, 0, 0, b""))); self.scans += 1
            if cap["ok"]: self.abs_got = cap["pop"]; self.seq = cap["echo"]; break
            self.bad += 1
        for _ in range(60):
            c = self._frame()
            if c is not None and c["nvalid"] == 0: break
        self.rxq.clear()
    def _frame(self, send=b"", seq=None):
        if not self.synced: self._sync()
        cap = unpack(self.scan(pack(len(send), self.abs_got & 255, self.seq if seq is None else seq, send))); self.scans += 1
        if not cap["ok"]: self.bad += 1; return None
        start = self.abs_got - ((self.abs_got - cap["pop"]) & 255)
        for i in range(min(cap["nvalid"], 14)):
            if start + i >= self.abs_got: self.rxq.append(cap["data"][i]); self.abs_got = start + i + 1
        self.rxfree = cap["rxfree"]; return cap
    def _poll(self):
        for _ in range(self.maxpoll):
            c = self._frame()
            if c is not None: return c
        raise RuntimeError("the card does not answer (every capture failed its CRC)")
    def write(self, b):
        b = bytes(b)
        for k in range(0, len(b), 14):
            chunk = b[k:k + 14]; seqn = (self.seq + 1) & 255; tries = 0
            while True:
                while self.rxfree == 0: self._poll()
                self._frame(chunk, seqn)
                c = self._poll()                       # the card echoes the last frame it accepted
                if c["echo"] == seqn: self.seq = seqn; break
                self.resends += 1; tries += 1
                if tries > 5000: raise RuntimeError("the card does not take the frame")
    in_waiting = 0
    def reset_input_buffer(self):          # for the serial-port style suites (BIST): drain what the card still holds, then forget it
        for _ in range(60):
            if self._poll()["nvalid"] == 0: break
        self.rxq.clear()
    def read(self, n):
        polls = 0
        while len(self.rxq) < n:
            self._poll(); polls += 1
            if polls > self.maxpoll: raise RuntimeError("the card answered %d of %d bytes" % (len(self.rxq), n))
        d = bytes(self.rxq[:n]); del self.rxq[:n]; return d
class SimExec:
    def __init__(self, vvp, args=()):
        self.p = subprocess.Popen(["vvp", "-n", vvp] + list(args), stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    def _rd(self, tag):
        while True:
            l = self.p.stdout.readline()
            if not l: raise RuntimeError("simulation ended")
            if l.startswith(tag): return l
    def scan(self, v):
        self.p.stdin.write("S %040x\n" % v); self.p.stdin.flush(); return int(self._rd("D").split()[1], 16)
    def idle(self, n):
        self.p.stdin.write("T %d\n" % n); self.p.stdin.flush(); self._rd("T")
    def close(self):
        try: self.p.stdin.write("Q\n"); self.p.stdin.flush()
        except Exception: pass
        self.p.wait(timeout=30)
class OpenOCDExec:
    """The card, through OpenOCD (the repo's board/ypcb-00338-1p1/openocd.cfg: Digilent JTAG-HS3, 10 MHz TCK, tap xc7.tap, IR length 6). One OpenOCD process stays up with its Tcl port open; every scan is `drscan` on USER1 (IR 0x02) of 160 bits. Only one program may own the cable: hw_server / xsdb are stopped first (as the repo's `fpga` command does)."""
    def __init__(self, cfg, openocd=None, port=6666, tap="xc7.tap", ir=0x02, bits=160):
        import socket, time, shutil
        self.tap, self.bits = tap, bits; self.logpath = "/tmp/hexn_openocd.log"
        for name in ("hw_server", "cs_server", "openocd"): subprocess.run(["pkill", "-x", name], capture_output=True)
        time.sleep(1.0)
        exe = openocd or os.environ.get("OPENOCD") or shutil.which("openocd") or "/opt/oss-cad-suite/bin/openocd"
        self.p = subprocess.Popen([exe, "-f", cfg, "-c", "tcl_port %d" % port, "-c", "gdb_port disabled", "-c", "telnet_port disabled", "-c", "init"], stdout=subprocess.DEVNULL, stderr=open(self.logpath, "w"))
        self.s = None
        for _ in range(100):
            try: self.s = socket.create_connection(("127.0.0.1", port), timeout=5); break
            except OSError: time.sleep(0.1)
        if self.s is None: raise RuntimeError("OpenOCD did not start; is the cable free and the card powered? (%s)" % self._err())
        self.s.settimeout(30)      # a scan takes under a millisecond; a stall this long is reported with OpenOCD's log
        self.cmd("irscan %s 0x%x" % (tap, ir))
    def _err(self):
        try: return open(self.logpath).read()[-900:]
        except Exception: return ""
    def cmd(self, c):
        self.s.sendall(c.encode() + b"\x1a"); buf = b""
        while not buf.endswith(b"\x1a"):
            try: d = self.s.recv(65536)
            except OSError: raise RuntimeError("OpenOCD did not answer %r within the timeout; its log (%s) ends: %s" % (c[:60], self.logpath, self._err()))
            if not d: raise RuntimeError("OpenOCD closed the connection")
            buf += d
        return buf[:-1].decode().strip()
    def scan(self, v):
        r = self.cmd("drscan %s %d 0x%x" % (self.tap, self.bits, v))
        try: return int(r, 16)
        except ValueError: raise RuntimeError("drscan answered %r" % r)
    def close(self):
        try: self.s.close()
        except Exception: pass
        self.p.terminate()
