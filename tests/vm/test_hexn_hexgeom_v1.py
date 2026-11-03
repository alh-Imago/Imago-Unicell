"""tests/vm/test_hexn_hexgeom_v1.py - checks the geometry claims of tools/hexn_hexgeom_v1.py (3 Nov 2026): the 2 Nov 08:20 ledger row stated them but marked them 'not tested'."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools"))
import hexn_hexgeom_v1 as H


def test_neighbours_are_symmetric_and_distinct():
    for r in range(8):
        for c in range(8):
            ns = [H.neighbour(r, c, f) for f in range(6)]
            assert len(set(ns)) == 6
            for f, n in enumerate(ns): assert H.neighbour(*n, H.opposite(f)) == (r, c)


def test_three_colouring_gives_the_work_routing_split():
    R = C = 13
    for (r, c) in H.cells(R, C):
        if not (1 <= r < R - 1 and 1 <= c < C - 1): continue          # interior cells have all six neighbours
        ns = [H.neighbour(r, c, f) for f in range(6)]
        w = sum(H.is_work(*n) for n in ns)
        if H.is_work(r, c): assert w == 0                               # work cells never touch each other: six routing neighbours
        else: assert w == 3                                             # a routing cell touches three work cells and three routing cells


def test_work_density_is_one_third():
    for n in (7, 9, 11):
        k = len(H.work_cells(n, n)); assert abs(k / (n * n) - 1 / 3) < 0.08, (n, k)
