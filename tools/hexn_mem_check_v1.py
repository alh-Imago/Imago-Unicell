"""Simulation check of the SAVE AND RECALL block through the board top v11 and its serial commands (rtl/tb_hexn_bytes_v1.v, CLKDIV 8): runs the suite of tools/hexn_mem_host_v1.py in two passes (record the commands, run the testbench, replay its answers) and compares EVERY answer with the Python rules.
Usage: python3 tools/hexn_mem_check_v1.py [TRIES]"""
import sys, os, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_mem_host_v1 as H
class Rec:
    def __init__(self): self.lines = []
    def write(self, b): self.lines += ["S %02x" % x for x in b]
    def read(self, n): self.lines.append("R %d" % n); return bytes(n)
class Replay:
    def __init__(self, replies): self.q = [x for r in replies for x in r]; self.i = 0
    def write(self, b): pass
    def read(self, n): d = bytes(self.q[self.i:self.i + n]); self.i += n; assert len(d) == n, "answer too short"; return d
def main():
    tries = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    rec = Rec(); H.suite(rec, tries); dd = tempfile.mkdtemp(); fn = os.path.join(dd, "script.txt"); open(fn, "w").write("\n".join(rec.lines) + "\n")
    src = ["rtl/tb_hexn_bytes_v1.v", "rtl/hexn_tang_top_v11.v", "rtl/hexn_uart_v1.v", "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_hex7_w18_v14.v", "rtl/hexn_bank_v15.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v4.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(dd, "s.vvp"), "-DTOP=hexn_tang_top_v11", "-DLATMOD=hexn_lattice_hex7_v14", "-DNCLS=7", "-DNCELL=1", "-DCLKDIV=8"] + [os.path.join(ROOT, x) for x in src], check=True, capture_output=True)
    out = subprocess.run(["vvp", "-n", os.path.join(dd, "s.vvp"), "+script=" + fn], capture_output=True, text=True).stdout
    replies = [[int(x, 16) for x in l.split()[1:]] for l in out.splitlines() if l.startswith("R")]
    bad, checks, table, fb = H.suite(Replay(replies), tries)
    H.show(table); print("simulation through the top: answers that differ from the Python rules: %d of %d" % (bad, checks))
    for f in fb: print("  ", f)
    sys.exit(0 if bad == 0 else 1)
if __name__ == "__main__": main()
