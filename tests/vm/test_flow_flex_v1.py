"""tests/vm/test_flow_flex_v1.py -- ledger #1032: the flow medium (standard diffusion + instructed pump) on the flex cells (tools/flow_flex_v1.py), proven in the generated RTL against the exact reference, with and
without random stalls, and the conservation law (total amount never changes). Requires iverilog."""
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
import flow_flex_v1 as F  # noqa: E402


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_flow_medium_rtl(mode):
    N, T = 5, 4
    g = Grid(rows=N * 30 + 20, cols=T * 120 + 40)
    ent, ex, _ = F.flow_medium(g, N, T)
    assert g.balance(limit=400) >= 0 and g.problems() == []
    r = random.Random(7)
    vec = [([r.choice([0, 0, 64, 500, 2000]) for _ in range(N)], [[r.randrange(0, 7) for _ in range(N)] for _ in range(T)]) for _ in range(8)]
    vec.append(([0, 4000, 0, 0, 0], [[0] * N] * T))
    vec.append(([0, 4000, 0, 0, 0], [[4] * N] * T))
    ents = {ent[("C", i)]: [v[0][i] for v in vec] for i in range(N)}
    ents.update({ent[("A", i, t)]: [v[1][t][i] for v in vec] for i in range(N - 1) for t in range(T)})
    names = {k: f"X{n}" for n, k in enumerate(ex)}
    got = run_rtl(tempfile.mkdtemp(), f"flow_{mode}", g.records(), ents, {names[k]: c for k, c in ex.items()}, mode, settle=60000, cycles=len(vec) * 600 + 40000)
    for q, (c0, cm) in enumerate(vec):
        ref = F.flow_ref(c0, cm)
        for t in range(T):
            prof = [got[names[(i, t)]][q] for i in range(N)]
            assert prof == ref[t], (q, t)
            assert sum(prof) == sum(c0)                                 # nothing is created or lost
