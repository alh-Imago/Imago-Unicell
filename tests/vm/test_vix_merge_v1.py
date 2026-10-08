"""tests/vm/test_vix_merge_v1.py -- ledger #1036: the MERGE core in the VIX / super-cell VM (the flex merge_cell_v4sa as a main-theme core).
Faces: A = first set bit of upstream_mask in N,S,E,W order, B = second. mode 0 A only, 1 B only, 2 arbitrate (round-robin, one at a time), 3 join-or (wait for both, output A|B)."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
import vm_introspection_v1 as intro  # noqa: E402


def design(mode):
    """N source (0,1) and W source (1,0) feed the merge M (1,1); sink K (1,2). A = N, B = W."""
    return [v3.IcmV3Record(cell_id="SN", row=0, col=1, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["s"]}),
            v3.IcmV3Record(cell_id="SW", row=1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}),
            v3.IcmV3Record(cell_id="M", row=1, col=1, core="merge", core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"], "mode": mode}),
            v3.IcmV3Record(cell_id="K", row=1, col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]


def run(mode, sends, ticks=80):
    """sends: list of (tick, 'N'|'W', value). Returns the words the sink received, in order."""
    g = SuperGrid(design(mode))
    k, seen = g.cells[(1, 2)], []
    for t in range(ticks):
        for (tt, who, v) in sends:
            if tt == t:
                g.inject(*((0, 1) if who == "N" else (1, 0)), v)
        g.tick()
        if k.ram_data_valid:
            seen.append(k.ram_data_reg)
            k.ram_data_valid = False
    return seen


def test_a_only_passes_a_and_never_takes_b():
    assert run(0, [(0, "N", 5), (0, "W", 9)]) == [5]


def test_b_only_passes_b_and_never_takes_a():
    assert run(1, [(0, "N", 5), (0, "W", 9)]) == [9]


def test_arbitrate_takes_one_at_a_time_and_loses_nothing():
    seen = run(2, [(0, "N", 5), (0, "W", 9)])
    assert sorted(seen) == [5, 9] and len(seen) == 2             # both arrive, never fused (5|9 would be 13)


def test_arbitrate_alternates_when_both_keep_coming():
    seen = run(2, [(0, "N", 1), (0, "W", 2), (10, "N", 3), (10, "W", 4)], ticks=120)
    assert sorted(seen) == [1, 2, 3, 4]


def test_arbitrate_passes_a_lone_word_from_either_side():
    assert run(2, [(0, "W", 7)]) == [7]
    assert run(2, [(0, "N", 8)]) == [8]


def test_join_or_waits_for_both_then_outputs_the_or():
    assert run(3, [(0, "N", 0x0F), (0, "W", 0xF0)]) == [0xFF]
    assert run(3, [(0, "N", 0x0F)]) == []                          # one half alone never goes out
    assert run(3, [(0, "N", 0x0F), (30, "W", 0xF0)]) == [0xFF]     # arrival times may differ


def test_join_or_does_two_items_in_a_row():
    assert run(3, [(0, "N", 1), (0, "W", 2), (20, "N", 4), (20, "W", 8)], ticks=140) == [3, 12]


def test_config_round_trip_and_introspection():
    recs = design(3)
    f = v3.pack_core_config("merge", recs[2].core_config)
    assert v3.unpack_core_config("merge", f)["mode"] == 3
    g = SuperGrid(recs)
    d = intro.cell_at(g, 1, 1)
    assert d["core"] == "merge" and d["merge"]["mode"] == 3
