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
  bit  25:    GS_LATCH_IN   — input-side latch, re-fires on down tick if no new data
  bit  26:    GS_OUT_POSEDGE — output buffer releases on rising edge (default: falling edge)
  bits 27-28: reserved for future use
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

# ── Input latch (bit 25) ──────────────────────────────────────────────────────
# When set, the cell maintains a latch on the INPUT side rather than (or as
# well as) the output side.
#
# Behaviour:
#   Rising edge:  new data arrives on bus at input_address
#                 -> store in input latch
#                 -> evaluate using new data
#                 -> output result on rising edge (normal)
#
#   Falling edge: if new data arrived this tick -> already handled above
#                 if NO new data arrived this tick
#                 -> evaluate using latched input value
#                 -> output result on falling edge
#                 -> cell effectively re-fires with last known input
#
# This enables the single-cell counter pattern:
#   gate_state     = GS_PASS | LOOP_MODE | GS_LATCH_IN
#   input_address  = own output address (LOOP_MODE feedback)
#   output_address = wherever count is needed
#
#   Each tick: if new data arrives it replaces the latched value.
#              if no new data, the latched value re-fires on the down tick.
#              LOOP_MODE keeps the cell armed continuously.
#              The latched value IS the running state — no external counter needed.
#
# Also fixes the cell-to-cell timing model:
#   Without GS_LATCH_IN: cell fires only when bus data arrives (tick dependent)
#   With GS_LATCH_IN:    cell fires on up tick if data arrives,
#                        fires on down tick if no data (using last known input)
#   This gives every cell a stable one-tick input memory, removing the need
#   for pad cells in some depth-matching scenarios.
#
# Compatible with GS_LATCH (output side) — both can be set simultaneously:
#   GS_LATCH_IN | GS_LATCH = latch both input and output
#   Useful for cells that need to hold state in both directions.
#
# NEVER set on bridge cells (GS_ADDR_LATCH). Bridge cells use the command
# bus protocol, not the data bus latch mechanism.
# Bits 27-28 remain reserved for future use.
#
GS_LATCH_IN = 1 << 25   # 0x02000000 — input-side latch, re-fires on down tick if no data

# ── Output buffer release edge (bit 26) ───────────────────────────────────────
# UniCell-edge model: the cell always computes on the falling edge (when B
# arrives). The result is held in an output buffer and released to the bus
# at a configurable edge in the NEXT clock cycle.
#
# Default (bit clear): output buffer releases on FALLING edge of cycle N+1.
#   negedge N:   B arrives, gate tree fires, result latched into output_buf
#   negedge N+1: output_buf drives bus → downstream A or B as configured
#
#   Use when the downstream cell expects input on its negedge (B path), or
#   when minimum inter-cell latency is acceptable and routing is known short.
#
# GS_OUT_POSEDGE (bit set): output buffer releases on RISING edge of cycle N+1.
#   negedge N:   B arrives, gate tree fires, result latched into output_buf
#   posedge N+1: output_buf drives bus → downstream cell receives as A
#
#   Use when feeding the A (rising edge) input of the next cell, or when
#   a full half-cycle of settling time is needed across longer bus routing.
#   This is the standard choice for most inter-cell connections — it gives
#   the downstream cell a full half-cycle (posedge → negedge) to receive
#   A before its B arrives.
#
# The compiler selects the release edge based on what the downstream cell
# expects on its input:
#   → downstream A path: set GS_OUT_POSEDGE (output arrives at posedge N+1)
#   → downstream B path: clear GS_OUT_POSEDGE (output arrives at negedge N+1)
#
# TODO (compiler): lower_to_cell_map_v2() must set GS_OUT_POSEDGE on cells
#   whose output feeds the A input of the next cell. Cells feeding B inputs
#   leave this bit clear. Default to GS_OUT_POSEDGE for safety until the
#   compiler has per-edge routing awareness.
#
GS_OUT_POSEDGE = 1 << 26   # 0x04000000 — output buffer releases on rising edge

# Convenience: counter cell — input latch + loop mode + pass through
# Cell holds running state via input latch, stays armed via LOOP_MODE,
# re-evaluates each tick. Configure input_address = own output_address.
GS_COUNTER = GS_LATCH_IN | LOOP_MODE | GS_PASS   # 0x02000400

# Convenience: loop_back with default routing (G8 → G0)
GS_LOOP_BACK_DEFAULT = GS_LOOP_BACK  # src=0 (G0 as dst), src bits=0 means G8 by convention

# Convenience: sentry/watcher cell — one per tile, emitted by compiler
# Watches tile input address, ticks PTT bus address every cycle while active.
# GS_LATCH holds the last value. LOOP_MODE keeps the cell armed after firing.
# GS_PASS passes input through unchanged — the value written to PTT encodes state.
# Never user-visible — emitted automatically by the compiler.
GS_SENTRY = GS_LATCH | LOOP_MODE | GS_PASS   # 0x000C00

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

# ── v2 single-cell gate states (verified by truth table) ─────────────────────
# These use the full two-input tree (A=rising edge, B=falling edge).
# GS_SYNC_WAIT (bit 15): cell waits for both A and B before firing.
# All binary ops are now single cells -- no multi-cell chains needed.

GS_SYNC_WAIT  = 1 << 15   # 0x00008000 -- wait for both A and B

# Two-input single-cell gate states (require GS_SYNC_WAIT for two inputs)
GS_AND_V2     = 0b000000111  # AND(A, B)
GS_OR_V2      = 0b000100100  # OR(A, B)
GS_NOR_V2     = 0b000000100  # NOR(A, B)
GS_NAND_V2    = 0b000100111  # NAND(A, B)
GS_XOR_V2     = 0b010111100  # XOR(A, B)
GS_XNOR_V2   = 0b000111100  # XNOR(A, B) -- 1 if A==B
GS_NOT_A_V2   = 0b000001110  # NOT(A) -- two-input mode
GS_NOT_B_V2   = 0b000000001  # NOT(B) -- two-input mode
# NOTE: the naming below reflects actual gate tree behaviour (verified by truth table).
# GS_PASS_A_V2 passes B (not A) — the 1-bit trace through the tree gives output=B.
# GS_PASS_B_V2 passes A (not B) — output=A. The names in the original spec were swapped.
# GS_PASS_B_V2=0 (all gates bypass) produces g0=a_in, and the final output is a_in=A.
# GS_PASS_A_V2=0b101100 produces output=B through the activated gate path.
# The constants are correct as coded — only the labels were misleading.
GS_PASS_A_V2  = 0b000101100  # actual output: B  (labelling preserved for compatibility)
GS_PASS_B_V2  = 0b000000000  # actual output: A  (labelling preserved for compatibility)
GS_ZERO_V2    = 0b000110000  # always 0
GS_ONE_V2     = 0b010110000  # always 1
