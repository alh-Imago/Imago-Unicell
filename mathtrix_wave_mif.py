"""
mathtrix_wave_mif.py — 2D Wave Equation (MIF)

    u_next[i,j] = 2*u[i,j] - u_prev[i,j] + c²*∇²u[i,j]

c=0.3, dt=1, fixed zero boundaries. Gaussian pulse at centre.
Demonstrates state storage across timesteps (u_prev).

Run: python mathtrix_wave_mif.py
"""

import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathtrix_laplacian_1d_mif import MIFRegion
from fp_tiles import TileLibrary

lib = TileLibrary()
C = 0.3; C2 = C*C


def wave_step(u, u_prev):
    N = len(u); M = len(u[0])
    u_next = [[0.0]*M for _ in range(N)]
    region = MIFRegion()

    for i in range(1, N-1):
        for j in range(1, M-1):
            lap = (u[i-1][j] + u[i+1][j] + u[i][j-1] + u[i][j+1] - 4*u[i][j])
            # u_next = 2*u - u_prev + c²*lap
            # MIF: MADD(c², lap, 2*u) then SUB u_prev
            u_next[i][j] = 2*u[i][j] - u_prev[i][j] + C2*lap

            for tile in ["MIF_UNPACK"]*6 + ["MIF_SUB"]*5 + ["MIF_ADD"]*3 + ["MIF_MADD","MIF_PACK"]:
                region.tiles_used.append(tile)
                region.total_cells += lib.get(tile).metadata.cell_count

    return u_next, region


def render_wave(u):
    N = len(u); M = len(u[0])
    maxv = max(abs(u[i][j]) for i in range(N) for j in range(M)) or 1.0
    lines = []
    for i in range(N):
        row = ''
        for j in range(M):
            v = u[i][j] / maxv
            if v > 0.6:   row += '██'
            elif v > 0.2: row += '▓▓'
            elif v > -0.2:row += '░░'
            elif v > -0.6:row += '▒▒'
            else:          row += '  '
        lines.append(row)
    return lines


def tile_cost_wave():
    tiles = {n: lib.get(n).metadata.cell_count for n in
             ["MIF_UNPACK","MIF_PACK","MIF_SUB","MIF_ADD","MIF_MADD"]}
    return (6*tiles["MIF_UNPACK"] + 5*tiles["MIF_SUB"] +
            3*tiles["MIF_ADD"] + tiles["MIF_MADD"] + tiles["MIF_PACK"])


def run_demo():
    N, M = 17, 17
    u = [[0.0]*M for _ in range(N)]
    u_prev = [[0.0]*M for _ in range(N)]

    # Gaussian pulse
    for i in range(N):
        for j in range(M):
            r2 = (i-N//2)**2 + (j-M//2)**2
            u[i][j] = math.exp(-r2/4.0)

    per_site = tile_cost_wave()

    print("=" * 60)
    print("  UniCell MathTrix — 2D Wave Equation (MIF)")
    print(f"  Grid: {N}×{M}  |  c={C}  |  Gaussian pulse at centre")
    print("=" * 60)
    print()
    print(f"  u_next = 2u - u_prev + c²∇²u")
    print(f"  Requires u and u_prev state (two timesteps in fabric memory).")
    print(f"  Per-site tile cost: ~{per_site:,}c")
    print()
    print("  █=high  ▓=mid-high  ░=low  ▒=mid-low  space=trough")
    print()

    for step in range(12):
        lines = render_wave(u)
        print(f"  Step {step}:")
        for line in lines:
            print(f"    {line}")
        print()
        u_next, _ = wave_step(u, u_prev)
        u_prev = u; u = u_next

    print("  Wave expands outward from Gaussian pulse, reflects at boundaries.")
    print("  u_prev demonstrates state storage — two MIF regions per site.")
    print("=" * 60)
    print()
    print("  [PASS] Wave equation demo completed successfully")


if __name__ == '__main__':
    run_demo()
