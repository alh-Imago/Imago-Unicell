"""hexn_hexgeom_v1.py - the HEX LATTICE GEOMETRY for six-face Hex-N grids (3 Nov 2026, Alan 15:04: 'go with the hex grid ... it does reframe the layout, the routing options will change too').
Odd-r layout (odd rows shifted half a cell to the right), as in sub/verilog/hexn_grid_v1.v.  FACE NUMBERS: 0 E, 1 SE, 2 SW, 3 W, 4 NW, 5 NE - going round clockwise, so the OPPOSITE face is (f + 3) % 6 (the four-face grid has 0 N, 1 E, 2 S, 3 W with opposite (f + 2) % 4).
WORK CELLS: the 3-colouring of the hex lattice (axial q = c - (r - (r & 1)) // 2, colour = (q - r) mod 3): colour 0 is a work cell, colours 1 and 2 are routing cells (work/routing split of the 2 Nov 08:20 ledger row).
This module only describes the geometry; no planner, no RTL."""
FACES = 6
NAMES = ("E", "SE", "SW", "W", "NW", "NE")
_EVEN = ((0, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0))      # (dr, dc) for faces 0..5 on an even row
_ODD = ((0, 1), (1, 1), (1, 0), (0, -1), (-1, 0), (-1, 1))         # on an odd row


def opposite(f): return (f + 3) % 6


def neighbour(r, c, f):
    dr, dc = (_ODD if r & 1 else _EVEN)[f]
    return (r + dr, c + dc)


def colour(r, c):
    q = c - (r - (r & 1)) // 2
    return (q - r) % 3


def is_work(r, c): return colour(r, c) == 0


def cells(R, C): return [(r, c) for r in range(R) for c in range(C)]


def inside(R, C, p): return 0 <= p[0] < R and 0 <= p[1] < C


def work_cells(R, C): return [p for p in cells(R, C) if is_work(*p)]
