"""Check of the board top v8 debug commands in simulation (rtl/tb_hexn_dbg_v2.v): replays the recorded reply bytes through the host script's own Board methods and compares them with the Python model. Usage: hexn_dbg_check_v2.py SEED K NB AW RECORDFILE"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_bank_model_v2 as M, hexn_tang_host_v3 as H
seed, K, NB, AW, rec = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
class Replay:
    def __init__(self, data): self.d = list(data)
    def write(self, x): pass
    def read(self, n): out = bytes(self.d[:n]); del self.d[:n]; return out
data = [int(l.split()[1]) for l in open(rec) if l.startswith("B ")]
m = M.make(seed, K, NB, AW, 16, 0.15); b = H.Board(Replay(data), K, NB); mask = H.mask
bits0, y0 = m["train"][0]; ok = True
def chk(name, cond): 
    global ok; ok &= bool(cond); print("%-28s %s" % (name, "ok" if cond else "WRONG"))
dm = b.dump()
chk("DUMP weights (+1 masks)", [d[0] for d in dm] == [sum(1 << j for j in range(NB) if m["wts"][k][j] > 0) for k in range(K)])
chk("DUMP weights (-1 masks)", [d[1] for d in dm] == [sum(1 << j for j in range(NB) if m["wts"][k][j] < 0) for k in range(K)])
chk("DUMP thresholds", [d[2] for d in dm] == m["thr"])
ds = b.dumpsums()
# the test pushes sample 0 through ACCUM once more after training, so its forward totals are added once to the model's sums
ep = list(m["sump"]); en = list(m["sumn"])
for k in range(K):
    net = sum(m["wts"][k][j] * bits0[j] for j in range(NB)); f = 0 if net <= 0 else min(10 * net, (1 << AW) - 1)
    if k == y0: ep[k] += f
    else: en[k] += f
chk("DUMPSUMS own-class sums", [s[0] for s in ds] == ep); chk("DUMPSUMS other-class sums", [s[1] for s in ds] == en)
eb, el, et = b.echo(); chk("ECHO bits, label, T", (eb, el, et) == (mask(bits0), y0, m["T"]))
pr = b.probe(); exp = []
for k in range(K):
    net = sum(m["wts"][k][j] * bits0[j] for j in range(NB)); exp.append((net, 0 if net <= 0 else min(10 * net, (1 << AW) - 1)))
chk("PROBE net / forward total", [(a, c) for a, c in pr] == exp)
cp, nw = b.cap(); T = m["T"]
chk("CAP write count", nw == K * NB)
chk("CAP counters seen", all((((v & 63) - 64) if (v & 63) > 31 else (v & 63)) == m["cnt"][i // NB][i % NB] for i, v in enumerate(cp)))
chk("CAP weights formed", all(((v >> 7) & 1, (v >> 6) & 1) == (int(m["cnt"][i // NB][i % NB] >= T), int(m["cnt"][i // NB][i % NB] <= -T)) for i, v in enumerate(cp)))
pk = b.peek(); chk("PEEK counters", pk == [m["cnt"][k][j] for k in range(K) for j in range(NB)])
print("ALL DEBUG COMMANDS OK" if ok else "SOME DEBUG COMMAND WRONG")
