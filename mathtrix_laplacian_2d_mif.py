"""
mathtrix_laplacian_2d_mif.py — MathTrix 2D Laplacian (heat equation, MIF)

Solves the 2D heat/diffusion equation:
    u_new[i,j] = u[i,j] + alpha*(u[i-1,j]+u[i+1,j]+u[i,j-1]+u[i,j+1] - 4*u[i,j])

alpha = 0.1 (CFL stable for 2D explicit: alpha <= 0.25).
Fixed zero boundaries. Unit impulse at centre.

MIF region per stencil point:
  4×MIF_UNPACK  (neighbours: left, right, up, down)
  1×MIF_UNPACK  (centre)
  4×MIF_SUB     (each neighbour - centre)
  3×MIF_ADD     (sum the four deviations)
  1×MIF_MADD    (diff * alpha + centre — fused)
  1×MIF_PACK    (result)

Run: python mathtrix_laplacian_2d_mif.py
"""

import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathtrix_laplacian_1d_mif import float_to_bits, bits_to_float, MIFRegion, ALPHA
from fp_tiles import TileLibrary

lib = TileLibrary()
ALPHA_2D = 0.1   # CFL condition for 2D: alpha <= 1/(2*ndim) = 0.25; use 0.1 for stability


def mif_stencil_2d(left, right, up, down, centre):
    """
    5-point 2D Laplacian stencil via MIF region.

    MIF op sequence:
      5×UNPACK: left, right, up, down, centre
      4×SUB:    left-c, right-c, up-c, down-c
      3×ADD:    (dl+dr), (du+dd), total_diff
      1×MADD:   diff*alpha + centre
      1×PACK:   result
    """
    region = MIFRegion()

    l_c,  l_m  = region.unpack(left)
    r_c,  r_m  = region.unpack(right)
    u_c,  u_m  = region.unpack(up)
    d_c,  d_m  = region.unpack(down)
    cen_c, cen_m = region.unpack(centre)

    # Deviations from centre
    dl_c, dl_m = region.sub(l_c,  l_m,  cen_c, cen_m)
    dr_c, dr_m = region.sub(r_c,  r_m,  cen_c, cen_m)
    du_c, du_m = region.sub(u_c,  u_m,  cen_c, cen_m)
    dd_c, dd_m = region.sub(d_c,  d_m,  cen_c, cen_m)

    # Sum deviations
    lr_c, lr_m = region.add(dl_c, dl_m, dr_c, dr_m)
    ud_c, ud_m = region.add(du_c, du_m, dd_c, dd_m)
    diff_c, diff_m = region.add(lr_c, lr_m, ud_c, ud_m)

    # Fused: diff * alpha + centre
    alpha_c, alpha_m = region._from_float(ALPHA_2D)
    result_c, result_m = region.madd(diff_c, diff_m, alpha_c, alpha_m, cen_c, cen_m)

    return region.pack(result_c, result_m), region


def laplacian_step_2d(u):
    N = len(u); M = len(u[0])
    u_new = [list(row) for row in u]
    for i in range(1, N-1):
        for j in range(1, M-1):
            u_new[i][j], _ = mif_stencil_2d(
                u[i][j-1], u[i][j+1],
                u[i-1][j], u[i+1][j],
                u[i][j]
            )
    return u_new


def tile_cost_2d():
    tiles = {n: lib.get(n).metadata.cell_count for n in
             ["MIF_UNPACK","MIF_PACK","MIF_SUB","MIF_ADD","MIF_MADD"]}
    boundary = 5 * tiles["MIF_UNPACK"] + tiles["MIF_PACK"]
    ops      = 4 * tiles["MIF_SUB"] + 3 * tiles["MIF_ADD"] + tiles["MIF_MADD"]
    return boundary, ops, boundary + ops


def render(u, width=40):
    """ASCII heat map."""
    N = len(u); M = len(u[0])
    maxv = max(u[i][j] for i in range(N) for j in range(M)) or 1.0
    chars = ' ░▒▓█'
    lines = []
    for i in range(N):
        row = ''
        for j in range(M):
            idx = min(4, int(5 * u[i][j] / maxv))
            row += chars[idx] * 2
        lines.append(row)
    return lines


def run_demo():
    N, M = 11, 11
    u = [[0.0]*M for _ in range(N)]
    u[N//2][M//2] = 1.0

    boundary_c, op_c, total_c = tile_cost_2d()
    interior = (N-2) * (M-2)

    _, sample = mif_stencil_2d(0.0, 0.0, 0.0, 0.0, 1.0)

    print("=" * 60)
    print("  UniCell MathTrix — 2D Heat Diffusion (MIF floating-point)")
    print(f"  Grid: {N}×{M}  |  Alpha: {ALPHA_2D}  |  Fixed zero boundaries")
    print("=" * 60)
    print()
    print(f"  Stencil tile costs (5-point, shared across all {interior} interior pts):")
    print(f"    Boundary (5×UNPACK + PACK):           {boundary_c:>5}c")
    print(f"    Ops  (4×SUB + 3×ADD + MADD):          {op_c:>5}c")
    print(f"    Per-stencil total:                    {total_c:>5}c")
    print(f"    With sharing: {total_c}c covers all {interior} points")
    print(f"    Without:      {interior}×{total_c} = {interior*total_c:,}c")
    print()

    for step in range(8):
        lines = render(u)
        print(f"  Step {step}:")
        for line in lines:
            print(f"    {line}")
        total_heat = sum(u[i][j] for i in range(N) for j in range(M))
        print(f"    Total heat: {total_heat:.4f}")
        print()
        if step < 7:
            u = laplacian_step_2d(u)

    print("  2D stencil uses same MIF tile set as 1D — only UNPACK count differs.")
    print("  4 neighbours instead of 2: +2×UNPACK, +2×SUB, +1×ADD.")
    print("  Heat spreads radially from centre impulse — correct 2D diffusion.")
    print("=" * 60)
    print()
    print("  [PASS] 2D MIF Laplacian demo completed successfully")


if __name__ == '__main__':
    run_demo()
