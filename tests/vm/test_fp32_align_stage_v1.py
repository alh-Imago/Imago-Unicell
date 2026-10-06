"""tests/vm/test_fp32_align_stage_v1.py -- ledger #987: ONE conditional RIGHT-shift stage (the align step of an fp32 add), real flex cells, no loop, no data-dependent routing.

    out = (v >> s)  if bit k of d is set  else  v          (s = 2^k; d = the exponent difference)

Why not the multiplier trick of the left-normalise: the high word of v*2^(32-s) is v>>s, but "no shift" would need the factor 2^32, which does not fit a 32-bit word. Instead, since a shift is
pure wiring in flex (any amount, #985): R = v >> s (a relay with the shift add-on), D = v - R (subtracting adder), M = D * b (b = the 0/1 word "bit k of d"), O = v - M. That is v when b = 0 and R when b = 1.
b comes from d with one relay << (31-k), one relay >> 1 (keeps the bit off the sign: the comparator is SIGNED) and a comparator >= 2^30.
Both operands of every two-operand cell are timed by route length: a subtract's minuend (v) is made to arrive EARLIER than its subtrahend. Real generated RTL (plain + stalls) == FlexGrid == Python. Requires iverilog.
"""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
from fp32_stage_builder_v1 import Grid  # noqa: E402

M32 = 0xFFFFFFFF


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fp32align_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def stage(k):
    s = 1 << k
    g = Grid(rows=8, cols=12)
    g.add("V", 2, 2)
    g.add("R", 3, 2, addon={"shift_en": 1, "direction": 1, "shift_amt": s})       # v >> s
    g.add("R2", 3, 3)
    g.add("D", 2, 3, "adder", {"subtract_mode": 1})                              # v - (v >> s)
    g.add("M", 2, 4, "mul")                                                      # (v - (v>>s)) * b
    g.add("O", 2, 5, "adder", {"subtract_mode": 1})                              # v - that
    g.add("OUT", 2, 6)
    g.add("E", 4, 1)
    g.add("EX", 4, 2)                                                             # one extra relay: the two operands of M must not arrive at the same hop
    g.add("B1", 4, 3, addon={"shift_en": 1, "direction": 0, "shift_amt": 31 - k})
    g.add("B2", 4, 4, addon={"shift_en": 1, "direction": 1, "shift_amt": 1})
    g.add("BC", 3, 4, "comparator", {"threshold": 1 << 30})
    for a, b in (("V", "D"), ("V", "R"), ("R", "R2"), ("R2", "D"), ("D", "M"), ("M", "O"), ("O", "OUT"), ("E", "EX"), ("EX", "B1"), ("B1", "B2"), ("B2", "BC"), ("BC", "M")):
        g.link(a, b)
    g.route("V", "O")
    return g.records()


def stream(k, seed):
    r = random.Random(seed)
    vs = [0, 1, M32, 0x00FFFFFF, 0x00800000, 0xABCDE000] + [r.getrandbits(32) for _ in range(10)]
    ds = [0, 1 << k, (1 << k) | 1, 31, 31 ^ (1 << k), 5] + [r.getrandbits(5) for _ in range(10)]
    return vs, ds


def run_vm(recs, vs, ds, ticks=400):
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen = []
    for v, d in zip(vs, ds):
        g.inject(*pos["V"], v)
        g.inject(*pos["E"], d)
        for _ in range(ticks):
            g.tick()
            c = g.cells[pos["OUT"]]
            if c.ram_data_valid:
                seen.append(c.ram_data_reg)
                c.ram_data_valid = False
    return seen


@pytest.mark.parametrize("k", [0, 1, 2, 3, 4])
@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_conditional_right_shift_stage(tmp, k, mode):
    recs = stage(k)
    vs, ds = stream(k, k)
    d, r = h.build(tmp, f"al{k}_{mode}", recs)
    assert r.returncode == 0, r.stderr[:1500]
    _, got = h.run_level(d, {"V": vs, "E": ds}, mode, 4, settle=2500)
    want = [(v >> (1 << k)) if (dd >> k) & 1 else v for v, dd in zip(vs, ds)]
    assert got["OUT"] == want
    assert any((dd >> k) & 1 for dd in ds) and any(not (dd >> k) & 1 for dd in ds)
    assert run_vm(recs, vs, ds) == want
