"""Hex-N bank learning curve v1 (new file).  Alan, 21 Oct 2026: run the plain detector bank for a long time (default 8,000 tries) and take a SNAPSHOT every 200 tries, so where the score flattens shows up early and nothing has to be rerun.
Same bank as hexn_bank_v4 with defaults (4 summing cells, all 12 wires, W=2, threshold 0..7, keep-or-undo search, same seeds and data, so the 1,000-try snapshot equals the earlier 1,000-try bank result and the 2,000-try snapshot equals the 2,000-try control).
At every snapshot the CURRENT best design is scored on the 200 fresh test samples (and its training reward noted).  Files: --out PREFIX writes PREFIX_t<tries>.txt ('seed accuracy template-rule', for hexn_ladder_compare_v1.py) and PREFIX_train.txt (seed tries train-reward).
Usage: python3 tools/hexn_bank_curve_v1.py --out /tmp/x [--tries 8000] [--every 200] [--first S] [--runs N] [--noise Q]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
b = load("hexn_bank_v4"); b.CELL = "sum"; b.SEE = "all"; b.M = 1; K = 4; b.WIRES = [b.wires(k) for k in range(K)]
v6, v12 = b.v6, b.v12


def curve(seed, q, tries, every, S, W=2, warm=100):
    rnd = random.Random(seed); tpl = v12.make_templates(rnd, K)
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test); lf = v6.Lfsr(seed + 77); best = None; br = -1; snaps = []
    for _ in range(warm):
        c = [b.new_cfg(lf) for _ in range(K)]; r = b.rewards(c, train, W)
        if r > br: best, br = c, r
    cur, cr = best, br
    for n in range(warm, tries + 1):
        if n % every == 0 or n == warm: snaps.append((n, b.accuracy(cur, test, W), cr))
        if n == tries: break
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(K); nxt[j] = b.mutate(nxt[j], lf)
        r = b.rewards(nxt, train, W)
        if r >= cr: cur, cr = nxt, r
    return snaps, v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--noise", type=float, default=0.15); ap.add_argument("--tries", type=int, default=8000); ap.add_argument("--every", type=int, default=200)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--per-class", type=int, default=16); a = ap.parse_args()
    for s in range(a.first, a.first + a.runs):
        snaps, tr = curve(s, a.noise, a.tries, a.every, a.per_class)
        for n, acc, cr in snaps:
            with open(f"{a.out}_t{n}.txt", "a") as f: f.write(f"{s:>4} {acc:>8.2f} {tr:>13.2f}\n")
            with open(f"{a.out}_train.txt", "a") as f: f.write(f"{s} {n} {cr}\n")
        print(f"seed {s}: " + "  ".join(f"{n}:{acc:.2f}" for n, acc, _ in snaps if n % 1000 == 0), flush=True)
