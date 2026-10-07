"""tests/vm/test_fp_add_tight_v1.py -- ledger #1026: the fp ADDER, TIGHTLY placed as a U (tools/fp_add_tight_v1.py), proven in the generated RTL against the exact reference `add_ref`
(fp_round_ref_v1.py) in every rounding mode: normals, subnormals, zeros of both signs, cancellation, ties, exponent gaps beyond the significand. Scope = the loose adder's without the special-value block:
no inf / nan operands and no overflowing result (those vectors are filtered out). Requires iverilog."""
import os
import random
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("", "../../tools"):
    sys.path.insert(0, os.path.join(HERE, sub))
from fp_block_runner_v1 import run_rtl  # noqa: E402
import fp_assembler_v1 as fa  # noqa: E402
import fp_add_tight_v1 as ft  # noqa: E402
from fp_round_ref_v1 import add_ref, MODES  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
from test_fp_round_modes_v1 import mode_vectors  # noqa: E402

_BUILT = {}


def build(fmt, mode):
    k = (fmt.name, mode)
    if k not in _BUILT:
        g = Grid(rows=140, cols=400)
        ent, ex, consts, _ = ft.fp_add_tight_u(g, fmt, rounding=mode)
        assert g.balance(limit=400) >= 0 and g.problems() == []
        _BUILT[k] = (g, ent, ex)
    return _BUILT[k]


def in_scope(fmt, a, b, mode):
    E, m = fmt.exp_bits, fmt.sig_bits - 1
    emax = (1 << E) - 1
    ex = lambda v: (v >> m) & emax  # noqa: E731
    if ex(a) == emax or ex(b) == emax:
        return False
    return all(ex(add_ref(fmt, a, b, m_)) != emax for m_ in MODES)            # no mode overflows (the directed modes saturate at the largest finite: the special block's job)


def vectors(fmt, mode):
    key = {"fp16": "fp16", "fp32": "fp32"}[fmt.name]
    V = [(a, b) for a, b in mode_vectors(key) if in_scope(fmt, a, b, mode)]
    E, m = fmt.exp_bits, fmt.sig_bits - 1
    r = random.Random(11)
    SG = 1 << (m + E)
    for _ in range(80):
        e1 = r.randrange(1, (1 << E) - 2)
        e2 = min(max(e1 + r.randrange(-3, 4), 0), (1 << E) - 2)
        a = r.choice([0, SG]) | (e1 << m) | r.getrandbits(m)
        b = r.choice([0, SG]) | (e2 << m) | r.getrandbits(m)
        if in_scope(fmt, a, b, mode):
            V.append((a, b))
    return V


@pytest.mark.parametrize("mode", MODES)
def test_adder_in_each_mode_rtl_fp16(mode):
    fmt = fa.FP16
    g, ent, ex = build(fmt, mode)
    V = vectors(fmt, mode)
    assert len(V) >= 60
    A, B = zip(*V)
    W = [add_ref(fmt, a, b, mode) for a, b in V]
    d = tempfile.mkdtemp()
    got = run_rtl(d, f"addtight_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=60000, cycles=len(V) * 60 + 9000)["R"]
    assert len(got) == len(W), (len(got), len(W))
    bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if x != w]
    assert not bad, (mode, len(bad), bad[:6])


def test_adder_with_random_stalls_rtl_fp16():
    fmt = fa.FP16
    g, ent, ex = build(fmt, "rne")
    V = vectors(fmt, "rne")[::3][:50]
    A, B = zip(*V)
    W = [add_ref(fmt, a, b, "rne") for a, b in V]
    d = tempfile.mkdtemp()
    got = run_rtl(d, "addtightst", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "stall", settle=60000, cycles=60000)["R"]
    assert got == W


def test_tight_adder_is_smaller_than_the_loose_one():
    g, ent, ex = build(fa.FP16, "rne")
    assert len(g.nodes) < 1702, len(g.nodes)             # the loose fp16 adder (no special block) is 1,702 cells
