"""
gate_states.py — Command latch constants, topology values, and operation tables.

Ground truth: fpga/verilog/unicell.v Protocol v2.3 (silicon-validated, iCEBreaker 2026-05-30).
See also: docs/CELL_INTERNALS.md (authoritative reference).

The cmd_latch is a single 32-bit word that defines a cell completely.
Load it via CMD_RECONFIGURE and the cell is live.

IMPORTANT DISTINCTION:
  cmd_latch  — cell's INTERNAL state register (what this file describes)
  cmd_bus    — 32-bit command word sent to the cell (separate concept)
  These are two different things. The constants here describe cmd_latch bits.

cmd_latch bit layout (confirmed on silicon, v2.3):
  bits  9-0:   topology      — NOR gate wiring, one-hot (10 bits)
  bit   10:    edge_mode     — 0=STANDARD (two-arrival), 1=EDGE (transition)
  bits 18-11:  auth_mask     — 8-bit security token (256 tokens)
                               Write-once at boot via CMD_BOOT_COMMIT.
                               WRITE-ONLY — zeroed in ICM files and debug output.
  bit   19:    output_set    — 1=output address configured, cell may fire
  bit   20:    latch_A_dis   — 1=disable A latch (PASS(B) from any topology)
  bit   21:    latch_B_dis   — 1=disable B trigger (PASS(A) from any topology)
  bit   22:    start_flag    — 1=armed (set by CMD_RECONFIGURE/CMD_RELEASE)
  bits 24-23:  dtype         — output data type (2 bits)
                               00=NUMERIC  01=SIGNED  10=ALPHA  11=DATETIME
  bit   25:    invert_out    — invert computed output at drain time
                               (in EDGE mode: selects negedge detection)
  bit   26:    latch_in      — hold a_arrived after firing, single arrival fires
                               requires ENABLE_LATCH_IN=1 at synthesis
  bit   27:    priority      — schedule first each tick
  bit   28:    trace         — log every fire to Ward trace buffer
  bit   29:    breakpoint    — halt array on fire
  bit   30:    one_shot      — fire once then disarm (clears start_flag)
  bit   31:    loop_back     — feed computed output back as next a_data

cmd_bus bit layout (v2.3 — NOT stored in cmd_latch, sent per-transaction):
  bits  7-0:   opcode        — 8-bit operation code
  bit   8:     gate_enable   — 1=filter by gate_set, 0=broadcast
  bits 16-9:   gate_set      — 8-bit group select tag
  bits 18-17:  preload_sel   — transient: 01=load 0x00000000, 10=load 0xFFFFFFFF
  bits 20-19:  shift_sel     — bit19=shift_in_en, bit20=shift_out_en
  bits 28-21:  auth_token    — 8-bit token matched against stored auth_mask
  bits 31-29:  spare

Two-arrival model (default for all cells):
  First arrival at input_address  -> stored in a_data latch, no output
  Second arrival at input_address -> fires gate tree on (a_data, bus_data)
  NOT(A) = NOR(A,A): send A twice to same address (Y-formation in compiler)
  latch_in (bit 26): a_arrived stays set — single arrival fires (memory/counter)
  edge_mode (bit 10): fires on 0->1 or 1->0 transition (single arrival)
"""

# ── NOR topology constants (bits 9-0) ─────────────────────────────────────────
# One-hot: bit N set = gate N active (NOR), bit N clear = gate N bypasses (PASS).
# All single-input ops use NOR(A,A) -- same value arrives twice via Y-formation.
# Two-input ops: A stored on first arrival, B is trigger value on second.
# Topology confirmed against gate tree in unicell.v:
#   g0 = NOR(a,a) = NOT(A)
#   g1 = NOR(b,b) = NOT(B)
#   g2 = NOR(g0,g1) = AND(A,B)
#   g3 = NOR(g2,b)
#   g4 = NOR(g2,a)
#   g5 = NOR(g3,g4)
#   g6 = NOR(g5,b)
#   g7 = NOR(g6,g5)
#   g8 = NOR(g7,0)

GS_PASS  = 0b0000000000   # 0x000 -- all gates bypassed: output = A (first arrival)
GS_NOT   = 0b0000000001   # 0x001 -- g0 active: NOT(A) = NOR(A,A)
GS_NOR   = 0b0000000100   # 0x004 -- g2 active: NOR(A,B)
GS_AND   = 0b0000000111   # 0x007 -- g0+g1+g2: AND(A,B)
GS_OR    = 0b0000100100   # 0x024 -- OR(A,B)
GS_NAND  = 0b0000100111   # 0x027 -- NAND(A,B)
GS_XOR   = 0b0010111100   # 0x0BC -- XOR(A,B)
GS_XNOR  = 0b0000111100   # 0x03C -- XNOR(A,B): 1 if A==B
GS_ZERO  = 0b0000110000   # always 0
GS_ONE   = 0b0010110000   # always 1

# Aliases -- legacy compiler code using _V2 suffix still works
GS_AND_V2  = GS_AND
GS_OR_V2   = GS_OR
GS_NOR_V2  = GS_NOR
GS_NAND_V2 = GS_NAND
GS_XOR_V2  = GS_XOR
GS_XNOR_V2 = GS_XNOR
GS_ZERO_V2 = GS_ZERO
GS_ONE_V2  = GS_ONE

# GS_SYNC_WAIT: retired flag — two-arrival is now the default behaviour.
# Kept as zero-value alias for backward compatibility with existing code.
GS_SYNC_WAIT = 0   # no-op: two-arrival is default, this flag is unused

# Retired constants — kept as aliases to prevent ImportError in legacy code
GS_SELECT  = 0   # SELECT cell retired — branch design pending
LOOP_MODE  = 1 << 31   # = GS_LOOP_BACK — alias, defined again below after GS_LOOP_BACK

# GS_PASS: output = A (first arrival value, stored in a_data)
# GS_PASS_B: output = B (second arrival value -- the trigger)
GS_PASS_B    = 0b0000101100   # output = B
GS_PASS_A_V2 = GS_PASS_B     # legacy alias (labelling was historically swapped)
GS_PASS_B_V2 = GS_PASS       # legacy alias

# NOT of a specific input
GS_NOT_A   = GS_NOT           # NOT(A): g0 active, NOT(first arrival)
GS_NOT_B   = 0b0000000010     # NOT(B): g1 active, NOT(second arrival)
GS_NOT_A_V2 = GS_NOT_A
GS_NOT_B_V2 = GS_NOT_B

TOPO_MASK = 0x3FF   # bits 9-0 -- isolate topology from control bits

def gs_topology(cmd_latch: int) -> int:
    """Extract the 10-bit topology field from a cmd_latch word."""
    return cmd_latch & TOPO_MASK


# ── bit 10: edge_mode ─────────────────────────────────────────────────────────
# 0 = STANDARD/LATCH -- two-arrival model (default for all cells)
# 1 = EDGE -- fires on data transition (single arrival)
#     posedge (cell_type=10): fires on 0->1 transition
#     negedge (cell_type=11): fires on 1->0 transition

GS_EDGE_MODE = 1 << 10   # 0x00000400


# ── bits 18-11: auth_mask ─────────────────────────────────────────────────────
# 8-bit security token. Set at boot via CMD_BOOT_COMMIT or CMD_RECONFIGURE.
# WRITE-ONLY in hardware. Always zeroed in Python cmd_latch words and ICM files.
# cmd_bus[28:21] carries the auth_token per transaction (matched against this).

AUTH_MASK_SHIFT = 11
AUTH_MASK_BITS  = 0xFF          # 8 bits (256 tokens)
AUTH_MASK_FIELD = AUTH_MASK_BITS << AUTH_MASK_SHIFT   # 0x0007F800


# ── bit 22: start_flag ────────────────────────────────────────────────────────
# Set by CMD_RECONFIGURE completion. Cleared by CMD_FREEZE or one_shot disarm.
# In Python VM: controlled as cell.start_flag -- not packed into cmd_latch word.

GS_START_FLAG = 1 << 22   # 0x00400000  (reference only)


# ── bits 24-23: dtype ─────────────────────────────────────────────────────────
# Output data type -- metadata for Ward, bridge, compiler.
# Gate tree behaviour unchanged regardless of dtype.

GS_DTYPE_SHIFT    = 23
GS_DTYPE_MASK     = 0b11 << GS_DTYPE_SHIFT   # 0x01800000

GS_DTYPE_NUMERIC  = 0b00 << GS_DTYPE_SHIFT   # 0x00000000 -- unsigned int (default)
GS_DTYPE_SIGNED   = 0b01 << GS_DTYPE_SHIFT   # 0x00800000 -- two's complement signed
GS_DTYPE_ALPHA    = 0b10 << GS_DTYPE_SHIFT   # 0x01000000 -- 8-bit character
GS_DTYPE_DATETIME = 0b11 << GS_DTYPE_SHIFT   # 0x01800000 -- Unix timestamp

def gs_dtype(cmd_latch: int) -> int:
    """Return the dtype field (0-3) from a cmd_latch word."""
    return (cmd_latch & GS_DTYPE_MASK) >> GS_DTYPE_SHIFT

GS_DTYPE_NAMES = {
    GS_DTYPE_NUMERIC:  "numeric",
    GS_DTYPE_SIGNED:   "signed",
    GS_DTYPE_ALPHA:    "alpha",
    GS_DTYPE_DATETIME: "datetime",
}

# Legacy aliases -- old GS_TYPE_* names still resolve correctly
GS_TYPE_SHIFT    = GS_DTYPE_SHIFT
GS_TYPE_MASK     = GS_DTYPE_MASK
GS_TYPE_NUMERIC  = GS_DTYPE_NUMERIC
GS_TYPE_SIGNED   = GS_DTYPE_SIGNED
GS_TYPE_ALPHA    = GS_DTYPE_ALPHA
GS_TYPE_DATETIME = GS_DTYPE_DATETIME
GS_TYPE_NAMES    = GS_DTYPE_NAMES

def gs_type(cmd_latch: int) -> int:
    """Return the dtype field (0-3). Alias for gs_dtype()."""
    return gs_dtype(cmd_latch)


# ── bit 25: invert_out ───────────────────────────────────────────────────────
# Invert computed output at drain time (not on data path — no timing impact).
# In EDGE mode: selects negedge detection (invert_out=1 → fires on 1→0 transition).

GS_INVERT_OUT_BIT = 1 << 25   # 0x02000000


# ── bit 26: latch_in ─────────────────────────────────────────────────────────
# Hold a_arrived set after firing — single arrival fires on next tick.
# Used for memory cells, counters, relay chains.
# Requires ENABLE_LATCH_IN=1 at synthesis (compiled out on iCEBreaker).

GS_LATCH_IN = 1 << 26   # 0x04000000
GS_LATCH    = GS_LATCH_IN   # alias

# Legacy cell_type aliases — the old 2-bit ctype field (bits 26:25) was
# a misread of the Verilog. The correct layout is two separate bits:
#   bit 25 = invert_out  (was incorrectly called ctype bit 0)
#   bit 26 = latch_in    (was incorrectly called ctype bit 1)
# These aliases preserve old code but map to the correct single bits.
GS_CTYPE_SHIFT    = 25
GS_CTYPE_MASK     = 0b11 << GS_CTYPE_SHIFT   # 0x06000000
GS_CTYPE_STANDARD = 0b00 << GS_CTYPE_SHIFT   # 0x00000000 — normal cell
GS_CTYPE_LATCH    = GS_LATCH_IN              # 0x04000000 — latch_in set
GS_CTYPE_POSEDGE  = 0b00 << GS_CTYPE_SHIFT   # posedge = edge_mode=1, invert_out=0
GS_CTYPE_NEGEDGE  = GS_INVERT_OUT_BIT        # negedge = edge_mode=1, invert_out=1
# NOTE: POSEDGE/NEGEDGE also require GS_EDGE_MODE (bit 10) to be set.

def gs_ctype(cmd_latch: int) -> int:
    """Return latch_in (bit 26) and invert_out (bit 25) as a 2-bit field.
    Bit 1 = latch_in, bit 0 = invert_out."""
    return (cmd_latch >> 25) & 0b11


# ── bits 27-29: scheduling and debug ─────────────────────────────────────────

GS_PRIORITY   = 1 << 27   # 0x08000000 -- schedule first each tick
GS_TRACE      = 1 << 28   # 0x10000000 -- record every fire to Ward trace
GS_BREAKPOINT = 1 << 29   # 0x20000000 -- halt array on fire


# ── bit 30: one_shot ─────────────────────────────────────────────────────────

GS_ONE_SHOT = 1 << 30   # 0x40000000 -- fire once then disarm permanently


# ── bit 31: loop_back ────────────────────────────────────────────────────────

GS_LOOP_BACK = 1 << 31   # 0x80000000 -- feed output back as next a_data


# ── Masks ─────────────────────────────────────────────────────────────────────

GS_FULL_MASK   = 0xFFFFFFFF
GS_LEGACY_MASK = 0x3FF        # original 10-bit topology only
GS_CONFIG_MASK = 0xFFC007FF   # all bits except auth_mask (bits 21-11 zeroed)
                               # use when saving cmd_latch to ICM or debug output


# ── Composite cell configurations ─────────────────────────────────────────────

# STORAGE: PASS topology + latch cell_type
# Single arrival fires (latch_in=1). Input -> gate tree -> stored -> re-emits every tick.
GS_STORAGE = GS_PASS | GS_LATCH_IN   # 0x02000000

# LOOP MEMORY: any topology + latch_in + loop_back
# Gate tree runs on trigger -> result stored -> fed back as next a_data.
GS_LOOP_MEM = GS_LATCH_IN | GS_LOOP_BACK   # 0x82000000

# COUNTER: PASS + latch_in + loop_back (specialisation of LOOP_MEM)
GS_COUNTER = GS_PASS | GS_LATCH_IN | GS_LOOP_BACK   # 0x82000000

# SENTRY: watches tile input, re-emits to PTT bus address every tick.
# PASS topology + latch_in. Emitted by compiler automatically -- never user-visible.
GS_SENTRY = GS_PASS | GS_LATCH_IN   # 0x02000000


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


# ── Operation table ───────────────────────────────────────────────────────────
# Maps operation name -> (topology_bits, num_inputs).
# Two-arrival is default -- no flag needed. Compiler emits Y-formation routing.

OPERATION_TABLE: dict = {
    "PASS":  (GS_PASS,  1),
    "NOT":   (GS_NOT,   1),
    "NOR":   (GS_NOR,   2),
    "AND":   (GS_AND,   2),
    "OR":    (GS_OR,    2),
    "NAND":  (GS_NAND,  2),
    "XOR":   (GS_XOR,   2),
    "XNOR":  (GS_XNOR,  2),
}

# ── Backward-compatibility aliases ───────────────────────────────────────────
# Names retired in v2 — kept here so old tests import without error.
# Do not use in new code.
GS_INVERT_OUT   = GS_INVERT_OUT_BIT  # was bit 13, now bit 25
GS_OUT_POSEDGE  = GS_CTYPE_POSEDGE   # renamed
GS_OUT_NEGEDGE  = GS_CTYPE_NEGEDGE   # renamed

# GS_FALL_EDGE: negedge edge detection.
# In v2.3: edge_mode (bit 10) + invert_out (bit 25).
# GS_CTYPE_NEGEDGE is the combined alias (= GS_INVERT_OUT_BIT).
# Note: edge_mode (bit 10 = GS_EDGE_MODE) must also be set for edge detection.
# For backward compat, GS_FALL_EDGE = GS_EDGE_MODE | GS_INVERT_OUT_BIT.
GS_FALL_EDGE    = GS_EDGE_MODE | GS_INVERT_OUT_BIT   # 0x02000400
GS_SYNC_WAIT    = 0                 # retired — two-arrival is now the default
GS_SELECT       = 0                 # retired — replaced by BranchPoint
GS_LOOP_MODE    = GS_LOOP_BACK      # renamed
GS_LATCH        = GS_LATCH_IN       # renamed
GS_BROADCAST    = 0                 # retired — broadcast is now the default (no addressing)
GS_PRIORITY_OUT = GS_PRIORITY       # renamed
# Lowercase function-style aliases (older code used these)
gs_loop_back  = GS_LOOP_BACK
gs_one_shot   = GS_ONE_SHOT
gs_latch_in   = GS_LATCH_IN
gs_edge_mode  = GS_EDGE_MODE
# More backward-compat aliases
LOOP_MODE           = GS_LOOP_BACK   # old name
GS_FULL_MASK        = 0xFFFFFFFF     # mask for full gs word
GS_LEGACY_MASK      = 0x000001FF     # v1 topology bits only
LOOP_BACK_SRC_SHIFT = 0              # retired field
LOOP_BACK_DST_SHIFT = 0              # retired field
def gs_extract_loop_back(gs):        # retired helper
    return bool(gs & GS_LOOP_BACK)
