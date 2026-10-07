"""tests/vm/test_fp_compare_tight_v1.py -- ledger #1012: the TIGHTLY placed comparator (tools/fp_compare_tight_v1.py, ~74 cells instead of 641) in the generated RTL against `cmp_ref`, the same vectors as the
loosely placed one: fp16, bfloat16, fp32 at a 64-bit word, plus random stalls. Requires iverilog."""
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
import fp_compare_tight_v1 as ct  # noqa: E402
from fp_round_ref_v1 import cmp_ref  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
from test_fp_compare_v1 import vectors  # noqa: E402

FORMATS = {"fp16": (fa.FP16, fa.FP16, 32), "bf16": (fa.BF16, fa.BF16, 32), "fp32w64": (fa.FpFormat("fp32w64", 24, 8, 64), fa.FP32, 64)}


def build(key):
    fmt = FORMATS[key][0]
    g = Grid(rows=24, cols=24)
    ent, ex, consts = ct.fp_compare_tight(g, fmt)
    assert g.balance(limit=100) >= 0 and g.problems() == []
    return g, ent, ex


def want(key, a, b):
    w = cmp_ref(FORMATS[key][1], a, b)
    return (1 << FORMATS[key][2]) - 1 if w == 0xFFFFFFFF else w


def test_it_is_small():
    g, _, _ = build("fp16")
    assert len(g.nodes) < 100, len(g.nodes)               # the loose placement was 641


@pytest.mark.parametrize("key", FORMATS)
def test_tight_compare_rtl(key):
    g, ent, ex = build(key)
    V = vectors(FORMATS[key][1])
    if key == "fp32w64":
        V = V[::3]
    A, B = zip(*V)
    W = [want(key, a, b) for a, b in V]
    assert {0, 1, 2, (1 << FORMATS[key][2]) - 1} <= set(W)
    got = run_rtl(tempfile.mkdtemp(), f"cmpt_{key}", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "plain", settle=3000, cycles=len(V) * 60 + 3000, width=FORMATS[key][2] if FORMATS[key][2] != 32 else None)["R"]
    assert len(got) == len(W), (len(got), len(W))
    bad = [(hex(a), hex(b), hex(w), hex(x)) for a, b, w, x in zip(A, B, W, got) if x != w]
    assert not bad, (key, len(bad), bad[:6])


def test_tight_compare_random_stalls_rtl():
    g, ent, ex = build("fp16")
    V = vectors(fa.FP16)[::9][:120]
    A, B = zip(*V)
    W = [want("fp16", a, b) for a, b in V]
    got = run_rtl(tempfile.mkdtemp(), "cmptst", g.records(), {ent["a"]: list(A), ent["b"]: list(B)}, ex, "stall", settle=4000, cycles=60000)["R"]
    assert got == W
