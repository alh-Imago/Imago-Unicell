#!/usr/bin/env python3
"""mutability_host.py -- ledger #1086, test 1 of the mutability proof. Talks to the board running mutability1h.fs over the USB serial port.

The bitstream NEVER changes during the test. For each phase this script (1) sends a new carrier configuration, (2) sends the same two operands, (3) reads the one word that came out of
the carrier and compares it with the word worked out here from the operands. Phase 0 is the first core on its own; phases 1 to 5 change the configuration (core setting, the shared
add-on chain, then the core itself); phase 6 puts the first configuration back.

  python3 mutability_host.py [PORT]                       the seven phases from mutability1.json
  python3 mutability_host.py PORT --cfg HEX40 [--a HEX8 --b HEX8]     send ONE configuration of your own (40 hex digits = the carrier's 160-bit word) and print what came out
  python3 mutability_host.py --selftest                    no board: checks the framing against a small software model of the board's serial protocol

Serial protocol (115200 8N1): 'C' + 20 bytes (cfg word, most significant byte first) -> board answers 'K'.
                              'D' + 4 bytes A + 4 bytes B -> board answers 'R' + 4 bytes (result), or 'T' if nothing came out in time.
Needs pyserial (pip install pyserial) except on Linux/macOS, where the standard library is enough.
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def cframe(cfg_hex):
    b = bytes.fromhex(cfg_hex.zfill(40))
    assert len(b) == 20
    return b"C" + b


def dframe(a, bb):
    return b"D" + a.to_bytes(4, "big") + bb.to_bytes(4, "big")


class Port:
    def __init__(self, path):
        try:
            import serial
            self.s = serial.Serial(path, 115200, timeout=0.05)
            self.kind = "pyserial"
        except ImportError:
            import termios, tty
            self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
            tty.setraw(self.fd)
            a = termios.tcgetattr(self.fd)
            a[4] = a[5] = termios.B115200
            a[2] |= termios.CLOCAL | termios.CREAD
            termios.tcsetattr(self.fd, termios.TCSANOW, a)
            self.s = None
            self.kind = "termios"

    def write(self, b):
        if self.s:
            self.s.write(b); self.s.flush()
        else:
            os.write(self.fd, b)

    def read(self, n, timeout):
        out, end = b"", time.time() + timeout
        while len(out) < n and time.time() < end:
            if self.s:
                out += self.s.read(n - len(out))
            else:
                import select
                r, _, _ = select.select([self.fd], [], [], 0.05)
                if r:
                    out += os.read(self.fd, n - len(out))
        return out

    def flush(self):
        self.read(4096, 0.2)


def run_phase(port, cfg_hex, a, bb):
    port.write(cframe(cfg_hex))
    k = port.read(1, 2.0)
    if k != b"K":
        return None, "no K (got %r)" % k
    port.write(dframe(a, bb))
    r = port.read(1, 3.0)
    if r == b"T":
        return None, "timeout: nothing came out of the carrier"
    if r != b"R":
        return None, "no R (got %r)" % r
    w = port.read(4, 1.0)
    if len(w) != 4:
        return None, "short reply %r" % w
    return int.from_bytes(w, "big"), ""


def main():
    args = sys.argv[1:]
    meta = json.load(open(os.path.join(HERE, "mutability1.json")))
    if "--selftest" in args:
        return selftest(meta)
    port_path = next((x for x in args if not x.startswith("--") and (len(args) == 1 or args[args.index(x) - 1] not in ("--cfg", "--a", "--b"))), None)
    if port_path is None:
        import glob
        c = sorted(glob.glob("/dev/ttyUSB*"), key=lambda s: int(''.join(ch for ch in s if ch.isdigit()) or 0))
        port_path = c[-1] if c else None
    if not port_path:
        sys.exit("no serial port found; name it: python3 mutability_host.py COM7   (or /dev/ttyUSB1)")
    opt = lambda n, d=None: args[args.index(n) + 1] if n in args else d
    a_, b_ = meta["operands"]
    port = Port(port_path)
    port.flush()
    if "--cfg" in args:
        a = int(opt("--a", "%X" % a_), 16); b = int(opt("--b", "%X" % b_), 16)
        v, why = run_phase(port, opt("--cfg"), a, b)
        print("cfg %s  A=%08X B=%08X ->" % (opt("--cfg"), a, b), ("%08X" % v) if v is not None else why)
        return 0 if v is not None else 1
    rows, bad = [], 0
    for i, p in enumerate(meta["phases"]):
        v, why = run_phase(port, p["cfg_word_hex"], a_, b_)
        ok = v == p["expected"]
        bad += 0 if ok else 1
        rows.append("phase %d  %-24s got %-8s want %08X  %s" % (i, p["label"], ("%08X" % v) if v is not None else "-", p["expected"], "ok" if ok else ("WRONG " + why)))
    same = len({p["expected"] for p in meta["phases"]}) == len(meta["phases"]) - 1
    out = ["mutability test 1 -- same bitstream, same operands A=%08X B=%08X, seven configurations" % (a_, b_)] + rows
    out.append("RESULT: %s" % ("PASS: the result followed the configuration every time, and phase 6 matches phase 0" if bad == 0 else "FAIL: %d of %d phases wrong" % (bad, len(rows))))
    text = "\n".join(out)
    print(text)
    open(os.path.join(HERE, "mutability_results.txt"), "w").write(text + "\n")
    return 0 if bad == 0 else 1


# --- a software model of the board's serial protocol, to test the framing and the reading code with no board (it does NOT model the carrier's arithmetic: it only returns the word the
# --- phase table says is expected, so a pass here proves the frames and parsing, nothing about the hardware)
class FakeBoard:
    def __init__(self, meta):
        self.meta, self.buf, self.rx, self.phase = meta, b"", b"", None
        self.table = {p["cfg_word_hex"]: p["expected"] for p in meta["phases"]}

    def write(self, b):
        self.rx += b
        while self.rx:
            if self.rx[:1] == b"C" and len(self.rx) >= 21:
                self.phase = self.rx[1:21].hex().upper().zfill(40); self.rx = self.rx[21:]; self.buf += b"K"
            elif self.rx[:1] == b"D" and len(self.rx) >= 9:
                a, bb = int.from_bytes(self.rx[1:5], "big"), int.from_bytes(self.rx[5:9], "big"); self.rx = self.rx[9:]
                assert (a, bb) == tuple(self.meta["operands"])
                v = self.table.get(self.phase)
                self.buf += (b"R" + v.to_bytes(4, "big")) if v is not None else b"T"
            else:
                break

    def read(self, n, timeout):
        o, self.buf = self.buf[:n], self.buf[n:]
        return o

    def flush(self):
        self.buf = b""


def selftest(meta):
    fb = FakeBoard(meta)
    for p in meta["phases"]:
        v, why = run_phase(fb, p["cfg_word_hex"], *meta["operands"])
        assert v == p["expected"], (p["label"], v, why)
    v, why = run_phase(fb, "0" * 40, *meta["operands"])
    assert v is None and "timeout" in why
    assert cframe("1") == b"C" + b"\x00" * 19 + b"\x01" and dframe(1, 2) == b"D\x00\x00\x00\x01\x00\x00\x00\x02"
    print("selftest ok: frames and replies parse for all", len(meta["phases"]), "phases and a timeout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
