"""tests/vm/test_hexn_facechoice_v1.py - FACE CHOICE in the square planner (hexn_wrgrid_v21, 3 Nov 2026, Alan 15:13)."""
import os, sys, random
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_wrgrid_v20 as G20, hexn_wrgrid_v21 as G21, hexn_pattern_designer_v10 as D


def _base(rec): return D.make_base(rec)


def _plan(G, base, t, tries=14): return G.plan10(t[0], t[1], t[2], base.R, base.C, base.type, tries=tries, ram=base.ram, lead_k=base.lead_k)


def test_standard_plans_are_unchanged():
    base = _base({"n": 7, "counts": {"UN": 2, "AL": 2, "BR": 1, "MG": 2, "JN": 2}, "ram": "none"})
    N20, N21 = G20.Node9, G21.Node9
    mk = lambda N: ([N("br", "branch", ["x", "y"], ["lo", "hi"], cfg=dict(route_lt=1, route_eq=1, route_gt=2, emit=3)), N("m", "merge", ["lo", "hi"], cfg=dict(mode=2)), N("r", "add", ["m", "c"])], ["x", "y", "c"], ["r"])
    a, b = _plan(G20, base, mk(N20)), _plan(G21, base, mk(N21))
    ja = {k: (v["op"], v["cfg"]) for k, v in a.g.work.items()}; jb = {k: (v["op"], v["cfg"]) for k, v in b.g.work.items()}
    assert ja == jb and a.g.route == b.g.route and not any("fi" in v["cfg"] for v in b.g.work.values())


def test_a_design_with_no_standard_plan_gets_one_with_chosen_faces():
    base = _base({"n": 7, "counts": {"UN": 2, "AL": 3, "BR": 1, "MG": 1, "JN": 2}, "ram": "none"})
    mk = lambda N: ([N("a", "shl", ["x"], k=1), N("b", "add", ["a", "y"]), N("c", "min", ["b", "z"]), N("r", "max", ["c", "w"])], ["x", "y", "z", "w"], ["r"])
    try: _plan(G20, base, mk(G20.Node9)); old = True
    except RuntimeError: old = False
    assert not old
    t = mk(G21.Node9); P = _plan(G21, base, t)
    assert G21.check_task(P, *t)[0]
    assert sum(1 for v in P.g.work.values() if "fi" in v["cfg"] or "fo" in v["cfg"]) >= 1


def test_generator_puts_the_chosen_faces_in_the_tile_word():
    import hexn_pattern_gen_v10 as P10, hexn_tile_cfg_jn_v1 as CJ
    cell = dict(type="JN", kind="add", mode="join", k=0, cfg=dict(fi={"W": "N", "N": "S"}, fo={"E": "W"}), ins=["a", "b"], outs=["r"])
    fi, fo, chosen = P10._faces(cell)
    assert chosen and fi == {"W": "N", "N": "S"} and fo == {"E": "W"}
    u = CJ.unpack(CJ.pack({}, fi["W"], fi["N"], (fo["E"],), "add"))
    assert u["sela"] == 0 and u["selb"] == 2 and u["result_to"] == [3]
    assert P10._faces(dict(cfg={}))[2] is False
