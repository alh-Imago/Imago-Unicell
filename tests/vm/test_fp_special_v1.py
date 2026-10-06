"""tests/vm/test_fp_special_v1.py -- ledger #1001: the adder's SPECIAL VALUES (inf, nan, overflow to inf) around the finished adder, from cells only (`fp_add(..., specials=True)`, the block laid out as
separate lines joined with crossing tiles). Checked against numpy's own float32 / float16 addition in the generated RTL (plain and with random stalls) and in FlexGrid; NaN results are compared as
"is a NaN" (any payload). Not covered (stated): subnormal inputs / results (flush) and underflow -- those vectors are excluded. Requires iverilog."""
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
    keep = []
    for a, b in zip(A, B):
        w = reference(key, a, b)
        def sub(v):
            return ((v >> m) & emax) == 0 and (v & ((1 << m) - 1)) != 0
        if sub(a) or sub(b) or sub(w):
            continue
        keep.append((a, b, w))
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


def test_bite_the_adder_without_the_block_gets_them_wrong(tmp):
    """The same vectors through the adder WITHOUT the special-value block must NOT match: the check has teeth."""
    g, ent, ex, _ = fadd.fp_add_grid(fa.FP32, specials=False, rows=34)
    assert g.balance() >= 0
    v = vectors("fp32")
    A, B, W = zip(*v)
    got = run_rtl(tmp, "sp_bite", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=60000)["R"]
    assert sum(not same(fa.FP32, x, w) for x, w in zip(got, W)) >= 5
