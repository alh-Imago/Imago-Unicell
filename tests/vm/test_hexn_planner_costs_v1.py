"""tests/vm/test_hexn_planner_costs_v1.py -- the corrected planner costs (hexn_wrgrid_v13, hexn_bases_v4; 2 Nov 2026). The numbers are the first tile's yosys counts (ledger 2 Nov 23:58); v12 / v3 stay as they were."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_wrgrid_v12 as G12, hexn_wrgrid_v13 as G13, hexn_bases_v3 as B3, hexn_bases_v4 as B4


def test_constants_and_unary_cost():
    assert G13.CELLTYPES["UN"][1] == 124 and G13.ROUTE_COST == 24 and G13.TILE_EXTRA == 39
    assert G12.CELLTYPES["UN"][1] == 43                               # the old file is untouched
    for t in ("AL", "JN", "BR", "MG", "PR", "SQ", "LT"):
        assert G13.CELLTYPES[t][1] == G12.CELLTYPES[t][1]             # only the unary core was re-measured


def test_base_cost_formula_by_hand():
    b = B4.make_pattern("math", 9)
    works = len(b.type); routing = b.R * b.C - works; ram = len(b.ram)
    want = sum(G13.CELLTYPES[t][1] + 39 for t in b.type.values()) + (routing - ram) * 24 + ram * 87
    assert b.cost() == want
    assert B3.make_pattern("math", 9).cost() == 4784                  # v3 still gives its old figure


def test_corrected_patterns_are_smaller_not_larger_overall():
    for name in ("math", "logic", "mixed", "ram2", "banded"):
        for n in (7, 9, 11, 13, 15):
            assert B4.make_pattern(name, n).cost() < B3.make_pattern(name, n).cost(), (name, n)


def test_same_designs_still_fit_with_the_same_planner_behaviour():
    t = B4.B2.all_tasks()["old/scale_offset"]
    b3, b4 = B3.make_pattern("math", 9), B4.make_pattern("math", 9)
    assert B3.fits(b3, t) is not None and B4.fits(b4, t) is not None
