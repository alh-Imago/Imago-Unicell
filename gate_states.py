"""
gate_states.py — Command latch constants, topology values, and operation tables.

Ground truth: fpga/verilog/unicell.v (silicon-validated, iCEBreaker 2026-05-17).
See also: docs/CELL_INTERNALS.md (authoritative reference).

The cmd_latch is a single 32-bit word that defines a cell completely.
Load it via CMD_RECONFIGURE and the cell is live.

cmd_latch bit layout (confirmed on silicon):
  bits  9-0:   topology      — NOR gate wiring, one-hot (10 bits)
  bit   10:    edge_mode     — 0=STANDARD/LATCH (two-arrival), 1=EDGE cell
  bits 21-11:  auth_mask     — write-only security token (11 bits)
                               Never in Python gate_state word — zeroed on ICM save
  bit   22:    start_flag    — 1 = armed (set by CMD_RECONFIGURE completion)
  bits 24-23:  dtype         — output data type (2 bits)
                               00=NUMERIC  01=SIGNED  10=ALPHA  11=DATETIME
  bits 26-25:  cell_type     — cell behaviour variant (2 bits)
                               00=standard  01=latch  10=posedge  11=negedge
  bit   27:    priority      — schedule this cell first each tick
  bit   28:    trace         — record every fire to Ward trace buffer
  bit   29:    breakpoint    — halt array on fire (Ward breakpoint)
  bit   30:    one_shot      — fire once then disarm (clears start_flag)
  bit   31:    loop_back     — feed computed output back as next a_data

Two-arrival model (default for all cells):
  First arrival at input_address  -> stored in a_data latch, no output
  Second arrival at input_address -> fires gate tree on a_data, output emitted
  NOT(A) = NOR(A,A): send A twice to same address (Y-formation in compiler)
  latch_in (cell_type=latch): a_arrived stays set -- single arrival fires (memory/counter)
  edge_mode=1: fires on 0->1 or 1->0 transition (single arrival)

Retired from previous layout (do not use):
  bit 9:   GS_SELECT      -- SELECT cell retired (branch design pending)
  bit 10:  LOOP_MODE      -- replaced by loop_back (bit 31) + latch cell_type
  bit 11:  GS_LATCH       -- replaced by cell_type=latch (bits 25-26)
  bit 12:  GS_ONE_SHOT    -- moved to bit 30
  bit 13:  GS_INVERT_OUT  -- moved to bit 25 (negedge cell_type implies invert)
  bit 14:  GS_BROADCAST   -- not in Verilog, retired
  bit 15:  GS_SYNC_WAIT   -- retired as explicit flag; two-arrival is default
  bit 16:  GS_LOOP_BACK   -- simplified; moved to bit 31 (no src/dst selectors)
  bits 17-22: loopback src/dst + addr_latch -- retired (64-bit address retired)
  bit 24:  GS_FALL_EDGE   -- internal to Verilog (odd_phase), not a cell flag
  bit 26:  GS_OUT_POSEDGE -- internal to Verilog (odd_phase drain), not a cell flag
  bits 27-28: old GS_TYPE -- shifted to bits 23-24
  bit 29:  old GS_PRIORITY -- shifted to bit 27
  bit 30:  old GS_TRACE   -- shifted to bit 28
  bit 31:  old GS_BREAKPOINT -- shifted to bit 29
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


# ── bits 21-11: auth_mask ─────────────────────────────────────────────────────
# 11-bit card-wide security token. WRITE-ONLY in hardware.
# Always zeroed in Python cmd_latch words and in ICM files.
# CommandInterface holds the token and inserts it into cmd_bus[14:4].

AUTH_MASK_SHIFT = 11
AUTH_MASK_BITS  = 0x7FF
AUTH_MASK_FIELD = AUTH_MASK_BITS << AUTH_MASK_SHIFT   # 0x003FF800


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


# ── bits 26-25: cell_type ─────────────────────────────────────────────────────
# Selects cell behaviour. Decoded once at CMD_RECONFIGURE -- static.

GS_CTYPE_SHIFT    = 25
GS_CTYPE_MASK     = 0b11 << GS_CTYPE_SHIFT   # 0x06000000

GS_CTYPE_STANDARD = 0b00 << GS_CTYPE_SHIFT   # 0x00000000 -- fires and disarms
GS_CTYPE_LATCH    = 0b01 << GS_CTYPE_SHIFT   # 0x02000000 -- latch_in: re-emits
GS_CTYPE_POSEDGE  = 0b10 << GS_CTYPE_SHIFT   # 0x04000000 -- edge, rising
GS_CTYPE_NEGEDGE  = 0b11 << GS_CTYPE_SHIFT   # 0x06000000 -- edge, falling

def gs_ctype(cmd_latch: int) -> int:
    """Return the cell_type field (0-3) from a cmd_latch word."""
    return (cmd_latch & GS_CTYPE_MASK) >> GS_CTYPE_SHIFT

# latch_in shorthand -- single arrival fires, a_arrived stays set (memory/counter)
GS_LATCH_IN = GS_CTYPE_LATCH   # 0x02000000

# Legacy aliases for edge mode — GS_OUT_POSEDGE/NEGEDGE predated the CTYPE naming
GS_OUT_POSEDGE = GS_CTYPE_POSEDGE   # 0x04000000
GS_OUT_NEGEDGE = GS_CTYPE_NEGEDGE   # 0x06000000


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
