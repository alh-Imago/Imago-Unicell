#!/usr/bin/env python3
"""scan_card_host.py (LaTeX-design version) -- ledger #1151 (generalised from the ledger #1147 kit script: the design name, first value and step function come from design.json). Ledger #1147 text: capture the looped CORDIC part-way through its work, on the Tang Nano 20K running scan.fs, save the state, and put it back (into the same card after a reset,
or into a card that has been powered off and loaded again) so it carries on to the same answer.  The bitstream never changes.  Protocol: see tools/board_scan_v1.py (copy in this folder: scan_host.py).

  python3 scan_card_host.py [PORT] --load scan.fs            run the demonstration on the card: for each cut (steps:lag:delay) -> run, freeze mid-flight, capture twice, finish the run (answer A);
                                                             then RESET the card, load the captured state back through checked chunks, read it back, finish the run (answer B). A and B must be the same.
  python3 scan_card_host.py [PORT] --load scan.fs --damage   the same, with deliberate damage on the cable side of the host: a flipped bit in a written chunk, a lost byte, a flipped bit in a received line.
  python3 scan_card_host.py [PORT] --capture-only --out img.json     run to the cut, capture twice, write the image file  (then power the card off if you like)
  python3 scan_card_host.py [PORT] --restore-only --in img.json      reset, load the image back, finish the run, compare with the loop's own model

The serial port is opened BEFORE the bitstream is loaded and kept open (the Tang Nano's USB bridge loses data otherwise: ledger #1133-#1141). Use --load with the .fs file, or load it yourself in another
terminal after this script prints 'port open'. Needs only Python 3 on Linux/macOS (termios); openFPGALoader for --load.
"""
import argparse, datetime, json, os, select, subprocess, sys, time, termios
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan_host as H  # noqa: E402

DESIGN = json.load(open(os.path.join(HERE, "design.json")))
Z0 = DESIGN["z0"]
_STEP = compile(DESIGN["step"], "design.json", "eval")


def step_fn(z):
    return eval(_STEP, {"__builtins__": {}}, {"z": z}) & 0xFFFFFFFF


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >> 31 else v


def model(n, z=Z0):
    out = []
    for _ in range(n):
        z = step_fn(z); out.append(z)
    return out


class SerialLink:
    instant = False

    def __init__(self, path):
        self.path, self.fd = path, None
        self.buf = b""
        self._open(wait=15)

    def _open(self, wait=0):
        t0 = time.time()
        while True:
            try:
                f = os.open(self.path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
                a = termios.tcgetattr(f)
                a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0; a[4] = a[5] = termios.B115200
                a[6][termios.VMIN] = 0; a[6][termios.VTIME] = 0
                termios.tcsetattr(f, termios.TCSANOW, a)
                self.fd = f
                return
            except OSError:
                if time.time() - t0 > wait:
                    raise
                time.sleep(0.1)

    def _pull(self, timeout):
        try:
            r, _, _ = select.select([self.fd], [], [], timeout)
            if r:
                b = os.read(self.fd, 4096)
                self.buf += b
        except OSError:
            try: os.close(self.fd)
            except OSError: pass
            self._open(wait=10)

    def send(self, data):
        for i in range(0, len(data), 16):                     # a few bytes at a time; the card's UART has no buffer
            while True:
                try:
                    os.write(self.fd, data[i:i + 16]); break
                except BlockingIOError:
                    time.sleep(0.002)
                except OSError:
                    self._open(wait=10)
            time.sleep(0.0001)

    def read(self, n, timeout=0.05):
        if not self.buf:
            self._pull(timeout)
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def drain(self):
        self._pull(0.05)
        out, self.buf = self.buf, b""
        return out


def finish_run(card, k2, dly2, lag2, steps_before):
    card.configure(2, k2, dly2, lag2)
    card.go()
    q = card.wait_stopped(timeout=30, steps=steps_before + k2)
    _, img = (card.capture(), card.dump_image())[1]
    return q, img


def one_cut(card, k1, lag, dly, k2=4, dly2=3, lag2=0, log=print):
    r = dict(cut="%d:%d:%d" % (k1, lag, dly))
    card.reset(); time.sleep(0.2)
    card.configure(2, k1, dly, lag); card.load(Z0)
    qa = card.wait_stopped(timeout=30)
    ses, img = card.capture_verified()
    tr = H.parse_trailer(img)
    r.update(steps_at_cut=tr["steps"], word_inside_grid=bool(qa["busy"]), closing_register_holds_word=bool(tr["has"]))
    qA, imgA = finish_run(card, k2, dly2, lag2, tr["steps"])          # the original run, carried on
    card.reset(); time.sleep(0.2)                                       # the card forgets everything
    card.configure(2, k2, dly2, lag2)
    card.restore(ses, img)                                               # state back in (8 checked chunks, applied, read back)
    card.go()
    qB = card.wait_stopped(timeout=30, steps=tr["steps"] + k2)
    _, imgB = (card.capture(), card.dump_image())[1]
    m = model(tr["steps"] + k2 + 1)
    r.update(answer_A=qA["word"], answer_B=qB["word"], model=m[qB["steps"] - 1], steps_end=qB["steps"], held_valid_end=qB["held_valid"],
             same_state=(imgA == imgB), ok=bool(imgA == imgB and qA["word"] == qB["word"] == m[qB["steps"] - 1] and qB["held_valid"]), stats=dict(card.stats))
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("port", nargs="?"); ap.add_argument("--load"); ap.add_argument("--damage", action="store_true")
    ap.add_argument("--cuts", default="3:3:0,4:12:0,5:30:0,3:0:0"); ap.add_argument("--capture-only", action="store_true"); ap.add_argument("--restore-only", action="store_true")
    ap.add_argument("--out"); ap.add_argument("--in", dest="inp"); ap.add_argument("--k2", type=int, default=4)
    a = ap.parse_args()
    port = a.port or sorted(f for f in (os.path.join("/dev", x) for x in os.listdir("/dev")) if "ttyUSB" in f or "ttyACM" in f)[-1]
    link = SerialLink(port)
    print("port open:", port, flush=True)
    if a.load:
        subprocess.run(["openFPGALoader", "-b", "tangnano20k", os.path.join(HERE, a.load) if not os.path.exists(a.load) else a.load], check=True)
        print("loaded; waiting 6 s for the card", flush=True); time.sleep(6)
    link.drain()
    log = lambda *x: print("   note:", *x, flush=True)
    faults = []
    if a.damage:
        faults = [("tx", "W", 3, "flip", 20), ("tx", "W", 6, "drop", 10), ("rx", "D", 4, "flip", 60)]
    lk = H.FaultLink(link, faults) if faults else link
    card = H.Card(lk, retries=4, read_timeout=1.5, log=log, design=DESIGN["name"])
    if a.capture_only or a.restore_only:
        if a.capture_only:
            k1, lag, dly = [int(x) for x in a.cuts.split(",")[0].split(":")]
            card.reset(); time.sleep(0.2); card.configure(2, k1, dly, lag); card.load(Z0)
            card.wait_stopped(30)
            ses, img = card.capture_verified()
            json.dump(dict(ses=ses, image=img.hex(), cut=[k1, lag, dly], design=DESIGN["name"], layout=DESIGN.get("layout"), when=datetime.datetime.now().isoformat()), open(a.out, "w"), indent=1)
            print("captured and written to", a.out, H.parse_trailer(img), card.stats)
            return
        d = json.load(open(a.inp)); img = bytes.fromhex(d["image"]); tr = H.parse_trailer(img)
        if d.get("design") != DESIGN["name"] or d.get("layout") != DESIGN.get("layout"):
            sys.exit("REFUSED: this image is from design %r layout %r, this kit is design %r layout %r" % (d.get("design"), d.get("layout"), DESIGN["name"], DESIGN.get("layout")))
        card.reset(); time.sleep(0.2); card.configure(2, a.k2, 3, 0)
        card.restore(d["ses"], img)
        card.go(); q = card.wait_stopped(30, steps=tr["steps"] + a.k2)
        m = model(tr["steps"] + a.k2 + 1)[q["steps"] - 1]
        print("restored; ran to step %d: word %d, model %d -> %s" % (q["steps"], q["word"], m, "PASS" if q["word"] == m and q["held_valid"] else "FAIL"), card.stats)
        sys.exit(0 if q["word"] == m else 1)
    results = []
    for c in a.cuts.split(","):
        k1, lag, dly = [int(x) for x in c.split(":")]
        r = one_cut(card, k1, lag, dly, a.k2)
        print("%s  cut at step %d (word %s)  A=%d B=%d model=%d  same full state: %s  -> %s  %s" % (r["cut"], r["steps_at_cut"], "inside the grid" if r["word_inside_grid"] else "in the closing register",
              r["answer_A"], r["answer_B"], r["model"], r["same_state"], "PASS" if r["ok"] else "FAIL", r["stats"]), flush=True)
        results.append(r)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    fn = os.path.join(HERE, "results", "scan_%s.json" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    json.dump(dict(results=results, damage=a.damage, injected=getattr(lk, "injected", 0)), open(fn, "w"), indent=1)
    print("written", fn, "| damage injected:", getattr(lk, "injected", 0))
    print("ALL PASS" if all(r["ok"] for r in results) else "SOME FAILED")
    sys.exit(0 if all(r["ok"] for r in results) else 1)


if __name__ == "__main__":
    main()
