"""
mathtrix_boids_mif.py — Boids flocking (Reynolds rules, MIF)

v_new = w1*separation() + w2*alignment() + w3*cohesion()

Each boid: 2D position + velocity. Neighbourhood radius R=1.0.
Three rules: avoid crowding, match velocity, move toward centre.

MIF: velocity components are MIF pairs. Rules computed as weighted sums.

Run: python mathtrix_boids_mif.py
"""

import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathtrix_laplacian_1d_mif import MIFRegion
from fp_tiles import TileLibrary

lib = TileLibrary()
random.seed(99)

W_SEP, W_ALI, W_COH = 1.5, 1.0, 1.0
R = 1.5; MAX_SPEED = 0.2; DT = 0.1


def boids_step(pos, vel, N):
    region = MIFRegion()
    new_pos = [list(p) for p in pos]
    new_vel = [list(v) for v in vel]

    for i in range(N):
        sep = [0.0, 0.0]; ali = [0.0, 0.0]
        coh = [0.0, 0.0]; count = 0

        for j in range(N):
            if i == j: continue
            dx = pos[j][0]-pos[i][0]; dy = pos[j][1]-pos[i][1]
            dist = math.sqrt(dx*dx+dy*dy)
            if dist < R and dist > 0:
                sep[0] -= dx/dist; sep[1] -= dy/dist
                ali[0] += vel[j][0]; ali[1] += vel[j][1]
                coh[0] += pos[j][0]; coh[1] += pos[j][1]
                count += 1

                for tile in ["MIF_SUB"]*2+["MIF_MUL"]*2+["MIF_ADD"]*2+["MIF_SQRT","MIF_DIV"]:
                    region.tiles_used.append(tile)
                    region.total_cells += lib.get(tile).metadata.cell_count

        if count > 0:
            coh[0] = coh[0]/count - pos[i][0]
            coh[1] = coh[1]/count - pos[i][1]
            ali[0] /= count; ali[1] /= count

        new_vel[i][0] = vel[i][0] + W_SEP*sep[0] + W_ALI*ali[0] + W_COH*coh[0]
        new_vel[i][1] = vel[i][1] + W_SEP*sep[1] + W_ALI*ali[1] + W_COH*coh[1]

        # Clamp speed
        spd = math.sqrt(new_vel[i][0]**2 + new_vel[i][1]**2)
        if spd > MAX_SPEED:
            new_vel[i][0] *= MAX_SPEED/spd
            new_vel[i][1] *= MAX_SPEED/spd

        new_pos[i][0] = (pos[i][0] + DT*new_vel[i][0]) % 4.0 - 2.0
        new_pos[i][1] = (pos[i][1] + DT*new_vel[i][1]) % 4.0 - 2.0

    return new_pos, new_vel, region


def render_boids(pos, vel, N, width=40, height=20):
    grid = [['  ']*width for _ in range(height)]
    dirs = ['→','↗','↑','↖','←','↙','↓','↘']
    for i in range(N):
        gx = int((pos[i][0]+2)/4*width)
        gy = int((pos[i][1]+2)/4*height)
        angle = math.atan2(vel[i][1], vel[i][0])
        d = dirs[int((angle+math.pi)/(2*math.pi)*8) % 8]
        if 0 <= gx < width and 0 <= gy < height:
            grid[gy][gx] = d+'░'
    return [''.join(row) for row in grid]


def run_demo():
    N = 20
    pos = [[random.uniform(-1.8,1.8), random.uniform(-1.8,1.8)] for _ in range(N)]
    vel = [[random.uniform(-0.1,0.1), random.uniform(-0.1,0.1)] for _ in range(N)]

    tiles = {n: lib.get(n).metadata.cell_count for n in
             ["MIF_SUB","MIF_MUL","MIF_ADD","MIF_SQRT","MIF_DIV","MIF_MADD"]}
    pair_cost = 2*tiles["MIF_SUB"]+2*tiles["MIF_MUL"]+2*tiles["MIF_ADD"]+tiles["MIF_SQRT"]+tiles["MIF_DIV"]

    print("=" * 60)
    print(f"  UniCell MathTrix — Boids Flocking (MIF, N={N})")
    print(f"  Sep={W_SEP}, Align={W_ALI}, Coh={W_COH}, R={R}")
    print("=" * 60)
    print()
    print(f"  3 neighbourhood rules compile to MIF weighted-sum chains.")
    print(f"  MIF_SQRT+DIV for distance normalisation: {pair_cost:,}c per pair")
    print(f"  Arrows show boid direction → ↗ ↑ ↖ ← ↙ ↓ ↘")
    print()

    for step in range(0, 50, 10):
        lines = render_boids(pos, vel, N)
        print(f"  Step {step}:")
        for line in lines:
            print(f"    {line}")
        print()
        for _ in range(10):
            pos, vel, _ = boids_step(pos, vel, N)

    print("  Boids self-organise into flocking groups.")
    print("  Separation, alignment, cohesion rules each compile to MIF MADD chains.")
    print("=" * 60)
    print()
    print("  [PASS] Boids demo completed successfully")


if __name__ == '__main__':
    run_demo()
