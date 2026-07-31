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
        self.auth_mask = 0
        self.input_address = self.CELL_ID & 0xFFFF
        self.output_address = (self.CELL_ID + 1) & 0xFFFF
        self.frozen = False
        self.physical_mode = True
        self.output_set = False
        self.a_arrived = False
        self.a_data = 0
        self.data_reg = 0
        self.one_shot_fired = False

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
        #63/#65 established the targeted variant, CMD_FREEZE_AT, is Phase 4
        -- this models the broadcast opcode only)."""
        if not self.auth_ok(auth_token):
            raise AuthError("CMD_FREEZE rejected: auth mismatch")
        self.frozen = True

    def release(self, auth_token: int = 0) -> None:
        """CMD_RELEASE (opcode 0x06)."""
        if not self.auth_ok(auth_token):
            raise AuthError("CMD_RELEASE rejected: auth mismatch")
        self.frozen = False

    def reconfigure(self, *, topology: Optional[int] = None,
                     is_command_cell: Optional[bool] = None,
                     start_flag: Optional[bool] = None,
                     dtype: Optional[int] = None,
                     invert_out: Optional[bool] = None,
                     latch_in: Optional[bool] = None,
                     priority_flag: Optional[bool] = None,
                     trace: Optional[bool] = None,
                     breakpoint: Optional[bool] = None,
                     one_shot: Optional[bool] = None,
                     loop_back: Optional[bool] = None,
                     latch_A_dis: Optional[bool] = None,
                     latch_B_dis: Optional[bool] = None,
                     auth_token: int = 0) -> None:
        """CMD_RECONFIGURE (opcode 0x04) -- sets the topology-latch fields
        from a config word. Modeled as keyword fields rather than a raw
        32-bit int for Phase 1 (a raw cmd_data[31:0] packer/unpacker can be
        added later if bit-exact wire-format testing is needed; the LOGICAL
        content is what this phase is proving). Only auth_ok is required
        (no config_match) -- CMD_RECONFIGURE is a BROADCAST opcode in the
        real RTL (points.md #62's own framing: CMD_LOAD_AT is what CMD_
        RECONFIGURE's Phase-4 targeted counterpart will be)."""
        if not self.auth_ok(auth_token):
            raise AuthError("CMD_RECONFIGURE rejected: auth mismatch")
        if topology is not None:        self.topology = topology & 0x3FF
        if is_command_cell is not None: self.is_command_cell = is_command_cell
        if start_flag is not None:      self.start_flag = start_flag
        if dtype is not None:           self.dtype = dtype & 0b11
        if invert_out is not None:      self.invert_out = invert_out
        if latch_in is not None:        self.latch_in = latch_in
        if priority_flag is not None:   self.priority_flag = priority_flag
        if trace is not None:           self.trace = trace
        if breakpoint is not None:      self.breakpoint = breakpoint
        if one_shot is not None:        self.one_shot = one_shot
        if loop_back is not None:       self.loop_back = loop_back
        if latch_A_dis is not None:     self.latch_A_dis = latch_A_dis
        if latch_B_dis is not None:     self.latch_B_dis = latch_B_dis

    def set_output_set(self, value: bool = True) -> None:
        """output_set is a separate register in the real RTL (see class
        docstring), touched as a side effect of CMD_SET_OUTPUT_ADDR and a
        few other opcodes in the real hardware. Exposed directly here for
        Phase 1 since the exact side-effect wiring across every opcode
        that touches it is a Phase-4-adjacent detail; test setup should
        call this explicitly rather than assume any one opcode implies it,
        until that wiring is confirmed opcode-by-opcode against the RTL."""
        self.output_set = value

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
        Returns the fired output value if this event completed a fire
        (second arrival), or None if it was absorbed as a first arrival /
        ignored (address mismatch, not armed, frozen, etc).

        Matches the two-arrival model at unicell64_v3.v lines 1397-1445
        exactly, including the loop_back-after-latch_in precedence (see
        module docstring) and the one_shot/start_flag interaction.

        Phase 1 does not model the odd_phase output-buffer pipeline stage
        (out_buf_valid/odd_phase drain) -- that's a hardware timing
        optimization, not part of the LOGICAL behavior this phase is
        proving. The fired value is returned directly, synchronously,
        the same cycle it's computed.
        """
        if self.is_command_cell:
            # Phase 5. Loud failure rather than silently computing a normal
            # gate result for a cell that's actually a command emitter in
            # the real hardware -- wrong silently is worse than NotImplemented.
            raise NotImplementedError(
                "is_command_cell fire behavior is Phase 5 (points.md #63/#65/#66) "
                "-- not yet modeled in this VM.")

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
        b = bus_data & _MASK32
        computed_output = compute_gate(self.topology, a, b)
        self.data_reg = computed_output  # RTL: raw, pre-invert_out value

        # latch_in re-arm, THEN loop_back -- program order in the RTL, and
        # since both write a_data, loop_back's write wins if both are set
        # (last non-blocking assignment on the same edge wins). Replicated
        # via ordering, not a special-cased "which wins" branch.
        if self.latch_in:
            self.a_arrived = True
            self.a_data = b
        else:
            self.a_arrived = False

        if self.loop_back:
            self.a_data = computed_output

        if self.one_shot:
            self.one_shot_fired = True
            self.start_flag = False

        fired_value = (~computed_output) & _MASK32 if self.invert_out else computed_output
        return fired_value

    def __repr__(self) -> str:
        return (f"UniCellV3(CELL_ID={self.CELL_ID}, topology={self.topology:#05x}, "
                f"in={self.input_address:#06x}, out={self.output_address:#06x}, "
                f"armed={self.start_flag}, frozen={self.frozen}, "
                f"a_arrived={self.a_arrived})")
