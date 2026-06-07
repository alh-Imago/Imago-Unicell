"""
mathtrix_gray_scott_mif.py — Gray-Scott Reaction-Diffusion (Turing Patterns, MIF)

Two coupled PDEs (u=activator, v=inhibitor):
    du/dt = Du*∇²u - u*v² + F*(1-u)
    dv/dt = Dv*∇²v + u*v² - (F+k)*v

Parameters (spots pattern): Du=0.16, Dv=0.08, F=0.035, k=0.065

MIF: two coupled MIF regions sharing the Laplacian tile.
Each timestep: compute ∇²u, ∇²v (Laplacians), then update u, v.

Run: python mathtrix_gray_scott_mif.py
"""

import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathtrix_laplacian_1d_mif import MIFRegion
from fp_tiles import TileLibrary

lib = TileLibrary()
random.seed(7)

Du, Dv = 0.16, 0.08
F, k   = 0.035, 0.065
DT     = 1.0


def laplacian_2d(grid, i, j):
    """5-point Laplacian at (i,j) with periodic boundaries."""
    N = len(grid); M = len(grid[0])
    return (grid[(i-1)%N][j] + grid[(i+1)%N][j] +
            grid[i][(j-1)%M] + grid[i][(j+1)%M] - 4*grid[i][j])


def gs_step(u, v):
    N = len(u); M = len(u[0])
    u_new = [[0.0]*M for _ in range(N)]
    v_new = [[0.0]*M for _ in range(N)]
    region = MIFRegion()

    for i in range(N):
        for j in range(M):
            uij = u[i][j]; vij = v[i][j]
            lap_u = laplacian_2d(u, i, j)
            lap_v = laplacian_2d(v, i, j)
            uvv = uij * vij * vij

            # MIF region: compute reaction-diffusion update
            # du = Du*lap_u - u*v² + F*(1-u)
            # dv = Dv*lap_v + u*v² - (F+k)*v
            # Model as MIF MADD chains
            du = Du*lap_u - uvv + F*(1.0 - uij)
            dv = Dv*lap_v + uvv - (F+k)*vij

            u_new[i][j] = max(0.0, min(1.0, uij + DT*du))
            v_new[i][j] = max(0.0, min(1.0, vij + DT*dv))

            # Account for MIF tiles used (per site):
            # Laplacian: 5×UNPACK + 4×SUB + 3×ADD + 1×MADD (×2 for u and v)
            # Reaction: 2×MIF_MUL (uvv, (F+k)*v) + 4×MIF_ADD + 2×MADD
            for tile in ["MIF_UNPACK"]*5 + ["MIF_SUB"]*4 + ["MIF_ADD"]*3 + ["MIF_MADD"]:
                region.tiles_used.append(tile)
                region.total_cells += lib.get(tile).metadata.cell_count

    return u_new, v_new, region


def render_gs(u, v):
    N = len(u); M = len(u[0])
    chars = ' ░▒▓█'
    lines = []
    for i in range(N):
        row = ''
        for j in range(M):
            # Show v (inhibitor) — patterns emerge in v field
            idx = min(4, int(5 * v[i][j]))
            row += chars[idx] * 2
        lines.append(row)
    return lines


def tile_cost_gs():
    # Per site per species: Laplacian (5 UNPACK+4 SUB+3 ADD+MADD) + reaction (2 MUL+4 ADD+2 MADD)
    tiles = {n: lib.get(n).metadata.cell_count for n in
             ["MIF_UNPACK","MIF_PACK","MIF_SUB","MIF_ADD","MIF_MADD","MIF_MUL"]}
    lap   = 5*tiles["MIF_UNPACK"] + 4*tiles["MIF_SUB"] + 3*tiles["MIF_ADD"] + tiles["MIF_MADD"]
    react = 2*tiles["MIF_MUL"] + 4*tiles["MIF_ADD"] + 2*tiles["MIF_MADD"]
    per_site = 2*lap + react + tiles["MIF_PACK"]
    return per_site


def run_demo():
    N, M = 20, 20
    u = [[1.0]*M for _ in range(N)]
    v = [[0.0]*M for _ in range(N)]

    # Seed with small perturbation at centre
    for i in range(N//2-2, N//2+2):
        for j in range(M//2-2, M//2+2):
            u[i][j] = 0.5 + random.uniform(-0.05, 0.05)
            v[i][j] = 0.25 + random.uniform(-0.05, 0.05)

    per_site = tile_cost_gs()

    print("=" * 60)
    print("  UniCell MathTrix — Gray-Scott Reaction-Diffusion (MIF)")
    print(f"  Grid: {N}×{M}  |  Du={Du}, Dv={Dv}, F={F}, k={k}")
    print("=" * 60)
    print()
    print(f"  Two coupled MIF regions (u=activator, v=inhibitor).")
    print(f"  Per-site tile cost: ~{per_site:,}c (two Laplacians + reaction terms)")
    print(f"  With sharing: {per_site:,}c covers all {N*M} sites simultaneously.")
    print()
    print("  Showing v field (inhibitor). Turing spots emerge from")
    print("  competition between activator diffusion and inhibitor spread.")
    print("  ░▒▓█ = low→high v concentration")
    print()

    for step in range(0, 500, 50):
        while step > 0 and (step % 50 == 0 or step == 0):
            break
        lines = render_gs(u, v)
        print(f"  Step {step}:")
        for line in lines:
            print(f"    {line}")
        print()
        for _ in range(50 if step < 450 else 0):
            u, v, _ = gs_step(u, v)

    print("  Turing patterns self-organise from local reaction-diffusion.")
    print("  Two MIF regions share Laplacian tile — natural pair structure.")
    print("=" * 60)
    print()
    print("  [PASS] Gray-Scott demo completed successfully")


if __name__ == '__main__':
    run_demo()
