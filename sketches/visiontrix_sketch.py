"""
visiontrix_sketch.py — VisionTrix tile cost sketch

Vision data arrives from a VideoBridge / UVC camera. The cheapest useful
operation is a 3×3 Sobel edge detector — it only needs integer add/subtract
on 8-bit pixel values, no multiply, no float.

VISIONTRIX FORMAT:
  Alphabet: 8-bit luminance (Y channel from YUV, or grayscale)
  Encoding: 4 pixels per 32-bit cell word (8 bits each, packed)
  On-fabric: a window of neighbouring pixels in cell registers

SOBEL EDGE DETECTOR — why it's the right first tile:
  Gx = (p02 + 2*p12 + p22) - (p00 + 2*p10 + p20)
  Gy = (p20 + 2*p21 + p22) - (p00 + 2*p01 + p02)
  |G| ≈ |Gx| + |Gy|   (L1 approximation to avoid SQRT)

  2*p = p + p = one INT32_ADD  (no multiply needed — coefficient is 2)
  All operations are INT32_ADD / INT32_SUB on 8-bit values in 32-bit words.
  
  Sobel requires 9 pixel neighbours (3×3 window). In the fabric these live
  in 9 preloaded cell registers — the window slides by reloading 3 cells
  (one new column) per pixel column advance. Streaming-window model, exactly
  like the temporal-blocking model in FlowTrix.

COST ESTIMATE — Sobel Gx path (one direction):
  Step 1: 2*p10 = p10 + p10              1 × INT32_ADD  = 482c  d10
  Step 2: row_top = p00 + (2*p10) + p20  2 × INT32_ADD  = 964c  d20
          (but pipeline: d10 for first ADD, then d10 more for second = d20)
  Step 3: 2*p12 = p12 + p12              1 × INT32_ADD  = 482c  d10  (parallel)
  Step 4: row_bot = p02 + (2*p12) + p22  2 × INT32_ADD  = 964c  d20  (parallel)
  Step 5: Gx = row_bot - row_top         1 × INT32_SUB  = 517c  d12

  Gx critical path: d20 (row computation) + d12 (subtract) = d32
  Gx cells (sequential, non-parallel stages share no cells):
    2×p10: 482 + 2×482 (row_top adds) = 482+482+482 = 1446c for top row
    2×p12: 482 + 482+482 = 1446c for bottom row  (parallel to top)
    subtract: 517c
  
  Gx ALONE: 1446 + 1446 + 517 = 3409c (parallel rows counted once each)
  
  BUT: many additions can be shared between Gx and Gy. 
  p10+p10 appears in Gx; p01+p01 appears in Gy. No sharing there.
  The |Gx| + |Gy| final step needs ABS — which is 0 cells (sign bit only in MIF,
  but for raw int we need: if negative, negate = one INT32_SUB from zero, 517c).

  Full Sobel (Gx + Gy + |Gx|+|Gy|):
    Gx path:    ~3409c
    Gy path:    ~3409c  (parallel, same structure)
    ABS(Gx):    517c
    ABS(Gy):    517c
    |Gx|+|Gy|: 482c
    
  Total: ~8334c — FAR outside 900c budget.

WHAT ACTUALLY FITS — pixel-level operations only:

  PIXEL_THRESHOLD (is luminance Y above threshold T?):
    INT32_LT_U: 518c  d14  ✓ fits
    Output: 1-bit edge/non-edge mask. Simple but useful for binary blob detection.

  PIXEL_DELTA (luminance difference between two pixels — temporal or spatial):
    INT32_SUB: 517c  d12  ✓ fits
    Use: frame differencing (motion detection) or horizontal pixel difference
         (crude 1D edge, no 3×3 window needed)
    
  PIXEL_ACCUMULATE (sum N pixels into a running total for mean filter):
    INT32_ADD: 482c  d10  ✓ fits
    Temporal blocking: reload window cells, accumulate N passes.

  1D HORIZONTAL DIFFERENCE (p[x] - p[x-1]):
    INT32_SUB with preloaded p[x-1]: 517c  d12  ✓ fits
    This IS a 1D edge detector — finds luminance steps along a scanline.
    Cheap, real, and useful as a NeuroTrix input (feed delta as LIF current).

HONEST SUMMARY:
  Full Sobel 3×3:     ~8334c  ✗  (9× budget)
  Pixel threshold:      518c  ✓
  Pixel delta (1 axis): 517c  ✓
  Frame difference:     517c  ✓  (temporal: this frame minus last frame)
  1D scanline edge:     517c  ✓

PRACTICAL APPROACH at 900c:
  One tile = one operation on one pixel or one pixel pair.
  A spatial filter needs TEMPORAL BLOCKING: load a window column into preloaded
  registers, compute one output pixel per pass, slide by reloading 3 cells.
  Sobel over a 640×480 frame = 640×480 fabric passes × 1 tile.
  SAME model as FlowTrix temporal blocking — exactly the right mental frame.
  On the Arria 10 at scale (many parallel tiles) this collapses.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from fp_tiles import TileLibrary

lib = TileLibrary()

def cost(name):
    t = lib.get(name)
    m = t.metadata
    return m.cell_count, getattr(m,'depth', getattr(m,'pipeline_depth',0))

add_c, add_d = cost('INT32_ADD')
sub_c, sub_d = cost('INT32_SUB')
ltu_c, ltu_d = cost('INT32_LT_U')

# Sobel Gx: three rows of pixels, weighted sum then subtract
# Row = p_left + 2*p_mid + p_right = ADD + ADD + ADD (sequential)
# 2*p_mid = p_mid + p_mid = one ADD
gx_double  = add_c                        # 2*p_mid
gx_row     = add_c + add_c               # + p_left, + p_right  (2 adds sequential)
gx_row_d   = add_d + add_d
gx_row_total = gx_double + gx_row        # cells for one weighted row
gx_subtract = sub_c                       # row_bot - row_top
# Two rows run in parallel: total cells = 2 × row + 1 × subtract
gx_cells = 2 * gx_row_total + gx_subtract
gx_depth = (add_d + gx_row_d + sub_d)    # double + row + subtract sequential

# Full Sobel: Gx + Gy (parallel) + 2×ABS + final ADD
sobel_abs = sub_c   # ABS via: if negative, 0-x; approximate with one SUB
full_sobel_cells = 2 * gx_cells + 2 * sobel_abs + add_c
full_sobel_depth = gx_depth + sub_d + add_d   # Gx/Gy parallel, then ABS, then sum

print("=== VisionTrix Tile Cost Sketch ===")
print()
print(f"Primitives:")
print(f"  INT32_ADD:   {add_c}c  d{add_d}")
print(f"  INT32_SUB:   {sub_c}c  d{sub_d}")
print(f"  INT32_LT_U:  {ltu_c}c  d{ltu_d}")
print()
print(f"Sobel 3×3 edge detector:")
print(f"  Gx (one direction):          {gx_cells}c  d{gx_depth}")
print(f"  Full Sobel (Gx+Gy+|G|):     {full_sobel_cells}c  d{full_sobel_depth}")
print(f"  Fits 900c? {'✓' if full_sobel_cells<=900 else f'✗  ({full_sobel_cells//900:.0f}× over budget)'}")
print()
print(f"What actually fits in 900c:")
for label, cells, depth in [
    ("PIXEL_THRESHOLD (LT_U: Y >= T?)",          ltu_c, ltu_d),
    ("PIXEL_DELTA (SUB: frame diff / 1D edge)",   sub_c, sub_d),
    ("PIXEL_ACCUMULATE (ADD: mean filter step)",  add_c, add_d),
    ("1D_SCANLINE_EDGE (SUB with preloaded prev)",sub_c, sub_d),
]:
    print(f"  {label}")
    print(f"    {cells}c  d{depth}  {'✓' if cells<=900 else '✗'}")
print()
print("Approach for Sobel at 900c budget:")
print("  TEMPORAL BLOCKING — same model as FlowTrix:")
print("  1 PIXEL_DELTA tile, 640×480 fabric passes per frame.")
print("  Preloaded registers hold the 3×3 window; slide by reloading 3 cells")
print("  per column advance. On GX660 at scale: many parallel tiles,")
print("  window slides across all columns simultaneously.")

