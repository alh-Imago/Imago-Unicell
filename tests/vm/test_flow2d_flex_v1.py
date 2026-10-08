"""tests/vm/test_flow2d_flex_v1.py -- ledger #1034: the 2-D flow medium (four-neighbour diffusion + instructed east / south pumps) on the flex cells (tools/flow2d_flex_v1.py), proven in the generated RTL against the exact
reference, with the conservation law. 2x2 over 2 steps plain and with random stalls; the 3x3 sheet over 1 step (~7,000 cells) plain. Requires iverilog."""
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
import flow2d_flex_v1 as F  # noqa: E402


def run(R, Q, T, mode, nvec, **kw):
    g = Grid(rows=R * 90 + 20, cols=T * (Q * 150 + 80) + 40)
    ent, ex, _ = F.flow2d_medium(g, R, Q, T, rh=26, wa=34, wb=18)
    assert g.balance(limit=800) >= 0 and g.problems() == []
    r = random.Random(2)
    vec = []
    for _ in range(nvec):
        c0 = [[r.choice([0, 0, 64, 500, 2000]) for _ in range(Q)] for _ in range(R)]
        cm = [([[r.randrange(0, 3) for _ in range(Q)] for _ in range(R)], [[r.randrange(0, 3) for _ in range(Q)] for _ in range(R)]) for _ in range(T)]
        vec.append((c0, cm))
    ents = {}
    for i in range(R):
        for j in range(Q):
            ents[ent[("C", i, j)]] = [v[0][i][j] for v in vec]
            for t in range(T):
                if j < Q - 1:
                    ents[ent[("AE", i, j, t)]] = [v[1][t][0][i][j] for v in vec]
                if i < R - 1:
                    ents[ent[("AS", i, j, t)]] = [v[1][t][1][i][j] for v in vec]
    names = {k: f"X{n}" for n, k in enumerate(ex)}
    got = run_rtl(tempfile.mkdtemp(), f"f2d_{R}{Q}{mode}", g.records(), ents, {names[k]: c for k, c in ex.items()}, mode, settle=80000, cycles=len(vec) * 900 + 60000)
    for q, (c0, cm) in enumerate(vec):
        ref = F.flow2d_ref(c0, cm)
        for t in range(T):
            sheet = [[got[names[(i, j, t)]][q] for j in range(Q)] for i in range(R)]
            assert sheet == ref[t], (q, t)
            assert sum(map(sum, sheet)) == sum(map(sum, c0))
    return len(g.nodes)


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_flow2d_2x2_rtl(mode):
    run(2, 2, 2, mode, 6)


def test_flow2d_3x3_rtl():
    assert run(3, 3, 1, "plain", 4) > 5000
