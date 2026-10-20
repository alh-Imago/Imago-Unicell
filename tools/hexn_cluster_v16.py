"""Hex-N cluster v16 (new file): a LOCAL TEACHER SIGNAL per output group, instead of one reward for the whole cluster (v15).
Same hex patch, same input/output layout, same classes/noise/samples/learner as v15.  The change is only the reward the learner sees:
v15: one 4-bit number (accuracy plus share) for the whole cluster.
v16: one 4-bit number PER output group g ('is group g firing exactly when the sample is class g?', balanced accuracy, 0..15), four numbers in all; a try is kept if their sum is not worse.
This is the feedback-lane idea: each output gets its own comparison with its own goal.  Test accuracy is read the same way as before (the group with the most output clocks wins; ties and silence count as wrong).
Usage: python3 tools/hexn_cluster_v16.py [--radius R] [--noise Q] [--first S] [--runs N] [--tries T] [--per-class S]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("hexn_cluster_v15", os.path.join(ROOT, "tools", "hexn_cluster_v15.py"))
c15 = importlib.util.module_from_spec(sp); sp.loader.exec_module(c15)


def local_rewards(topo, cfgs, data, bits=4):
    pos = [0] * 4; neg = [0] * 4; tp = [0] * 4; tn = [0] * 4
    for b, y in data:
        g = c15.respond(topo, cfgs, b)
        for k in range(4):
            fire = g[k] > 0
            if y == k: pos[k] += 1; tp[k] += fire
            else: neg[k] += 1; tn[k] += (not fire)
    top = (1 << bits) - 1
    return sum(round(top * (tp[k] / pos[k] + tn[k] / neg[k]) / 2) for k in range(4))


def one(seed, R, q, tries, S, warm=100):
    topo = c15.Topo(R); rnd = random.Random(seed); tpl = c15.v12.make_templates(rnd, 4)
    train = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(S)]
    test = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(50)]
    lf = c15.v6.Lfsr(seed + 77); n = len(topo.cells); best = None; br = -1
    for _ in range(warm):
        c = [c15.easy(lf) for _ in range(n)]; r = local_rewards(topo, c, train)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(n); nxt[j] = c15.mutate(nxt[j], lf)
        r = local_rewards(topo, nxt, train)
        if r >= cr: cur, cr = nxt, r
    return c15.accuracy(topo, cur, test), c15.v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--radius", type=int, default=1); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=600)
    ap.add_argument("--per-class", type=int, default=16); a = ap.parse_args()
    print(f"hex cluster radius {a.radius}, LOCAL per-group rewards, noise {a.noise}, {a.tries} tries, {a.per_class} training samples per class")
    print(f"{'seed':>4} {'learned':>8} {'template-rule':>13} {'chance':>7}")
    for s in range(a.first, a.first + a.runs):
        l, t = one(s, a.radius, a.noise, a.tries, a.per_class); print(f"{s:>4} {l:>8.2f} {t:>13.2f} {0.25:>7.2f}", flush=True)
