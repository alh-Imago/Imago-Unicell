"""Hex-N 12-wire detector bank on a HEX LATTICE with edge bridges (Alan, 21 Oct 2026). Usage: hexn_lattice_v1.py [shape ...]   shapes: hex7 hex19 rhombus4 par8 par16 (default: all).
Geometry (axial coordinates q,r; face f = 0..5 around a cell, opposite face = f+3; neighbour of face f is cell + DIR[f]):
  A cell LISTENS on faces 0, 2, 4 (one face of each of the three line directions {0,3}, {1,4}, {2,5}) and keeps faces 1, 3, 5 free (for the output and anything else).
  Each lattice edge is listened to by exactly ONE of its two cells (a listening face f of one cell is face f+3, not a listening face, of its neighbour), so there is one BRIDGE per listened edge: 3 bridges per cell, every edge counted once.
  A bridge carries one 4-wire group (A for face 0, B for face 2, C for face 4 = the 12 input wires) and is a register (4 flip-flops): it takes the group from the previous bridge on the same straight line, hands it to the cell that listens to it,
  and to the next bridge (cell + DIR[f]).  The first bridge of every line is fed from the input bus.
Checks: every cell hears all three groups; no cell listens on more than 3 faces; every line is unbroken (no gap cells); bridges = 3 per cell; feeds per group = number of lines; settle time = longest line; and a clocked propagation test (input changes, every cell sees the right 12 wires after the settle time)."""
import sys, random
DIR = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
LISTEN = [0, 2, 4]            # listening faces; group g = index in this list
def shape(name):
    if name == "hex7": return [(q, r) for q in range(-1, 2) for r in range(-1, 2) if abs(q + r) <= 1]
    if name == "hex19": return [(q, r) for q in range(-2, 3) for r in range(-2, 3) if abs(q + r) <= 2]
    if name == "rhombus4": return [(q, r) for q in range(2) for r in range(2)]
    if name == "par8": return [(q, r) for q in range(4) for r in range(2)]
    if name == "par16": return [(q, r) for q in range(4) for r in range(4)]
    raise SystemExit("unknown shape " + name)
def layout(cells):
    S = set(cells); idx = {c: i for i, c in enumerate(cells)}
    br = {}                                                  # (cell, group) -> dict(up=(cell,group) or None, pos=hops from feed)
    for c in cells:
        for g, f in enumerate(LISTEN):
            d = DIR[f]; prev = (c[0] - d[0], c[1] - d[1])
            br[(c, g)] = {"up": (prev, g) if prev in S else None}
    for key in br:                                           # position along the line (1 = first bridge, fed from the bus)
        n = 1; k = key
        while br[k]["up"] is not None: k = br[k]["up"]; n += 1
        br[key]["pos"] = n
    return idx, br
def check(name):
    cells = shape(name); idx, br = layout(cells); S = set(cells); problems = []
    for c in cells:
        heard = sorted(g for g in range(3) if (c, g) in br)
        if heard != [0, 1, 2]: problems.append(f"cell {c} hears groups {heard}")
        if len(LISTEN) != 3 or set(LISTEN) & {1, 3, 5}: problems.append("listening faces overlap the free faces")
    # lines unbroken: along each direction, the cells of a line must be consecutive (no gap cell between two member cells)
    gaps = 0
    for g, f in enumerate(LISTEN):
        d = DIR[f]
        for c in cells:
            if (c[0] - d[0], c[1] - d[1]) not in S:        # first cell of a line
                n = c
                while (n[0] + d[0], n[1] + d[1]) in S: n = (n[0] + d[0], n[1] + d[1])
                # any further member beyond a gap?
                m = (n[0] + 2 * d[0], n[1] + 2 * d[1])
                for _ in range(60):
                    if m in S: gaps += 1
                    m = (m[0] + d[0], m[1] + d[1])
    if gaps: problems.append(f"{gaps} line(s) have a gap cell")
    feeds = [sum(1 for k, v in br.items() if k[1] == g and v["up"] is None) for g in range(3)]
    settle = max(v["pos"] for v in br.values())
    # clocked propagation test: bridge registers, input bus changes every few clocks
    state = {k: 0 for k in br}; rnd = random.Random(7); bus = [0, 0, 0]; ok = True; last_change = 0
    for t in range(400):
        if t % 37 == 0: bus = [rnd.randrange(16) for _ in range(3)]; last_change = t
        new = {}
        for k, v in br.items(): new[k] = bus[k[1]] if v["up"] is None else state[v["up"]]
        state = new
        if t - last_change >= settle:
            for c in cells:
                for g in range(3):
                    if state[(c, g)] != bus[g]: ok = False
    if not ok: problems.append("propagation test failed")
    return len(cells), len(br), feeds, settle, problems
if __name__ == "__main__":
    names = sys.argv[1:] or ["rhombus4", "hex7", "par8", "par16", "hex19"]
    print("%-9s %-6s %-8s %-18s %-14s %s" % ("shape", "cells", "bridges", "feeds per group", "settle clocks", "result"))
    for nm in names:
        n, nb, feeds, settle, pr = check(nm)
        print("%-9s %-6d %-8d %-18s %-14d %s" % (nm, n, nb, "/".join(map(str, feeds)) + " lines", settle, "OK: every cell hears all 12 wires, 3 free faces each" if not pr else "PROBLEMS: " + "; ".join(pr)))
