"""tests/vm/test_nor_adder_v1.py -- ledger #1036 addendum 48: the 32-bit adder made ONLY of nano gate cells (AND / OR / XOR) and relay / shift cells (tools/nor_adder_v1.py) equals real addition mod 2^32
in the generated flex RTL (plain and with random stalls) and in FlexGrid. Requires iverilog."""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
from fp_block_runner_v1 import run_rtl, run_vm  # noqa: E402
import nor_adder_v1 as na  # noqa: E402

M = 0xFFFFFFFF


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="noradd_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def vectors():
    r = random.Random(3)
    v = [(0, 0), (M, 1), (1, M), (M, M), (0x7FFFFFFF, 1), (0x55555555, 0xAAAAAAAA), (0xFFFFFFFE, 1), (0x80000000, 0x80000000)]
    v += [((1 << i) - 1, 1) for i in range(1, 33)]                  # a carry that travels exactly i bits
    v += [(r.getrandbits(32), r.getrandbits(32)) for _ in range(40)]
    return v


def test_only_nor_built_gates_and_wiring():
    g, _ = na.build_tight()
    assert g.problems() == []
    cores = {n["core"] for n in g.nodes.values()}
    assert cores == {"nano", "ram", "cross"}, cores                 # no adder, comparator, mask or other word cell
    assert {n["cfg"]["topology"] for n in g.nodes.values() if n["core"] == "nano"} == {na.AND, na.OR, na.XOR}
    assert all(set(n["addon"]) <= {"shift_en", "direction", "shift_amt"} for n in g.nodes.values())


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_nor_adder_rtl(tmp, mode):
    g, _ = na.build_tight()
    vs = vectors()
    got = run_rtl(tmp, "noradd", na.records(g), {"A": [a for a, _ in vs], "B": [b for _, b in vs]}, {"S": "E"}, mode, settle=40000, cycles=12000)["S"]
    assert len(got) == len(vs)
    assert got == [(a + b) & M for a, b in vs]


def test_nor_adder_flexgrid():
    g, _ = na.build_tight()
    vs = vectors()[:16]
    got = run_vm(na.records(g), {"A": [a for a, _ in vs], "B": [b for _, b in vs]}, {"S": "E"}, {}, ticks=300)["S"]
    assert got == [(a + b) & M for a, b in vs]


def test_the_test_bites():
    """A sum that is wrong must be caught: the final XOR becomes OR and the result differs."""
    g, _ = na.build_tight()
    g.nodes["S"]["cfg"]["topology"] = na.OR
    vs = [(1, 1), (3, 5)]
    got = run_vm(na.records(g), {"A": [a for a, _ in vs], "B": [b for _, b in vs]}, {"S": "E"}, {}, ticks=300)["S"]
    assert got != [(a + b) & M for a, b in vs]


# ---- the carrier line (addendum 49): the same adder in the standard-mode VM, and folded into a near-square block -------------------------------------------------------------------------
def test_folded_layout_adds_in_std_vm_flexgrid_and_rtl(tmp):
    import card_fit_v1 as cf
    from unicell_super_automaton_v1 import SuperGrid
    g, _ = na.build_folded()
    assert g.problems() == []
    recs = na.records(g)
    assert cf.array_cells(recs) < 200 < cf.array_cells(na.records(na.build_tight()[0]))        # the fold is what makes it fit the dense array
    vs = vectors()
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    for a, b in vs[:24]:                                                                       # standard-mode VM: the carrier line's reference
        G = SuperGrid(recs)
        G.inject(*pos["A"], a)
        G.inject(*pos["B"], b)
        for _ in range(400):
            G.tick()
        assert G.cells[pos["E"]].ram_data_reg == (a + b) & M, (hex(a), hex(b))
    for mode in ("plain", "stall"):
        got = run_rtl(tmp, "noradfold", recs, {"A": [a for a, _ in vs], "B": [b for _, b in vs]}, {"S": "E"}, mode, settle=40000, cycles=12000)["S"]
        assert got == [(a + b) & M for a, b in vs]


def test_std_vm_long_layout_too():
    from unicell_super_automaton_v1 import SuperGrid
    recs = na.records(na.build_tight()[0])
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    for a, b in vectors()[:12]:
        G = SuperGrid(recs)
        G.inject(*pos["A"], a)
        G.inject(*pos["B"], b)
        for _ in range(300):
            G.tick()
        assert G.cells[pos["E"]].ram_data_reg == (a + b) & M
