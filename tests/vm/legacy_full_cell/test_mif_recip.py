#!/usr/bin/env python3
"""
test_mif_recip.py — MIF_RECIP (LUT-seeded Newton-Raphson reciprocal) tile.

MIF_RECIP exposes the previously-private LUT-NR reciprocal as a first-class
tile. It is the shallow primitive for 1/B (e.g. 1/rho in the LBM collide),
far shallower than full MIF_DIV at the cost of more cells. These checks cover
registration, the depth advantage that motivates it, and its use in the collide.

Note: like the rest of the MIF family, MIF_RECIP is a structural/cost tile —
pipeline depth and cell count are modelled; the numeric reference is computed
in float by the caller. This suite asserts those structural properties, not a
run_tile numeric evaluation of the NR mantissa path.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fp_tiles import TileLibrary, make_mif_recip, TIER_FLOAT, _TILE_TIERS
from flowtrix_lbm_mif import collide_tiled
from cell_format import FormatRegistry

passed = failed = 0
fails = []
def check(label, cond):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1; fails.append(label)

lib = TileLibrary()

# ── Registration ─────────────────────────────────────────────────────────────
recip = lib.get("MIF_RECIP")
check("MIF_RECIP is registered in the library", recip is not None)
check("MIF_RECIP operation metadata is MIF_RECIP", recip.metadata.operation == "MIF_RECIP")
check("MIF_RECIP is in the float tier", _TILE_TIERS.get("MIF_RECIP") == TIER_FLOAT)
check("make_mif_recip builds standalone", make_mif_recip().metadata.operation == "MIF_RECIP")

# ── Shape: single input (1/B), B on in_b ─────────────────────────────────────
check("MIF_RECIP has a B input", len(recip.in_b) > 0)
check("MIF_RECIP has 32-bit precision", recip.metadata.precision == 32)
check("MIF_RECIP output is one MIF word (64 bits: ctrl+mant)", len(recip.out) == 64)

# ── The depth advantage that motivates the tile ──────────────────────────────
div = lib.get("MIF_DIV")
check("MIF_RECIP is shallower than MIF_DIV", recip.metadata.pipeline_depth < div.metadata.pipeline_depth)
check("MIF_RECIP depth is ~349", 300 <= recip.metadata.pipeline_depth <= 400)
check("MIF_DIV depth is ~1177", 1100 <= div.metadata.pipeline_depth <= 1250)
# 3x+ shallower is the whole point (depth/area trade)
check("MIF_RECIP is at least 3x shallower than MIF_DIV",
      div.metadata.pipeline_depth >= 3 * recip.metadata.pipeline_depth)
check("MIF_RECIP costs more cells than MIF_DIV (the trade)",
      recip.metadata.cell_count > div.metadata.cell_count)

# ── Integration: the collide now uses MIF_RECIP, numeric result unchanged ─────
flow = FormatRegistry.get_default().get("FlowTrix_D2Q9")
f = [flow.WEIGHTS[i] for i in range(9)]
f_new, region = collide_tiled(f, tau=0.8)

check("collide uses exactly one MIF_RECIP", region.tiles.get("MIF_RECIP") == 1)
check("collide no longer uses full MIF_DIV", "MIF_DIV" not in region.tiles)
check("collide critical path is the optimised 1714", region.depth == 1714)

# numeric: tile decomposition still matches the reference collide to fp precision
ref = flow.collide(f, tau=0.8)
maxerr = max(abs(a - b) for a, b in zip(f_new, ref))
check("collide matches FlowTrix_D2Q9.collide to machine precision", maxerr < 1e-12)

# ── Report ───────────────────────────────────────────────────────────────────
print(f"\nResults: {passed} passed, {failed} failed out of {passed + failed} tests")
if fails:
    print("Failed tests:")
    for f_ in fails:
        print(f"  {f_}")
    sys.exit(1)
print("ALL TESTS PASSED")
