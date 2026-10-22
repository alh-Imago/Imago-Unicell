"""Simulation check of the WRITE RULE v2 through the board top v11 (like hexn_mem_check_v1.py): record the commands of the five policies (decisions from the Python rules), run them in the testbench, replay the testbench's answers through the same policies and compare every one.
Usage: python3 tools/hexn_mem_write_check_v2.py [SEEDS]"""
import sys, os, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_mem_write_v2 as W
from hexn_mem_check_v1 import Replay
class RecRef(W.RefLink):
    def __init__(self, lines): super().__init__(); self.lines = lines
    def write(self, b): self.lines += ["S %02x" % x for x in b]; super().write(b)
    def read(self, n): self.lines.append("R %d" % n); return super().read(n)
def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1; lines = []; plan = [(p, s) for p in W.POLICIES.values() for s in range(1, n + 1)]
    for p, s in plan: W.run(RecRef(lines), p, s)
    dd = tempfile.mkdtemp(); fn = os.path.join(dd, "script.txt"); open(fn, "w").write("\n".join(lines) + "\n")
    src = open(os.path.join(ROOT, "tools/hexn_mem_check_v1.py")).read().split("src = ")[1].split("\n")[0]
    src = eval(src); 
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(dd, "s.vvp"), "-DTOP=hexn_tang_top_v11", "-DLATMOD=hexn_lattice_hex7_v14", "-DNCLS=7", "-DNCELL=1", "-DCLKDIV=8"] + [os.path.join(ROOT, x) for x in src], check=True, capture_output=True)
    out = subprocess.run(["vvp", "-n", os.path.join(dd, "s.vvp"), "+script=" + fn], capture_output=True, text=True).stdout
    rep = Replay([[int(x, 16) for x in l.split()[1:]] for l in out.splitlines() if l.startswith("R")])
    bad = checks = 0
    for p, s in plan: r = W.run(rep, p, s); bad += r["bad"]; checks += r["checks"]
    print("simulation through the top: answers that differ from the Python rules: %d of %d" % (bad, checks)); sys.exit(0 if bad == 0 else 1)
if __name__ == "__main__": main()
