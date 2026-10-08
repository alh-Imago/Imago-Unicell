"""tests/vm/test_fp_special_v1.py -- ledger #1001: the adder's SPECIAL VALUES (inf, nan, overflow to inf) around the finished adder, from cells only (`fp_add(..., specials=True)`, the block laid out as
separate lines joined with crossing tiles). Checked against numpy's own float32 / float16 addition in the generated RTL (plain and with random stalls) and in FlexGrid; NaN results are compared as
"is a NaN" (any payload). Ledger #1005 adds SUBNORMAL inputs and results (gradual underflow: a sum is never below the smallest subnormal, an addition that ends below the smallest
normal is exact), so nothing is excluded any more; signed zeros are compared as numpy gives them. Requires iverilog."""
import os
import random
import shutil
import struct
import sys
import tempfile

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
from fp_block_runner_v1 import run_rtl, run_vm  # noqa: E402
import fp_assembler_v1 as fa  # noqa: E402
import fp_add_v1 as fadd  # noqa: E402

FORMATS = {"fp32": (fa.FP32, np.float32, "<f", "<I"), "fp16": (fa.FP16, np.float16, "<e", "<H")}


def to_f(fmt_key, b):
    _f, _np, fs, is_ = FORMATS[fmt_key]
    return _np(struct.unpack(fs, struct.pack(is_, b))[0])


def to_b(fmt_key, f):
    _f, _np, fs, is_ = FORMATS[fmt_key]
    return struct.unpack(is_, struct.pack(fs, f))[0]


def is_nan(fmt, v):
    E, m = fmt.exp_bits, fmt.sig_bits - 1
    return ((v >> m) & ((1 << E) - 1)) == (1 << E) - 1 and (v & ((1 << m) - 1)) != 0


def reference(key, a, b):
    fmt = FORMATS[key][0]
    with np.errstate(all="ignore"):
        return to_b(key, FORMATS[key][1](to_f(key, a)) + FORMATS[key][1](to_f(key, b)))


def vectors(key, seed=3):
    fmt = FORMATS[key][0]
    E, m = fmt.exp_bits, fmt.sig_bits - 1
    emax = (1 << E) - 1
    INF, SG = emax << m, 1 << (m + E)
    big = ((emax - 1) << m) | ((1 << m) - 1)
    qnan = INF | (1 << (m - 1))
    A = [(1 << (m)) * (emax // 2), INF, INF | SG, INF, qnan, big, big, big | SG, INF + 1, INF, big, (emax // 2) << m, 0, SG]
    B = [((emax // 2) + 1) << m, (emax // 2) << m, (emax // 2) << m, INF | SG, (emax // 2) << m, big, ((emax - 5) << m), big | SG, (emax // 2) << m, INF, big >> 1 | (1 << m), ((emax // 2) << m) | SG, SG, 0]
    r = random.Random(seed)
    for _ in range(14):
        e1, e2 = r.choice([emax - 1, emax - 2, r.randrange(1, emax)]), r.choice([emax - 1, r.randrange(1, emax)])
        A.append((r.getrandbits(1) << (m + E)) | (e1 << m) | r.getrandbits(m))
        B.append((r.getrandbits(1) << (m + E)) | (e2 << m) | r.getrandbits(m))
    for _ in range(26):                                        # subnormal inputs / results (#1005)
        sg = lambda: r.getrandbits(1) << (m + E)
        kind = r.randrange(6)
        if kind == 0:                                          # two subnormals (the sum may carry into the smallest normal)
            a, b = sg() | r.getrandbits(m), sg() | r.getrandbits(m)
        elif kind == 1:                                        # subnormal + a small normal
            a, b = sg() | r.getrandbits(m), sg() | (r.randrange(1, 4) << m) | r.getrandbits(m)
        elif kind == 2:                                        # near-equal small normals, opposite sign: the difference is a subnormal
            e0 = r.randrange(1, 3)
            x = (e0 << m) | r.getrandbits(m)
            a, b = x, (1 << (m + E)) | ((e0 + r.choice([0, 0, -1 if e0 > 1 else 0])) << m) | r.getrandbits(m)
        elif kind == 3:                                        # a subnormal and its own negative plus a little: exact cancellation to a smaller subnormal
            x = r.getrandbits(m) | 1
            a, b = x, (1 << (m + E)) | (x ^ r.getrandbits(r.randrange(1, m)))
        elif kind == 4:                                        # a subnormal + a big number (sticky: the subnormal is rounded away or not)
            a, b = sg() | r.getrandbits(m), sg() | (r.randrange(1, emax - 1) << m) | r.getrandbits(m)
        else:                                                  # zero / signed zero + a subnormal
            a, b = r.choice([0, 1 << (m + E)]), sg() | r.getrandbits(m)
        A.append(a)
        B.append(b)
    A += [1, SG | 1, 1 << (m - 1), (1 << m) - 1, 1 << m, (1 << m) | 1, (2 << m)]
    B += [1, 1, 1 << (m - 1), 1, SG | ((1 << m) + 1), SG | (1 << m), SG | ((1 << m) | 1)]
    keep = []
    for a, b in zip(A, B):
        keep.append((a, b, reference(key, a, b)))
    return keep


def same(fmt, got, want):
    return (is_nan(fmt, got) and is_nan(fmt, want)) or got == want


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fpspecial_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


_BUILT = {}


def build(key):
    if key not in _BUILT:
        g, ent, ex, consts = fadd.fp_add_grid(FORMATS[key][0])
        assert g.balance() >= 0 and g.problems() == []
        _BUILT[key] = (g, ent, ex, consts)
    return _BUILT[key]


def test_vectors_contain_subnormal_inputs_and_results():
    v = vectors("fp32")
    sub = lambda x: ((x >> 23) & 255) == 0 and (x & 0x7FFFFF) != 0
    assert sum(sub(a) or sub(b) for a, b, _ in v) >= 20
    assert sum(sub(w) for _, _, w in v) >= 12                           # subnormal RESULTS (incl. exact cancellation)
    assert sum(sub(w) and not sub(a) and not sub(b) for a, b, w in v) >= 2   # a subnormal result from normal inputs
    assert any(((w >> 23) & 255) == 1 and sub(a) and sub(b) for a, b, w in v)   # a rounding carry into the smallest normal


def test_vectors_really_contain_every_special_case():
    v = vectors("fp32")
    fmt = fa.FP32
    assert len(v) >= 20
    assert sum(is_nan(fmt, w) for _, _, w in v) >= 3                     # nan in, inf - inf
    assert sum(((w >> 23) & 255) == 255 and (w & 0x7FFFFF) == 0 for _, _, w in v) >= 5   # infinities (incl. overflow)
    assert any(((a >> 23) & 255) < 255 and ((b >> 23) & 255) < 255 and ((w >> 23) & 255) == 255 for a, b, w in v)  # overflow from finite inputs


@pytest.mark.parametrize("key", list(FORMATS))
def test_specials_in_rtl(tmp, key):
    fmt = FORMATS[key][0]
    g, ent, ex, _ = build(key)
    v = vectors(key)
    A, B, W = zip(*v)
    modes = ("plain", "stall") if key == "fp32" else ("plain",)
    for mode in modes:
        got = run_rtl(tmp, f"sp_{key}_{mode}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, mode, settle=90000)["R"]
        bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if not same(fmt, x, w)]
        assert not bad, bad[:4]


def test_specials_in_flexgrid_fp32():
    g, ent, ex, consts = build("fp32")
    v = vectors("fp32")[:6]
    A, B, W = zip(*v)
    got = run_vm(g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, consts, ticks=1500)["R"]
    assert all(same(fa.FP32, x, w) for x, w in zip(got, W)), [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got)]


def test_subnormals_in_flexgrid_fp32():
    """A few subnormal cases through the FlexGrid VM (slow: ~1700 cells): a subnormal result from two normals, a carry into the smallest normal, subnormal + subnormal, subnormal + big."""
    g, ent, ex, consts = build("fp32")
    sub = lambda x: ((x >> 23) & 255) == 0 and (x & 0x7FFFFF) != 0
    v = vectors("fp32")
    pick = [next(t for t in v if sub(t[2]) and not sub(t[0]) and not sub(t[1])),
            next(t for t in v if ((t[2] >> 23) & 255) == 1 and sub(t[0]) and sub(t[1])),
            next(t for t in v if sub(t[0]) and sub(t[1]) and sub(t[2])),
            next(t for t in v if sub(t[0]) and ((t[1] >> 23) & 255) > 100 and ((t[1] >> 23) & 255) < 255)]
    A, B, W = zip(*pick)
    got = run_vm(g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, consts, ticks=1500)["R"]
    assert all(same(fa.FP32, x, w) for x, w in zip(got, W)), [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got)]


def test_bite_flushing_subnormals_would_get_them_wrong():
    """The subnormal vectors have teeth: an adder that flushed subnormal inputs and results to zero (the #990 scope) would miss many of them."""
    fmt = fa.FP32
    flush = lambda x: x & (1 << 31) if ((x >> 23) & 255) == 0 else x
    v = vectors("fp32")
    wrong = 0
    for a, b, w in v:
        fw = reference("fp32", flush(a), flush(b))
        fw = flush(fw)
        wrong += not same(fmt, fw, w)
    assert wrong >= 15, wrong


def test_bite_the_adder_without_the_block_gets_them_wrong(tmp):
    """The same vectors through the adder WITHOUT the special-value block must NOT match: the check has teeth."""
    g, ent, ex, _ = fadd.fp_add_grid(fa.FP32, specials=False, rows=34)
    assert g.balance() >= 0
    v = vectors("fp32")
    A, B, W = zip(*v)
    got = run_rtl(tmp, "sp_bite", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=60000)["R"]
    assert sum(not same(fa.FP32, x, w) for x, w in zip(got, W)) >= 5
