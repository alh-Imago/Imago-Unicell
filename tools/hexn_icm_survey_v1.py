"""hexn_icm_survey_v1.py - READ-ONLY survey (2 Nov 2026): how many Hex-N routing cells can be written as ONE ICM cell?
A Hex-N routing cell may carry several independent paths ({out face: in face} per path).  An ICM relay cell has one upstream_mask and one
downstream_mask, and everything arriving is OR-merged to everything offered, so a cell with 2+ independent paths (a crossing, or two corners) has no
single-cell ICM form on four faces.  Counts over the 19 example designs on a free (unconstrained) grid.  Prints; changes nothing."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_bases_v2 as B, hexn_wrgrid_v11 as G

OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}


def survey():
    rows = []
    for nm, t in B.all_tasks().items():
        g = G.configure9(B.free_plan(t)); multi = cross = fan = 0
        for c, sel in g.route.items():
            if len(sel) > 1:
                multi += 1
                axes = {("h" if o in "EW" else "v") for o in sel}
                if axes == {"h", "v"} and all(OPP[o] == i for o, i in sel.items()): cross += 1
            if len(set(sel.values())) < len(sel): fan += 1
        rows.append((nm, len(g.route), multi, cross, fan))
    return rows


if __name__ == "__main__":
    rows = survey()
    for r in rows: print("%-24s routing cells %3d  with 2+ paths %3d  straight crossings %3d  fan-out cells %3d" % r)
    print("TOTAL designs %d, routing cells %d, with 2+ paths %d, straight crossings %d, fan-out %d" % (len(rows), *[sum(r[i] for r in rows) for i in (1, 2, 3, 4)]))
