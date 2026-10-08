"""tests/vm/test_fp32_align_chain_v1.py -- ledger #988: the full ALIGN (variable right shift by an exponent difference d) from real flex cells: six conditional-right-shift stages
(see test_fp32_align_stage_v1.py) for the bits of d: shift 1, 2, 4, 8, 16 when bit k of d is set, and shift 31 when d >= 32 (the clamp: a comparator on d itself).
A d >= 32 therefore leaves at most bit 0 of the word (the significand sits in the top 24 bits of the 32-bit word, bits 7..0 are guard/sticky region), never a wrong high bit.
The value runs through the six stages; d runs along a bus under them and each stage takes its bit. Real generated RTL (plain + stalls) == FlexGrid == Python. Requires iverilog.
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
SHIFTS = (1, 2, 4, 8, 16, 31)
PITCH = 5


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fp32alignchain_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def build():
    """Per stage (pitch 5): V -> {D, R(shift) -> R2 -> D}; D -> M(*b) -> O; v itself goes V -> (1,2) -> (1,3) -> O (O sits NORTH of M so the minuend arrives well before M's product); O -> 3 relays -> next V."""
    g = Grid(rows=8, cols=PITCH * 6 + 4)
    for k, s in enumerate(SHIFTS):
        c, p = PITCH * k, f"A{k}."
        g.add(p + "V", 2, 2 + c)
        g.add(p + "R", 3, 2 + c, addon={"shift_en": 1, "direction": 1, "shift_amt": s})
        g.add(p + "R2", 3, 3 + c)
        g.add(p + "D", 2, 3 + c, "adder", {"subtract_mode": 1})
        g.add(p + "M", 2, 4 + c, "mul")
        g.add(p + "O", 1, 4 + c, "adder", {"subtract_mode": 1})
        g.add(p + "VA", 1, 2 + c)
        g.add(p + "VB", 1, 3 + c)
        g.add(p + "E", 4, 1 + c)
        g.add(p + "EX", 4, 2 + c)
        last = k == 5
        g.add(p + "B1", 4, 3 + c, addon=None if last else {"shift_en": 1, "direction": 0, "shift_amt": 31 - k})
        g.add(p + "B2", 4, 4 + c, addon=None if last else {"shift_en": 1, "direction": 1, "shift_amt": 1})
        g.add(p + "BC", 3, 4 + c, "comparator", {"threshold": 32 if last else 1 << 30})
        for a, b in (("V", "D"), ("V", "R"), ("R", "R2"), ("R2", "D"), ("D", "M"), ("M", "O"), ("V", "VA"), ("VA", "VB"), ("VB", "O"), ("E", "EX"), ("EX", "B1"), ("B1", "B2"), ("B2", "BC"), ("BC", "M")):
            g.link(p + a, p + b)
        g.add(f"P{k}", 5, 1 + c)                              # the d bus (row 5): each bus cell feeds this stage's E and the next bus cell
        g.link(f"P{k}", p + "E")
    return g


def finish(g):
    for k in range(1, 6):
        g.route(f"P{k - 1}", f"P{k}")
    for k in range(5):
        g.route(f"A{k}.O", f"A{k + 1}.V")
    g.add("OUT", 0, 4 + PITCH * 5)
    g.link("A5.O", "OUT")
    return g.records()


def aligned(v, d):
    """Independent of the cell wiring: a plain shift by d, and for d >= 32 the clamp (shift by d mod 32, then 31 more)."""
    return v >> d if d < 32 else (v >> (d & 31)) >> 31


def run_vm(recs, vs, ds, ticks=900):
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen = []
    for v, d in zip(vs, ds):
        g.inject(*pos["A0.V"], v)
        g.inject(*pos["P0"], d)
        for _ in range(ticks):
            g.tick()
            c = g.cells[pos["OUT"]]
            if c.ram_data_valid:
                seen.append(c.ram_data_reg)
                c.ram_data_valid = False
    return seen


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_align_chain(tmp, mode):
    recs = finish(build())
    r = random.Random(4)
    vs = [M32, 0xFFFFFF00, 0x80000000, 0x12345678, 1, 0] + [r.getrandbits(32) for _ in range(20)]
    ds = [0, 1, 7, 31, 32, 33, 5, 8, 16, 24, 40, 100] + [r.randrange(0, 60) for _ in range(14)]
    d, res = h.build(tmp, f"alch_{mode}", recs)
    assert res.returncode == 0, res.stderr[:1500]
    _, got = h.run_level(d, {"A0_V": vs, "P0": ds}, mode, 4, settle=4000)
    want = [aligned(v, dd) for v, dd in zip(vs, ds)]
    assert got["OUT"] == want, [(hex(v), dd, hex(a), hex(b)) for v, dd, a, b in zip(vs, ds, got["OUT"], want) if a != b][:3]
    assert run_vm(recs, vs, ds) == want
