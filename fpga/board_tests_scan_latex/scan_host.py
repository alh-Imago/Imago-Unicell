#!/usr/bin/env python3
"""tools/scan_host_v2.py -- ledger #1151 (v2 = v1 with the design name as a parameter of Card, so one host serves any design; v1 untouched). Ledger #1146: the PC side of the in-flight capture / restore protocol (card side: tools/board_scan_v1.py; protocol described there).

The same code runs against the simulated card (board_scan_v1.SimCard) and against the real card (SerialLink, Python raw reader opened BEFORE the card is loaded and kept open).
Nothing is trusted: every dumped chunk is accepted only with design name, session, sequence number and CRC-32 all correct; every written chunk is acknowledged by the card only if its own CRC check passed;
a whole capture is taken twice and the two images must be identical; a restore is read back (captured again from the restored card) and must equal what was sent. Anything else is retried a bounded number of times
and then raises ScanError -- it never returns a wrong image quietly.
A link has send(bytes), read(n, timeout) -> up to n bytes, drain() -> everything buffered, and the attribute `instant` (True when read() never waits: the simulation).
"""
import re
import time
import zlib

DESIGN = "lcordic"
NCH, CH, IMG = 8, 32, 256
LINE = re.compile(rb"UCS " + DESIGN.encode() + rb" ses=([0-9a-f]{4}) seq=([0-7]) of=8 d=([0-9a-f]{64}) crc=([0-9a-f]{8})\r?\n")


class ScanError(Exception):
    pass


def crc32(b):
    return zlib.crc32(b) & 0xFFFFFFFF


def chunk_crc(ses, seq, data):
    return crc32(bytes([ses >> 8, ses & 255, seq, NCH]) + data)


def w_frame(ses, seq, data):
    assert len(data) == CH
    return b"W" + bytes([ses >> 8, ses & 255, seq, NCH]) + data + chunk_crc(ses, seq, data).to_bytes(4, "big")


def parse_trailer(img):
    word = int.from_bytes(img[240:244], "big")
    return dict(word=word, signed=word - (1 << 32) if word >> 31 else word, has=img[244] & 1, steps=int.from_bytes(img[245:247], "big"))


class Card:
    def __init__(self, link, retries=4, read_timeout=1.0, log=None, design=DESIGN):
        self.link, self.retries, self.rt = link, retries, read_timeout
        self.design = design
        self.line = re.compile(rb"UCS " + design.encode() + rb" ses=([0-9a-f]{4}) seq=([0-7]) of=8 d=([0-9a-f]{64}) crc=([0-9a-f]{8})\r?\n")
        self.stats = dict(dump_retries=0, write_retries=0, capture_retries=0, simple_retries=0)
        self.log = log or (lambda *a: None)

    # ---- low level
    def _read(self, n, timeout=None):
        timeout = self.rt if timeout is None else timeout
        out = b""
        t0 = time.time()
        while len(out) < n:
            b = self.link.read(n - len(out), 0.05)
            out += b
            if not b:
                if getattr(self.link, "instant", False) or time.time() - t0 > timeout:
                    break
        return out

    def _line(self, timeout=None):
        timeout = self.rt if timeout is None else timeout
        out = b""
        t0 = time.time()
        while not out.endswith(b"\n"):
            b = self.link.read(1, 0.05)
            out += b
            if not b:
                if getattr(self.link, "instant", False) or time.time() - t0 > timeout:
                    break
        return out

    def _simple(self, frame, expect=b"K", n=1):
        for k in range(self.retries + 1):
            self.link.drain()
            self.link.send(frame)
            r = self._read(n)
            if r[:1] == expect:
                return r
            self.stats["simple_retries"] += 1
            self.log("command %r: reply %r, retrying" % (frame[:1], r))
        raise ScanError("command %r: no good reply after %d tries (last %r)" % (frame[:1], self.retries + 1, r))

    # ---- commands
    def reset(self):
        return self._simple(b"X")

    def configure(self, mode, n, dly, lag):
        return self._simple(b"C" + bytes([mode, n >> 8, n & 255, dly, lag]))

    def load(self, word):
        return self._simple(b"L" + (word & 0xFFFFFFFF).to_bytes(4, "big"))

    def go(self):
        return self._simple(b"G")

    def query(self):
        for k in range(self.retries + 1):
            self.link.drain()
            self.link.send(b"Q")
            r = self._read(12)
            if len(r) == 12 and r[:1] == b"Q":
                f = r[1]
                steps = int.from_bytes(r[2:4], "big")
                word = int.from_bytes(r[4:8], "big")
                return dict(stopped=f & 1, busy=(f >> 1) & 1, held_valid=(f >> 2) & 1, hold=(f >> 3) & 1, steps=steps, word=word, signed=word - (1 << 32) if word >> 31 else word, run_clocks=int.from_bytes(r[8:12], "big"))
        raise ScanError("query: no good reply")

    def wait_stopped(self, timeout=30.0, steps=None):
        t0 = time.time()
        while True:
            q = self.query()
            if q["stopped"] and (steps is None or q["steps"] == steps):
                return q
            if time.time() - t0 > timeout:
                raise ScanError("card did not stop in %.0f s (last %r)" % (timeout, q))
            if getattr(self.link, "instant", False):
                self.link.idle(2000)

    def capture(self):
        r = self._simple(b"S", expect=b"K")
        return r

    def dump_chunk(self, seq):
        last = None
        for k in range(self.retries + 1):
            self.link.drain()
            self.link.send(b"D" + bytes([seq]))
            raw = b""
            t0 = time.time()
            while True:
                ln = self._line()
                raw += ln
                m = self.line.search(raw)
                if m or not ln:
                    break
            if m:
                ses, sq, d, c = int(m.group(1), 16), int(m.group(2)), bytes.fromhex(m.group(3).decode()), int(m.group(4), 16)
                if sq == seq and c == chunk_crc(ses, sq, d):
                    return ses, d
                last = "line parsed but seq/CRC wrong"
            else:
                last = "no valid line (%d bytes: %r...)" % (len(raw), raw[:40])
            self.stats["dump_retries"] += 1
            self.log("dump chunk %d: %s, retrying" % (seq, last))
            time.sleep(0 if getattr(self.link, "instant", False) else 0.2)
        raise ScanError("dump chunk %d: %s after %d tries" % (seq, last, self.retries + 1))

    def dump_image(self):
        parts, sessions = [], set()
        for seq in range(NCH):
            ses, d = self.dump_chunk(seq)
            sessions.add(ses)
            parts.append(d)
        if len(sessions) != 1:
            raise ScanError("chunks come from different sessions: %r" % sorted(sessions))
        return sessions.pop(), b"".join(parts)

    def capture_verified(self):
        """Capture twice (the chain is read by recirculating, so the second capture is the same state): the two images must be identical."""
        prev = None
        for k in range(self.retries + 1):
            self.capture()
            ses1, a = self.dump_image()
            self.capture()
            ses2, b = self.dump_image()
            if a == b and ses2 == ses1 + 1:
                return ses2, a
            self.stats["capture_retries"] += 1
            self.log("two captures differ (or sessions odd): %d bytes differ" % sum(x != y for x, y in zip(a, b)))
        raise ScanError("two captures never agreed")

    def write_chunk(self, ses, seq, data):
        last = None
        for k in range(self.retries + 1):
            self.link.drain()
            self.link.send(w_frame(ses, seq, data))
            r = self._read(3, self.rt + 0.5)
            if len(r) == 3 and r[0:1] == b"K" and r[1] == seq and (r[2] >> seq) & 1:
                return r[2]
            last = r
            self.stats["write_retries"] += 1
            self.log("write chunk %d: reply %r, retrying" % (seq, r))
            time.sleep(0 if getattr(self.link, "instant", False) else 0.3)
            self.link.drain()
        raise ScanError("write chunk %d: no 'K' after %d tries (last reply %r)" % (seq, self.retries + 1, last))

    def restore(self, ses, image, verify=True):
        """Write the image (8 checked chunks), apply it, and read it back from the restored card. The card must have been reset and configured first; release with go() afterwards."""
        assert len(image) == IMG
        self._simple(b"Z")
        for seq in range(NCH):
            self.write_chunk(ses, seq, image[seq * CH:(seq + 1) * CH])
        m = self._simple(b"M", expect=b"M", n=4)
        if m[1] != 0xFF:
            raise ScanError("card reports chunk mask %02x after the writes" % m[1])
        self._simple(b"A")
        if verify:
            _, back = self.capture_verified()
            if back != image:
                bad = [i for i in range(IMG) if back[i] != image[i]]
                raise ScanError("READ-BACK DIFFERS after restore: %d bytes (first at %d)" % (len(bad), bad[0]))
        return True


class FaultLink:
    """Wraps a link and damages traffic on purpose.  faults: list of (dir, letter, nth, kind, pos): dir 'tx' (host->card) or 'rx' (card->host); letter = the command letter;
    nth = which use of that command (1 = first; 0 = every one); kind 'flip' (flip a bit of byte pos), 'drop' (remove byte pos), 'dup' (repeat byte pos)."""

    def __init__(self, inner, faults):
        self.inner, self.faults, self.count = inner, list(faults), {}
        self.instant = getattr(inner, "instant", False)
        self.injected = 0

    def _hit(self, d, letter):
        n = self.count.get(letter, 0)
        return [f for f in self.faults if f[0] == d and f[1] == letter and f[2] in (0, n)]

    @staticmethod
    def _apply(b, kind, pos):
        b = bytearray(b)
        if pos >= len(b):
            return bytes(b)
        if kind == "flip":
            b[pos] ^= 0x10
        elif kind == "drop":
            del b[pos]
        elif kind == "dup":
            b.insert(pos, b[pos])
        return bytes(b)

    def send(self, data):
        letter = chr(data[0]) if data else ""
        self.count[letter] = self.count.get(letter, 0) + 1
        for f in self._hit("tx", letter):
            data = self._apply(data, f[3], f[4]); self.injected += 1
        rxf = self._hit("rx", letter)
        if hasattr(self.inner, "idle"):          # simulated card: the reply is already in the buffer after send(), damage it there (flip, drop, dup)
            before = len(self.inner.buf)
            self.inner.send(data)
            for f in rxf:
                new = self._apply(self.inner.buf[before:], f[3], f[4]); self.injected += 1
                self.inner.buf = self.inner.buf[:before] + new
        else:                                    # real serial link: replies arrive later, so only bit flips are applied, as the bytes are read
            self.inner.send(data)
            self.rx_pending, self.rx_off = [f for f in rxf if f[3] == "flip"], 0

    rx_pending, rx_off = (), 0

    def read(self, n, timeout=None):
        b = self.inner.read(n, timeout)
        if self.rx_pending and b:
            b = bytearray(b)
            for f in self.rx_pending:
                if self.rx_off <= f[4] < self.rx_off + len(b):
                    b[f[4] - self.rx_off] ^= 0x10; self.injected += 1
            self.rx_off += len(b); b = bytes(b)
        return b

    def drain(self):
        return self.inner.drain()

    def idle(self, c):
        return self.inner.idle(c)
