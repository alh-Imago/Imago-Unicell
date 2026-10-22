"""Hex-N on the Tang Nano 20K, SAVE AND RECALL test (bitstream from tools/hexn_tang_build_v16.sh, board top v11 with rtl/hexn_mem_v1.v). Runs the suite of tools/hexn_mem_host_v1.py on the real board: 8 objects saved per row, cues watched, recalled; EVERY answer (saved slots read back with DUMP, every RECALL: best slot, matches, known wires, second best, integrated cue, recalled pattern, deviation mask) is compared with the Python copy of the block's rules.
Usage:  python3 tools/hexn_tang_mem_v1.py --port /dev/ttyUSB1 [--tries 150]   |  --selftest (Python stand-in, no board)"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_mem_host_v1 as H
class SerialLink:
    def __init__(self, ser): self.s = ser
    def write(self, b): self.s.write(b)
    def read(self, n):
        d = self.s.read(n)
        if len(d) != n: sys.exit("the board answered %d of %d bytes (is the memory bitstream loaded, and is this the right port?)" % (len(d), n))
        return d
class FakeLink:
    """Stand-in for --selftest: answers from the Python rules (tests the framing and bookkeeping of this script, not the hardware)."""
    def __init__(self): self.m = H.MemRef(); self.out = bytearray()
    def write(self, b):
        c = b[0]
        if c == 0x20: self.m.clr(); self.out.append(0xA5)
        elif c == 0x25: self.m.clrall(); self.out.append(0xA5)
        elif c == 0x21: self.m.watch(b[1] | (b[2] << 8) | (b[3] << 16), b[4] | (b[5] << 8) | (b[6] << 16)); self.out.append(0xA5)
        elif c == 0x22: self.m.save(b[1]); self.out.append(0xA5)
        elif c == 0x23: i, bm, kn, sm, cue, rec, dev = self.m.recall(); self.out += bytes([i, bm, kn, sm] + H.b3(cue) + H.b3(rec) + H.b3(dev))
        elif c == 0x24: v, bits = self.m.dump(b[1]); self.out += bytes([v] + H.b3(bits))
    def read(self, n): d = bytes(self.out[:n]); del self.out[:n]; return d
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--tries", type=int, default=150); ap.add_argument("--selftest", action="store_true"); a = ap.parse_args()
    if a.selftest: link = FakeLink()
    else:
        import serial; ser = serial.Serial(a.port, a.baud, timeout=5); ser.reset_input_buffer(); link = SerialLink(ser)
    bad, checks, table, fb = H.suite(link, a.tries); H.show(table)
    print("board answers that differ from the Python rules: %d of %d" % (bad, checks))
    for f in fb: print("  ", f)
    print("MEMORY TEST PASS" if bad == 0 else "MEMORY TEST FAIL"); sys.exit(0 if bad == 0 else 1)
if __name__ == "__main__": main()
