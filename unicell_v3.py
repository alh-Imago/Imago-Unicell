"""
unicell_v3.py — UniCell VM, Phase 1 of the v3.1 rebuild (2026-07-31).

Ground truth: fpga/verilog/unicell64_v3.v (protocol v3.1, points.md through
#66). This REPLACES unicell.py as the cell model going forward — that file
matches a retired, pre-v3 architecture (single 32-bit cmd_latch, no
address-lane split, no methodology/routing latches) and is kept only as
historical reference until every dependent (unicell_array.py, controller.py,
compiler.py, tests) is migrated across the full phase plan below.

PHASING (Alan, 2026-07-31 — "design the cell correctly, then scale up"):
  Phase 1 (THIS FILE): topology latch [31:0] + foundational two-arrival
    mechanics + boot/auth/addressing (load-bearing for every later phase,
    not deferrable) + the core opcodes.
  Phase 2 (not yet built): methodology latch [63:32] — nibble mask, shift,
    lane cut. auth_mask's STORAGE lives in this bit range too, but auth
    itself is foundational and IS built here (see below).
  Phase 3 (not yet built): routing latch [95:64] — routing_mask,
    cardinal_edge, the comparator, dynamic_route_en, the three patterns.
  Phase 4 (not yet built): targeted opcodes — SET_TARGET/config_match-based
    per-cell addressing (CMD_LOAD_AT, CMD_SET_ROUTE_LATCH_AT, CMD_FREEZE_AT/
    CMD_RELEASE_AT).
  Phase 5 (not yet built): command-emit (is_command_cell), targeted
    emission (points.md #66), CMD_LOAD_DONE's dual-bus confirm (#63).
  Phase 6 (not yet built): array-level semantics — wired-OR collision/
    composition (#32), masked distributed command assembly (#60), the
    four-role SENDER/TARGET/WATCHER/COUNTER loader.

Why auth/boot/addressing is IN Phase 1 despite auth_mask's bits technically
living in what's labelled the "methodology latch" range ([63:53]): nothing
in the cell — no config opcode, no fire — works without knowing whether the
cell is booted and authenticated. It's load-bearing state, not a deferrable
computational modifier (unlike nibble_mask/shift/lane_cut, which genuinely
are Phase 2 and don't affect whether ANY of this works).

cmd_latch is stored as a single 128-bit Python int from the start (the full
eventual width is already known), but Phase 1 only reads/writes the fields
documented below — the topology latch [31:0], plus auth_mask [63:53] which
is foundational. Everything else in [63:32]/[95:64]/[127:96] stays zero
until its phase.

── Topology latch (cmd_latch[31:0]) — verified against unicell64_v3.v
   2026-07-30 (points.md #49/#51), re-verified against the LOGIC (not just
   the header comment) while building this file:
  [9:0]   topology      — NOR-gate-tree selector (see TOPOLOGY_TABLE below)
  [10]    is_command_cell — Phase 5. Stored/settable here for field-map
          fidelity; the actual command-emit BEHAVIOR is not implemented
          until Phase 5. A cell with this bit set will raise
          NotImplementedError on fire rather than silently do the wrong
          thing.
  [12:11] cell_mode     — reserved, unwired in the RTL too (points.md #58/59)
  [18:13] free
  [22]    start_flag    — armed; NOTE: despite older doc references,
          `output_set` is a SEPARATE register in the actual RTL (line 479),
          NOT cmd_latch[19] — the header comment in unicell64_v3.v claiming
          [19]=output_set is stale/wrong, caught by reading the logic
          directly rather than trusting the comment (same discipline this
          project has applied to the RTL itself all along). Modeled here
          as its own field, matching the real register.
  [24:23] dtype         — stored, not yet interpreted (no dtype-dependent
          behavior exists in the RTL either — it's genuinely inert today)
  [25]    invert_out    — applied at the OUTPUT only; internal state
          (data_reg, loop_back, latch_in re-arm) all see the RAW,
          non-inverted computed_output, exactly as unicell64_v3.v does
          (invert_out is applied at the drain/odd_phase stage, not baked
          into computed_output itself)
  [26]    latch_in      — a_arrived stays set after fire (single-arrival
          re-fire mode); ALSO updates a_data to the new arrival's value
          each time (not just "stays armed" — the RTL updates a_data too)
  [27]    priority, [28] trace, [29] breakpoint — stored, not yet acted on
          (no scheduler/tracing exists in this VM yet; these are inert
          placeholders matching the RTL fields' own current inertness
          outside of a real scheduling environment)
  [30]    one_shot      — fires once, then start_flag clears permanently
  [31]    loop_back     — feeds computed_output back as the next a_data.
          PRECEDENCE, verified against the RTL's actual statement order
          (Verilog non-blocking assignment: last write in program order to
          the same signal wins on the same clock edge): loop_back's write
          to a_data comes AFTER latch_in's in unicell64_v3.v — so if BOTH
          are set on the same fire, loop_back's value (computed_output)
          wins over latch_in's (the raw incoming arrival). Replicated here
          exactly via ordering, not asserted from memory.

  [20]    latch_A_dis   — ACTUALLY WIRED: gates whether a first arrival
          gets stored into a_data at all (verified at RTL line ~1402).
  [21]    latch_B_dis   — DOCUMENTED but NOT ACTUALLY WIRED into any
          firing condition anywhere in unicell64_v3.v (verified by
          grepping every use of the signal — it's declared, configurable,
          but dead). Modeled here as a stored-but-inert field, matching
          the real silicon exactly rather than inventing behavior the RTL
          doesn't have. If a future RTL change wires it up, this file
          needs the matching update (and the comment above corrected).

Foundational (not "cmd_latch fields" in the strict topology-latch sense,
but load-bearing, hence Phase 1):
  CELL_ID          — permanent identity, immutable after construction
                     (baked-in, per the two-state boot/run model)
  input_address    — mutable LISTEN address (addr_match key). Defaults to
                     CELL_ID (a cell listens on its own identity until
                     explicitly re-pointed).
  output_address   — defaults to CELL_ID+1 (verified at RTL line 475)
  auth_mask        — 11-bit, defaults to 0 (auth_boot=True: unconfigured
                     cells accept CMD_BOOT_COMMIT and CMD_ARRAY_RESET
                     unconditionally; everything else needs auth_ok once
                     a real mask is stored)
  physical_mode    — 1=BOOT state, 0=RUN state
  output_set       — separate register (see note above), gates bus_hit
  frozen           — disarms bus_hit entirely when set
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Topology decode table (cmd_latch[9:0]) ────────────────────────────────────
# Verified against unicell64_v3.v lines ~724-753 (the g0..g9 NOR-decomposition
# and the case(topology) table), NOT reconstructed from memory. Every gate is
# built from repeated NOR — this is the actual thesis of the project
# ("topology is computation"), so the VM computes it the SAME way the
# silicon does rather than shortcutting with Python's native ~/&/|/^ on the
# final result. Test vectors A=0xDEADBEEF, B=0xCAFEBABE match the RTL's own
# verification comment (line 736).

TOPO_PASS_A = 0x000   # identity(A) — default/fallback
TOPO_NOT_A  = 0x001
TOPO_NOT_B  = 0x002   # real, decoded, but no dedicated preset opcode (points.md #56)
TOPO_NOR    = 0x004
TOPO_AND    = 0x007
TOPO_ZERO   = 0x030
TOPO_XNOR   = 0x03C
TOPO_OR     = 0x024
TOPO_NAND   = 0x027
TOPO_PASS_B = 0x02C
TOPO_ONE    = 0x0B0
TOPO_XOR    = 0x0BC

_MASK32 = 0xFFFFFFFF


def _gate_tree(a: int, b: int) -> dict:
    """The exact NOR-decomposition from unicell64_v3.v lines 724-733."""
    g0 = (~(a | a)) & _MASK32                    # NOT(A)
    g1 = (~(b | b)) & _MASK32                    # NOT(B)
    g2 = (~(g0 | g1)) & _MASK32                  # AND(A,B) = NOR(NOT A, NOT B)
    g3 = (~(g2 | g2)) & _MASK32                  # NAND(A,B)
    g4 = (~(a | b)) & _MASK32                    # NOR(A,B)
    g5 = (~(g4 | g4)) & _MASK32                  # OR(A,B)
    g6 = (~(a | g4)) & _MASK32                   # NOR(A, NOR(A,B))
    g7 = (~(b | g4)) & _MASK32                   # NOR(B, NOR(A,B))
    g8 = (~(g6 | g7)) & _MASK32                  # XNOR(A,B)
    g9 = (~(g8 | g8)) & _MASK32                  # XOR(A,B)
    return {"g0": g0, "g1": g1, "g2": g2, "g3": g3, "g4": g4,
            "g5": g5, "g6": g6, "g7": g7, "g8": g8, "g9": g9}


def compute_gate(topology: int, a: int, b: int) -> int:
    """
    computed_output — matches the case(topology) table at unicell64_v3.v
    lines 740-753 exactly, including its fallback-to-PASS_A default for any
    topology code not in the table (same as the RTL's `default:` arm).
    a = input_val (A, the stored/first-arrival operand)
    b = second_val (B, the live/second-arrival trigger operand)
    """
    a &= _MASK32
    b &= _MASK32
    g = _gate_tree(a, b)
    return {
        TOPO_PASS_A: a,
        TOPO_PASS_B: b,
        TOPO_NOT_A:  g["g0"],
        TOPO_NOT_B:  g["g1"],
        TOPO_NOR:    g["g4"],
        TOPO_AND:    g["g2"],
        TOPO_OR:     g["g5"],
        TOPO_NAND:   g["g3"],
        TOPO_XOR:    g["g9"],
        TOPO_XNOR:   g["g8"],
        TOPO_ZERO:   0,
        TOPO_ONE:    _MASK32,
    }.get(topology, a)  # default: fallback PASS(A), matches RTL exactly


# ── Phase 2: methodology transforms ───────────────────────────────────────────
# Verified against unicell64_v3.v lines 683-808 (the logic, not the comment).
# Both shifts are a FIXED-PATTERN MUX, not a general barrel shifter -- only
# these specific amounts are wired; anything else passes through unshifted.
# This is a real hardware cost tradeoff (a small mux vs. a full barrel
# shifter), not an arbitrary limitation, and the VM replicates it exactly
# rather than "helpfully" supporting every amount.
_SHIFT_AMOUNTS = (1, 2, 4, 8, 12, 16, 20, 24, 28)


def shift_in_left(value: int, shift_amt: int, enabled: bool) -> int:
    """bus_data_shifted (line 683-698): shift the incoming trigger LEFT by
    shift_amt bits before it reaches the gate tree, when shift_in_en=1."""
    value &= _MASK32
    if not enabled or shift_amt not in _SHIFT_AMOUNTS:
        return value
    return (value << shift_amt) & _MASK32


def shift_out_right(value: int, shift_amt: int, enabled: bool) -> int:
    """computed_shifted (line 772-785): shift the gate result RIGHT by
    shift_amt bits before emission, when shift_out_en=1. Internal state
    (data_reg, loop_back, latch_in) never sees this -- only the externally
    emitted value does, matching the RTL's out_buf_data assignment."""
    value &= _MASK32
    if not enabled or shift_amt not in _SHIFT_AMOUNTS:
        return value
    return value >> shift_amt   # zero-fill from the top, matches {N'h0, value[31:N]}


def apply_nibble_mask(value: int, nibble_mask: int, enabled: bool) -> int:
    """bus_data_masked (line 703-707): per-nibble BLOCK(1)/PASS(0) on the
    trigger operand ONLY -- verified (points.md #60 investigation, repeated
    here): the stored first-arrival value is ALWAYS written from raw
    bus_data, never masked. Masking only ever touches the B/trigger operand."""
    value &= _MASK32
    if not enabled:
        return value
    keep = 0
    for nib in range(8):
        if not ((nibble_mask >> nib) & 1):   # 0 = PASS -- keep this nibble
            keep |= 0xF << (nib * 4)
    return value & keep


def compute_lane_kill(shift_amt: int, lane_cut: int) -> int:
    """lane_kill (line 802-808): zeros the bit-window that crossed a CUT
    byte boundary (8/16/24) during a right-shift by shift_amt. All cuts 0
    (default) -> lane_kill = all-ones -> no-op, bit-identical to the plain
    out-shift (the RTL's own regression-safety property, replicated here)."""
    lane_ones = (1 << shift_amt) - 1 if shift_amt > 0 else 0
    win8  = ((lane_ones << 8)  >> shift_amt) & _MASK32 if (lane_cut & 0b001) else 0
    win16 = ((lane_ones << 16) >> shift_amt) & _MASK32 if (lane_cut & 0b010) else 0
    win24 = ((lane_ones << 24) >> shift_amt) & _MASK32 if (lane_cut & 0b100) else 0
    return (~(win8 | win16 | win24)) & _MASK32


# ── Phase 3: comparator + effective routing ───────────────────────────────────
# Verified against unicell64_v3.v lines 538-559. IMPORTANT, easy to miss: the
# comparator reads the RAW incoming value (bus_data_r), NOT the shift_in/
# nibble_mask-transformed operand used for the gate tree -- two different
# versions of "B" serve two different purposes on the same fire. Comparison
# is UNSIGNED (Verilog default on unsigned wires, which is what a_data/
# bus_data_r are -- neither declared `signed` anywhere in the RTL).
_ROUTE_MASK6 = 0x3F


def select_pattern(bus_data_raw: int, a_data: int,
                    pattern_low: int, pattern_equal: int, pattern_high: int) -> int:
    """selected_pattern (line 556-558): unsigned compare of the RAW trigger
    against the stored a_data -- HIGH/LOW/EQUAL picks one of the three
    stored 6-bit patterns."""
    bus_data_raw &= _MASK32
    a_data &= _MASK32
    if bus_data_raw > a_data:
        return pattern_high & _ROUTE_MASK6
    elif bus_data_raw < a_data:
        return pattern_low & _ROUTE_MASK6
    else:
        return pattern_equal & _ROUTE_MASK6


def compute_effective_routing(dynamic_route_en: bool, selected_pattern: int,
                               routing_mask: int) -> int:
    """effective_routing (line 563-568): per-fire WHERE. dynamic_route_en=0
    collapses to routing_mask alone (patterns bypassed) -- reproduces the
    pre-#49 static behavior exactly, zero change for any cell not opting in."""
    routing_mask &= _ROUTE_MASK6
    if not dynamic_route_en:
        return routing_mask
    return (selected_pattern & _ROUTE_MASK6) & routing_mask


def compute_transit_only(effective_routing: int, cardinal_edge: int) -> bool:
    """transit_only (line 570-571): suppress local presentation only if this
    fire is routing somewhere (effective_routing != 0) AND every direction
    it's routing to is marked cardinal-only. One active direction left
    un-marked keeps local alive even while another is a pure conduit on the
    same fire -- this is the actual capability #58 built (a single global
    bit could not express it)."""
    effective_routing &= _ROUTE_MASK6
    cardinal_edge &= _ROUTE_MASK6
    return (effective_routing != 0) and ((effective_routing & ~cardinal_edge & _ROUTE_MASK6) == 0)


# ── dtype constants (stored, not yet interpreted — see class docstring) ──────
DTYPE_NUMERIC  = 0b00
DTYPE_SIGNED   = 0b01
DTYPE_ALPHA    = 0b10
DTYPE_DATETIME = 0b11


class AuthError(RuntimeError):
    """Raised when a config operation fails auth_ok. Matches the RTL's
    silent-reject-on-mismatch behavior being made LOUD in the VM instead —
    a design choice: hardware silently drops a bad auth token (no signal
    reaches anywhere), but a VM that silently no-ops on a config call the
    test author *thought* succeeded is a worse debugging experience than
    hardware ever is. Raise here; the RTL doesn't need to."""
    pass


@dataclass
class UniCellV3:
    """
    One UniCell, v3.1 protocol, Phase 1 (topology latch + foundational
    two-arrival mechanics + boot/auth/addressing). See module docstring for
    the full phase plan and exact RTL cross-references.
    """
    CELL_ID: int

    # ── Foundational state (not cmd_latch bits in the strict sense, but
    # load-bearing — see module docstring) ──────────────────────────────────
    input_address:  int  = field(default=None)   # None -> defaults to CELL_ID in __post_init__
    output_address:  int = field(default=None)   # None -> defaults to CELL_ID+1
    auth_mask:      int  = 0            # 11-bit; 0 = auth_boot (unconfigured)
    physical_mode:  bool = True         # True = BOOT state
    output_set:     bool = False        # separate register — see class docstring
    frozen:         bool = False

    # ── Topology latch fields (cmd_latch[31:0]) ─────────────────────────────
    topology:        int  = TOPO_PASS_A
    is_command_cell: bool = False       # Phase 5 — stored, NotImplementedError on fire if set
    cell_mode:       int  = 0           # reserved, unwired (2 bits)
    start_flag:      bool = False       # "armed"
    dtype:           int  = DTYPE_NUMERIC
    invert_out:      bool = False
    latch_in:        bool = False
    priority_flag:   bool = False       # inert placeholder (no scheduler yet)
    trace:           bool = False       # inert placeholder (no Ward/tracing yet)
    breakpoint:      bool = False       # inert placeholder
    one_shot:        bool = False
    loop_back:       bool = False
    latch_A_dis:     bool = False       # ACTUALLY WIRED (gates first-arrival store)
    latch_B_dis:     bool = False       # DOCUMENTED, NOT WIRED in the real RTL — inert here too

    # ── Two-arrival mechanics state ─────────────────────────────────────────
    a_data:         int  = 0
    a_arrived:      bool = False
    data_reg:       int  = 0
    one_shot_fired: bool = False

    # ── Phase 2: methodology latch fields (cmd_latch[63:32]) ────────────────
    # Verified against unicell64_v3.v lines 588-592, 700-808, 892-895 (the
    # logic, not just the field-map comment -- same discipline as Phase 1).
    nibble_mask:    int  = 0     # 8 bits, one per nibble: 1=BLOCK, 0=PASS
    mask_en:        bool = False
    shift_amt:      int  = 0     # 0-31; STORED as 6 bits in the real RTL
                                 # (cmd_latch[46:41]) but only the low 5 bits
                                 # are ever actually consumed by the shift
                                 # tables (verified: `shift_amt[4:0]` is what
                                 # both bus_data_shifted and computed_shifted
                                 # read) -- the 6th stored bit is dead,
                                 # matching the same category of quirk as
                                 # latch_B_dis. Modeled here as a plain 0-31
                                 # int, masked to 5 bits on use, matching
                                 # what's actually consumed.
    shift_in_en:    bool = False  # shift the TRIGGER (B) left before the gate
    shift_out_en:   bool = False  # shift the RESULT right before emission
    lane_cut:       int  = 0     # 3 bits: cut bits at byte boundaries 8/16/24

    # ── Phase 3: routing latch fields (cmd_latch[95:64]) ────────────────────
    # Verified against unicell64_v3.v lines 515-559 (points.md #49/#51/#58/#59).
    # 6-bit fields, 3D-ready; only the low 4 bits (N/S/E/W) are physically
    # wired to real bridges today -- bits [5:4] reserved for future Up/Down.
    routing_mask:      int  = 0   # "openness" -- which directions are open at all
    cardinal_edge:     int  = 0   # per open direction: local(0) or cardinal-hop(1)
    pattern_low:       int  = 0   # wanted directions when comparator = LOW
    pattern_equal:     int  = 0   # wanted directions when comparator = EQUAL
    pattern_high:      int  = 0   # wanted directions when comparator = HIGH
    dynamic_route_en:  bool = False  # 0=ignore comparator, effective_routing=routing_mask

    # Buffered fire-time routing result -- mirrors the RTL's own out_buf_
    # routing/out_buf_transit registers (unicell64_v3.v line 583-589), which
    # are captured AT the moment of fire (since a_data/bus_data may move on
    # before a later drain stage reads them) and consumed separately from
    # the fired data value. Phase 3 computes these correctly per-fire;
    # Phase 6 (array-level) is what actually ROUTES a fired value to other
    # cells using them.
    last_fire_routing: int  = 0   # effective_routing at the most recent fire
    last_fire_transit: bool = False  # transit_only at the most recent fire

    # ── Phase 5: command-emit state (cmd_emit_buf_bus/data equivalents) ─────
    # Verified against unicell64_v3.v lines 1427-1437 (generic is_command_cell
    # fire) and 1088-1127 (CMD_LOAD_DONE's dual-bus confirm, points.md #63).
    last_emit_bus:    int  = 0     # the emitted command word (== a_data at fire time)
    last_emit_target: Optional[int] = None  # output_address at fire time
    load_confirmed:   bool = False  # cmd_latch[52] -- debug-only bookkeeping,
                                    # NOT part of the wire protocol (RTL's own note)

    def __post_init__(self):
        if self.input_address is None:
            self.input_address = self.CELL_ID & 0xFFFF
        if self.output_address is None:
            self.output_address = (self.CELL_ID + 1) & 0xFFFF

    # ── Auth / addressing ────────────────────────────────────────────────────

    @property
    def auth_boot(self) -> bool:
        """auth_mask == 0 -> unconfigured, CMD_BOOT_COMMIT/CMD_ARRAY_RESET
        accepted unconditionally. Matches unicell64_v3.v line 844."""
        return self.auth_mask == 0

    def auth_ok(self, auth_token: int = 0) -> bool:
        """Matches unicell64_v3.v line 845 exactly: auth_boot OR token match."""
        return self.auth_boot or (auth_token == self.auth_mask)

    def addr_match(self, bus_addr: int) -> bool:
        """DATA key — the mutable listen address. unicell64_v3.v line 812."""
        return bus_addr == self.input_address

    def config_match(self, bus_addr: int) -> bool:
        """CONFIG key — the permanent identity. unicell64_v3.v line 813.
        ALL config targets CELL_ID, never the mutable listen address —
        this is what makes two cells sharing a listen address still
        individually configurable (fusion impossible), per the RTL's own
        v3 addressing-split invariant."""
        return bus_addr == self.CELL_ID

    # ── Boot / reset ─────────────────────────────────────────────────────────

    def boot_commit(self, logical_addr: int, auth_mask_bits: int) -> None:
        """CMD_BOOT_COMMIT (opcode 0x07). No auth required — BOOT-state only,
        exempt per the RTL. Ignored if already in RUN state (physical_mode
        already False), matching `if (physical_mode) begin ... end` exactly
        rather than silently applying it anyway."""
        if not self.physical_mode:
            return
        self.input_address = logical_addr & 0xFFFF
        # RTL stores {3'b0, cmd_data[23:16]} -- only the low 8 bits of the
        # 11-bit auth_mask are settable via BOOT_COMMIT; the upper 3 bits
        # default 0 here and need CMD_LOAD_AT (Phase 4) to set non-zero.
        self.auth_mask = auth_mask_bits & 0xFF
        self.physical_mode = False

    def array_reset(self, auth_token: int = 0) -> None:
        """CMD_ARRAY_RESET (opcode 0x08). Auth-gated (unlike a real hardware
        rst, which needs no auth by definition — this is the SOFTWARE reset
        command). Matches unicell64_v3.v lines 939-954 exactly."""
        if not self.auth_ok(auth_token):
            raise AuthError(f"CMD_ARRAY_RESET rejected: auth_token={auth_token:#x} "
                             f"!= auth_mask={self.auth_mask:#x}")
        self.topology = TOPO_PASS_A
        self.is_command_cell = False
        self.cell_mode = 0
        self.start_flag = False
        self.dtype = DTYPE_NUMERIC
        self.invert_out = False
        self.latch_in = False
        self.priority_flag = False
        self.trace = False
        self.breakpoint = False
        self.one_shot = False
        self.loop_back = False
        self.latch_A_dis = False
        self.latch_B_dis = False
        self.nibble_mask = 0
        self.mask_en = False
        self.shift_amt = 0
        self.shift_in_en = False
        self.shift_out_en = False
        self.lane_cut = 0
        self.routing_mask = 0
        self.cardinal_edge = 0
        self.pattern_low = 0
        self.pattern_equal = 0
        self.pattern_high = 0
        self.dynamic_route_en = False
        self.last_fire_routing = 0
        self.last_fire_transit = False
        self.auth_mask = 0
        self.input_address = self.CELL_ID & 0xFFFF
        self.output_address = (self.CELL_ID + 1) & 0xFFFF
        self.frozen = False
        self.physical_mode = True
        self.output_set = False
        self.a_arrived = False
        # NOTE: the real RTL does NOT explicitly reset a_data on
        # CMD_ARRAY_RESET (verified against the exact handler -- only
        # `cmd_latch<=128'h0`, which doesn't include a_data, a separate
        # register). Not resetting it here either, even though it's
        # unobservable in practice (a_arrived=False means nothing reads it
        # until a fresh first-arrival overwrites it) -- faithful to what the
        # silicon actually does, not a "helpful" extra reset it doesn't have.
        self.data_reg = 0
        self.one_shot_fired = False
        self.load_confirmed = False  # cmd_latch[52] -- genuinely cleared by cmd_latch<=0

    # ── Config opcodes ───────────────────────────────────────────────────────

    def set_input_address(self, addr: int, auth_token: int = 0) -> None:
        """CMD_SET_INPUT_ADDR (opcode 0x02)."""
        if not self.auth_ok(auth_token):
            raise AuthError("CMD_SET_INPUT_ADDR rejected: auth mismatch")
        self.input_address = addr & 0xFFFF

    def set_output_address(self, addr: int, auth_token: int = 0) -> None:
        """CMD_SET_OUTPUT_ADDR (opcode 0x03)."""
        if not self.auth_ok(auth_token):
            raise AuthError("CMD_SET_OUTPUT_ADDR rejected: auth mismatch")
        self.output_address = addr & 0xFFFF

    def freeze(self, auth_token: int = 0) -> None:
        """CMD_FREEZE (opcode 0x05). Broadcast in real hardware (points.md
        #63/#65 established the targeted variant, CMD_FREEZE_AT, below)."""
        if not self.auth_ok(auth_token):
            raise AuthError("CMD_FREEZE rejected: auth mismatch")
        self.frozen = True

    def release(self, auth_token: int = 0) -> None:
        """CMD_RELEASE (opcode 0x06)."""
        if not self.auth_ok(auth_token):
            raise AuthError("CMD_RELEASE rejected: auth mismatch")
        self.frozen = False

    # ── Phase 4: targeted freeze/release (CMD_FREEZE_AT/CMD_RELEASE_AT) ────
    # Caught and fixed for real in points.md #63/#65: CMD_FREEZE being
    # broadcast-only meant freezing a TARGET cell also froze any WATCHER
    # meant to stay active -- config_match-gated targeted variants, same
    # two-word SET_TARGET+opcode shape as CMD_LOAD_AT.

    def freeze_at(self, bus_addr: int, auth_token: int = 0) -> None:
        """CMD_FREEZE_AT (opcode 39)."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("CMD_FREEZE_AT rejected: config_match or auth failed")
        self.frozen = True

    def release_at(self, bus_addr: int, auth_token: int = 0) -> None:
        """CMD_RELEASE_AT (opcode 40)."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("CMD_RELEASE_AT rejected: config_match or auth failed")
        self.frozen = False

    # ── Phase 5: CMD_LOAD_DONE (opcode 27, points.md #63) ───────────────────

    def load_done(self, bus_addr: int, auth_token: int = 0) -> int:
        """CMD_LOAD_DONE -- the cycle-3 completion marker of the fixed
        3-cycle load protocol. Verified against unicell64_v3.v lines
        1088-1127: config_match+auth gated ONLY -- NOT bus_hit/frozen, so a
        TARGET cell can confirm even while frozen mid-program (the whole
        point of the four-role SENDER/TARGET/WATCHER/COUNTER loader design).

        Drives BOTH buffers, per the #63 fix: last_emit_bus/last_emit_target
        (the command-bus path, for an EXTERNAL host/probe watching bit 17 --
        opcode field is CMD_NOP so a receiver checking only that bit sees a
        clean confirm) AND returns the data-bus confirm marker directly (the
        path an in-fabric WATCHER cell catches via its own ordinary
        receive() -- no new decode logic needed on the receiving side at
        all, which is the actual thing #63 was built to prove).

        Returns the confirm marker (0x00000001) -- what a WATCHER's own
        receive() call would see as this event's bus_data, mirroring how a
        normal fire's return value represents the data-bus side."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("CMD_LOAD_DONE rejected: config_match or auth failed")
        self.load_confirmed = True
        self.last_emit_bus = 0x00020000          # bit17=1 (completion flag), opcode=CMD_NOP
        self.last_emit_target = self.output_address
        return 0x00000001                        # confirm marker, local-only (no cardinal escape)

    def _apply_topology_word(self, *, topology: int = TOPO_PASS_A,
                              is_command_cell: bool = False,
                              auth_mask_bits: Optional[int] = None,
                              start_flag: bool = False,
                              latch_A_dis: bool = False,
                              latch_B_dis: bool = False,
                              dtype: int = DTYPE_NUMERIC,
                              invert_out: bool = False,
                              latch_in: bool = False,
                              priority_flag: bool = False,
                              trace: bool = False,
                              breakpoint: bool = False,
                              one_shot: bool = False,
                              loop_back: bool = False) -> None:
        """Shared body for CMD_RECONFIGURE and CMD_LOAD_AT (Phase 4) --
        verified field-for-field identical between the two in the real RTL
        (lines 973-998 vs 1032-1059), differing ONLY in gating. cmd_data is
        a FULL 32-bit word in real hardware: every field is written every
        time, with no 'leave unchanged' behavior -- unspecified keyword
        args here default to what a zero bit in that position would
        produce, matching real behavior exactly (an earlier version of this
        method wrongly modeled 'only touch what's passed,' caught and fixed
        while building Phase 4 -- no existing test relied on the wrong
        behavior, confirmed before fixing).
        auth_mask_bits: 11-bit, written ONLY if physical_mode (boot-only,
        matches `if (physical_mode) cmd_latch[63:53] <= cmd_data[30:20]`
        in both opcodes exactly).
        Unconditional side effects on EVERY call, matching the RTL exactly:
        frozen/one_shot_fired/a_arrived clear, output_set sets."""
        self.topology = topology & 0x3FF
        self.is_command_cell = is_command_cell
        if self.physical_mode and auth_mask_bits is not None:
            self.auth_mask = auth_mask_bits & 0x7FF
        self.start_flag = start_flag
        self.latch_A_dis = latch_A_dis
        self.latch_B_dis = latch_B_dis
        self.dtype = dtype & 0b11
        self.invert_out = invert_out
        self.latch_in = latch_in
        self.priority_flag = priority_flag
        self.trace = trace
        self.breakpoint = breakpoint
        self.one_shot = one_shot
        self.loop_back = loop_back
        self.frozen = False
        self.one_shot_fired = False
        self.a_arrived = False
        self.output_set = True

    def reconfigure(self, *, auth_token: int = 0, **fields) -> None:
        """CMD_RECONFIGURE (opcode 0x04) -- BROADCAST (auth_ok only, no
        config_match). See _apply_topology_word for the full field set and
        the RTL cross-reference; CMD_LOAD_AT (load_at(), below) is the
        field-identical, config_match-gated counterpart."""
        if not self.auth_ok(auth_token):
            raise AuthError("CMD_RECONFIGURE rejected: auth mismatch")
        self._apply_topology_word(**fields)

    def load_at(self, bus_addr: int, auth_token: int = 0, **fields) -> None:
        """CMD_LOAD_AT (opcode 23, Phase 4) -- config_match-gated. Verified
        field-for-field IDENTICAL to CMD_RECONFIGURE in the real RTL (lines
        973-998 vs 1032-1059) -- the only difference is this gating. Only
        the addressed cell (bus_addr == its own CELL_ID) applies it,
        enabling per-cell heterogeneous config without a broadcast hitting
        every cell (the actual gap CMD_RECONFIGURE has on its own)."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("CMD_LOAD_AT rejected: config_match or auth failed")
        self._apply_topology_word(**fields)

    def set_output_set(self, value: bool = True) -> None:
        """output_set is a separate register in the real RTL (see class
        docstring), touched as a side effect of CMD_SET_OUTPUT_ADDR and a
        few other opcodes in the real hardware. Exposed directly here for
        Phase 1 since the exact side-effect wiring across every opcode
        that touches it is a Phase-4-adjacent detail; test setup should
        call this explicitly rather than assume any one opcode implies it,
        until that wiring is confirmed opcode-by-opcode against the RTL."""
        self.output_set = value

    # ── Phase 2: methodology setters (METH_SET_*) ───────────────────────────
    # All config_match-gated in the real RTL (unicell64_v3.v line ~1135's
    # `if (config_match && auth_ok)` wraps the whole methodology dispatch),
    # unlike CMD_RECONFIGURE which is auth_ok-only/broadcast (points.md #62's
    # own framing). `bus_addr` is the address this call claims to be issued
    # against -- in a real multi-cell array (Phase 6) that's a shared bus
    # value every cell sees; here, with one cell in isolation, the caller
    # passes it explicitly so the config_match gating is exercised for real
    # rather than assumed to always pass.

    def set_nibble_mask(self, bus_addr: int, mask: int, auth_token: int = 0) -> None:
        """METH_SET_MASK. mask: 8 bits, one per nibble, 1=BLOCK 0=PASS."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("METH_SET_MASK rejected: config_match or auth failed")
        self.nibble_mask = mask & 0xFF
        self.mask_en = True

    def set_shift_in(self, bus_addr: int, amount: int, auth_token: int = 0) -> None:
        """METH_SET_SHIFT_IN. amount stored 0-31 (low 5 bits are what's
        actually consumed by the shift table -- see shift_amt field note)."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("METH_SET_SHIFT_IN rejected: config_match or auth failed")
        self.shift_amt = amount & 0x3F
        self.shift_in_en = True

    def set_shift_out(self, bus_addr: int, amount: int, auth_token: int = 0) -> None:
        """METH_SET_SHIFT_OUT. Same stored shift_amt as SET_SHIFT_IN -- the
        real RTL has exactly one shift_amt register shared by both
        directions (verified: both `shift_in_en` and `shift_out_en`
        resolve to the same `m_shift_amt[4:0]`, line 894-895)."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("METH_SET_SHIFT_OUT rejected: config_match or auth failed")
        self.shift_amt = amount & 0x3F
        self.shift_out_en = True

    def set_lane_cut(self, bus_addr: int, bits: int, auth_token: int = 0) -> None:
        """METH_SET_LANE. 3 bits, one per byte boundary (8/16/24)."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("METH_SET_LANE rejected: config_match or auth failed")
        self.lane_cut = bits & 0b111

    # ── Phase 3: routing-latch setters ──────────────────────────────────────
    # METH_SET_ROUTING/METH_SET_CARDINAL_EDGE are config_match-gated, same
    # family as the Phase 2 methodology opcodes. CMD_SET_ROUTE_LATCH is the
    # WHOLE-latch broadcast load (auth_ok only, no config_match) -- points.md
    # #59's own design, deliberately mirroring CMD_RECONFIGURE's tradeoff:
    # fine for setting many cells identically, defeats heterogeneous per-cell
    # routing otherwise (which is exactly why #62 added the targeted
    # counterpart, CMD_SET_ROUTE_LATCH_AT -- that's Phase 4, config_match-
    # gated, not built yet).

    def set_routing_mask(self, bus_addr: int, mask: int, auth_token: int = 0) -> None:
        """METH_SET_ROUTING. Low 4 bits are the real N/S/E/W wiring today;
        bits [5:4] reserved for future 3D (Up/Down) bridges."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("METH_SET_ROUTING rejected: config_match or auth failed")
        self.routing_mask = mask & _ROUTE_MASK6

    def set_cardinal_edge(self, bus_addr: int, mask: int, auth_token: int = 0) -> None:
        """METH_SET_CARDINAL_EDGE. Per-edge local(0)/cardinal-hop(1), bit-
        for-bit paired with routing_mask."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("METH_SET_CARDINAL_EDGE rejected: config_match or auth failed")
        self.cardinal_edge = mask & _ROUTE_MASK6

    def set_transit(self, bus_addr: int, all_cardinal: bool, auth_token: int = 0) -> None:
        """METH_SET_TRANSIT -- the LEGACY convenience opcode from #58: sets
        ALL of cardinal_edge's bits uniformly (all-cardinal-only or
        all-local), reproducing the pre-#42 single global transit_only bit
        exactly. Kept for the same backward-compatibility reason the RTL
        keeps it."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("METH_SET_TRANSIT rejected: config_match or auth failed")
        self.cardinal_edge = _ROUTE_MASK6 if all_cardinal else 0

    def _apply_route_latch_word(self, *, routing_mask: int = 0,
                                 cardinal_edge: int = 0,
                                 pattern_low: int = 0,
                                 pattern_equal: int = 0,
                                 pattern_high: int = 0,
                                 dynamic_route_en: bool = False) -> None:
        """Shared body for CMD_SET_ROUTE_LATCH and CMD_SET_ROUTE_LATCH_AT
        (Phase 4) -- verified field-for-field identical in the real RTL
        (lines 1000-1012 vs #62's targeted counterpart), differing only in
        gating. Full-word overwrite semantics, same correction applied here
        as _apply_topology_word: every field is written every time,
        unspecified keywords default to their zero value, not 'unchanged'.
        No side effects beyond the six fields (verified: 'no physical_mode
        branching needed' in the RTL's own comment -- unlike the topology
        latch, nothing here touches frozen/output_set/etc)."""
        self.routing_mask = routing_mask & _ROUTE_MASK6
        self.cardinal_edge = cardinal_edge & _ROUTE_MASK6
        self.pattern_low = pattern_low & _ROUTE_MASK6
        self.pattern_equal = pattern_equal & _ROUTE_MASK6
        self.pattern_high = pattern_high & _ROUTE_MASK6
        self.dynamic_route_en = dynamic_route_en

    def set_route_latch(self, *, auth_token: int = 0, **fields) -> None:
        """CMD_SET_ROUTE_LATCH (opcode 37) -- whole routing-latch load,
        BROADCAST (auth_ok only, no config_match), mirroring CMD_
        RECONFIGURE's own tradeoff exactly. See _apply_route_latch_word for
        the field set; set_route_latch_at() is the targeted counterpart."""
        if not self.auth_ok(auth_token):
            raise AuthError("CMD_SET_ROUTE_LATCH rejected: auth mismatch")
        self._apply_route_latch_word(**fields)

    def set_route_latch_at(self, bus_addr: int, auth_token: int = 0, **fields) -> None:
        """CMD_SET_ROUTE_LATCH_AT (opcode 38, Phase 4/points.md #62) --
        config_match-gated targeted counterpart to CMD_SET_ROUTE_LATCH.
        Caught before it shipped in the real project: a broadcast-only
        routing latch load would defeat per-cell heterogeneous routing
        entirely, same trap CMD_RECONFIGURE was in before CMD_LOAD_AT."""
        if not (self.config_match(bus_addr) and self.auth_ok(auth_token)):
            raise AuthError("CMD_SET_ROUTE_LATCH_AT rejected: config_match or auth failed")
        self._apply_route_latch_word(**fields)

    # ── Topology presets (CMD_TOPO_* family) ────────────────────────────────
    # Each preset bundles topology + an appropriate latch_in default, exactly
    # as unicell64_v3.v's case arms do (lines 1284-1349) -- single-input ops
    # (PASS_A, NOT_A, ZERO, ONE) get latch_in=1 automatically; two-input ops
    # (NOR, AND, OR, NAND, PASS_B, XNOR, XOR) get latch_in=0. `armed` picks
    # the _COLD (armed=False) vs plain (armed=True) opcode variant.

    _PRESETS = {
        "PASS_A": (TOPO_PASS_A, True),
        "NOT_A":  (TOPO_NOT_A,  True),
        "NOR":    (TOPO_NOR,    False),
        "AND":    (TOPO_AND,    False),
        "OR":     (TOPO_OR,     False),
        "NAND":   (TOPO_NAND,   False),
        "PASS_B": (TOPO_PASS_B, False),
        "XNOR":   (TOPO_XNOR,   False),
        "XOR":    (TOPO_XOR,    False),
        "ZERO":   (TOPO_ZERO,   True),
        "ONE":    (TOPO_ONE,    True),
    }

    def set_topology_preset(self, name: str, armed: bool, auth_token: int = 0) -> None:
        """CMD_TOPO_<NAME>[_COLD]. `armed` selects the plain (armed=True)
        vs _COLD (armed=False) variant -- matches `cmd_latch[22] <=
        cmd_opcode[0]` in the RTL exactly (armed variants are the odd
        opcode in each pair)."""
        if not self.auth_ok(auth_token):
            raise AuthError(f"CMD_TOPO_{name} rejected: auth mismatch")
        if name not in self._PRESETS:
            raise ValueError(f"unknown topology preset {name!r} "
                              f"(valid: {sorted(self._PRESETS)})")
        topo, latch_in_default = self._PRESETS[name]
        self.topology = topo
        self.latch_in = latch_in_default
        self.start_flag = armed

    # ── Two-arrival fire mechanics ───────────────────────────────────────────

    def bus_hit(self, bus_addr: int, cmd_valid: bool = False) -> bool:
        """Matches unicell64_v3.v line 818 exactly."""
        return (not self.frozen and self.start_flag and self.output_set
                and not cmd_valid and self.addr_match(bus_addr))

    def receive(self, bus_addr: int, bus_data: int) -> Optional[int]:
        """
        Deliver one data-bus event (bus_valid this cycle) to the cell.
        Returns the fired DATA-BUS output value if this event completed an
        ordinary fire, or None if it was absorbed as a first arrival /
        ignored (address mismatch, not armed, frozen, etc) OR if this cell
        is a command-emit cell (Phase 5) -- a command-emit fire produces no
        data-bus output at all; see last_emit_bus/last_emit_target instead,
        buffered the same way last_fire_routing/last_fire_transit are.

        Matches the two-arrival model at unicell64_v3.v lines 1397-1445
        exactly, including the loop_back-after-latch_in precedence (see
        module docstring), the one_shot/start_flag interaction, and the
        is_command_cell branch (line 1427-1437) -- verified: data_reg,
        the comparator, latch_in, loop_back, and one_shot ALL still apply
        UNCONDITIONALLY regardless of is_command_cell; only the output
        DESTINATION (command bus vs data bus) differs. A command-emit
        cell can genuinely have latch_in/loop_back set too, same as any
        other cell -- the RTL doesn't special-case those away.

        Phase 1 does not model the odd_phase output-buffer pipeline stage
        (out_buf_valid/odd_phase drain) -- that's a hardware timing
        optimization, not part of the LOGICAL behavior this phase is
        proving. The fired value is returned directly, synchronously,
        the same cycle it's computed.
        """
        hit = self.bus_hit(bus_addr, cmd_valid=False)

        # First arrival: store into a_data (gated by latch_A_dis -- ACTUALLY
        # wired in the real RTL; see class docstring re: latch_B_dis, which
        # is documented but dead in the silicon and modeled as dead here too).
        if hit and not self.a_arrived and not self.latch_A_dis:
            self.a_data = bus_data & _MASK32
            self.a_arrived = True
            return None

        # Second arrival: fire, if armed for it (one_shot not yet spent).
        new_data = (not (self.one_shot and self.one_shot_fired)) and hit and self.a_arrived
        if not new_data:
            return None

        a = self.a_data
        b_raw = bus_data & _MASK32   # RAW value -- used for latch_in's rearm store,
                                     # exactly as unicell64_v3.v's `a_data <= bus_data_r`
                                     # does (NOT bus_data_masked -- verified, same
                                     # never-mask-a-stored-value pattern as the
                                     # first-arrival store).
        # Phase 2: shift_in then nibble_mask, applied ONLY to the gate's B
        # operand (second_val) -- never to any stored value. Order matches
        # the RTL exactly: bus_data_shifted first, THEN nibble mask on top
        # (line 707: `bus_data_shifted & nibble_keep`).
        b_shifted = shift_in_left(b_raw, self.shift_amt & 0x1F, self.shift_in_en)
        b_gate    = apply_nibble_mask(b_shifted, self.nibble_mask, self.mask_en)

        computed_output = compute_gate(self.topology, a, b_gate)
        self.data_reg = computed_output  # RTL: raw, pre-shift-out/pre-lane/pre-invert_out
                                          # -- computed UNCONDITIONALLY, even for a
                                          # command-emit cell (its VALUE is simply
                                          # unused by the emit path, matching the RTL).

        # Phase 3: comparator + effective routing -- uses the RAW trigger
        # (b_raw), NOT b_gate. Computed UNCONDITIONALLY too (verified: the
        # RTL computes this before the is_command_cell branch, not inside
        # the else) -- semantically meaningless for a command-emit cell's
        # own emission (which doesn't reference it), but faithfully
        # replicated anyway rather than special-cased away.
        selected = select_pattern(b_raw, a, self.pattern_low, self.pattern_equal, self.pattern_high)
        effective_routing = compute_effective_routing(self.dynamic_route_en, selected, self.routing_mask)
        self.last_fire_routing = effective_routing
        self.last_fire_transit = compute_transit_only(effective_routing, self.cardinal_edge)

        # Phase 5: is_command_cell branch (line 1427-1437) -- EMIT drives the
        # STORED a_data (captured as `a` above, BEFORE this fire's own
        # latch_in/loop_back mutations below) onto the command bus, targeted
        # by output_address. The second arrival's own value (b_raw) is
        # ignored entirely for the emitted content -- only used as the
        # trigger. No shift_out/lane_cut/invert_out applied to an emission
        # (verified: `cmd_emit_buf_bus <= a_data;` is raw, unlike the
        # else-branch's out_buf_data <= computed_lane).
        if self.is_command_cell:
            self.last_emit_bus = a & _MASK32
            self.last_emit_target = self.output_address
            fired_value = None
        else:
            # Phase 2: shift_out then lane_cut, applied ONLY to the externally
            # emitted value -- data_reg/loop_back/latch_in above all already used
            # the RAW computed_output, matching the RTL's out_buf_data-only
            # application exactly (line 1439: `out_buf_data <= computed_lane`).
            # invert_out applies LAST, at the drain stage, on top of the
            # shifted+lane-cut value (matches the RTL's `out_data <= invert_out
            # ? ~out_buf_data : out_buf_data` reading from computed_lane).
            shifted_out = shift_out_right(computed_output, self.shift_amt & 0x1F, self.shift_out_en)
            lane_kill   = compute_lane_kill(self.shift_amt & 0x1F, self.lane_cut)
            computed_lane = shifted_out & lane_kill
            fired_value = (~computed_lane) & _MASK32 if self.invert_out else computed_lane

        # latch_in re-arm, THEN loop_back -- program order in the RTL, and
        # since both write a_data, loop_back's write wins if both are set
        # (last non-blocking assignment on the same edge wins). Replicated
        # via ordering, not a special-cased "which wins" branch. Uses b_raw,
        # NOT b_gate -- the stored value is never shifted/masked, only the
        # gate's live B operand is. APPLIES REGARDLESS of is_command_cell,
        # matching the RTL exactly -- these are outside the if/else.
        if self.latch_in:
            self.a_arrived = True
            self.a_data = b_raw
        else:
            self.a_arrived = False

        if self.loop_back:
            self.a_data = computed_output

        if self.one_shot:
            self.one_shot_fired = True
            self.start_flag = False

        return fired_value

    def __repr__(self) -> str:
        return (f"UniCellV3(CELL_ID={self.CELL_ID}, topology={self.topology:#05x}, "
                f"in={self.input_address:#06x}, out={self.output_address:#06x}, "
                f"armed={self.start_flag}, frozen={self.frozen}, "
                f"a_arrived={self.a_arrived})")
