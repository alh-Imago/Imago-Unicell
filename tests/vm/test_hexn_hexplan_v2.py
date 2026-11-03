"""tests/vm/test_hexn_hexplan_v2.py - four-input priority tile (one PR cell, W,N,S,E) on the hex planner tools/hexn_wrgrid_hex_v3.py (3 Nov 2026)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools"))
import hexn_wrgrid_hex_v3 as H
N = H.Node9
MIX = {"UN": 2, "AL": 3, "JN": 4, "BR": 1, "MG": 1, "PR": 4}


def _types(n, off):
    H.OFFSET = off; wc = H.Grid12(n, n).work_cells(); seq = []; c = dict(MIX)
    while any(c.values()):
        for k in list(c):
            if c[k]: seq.append(k); c[k] -= 1
    return {w: t for w, t in zip(wc, (seq + ["AL"] * len(wc))[:len(wc)])}


def _run(n, off, k):
    ins = ["x", "y", "z", "w"][:k]
    nodes = [N("p", "prio", ins, cfg=dict(mask=(1 << k) - 1, ranks=(0, 1, 2, 3), mode=0))]
    try:
        P = H.plan10(nodes, ins, ["p"], n, n, _types(n, off), tries=40)
        return H.check_task(P, nodes, ins, ["p"])[0]
    finally:
        H.OFFSET = 0


def test_prio4_plans_and_equals_the_reference_on_hex_9x9():
    for off in (0, 1, 2): assert _run(9, off, 4)


def test_prio4_plans_on_hex_7x7_offset2():
    assert _run(7, 2, 4)


def test_prio3_still_plans_on_hex_7x7():
    for off in (0, 1, 2): assert _run(7, off, 3)
