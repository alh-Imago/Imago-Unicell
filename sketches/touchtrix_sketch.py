"""
touchtrix_sketch.py — TouchTrix tile cost sketch

Touch data arrives from a TouchBridge on the bus as a packed 32-bit word
(same protocol as MouseBridge). The fabric-side job is to unpack it into
usable typed values: X coordinate, Y coordinate, pressure, contact ID.

TOUCH EVENT WORD (32-bit, from TouchBridge):
  bits 31-28:  contact ID (0-15, for multitouch)
  bits 27-24:  event type (0=contact, 1=lift, 2=move)
  bits 23-16:  pressure (0-255)
  bits 15-8:   X high byte  (0-255, scaled from device resolution)
  bits  7-0:   Y high byte  (0-255, scaled from device resolution)

Full 16-bit X/Y available via separate GET_X / GET_Y commands (same pattern
as MouseBridge MS_CMD_GET_X / MS_CMD_GET_Y). The packed word gives 8-bit
resolution fast; full resolution costs a second bus transaction.

TILE: TOUCH_UNPACK
  Job: unpack the 32-bit event word into 4 × 8-bit fields on separate
       output addresses so downstream tiles see typed values not a packed int.
  Method: shift + AND masking — pure INT32 operations, no MIF needed.
  
  contact_id = (word >> 28) & 0xF      →  INT32_SHR + INT32_AND  
  event_type = (word >> 24) & 0xF      →  INT32_SHR + INT32_AND  
  pressure   = (word >> 16) & 0xFF     →  INT32_SHR_16 + INT32_AND
  x_hi       = (word >>  8) & 0xFF     →  INT32_SHR_8  + INT32_AND
  y_hi       =  word        & 0xFF     →  INT32_AND only (no shift)

  All 5 fields run IN PARALLEL from the same input word — critical path
  is the deepest single field, not the sum.

Cost estimate (each field is one shift + one AND):
  INT32_SHR_8:  40c  d2   (x_hi)
  INT32_SHR_16: 40c  d2   (pressure — use two SHR_8 in series if no SHR_16)
                           actually SHR_8 twice: 40+40 = 80c d4
  INT32_SHR_4 × 7: 36×7 = 252c  d14  (>> 28 = four SHR_4 in series for contact_id)
  INT32_AND × 5:  32×5  = 160c  d1   (masks run in parallel, 1 tick deep)
  
  Total (parallel fields, non-overlapping cells):
    5 × AND = 160c
    SHR for x_hi:      40c
    SHR for pressure:  80c  (two SHR_8)
    SHR for event_type: 40+40+40 = 120c (SHR_8 × 3 = >> 24)
    SHR for contact_id: 36×7 = 252c (SHR_4 × 7 = >> 28)
    
  Total fabric cells: 160 + 40 + 80 + 120 + 252 = 652c
  Critical path depth: contact_id field = d14 + d1 = d15

FITS IN 800-900c BUDGET: YES, with ~150-250c to spare.

TILE: TOUCH_DELTA
  Job: compute (X - prev_X, Y - prev_Y) — motion delta between contacts.
  Used for gesture recognition (swipe velocity, pinch distance change).
  Needs two INT32_SUB tiles + two preloaded registers (prev_X, prev_Y).
  
  Cost: 2 × INT32_SUB = 2 × 517c = 1034c
  DOES NOT FIT alone. But prev values can be preloaded (preload_sel pattern)
  reducing to: 1 × INT32_SUB (current - preloaded_prev) × 2 outputs = still 1034c.
  
  VERDICT: TOUCH_DELTA does not fit in 800-900c. Needs 2× budget or temporal
  blocking (compute X delta, reload, compute Y delta = 2 pipeline passes).
  On Arria 10 GX660 at scale: trivial. On iCEBreaker: impossible (4-cell limit).

TILE: TOUCH_PRESSURE_THRESHOLD  
  Job: 1-bit output — is pressure above threshold T?
       pressure >= T → 1 (contact confirmed), else 0 (noise rejection)
  Uses: INT32_LT_U (threshold vs pressure, reversed)
  
  Cost: 518c + preloaded T constant = 518c
  FITS IN 800-900c: YES (518c, leaves ~300c).

COMBINED PIPELINE (what fits in ~850c):
  TOUCH_UNPACK + TOUCH_PRESSURE_THRESHOLD in sequence:
    652c + 518c = 1170c  — does NOT fit as one tile.
  
  But: TOUCH_UNPACK feeds TOUCH_PRESSURE_THRESHOLD on the pressure field only.
  The pressure field extraction is INT32_SHR_8 (×2) + INT32_AND = 80+80+32 = 112c.
  TOUCH_PRESSURE_THRESHOLD = 518c.
  Full pressure-gated touch detect = 112 + 518 = 630c. FITS.

  Or: TOUCH_UNPACK (652c) alone fits, feeds downstream tiles via PTT.
  Each downstream tile (pressure threshold, delta, etc.) is a separate pond.

SUMMARY TABLE:
  TOUCH_UNPACK             652c  d15   fits 800-900c ✓
  TOUCH_PRESSURE_THRESHOLD 518c  d14   fits 800-900c ✓
  TOUCH_PRESSURE_DETECT    630c  d16   fits 800-900c ✓ (unpack pressure + threshold)
  TOUCH_DELTA (X or Y)     517c  d12   fits ✓ but needs 2 passes for both axes
  TOUCH_DELTA (X and Y)   1034c  d12   does NOT fit ✗
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from fp_tiles import TileLibrary

lib = TileLibrary()

def cost(name):
    t = lib.get(name)
    m = t.metadata
    return m.cell_count, getattr(m,'depth',getattr(m,'pipeline_depth',0))

# Compute actual costs from library
shr4_c,  shr4_d  = cost('INT32_SHR_4')
shr8_c,  shr8_d  = cost('INT32_SHR_8')
and_c,   and_d   = cost('INT32_AND')
sub_c,   sub_d   = cost('INT32_SUB')
ltu_c,   ltu_d   = cost('INT32_LT_U')
mux_c,   mux_d   = cost('INT32_MUX')

# TOUCH_UNPACK: 5 parallel fields
# y_hi:        AND only                              = and_c,  d=and_d
# x_hi:        SHR_8 + AND                          = shr8_c + and_c
# pressure:    SHR_8 + SHR_8 + AND                  = 2*shr8_c + and_c
# event_type:  SHR_8 + SHR_8 + SHR_8 + AND         = 3*shr8_c + and_c
# contact_id:  SHR_4 × 7 + AND                      = 7*shr4_c + and_c

unpack_cells = (
    and_c +                        # y_hi
    (shr8_c + and_c) +             # x_hi
    (2*shr8_c + and_c) +           # pressure
    (3*shr8_c + and_c) +           # event_type
    (7*shr4_c + and_c)             # contact_id
)
unpack_depth = max(
    and_d,                         # y_hi critical path
    shr8_d + and_d,                # x_hi
    2*shr8_d + and_d,              # pressure
    3*shr8_d + and_d,              # event_type
    7*shr4_d + and_d,              # contact_id (longest)
)

# TOUCH_PRESSURE_DETECT: pressure field extraction + threshold compare
pressure_extract_c = 2*shr8_c + and_c
pressure_extract_d = 2*shr8_d + and_d
touch_detect_c = pressure_extract_c + ltu_c
touch_detect_d = pressure_extract_d + ltu_d

# TOUCH_DELTA single axis (preloaded prev value)
delta_c = sub_c
delta_d = sub_d

print("=== TouchTrix Tile Cost Sketch ===")
print()
print(f"Primitives used:")
print(f"  INT32_SHR_4:  {shr4_c}c  d{shr4_d}")
print(f"  INT32_SHR_8:  {shr8_c}c  d{shr8_d}")
print(f"  INT32_AND:    {and_c}c   d{and_d}")
print(f"  INT32_SUB:    {sub_c}c  d{sub_d}")
print(f"  INT32_LT_U:   {ltu_c}c  d{ltu_d}")
print()
print(f"TOUCH_UNPACK (5 parallel fields from 32-bit event word):")
print(f"  cells = {unpack_cells}c,  depth = d{unpack_depth}")
print(f"  {'FITS' if unpack_cells <= 900 else 'DOES NOT FIT'} in 900c budget")
print()
print(f"TOUCH_PRESSURE_DETECT (pressure extract + threshold gate):")
print(f"  cells = {touch_detect_c}c,  depth = d{touch_detect_d}")
print(f"  {'FITS' if touch_detect_c <= 900 else 'DOES NOT FIT'} in 900c budget")
print()
print(f"TOUCH_DELTA single axis (preloaded prev, one SUB):")
print(f"  cells = {delta_c}c,  depth = d{delta_d}")
print(f"  {'FITS' if delta_c <= 900 else 'DOES NOT FIT'} in 900c budget")
print(f"  NOTE: X and Y together = {2*delta_c}c -- {'fits' if 2*delta_c<=900 else 'does not fit'}")
print()
print(f"Budget summary (900c target):")
print(f"  TOUCH_UNPACK alone:          {unpack_cells}c  {'✓' if unpack_cells<=900 else '✗'}")
print(f"  TOUCH_PRESSURE_DETECT alone: {touch_detect_c}c  {'✓' if touch_detect_c<=900 else '✗'}")
print(f"  TOUCH_DELTA (X only):        {delta_c}c  {'✓' if delta_c<=900 else '✗'}")
print(f"  TOUCH_DELTA (X+Y):           {2*delta_c}c  {'✓' if 2*delta_c<=900 else '✗'}")
print(f"  UNPACK + DETECT combined:    {unpack_cells+touch_detect_c}c  {'✓' if unpack_cells+touch_detect_c<=900 else '✗'}")

