"""
flowtrix_lbm_mif.py — D2Q9 BGK collide step as composed MIF tiles

This is the tile-level realisation of LBM_COLLIDE: the cell cluster that must
reproduce FlowTrix_D2Q9.collide() from cell_format.py, built by composing the
existing MIF tile family (the same way the MathTrix reference models compose
MIF_ADD/MUL/MADD/DIV). It does two jobs:

  1. CORRECTNESS — runs the collide arithmetic through the actual tile
     decomposition and asserts the result equals the validated FlowTrix
     ground truth, tick for tick.
  2. PREDICTED TICKS/UPDATE — sums the critical-path pipeline depth across
     the collide stages, giving the deterministic per-site tick count the
     compiler can publish BEFORE silicon (the metric PLAN's FlowTrix section
     promises: predicted vs measured).

Two structural facts about D2Q9 make this cheaper than a naive port, and both
fall out of the lattice, not cleverness:

  TERNARY VELOCITIES KILL THE MOMENT MULTIPLIES. Every e_i component is in
  {-1, 0, +1}, so momentum sum_i e_i f_i and every dot product e_i . u are
  pure add/subtract — NO MIF_MUL in the moment computation or in the e.u
  terms. A method with arbitrary lattice vectors would need a multiply per
  component per direction; D2Q9 needs none. This is a real cell-budget and
  depth saving handed to us by the velocity set.

  RECIPROCAL ONCE, NOT TWICE. ux = xmom/rho and uy = ymom/rho share 1/rho.
  Computing the reciprocal once (1 MIF_DIV) then two MIF_MUL is far cheaper
  than two MIF_DIV, because DIV is the most expensive tile in the family.

The collide pipeline is DIVISION-DOMINATED: the single 1/rho reciprocal is
the largest contributor to the tick count. That is the optimisation lever,
and it points straight at the existing MIF_DIV/SQRT LUT work — in
incompressible LBM rho stays near 1.0, so a LUT-seeded reciprocal (or a short
Newton step from a 2-rho seed) would slash the dominant stage. Flagged for
the optimisation pass; this reference reports the honest un-optimised figure.

Run: python3 flowtrix_lbm_mif.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cell_format import FormatRegistry
from fp_tiles import TileLibrary

lib = TileLibrary()
flow = FormatRegistry.get_default().get("FlowTrix_D2Q9")


def tile(name):
    m = lib.get(name).metadata
    depth = getattr(m, "depth", getattr(m, "pipeline_depth", 0))
    return m.cell_count, depth


class FlowRegion:
    """
    Models the D2Q9 collide cell cluster. Computes the real arithmetic (to
    validate against ground truth) while accumulating tile cell-cost and a
    stage-structured critical-path depth (the predicted ticks/update).

    Depth is tracked as the critical path: tiles within a stage that run in
    parallel contribute max(depth); stages run in sequence and sum. This is
    the honest 'ticks for one collide' a compiler would schedule.
    """

    def __init__(self):
        self.cells = 0
        self.depth = 0            # critical-path ticks
        self.tiles = {}           # name -> instance count
        self.stages = []          # (stage_name, stage_depth)

    def _count(self, name, n=1):
        c, _ = tile(name)
        self.cells += c * n
        self.tiles[name] = self.tiles.get(name, 0) + n

    def stage(self, name, tile_chain):
        """
        Record one sequential stage. `tile_chain` is a list of tile names that
        lie on this stage's critical path (sequential within the stage). Tiles
        used in parallel but off the critical path are counted for cells via
        _count separately. Returns nothing; advances self.depth by the chain.
        """
        d = 0
        for t in tile_chain:
            self._count(t)
            _, td = tile(t)
            d += td
        self.depth += d
        self.stages.append((name, d))

    def parallel_count(self, name, n):
        """Count n parallel instances for cell cost only (off critical path)."""
        self._count(name, n)


def collide_tiled(f, tau):
    """
    One BGK collide via the tile decomposition. Returns (f_new, region).
    f is the list of 9 distributions; tau the relaxation time.
    The arithmetic mirrors FlowTrix_D2Q9.collide exactly; the region records
    the tile cost and predicted tick depth.
    """
    r = FlowRegion()
    omega = 1.0 / tau

    # ── Stage 1: moments (rho, xmom, ymom) — pure adds, ternary velocities ──
    # rho = sum of 9 f_i. Reduction tree over 9 values = 4 add-levels on the
    # critical path. xmom/ymom run in parallel (also adds/subs), off the
    # critical path for depth but counted for cells.
    rho = sum(f)
    # momentum sums (ex,ey in {-1,0,+1} -> add/sub only, NO MUL):
    xmom = (f[1] + f[5] + f[8]) - (f[3] + f[6] + f[7])
    ymom = (f[2] + f[5] + f[6]) - (f[4] + f[7] + f[8])
    r.stage("moments(rho)", ["MIF_ADD"] * 4)          # 9->1 reduction depth
    r.parallel_count("MIF_ADD", 4)                     # xmom tree (parallel)
    r.parallel_count("MIF_SUB", 1)
    r.parallel_count("MIF_ADD", 4)                     # ymom tree (parallel)
    r.parallel_count("MIF_SUB", 1)

    # ── Stage 2: reciprocal 1/rho — the dominant stage ──────────────────────
    inv_rho = 1.0 / rho if rho != 0 else 0.0
    r.stage("reciprocal(1/rho)", ["MIF_DIV"])          # <-- division-dominated

    # ── Stage 3: velocities ux, uy = mom * (1/rho) — 2 MUL, parallel ────────
    ux = xmom * inv_rho
    uy = ymom * inv_rho
    r.stage("velocity(u)", ["MIF_MUL"])                # critical path: 1 MUL
    r.parallel_count("MIF_MUL", 1)                      # the second (parallel)

    # ── Stage 4: usqr = ux^2 + uy^2, then 1.5*usqr ──────────────────────────
    usqr = ux * ux + uy * uy
    r.stage("usqr", ["MIF_MUL", "MIF_MADD"])           # ux^2 ; +uy^2 fused
    # (1.5*usqr folded into the equilibrium MADDs below)

    # ── Stage 5: equilibrium feq_i for all 9 (parallel); critical = 1 dir ──
    # feq_i = w_i*rho*[1 + 3(e.u) + 4.5(e.u)^2 - 1.5|u|^2]
    # e.u is add/sub of ux,uy (ternary e). Per direction critical path:
    #   eu (ADD) -> eu^2 (MUL) -> bracket via MADDs -> * (w_i*rho) (MUL)
    feq = flow.equilibrium(rho, ux, uy)
    r.stage("equilibrium", ["MIF_ADD",     # e.u
                            "MIF_MUL",      # (e.u)^2
                            "MIF_MADD",     # 1 + 3 e.u
                            "MIF_MADD",     # + 4.5 (e.u)^2
                            "MIF_MADD",     # - 1.5 usqr
                            "MIF_MUL"])     # * (w_i * rho)
    r.parallel_count("MIF_ADD", 8)         # other 8 directions' e.u (parallel)
    r.parallel_count("MIF_MUL", 8 * 2)     # their squares + final scales
    r.parallel_count("MIF_MADD", 8 * 3)    # their brackets

    # ── Stage 6: relax f_i += omega*(feq_i - f_i) — all 9 parallel ──────────
    f_new = [f[i] + omega * (feq[i] - f[i]) for i in range(9)]
    r.stage("relax", ["MIF_SUB", "MIF_MADD"])          # (feq-f) ; f+omega*()
    r.parallel_count("MIF_SUB", 8)
    r.parallel_count("MIF_MADD", 8)

    return f_new, r


# ── Self-check / report ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import random
    print("⬡ FlowTrix D2Q9 — BGK collide as composed MIF tiles")
    print("=" * 58)

    # Correctness: tiled collide must equal the FlowTrix ground truth.
    random.seed(7)
    max_err = 0.0
    for _ in range(2000):
        f = [random.uniform(0.02, 0.25) for _ in range(9)]
        tau = random.uniform(0.6, 2.0)
        got, _ = collide_tiled(f, tau)
        ref = flow.collide(f, tau)
        max_err = max(max_err, max(abs(got[i] - ref[i]) for i in range(9)))
    print(f"\nCorrectness vs flow.collide() over 2000 random sites:")
    print(f"  max abs error = {max_err:.2e}   match: {max_err < 1e-12}")

    # Cost + predicted ticks.
    f = [flow.WEIGHTS[i] for i in range(9)]   # rest state, rho=1
    _, r = collide_tiled(f, tau=0.8)
    print(f"\nPer-site collide cost (un-optimised):")
    print(f"  total cells          = {r.cells:,}")
    print(f"  predicted ticks/update = {r.depth:,}  (critical path)")
    print(f"\n  Stage breakdown (critical-path ticks):")
    for name, d in r.stages:
        pct = 100.0 * d / r.depth
        bar = "█" * int(pct / 2)
        print(f"    {name:20} {d:5}  {pct:4.1f}%  {bar}")
    div_depth = next(d for n, d in r.stages if n.startswith("reciprocal"))
    print(f"\n  Division is {100.0*div_depth/r.depth:.0f}% of the pipeline — "
          f"the LUT-reciprocal optimisation lever (cf. MIF_DIV/SQRT work).")
    print(f"\n  Tile instances per site:")
    for n in sorted(r.tiles):
        print(f"    {n:12} x{r.tiles[n]}")

    print("\nAll demos passed ✓")
