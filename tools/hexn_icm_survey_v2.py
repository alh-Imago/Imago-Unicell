"""hexn_icm_survey_v2.py - CORRECTS hexn_icm_survey_v1.py (2 Nov 2026).  v1 said a Hex-N routing cell with 2+ paths has no single-cell ICM form.  That was WRONG
in part: the ICM already has native wiring cores 'cross' (straight pairs W-E, N-S) and 'corner' (turn 0: E-N, W-S; turn 1: E-S, W-N), pure-wiring tiles with four
independent one-word slices (nano/corner_cell_automaton_v1.py, fpga corner_cell_v4 / cross_cell_v4, ICM core_select 11 and 10).  A routing cell whose paths are a
SUBSET of one tile's pairs can be that tile (unused slices idle).  This classifies every routing cell of the 19 example designs on a free grid:
  cross / corner0 / corner1 : all its paths are pairs of that tile
  relay   : one input fanned out to one or more outputs, nothing else (ICM 'ram' relay, downstream_mask can fan out)
  other   : mixed straights and turns, or a fan-out plus other paths - no single ICM tile.
Directions: a Hex-N path is {out face: in face}.  The ICM tiles carry words BOTH ways on each pair; Hex-N paths are one way, so a tile does at least what is needed.
Prints; changes nothing."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_bases_v2 as B, hexn_wrgrid_v11 as G

CROSS = {("W", "E"), ("E", "W"), ("N", "S"), ("S", "N")}                      # (in face, out face)
CORNER = {0: {("E", "N"), ("N", "E"), ("W", "S"), ("S", "W")}, 1: {("E", "S"), ("S", "E"), ("W", "N"), ("N", "W")}}


def classify(sel):
    pairs = {(i, o) for o, i in sel.items()}
    if len(set(sel.values())) == 1 and len(sel) >= 1 and not (len(sel) == 1 and pairs <= (CROSS | CORNER[0] | CORNER[1])):
        return "relay"                                                          # one input, fan-out
    if pairs <= CROSS: return "cross"
    if pairs <= CORNER[0]: return "corner0"
    if pairs <= CORNER[1]: return "corner1"
    return "other"


def survey():
    rows = []
    for nm, t in B.all_tasks().items():
        g = G.configure9(B.free_plan(t)); cnt = collections.Counter(classify(sel) for sel in g.route.values())
        rows.append((nm, len(g.route), cnt))
    return rows


if __name__ == "__main__":
    tot = collections.Counter(); n = 0
    for nm, k, cnt in survey():
        print("%-24s %3d routing cells: %s" % (nm, k, ", ".join("%s %d" % kv for kv in sorted(cnt.items())))); tot.update(cnt); n += k
    print("TOTAL %d routing cells: %s" % (n, ", ".join("%s %d" % kv for kv in sorted(tot.items()))))
