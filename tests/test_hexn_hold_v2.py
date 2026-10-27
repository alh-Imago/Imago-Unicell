"""Hex-N hold counter v2 (rtl/hexn_hold_v2.v: skip_none input) against its Python rule: random streams with NONE (15) mixed in, n = 0, 1, 2, 3, 7, 20, 255, skip 0 and 1, and mid-stream changes of n and skip. skip 0 must equal v1. Requires iverilog."""
import os, random, shutil, subprocess, tempfile
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pytestmark = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")
def sim(entries):
    d = tempfile.mkdtemp(); stim = os.path.join(d, "s.hex"); open(stim, "w").write("\n".join("%04x" % e for e in entries) + "\n")
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "a.vvp"), os.path.join(ROOT, "rtl", "hexn_hold_v2.v"), os.path.join(ROOT, "rtl", "tb_hexn_hold_v2.v")], check=True)
    out = subprocess.run(["vvp", os.path.join(d, "a.vvp"), "+stim=" + stim, "+count=%d" % len(entries)], capture_output=True, text=True, check=True).stdout
    return [tuple(int(x) for x in l.split()) for l in out.splitlines() if l.strip() and l[0].isdigit()]
def ref(xs, ns, ss):
    cur = None; cand = None; cnt = 0; res = []
    for x, n, s in zip(xs, ns, ss):
        chg = 0
        if cur is None: cur = x
        elif s and x == 15: pass
        elif x == cur: cand = None; cnt = 0
        else:
            cnt = cnt + 1 if (cand is not None and x == cand) else 1; cand = x
            if cnt >= max(n, 1): cur = x; cand = None; cnt = 0; chg = 1
        res.append((cur, 1, chg))
    return res
def check(xs, ns, ss):
    got = sim([(s << 12) | (n << 4) | x for x, n, s in zip(xs, ns, ss)]); want = ref(xs, ns, ss)
    assert got == want, [(i, a, b) for i, (a, b) in enumerate(zip(got, want)) if a != b][:5]
def stream(r, n):
    xs = []; v = 0
    while len(xs) < n:
        if r.random() < 0.2: v = r.choice([0, 1, 2, 15])
        xs += [v if r.random() > 0.2 else r.choice([15, 15, r.randrange(16)]) for _ in range(r.randrange(1, 40))]
    return xs[:n]
def test_random():
    r = random.Random(11)
    for n in (0, 1, 2, 3, 7, 20, 255):
        for s in (0, 1): check(stream(r, 500), [n] * 500, [s] * 500)
def test_midstream_changes():
    r = random.Random(12); xs = stream(r, 900); check(xs, [r.choice([1, 3, 5, 20]) for _ in xs], [r.randrange(2) for _ in xs])
def test_first_sample_none_taken_at_once():
    check([15, 15, 3, 3, 3, 3], [3] * 6, [1] * 6)
def test_skip_equals_strict_without_none():
    r = random.Random(13); xs = [r.choice([0, 1, 2]) for _ in range(600)]
    a = sim([(0 << 12) | (4 << 4) | x for x in xs]); b = sim([(1 << 12) | (4 << 4) | x for x in xs]); assert a == b
