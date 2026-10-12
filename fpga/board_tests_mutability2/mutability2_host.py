#!/usr/bin/env python3
"""mutability2_host.py -- ledger #1088, test 2 of the mutability proof (Tang Nano 20K, mixed-family card: carrier v1d + standalone command_cell_v4 + standalone sequencer_cell_v4).
Talks to the board running mutability2.fs over the USB serial port. The bitstream NEVER changes.

  python3 mutability2_host.py [PORT] [--mhz 27]     run everything: 7 reconfiguration phases through the command cell, then two 64-result streams
  python3 mutability2_host.py --selftest            no board: checks the framing against a small software model of the serial protocol

Serial protocol (115200 8N1):
  'W' n w1..wn (n <= 12 words, 4 bytes each, big-endian) -> 'K' + 4 bytes = clocks the command cell took to relay the words and go quiet, or 'T'
  'D' A(4) B(4)                                            -> 'R' + result(4) + latency(4) = clocks from B going in to the result on the east face, or 'T'
  'S' cfg(8) n(2)                                          -> 'U' + first_result_clock(4) + clock_of_nth_result(4) + first_value(4) + last_value(4), or 'T'
Every clock figure is counted ON THE CARD. Nanoseconds = clocks x period (27 MHz = 37.04 ns); the figures are exact counts, not Fmax claims.
All results are also written to mutability2_results.txt and mutability2_results.json (keep a copy of both).
"""
import json, os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def wframe(words):
    return b"W" + bytes([len(words)]) + b"".join(w.to_bytes(4, "big") for w in words)


def dframe(a, b):
    return b"D" + a.to_bytes(4, "big") + b.to_bytes(4, "big")


def sframe(cfg, n):
    return b"S" + cfg.to_bytes(8, "big") + n.to_bytes(2, "big")


class Port:
    def __init__(self, path):
        try:
            import serial
            self.s = serial.Serial(path, 115200, timeout=0.05)
        except ImportError:
            import termios, tty
            self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
            tty.setraw(self.fd)
            a = termios.tcgetattr(self.fd)
            a[4] = a[5] = termios.B115200
            a[2] |= termios.CLOCAL | termios.CREAD
            termios.tcsetattr(self.fd, termios.TCSANOW, a)
            self.s = None

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


def reprogram(port, words):
    port.write(wframe(words))
    k = port.read(1, 3.0)
    if k != b"K":
        return None, "no K (got %r)" % k
    c = port.read(4, 1.0)
    return (int.from_bytes(c, "big") if len(c) == 4 else None), ""


def single(port, a, b):
    port.write(dframe(a, b))
    r = port.read(1, 3.0)
    if r != b"R":
        return None, None, "no R (got %r)" % r
    d = port.read(8, 1.0)
    if len(d) != 8:
        return None, None, "short reply %r" % d
    return int.from_bytes(d[:4], "big"), int.from_bytes(d[4:], "big"), ""


def stream(port, cfg, n):
    port.write(sframe(cfg, n))
    r = port.read(1, 10.0)
    if r != b"U":
        return None, "no U (got %r)" % r
    d = port.read(16, 1.0)
    if len(d) != 16:
        return None, "short reply %r" % d
    return [int.from_bytes(d[i:i + 4], "big") for i in (0, 4, 8, 12)], ""


def run(port, meta, mhz):
    period = 1000.0 / mhz
    a, b = meta["operands"]
    lines, bad, data = [], 0, dict(phases=[], streams=[], mhz=mhz, when=datetime.datetime.now().isoformat(timespec="seconds"))
    lines.append("mutability test 2 -- same bitstream; carrier configured ONLY by the command cell; clock %.1f MHz (%.2f ns/clock)" % (mhz, period))
    for i, p in enumerate(meta["phases"]):
        words = [int(x, 16) for x in p["words_hex"]]
        clk, why = reprogram(port, words)
        if p["kind"] == "d":
            v, lat, why2 = single(port, a, b)
            ok = clk is not None and v == p["expected"]
            bad += 0 if ok else 1
            lines.append("phase %d  %-24s reprogram %s clk (%s ns)  got %-8s want %08X  latency %s clk (%s ns)  %s" % (
                i, p["label"], clk, ("%.0f" % (clk * period)) if clk is not None else "-", ("%08X" % v) if v is not None else "-", p["expected"],
                lat, ("%.0f" % (lat * period)) if lat is not None else "-", "ok" if ok else "WRONG " + (why or why2)))
            data["phases"].append(dict(i=i, label=p["label"], reprogram_clk=clk, got=v, want=p["expected"], latency_clk=lat, ok=ok))
        else:
            res, why2 = stream(port, meta["seq_cfg"], p["n"])
            ok = clk is not None and res is not None and res[2] == p["first"] and res[3] == p["last"]
            bad += 0 if ok else 1
            if res:
                per = (res[1] - res[0]) / (p["n"] - 1)
                lines.append("stream %d %-14s reprogram %s clk; n=%d  first result at clk %d, n-th at clk %d  -> %.2f clk/result (%.1f ns, %.2f M results/s)  first %08X (want %08X) last %08X (want %08X)  %s" % (
                    i, p["label"], clk, p["n"], res[0], res[1], per, per * period, 1000.0 / (per * period), res[2], p["first"], res[3], p["last"], "ok" if ok else "WRONG"))
                data["streams"].append(dict(i=i, label=p["label"], n=p["n"], first_clk=res[0], total_clk=res[1], clk_per_result=per, first=res[2], last=res[3], ok=ok))
            else:
                lines.append("stream %d %-14s WRONG %s" % (i, p["label"], why or why2))
    lines.append("RESULT: %s" % ("PASS: every reconfiguration came from the command cell and the results followed it" if bad == 0 else "FAIL: %d item(s) wrong" % bad))
    data["pass"] = bad == 0
    text = "\n".join(lines)
    print(text)
    open(os.path.join(HERE, "mutability2_results.txt"), "w").write(text + "\n")
    json.dump(data, open(os.path.join(HERE, "mutability2_results.json"), "w"), indent=1)
    return 0 if bad == 0 else 1


class FakeBoard:
    """Software model of the serial protocol only (it replays the expected answers); a pass here proves the framing and parsing, nothing about the hardware."""
    def __init__(self, meta):
        self.meta, self.buf, self.rx, self.i = meta, b"", b"", -1

    def write(self, b):
        self.rx += b
        while self.rx:
            if self.rx[:1] == b"W" and len(self.rx) >= 2 and len(self.rx) >= 2 + 4 * self.rx[1]:
                n = self.rx[1]; self.rx = self.rx[2 + 4 * n:]; self.i += 1; self.buf += b"K" + (40).to_bytes(4, "big")
            elif self.rx[:1] == b"D" and len(self.rx) >= 9:
                self.rx = self.rx[9:]; p = self.meta["phases"][self.i]; self.buf += b"R" + p["expected"].to_bytes(4, "big") + (3).to_bytes(4, "big")
            elif self.rx[:1] == b"S" and len(self.rx) >= 11:
                self.rx = self.rx[11:]; p = self.meta["phases"][self.i]; self.buf += b"U" + b"".join(x.to_bytes(4, "big") for x in (6, 258, p["first"], p["last"]))
            else:
                break

    def read(self, n, timeout):
        o, self.buf = self.buf[:n], self.buf[n:]
        return o

    def flush(self):
        self.buf = b""


def main():
    args = sys.argv[1:]
    meta = json.load(open(os.path.join(HERE, "mutability2.json")))
    mhz = float(args[args.index("--mhz") + 1]) if "--mhz" in args else 27.0
    if "--selftest" in args:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            rc = run(FakeBoard(meta), meta, mhz)
        assert rc == 0
        assert wframe([1, 2]) == b"W\x02\x00\x00\x00\x01\x00\x00\x00\x02" and sframe(1, 2) == b"S" + b"\x00" * 7 + b"\x01\x00\x02"
        print("selftest ok: frames and replies parse for all", len(meta["phases"]), "phases")
        os.remove(os.path.join(HERE, "mutability2_results.txt")); os.remove(os.path.join(HERE, "mutability2_results.json"))
        return 0
    path = next((x for i, x in enumerate(args) if not x.startswith("--") and (i == 0 or args[i - 1] != "--mhz")), None)
    if path is None:
        import glob
        c = sorted(glob.glob("/dev/ttyUSB*"), key=lambda s: int("".join(ch for ch in s if ch.isdigit()) or 0))
        path = c[-1] if c else None
    if not path:
        sys.exit("no serial port found; name it: python3 mutability2_host.py COM7   (or /dev/ttyUSB1)")
    port = Port(path)
    port.flush()
    return run(port, meta, mhz)


if __name__ == "__main__":
    sys.exit(main())
