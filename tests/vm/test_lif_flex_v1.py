"""tests/vm/test_lif_flex_v1.py -- ledger #1030: the LIF neuron (one neuron, and a two-neuron network) on the flex cells, time unrolled into space (tools/lif_flex_v1.py), proven in the generated RTL
against the exact integer reference (spike trains and final membrane), with and without random stalls. Requires iverilog."""
import os
import random
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("", "../../tools"):
    sys.path.insert(0, os.path.join(HERE, sub))
from fp_block_runner_v1 import run_rtl  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
import lif_flex_v1 as L  # noqa: E402

K, TH = 3, 256


def vectors(T, N, seed):
    r = random.Random(seed)
    cur = [0, 0, 40, 90, 200, 300]
    V = [[[r.choice(cur) for _ in range(T)] for _ in range(N)] for _ in range(20)]
    V.append([[400] + [0] * (T - 1)] + [[0] * T] * (N - 1))
    V.append([[0] * T] * N)
    V.append([[60] * T] + [[0] * T] * (N - 1))
    return V


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_single_neuron_rtl(mode):
    T = 8
    g = Grid(rows=40, cols=40 * T + 40)
    ent, ex, _ = L.lif_neuron(g, T, K, TH)
    assert g.balance(limit=400) >= 0 and g.problems() == []
    V = [v[0] for v in vectors(T, 1, 3)]
    ents = {ent[f"I{t}"]: [v[t] for v in V] for t in range(T)}
    exits = {**{f"S{t}": ex[f"S{t}"] for t in range(T)}, "VF": ex["VF"]}
    got = run_rtl(tempfile.mkdtemp(), f"lif1_{mode}", g.records(), ents, exits, mode, settle=40000, cycles=len(V) * 300 + 20000)
    for q, v in enumerate(V):
        sp, vf = L.lif_ref(v, K, TH)
        assert [got[f"S{t}"][q] for t in range(T)] == sp and got["VF"][q] == vf, (q, v)
    assert any(any(L.lif_ref(v, K, TH)[0]) for v in V)


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_two_neuron_network_rtl(mode):
    T, N, W = 6, 2, [[0, 200], [180, 0]]
    g = Grid(rows=70, cols=40 * T + 60)
    ent, ex, _ = L.lif_network(g, N, T, W, K, TH)
    assert g.balance(limit=400) >= 0 and g.problems() == []
    V = vectors(T, N, 5)
    ents = {ent[(j, t)]: [v[j][t] for v in V] for j in range(N) for t in range(T)}
    exits = {**{f"S{j}_{t}": ex[(j, t)] for j in range(N) for t in range(T)}, **{f"VF{j}": ex[(j, "VF")] for j in range(N)}}
    got = run_rtl(tempfile.mkdtemp(), f"lifnet_{mode}", g.records(), ents, exits, mode, settle=40000, cycles=len(V) * 400 + 30000)
    for q, v in enumerate(V):
        sp, fv = L.net_ref(v, W, K, TH)
        for j in range(N):
            assert [got[f"S{j}_{t}"][q] for t in range(T)] == sp[j] and got[f"VF{j}"][q] == fv[j], (q, j, v)


def test_subtract_from_the_same_source_keeps_its_minuend_rtl():
    """#1031: v - (v >> 3), where BOTH operands of the subtract descend from v: the declared minuend (the first operand) must be recognised by the layout engine and arrive first."""
    import netplace_v1 as npl
    import fp_add_v1 as fa
    import fp_mul_tight_v1 as f
    n = npl.Net()
    n.op("PV", "relay", [])
    n.op("L", "relay", ["PV"], addon=fa.shr(3))
    n.op("O.D", "sub", ["PV", "L"])
    for sd in (1, 2, 3):
        g = Grid(rows=30, cols=60)
        nm, _, _ = f.place_net_tight(g, n, "X", 2, 2, ["PV"], 12, 24, pitch=3, gap=2, outs=["O.D"], seeds=(sd,))
        assert g.balance(limit=60) >= 0 and g.problems() == []
        vals = [0, 5, 8, 100, 255, 1000, 12345]
        got = run_rtl(tempfile.mkdtemp(), f"mn{sd}", g.records(), {nm["PV"]: vals}, {"D": nm["O.D"]}, "plain", settle=5000, cycles=6000)["D"]
        assert got == [v - (v >> 3) for v in vals]
