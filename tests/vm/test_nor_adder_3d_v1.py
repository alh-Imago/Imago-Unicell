"""tests/vm/test_nor_adder_3d_v1.py -- ledger #1036 addendum 50: the six-neighbour toy grid with gate and shift cells (nano/experimental_3d_nor_v2.py) and the NOR-built adder laid out in it
(tools/nor_adder_3d_v1.py). VM ONLY: (1) the toy's gate / shift / relay behaviour is the standard-mode VM's, checked against SuperGrid on small flat designs; (2) the 3D adder equals real addition;
(3) the test bites; (4) the stage tile is what the formula says."""
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("..", "../../tools", "../../nano"):
    sys.path.insert(0, os.path.join(HERE, sub))
import experimental_3d_nor_v2 as m3  # noqa: E402
import nor_adder_3d_v1 as t3  # noqa: E402
import nor_adder_v1 as na  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

M = 0xFFFFFFFF


def flat_design(topo, shift, left):
    """B(0,0) -> Bd(0,1) -> gate(1,1) <- A(1,0); gate -> shift cell (1,2) -> E(1,3): one gate and one shift, in the standard-mode VM's vocabulary and in the toy's."""
    g = Grid(rows=3, cols=5)
    g.add("B", 0, 0)
    g.add("Bd", 0, 1)
    g.add("A", 1, 0)
    g.add("G", 1, 1, "nano", {"topology": topo, "ready": 1})
    g.add("SH", 1, 2, "ram", None, {"shift_en": 1, "direction": 0 if left else 1, "shift_amt": shift})
    g.add("E", 1, 3)
    for a, b in (("B", "Bd"), ("Bd", "G"), ("A", "G"), ("G", "SH"), ("SH", "E")):
        g.link(a, b)
    toy = m3.Grid3()
    for nm, cell in (("B", m3.Cell3()), ("Bd", m3.Cell3()), ("A", m3.Cell3()), ("G", m3.Cell3("gate", m3.TOPOLOGY[topo])), ("SH", m3.Cell3("relay", None, shift, left)), ("E", m3.Cell3())):
        toy.add((g.nodes[nm]["r"], g.nodes[nm]["c"], 0), cell)
    for a, b, _ in g.links:
        toy.link((g.nodes[a]["r"], g.nodes[a]["c"], 0), (g.nodes[b]["r"], g.nodes[b]["c"], 0))
    return na.records(g), toy


@pytest.mark.parametrize("topo", sorted(m3.TOPOLOGY))
@pytest.mark.parametrize("shift,left", [(0, True), (1, True), (4, False), (16, True)])
def test_toy_gate_and_shift_equal_the_standard_vm(topo, shift, left):
    recs, toy = flat_design(topo, shift, left)
    r = random.Random(topo * 7 + shift)
    for a, b in [(0, 0), (M, M), (M, 0), (0x12345678, 0x0F0F0F0F)] + [(r.getrandbits(32), r.getrandbits(32)) for _ in range(6)]:
        G = SuperGrid(recs)
        pos = {x.cell_id: (x.row, x.col) for x in recs}
        G.inject(*pos["A"], a)
        G.inject(*pos["B"], b)
        for _ in range(60):
            G.tick()
        want = G.cells[pos["E"]].ram_data_reg
        _t, got = toy.run({(1, 0, 0): a, (0, 0, 0): b}, (1, 3, 0))
        assert got == want, (hex(topo), shift, left, hex(a), hex(b))


def test_3d_adder_equals_addition():
    res = t3.measure()
    g, pos = t3.build_stacked_grid(tuple(res["orientations"]), res["seed"])
    assert t3.check(g, pos, 150) is not None
    assert res["cells"] == len(g.cells) and res["gates"] == 17 and res["shift_cells"] == 10


def test_3d_adder_uses_only_gates_shifts_and_relays_and_fewer_cells_than_2d():
    res = t3.measure()
    g, _ = t3.build_stacked_grid(tuple(res["orientations"]), res["seed"])
    assert {c.kind for c in g.cells.values()} == {"relay", "gate"}
    assert {c.gate for c in g.cells.values() if c.kind == "gate"} == {"AND", "OR", "XOR"}
    assert res["cells"] < len(na.build_tight()[0].nodes)          # the whole point: six faces need fewer relays than four


def test_the_3d_test_bites():
    res = t3.measure()
    g, pos = t3.build_stacked_grid(tuple(res["orientations"]), res["seed"])
    g.cells[pos["S"]].gate = "OR"
    assert t3.check(g, pos, 5) is None


def test_stage_tile_formula_has_only_two_collision_free_orientation_sequences():
    import itertools
    ok = [p for p in itertools.product(range(6), repeat=4) if len(set(t3.stacked_positions((0,) + p).values())) == len(t3.stacked_positions((0,) + p))]
    assert sorted((0,) + p for p in ok) == sorted(t3.PERMS)
