"""tests/vm/test_flex_free_shift_v1.py -- ledger #985 (Alan: the flex shift is just wiring, so it can be ANY amount 0..max bits, left or right -- not the std VM's sparse taps).

Every shift_amt 1..31 (the ICM field is 5 bits), left and right, on a ram relay in the FLEX family: generated RTL (plain + stalls) == FlexGrid == the plain Python shift.
The std VM keeps its own taps (untouched); on a std tap the flex result is identical to it; the SUB family still mirrors the std chain (tests/test_flexsub_addon_v1.py). Requires iverilog.
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
VALS = [0, 1, M32, 0x80000000, 0x12345678, 0xDEADBEEF, 0x00FF00FF] + [random.Random(5).getrandbits(32) for _ in range(5)]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="freeshift_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def design(n):
    g = Grid(rows=5, cols=6)
    g.add("X", 2, 1)
    g.add("L", 1, 1, addon={"shift_en": 1, "direction": 0, "shift_amt": n})
    g.add("R", 3, 1, addon={"shift_en": 1, "direction": 1, "shift_amt": n})
    g.add("EL", 1, 2)
    g.add("ER", 3, 2)
    for a, b in (("X", "L"), ("X", "R"), ("L", "EL"), ("R", "ER")):
        g.link(a, b)
    return g.records()


@pytest.mark.parametrize("n", range(1, 32))
def test_any_shift_amount_left_and_right(tmp, n):
    recs = design(n)
    d, r = h.build(tmp, f"fs{n}", recs)
    assert r.returncode == 0, r.stderr[:800]
    mode = "stall" if n % 2 else "plain"
    _, got = h.run_level(d, {"X": VALS}, mode, 4, settle=600)
    assert got["EL"] == [(v << n) & M32 for v in VALS]
    assert got["ER"] == [v >> n for v in VALS]
    g = fg.FlexGrid(recs, width=32)
    pos = {x.cell_id: (x.row, x.col) for x in recs}
    seen = {"EL": [], "ER": []}
    for v in VALS:
        g.inject(*pos["X"], v)
        for _ in range(60):
            g.tick()
            for e in seen:
                c = g.cells[pos[e]]
                if c.ram_data_valid:
                    seen[e].append(c.ram_data_reg)
                    c.ram_data_valid = False
    assert seen == {"EL": got["EL"], "ER": got["ER"]}
