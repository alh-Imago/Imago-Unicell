"""Hex-N v7 (new file; v1-v6 untouched). VM only. Two experiments, as agreed with Alan:

 --mode onebit : the cheapest feedback design. The teacher says ONE bit per trial: 'better than the best so far' (strict, '>') or
                 'not worse' ('>='). No reward number crosses the feedback lines. The warm start becomes a tournament (a random cell
                 replaces the held one only when the teacher says 'better'). Everything else is the v6 learner (LFSR, 1-3 changes per try).
 --mode net    : a LINE of K cells. Cell i face 0 is wired to cell i+1 face 3 (lane for lane, same clock). External stimulus drives cell 0
                 (all lanes except face 0); the last cell's output is what the teacher compares with the goal (the output of a hidden
                 network of the same shape, so the goal is reachable). The learner sees only the teacher's 4-bit reward for the WHOLE
                 network: it must find which cell to change by trial. Each try changes 1-3 settings in randomly chosen cells.
Usage: python3 tools/hexn_network_v7.py --mode onebit [--strict] | --mode net --cells K [--first S] [--runs N] [--tries T]"""
import argparse, importlib.util, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v3, v6 = load("hexn_mutation_v3"), load("hexn_learner_v6")
v1, Lfsr, Cell, N, F, P, PL = v3.v1, v6.Lfsr, v3.Cell, v3.N, v3.v1.F, v3.v1.P, v3.PL


# ---------- one-bit teacher ----------
def onebit(seed, tries, w, warm, strict):
    rnd = random.Random(seed); stim = v1.make_stimuli(rnd); gb = v3.bursts(v1.rand_cfg(rnd), stim)
    sc = lambda c: v3.score(c, stim, gb, w); lf = Lfsr(seed + 77)
    held = v1.rand_cfg(lf); hs = sc(held)                       # teacher remembers the held score; the cell only sees 'better?'
    better = (lambda a, b: a > b) if strict else (lambda a, b: a >= b)
    for _ in range(warm - 1):
        c = v1.rand_cfg(lf); s = sc(c)
        if better(s, hs): held, hs = c, s
    for _ in range(tries - warm):
        nxt = held
        for _ in range(1 + lf.randrange(3)): nxt = v1.mutate(nxt, lf)
        s = sc(nxt)
        if better(s, hs): held, hs = nxt, s
    rr = random.Random(seed + 1); rb = max(sc(v1.rand_cfg(rr)) for _ in range(tries))
    return hs, rb


# ---------- network ----------
def net_bursts(cfgs, stim):
    k = len(cfgs); cells = [Cell(*c) for c in cfgs]; fw, fb = [], []; acc = [0] * N
    for t, (rx0, phase, ps, we) in enumerate(stim):
        tx = [c.tx(phase) for c in cells]
        for i, c in enumerate(cells):
            rx = list(rx0) if i == 0 else [0] * N
            if i == 0:
                for p in range(P): rx[0 * P + p] = 0                       # face 0 of cell 0 is wired to cell 1, not external
                if k > 1:
                    for p in range(P): rx[0 * P + p] = tx[1][3 * P + p]
            else:
                for p in range(P): rx[3 * P + p] = tx[i - 1][0 * P + p]
                if i < k - 1:
                    for p in range(P): rx[0 * P + p] = tx[i + 1][3 * P + p]
            c.clock(rx, phase, ps, we)
        if ps: acc = [0] * N
        acc = [a + b for a, b in zip(acc, tx[-1])]
        if t % PL == PL - 1: (fb if phase else fw).append(list(acc))
    return fw, fb


def net_score(cfgs, stim, gb, w):
    fw, fb = net_bursts(cfgs, stim)
    parts = [(1 - w, v3.closeness(fw, gb[0])), (w, v3.closeness(fb, gb[1]))]
    parts = [(x, c) for x, c in parts if c is not None and x > 0]; tot = sum(x for x, _ in parts)
    return 0 if tot == 0 else round(1000 * sum(x * c for x, c in parts) / tot)


def net_run(seed, k, tries, w, warm, bits, min_goal=20):
    rnd = random.Random(seed); stim = v1.make_stimuli(rnd)
    for _ in range(500):                       # a hidden network whose last cell is silent teaches nothing: draw until its output has >= min_goal clocks
        gb = net_bursts([v1.rand_cfg(rnd) for _ in range(k)], stim)
        if sum(map(sum, gb[0])) + sum(map(sum, gb[1])) >= min_goal: break
    q = lambda cf: net_score(cf, stim, gb, w) * ((1 << bits) - 1) // 1000
    lf = Lfsr(seed + 77); best = None; br = -1
    for _ in range(warm):
        c = [v1.rand_cfg(lf) for _ in range(k)]; r = q(c)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(k); nxt[j] = v1.mutate(nxt[j], lf)
        r = q(nxt)
        if r >= cr: cur, cr = nxt, r
    rr = random.Random(seed + 1)
    rb = max(net_score([v1.rand_cfg(rr) for _ in range(k)], stim, gb, w) for _ in range(tries))
    return net_score(cur, stim, gb, w), rb


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--mode", default="net"); ap.add_argument("--cells", type=int, default=2)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--tries", type=int, default=1500); ap.add_argument("--warm", type=int, default=100)
    ap.add_argument("--bits", type=int, default=4); ap.add_argument("--fb", type=float, default=0.5); ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    print(f"mode {a.mode}" + (f", strict '>'" if a.strict else ", '>='") if a.mode == "onebit" else f"mode net, {a.cells} cells, reward bits {a.bits}, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'random-best':>11}")
    for s in range(a.first, a.first + a.runs):
        r = onebit(s, a.tries, a.fb, a.warm, a.strict) if a.mode == "onebit" else net_run(s, a.cells, a.tries, a.fb, a.warm, a.bits)
        print(f"{s:>4} {r[0]:>8} {r[1]:>11}", flush=True)
