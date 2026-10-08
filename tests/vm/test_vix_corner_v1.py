"""tests/vm/test_vix_corner_v1.py -- ledger #1035: the CORNER wiring core in the VIX / super-cell VM (SuperGrid): `turn` 0 pairs E-N and W-S, `turn` 1 pairs E-S and W-N, both directions, four independent slices."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
import vm_introspection_v1 as intro  # noqa: E402

FACE = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}
OPP = {"n": "s", "s": "n", "e": "w", "w": "e"}
PAIRS = {0: {"e": "n", "n": "e", "w": "s", "s": "w"}, 1: {"e": "s", "s": "e", "w": "n", "n": "w"}}


def build(turn, ins):
    """Corner X at (2,2); for every entry arm in `ins` a source ram S<arm> pointing at X, and for its partner arm a sink ram K<arm>."""
    recs = [v3.IcmV3Record(cell_id="X", row=2, col=2, core="corner", core_config={"turn": turn})]
    for a in ins:
        dr, dc = FACE[a]
        recs.append(v3.IcmV3Record(cell_id="S" + a, row=2 + dr, col=2 + dc, core="ram", core_config={"upstream_mask": [], "downstream_mask": [OPP[a]]}))
        o = PAIRS[turn][a]
        dr, dc = FACE[o]
        recs.append(v3.IcmV3Record(cell_id="K" + o, row=2 + dr, col=2 + dc, core="ram", core_config={"upstream_mask": [OPP[o]], "downstream_mask": []}))
    return recs


@pytest.mark.parametrize("turn", [0, 1])
@pytest.mark.parametrize("ins", [("w", "e"), ("n", "s"), ("w", "n"), ("e", "s")])
def test_two_arms_turn_to_their_partners_at_once(turn, ins):
    # arms used as entries must not also be exits: pick pairs whose partners are the other two arms
    if set(PAIRS[turn][a] for a in ins) & set(ins):
        pytest.skip("an entry arm would also be an exit arm")
    recs = build(turn, ins)
    g = SuperGrid(recs)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    for k, a in enumerate(ins):
        g.inject(*pos["S" + a], 100 + k)
    got = {}
    for _ in range(40):
        g.tick()
        for a in ins:
            o = PAIRS[turn][a]
            c = g.cells[pos["K" + o]]
            if c.ram_data_valid:
                got[o] = c.ram_data_reg
                c.ram_data_valid = False
    for k, a in enumerate(ins):
        assert got[PAIRS[turn][a]] == 100 + k, (turn, a, got)


def test_two_words_in_a_row_on_one_arm_both_arrive_in_order():
    recs = build(0, ("w",))
    g = SuperGrid(recs)
    sw = next((r.row, r.col) for r in recs if r.cell_id == "Sw")
    ks = g.cells[next((r.row, r.col) for r in recs if r.cell_id == "Ks")]
    seen = []
    g.inject(*sw, 11)
    for t in range(60):
        if t == 8:
            g.inject(*sw, 22)
        g.tick()
        if ks.ram_data_valid:
            seen.append(ks.ram_data_reg)
            ks.ram_data_valid = False
    assert seen == [11, 22]


def test_introspection_reports_the_corner():
    g = SuperGrid(build(1, ("w",)))
    d = intro.cell_at(g, 2, 2)
    assert d["core"] == "corner" and d["corner"]["turn"] == 1
