#!/usr/bin/env python3
"""saveload_host_v2.py -- ledger #1099 (v2 of saveload_host.py: a reply that is not the expected byte is retried after flushing, and --probe prints the raw bytes of a few frames; the framing and results are unchanged): talks to the Tang Nano 20K running saveload.fs (the looped CORDIC on the flex cells with a self-stop). The bitstream NEVER changes.

  python3 saveload_host_v2.py [PORT] --sanity                     the four short checks (back pressure, freeze, freeze with the word inside the grid, save / fresh card / load) at 3 + 3 steps
  python3 saveload_host_v2.py [PORT] --state tang_state.json --steps 300 [--label A] [--mode 3]
                                                               reset the card, load the word from the VM's save (made with flex_tang_bridge_v1.py make-state), let the card run --steps results by
                                                               itself and stop, read the word and counters, write tang_result_<label>.json  (pass that file back)
  python3 saveload_host_v2.py [PORT] --from-zero --steps 300 [--label Z]     the same, starting from the loop's first value (50000) instead of a VM state
  python3 saveload_host_v2.py --selftest                          no board: checks the frames against a software model of the card

The card stops ITSELF at the programmed step count and raises `stopped`; this script only reads it afterwards, so serial speed does not matter. mode: 1 = back pressure, 2 = freeze,
3 = both. All counters are counted on the card. Serial protocol (115200 8N1): 'X' reset; 'C' mode N(2) dly lag configure; 'L' word(4) load; 'G' release; 'Q' query -> 'Q' flags steps(2) word(4) run_clocks(4);
flags bit0 stopped, bit1 busy (a grid cell still holds a word), bit2 held_valid.  Needs pyserial (pip install pyserial) except on Linux/macOS.
"""
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
Z0 = 50000
KS = (45000, 26565, 14036, 7125)
DRIFT = 1237


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >> 31 else v


def step_fn(z):
    """one pass round the loop (the independent definition used to check the card)"""
    for k in KS:
        z = s32(z - k if z > 0 else z + k)
    return s32(z + DRIFT)


def model(n, z=Z0):
    out = []
    for _ in range(n):
        z = step_fn(z)
        out.append(z)
    return out


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


RETRIES = []


def cmd(port, frame):
    for attempt in range(3):
        port.write(frame)
        k = port.read(1, 2.0)
        if k == b"K":
            return
        RETRIES.append((frame[:1], k))                       # remembered and printed at the end: a retry is not hidden
        time.sleep(0.3)
        port.flush()
    raise RuntimeError("no K for frame %r after 3 tries (got %r)" % (frame[:1], k))


def X(p): cmd(p, b"X"); time.sleep(0.05)
def C(p, mode, n, dly=4, lag=0): cmd(p, b"C" + bytes([mode, n >> 8, n & 255, dly, lag]))
def L(p, word): cmd(p, b"L" + (word & 0xFFFFFFFF).to_bytes(4, "big"))
def G(p): cmd(p, b"G")


def Q(p):
    p.write(b"Q")
    r = p.read(12, 1.0)
    if len(r) != 12 or r[:1] != b"Q":
        raise RuntimeError("bad query reply %r" % r)
    fl = r[1]
    return dict(stopped=fl & 1, busy=(fl >> 1) & 1, held_valid=(fl >> 2) & 1, steps=int.from_bytes(r[2:4], "big"), word=int.from_bytes(r[4:8], "big"),
                run_clocks=int.from_bytes(r[8:12], "big"), raw=r.hex())


def wait_stop(p, steps, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        q = Q(p)
        if q["stopped"] and q["steps"] == steps:
            return q
        time.sleep(0.01)
    raise RuntimeError("the card did not stop at step %d within %.0f s (last: %s)" % (steps, timeout, q))


def expect(label, q, **want):
    bad = [k for k, v in want.items() if (q[k] & 0xFFFFFFFF if k == "word" else q[k]) != (v & 0xFFFFFFFF if k == "word" else v)]
    print("  %s %-34s stopped=%d busy=%d held_valid=%d steps=%-4d word=%-11d run_clocks=%d" % ("ok  " if not bad else "WRONG", label, q["stopped"], q["busy"], q["held_valid"], q["steps"], s32(q["word"]), q["run_clocks"]),
          "" if not bad else "  (wrong: %s, wanted %s)" % (bad, want))
    return not bad


def sanity(p, k1=3, k2=3):
    m = model(k1 + k2 + 2)
    ok = True
    print("S1 back pressure")
    X(p); C(p, 1, k1); L(p, Z0); q = wait_stop(p, k1); ok &= expect("stop at %d" % k1, q, stopped=1, busy=0, held_valid=1, steps=k1, word=m[k1 - 1])
    C(p, 1, k2); G(p); q = wait_stop(p, k1 + k2); ok &= expect("release, stop at %d" % (k1 + k2), q, stopped=1, busy=0, held_valid=1, steps=k1 + k2, word=m[k1 + k2 - 1])
    print("S2 freeze")
    X(p); C(p, 2, k1); L(p, Z0); q = wait_stop(p, k1); ok &= expect("stop at %d" % k1, q, stopped=1, busy=0, held_valid=1, steps=k1, word=m[k1 - 1])
    C(p, 2, k2); G(p); q = wait_stop(p, k1 + k2); ok &= expect("release, stop at %d" % (k1 + k2), q, stopped=1, busy=0, held_valid=1, steps=k1 + k2, word=m[k1 + k2 - 1])
    print("S3 freeze with the word inside the grid, then resume")
    X(p); C(p, 2, k1, 0, 12); L(p, Z0); q = wait_stop(p, k1); ok &= expect("frozen mid-flight at %d" % k1, q, stopped=1, busy=1, held_valid=0, steps=k1)
    C(p, 2, k2, 0, 12); G(p); q = wait_stop(p, k1 + k2); ok &= expect("released, frozen again at %d" % (k1 + k2), q, stopped=1, busy=1, held_valid=0, steps=k1 + k2)
    C(p, 2, 1, 4, 0); G(p); q = wait_stop(p, k1 + k2 + 1); ok &= expect("released, one more step", q, stopped=1, busy=0, held_valid=1, steps=k1 + k2 + 1, word=m[k1 + k2])
    print("S4 save, fresh card, load, run on")
    X(p); C(p, 3, k1); L(p, Z0); q = wait_stop(p, k1); ok &= expect("run to %d (this is the save)" % k1, q, stopped=1, busy=0, held_valid=1, steps=k1, word=m[k1 - 1])
    saved = q["word"]
    X(p); C(p, 3, k2); L(p, saved); q = wait_stop(p, k2); ok &= expect("fresh card, loaded, run %d more" % k2, q, stopped=1, busy=0, held_valid=1, steps=k2, word=m[k1 + k2 - 1])
    return ok


def run_from(p, word, from_step, steps, mode, label, source):
    X(p); C(p, mode, steps); L(p, word)
    t0 = time.time()
    q = wait_stop(p, steps, timeout=30.0)
    q2 = Q(p)                                    # read again: a stopped card must stay as it is
    res = dict(label=label, source=source, from_step=from_step, ran=steps, final_step=from_step + steps, mode=mode, word=q["word"], word_signed=s32(q["word"]),
               steps_counter=q["steps"], run_clocks=q["run_clocks"], busy=q["busy"], held_valid=q["held_valid"], stable_on_second_read=(q2["word"], q2["steps"], q2["busy"]) == (q["word"], q["steps"], q["busy"]),
               model_word=model(steps, word)[-1] & 0xFFFFFFFF, raw=q["raw"], when=datetime.datetime.now().isoformat(timespec="seconds"))
    res["matches_model"] = res["word"] == res["model_word"]
    fn = os.path.join(HERE, "tang_result_%s.json" % label)
    json.dump(res, open(fn, "w"), indent=1)
    print("loaded word %d (step %d), card ran %d steps by itself in %d clocks (%.1f us at 27 MHz) and stopped" % (s32(word), from_step, steps, q["run_clocks"], q["run_clocks"] / 27.0))
    print("result word %d at step %d; Python model says %d: %s; wrote %s" % (s32(q["word"]), from_step + steps, s32(res["model_word"]), "match" if res["matches_model"] else "MISMATCH", fn))
    return res["matches_model"] and res["stable_on_second_read"] and not q["busy"]


# ---- a software model of the card's serial protocol (frames and replies only; it computes the loop with the definition above)
class FakeBoard:
    def __init__(self):
        self.buf = b""; self.rx = b""; self.reset()

    def reset(self):
        self.steps = 0; self.word = 0; self.valid = 0; self.n = 0; self.mode = 1; self.stopped = 0; self.run = 0

    def write(self, b):
        self.rx += b
        while self.rx:
            c = self.rx[:1]
            if c == b"X": self.reset(); self.buf += b"K"; self.rx = self.rx[1:]
            elif c == b"C" and len(self.rx) >= 6: self.mode, self.n = self.rx[1], int.from_bytes(self.rx[2:4], "big"); self.buf += b"K"; self.rx = self.rx[6:]
            elif c == b"L" and len(self.rx) >= 5:
                self.word = int.from_bytes(self.rx[1:5], "big"); self.valid = 1; self.buf += b"K"; self.rx = self.rx[5:]
                self.advance()
            elif c == b"G": self.buf += b"K"; self.rx = self.rx[1:]; self.advance()
            elif c == b"Q":
                self.rx = self.rx[1:]
                self.buf += b"Q" + bytes([self.stopped | (self.valid << 2)]) + self.steps.to_bytes(2, "big") + (self.word & 0xFFFFFFFF).to_bytes(4, "big") + self.run.to_bytes(4, "big")
            else: break

    def advance(self):
        w = s32(self.word)
        for _ in range(self.n):
            w = step_fn(w); self.steps += 1; self.run += 46
        self.word = w & 0xFFFFFFFF; self.stopped = 1

    def read(self, n, timeout):
        o, self.buf = self.buf[:n], self.buf[n:]
        return o

    def flush(self):
        self.buf = b""


def main():
    a = sys.argv[1:]
    opt = lambda n, d=None: a[a.index(n) + 1] if n in a else d
    if "--selftest" in a:
        fb = FakeBoard()
        X(fb); C(fb, 3, 5); L(fb, Z0); q = wait_stop(fb, 5)
        assert q["stopped"] == 1 and q["steps"] == 5 and s32(q["word"]) == model(5)[-1], q
        assert run_from(fb, model(7)[-1], 7, 4, 3, "selftest", "selftest")
        os.remove(os.path.join(HERE, "tang_result_selftest.json"))
        print("selftest ok: frames and replies parse; a loaded word runs on to the model's value")
        return 0
    port_path = next((x for x in a if not x.startswith("--") and (a.index(x) == 0 or a[a.index(x) - 1] not in ("--state", "--steps", "--label", "--mode"))), None)
    if port_path is None:
        import glob
        c = sorted(glob.glob("/dev/ttyUSB*"), key=lambda s: int("".join(ch for ch in s if ch.isdigit()) or 0))
        port_path = c[-1] if c else None
    if not port_path:
        sys.exit("no serial port found; name it: python3 saveload_host_v2.py COM7   (or /dev/ttyUSB1)")
    p = Port(port_path)
    p.flush()
    if "--probe" in a:
        for name, fr, n in (("X", b"X", 1), ("Q", b"Q", 12), ("X", b"X", 1), ("Q", b"Q", 12)):
            p.write(fr)
            r = p.read(n, 1.0)
            print("sent %s -> %d bytes: %s" % (name, len(r), r.hex(" ")))
            time.sleep(0.2)
        return 0
    if "--sanity" in a:
        ok = sanity(p)
        if RETRIES:
            print("NOTE: %d frame(s) needed a retry: %s" % (len(RETRIES), RETRIES))
        print("RESULT: %s" % ("PASS: back pressure, freeze, freeze with the word inside the grid, and save / fresh card / load all behaved" if ok else "FAIL"))
        return 0 if ok else 1
    steps = int(opt("--steps", "300")); label = opt("--label", "run"); mode = int(opt("--mode", "3"))
    if "--state" in a:
        st = json.load(open(opt("--state")))
        ok = run_from(p, st["word"], st["step"], steps, mode, label, "state file %s (%s)" % (opt("--state"), st.get("design_hash", "")[:12]))
    elif "--from-zero" in a:
        ok = run_from(p, Z0, 0, steps, mode, label, "first value %d" % Z0)
    else:
        print(__doc__)
        return 2
    if RETRIES:
        print("NOTE: %d frame(s) needed a retry: %s" % (len(RETRIES), RETRIES))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
