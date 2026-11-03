"""tests/vm/test_hexn_hexplan_v1.py - the HEX planner (tools/hexn_wrgrid_hex_v1.py, 3 Nov 2026): plans and simulates designs on the six-face hex grid; simulation equals the word-level reference."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools"))
import hexn_wrgrid_hex_v1 as H
N = H.Node9


def _types(n, off, mix):
    H.OFFSET = off; wc = H.Grid12(n, n).work_cells(); seq = []; c = dict(mix)
    while any(c.values()):
        for k in list(c):
            if c[k]: seq.append(k); c[k] -= 1
    return {w: t for w, t in zip(wc, (seq + ["AL"] * len(wc))[:len(wc)])}


def test_simple_design_plans_and_equals_the_reference():
    ct = _types(7, 1, {"UN": 2, "AL": 3, "JN": 6, "BR": 2, "MG": 1})
    nodes = [N("a", "add", ["x", "y"]), N("r", "sub", ["a", "z"])]
    P = H.plan10(nodes, ["x", "y", "z"], ["r"], 7, 7, ct, tries=14)
    ok, why = H.check_task(P, nodes, ["x", "y", "z"], ["r"]); assert ok, why
    assert H.simulate9(P, dict(x=100, y=37, z=5), ["r"])["r"][0][1] == 132
    for i in P.g.work.values():
        assert set(i["cfg"].get("fi", {}).values()) <= set(H.HEXF)            # real hex faces only
    for p in P.g.pads_in.values(): assert p[1] == 0 and not P.g.is_work(*p)  # inputs on the west edge, on routing cells
    for p in P.g.pads_out.values(): assert p[1] == 6 and not P.g.is_work(*p)


def test_branch_merge_design_on_the_hex_grid():
    ct = _types(9, 1, {"UN": 4, "AL": 5, "JN": 11, "BR": 4, "MG": 3})
    nodes = [N("br", "branch", ["x", "y"], ["lo", "hi"], cfg=dict(route_lt=1, route_eq=1, route_gt=2, emit=3)), N("m", "merge", ["lo", "hi"], cfg=dict(mode=2)), N("r", "add", ["m", "c"])]
    P = H.plan10(nodes, ["x", "y", "c"], ["r"], 9, 9, ct, tries=14)
    ok, why = H.check_task(P, nodes, ["x", "y", "c"], ["r"]); assert ok, why


def test_work_cell_colour_offset_moves_the_work_cells():
    H.OFFSET = 1; a = set(H.Grid12(7, 7).work_cells()); H.OFFSET = 2; b = set(H.Grid12(7, 7).work_cells()); H.OFFSET = 0
    assert a and b and not (a & b)
