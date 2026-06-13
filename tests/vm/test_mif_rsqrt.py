#!/usr/bin/env python3
"""
test_mif_rsqrt.py — MIF_RSQRT (LUT-seeded Newton-Raphson reciprocal square root).

MIF_RSQRT computes 1/sqrt(B) as a single fused tile, for kernels that normalise
a vector (1/|v|) or take a gravitational 1/r factor — replacing a separate
MIF_SQRT followed by MIF_RECIP/MIF_DIV. Its win is in *depth* (latency); it
costs more cells — the same depth-for-cells trade as MIF_RECIP. These checks
cover registration, that fused depth advantage, and the trade.

Like the rest of the MIF NR family this is a structural/cost tile: depth and
cells are modelled; the LUT mantissa path is depth-tracking, not run_tile
numerically validated. The suite asserts those structural properties.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fp_tiles import TileLibrary, make_mif_rsqrt, TIER_FLOAT, _TILE_TIERS
from cell_format import FormatRegistry

passed = failed = 0
fails = []
def check(label, cond):
    global passed, failed
    if cond: passed += 1
    else: failed += 1; fails.append(label)

lib = TileLibrary()

# ── Registration ─────────────────────────────────────────────────────────────
rs = lib.get("MIF_RSQRT")
check("MIF_RSQRT is registered", rs is not None)
check("MIF_RSQRT operation metadata is MIF_RSQRT", rs.metadata.operation == "MIF_RSQRT")
check("MIF_RSQRT is in the float tier", _TILE_TIERS.get("MIF_RSQRT") == TIER_FLOAT)
check("make_mif_rsqrt builds standalone", make_mif_rsqrt().metadata.operation == "MIF_RSQRT")
check("MIF_RSQRT is valid in the MIF format",
      FormatRegistry.get_default().get("MIF").validate_tile("MIF_RSQRT")[0])

# ── Shape: single input (1/sqrt(B)), B on in_b ───────────────────────────────
check("MIF_RSQRT has a B input", len(rs.in_b) > 0)
check("MIF_RSQRT output is one MIF word (64 bits)", len(rs.out) == 64)
check("MIF_RSQRT is 32-bit precision", rs.metadata.precision == 32)

# ── The fused-depth advantage that motivates the tile ────────────────────────
sq = lib.get("MIF_SQRT")
rc = lib.get("MIF_RECIP")
dv = lib.get("MIF_DIV")
combined_sqrt_recip = sq.metadata.pipeline_depth + rc.metadata.pipeline_depth
combined_sqrt_div   = sq.metadata.pipeline_depth + dv.metadata.pipeline_depth

check("MIF_RSQRT shallower than MIF_SQRT alone",
      rs.metadata.pipeline_depth < sq.metadata.pipeline_depth)
check("MIF_RSQRT much shallower than MIF_SQRT + MIF_RECIP",
      rs.metadata.pipeline_depth < combined_sqrt_recip)
check("MIF_RSQRT is at least 3x shallower than sqrt+recip",
      combined_sqrt_recip >= 3 * rs.metadata.pipeline_depth)
check("MIF_RSQRT far shallower than sqrt+div",
      rs.metadata.pipeline_depth * 4 < combined_sqrt_div)
check("MIF_RSQRT depth is ~445", 380 <= rs.metadata.pipeline_depth <= 520)

# ── The trade: rsqrt costs more cells than the separate tiles (depth-for-cells)
check("MIF_RSQRT costs more cells than MIF_SQRT (the trade)",
      rs.metadata.cell_count > sq.metadata.cell_count)
check("MIF_RSQRT does more work than MIF_RECIP (extra mul/iteration)",
      rs.metadata.pipeline_depth > rc.metadata.pipeline_depth)

# ── Report ───────────────────────────────────────────────────────────────────
print(f"\nMIF_RSQRT depth {rs.metadata.pipeline_depth} / cells {rs.metadata.cell_count}; "
      f"sqrt+recip combined depth {combined_sqrt_recip}, sqrt+div {combined_sqrt_div}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if fails:
    print("Failed tests:")
    for f_ in fails:
        print(f"  {f_}")
    sys.exit(1)
print("ALL TESTS PASSED")
