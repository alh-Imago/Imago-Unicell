"""tests/vm/test_hexn_bases_v1.py -- base designs (bitstreams), fitting a design onto them, the fewest-bitstreams library, new-base suggestion and the program (tools/hexn_bases_v1.py)."""
import os, sys, random
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_bases_v1 as B
import hexn_wrgrid_v10 as G

N = G.Node9
ALL = B.all_tasks()
SMALL = {k: ALL[k] for k in ("old/scale_offset", "old/mid", "old/diff_abs", "new/merge_two", "new/prio3", "new/branch_route")}


def _replay_ok(base, program, task, trials=4):
    rnd = random.Random(2)
    for _ in range(trials):
        iv = {n: rnd.randrange(1 << 20) for n in task[1]}
        cap = B.run_program(base, program, task, iv); ref = G.ref9(task[0], iv)
        for o in task[2]:
            got = [w for _, w in cap[o]]; ordd, want = ref[o]
            if (got != want) if ordd else (sorted(got) != sorted(want)): return False
    return True


def test_base_layout_and_cost():
    b = B.Base(9, {"JN": 2, "BR": 1})
    assert sum(1 for t in b.type.values() if t == "JN") == 2 and sum(1 for t in b.type.values() if t == "BR") == 1 and len(b.type) == 16
    assert sum(1 for t in b.type.values() if t == "AL") == 13           # the spare cells are cheap aligned cores
    assert b.cost() == 13 * 43 + 2 * 141 + 154 + (81 - 16) * 60         # routing cells cost 60 once a self-timed type is present
    assert B.Base(9, {"AL": 3}).cost() == 16 * 43 + 65 * 30


def test_fit_rules():
    d = ALL["old/diff_abs"]                                              # sub, sub, max: needs a join core for max
    assert not B.fits(B.Base(9, {"AL": 16}), d)                          # aligned-only cells cannot compare
    assert B.fits(B.Base(9, {"JN": 1}), d)
    assert not B.fits(B.Base(9, {"JN": 4}), ALL["new/prio3"])            # no priority cell on the base
    assert B.fits(B.Base(9, {"PR": 1}), ALL["new/prio3"])


def test_library_and_program_replay():
    big = B.build_library(SMALL, budget=B.BUDGET_TANG)
    assert len(big) == 1                                                 # one base hosts all six and stays inside the budget
    tiny = B.build_library(SMALL, budget=1)
    assert len(tiny) == len(SMALL)                                    # nothing can merge
    mid = B.build_library(SMALL, budget=4000)
    assert 1 <= len(mid) <= len(SMALL)
    for base, members in mid:
        assert base.cost() <= 4000 or len(members) == 1
        for m in members:
            P = B.fits(base, SMALL[m]); assert P, (base, m)             # every member really runs on its base
            d = B.place([(base, members)], SMALL[m]); assert d["decision"] == "fits"
            assert _replay_ok(d["base"], d["program"], SMALL[m]), m


def test_new_base_and_refusals():
    lib = B.build_library(SMALL, budget=4000)
    two_br = ([N("b1", "branch", ["x", "y"], ["lo1", "hi1"], cfg=dict(route_lt=1, route_eq=1, route_gt=2, emit=1)),
               N("b2", "branch", ["y", "z"], ["lo2", "hi2"], cfg=dict(route_lt=1, route_eq=1, route_gt=2, emit=1)),
               N("m", "merge", ["lo1", "lo2"], cfg=dict(mode=2))], ["x", "y", "z"], ["m", "hi1", "hi2"])
    d = B.place(lib, two_br, budget=4000, members=SMALL)
    assert d["decision"] in ("extend", "new") and sum(1 for t in d["base"].type.values() if t == "BR") >= 2
    assert _replay_ok(d["base"], d["program"], two_br)
    tree = ([N("p1", "prio", ["x", "y", "z"], cfg=dict(mask=7, ranks=(0, 1, 2, 3), mode=0)), N("p2", "prio", ["p1", "w", "v"], cfg=dict(mask=7, ranks=(0, 1, 2, 3), mode=0))], ["x", "y", "z", "w", "v"], ["p2"])
    d = B.place(lib, tree, budget=4000, members=SMALL)
    assert d["decision"] == "refused" and "wrong" in d["reason"]         # a priority fed by a priority loses a word: no base can host it
    cond = ([N("b1", "branch", ["x", "y"], ["lo", "hi"]), N("b2", "branch", ["lo", "z"], ["l2", "h2"])], ["x", "y", "z"], ["l2", "h2", "hi"])
    assert B.place(lib, cond, budget=4000, members=SMALL)["decision"] == "refused"
