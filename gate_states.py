"""
gate_states.py — Gate state constants and operation tables.

Gate state register: 32 bits (extended from original 11 bits).

Layout:
  bits 0-8:   NOR gate topology — one bit per gate, set = active NOR, clear = bypass
  bit 9:      GS_SELECT — conditional router sentinel (not a NOR computation)
  bit 10:     LOOP_MODE — cell does not clear start_flag after firing
  bit 11:     GS_LATCH  — latch mode: register holds data value, re-emits each tick
  bit 12:     GS_ONE_SHOT — fire exactly once then lock (start_flag cleared, never re-armed)
  bit 13:     GS_INVERT_OUT — flip output bit after gate computation (free NOT on result)
  bit 14:     GS_BROADCAST — send result to ALL cells watching output_address (wired fan-out)
  bit 15:     GS_SYNC_WAIT — hold until two input packets have arrived before firing
  bit 16:     GS_LOOP_BACK — enable internal feedback: G8 output feeds back to G0 input
  bits 17-19: LOOP_BACK_SRC — source gate for loopback (0-8)
  bits 20-22: LOOP_BACK_DST — destination gate input for loopback (0-8)
  bit  23:    GS_ADDR_LATCH — extended 64-bit address latch (bridge cells only)
  bit  24:    GS_FALL_EDGE  — assert output on falling clock edge (default: rising)
  bits 25-28: reserved for future use
  bit 29:     GS_PRIORITY — this cell jumps the segment emission queue
  bit 30:     GS_TRACE — log every firing to the debug buffer
  bit 31:     GS_BREAKPOINT — halt the array when this cell fires (debug freeze)

SELECT gate state:
  GS_SELECT is a sentinel (bit 9, outside the 9-bit NOR topology).
  A SELECT cell does not transform its value through the NOR gates.
  It reads the incoming value as a 1-bit condition and routes to one of
  two output addresses:
    condition == 1  →  output_address      (true branch)
    condition == 0  →  output_address_alt  (false branch)
  The value is passed unchanged to whichever address is chosen.

LOOP_MODE (bit 10):
  OR with any gate state: e.g. GS_PASS | LOOP_MODE, GS_SELECT | LOOP_MODE.
  When set, start_flag is NOT cleared after the cell fires. The cell
  re-evaluates every time its input_address carries new data.

GS_LATCH (bit 11):
  The 32-bit gate_state register itself holds the data value when in latch mode.
  The cell retains the last computed result and re-emits it every tick while
  start_flag is asserted. Updates when new data arrives on input_address.
  Replaces the old software-only storage_mode flag with a proper silicon model.

GS_SYNC_WAIT (bit 15):
  Cell holds until two distinct input packets have arrived on input_address
  before firing. Eliminates depth-equalisation PASS chains — cells can wait
  for the slower of two paths to arrive rather than padding the faster one.

GS_LOOP_BACK (bit 16):
  Enables internal feedback path: the G8 output is routed back to the G0
  input within the same cell. Creates an SR latch or ring oscillator in a
  single cell without external bus feedback wiring.
  LOOP_BACK_SRC (bits 17-19) and LOOP_BACK_DST (bits 20-22) select which
  gate output feeds back to which gate input (default: G8 → G0).
"""

# ── NOR topology constants ────────────────────────────────────────────────────

GS_PASS   = 0b000000000   # all gates bypassed — pass input through unchanged
GS_NOT    = 0b000000001   # gate 0 active — NOT(A) = NOR(A,A)
GS_NOR    = 0b000000100   # gate 2 active — NOR(g1,g2)

# ── Control flags (bits 9-10, unchanged from original) ───────────────────────

GS_SELECT = 1 << 9    # 0x200 — conditional router, not NOR computation
LOOP_MODE = 1 << 10   # 0x400 — cell stays armed after firing

# ── New mode flags (bits 11-31) ───────────────────────────────────────────────

GS_LATCH      = 1 << 11   # 0x000800 — latch mode: register holds + re-emits data
GS_ONE_SHOT   = 1 << 12   # 0x001000 — fire once then lock permanently
GS_INVERT_OUT = 1 << 13   # 0x002000 — invert output after gate computation
GS_BROADCAST  = 1 << 14   # 0x004000 — fan out to all cells at output_address
GS_SYNC_WAIT  = 1 << 15   # 0x008000 — wait for two inputs before firing
GS_LOOP_BACK  = 1 << 16   # 0x010000 — enable internal G8→G0 feedback

# Loopback source and destination gate selectors (3 bits each)
LOOP_BACK_SRC_SHIFT = 17
LOOP_BACK_DST_SHIFT = 20
LOOP_BACK_SRC_MASK  = 0b111 << LOOP_BACK_SRC_SHIFT   # bits 17-19
LOOP_BACK_DST_MASK  = 0b111 << LOOP_BACK_DST_SHIFT   # bits 20-22

# Debug flags
GS_PRIORITY   = 1 << 29   # 0x20000000 — jump segment emission queue
GS_TRACE      = 1 << 30   # 0x40000000 — log every firing to debug buffer
GS_BREAKPOINT = 1 << 31   # 0x80000000 — halt array when this cell fires

# ── Extended address latch (bit 23) ──────────────────────────────────────────
# When GS_ADDR_LATCH is set the cell acts as a 64-bit address latch.
# The data register holds the UPPER 32 bits of the forwarding address.
# The output_address register holds the LOWER 32 bits (as always).
# Together: full_address = (data_register << 32) | output_address
#
# The cell DATA BUS is 32-bit unchanged. Cells still fire on 32-bit addresses.
# GS_ADDR_LATCH only affects the COMMAND BUS routing layer.
# ONLY ever set on bridge cells by CommandInterface (OS layer).
# NEVER set on compute cells. NEVER emitted by the compiler.
#
# Relocation via Command 3 (auth required):
#   Write new lower address → output_address register  (Command 2)
#   Write new upper address → data register            (Command 0)
#   Bridge transparently forwards to new 64-bit address.
#   All cells pointing at this bridge need no changes.
#
GS_ADDR_LATCH = 1 << 23   # 0x00800000 — extended address latch mode

# ── Edge selection (bit 24) ───────────────────────────────────────────────────
# Controls which clock edge the cell asserts its output on.
#
# Default (bit clear): cell asserts output on the RISING edge.
# GS_FALL_EDGE (bit set): cell asserts output on the FALLING edge.
#
# This eliminates bus collisions when two values arrive at the same address
# in the same clock cycle without requiring PASS pad cells:
#
#   Cell output  → always rising edge  (it fired, data is on its way)
#   Table value  → always falling edge (scheduled injection, arrives after
#                                       cell outputs have settled)
#
# For cell-to-cell trees where two cell outputs target the same address,
# the compiler assigns one GS_FALL_EDGE to separate them within the cycle.
# The compiler chooses edge assignment based on program structure:
#   - Table/literal values:  GS_FALL_EDGE set   (falling)
#   - Cell output values:    GS_FALL_EDGE clear  (rising, default)
#   - Cell-to-cell conflict: compiler resolves by assigning one cell
#                            GS_FALL_EDGE; flagged in compile output.
#
# The half-cycle window at 12MHz is ~41ns — sufficient for iCE40 routing.
# GS_LATCH must be set on the sending cell for the held value to be stable
# across the full cycle. The two flags work together:
#   GS_LATCH      — hold output value so it is readable at both edges
#   GS_FALL_EDGE  — assert on falling edge to avoid rising-edge collision
#
# NEVER set on bridge cells (GS_ADDR_LATCH cells). Bridge cells use the
# command bus, not the data bus edge protocol.
# Set by the compiler only — not a user-visible primitive.
#
GS_FALL_EDGE  = 1 << 24   # 0x01000000 — assert output on falling clock edge

# Convenience: combined latch + fall edge for table-injected values
GS_TABLE_VAL  = GS_LATCH | GS_FALL_EDGE   # stable held value on falling edge

# Convenience: loop_back with default routing (G8 → G0)
GS_LOOP_BACK_DEFAULT = GS_LOOP_BACK  # src=0 (G0 as dst), src bits=0 means G8 by convention

# Mask covering all valid gate_state bits
GS_FULL_MASK = 0xFFFFFFFF

# Mask covering original 11-bit field (for migration / version detection)
GS_LEGACY_MASK = 0x7FF

# ── Composite gate state helpers ──────────────────────────────────────────────

def gs_loop_back(src_gate: int = 8, dst_gate: int = 0) -> int:
    """Build a GS_LOOP_BACK value with specific src/dst gate indices (0-8)."""
    return (GS_LOOP_BACK
            | ((src_gate & 0b111) << LOOP_BACK_SRC_SHIFT)
            | ((dst_gate & 0b111) << LOOP_BACK_DST_SHIFT))

def gs_extract_loop_back(gate_state: int) -> tuple:
    """Extract (src_gate, dst_gate) from a gate_state with GS_LOOP_BACK set."""
    src = (gate_state & LOOP_BACK_SRC_MASK) >> LOOP_BACK_SRC_SHIFT
    dst = (gate_state & LOOP_BACK_DST_MASK) >> LOOP_BACK_DST_SHIFT
    return src, dst

# ── Composite op markers (multi-cell, not single gate states) ─────────────────

GS_AND  = "AND"    # composite — NOR(NOT A, NOT B)
GS_OR   = "OR"     # composite — NOT(NOR(A, B))
GS_XOR  = "XOR"    # composite — NOR(NOR(A,¬B), NOR(¬A,B))
GS_NAND = "NAND"   # composite — NOT(AND)
GS_XNOR = "XNOR"   # composite — NOT(XOR)

# ── Operation table ───────────────────────────────────────────────────────────
# Maps operation name -> (gate_state_or_marker, num_inputs)

OPERATION_TABLE: dict = {
    "PASS":  (GS_PASS, 1),
    "NOT":   (GS_NOT,  1),
    "NOR":   ("NOR",   2),
    "OR":    ("OR",    2),
    "AND":   ("AND",   2),
    "NAND":  ("NAND",  2),
    "XOR":   ("XOR",   2),
    "XNOR":  ("XNOR",  2),
}

# ── Compiler operator maps ────────────────────────────────────────────────────

BINOP_MAP: dict = {
    "BitAnd": "AND",
    "BitOr":  "OR",
    "BitXor": "XOR",
    "And":    "AND",
    "Or":     "OR",
}

BOOLOP_MAP: dict = {
    "And": "AND",
    "Or":  "OR",
}

UNARYOP_MAP: dict = {
    "Not":    "NOT",
    "Invert": "NOT",
}

COMPARE_MAP: dict = {
    "Eq":    "XNOR",
    "NotEq": "XOR",
}
