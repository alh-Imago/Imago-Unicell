#!/usr/bin/env python3
"""hexn_host_v1.py - talk to a Hex-N card (hexn_frame_v1 over its UART) from the PC (3 Nov 2026, Alan 13:55). Needs pyserial.
  python3 tools/hexn_host_v1.py ports                       find which /dev/ttyUSB* / ttyACM* answers the identify command (115200 8N1)
  python3 tools/hexn_host_v1.py id   --port /dev/ttyUSB1    identify: pattern id and rows
  python3 tools/hexn_host_v1.py wipe --port P               wipe (the card holds clear for 160 clocks)
  python3 tools/hexn_host_v1.py run  --port P --ref REF.json --unit UNIT.json --set x=5 --set y=6 [--no-wipe]
        checks the unit against the card's pattern id, wipes, loads the program, presents the PARALLEL words, reads the log of output words with their ticks, and (default) compares with the serial VM:
        words must be equal and every tick = the VM's tick + 32 (the offset measured in simulation).
The byte layouts are those of sub/verilog/hexn_frame_v1.v (same as tools/hexn_card_sim_v1.py). Nothing here changes the card's flash."""
import argparse, glob, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
OFFSET = 32


def cmd_id(): return b"I"
def cmd_wipe(): return b"W"
def cmd_cfg(image): return b"B" + bytes(image)
def cmd_data(row, word): return b"D" + bytes([row]) + (word & 0xFFFFFFFF).to_bytes(4, "little")
def cmd_go(mask): return b"G" + bytes([mask])
def cmd_log(): return b"L"


def parse_id(b):
    if len(b) != 5: raise ValueError("identify reply has %d bytes, wanted 5" % len(b))
    return dict(pattern_id=int.from_bytes(b[:4], "little"), rows=b[4])


def parse_log(b):
    n = b[0]
    if len(b) != 1 + 7 * n: raise ValueError("log reply has %d bytes for %d entries" % (len(b), n))
    return [(b[1 + 7 * i], int.from_bytes(b[2 + 7 * i:6 + 7 * i], "little"), int.from_bytes(b[6 + 7 * i:8 + 7 * i], "little")) for i in range(n)]


class Card:
    def __init__(self, port, baud=115200, timeout=2.0):
        import serial
        self.s = serial.Serial(port, baud, timeout=timeout)
        self.s.reset_input_buffer()

    def read(self, n, what):
        b = self.s.read(n)
        if len(b) != n: raise TimeoutError("%s: wanted %d bytes, got %d (%r)" % (what, n, len(b), b))
        return b

    def ident(self): self.s.write(cmd_id()); return parse_id(self.read(5, "identify"))
    def wipe(self): self.s.write(cmd_wipe()); self._k("wipe")
    def load(self, image):
        self.s.write(cmd_cfg(image)); self._k("config chain")
    def put(self, row, word): self.s.write(cmd_data(row, word)); self._k("data")
    def go(self, mask): self.s.write(cmd_go(mask)); self._k("go")
    def log(self):
        self.s.write(cmd_log()); n = self.read(1, "log count")[0]
        return parse_log(bytes([n]) + (self.read(7 * n, "log entries") if n else b""))
    def _k(self, what):
        b = self.read(1, what)
        if b != b"K": raise RuntimeError("%s: expected 'K', got %r" % (what, b))


def candidate_ports():
    return sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0]); ap.add_argument("cmd", choices=["ports", "id", "wipe", "run"]); ap.add_argument("--port")
    ap.add_argument("--ref"); ap.add_argument("--unit"); ap.add_argument("--set", action="append", default=[]); ap.add_argument("--no-wipe", action="store_true"); ap.add_argument("--no-compare", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "ports":
        for p in candidate_ports():
            try: r = Card(p, timeout=0.5).ident(); print("%s: ANSWERS  pattern id %08X, rows %d" % (p, r["pattern_id"], r["rows"]))
            except Exception as e: print("%s: no answer (%s)" % (p, str(e)[:60]))
        return 0
    if not a.port: sys.exit("give --port (try: ports)")
    c = Card(a.port)
    if a.cmd == "id": r = c.ident(); print("pattern id %08X, rows %d" % (r["pattern_id"], r["rows"])); return 0
    if a.cmd == "wipe": c.wipe(); print("wiped"); return 0
    import hexn_assemble_v2 as A, hexn_icm_export_v3 as X
    if not (a.ref and a.unit and a.set): sys.exit("run needs --ref, --unit and at least one --set name=value")
    ref = json.load(open(a.ref)); unit = json.load(open(a.unit)); pr = A.check_unit_for(ref, unit)
    if pr: sys.exit("refused: " + "; ".join(pr))
    r = c.ident()
    if r["pattern_id"] != ref["pattern_id"]: sys.exit("the card holds pattern %08X, this unit is for %08X: load the right bitstream first" % (r["pattern_id"], ref["pattern_id"]))
    program = X.from_icm(unit["program"]); vals = {k: int(v, 0) for k, v in (s.split("=", 1) for s in a.set)}
    miss = set(program["pads_in"]) - set(vals)
    if miss: sys.exit("no value for input(s): %s" % ", ".join(sorted(miss)))
    if not a.no_wipe: c.wipe()
    c.load(A.chain_image(ref, program))
    for n in program["pads_in"]: c.put(program["pads_in"][n][0], vals[n])
    c.go(sum(1 << program["pads_in"][n][0] for n in program["pads_in"])); time.sleep(0.3)
    log = c.log(); rows = {v[0]: k for k, v in program["pads_out"].items()}
    for row, word, tick in log: print("output %-8s row %d  word %d (0x%08x)  tick %d" % (rows.get(row, "?"), row, word, word, tick))
    if a.no_compare: return 0
    import hexn_vm_v4 as VM
    cap = VM.SerialVM.load(unit["program"]).run(vals); ok = True
    for name, row in ((k, v[0]) for k, v in program["pads_out"].items()):
        got = [(w, t) for r_, w, t in log if r_ == row]; want = [(w, t + OFFSET) for t, w in cap[name]]
        same = got == want; ok &= same
        print("%s: card %s the serial VM" % (name, "MATCHES" if same else "DIFFERS FROM")); 
        if not same: print("   card:", got, "\n   VM  :", want)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
