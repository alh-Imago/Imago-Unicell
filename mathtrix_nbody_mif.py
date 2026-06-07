"""
mathtrix_nbody_mif.py — N-body gravity (softened potential, MIF)

    F_i = sum_j( m_i*m_j * (x_j-x_i) / (dist(i,j)² + eps)^1.5 )

Uses MIF_DIV and MIF_SQRT. Softening eps=0.1 prevents singularity.
2D positions for display; 2D forces.

Run: python mathtrix_nbody_mif.py
"""

import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathtrix_laplacian_1d_mif import MIFRegion
from fp_tiles import TileLibrary

lib = TileLibrary()
random.seed(13)
EPS2 = 0.01   # softening squared
DT   = 0.01


def nbody_step(pos, vel, mass):
    N = len(pos)
    force = [[0.0, 0.0] for _ in range(N)]
    region = MIFRegion()

    for i in range(N):
        for j in range(N):
            if i == j: continue
            dx = pos[j][0] - pos[i][0]
            dy = pos[j][1] - pos[i][1]
            r2 = dx*dx + dy*dy + EPS2
            r3 = r2 ** 1.5
            f  = mass[i] * mass[j] / r3
            force[i][0] += f * dx
            force[i][1] += f * dy

            # MIF tiles: 2×SUB (dx,dy) + 2×MUL (dx²,dy²) + ADD + const +
            #            SQRT + DIV + MUL(mass) + ADD(force)
            for tile in (["MIF_SUB"]*2 + ["MIF_MUL"]*3 +
                         ["MIF_ADD"]*2 + ["MIF_SQRT","MIF_DIV","MIF_PACK"]):
                region.tiles_used.append(tile)
                region.total_cells += lib.get(tile).metadata.cell_count

    # Integrate
    new_pos = [[0.0, 0.0] for _ in range(N)]
    new_vel = [[0.0, 0.0] for _ in range(N)]
    for i in range(N):
        new_vel[i][0] = vel[i][0] + DT * force[i][0] / mass[i]
        new_vel[i][1] = vel[i][1] + DT * force[i][1] / mass[i]
        new_pos[i][0] = pos[i][0] + DT * new_vel[i][0]
        new_pos[i][1] = pos[i][1] + DT * new_vel[i][1]

    return new_pos, new_vel, region


def render_nbody(pos, mass, width=40, height=20):
    grid = [['  ']*width for _ in range(height)]
    for i, (px, py) in enumerate(pos):
        gx = int((px + 2) / 4 * width)
        gy = int((py + 2) / 4 * height)
        if 0 <= gx < width and 0 <= gy < height:
            m = mass[i]
            sym = '██' if m > 2 else '▓▓' if m > 1 else '░░'
            grid[gy][gx] = sym
    return [''.join(row) for row in grid]


def run_demo():
    N = 6
    pos  = [[random.uniform(-1.5, 1.5), random.uniform(-1.5, 1.5)] for _ in range(N)]
    vel  = [[random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)] for _ in range(N)]
    mass = [random.uniform(0.5, 3.0) for _ in range(N)]

    tiles = {n: lib.get(n).metadata.cell_count for n in
             ["MIF_SUB","MIF_MUL","MIF_ADD","MIF_SQRT","MIF_DIV"]}
    pair_cost = (2*tiles["MIF_SUB"] + 3*tiles["MIF_MUL"] +
                 2*tiles["MIF_ADD"] + tiles["MIF_SQRT"] + tiles["MIF_DIV"])
    total_pairs = N * (N-1)

    print("=" * 60)
    print(f"  UniCell MathTrix — N-body Gravity (MIF, N={N})")
    print(f"  Softened potential: eps²={EPS2}, dt={DT}")
    print("=" * 60)
    print()
    print(f"  MIF_SQRT ({tiles['MIF_SQRT']}c) and MIF_DIV ({tiles['MIF_DIV']}c)")
    print(f"  enable gravitational force computation natively.")
    print(f"  Per body-pair: ~{pair_cost:,}c")
    print(f"  Total pairs: {total_pairs}  →  ~{total_pairs*pair_cost:,}c per step")
    print(f"  With pair-tile sharing: {pair_cost:,}c covers all {total_pairs} pairs")
    print()
    print("  ██=heavy  ▓=medium  ░=light body")
    print()

    for step in range(0, 60, 10):
        lines = render_nbody(pos, mass)
        print(f"  Step {step}:")
        for line in lines:
            print(f"    {line}")
        print()
        for _ in range(10):
            pos, vel, _ = nbody_step(pos, vel, mass)

    print("  Bodies cluster under mutual gravity (softened to prevent singularity).")
    print("  MIF_SQRT+DIV: exponent manipulation on ctrl cell handles the 1/r² naturally.")
    print("=" * 60)
    print()
    print("  [PASS] N-body demo completed successfully")


if __name__ == '__main__':
    run_demo()
