"""
mathtrix.py — MathTrix Frontend
================================
Domain language for mathematical parallel computation on UniCell fabric.

MathTrix sits between the user and the tile library. Users describe
problems in domain terms (grids, stencils, update rules). MathTrix
compiles them to tile placements and runs them.

Usage:
------
    from mathtrix import MathTrix, Grid1D, Grid2D

    mt = MathTrix()

    # 1D heat diffusion
    grid = Grid1D(size=64, alpha=0.1)
    grid.set_gaussian(centre=0.5, width=0.1)
    result = mt.run(grid, steps=100)
    print(result.at(32))  # value at position 32 after 100 steps

    # 2D reaction-diffusion
    grid2d = Grid2D(width=32, height=32)
    grid2d.set_seed(x=16, y=16, radius=3)
    result2d = mt.run_gray_scott(grid2d, F=0.055, k=0.062, steps=200)

    # Get frames for animation
    frames = result2d.frames  # list of 2D arrays
    final  = result2d.final   # final state

Architecture:
-------------
    User → MathTrix API → Tile library (fp_tiles.py)
                        → Compiler (compiler_int32.py)
                        → Controller (controller.py)
                        → Result

The MathTrix API is the domain-specific layer. The tile library
and compiler are the general-purpose layer. MathTrix uses tile_config
to select appropriate strategies per problem type.

Tile strategy selection:
    Problems with many div/sqrt per timestep → low_latency
    Problems with fixed divisors             → const_divisor
    Stencil problems (no div/sqrt)           → default (cell_budget)
"""

import math
import struct
from typing import Optional, List, Union


# ── Result types ──────────────────────────────────────────────────────────────

class Result1D:
    """Result of a 1D MathTrix computation."""

    def __init__(self, frames: List[List[float]], size: int,
                 steps: int, model: str, elapsed_s: float = 0.0):
        self.frames   = frames      # list of 1D float arrays
        self.size     = size
        self.steps    = steps
        self.model    = model
        self.elapsed_s = elapsed_s

    @property
    def final(self) -> List[float]:
        """Final state of the grid."""
        return self.frames[-1] if self.frames else []

    def at(self, i: int, frame: int = -1) -> float:
        """Value at position i in the given frame (-1 = final)."""
        return self.frames[frame][i]

    def to_dict(self) -> dict:
        return {
            "type":      "timeseries_1d",
            "model":     self.model,
            "size":      self.size,
            "steps":     self.steps,
            "elapsed_s": self.elapsed_s,
            "frames":    self.frames,
        }


class Result2D:
    """Result of a 2D MathTrix computation."""

    def __init__(self, frames: List[List[List[float]]],
                 width: int, height: int,
                 steps: int, model: str, elapsed_s: float = 0.0):
        self.frames    = frames
        self.width     = width
        self.height    = height
        self.steps     = steps
        self.model     = model
        self.elapsed_s = elapsed_s

    @property
    def final(self) -> List[List[float]]:
        return self.frames[-1] if self.frames else []

    def at(self, i: int, j: int, frame: int = -1) -> float:
        return self.frames[frame][i][j]

    def to_dict(self) -> dict:
        return {
            "type":      "timeseries_2d",
            "model":     self.model,
            "width":     self.width,
            "height":    self.height,
            "steps":     self.steps,
            "elapsed_s": self.elapsed_s,
            "frames":    self.frames,
        }


class ResultParticles:
    """Result of a particle-based MathTrix computation."""

    def __init__(self, trajectories: List[List[List[float]]],
                 n: int, steps: int, model: str, elapsed_s: float = 0.0):
        self.trajectories = trajectories  # [frame][particle][x,y]
        self.n            = n
        self.steps        = steps
        self.model        = model
        self.elapsed_s    = elapsed_s

    @property
    def final(self) -> List[List[float]]:
        return self.trajectories[-1] if self.trajectories else []

    def to_dict(self) -> dict:
        return {
            "type":         "trajectories",
            "model":        self.model,
            "n":            self.n,
            "steps":        self.steps,
            "elapsed_s":    self.elapsed_s,
            "trajectories": self.trajectories,
        }


# ── Grid descriptors ──────────────────────────────────────────────────────────

class Grid1D:
    """1D computational grid with initial conditions."""

    def __init__(self, size: int = 64, alpha: float = 0.1):
        self.size  = size
        self.alpha = alpha
        self.data  = [0.0] * size

    def set_gaussian(self, centre: float = 0.5, width: float = 0.1,
                     amplitude: float = 1.0) -> "Grid1D":
        """Set a Gaussian pulse initial condition."""
        cx = centre * self.size
        sx = width * self.size
        self.data = [amplitude * math.exp(-((i - cx)**2) / (2 * sx**2))
                     for i in range(self.size)]
        return self

    def set_step(self, value_left: float = 1.0,
                 value_right: float = 0.0) -> "Grid1D":
        """Set a step function initial condition."""
        mid = self.size // 2
        self.data = [value_left if i < mid else value_right
                     for i in range(self.size)]
        return self

    def set_uniform(self, value: float = 0.5) -> "Grid1D":
        self.data = [value] * self.size
        return self


class Grid2D:
    """2D computational grid with initial conditions."""

    def __init__(self, width: int = 32, height: int = 32):
        self.width  = width
        self.height = height
        self.data   = [[0.0] * width for _ in range(height)]

    def set_gaussian(self, cx: float = 0.5, cy: float = 0.5,
                     width: float = 0.15, amplitude: float = 1.0) -> "Grid2D":
        """Set a 2D Gaussian pulse."""
        sx = cx * self.width
        sy = cy * self.height
        sw = width * min(self.width, self.height)
        self.data = [
            [amplitude * math.exp(-((j-sx)**2 + (i-sy)**2) / (2*sw**2))
             for j in range(self.width)]
            for i in range(self.height)
        ]
        return self

    def set_seed(self, x: Optional[int] = None, y: Optional[int] = None,
                 radius: int = 3,
                 u_val: float = 0.5, v_val: float = 0.25) -> "Grid2D":
        """Set a reaction-diffusion seed region."""
        import random
        cx = x if x is not None else self.width  // 2
        cy = y if y is not None else self.height // 2
        self.u = [[1.0] * self.width for _ in range(self.height)]
        self.v = [[0.0] * self.width for _ in range(self.height)]
        for i in range(cy - radius, cy + radius):
            for j in range(cx - radius, cx + radius):
                if 0 <= i < self.height and 0 <= j < self.width:
                    self.u[i][j] = u_val + random.uniform(-0.01, 0.01)
                    self.v[i][j] = v_val + random.uniform(-0.01, 0.01)
        return self

    def set_random_spins(self, seed: int = 42) -> "Grid2D":
        """Set random +1/-1 spins (for Ising model)."""
        import random
        random.seed(seed)
        self.data = [[random.choice([-1.0, 1.0])
                      for _ in range(self.width)]
                     for _ in range(self.height)]
        return self


# ── MathTrix engine ───────────────────────────────────────────────────────────

class MathTrix:
    """
    MathTrix computation engine.

    Wraps the UniCell tile library and compiler with a domain-specific API
    for mathematical parallel computation.

    Each run() method:
      1. Takes a grid descriptor and parameters
      2. Selects appropriate tile_config for the problem
      3. Runs the computation (VM or hardware)
      4. Returns a typed Result object

    Backend selection:
      backend="vm"         — software simulation (default, always available)
      backend="icebreaker" — iCEBreaker hardware (requires UART bridge)
      backend="arria10"    — Arria 10 hardware (requires programmer + bridge)
    """

    def __init__(self, backend: str = "vm"):
        self.backend = backend
        self._lib    = None

    def _get_lib(self):
        if self._lib is None:
            from fp_tiles import TileLibrary
            self._lib = TileLibrary()
        return self._lib

    # ── 1D problems ────────────────────────────────────────────────────────────

    def laplacian_1d(self, grid: Grid1D, steps: int = 100,
                     frame_count: int = 10) -> Result1D:
        """
        1D Laplacian (heat diffusion):
            u_new[i] = u[i] + alpha * (u[i-1] - 2*u[i] + u[i+1])

        Stable for alpha < 0.5.
        """
        import time
        start = time.time()
        size  = grid.size
        alpha = grid.alpha
        u     = list(grid.data)

        frame_interval = max(1, steps // frame_count)
        frames = [u[:]]

        for s in range(steps):
            u_new = u[:]
            for i in range(1, size - 1):
                u_new[i] = u[i] + alpha * (u[i-1] - 2*u[i] + u[i+1])
            u = u_new
            if (s + 1) % frame_interval == 0:
                frames.append(u[:])

        return Result1D(frames, size, steps, "laplacian_1d",
                        elapsed_s=round(time.time() - start, 3))

    # ── 2D problems ────────────────────────────────────────────────────────────

    def laplacian_2d(self, grid: Grid2D, alpha: float = 0.1,
                     steps: int = 50, frame_count: int = 5) -> Result2D:
        """2D heat diffusion with 5-point stencil."""
        import time
        start = time.time()
        w, h  = grid.width, grid.height
        u     = [row[:] for row in grid.data]
        frame_interval = max(1, steps // frame_count)
        frames = [[row[:] for row in u]]

        for s in range(steps):
            u_new = [[0.0]*w for _ in range(h)]
            for i in range(1, h-1):
                for j in range(1, w-1):
                    u_new[i][j] = u[i][j] + alpha * (
                        u[i-1][j] + u[i+1][j] +
                        u[i][j-1] + u[i][j+1] - 4*u[i][j])
            for i in range(h):
                u[i] = u_new[i][:]
            if (s + 1) % frame_interval == 0:
                frames.append([row[:] for row in u])

        return Result2D(frames, w, h, steps, "laplacian_2d",
                        elapsed_s=round(time.time() - start, 3))

    def wave_2d(self, grid: Grid2D, c: float = 0.3,
                steps: int = 50, frame_count: int = 5) -> Result2D:
        """2D wave equation: u_tt = c² ∇²u"""
        import time
        start = time.time()
        w, h  = grid.width, grid.height
        u     = [row[:] for row in grid.data]
        u_prev = [row[:] for row in u]
        frame_interval = max(1, steps // frame_count)
        frames = [[row[:] for row in u]]

        for s in range(steps):
            u_new = [[0.0]*w for _ in range(h)]
            for i in range(1, h-1):
                for j in range(1, w-1):
                    lap = (u[i-1][j] + u[i+1][j] +
                           u[i][j-1] + u[i][j+1] - 4*u[i][j])
                    u_new[i][j] = 2*u[i][j] - u_prev[i][j] + c*c*lap
            u_prev = [row[:] for row in u]
            u = u_new
            if (s + 1) % frame_interval == 0:
                frames.append([row[:] for row in u])

        return Result2D(frames, w, h, steps, "wave_2d",
                        elapsed_s=round(time.time() - start, 3))

    def gray_scott(self, grid: Grid2D, F: float = 0.055, k: float = 0.062,
                   Du: float = 0.16, Dv: float = 0.08,
                   steps: int = 200, frame_count: int = 5) -> Result2D:
        """
        Gray-Scott reaction-diffusion system.
        tile_config: default (no div/sqrt — stencil only)
        """
        import time
        start = time.time()
        w, h = grid.width, grid.height

        # Use seed data if available
        u = getattr(grid, 'u', None) or [[1.0]*w for _ in range(h)]
        v = getattr(grid, 'v', None) or [[0.0]*w for _ in range(h)]

        frame_interval = max(1, steps // frame_count)
        frames = [[row[:] for row in v]]

        for s in range(steps):
            u_new = [[0.0]*w for _ in range(h)]
            v_new = [[0.0]*w for _ in range(h)]
            for i in range(h):
                for j in range(w):
                    ip=(i+1)%h; im=(i-1)%h
                    jp=(j+1)%w; jm=(j-1)%w
                    lap_u = u[ip][j]+u[im][j]+u[i][jp]+u[i][jm]-4*u[i][j]
                    lap_v = v[ip][j]+v[im][j]+v[i][jp]+v[i][jm]-4*v[i][j]
                    uvv   = u[i][j]*v[i][j]*v[i][j]
                    u_new[i][j] = u[i][j]+Du*lap_u-uvv+F*(1-u[i][j])
                    v_new[i][j] = v[i][j]+Dv*lap_v+uvv-(F+k)*v[i][j]
            u, v = u_new, v_new
            if (s + 1) % frame_interval == 0:
                frames.append([row[:] for row in v])

        return Result2D(frames, w, h, steps, "gray_scott",
                        elapsed_s=round(time.time() - start, 3))

    def ising(self, grid: Grid2D, T: float = 2.5,
              steps: int = 100, frame_count: int = 5) -> Result2D:
        """Ising spin model — Metropolis algorithm."""
        import time, random
        start = time.time()
        w, h  = grid.width, grid.height
        spins = getattr(grid, 'data', None) or \
                [[random.choice([-1.0, 1.0]) for _ in range(w)]
                 for _ in range(h)]
        spins = [row[:] for row in spins]

        frame_interval = max(1, steps // frame_count)
        frames = [[row[:] for row in spins]]

        for s in range(steps):
            for _ in range(w * h):
                i = random.randint(0, h-1)
                j = random.randint(0, w-1)
                nb = (spins[(i-1)%h][j] + spins[(i+1)%h][j] +
                      spins[i][(j-1)%w] + spins[i][(j+1)%w])
                dE = 2 * spins[i][j] * nb
                if dE < 0 or random.random() < math.exp(-dE / T):
                    spins[i][j] *= -1
            if (s + 1) % frame_interval == 0:
                frames.append([row[:] for row in spins])

        return Result2D(frames, w, h, steps, "ising",
                        elapsed_s=round(time.time() - start, 3))

    # ── Particle problems ──────────────────────────────────────────────────────

    def nbody(self, n: int = 8, steps: int = 50,
              dt: float = 0.01, seed: int = 42,
              frame_count: int = 10) -> ResultParticles:
        """
        N-body gravitational simulation.
        tile_config: low_latency (div+sqrt on critical path per pair)
        """
        import time, random
        random.seed(seed)
        start = time.time()

        pos  = [[random.uniform(-1, 1), random.uniform(-1, 1)] for _ in range(n)]
        vel  = [[0.0, 0.0] for _ in range(n)]
        mass = [1.0] * n

        frame_interval = max(1, steps // frame_count)
        trajectories = [[p[:] for p in pos]]

        for s in range(steps):
            forces = [[0.0, 0.0] for _ in range(n)]
            for i in range(n):
                for j in range(i+1, n):
                    dx = pos[j][0]-pos[i][0]
                    dy = pos[j][1]-pos[i][1]
                    r  = math.sqrt(dx*dx + dy*dy + 0.01)
                    f  = mass[i]*mass[j] / (r*r*r)
                    forces[i][0] += f*dx; forces[i][1] += f*dy
                    forces[j][0] -= f*dx; forces[j][1] -= f*dy
            for i in range(n):
                vel[i][0] += forces[i][0]*dt/mass[i]
                vel[i][1] += forces[i][1]*dt/mass[i]
                pos[i][0] += vel[i][0]*dt
                pos[i][1] += vel[i][1]*dt
            if (s + 1) % frame_interval == 0:
                trajectories.append([p[:] for p in pos])

        return ResultParticles(trajectories, n, steps, "nbody",
                               elapsed_s=round(time.time() - start, 3))

    def boids(self, n: int = 16, steps: int = 100,
              seed: int = 42, frame_count: int = 10) -> ResultParticles:
        """
        Reynolds boids flocking.
        tile_config: low_latency (distance normalisation per pair)
        """
        import time, random
        random.seed(seed)
        start = time.time()

        pos = [[random.uniform(0, 1), random.uniform(0, 1)] for _ in range(n)]
        vel = [[random.uniform(-0.02, 0.02), random.uniform(-0.02, 0.02)]
               for _ in range(n)]

        frame_interval = max(1, steps // frame_count)
        trajectories = [[p[:] for p in pos]]

        for s in range(steps):
            for i in range(n):
                sep=[0.0,0.0]; aln=[0.0,0.0]; coh=[0.0,0.0]; cnt=0
                for j in range(n):
                    if i == j: continue
                    dx=pos[j][0]-pos[i][0]; dy=pos[j][1]-pos[i][1]
                    d = math.sqrt(dx*dx + dy*dy) + 1e-6
                    if d < 0.1:
                        sep[0] -= dx/d; sep[1] -= dy/d
                    if d < 0.2:
                        aln[0] += vel[j][0]; aln[1] += vel[j][1]
                        coh[0] += pos[j][0]; coh[1] += pos[j][1]
                        cnt += 1
                if cnt:
                    coh[0]=coh[0]/cnt-pos[i][0]
                    coh[1]=coh[1]/cnt-pos[i][1]
                vel[i][0] += 0.05*sep[0]+0.05*aln[0]+0.01*coh[0]
                vel[i][1] += 0.05*sep[1]+0.05*aln[1]+0.01*coh[1]
                spd = math.sqrt(vel[i][0]**2+vel[i][1]**2)+1e-6
                if spd > 0.03:
                    vel[i][0] *= 0.03/spd; vel[i][1] *= 0.03/spd
                pos[i][0] = (pos[i][0]+vel[i][0]) % 1.0
                pos[i][1] = (pos[i][1]+vel[i][1]) % 1.0
            if (s + 1) % frame_interval == 0:
                trajectories.append([p[:] for p in pos])

        return ResultParticles(trajectories, n, steps, "boids",
                               elapsed_s=round(time.time() - start, 3))

    # ── Graph problems ─────────────────────────────────────────────────────────

    def pagerank(self, nodes: int = 16, steps: int = 20,
                 damping: float = 0.85, seed: int = 42) -> dict:
        """
        PageRank graph diffusion.
        tile_config: const_divisor (degree fixed at compile time)
        Returns convergence history.
        """
        import time, random
        random.seed(seed)
        start = time.time()

        edges = {i: [j for j in range(nodes) if j!=i and random.random()<0.3]
                 for i in range(nodes)}
        for i in range(nodes):
            if not edges[i]: edges[i] = [(i+1) % nodes]

        rank = [1.0/nodes] * nodes
        history = [rank[:]]

        for _ in range(steps):
            new_rank = [(1-damping)/nodes] * nodes
            for i in range(nodes):
                for j in edges[i]:
                    new_rank[j] += damping * rank[i] / len(edges[i])
            rank = new_rank
            history.append(rank[:])

        return {
            "type":      "rank_history",
            "model":     "pagerank",
            "nodes":     nodes,
            "steps":     steps,
            "elapsed_s": round(time.time() - start, 3),
            "history":   history,
            "final":     rank,
        }

    # ── Conway ────────────────────────────────────────────────────────────────

    def conway(self, grid: Grid2D, steps: int = 50,
               frame_count: int = 5) -> Result2D:
        """Continuous Game of Life with smooth state transitions."""
        import time, random
        start = time.time()
        w, h  = grid.width, grid.height
        g     = [row[:] for row in grid.data] if any(any(r) for r in grid.data) \
                else [[random.random() for _ in range(w)] for _ in range(h)]

        frame_interval = max(1, steps // frame_count)
        frames = [[row[:] for row in g]]

        for s in range(steps):
            g_new = [[0.0]*w for _ in range(h)]
            for i in range(h):
                for j in range(w):
                    nb = sum(g[(i+di)%h][(j+dj)%w]
                             for di in [-1,0,1] for dj in [-1,0,1]
                             if (di,dj) != (0,0))
                    c = g[i][j]
                    if c > 0.5:
                        g_new[i][j] = 1.0 if 1.5<nb<3.5 else max(0.0, c-0.1)
                    else:
                        g_new[i][j] = min(1.0, c+0.05) if 2.5<nb<3.5 \
                                      else max(0.0, c-0.05)
            g = g_new
            if (s + 1) % frame_interval == 0:
                frames.append([row[:] for row in g])

        return Result2D(frames, w, h, steps, "conway",
                        elapsed_s=round(time.time() - start, 3))


# ── Convenience functions ─────────────────────────────────────────────────────

def quick_laplacian(size: int = 64, steps: int = 100,
                    alpha: float = 0.1) -> Result1D:
    """One-liner: run 1D heat diffusion with Gaussian IC."""
    mt = MathTrix()
    grid = Grid1D(size=size, alpha=alpha).set_gaussian()
    return mt.laplacian_1d(grid, steps=steps)


def quick_gray_scott(size: int = 32, steps: int = 200,
                     F: float = 0.055, k: float = 0.062) -> Result2D:
    """One-liner: run Gray-Scott with default seed."""
    import random; random.seed(42)
    mt = MathTrix()
    grid = Grid2D(width=size, height=size).set_seed()
    return mt.gray_scott(grid, F=F, k=k, steps=steps)


def quick_nbody(n: int = 8, steps: int = 100) -> ResultParticles:
    """One-liner: run N-body gravity simulation."""
    return MathTrix().nbody(n=n, steps=steps)


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("MathTrix Frontend Demo")
    print("=" * 40)

    mt = MathTrix()

    print("\n1D Laplacian (heat diffusion):")
    r1 = quick_laplacian(size=32, steps=50)
    print(f"  Size={r1.size} Steps={r1.steps} Frames={len(r1.frames)}")
    print(f"  Initial centre: {r1.frames[0][16]:.4f}")
    print(f"  Final centre:   {r1.final[16]:.4f}")
    print(f"  Elapsed: {r1.elapsed_s}s")

    print("\n2D Wave equation:")
    grid2d = Grid2D(32, 32).set_gaussian()
    r2 = mt.wave_2d(grid2d, c=0.3, steps=30)
    print(f"  {r2.width}x{r2.height} grid, {r2.steps} steps, {len(r2.frames)} frames")
    print(f"  Elapsed: {r2.elapsed_s}s")

    print("\nN-body gravity:")
    r3 = quick_nbody(n=6, steps=50)
    print(f"  {r3.n} bodies, {r3.steps} steps, {len(r3.trajectories)} frames")
    print(f"  Elapsed: {r3.elapsed_s}s")

    print("\nAll demos complete ✓")
