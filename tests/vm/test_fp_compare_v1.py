"""tests/vm/test_fp_compare_v1.py -- ledger #1009: the floating-point COMPARATOR from cells (tools/fp_compare_v1.py) in the generated RTL against `cmp_ref` (exact rationals; -1 / 0 / +1, 2 when unordered), fp16 and
bfloat16, plus random stalls. `cmp_ref` is anchored to numpy's float16 comparison. Vectors: every pair of 30 values (zeros of both signs, subnormals, neighbours in the last place, one, the largest normal, the
infinities, nans), random pairs, equal magnitudes with opposite signs, adjacent keys."""
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
import fp_compare_v1 as fc  # noqa: E402
from fp_round_ref_v1 import cmp_ref  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402

FORMATS = {"fp16": fa.FP16, "bf16": fa.BF16}
_BUILT = {}


def build(key):
    if key not in _BUILT:
        g = Grid(rows=120, cols=300)
        ent, ex, consts, _ = fc.fp_compare(g, FORMATS[key])
        assert g.balance(limit=300) >= 0 and g.problems() == []
        _BUILT[key] = (g, ent, ex)
    return _BUILT[key]


def vectors(fmt, seed=3):
    E, m = fmt.exp_bits, fmt.sig_bits - 1
    SG, INF = 1 << (m + E), ((1 << E) - 1) << m
    r = random.Random(seed)
    one = (((1 << (E - 1)) - 1) << m)
    base = [0, 1, (1 << m) - 1, 1 << m, (1 << m) + 1, one - 1, one, one + 1, INF - 1, INF, INF | 1, INF | (1 << (m - 1)), (one + (1 << m)), r.getrandbits(m + E), r.getrandbits(m + E), r.getrandbits(m + E)]
    sp = base + [SG | v for v in base]
    V = [(a, b) for a in sp for b in sp]
    for _ in range(150):
        a, b = r.getrandbits(m + E + 1), r.getrandbits(m + E + 1)
        V.append((a, b))
        V.append((a, a ^ SG))                                # the same magnitude, opposite signs
        k = a & (SG - 1)
        V.append((a, (a & SG) | min(k + 1, SG - 1)))        # the next key up
    return V


def same(fmt, got, want):
    return got == want


def test_reference_is_numpy():
    r = random.Random(4)
    for _ in range(4000):
        a, b = r.getrandbits(16), r.getrandbits(16)
        x, y = np.array([a], dtype=np.uint16).view(np.float16)[0], np.array([b], dtype=np.uint16).view(np.float16)[0]
        got = cmp_ref(fa.FP16, a, b)
        if np.isnan(x) or np.isnan(y):
            assert got == 2
        else:
            assert got == (0xFFFFFFFF if x < y else 1 if x > y else 0), (hex(a), hex(b))


@pytest.mark.parametrize("key", FORMATS)
def test_compare_rtl(key):
    fmt = FORMATS[key]
    g, ent, ex = build(key)
    V = vectors(fmt)
    A, B = zip(*V)
    W = [cmp_ref(fmt, a, b) for a, b in V]
    assert {0, 1, 2, 0xFFFFFFFF} <= set(W)
    d = tempfile.mkdtemp()
    got = run_rtl(d, f"cmp_{key}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=3000, cycles=120000)["R"]
    assert len(got) == len(W), (len(got), len(W))
    bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if x != w]
    assert not bad, (key, len(bad), bad[:6])


def test_compare_random_stalls_rtl_fp16():
    g, ent, ex = build("fp16")
    V = vectors(fa.FP16)[::9][:120]
    A, B = zip(*V)
    W = [cmp_ref(fa.FP16, a, b) for a, b in V]
    d = tempfile.mkdtemp()
    got = run_rtl(d, "cmpst", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "stall", settle=4000, cycles=60000)["R"]
    assert got == W
