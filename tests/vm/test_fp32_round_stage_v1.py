"""tests/vm/test_fp32_round_stage_v1.py -- ledger #984: STICKY + ROUND-TO-NEAREST-EVEN from real flex cells, no loop, no branch.

Input word X = significand(24) << 8 | low byte (bit 7 = guard, bits 6..0 = the bits below it). Every quantity is a 0/1 word made by one shift add-on relay and one comparator:
    lsb    = X[8]      : relay <<23 then >>1, comparator >= 2^30
    guard  = X[7]      : relay <<24 then >>1, comparator >= 2^30
    sticky = X[6:0]!=0 : relay <<25 then >>1, comparator >= 1          (the "reduce by one until even" loop of the design notes is not needed: the shift drops everything above the low bits,
                                                                  and a >= 1 comparison IS the any-bit-set test)
    t = sticky + lsb ; or = (t >= 1) ; u = guard + or ; up = (u >= 2)  =  guard AND (sticky OR lsb)   (adders + comparators; no nano gate needed)
    out = (X >> 8) + up                                         (an adder; a carry out to 2^24 is the rounding overflow, handled by the exponent step later)
NOTE the comparator is SIGNED (as in the VM): a bit isolated at bit 31 would read as negative, hence the extra >>1 relay that moves it to bit 30.
Compared with fp32_boundary_v1.round_to_nearest_even for every guard/sticky/lsb combination plus random words; generated RTL (plain + stalls) and FlexGrid. Requires iverilog.
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
from fp32_boundary_v1 import round_to_nearest_even  # noqa: E402
from fp32_stage_builder_v1 import Grid  # noqa: E402


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="fp32round_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def sh(left):
    return {"shift_en": 1, "direction": 0, "shift_amt": left} if left in (1, 2, 4, 8, 12, 16, 20, 24, 28) else {"shift_en": 1, "direction": 0, "shift_amt": left - left % 4 if left % 4 else left, "shift_fine": left % 4}


def build():
    R1 = {"shift_en": 1, "direction": 1, "shift_amt": 1}                           # >> 1: puts the isolated bit at bit 30, so the SIGNED comparator never sees a sign bit
    g = Grid(rows=10, cols=14)
    g.add("X", 3, 1)
    g.add("SIG", 2, 1, addon={"shift_en": 1, "direction": 1, "shift_amt": 8})
    g.add("STR", 3, 2, addon=sh(25))
    g.add("STR2", 3, 3, addon=R1)
    g.add("STC", 3, 4, "comparator", {"threshold": 1})
    g.add("LBR", 4, 1, addon=sh(23))
    g.add("LBR2", 5, 1, addon=R1)
    g.add("LBX", 5, 2)
    g.add("LBY", 5, 3)
    g.add("LBC", 5, 4, "comparator", {"threshold": 1 << 30})
    g.add("ADD1", 4, 4, "adder")
    g.add("ORC", 4, 5, "comparator", {"threshold": 1})
    g.add("GDR", 3, 0, addon=sh(24))
    g.add("GDR2", 2, 0, addon=R1)
    g.add("GDC", 1, 0, "comparator", {"threshold": 1 << 30})
    g.add("ADD2", 4, 6, "adder")
    g.add("UPC", 4, 7, "comparator", {"threshold": 2})
    g.add("ADD3", 4, 8, "adder")
    g.add("OUT", 4, 9)
    for a, b in (("X", "SIG"), ("X", "STR"), ("STR", "STR2"), ("STR2", "STC"), ("STC", "ADD1"), ("X", "LBR"), ("LBR", "LBR2"), ("LBR2", "LBX"), ("LBX", "LBY"), ("LBY", "LBC"), ("LBC", "ADD1"), ("ADD1", "ORC"),
                 ("X", "GDR"), ("GDR", "GDR2"), ("GDR2", "GDC"), ("ORC", "ADD2"), ("ADD2", "UPC"), ("UPC", "ADD3"), ("ADD3", "OUT")):
        g.link(a, b)
    g.route("SIG", "ADD3")
    g.route("GDC", "ADD2")
    return g.records()


def expected(x):
    sig, guard, sticky = x >> 8, (x >> 7) & 1, 1 if x & 0x7F else 0
    return round_to_nearest_even(sig, guard, sticky)


def words():
    r = random.Random(11)
    w = [(s << 8) | low for s in (0x800000, 0x800001, 0xFFFFFF, 0xABCDEF, 0xABCDEE) for low in (0, 1, 0x40, 0x7F, 0x80, 0x81, 0xC0, 0xFF)]
    return w + [(r.getrandbits(24) | 0x800000) << 8 | r.getrandbits(8) for _ in range(40)]


def run_vm(recs, vals, ticks=700):
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen = []
    for v in vals:
        g.inject(*pos["X"], v)
        for _ in range(ticks):
            g.tick()
            c = g.cells[pos["OUT"]]
            if c.ram_data_valid:
                seen.append(c.ram_data_reg)
                c.ram_data_valid = False
    return seen


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_sticky_and_round_nearest_even(tmp, mode):
    recs = build()
    vals = words()
    d, r = h.build(tmp, f"round_{mode}", recs)
    assert r.returncode == 0, r.stderr[:1500]
    _, got = h.run_level(d, {"X": vals}, mode, 4, settle=3000)
    want = [expected(x) for x in vals]
    assert got["OUT"] == want
    assert any(w != x >> 8 for w, x in zip(want, vals)) and any(w == x >> 8 for w, x in zip(want, vals))
    assert run_vm(recs, vals) == want
