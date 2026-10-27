"""Hex-N hold counter (rtl/hexn_hold_v1.v) and history + dwell counter (rtl/hexn_hist_v1.v) against their Python models: random streams, edge values of n, and the real thermistor replay (raw bank output, N = 1, 5, 20). Requires iverilog. Model of the hold = tools/hexn_hold_v1.py hold(); the history model is written here from the semantics in docs/hex-n/LAYER_INTERFACES_v1.md."""
import os, random, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
pytestmark = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")
def sim(tb, srcs, entries, width):
    d = tempfile.mkdtemp(); stim = os.path.join(d, "s.hex"); open(stim, "w").write("\n".join("%0*x" % (width, e) for e in entries) + "\n")
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "a.vvp")] + [os.path.join(ROOT, "rtl", s) for s in srcs], check=True)
    out = subprocess.run(["vvp", os.path.join(d, "a.vvp"), "+stim=" + stim, "+count=%d" % len(entries)], capture_output=True, text=True, check=True).stdout
    return [tuple(int(x) for x in l.split()) for l in out.splitlines() if l.strip() and l[0].isdigit()]
def hold_ref(xs, ns):
    cur = None; cand = None; cnt = 0; res = []
    for x, n in zip(xs, ns):
        chg = 0
        if cur is None: cur = x
        elif x == cur: cand = None; cnt = 0
        else:
            if cand is not None and x == cand: cnt += 1
            else: cand = x; cnt = 1
            if cnt >= max(n, 1): cur = x; cand = None; cnt = 0; chg = 1
        res.append((cur, 1, chg))
    return res
def run_hold(xs, ns):
    got = sim("tb_hexn_hold_v1.v", ["hexn_hold_v1.v", "tb_hexn_hold_v1.v"], [(n << 4) | x for x, n in zip(xs, ns)], 3)
    assert got == hold_ref(xs, ns), [(i, a, b) for i, (a, b) in enumerate(zip(got, hold_ref(xs, ns))) if a != b][:5]
def test_hold_random():
    r = random.Random(1)
    for n in (0, 1, 2, 3, 7, 20, 255):
        xs = []; v = 0
        while len(xs) < 600:
            if r.random() < 0.2: v = r.choice([0, 1, 2, 15])
            xs += [v if r.random() > 0.15 else r.randrange(16) for _ in range(r.randrange(1, 40))]
        run_hold(xs[:600], [n] * 600)
def test_hold_n_changes_midstream():
    r = random.Random(2); xs = [r.choice([3, 3, 3, 4, 15]) for _ in range(800)]; run_hold(xs, [r.choice([1, 5, 20]) for _ in range(800)])
def test_hold_thermistor_replay():
    import hexn_hold_v1 as H
    H.R.light(); H.R.pot(); H.R.therm()
    for name, out, ref, nt in H.CAP:
        if name != "therm raw": continue
        xs = [15 if x == -1 else x for x in out]
        for n in (1, 5, 20):
            run_hold(xs, [n] * len(xs))
            got = sim("tb_hexn_hold_v1.v", ["hexn_hold_v1.v", "tb_hexn_hold_v1.v"], [(n << 4) | x for x, n in zip(xs, [n] * len(xs))], 3)
            assert sum(c for _, _, c in got) == sum(1 for a, b in zip(H.hold(out, n)[1:], H.hold(out, n)) if a != b), n
def hist_ref(entries, D=4, DW=6):
    hist = []; dwell = prev = 0; res = []
    for e in entries:
        ev, tick, cls = (e >> 7) & 1, (e >> 6) & 1, e & 15
        if ev: hist = [cls] + hist[:D - 1]; prev = dwell; dwell = 0
        elif tick and dwell != (1 << DW) - 1: dwell += 1
        packed = sum(h << (4 * i) for i, h in enumerate(hist)); res.append((packed, dwell, prev, len(hist)))
    return res
def test_hist_random():
    r = random.Random(3); es = []
    for _ in range(3000): es.append((int(r.random() < 0.04) << 7) | (int(r.random() < 0.5) << 6) | r.randrange(16))
    got = sim("tb_hexn_hist_v1.v", ["hexn_hist_v1.v", "tb_hexn_hist_v1.v"], es, 2)
    assert got == hist_ref(es)
def test_hist_saturation():
    es = [0x80 | 5] + [0x40] * 100 + [0x80 | 6] + [0x40] * 3
    got = sim("tb_hexn_hist_v1.v", ["hexn_hist_v1.v", "tb_hexn_hist_v1.v"], es, 2); assert got == hist_ref(es); assert max(g[1] for g in got) == 63
