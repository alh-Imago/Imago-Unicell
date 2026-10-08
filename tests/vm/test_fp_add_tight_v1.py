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


# ---- fp64 (ledger #1027): 53-bit significand, 11-bit exponent, a 64-bit cell word ---------------------------------------------------------------------------------------------------------
F64 = fa.FpFormat("fp64", 53, 11, 64)


def vectors64(mode, seed=21):
    fmt = F64
    E, m = 11, 52
    emax = (1 << E) - 1
    SG = 1 << (m + E)
    r = random.Random(seed)
    V = [(0, 0), (SG, SG), (SG, 0), (0, SG), (1, 1), (1, SG | 1), (SG | 1, 1), (1 << m, SG | (1 << m)), (1 << m, (1 << m) | 1)]
    one = 1023 << m
    V += [(one, one), (one, SG | one), (one, one | 1), (one | 1, SG | one), (one, 1), (one, SG | 1)]
    for _ in range(40):                                       # near exponents, any signs
        e = r.randrange(2, emax - 2)
        a = r.choice([0, SG]) | (e << m) | r.getrandbits(m)
        b = r.choice([0, SG]) | (max(e + r.randrange(-3, 4), 0) << m) | r.getrandbits(m)
        V.append((a, b))
    for _ in range(12):                                       # cancellation: nearly equal, opposite signs
        e = r.randrange(2, emax - 2)
        x = (e << m) | r.getrandbits(m)
        V.append((x, (x ^ SG) ^ r.getrandbits(r.randrange(1, 8))))
    for _ in range(12):                                       # guard set, sticky clear / set; exact half-ulp ties
        e = r.randrange(60, emax - 2)
        x = (e << m) | r.getrandbits(m)
        sh = r.randrange(m - 1, m + 3)
        V.append((x | r.choice([0, SG]), ((e - sh) << m) | r.choice([0, r.getrandbits(m)]) | r.choice([0, SG])))
    for k in range(3):
        e = 1100 + 7 * k
        V += [(e << m, (e - m - 1) << m), (SG | (e << m), SG | ((e - m - 1) << m)), ((e << m) | 1, (e - m - 1) << m)]
    for _ in range(10):                                       # subnormals and the smallest normals
        V.append((r.choice([0, SG]) | r.getrandbits(m), r.choice([0, SG]) | (r.randrange(0, 3) << m) | r.getrandbits(m)))
    for _ in range(6):                                        # a huge gap: the small one is only a sticky
        e = r.randrange(200, emax - 2)
        V.append(((e << m) | r.getrandbits(m), r.choice([0, SG]) | ((e - r.randrange(54, 90)) << m) | r.getrandbits(m)))
    return [(a, b) for a, b in V if in_scope(fmt, a, b, mode)]


@pytest.mark.parametrize("mode", MODES)
def test_fp64_adder_in_each_mode_rtl(mode):
    g = Grid(rows=140, cols=700)
    ent, ex, consts, _ = ft.fp_add_tight_u(g, F64, rounding=mode)
    assert g.balance(limit=800) >= 0 and g.problems() == []
    V = vectors64(mode)
    assert len(V) >= 100
    A, B = zip(*V)
    W = [add_ref(F64, a, b, mode) for a, b in V]
    d = tempfile.mkdtemp()
    got = run_rtl(d, f"addtight64_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=60000, cycles=len(V) * 80 + 12000, width=64)["R"]
    assert len(got) == len(W), (len(got), len(W))
    bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if x != w]
    assert not bad, (mode, len(bad), bad[:6])
