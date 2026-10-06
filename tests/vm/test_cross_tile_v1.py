"""tests/vm/test_cross_tile_v1.py -- ledger #990: the CROSSING tile (core "cross", Alan 6 Oct 2026): W<->E and N<->S straight through, no control, ONE TICK PER TILE per direction of travel (Alan: "add the tick as 1 per tile, as with all other cores").
It exists because planar routing of a real design (the fp adder) hit "walls": two lanes that must cross. Checked in the generated RTL (plain + random stalls: the netlist splice makes the
crossing a direct wire), in FlexGrid (neighbor_pos steps into the tile's register slice for that direction), and in the layout engine (a route may pass straight through another route's relay; unroute gives the tile back).
Bite check: if the tile were an ordinary relay (ram) the two streams would be MIXED -- the test shows they are not. Requires iverilog."""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
from fp_block_runner_v1 import run_rtl, run_vm  # noqa: E402
from flex_layout_v1 import Grid, LayoutError  # noqa: E402


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="crosstile_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def tile(core):
    g = Grid(rows=6, cols=6)
    for n, r, c, k in [("a0", 2, 0, "ram"), ("a1", 2, 1, "ram"), ("X", 2, 2, core), ("a2", 2, 3, "ram"), ("a3", 2, 4, "ram"),
                       ("b0", 0, 2, "ram"), ("b1", 1, 2, "ram"), ("b2", 3, 2, "ram"), ("b3", 4, 2, "ram")]:
        g.add(n, r, c, k)
    for a, b in [("a0", "a1"), ("a1", "X"), ("X", "a2"), ("a2", "a3"), ("b0", "b1"), ("b1", "X"), ("X", "b2"), ("b2", "b3")]:
        g.link(a, b)
    return g


def streams(n=20, seed=1):
    r = random.Random(seed)
    return [r.getrandbits(32) for _ in range(n)], [r.getrandbits(32) for _ in range(n)]


@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_two_streams_cross_in_rtl(tmp, mode):
    A, B = streams()
    got = run_rtl(tmp, "x_" + mode, tile("cross").records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"}, mode, settle=400)
    assert got["A"] == A and got["B"] == B


def test_two_streams_cross_in_vm():
    A, B = streams()
    vm = run_vm(tile("cross").records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"}, {}, ticks=60)
    assert vm["A"] == A and vm["B"] == B


def test_bite_an_ordinary_relay_would_mix_the_streams(tmp):
    A, B = streams()
    got = run_rtl(tmp, "x_ram", tile("ram").records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"}, "plain", settle=400)
    assert not (got["A"] == A and got["B"] == B)


def test_layout_route_crosses_and_unroute_restores(tmp):
    g = Grid(rows=8, cols=8)
    for n, r, c in (("a0", 3, 0), ("a3", 3, 7), ("b0", 0, 4), ("b3", 7, 4)):
        g.add(n, r, c)
    g.route("a0", "a3")
    with pytest.raises(LayoutError):
        g.route("b0", "b3")                                   # blocked, and crossing is opt-in
    g.route("b0", "b3", cross=True)
    assert [k for k, v in g.nodes.items() if v["core"] == "cross"] and len(g.crossed) == 1
    h = g.hops()
    assert h["a3"] == 8 and h["b3"] == 8                      # one tick per tile: the owner's relay (6 relays + the end cell) and the crossing route (5 relays + the tile + the end cell)
    A, B = streams(12, 2)
    got = run_rtl(tmp, "xr", g.records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"}, "stall", settle=500)
    assert got["A"] == A and got["B"] == B
    vm = run_vm(g.records(), {"a0": A, "b0": B}, {"A": "a3", "B": "b3"}, {}, ticks=80)
    assert vm["A"] == A and vm["B"] == B
    with pytest.raises(LayoutError):
        g.unroute("a0", "a3")                                 # the owner is crossed: unroute the crossing route first
    g.unroute("b0", "b3")
    assert not g.crossed and all(v["core"] == "ram" for v in g.nodes.values())


def test_each_tile_costs_exactly_one_tick_per_direction(tmp):
    """The tile is one register slice per direction: a stream through a cross arrives exactly as late as through a plain relay (RTL and VM), and the two axes do not slow each other."""
    A, B = streams(8, 5)
    for core in ("cross", "ram"):
        recs = tile(core).records()
        vm = run_vm(recs, {"a0": A[:1], "b0": B[:1]} if core == "cross" else {"a0": A[:1]}, {"A": "a3", **({"B": "b3"} if core == "cross" else {})}, {}, ticks=1)
    # arrival tick of the first word at a3, counted tick by tick, must be the same as through a plain relay in the same place
    import flex_grid_v1 as fg

    def first_tick(core):
        g = fg.FlexGrid(tile(core).records(), width=32)
        g.inject(2, 0, 7)
        cell = g.cells[(2, 4)]
        for t in range(1, 60):
            g.tick()
            if cell.ram_data_valid:
                return t
        return None
    assert first_tick("cross") == first_tick("ram") is not None


def test_two_crossings_in_a_row_rtl_and_vm(tmp):
    """Two crossing tiles side by side on one lane (each a slice): the A stream goes W->E through both while two B streams go N->S through one tile each."""
    g = Grid(rows=6, cols=7)
    for n, r, c, k in [("a0", 2, 0, "ram"), ("a1", 2, 1, "ram"), ("X1", 2, 2, "cross"), ("X2", 2, 3, "cross"), ("a2", 2, 4, "ram"), ("a3", 2, 5, "ram"),
                       ("b0", 0, 2, "ram"), ("b1", 1, 2, "ram"), ("b2", 3, 2, "ram"), ("b3", 4, 2, "ram"),
                       ("c0", 0, 3, "ram"), ("c1", 1, 3, "ram"), ("c2", 3, 3, "ram"), ("c3", 4, 3, "ram")]:
        g.add(n, r, c, k)
    for a, b in [("a0", "a1"), ("a1", "X1"), ("X1", "X2"), ("X2", "a2"), ("a2", "a3"), ("b0", "b1"), ("b1", "X1"), ("X1", "b2"), ("b2", "b3"), ("c0", "c1"), ("c1", "X2"), ("X2", "c2"), ("c2", "c3")]:
        g.link(a, b)
    A, B = streams(15, 7)
    C = [x ^ 0xA5A5A5A5 for x in B]
    ent, ex = {"a0": A, "b0": B, "c0": C}, {"A": "a3", "B": "b3", "C": "c3"}
    for mode in ("plain", "stall"):
        got = run_rtl(tmp, "x2_" + mode, g.records(), ent, ex, mode, settle=600)
        assert got == {"A": A, "B": B, "C": C}
    assert run_vm(g.records(), ent, ex, {}, ticks=80) == {"A": A, "B": B, "C": C}
