"""Probe for the cell-loading command (LOADCELLN 0x11) on a card build with many cells: sends it for every cell number with three kinds of settings and reports which ones the card does not acknowledge with 0xA5. No training needed. Run with the card wrapper (from ~/ypcb-00338-1p1):
  nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/tools/hexn_card_run_v1.py tools/hexn_card_probe_v1.py --ncell 128"""
import sys, argparse, random
ap = argparse.ArgumentParser(); ap.add_argument("--ncell", type=int, required=True); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); a = ap.parse_args()
import serial; link = serial.Serial(a.port, a.baud, timeout=5); r = random.Random(1)
def ack(link):
    try: return link.read(1)[0]
    except Exception as e: return "no answer (%s)" % str(e)[:60]
def show(x): return ("0x%02x" % x) if isinstance(x, int) else x
print("TRACE on a fresh load (expected 0xa5 every time):")
link.write(bytes([1])); print("  CLEAR                 ->", show(ack(link)))
for n in range(3):
    link.write(bytes([0x11, n, 0, 0, 0, 0, 0, 0])); print("  LOADCELLN cell %d      ->" % n, show(ack(link)))
    link.write(bytes([1])); print("  CLEAR after it        ->", show(ack(link)))
link.write(bytes([0x10, 0])); print("  SETLEAK 0             ->", show(ack(link)))
link.write(bytes([1])); print("  CLEAR                 ->", show(ack(link)))
print("FULL PROBE:")
for name, mk in (("threshold 0, lanes all off", lambda n: (0, [0] * 5)), ("threshold 0, lanes random", lambda n: (0, [r.randrange(256) & 0x55 | (r.randrange(256) & 0xAA) for _ in range(5)])), ("threshold random, lanes random", lambda n: (r.randrange(12), [r.randrange(256) for _ in range(5)]))):
    bad = []
    for n in range(a.ncell):
        thr, lanes = mk(n); link.write(bytes([0x11, n, thr] + lanes)); x = ack(link)
        if x != 0xA5:
            bad.append((n, x)); link.reset_input_buffer()
    print("%-34s: %d of %d cells not acknowledged%s" % (name, len(bad), a.ncell, ("; first: " + ", ".join("cell %d -> %s" % (n, ("0x%02x" % x) if isinstance(x, int) else x) for n, x in bad[:8])) if bad else ""))
