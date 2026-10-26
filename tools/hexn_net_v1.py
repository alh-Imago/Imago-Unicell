"""hexn_net_v1: does a signal get through a LINE of cells at all? (Python model only; new file; hexn_network_v7/v8 untouched and still withdrawn.)
Cell = the v2 cell model (tools/hexn_cell_v2_model.py, MixCell: every face feeds ONE decision, Alan's choice of 20 Oct). ASSUMPTION to check: the RTL cell used in the bank (hexn_cell_v5) behaves as that model; the v2 model header says 'no RTL yet', so this is not verified here.
Wiring (as v7/v8): cell i face 0 lane q  <->  cell i+1 face 3 lane q, BOTH directions (each end hears the other end's tx), same clock. Cell 0 is driven from outside on faces 1, 2, 4, 5 (and face 3).
Gate before any learning: random cells from a signal-passing family; run the line with a WEAK and a STRONG external stimulus (per-lane per-clock chance d_low / d_high); the network 'passes information' when the last cell's output
(total clocks high over the last 4 windows, all lanes) is DIFFERENT for the two stimuli; it 'is stuck' when the output is the same (including all zero or all saturated). Reported per line length K."""
import sys, os, random, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("cm", os.path.join(ROOT, "tools", "hexn_cell_v2_model.py")); cm = importlib.util.module_from_spec(sp); sp.loader.exec_module(cm)
F, P, N, AW = cm.F, cm.P, cm.N, cm.AW; PL = 10
FACE0 = range(0, P); FACE3 = range(3 * P, 4 * P)
def rand_cell(rnd, thr_max):
    act = [int(rnd.random() < 0.9) for _ in range(N)]; dr = [0] * N; code = [rnd.choice((0, 1, 1, 2, 2)) for _ in range(N)]
    for i in FACE0: act[i] = 1; dr[i] = rnd.choice((1, 1, 1, 3))      # sends forward (3 = send forward, receive feedback)
    for i in FACE3: act[i] = 1; dr[i] = rnd.choice((0, 0, 0, 2))      # receives forward (2 = receive forward, send feedback)
    return (act, dr, code, [rnd.randint(1, thr_max)] * F, 0)
def run(cells, d, windows, rnd):
    K = len(cells); cs = [cm.MixCell(*c) for c in cells]; total = [0] * windows; ext_lanes = [i for i in range(N) if i not in FACE0]
    for w in range(windows):
        for phase in (0, 1):
            for t in range(PL):
                ps, we = int(t == 0), int(phase == 1 and t == PL - 1)
                tx = [c.tx(phase) for c in cs]
                for k in range(K):
                    rx = [0] * N
                    if k == 0:
                        for i in ext_lanes: rx[i] = int(rnd.random() < d)
                    if k > 0:
                        for q in range(P): rx[3 * P + q] |= tx[k - 1][q]                 # from the cell before: its face 0 -> my face 3
                    if k < K - 1:
                        for q in range(P): rx[q] |= tx[k + 1][3 * P + q]                 # from the cell after: its face 3 -> my face 0
                    cs[k].clock(rx, phase, ps, we)
                total[w] += sum(tx[K - 1])
    return total
def trial(seed, K, thr_max, d_low, d_high):
    rnd = random.Random(seed); cells = [rand_cell(rnd, thr_max) for _ in range(K)]; W = K + 4
    lo = run(cells, d_low, W, random.Random(seed + 1)); hi = run(cells, d_high, W, random.Random(seed + 2))
    a, b = sum(lo[-4:]), sum(hi[-4:]); return a, b
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100; thr_max = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    d_low, d_high = 0.03, 0.15
    print(f"{n} random lines per length; cell thresholds 1..{thr_max}; external chance per lane per clock: weak {d_low}, strong {d_high}")
    print("K | passes information (output differs) | stronger input gives MORE output | stuck at zero (both) | stuck equal and nonzero | mean output weak / strong")
    for K in (1, 2, 3, 4, 6, 8):
        r = [trial(s, K, thr_max, d_low, d_high) for s in range(n)]
        diff = sum(a != b for a, b in r); more = sum(b > a for a, b in r); zero = sum(a == 0 and b == 0 for a, b in r); eq = sum(a == b and a > 0 for a, b in r)
        print(f"{K} | {diff/n:.2f} | {more/n:.2f} | {zero/n:.2f} | {eq/n:.2f} | {sum(a for a, b in r)/n:.1f} / {sum(b for a, b in r)/n:.1f}")
