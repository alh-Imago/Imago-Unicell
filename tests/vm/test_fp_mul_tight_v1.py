"""tests/vm/test_fp_mul_tight_v1.py -- ledger #1013: the fp16 MULTIPLIER with a TIGHT front block (tools/fp_mul_tight_v1.py), the same proof as test_fp_mul_v1.py: the whole thing, the whole thing in the generated RTL, against the exact reference `mul_ref` (fp_round_ref_v1.py) in every rounding mode.
The reference is anchored to numpy (float16 product, round-to-nearest-even) in `test_reference_is_numpy`. Vectors: every pair of a set of special values (zeros, subnormals, the smallest / largest normal, one, inf, nan), random
normals whose exponents sum near the UNDERFLOW and OVERFLOW boundaries, subnormal x normal, exact products by a power of two (ties when the result is subnormal), opposite signs."""
import os
import random
import sys
import tempfile

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("", "../../tools"):
    sys.path.insert(0, os.path.join(HERE, sub))
from fp_block_runner_v1 import run_rtl  # noqa: E402
import fp_assembler_v1 as fa  # noqa: E402
import fp_mul_tight_v1 as fm  # noqa: E402
from fp_round_ref_v1 import mul_ref, MODES  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402

FMT = fa.FP16
E, M = FMT.exp_bits, FMT.sig_bits - 1
SG = 1 << (M + E)
INF = ((1 << E) - 1) << M
_BUILT = {}


def is_nan(v):
    return (v & INF) == INF and (v & ((1 << M) - 1)) != 0


def same(got, want):
    return got == want or (is_nan(got) and is_nan(want))


def build(mode):
    if mode not in _BUILT:
        g = Grid(rows=200, cols=400)
        ent, ex, consts, _ = fm.fp_mul_tight_u(g, FMT, rounding=mode)
        assert g.balance(limit=400) >= 0 and g.problems() == []
        _BUILT[mode] = (g, ent, ex)
    return _BUILT[mode]


def vectors(seed=5):
    r = random.Random(seed)
    sp = [0, SG, 1, SG | 0x03FF, 0x0400, 0x3C00, SG | 0x3C00, 0x7BFF, 0x7C00, SG | 0x7C00, 0x7E00, 0x3555, 0x0155]
    V = [(a, b) for a in sp for b in sp]
    bias = (1 << (E - 1)) - 1
    for _ in range(100):                                     # exponents summing near the underflow boundary (e1 + e2 - bias around 0) and the overflow boundary (around 2^E - 1)
        for tgt in (bias, 2 * bias + 1):
            e1 = r.randrange(1, (1 << E) - 1)
            e2 = min(max(tgt + r.randrange(-3, 4) - e1, 1), (1 << E) - 2)
            a = (r.choice([0, SG])) | (e1 << M) | r.getrandbits(M)
            b = (r.choice([0, SG])) | (e2 << M) | r.getrandbits(M)
            V.append((a, b))
    for _ in range(60):                                      # subnormals
        a = r.choice([0, SG]) | r.getrandbits(M)
        b = r.choice([0, SG]) | (r.randrange(0, 1 << E - 1 + 1) << M) | r.getrandbits(M)
        V.append((a, b))
    for _ in range(60):                                      # a number times a power of two: exact; the result is subnormal for the small ones (ties)
        a = r.choice([0, SG]) | (r.randrange(1, 31) << M) | r.getrandbits(M)
        b = r.choice([0, SG]) | (r.randrange(1, 16) << M)
        V.append((a, b))
    V = [(a & 0xFFFF, b & 0xFFFF) for a, b in V]
    assert all(0 <= a < 1 << 16 and 0 <= b < 1 << 16 for a, b in V)
    return V


def test_reference_is_numpy():
    r = random.Random(2)
    for _ in range(4000):
        a, b = r.getrandbits(16), r.getrandbits(16)
        x, y = np.array([a], dtype=np.uint16).view(np.float16)[0], np.array([b], dtype=np.uint16).view(np.float16)[0]
        with np.errstate(all="ignore"):
            z = int(np.array([x * y], dtype=np.float16).view(np.uint16)[0])
        assert same(mul_ref(FMT, a, b, "rne"), z), (hex(a), hex(b))


def test_modes_differ_on_the_vectors():
    V = vectors()
    outs = {m: [mul_ref(FMT, a, b, m) for a, b in V] for m in MODES}
    for i, a in enumerate(MODES):
        for b in MODES[i + 1:]:
            assert sum(x != y for x, y in zip(outs[a], outs[b])) >= 3, (a, b)


@pytest.mark.parametrize("mode", MODES)
def test_multiplier_in_each_mode_rtl_fp16(mode):
    g, ent, ex = build(mode)
    V = vectors()
    A, B = zip(*V)
    W = [mul_ref(FMT, a, b, mode) for a, b in V]
    d = tempfile.mkdtemp()
    got = run_rtl(d, f"multight_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=4000, cycles=30000)["R"]
    assert len(got) == len(W), (len(got), len(W))
    bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if not same(x, w)]
    assert not bad, (mode, len(bad), bad[:6])


@pytest.mark.parametrize("mode", ("rne", "rdn"))
def test_multiplier_with_random_stalls_rtl_fp16(mode):
    """Random gaps on the inputs and random stalls on the output: the handshake keeps every item, in order."""
    g, ent, ex = build(mode)
    V = vectors()[::7][:60]
    A, B = zip(*V)
    W = [mul_ref(FMT, a, b, mode) for a, b in V]
    d = tempfile.mkdtemp()
    got = run_rtl(d, f"multightst_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "stall", settle=6000, cycles=40000)["R"]
    assert len(got) == len(W), (len(got), len(W))
    bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if not same(x, w)]
    assert not bad, (mode, len(bad), bad[:6])


def test_tight_front_is_small():
    g, ent, ex = build("rne")
    assert len(g.nodes) < 1500, len(g.nodes)             # the loose multiplier is 5805 cells (#1013: 2125; #1014: 1229)


@pytest.mark.parametrize("mode", ("rne", "rdn"))
def test_tight_fp32_multiplier_at_word_64_rtl(mode):
    """The same tight multiplier for fp32 at a 64-bit cell word (ledger #1011 gave the word, #1014 the tight placement)."""
    from test_fp_wide_v1 import mul_vectors, FP32W64, INF as INF32
    g = Grid(rows=260, cols=1100)
    ent, ex, consts, _ = fm.fp_mul_tight_u(g, FP32W64, rounding=mode)
    assert g.balance(limit=500) >= 0 and g.problems() == []
    V = mul_vectors()
    A, B = zip(*V)
    d = tempfile.mkdtemp()
    got = run_rtl(d, f"multight32w64_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=6000, cycles=len(V) * 60 + 9000, width=64)["R"]
    nan = lambda v: (v & INF32) == INF32 and (v & 0x7FFFFF) != 0  # noqa: E731
    want = [mul_ref(fa.FP32, a, b, mode) for a, b in V]
    bad = [(hex(a), hex(b), hex(x), hex(w)) for a, b, x, w in zip(A, B, got, want) if x != w and not (nan(x) and nan(w))]
    assert len(got) == len(V) and not bad, (mode, len(got), len(g.nodes), bad[:5])


# ---- fp64 (ledger #1028): the 106-bit product through a 64-bit word (four limb products, top 64 bits + a jammed sticky) ------------------------------------------------------------------
F64 = fa.FpFormat("fp64", 53, 11, 64)
_B64 = {}


def vectors64(seed=7):
    E64, M64 = 11, 52
    SG64 = 1 << (M64 + E64)
    INF64 = ((1 << E64) - 1) << M64
    r = random.Random(seed)
    sp = [0, SG64, 1, SG64 | ((1 << M64) - 1), 1 << M64, 1023 << M64, SG64 | (1023 << M64), INF64 - 1, INF64, SG64 | INF64, INF64 | (1 << 51), 0x3FF5555555555555, 0x0015555555555555]
    V = [(a, b) for a in sp for b in sp]
    bias = 1023
    for _ in range(60):                                      # exponents summing near the underflow boundary and the overflow boundary
        for tgt in (bias, 2 * bias + 1):
            e1 = r.randrange(1, 2047 - 1)
            e2 = min(max(tgt + r.randrange(-3, 4) - e1, 1), 2046)
            V.append((r.choice([0, SG64]) | (e1 << M64) | r.getrandbits(M64), r.choice([0, SG64]) | (e2 << M64) | r.getrandbits(M64)))
    for _ in range(30):                                      # ordinary products: every limb carries something
        e1, e2 = r.randrange(400, 1600), r.randrange(400, 1600)
        V.append((r.choice([0, SG64]) | (e1 << M64) | r.getrandbits(M64), r.choice([0, SG64]) | (e2 << M64) | r.getrandbits(M64)))
    for _ in range(20):                                      # subnormals
        V.append((r.choice([0, SG64]) | r.getrandbits(M64), r.choice([0, SG64]) | (r.randrange(0, 2047) << M64) | r.getrandbits(M64)))
    for _ in range(20):                                      # a number times a power of two: exact; subnormal results for the small ones (ties)
        V.append((r.choice([0, SG64]) | (r.randrange(1, 60) << M64) | r.getrandbits(M64), r.choice([0, SG64]) | (r.randrange(1, 1023) << M64)))
    for _ in range(12):                                      # products whose low bits are ONLY a sticky: significands with a few top bits and a lone low bit
        a = (1023 << M64) | (r.getrandbits(8) << 44) | 1
        b = (1023 << M64) | (r.getrandbits(8) << 44) | 1
        V.append((a, b))
    return V


@pytest.mark.parametrize("mode", MODES)
def test_fp64_multiplier_in_each_mode_rtl(mode):
    if mode not in _B64:
        g = Grid(rows=200, cols=900)
        ent, ex, consts, _ = fm.fp_mul_tight_u(g, F64, rounding=mode)
        assert g.balance(limit=900) >= 0 and g.problems() == []
        _B64[mode] = (g, ent, ex)
    g, ent, ex = _B64[mode]
    V = vectors64()
    A, B = zip(*V)
    W = [mul_ref(F64, a, b, mode) for a, b in V]
    d = tempfile.mkdtemp()
    got = run_rtl(d, f"mul64_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=8000, cycles=len(V) * 70 + 12000, width=64)["R"]
    nan = lambda v: (v & 0x7FF0000000000000) == 0x7FF0000000000000 and (v & ((1 << 52) - 1)) != 0  # noqa: E731
    assert len(got) == len(W), (len(got), len(W))
    bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if x != w and not (nan(x) and nan(w))]
    assert not bad, (mode, len(bad), bad[:6])
