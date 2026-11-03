"""tests/vm/test_hexn_hexvm_v1.py - the six-face program file (icm-hexn-v4) and the hex serial VM (hexn_vm_v7): a plan written out and replayed from the file alone gives the planner's words (3 Nov 2026)."""
import copy, json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools"))
import hexn_wrgrid_hex_v3 as H
import hexn_icm_export_v4 as X
import hexn_vm_v7 as V
N = H.Node9
MIX = {"UN": 2, "AL": 3, "JN": 4, "BR": 1, "MG": 1, "PR": 4}


def _types(n, off):
    H.OFFSET = off; wc = H.Grid12(n, n).work_cells(); seq = []; c = dict(MIX)
    while any(c.values()):
        for k in list(c):
            if c[k]: seq.append(k); c[k] -= 1
    return {w: t for w, t in zip(wc, (seq + ["AL"] * len(wc))[:len(wc)])}


def _case(kind, n=7, off=2):
    ct = _types(n, off)
    if kind == "prio4": nodes, ins, outs = [N("p", "prio", ["x", "y", "z", "w"], cfg=dict(mask=15, ranks=(0, 1, 2, 3), mode=0))], ["x", "y", "z", "w"], ["p"]
    else: nodes, ins, outs = [N("a", "add", ["x", "y"]), N("r", "sub", ["a", "z"])], ["x", "y", "z"], ["r"]
    P = H.plan10(nodes, ins, outs, n, n, ct, tries=40)
    return P, ct, ins, outs


@pytest.mark.parametrize("kind", ["prio4", "addsub"])
def test_file_replay_equals_the_planner(kind):
    P, ct, ins, outs = _case(kind)
    d = json.loads(json.dumps(X.to_icm(X.program_of(P, ct, "t"))))          # through text, as a file would be
    inp = {k: 10 * (i + 3) for i, k in enumerate(ins)}
    H.OFFSET = 2; want = H.simulate9(P, inp, outs); H.OFFSET = 0
    assert V.HexVM.load(d).run(inp) == want and all(want[o] for o in outs)
    assert H.OFFSET == 0                                                    # the VM puts the global back


def test_damaged_file_is_refused():
    P, ct, ins, outs = _case("addsub")
    d = X.to_icm(X.program_of(P, ct, "t"))
    bad = copy.deepcopy(d); bad["records"][0]["col"] += 0; bad["offset"] = 1
    with pytest.raises(ValueError): X.from_icm(bad)
    bad = copy.deepcopy(d); bad["faces"] = 4
    with pytest.raises(ValueError): X.from_icm(bad)


def test_work_cell_on_a_routing_position_is_refused():
    P, ct, ins, outs = _case("addsub")
    prog = X.program_of(P, ct, "t"); k = next(iter(prog["cells"]))
    prog["cells"]["0,1" if k != "0,1" else "0,2"] = prog["cells"][k]
    with pytest.raises(ValueError): X.to_icm(prog)
