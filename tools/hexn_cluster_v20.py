"""Hex-N cluster v20 (new file): the FROZEN-MODEL test (Alan, 20 Oct 2026).  Train the cluster on data with --train-noise (default 0 = clean), FREEZE it, then test it on fresh samples at several noise levels (--test-noises),
with and without run-time adaptation.  'Adapt' = the threshold offset (--M, --run) starts at 0 and moves during the test stream; 'frozen' = M 0 at test time (the plain cell).
The search itself (warm start, keep-or-undo, v19 flags such as --score) is v19's; training always uses M 0 unless --train-M is given, so the adaptation is only ever tested on a model it was not trained with.
Output per seed: accuracy at each test noise, frozen and adapted, and the template-rule ceiling at that noise.
Usage: python3 tools/hexn_cluster_v20.py [--train-noise Q] [--test-noises 0,0.05,0.15,0.25] [--M 2 --run 3] [--score] [--first S] [--runs N] [--tries T]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("hexn_cluster_v19", os.path.join(ROOT, "tools", "hexn_cluster_v19.py"))
v19 = importlib.util.module_from_spec(sp); sp.loader.exec_module(v19)
c15 = v19.c15


def train(seed, R, q, tries, S, trainM, run, warm=100):
    topo = c15.Topo(R); rnd = random.Random(seed); tpl = c15.v12.make_templates(rnd, 4)
    tr = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(S)]
    random.Random(seed + 5).shuffle(tr)
    lf = c15.v6.Lfsr(seed + 77); n = len(topo.cells); best = None; br = -1
    for _ in range(warm):
        c = [c15.easy(lf) for _ in range(n)]; r, st = v19.rewards(topo, c, tr, trainM, run)
        if r > br: best, br, bst = c, r, st
    cur, cr, cst = best, br, bst
    for t in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            if v19.FLAGS["aim"] and cst and lf.randrange(2):
                cand = sorted({ci for k in cst for (ci, _) in topo.outputs[k]}); j = cand[lf.randrange(len(cand))]
            else: j = lf.randrange(n)
            nxt[j] = v19.mutate(nxt[j], lf)
        r, st = v19.rewards(topo, nxt, tr, trainM, run)
        if r >= cr: cur, cr, cst = nxt, r, st
    return topo, tpl, cur


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--radius", type=int, default=1); ap.add_argument("--train-noise", type=float, default=0.0)
    ap.add_argument("--test-noises", default="0,0.05,0.15,0.25"); ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--tries", type=int, default=600); ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--M", type=int, default=2); ap.add_argument("--run", type=int, default=3)
    ap.add_argument("--train-M", type=int, default=0)
    for f in v19.FLAGS: ap.add_argument("--" + f, action="store_true")
    a = ap.parse_args()
    for f in v19.FLAGS: v19.FLAGS[f] = getattr(a, f)
    nz = [float(x) for x in a.test_noises.split(",")]
    print(f"v20 frozen-model test: trained at noise {a.train_noise}, train M {a.train_M}, adaptation M={a.M} run={a.run}, flags {[f for f in v19.FLAGS if v19.FLAGS[f]]}, {a.tries} tries")
    print("seed noise frozen adapted ceiling")
    for s in range(a.first, a.first + a.runs):
        topo, tpl, cur = train(s, a.radius, a.train_noise, a.tries, a.per_class, a.train_M, a.run)
        for q in nz:
            rnd = random.Random(1000 * s + int(q * 100) + 7)
            test = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(50)]; random.Random(s + 11).shuffle(test)
            fz = v19.accuracy(topo, cur, test, 0, a.run); ad = v19.accuracy(topo, cur, test, a.M, a.run); ce = c15.v12.template_rule(tpl, test)
            print(f"{s:>4} {q:>5} {fz:>6.2f} {ad:>7.2f} {ce:>7.2f}", flush=True)
