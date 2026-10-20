"""Hex-N v14: is the v2 cell (faces feed one decision) harder to train than v1? Same task as v9 at delay 0: a hidden 'teacher' cell of the SAME kind produces the goal from the
same random inputs; the learner (v6: LFSR, 4-bit reward, warm start, keep-or-undo, 1-3 changes, 1500 tries) must reproduce it.  --cell v1 = six independent faces, --cell v2 = faces feed one
decision.  A fair like-for-like comparison of how learnable each cell is; it says nothing about which cell is more USEFUL (v1 cannot do the pattern task at all).
Usage: python3 tools/hexn_match_v14.py --cell v1|v2 [--first S] [--runs N] [--tries T]"""
import argparse, importlib.util, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v9, mc = load("hexn_delay_v9"), load("hexn_cell_v2_model")
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--cell", default="v1"); ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--runs", type=int, default=20); ap.add_argument("--tries", type=int, default=1500); a = ap.parse_args()
    if a.cell == "v2":
        v9.v3.Cell = mc.MixCell; v9.v1.F = 1          # v1.F = 1 so the single threshold is the one that gets mutated
    print(f"cell {a.cell}, delay 0, {v9.WIN} windows, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'random-best':>11}")
    for s in range(a.first, a.first + a.runs):
        l, rb = v9.one(s, 0, a.tries, 0.5, 100, 4); print(f"{s:>4} {l:>8} {rb:>11}", flush=True)
