"""Session plan + checker (tools/hexn_session_plan_v1.py, tools/hexn_session_check_v1.py): the plan is valid (each routine four times, no routine twice in a row, goal key depends on first AND middle keys), and the checker finds every planned press in the real 27 Oct all-keys recording when given its true order, and reports a missing press, an extra press and a substituted press when the plan is altered. Python only."""
import os, sys, json, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_session_plan_v1 as P, hexn_session_check_v1 as C
EDGES = os.path.join(ROOT, "docs", "hex-n", "data", "esp_run_20261027_ir_all_keys_edges.csv")
def plan_with(keys):
    d = tempfile.mkdtemp(); p = os.path.join(d, "p.json"); json.dump({"runs": {"1": {"table_index": keys}}}, open(p, "w")); return p
def test_plan_valid():
    plan = json.load(open(os.path.join(ROOT, "docs", "hex-n", "sessions", "routines_plan_v1.json")))
    for run in plan["runs"].values():
        o = run["routine_order"]; assert sorted(o) == sorted("ABCD" * 4) and all(a != b for a, b in zip(o, o[1:])); assert len(run["keys"]) == 64 and len(run["table_index"]) == 64
    g = {}
    for r, k in P.ROUTINES.items(): g.setdefault((k[0], tuple(k[1:3])), set()).add(P.GOAL[r])
    assert all(len(v) == 1 for v in g.values()); assert len({P.GOAL[r] for r in "ABCD"}) == 2
    assert P.GOAL["A"] != P.GOAL["B"] and P.GOAL["C"] != P.GOAL["D"] and P.ROUTINES["A"][1:3] == P.ROUTINES["B"][1:3]
def test_checker_on_real_recording():
    true = list(range(21)) + list(range(13)); ok, cnt = C.check(EDGES, 1, plan_with(true), quiet=True); assert ok and cnt["match"] == 34
    ok, cnt = C.check(EDGES, 1, plan_with(true + [5]), quiet=True); assert not ok and cnt["missing"] == 1
    ok, cnt = C.check(EDGES, 1, plan_with(true[:10] + true[11:]), quiet=True); assert not ok and cnt["extra"] == 1
    t = list(true); t[7] = 20; ok, cnt = C.check(EDGES, 1, plan_with(t), quiet=True); assert not ok and cnt["sub"] == 1
