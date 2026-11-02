"""tests/vm/test_hexn_twins_v1.py -- the word-level twins (tools/hexn_twins_v1.py) against the RTL cores, on random stimuli, tick for tick and word for word. Needs iverilog."""
import os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from hexn_rtl_probe_v1 import probe
import hexn_twins_v1 as T

W = 32


def run_twin(twin, stim, face_of, out_of, nclk):
    """drive the twin with the same stimulus; returns [(out_port, start, word)] like probe()"""
    cur = {}; res = []
    for t in range(nclk):
        ins = {}
        for port, items in stim.items():
            for (s, w) in items:
                if s <= t < s + W: ins[face_of[port]] = ((w >> (t - s)) & 1, 1 if t == s else 0)
                if port == "adv" and t == s: ins[face_of[port]] = (1, 1)
        # the twin sees tick t; its outputs are visible at t+1
        outs = twin.step(t, ins)
        for of, (b, f) in outs.items():
            p = out_of[of]
            if f: cur[p] = [t + 1, 0, 0]
            if p in cur and cur[p][1] < W:
                st = cur[p]; st[2] |= b << st[1]; st[1] += 1
                if st[1] == W: res.append((p, st[0], st[2])); del cur[p]
    return sorted(res, key=lambda x: (x[1], x[0]))


def _rand_starts(rnd, n, lo=5, hi=330):
    """start ticks on ONE link: words cannot overlap, so at least 32 ticks apart"""
    out = []; t = lo + rnd.randrange(0, 40)
    for _ in range(n):
        if t >= hi: break
        out.append(t); t += 32 + rnd.randrange(0, 80)
    return out


def test_merge_twin():
    rnd = random.Random(11); bad = 0
    for it in range(60):
        mode = rnd.choice([0, 1, 2, 2, 3]); stim = {"a": [(s, rnd.randrange(1 << 32)) for s in _rand_starts(rnd, rnd.randrange(1, 5))], "b": [(s, rnd.randrange(1 << 32)) for s in _rand_starts(rnd, rnd.randrange(1, 5))]}
        if mode == 3: stim = {"a": [(rnd.randrange(5, 200), rnd.randrange(1 << 32))], "b": [(rnd.randrange(5, 200), rnd.randrange(1 << 32))]}
        rtl = probe("merge", {"mode": mode}, stim, 700)
        tw = run_twin(T.MergeTwin(mode), stim, {"a": "W", "b": "N"}, {"E": "r"}, 700)
        if rtl != tw: bad += 1; print("MISMATCH merge mode", mode, {k: [s for s, _ in v] for k, v in stim.items()}, [(p, s) for p, s, _ in rtl], [(p, s) for p, s, _ in tw])
    assert bad == 0, bad


def test_prio_twin():
    rnd = random.Random(12); bad = 0
    ports = ["dn", "ds", "de", "dw"]; faces = {"dn": "N", "ds": "S", "de": "E", "dw": "W"}
    for it in range(60):
        mode = rnd.choice([0, 1, 2]); mask = rnd.choice([15, 15, 7, 13, rnd.randrange(1, 16)]); ranks = rnd.randrange(256); ln = rnd.randrange(0, 5) if mode == 2 else 0; order = rnd.randrange(256)
        stim = {p: [(s, rnd.randrange(1 << 32)) for s in _rand_starts(rnd, rnd.randrange(0, 4))] for p in ports}
        cfg = {"mask": mask, "ranks": ranks, "mode": mode, "len": ln, "order": order}
        rtl = probe("prio", cfg, stim, 800)
        tw = run_twin(T.PrioTwin(mask, [(ranks >> (2 * i)) & 3 for i in range(4)], mode, ln, [(order >> (2 * i)) & 3 for i in range(4)]), stim, faces, {"E": "r"}, 800)
        if rtl != tw: bad += 1; print("MISMATCH prio", cfg, {k: [s for s, _ in v] for k, v in stim.items()}, [(p, s) for p, s, _ in rtl], [(p, s) for p, s, _ in tw])
    assert bad == 0, bad


def test_branch_twin():
    rnd = random.Random(13); bad = 0
    for it in range(50):
        cfg = {"route_lt": rnd.randrange(4), "route_eq": rnd.randrange(4), "route_gt": rnd.randrange(4), "emit": rnd.randrange(4), "fixed": rnd.randrange(1 << 32)}
        pick = lambda: rnd.choice([rnd.randrange(1 << 32), rnd.randrange(8), (1 << 32) - rnd.randrange(1, 8), 1 << 31, (1 << 31) - 1])
        n = rnd.randrange(1, 4)
        stim = {"a": [(s, pick()) for s in _rand_starts(rnd, n, 5, 300)], "b": [(s, pick()) for s in _rand_starts(rnd, n, 5, 300)]}
        if rnd.random() < 0.4: stim["b"] = [(s, w) for (s, _), (_, w) in zip(stim["a"], stim["a"])]       # equal words
        rtl = probe("branch", cfg, stim, 700)
        tw = run_twin(T.BranchTwin(cfg["route_lt"], cfg["route_eq"], cfg["route_gt"], cfg["emit"], cfg["fixed"]), stim, {"a": "W", "b": "N"}, {"E": "o1", "S": "o2"}, 700)
        if rtl != tw: bad += 1; print("MISMATCH branch", cfg, {k: [s for s, _ in v] for k, v in stim.items()}, [(p, s) for p, s, _ in rtl], [(p, s) for p, s, _ in tw])
    assert bad == 0, bad


def test_seq_twin():
    rnd = random.Random(14); bad = 0
    for it in range(40):
        ln = rnd.randrange(0, 5); vals = [rnd.randrange(1 << 32) for _ in range(4)]
        stim = {"adv": [(s, 0) for s in _rand_starts(rnd, rnd.randrange(1, 7), 5, 400)]}
        v128 = sum(v << (32 * i) for i, v in enumerate(vals))
        rtl = probe("seq", {"vals": v128, "len": ln}, stim, 700)
        tw = run_twin(T.SeqTwin(vals, ln), stim, {"adv": "W"}, {"E": "r"}, 700)
        if rtl != tw: bad += 1; print("MISMATCH seq", ln, [s for s, _ in stim["adv"]], [(p, s) for p, s, _ in rtl], [(p, s) for p, s, _ in tw])
    assert bad == 0, bad
