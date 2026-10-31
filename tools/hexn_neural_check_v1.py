"""hexn_neural_check_v1: bit-true check of rtl/hexn_neural_v1.v against tools/hexn_layer1_int_v4.py (OnlineInt4, the bias-corrected rule) on random positions (31 Oct 2026). Needs iverilog.
Stimulus: weights preloaded (hand or random), then 600 commands: evaluations and learning steps (teacher random in -1..1, doubled step on 1 in 4) on boards from random play. Every output and every weight after each command must equal the Python model. Run for WB 14 and 10.
Usage: python3 tools/hexn_neural_check_v1.py [WB ...]"""
import os, sys, random, subprocess, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_layer1_int_v1 as I, hexn_layer1_int_v4 as I4
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def board(rnd):
    b = C.new()
    for k in range(rnd.randint(3, 36)):
        l = C.legal(b)
        if not l: break
        C.drop(b, rnd.choice(l), 1 if k % 2 == 0 else 2)
    return b
def run(WB, seed=1, n=600):
    rnd = random.Random(seed); j = I4.OnlineInt4("hand" if seed % 2 else "blank", "TD", WB); words = []; exp = []
    for i in range(7): words.append((2 << 62) | ((j.W[i] & 0xFFFF) << 35) | (i << 5)); exp.append(None)
    words.append((2 << 62) | ((j.Bq & 0xFFFF) << 35) | (7 << 5))
    for _ in range(n):
        b = board(rnd); x = I.xint(b); xp = sum(v << (6 * i) for i, v in enumerate(x))
        if rnd.random() < 0.4: words.append((0 << 62) | (xp << 9)); exp.append(("e", b, None, 1))
        else:
            tq = rnd.randint(-256, 256); m = 2 if rnd.random() < 0.25 else 1
            words.append((1 << 62) | ((1 if m == 2 else 0) << 61) | ((tq & 0x3FF) << 51) | (xp << 9)); exp.append(("l", b, tq, m))
    d = tempfile.mkdtemp()
    open(os.path.join(d, "stim.hex"), "w").write("\n".join("%016x" % w for w in words) + "\n")
    subprocess.check_call(["iverilog", "-g2012", "-P", "tb_hexn_neural_v1.WB=%d" % WB, "-o", os.path.join(d, "sim"), os.path.join(ROOT, "rtl/tb_hexn_neural_v1.v"), os.path.join(ROOT, "rtl/hexn_neural_v1.v"), os.path.join(ROOT, "rtl/hexn_tanh512_v1.v")])
    subprocess.check_call(["vvp", "sim", "+N=%d" % len(words)], cwd=d, stdout=subprocess.DEVNULL)
    got = [l.split() for l in open(os.path.join(d, "neural_out.txt"))]; shutil.rmtree(d)
    bad = 0; gi = 8
    for e in exp[7:]:
        kind, b, tq, m = e; x = I.xint(b); o = j.out(x)
        if kind == "l":
            # same update as OnlineInt.update with t given in Q8 (round(t*256) is tq)
            j.update(b, tq / 256.0, m)
        g = got[gi]; gi += 1; y = int(g[1]); w = [int(v) for v in g[2:]]
        if y != o or w != j.W + [j.Bq]: bad += 1
        if bad == 1 and (y != o or w != j.W + [j.Bq]): print("first mismatch at command", gi - 9, "rtl", y, w, "model", o, j.W, j.Bq)
    return bad, len(exp) - 7, j.amax, j.wmax
if __name__ == "__main__":
    for WB in [int(a) for a in sys.argv[1:]] or [14, 10]:
        for seed in (1, 2):
            bad, n, am, wm = run(WB, seed); print("WB %d seed %d: %d commands, %d mismatches (max |acc| %d, max |W| %d)" % (WB, seed, n, bad, am, wm))
