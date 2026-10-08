"""tests/vm/test_ot_w2_v1.py -- ledger #1033: the 1D Wasserstein-2 distance engine built from flex cells (tools/ot_w2_v1.py), after Mirauta et al., arXiv:2610.04091.

Three independent references agree: the merge formula the cells implement, the paper's north-west corner algorithm, and a numerical quantile integral. The cell design is then
checked against them in FlexGrid and in the generated RTL."""
import os
import random
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for d in ("tools", "nano", os.path.join("tests", "vm")):
    sys.path.insert(0, os.path.join(ROOT, d))

import ot_w2_v1 as W  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402

N, T = 4, 64


def sig(rng, n, t):
    xs = sorted(rng.randint(0, 255) for _ in range(n))
    cuts = sorted(rng.randint(0, t) for _ in range(n - 1))
    return xs, [b - a for a, b in zip([0] + cuts, cuts + [t])]


def test_merge_formula_equals_north_west_corner():
    rng = random.Random(1)
    for _ in range(3000):
        n, t = rng.choice([2, 4, 8, 16]), rng.choice([16, 64, 256, 1000])
        a, b = sig(rng, n, t), sig(rng, n, t)
        assert W.w2_ref(*a, *b) == W.w2_nwca(*a, *b)


def test_against_a_quantile_integral():
    np = pytest.importorskip("numpy")
    rng = random.Random(4)
    qs = (np.arange(400000) + 0.5) / 400000
    for _ in range(5):
        (xm, wm), (xn, wn) = sig(rng, 8, 256), sig(rng, 8, 256)
        q = lambda x, w: np.array(x)[np.searchsorted(np.cumsum(w) / sum(w), qs, side="right")]
        assert abs(W.w2_ref(xm, wm, xn, wn) / 256 - np.mean((q(xm, wm) - q(xn, wn)) ** 2)) < 1.0


def test_merge_network_sorts_two_sorted_halves():
    import itertools
    for n2 in (4, 8, 16):
        for _ in range(200):
            rng = random.Random(n2 * 1000 + _)
            v = sorted(rng.randint(0, 9) for _ in range(n2 // 2)) + sorted(rng.randint(0, 9) for _ in range(n2 // 2))
            for a, b in W.merge_pairs(n2):
                if v[a] > v[b]:
                    v[a], v[b] = v[b], v[a]
            assert v == sorted(v)
    assert sum(len(s) for s in W.merge_stages(8)) == len(W.merge_pairs(8)) == 9


@pytest.fixture(scope="module")
def engine():
    g = Grid(rows=300, cols=400)
    ent, ex, consts = W.w2_engine(g, n=N, T=T)
    assert g.balance(limit=600) >= 0 and g.problems() == []
    return g, ent, ex, consts


def items(seed, k):
    rng = random.Random(seed)
    its = [(sig(rng, N, T), sig(rng, N, T)) for _ in range(k)]
    its.append(((list(range(N)), [T // N] * N), (list(range(N)), [T // N] * N)))      # identical: distance 0
    return its


def feed(ent, its):
    entries = {c: [] for c in ent.values()}
    for (xm, wm), (xn, wn) in its:
        for i in range(N):
            entries[ent[f"XM{i}"]].append(xm[i])
            entries[ent[f"XN{i}"]].append(xn[i])
        for i in range(N - 1):
            entries[ent[f"WM{i}"]].append(wm[i])
            entries[ent[f"WN{i}"]].append(wn[i])
    return entries


def test_engine_in_flexgrid(engine):
    from fp_block_runner_v1 import run_vm
    g, ent, ex, consts = engine
    its = items(2, 6)
    got = run_vm(g.records(), feed(ent, its), ex, consts, ticks=2500)["W2"]
    assert got == [W.w2_ref(*a, *b) for a, b in its]


@pytest.mark.skipif(__import__("shutil").which("iverilog") is None, reason="needs iverilog")
@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_engine_in_generated_rtl(engine, mode):
    from fp_block_runner_v1 import run_rtl
    g, ent, ex, _ = engine
    its = items(3, 12)
    got = run_rtl(tempfile.mkdtemp(), f"w2_{mode}", g.records(), feed(ent, its), ex, mode, settle=60000)["W2"]
    assert got == [W.w2_ref(*a, *b) for a, b in its]
