"""
unicell_super_automaton_v1.py — VM dispatch for the super cell
(`unicell_super_v1.v`), item 2 of `#324`'s own stated next phase
(`points.md #336` did item 1, the ICM v3 format itself).

GROUND TRUTH, read directly before writing anything here: `ram_cell_v1.v`,
`adder_cell_v1.v`, `accumulator_cell_v1.v`, `compare_cell_v1.v`,
`latch_cell_v1.v`, `nibble_mask_addon_v1.v`, `shift_lane_addon_v1.v`,
`invert_addon_v1.v`. nano's own behavior is NOT reimplemented here — it
is delegated to `nano/unicell_automaton_v1.py`'s already-proven `CACell`
directly (composition, not reinvention), configured only with the subset
`icm_v3.py`'s nano field table actually exposes (topology/ready/
routing_mask/cardinal_edge -- no hold/feedback/command-cell/loop_back/
latch_in/one_shot, matching `ICM_V3_FORMAT.md`'s own documented scope
limit).

ABSTRACTION LEVEL, stated honestly, matching `unicell_automaton_v1.py`'s
own precedent: this is an EVENT-DRIVEN tick model (one call per pending
delivery per tick, OR-combining same-cycle same-cell arrivals per
`points.md #153`), not a clock-cycle-accurate register replica of the
RTL's `always @(posedge clk)` blocks. This is the same level of fidelity
`CACell`/`CAGrid` already commit to for nano -- correctness of protocol,
ordering, and computed results, not cycle-for-cycle timing.

A REAL SIMPLIFICATION, stated rather than hidden: like `CACell.deliver()`,
a fire here does NOT pre-check a downstream neighbor's own readiness
before attempting delivery (the real RTL's `targets_all_ready`/`ready_in`
check) -- it always attempts, and the TARGET's own `deliver()` rejects
(returns `accepted=False`) if it isn't actually able to receive, causing
a retry next tick via the same `SuperGrid.tick()` requeue mechanism
`CAGrid.tick()` already uses. This converges to the same steady-state
behavior with different intermediate-tick backpressure timing -- an
existing, already-accepted modeling choice in this codebase, not a new
one introduced here.

THE GENERIC OFFER PASS -- the one genuinely new mechanism this file adds
beyond what `CAGrid` already had: none of the 5 non-nano cores fire in
direct response to the event that filled their output register (the real
RTL's `any_fire` is a COMBINATIONAL re-evaluation, live every cycle, not
triggered by the capture event itself). So `SuperGrid.tick()` runs a
second, generic pass every tick -- any non-nano cell with something valid
to offer and `pending_ack==0` re-arms and fires, whether or not anything
was captured that same tick. This single mechanism naturally reproduces
BOTH shapes correctly: a single-shot core (RAM/adder/comparator) offers
once after each capture and goes quiet until captured again (its `_valid`
flag clears the moment its offer fully drains -- the drain-detection pass
below); a continuously-live core (accumulator/latch/RAM fixed-mode) never
clears `_valid` at all, so it re-arms and re-fires every single tick it's
idle -- a genuine continuous heartbeat, matching the sentinel design
intent these two cores were built for (`points.md #294`/`#295`).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from unicell_automaton_v1 import CACell, N, S, E, W, _DIRS, _DIR_BIT, _OPPOSITE, _MASK32, _MASK4

import icm_v3 as v3
import generic_field_codec_v1 as gfc

_ROOT_DEFINITION = gfc.load_root_definition()

from dataclasses import dataclass as _dataclass
from typing import Callable as _Callable


@_dataclass
class CoreHandler:
    """One core type's registered behavior (`points.md #358`) -- the
    real, concrete step toward `#216` item 4 ("genuinely parameterized
    against whatever root definition got loaded, not hardcoded to
    today's specific cell revision"): a NEW core type can be added by
    registering one of these, without touching `SuperCell`'s own
    `deliver()`/`_offer_state()`/`is_continuously_live()`/
    `clear_valid_on_drain()` methods at all -- the same registration-
    based extensibility pattern that already worked well for the tile
    library (`SuperTileLibrary.register()`, `ComposedTileLibrary.
    register()`), applied here to core BEHAVIOR dispatch specifically.

    REAL, HONEST SCOPE: this is a dispatch-mechanism refactor, not a
    "genuinely generic, root-definition-driven BEHAVIOR" engine --
    `root_definition.json` only captures FIELD POSITIONS (`#355`), not
    capture/offer semantics, which genuinely can't be reduced to data
    without something much bigger (a real hardware-behavior description
    language, its own separate undertaking, not attempted here). A new
    core's own `deliver`/`offer_state` functions still need real Python
    written for them -- this registry just means writing that Python is
    the ONLY thing needed, not also patching four separate if/elif
    chains scattered through this file."""
    deliver: _Callable
    offer_state: "_Callable | None" = None
    continuously_live: bool = False
    clear_valid: "_Callable | None" = None


_CORE_HANDLERS: dict = {}


def register_core_handler(name: str, handler: CoreHandler) -> None:
    if name in _CORE_HANDLERS:
        raise ValueError(f"core handler {name!r} already registered")
    _CORE_HANDLERS[name] = handler


_CONTINUOUSLY_LIVE_CORES = frozenset({"accumulator", "latch"})  # RAM adds itself when fixed_mode=1


def _wrap_signed32(v: int) -> int:
    v &= _MASK32
    return v - (1 << 32) if v & 0x80000000 else v


def apply_addons(value: int, addon_config: dict) -> int:
    """nibble_mask -> shift_lane -> invert, matching unicell_super_v1.v
    lines 337-349's real instantiation order exactly."""
    value &= _MASK32

    # nibble_mask_addon_v1.v
    if addon_config.get("mask_en"):
        nm = addon_config.get("nibble_mask", 0)
        keep = 0
        for nibble in range(8):
            if not ((nm >> nibble) & 1):
                keep |= 0xF << (4 * nibble)
        value &= keep

    # shift_lane_addon_v1.v -- sparse fixed-pattern shift, faithfully ported
    if addon_config.get("shift_en"):
        amt = addon_config.get("shift_amt", 0)
        direction = addon_config.get("direction", 0)
        _SUPPORTED = (1, 2, 4, 8, 12, 16, 20, 24, 28)
        if amt in _SUPPORTED:
            if direction:  # SHIFT_OUT (right)
                shifted = (value >> amt) & _MASK32
                lane_cut = addon_config.get("lane_cut", 0)
                lane_ones = (1 << amt) - 1
                lane_kill = _MASK32
                if lane_cut & 1:
                    lane_kill &= ~((lane_ones << 8) >> amt) & _MASK32
                if lane_cut & 2:
                    lane_kill &= ~((lane_ones << 16) >> amt) & _MASK32
                if lane_cut & 4:
                    lane_kill &= ~((lane_ones << 24) >> amt) & _MASK32
                value = shifted & lane_kill
            else:  # SHIFT_IN (left)
                value = (value << amt) & _MASK32
        # unsupported amount: deliberate no-op, matches the RTL exactly

    # invert_addon_v1.v
    if addon_config.get("invert_en"):
        value = (~value) & _MASK32

    return value


@dataclass
class SuperCell:
    """One `unicell_super_v1.v` instance -- every core's own register set
    is present (matching the real RTL's "all 6 always physically
    instantiated" design), but only the SELECTED core's fields are ever
    written to by `deliver()`/the offer pass. Built FROM an
    `icm_v3.IcmV3Record` via `from_record()`, not usually constructed
    directly."""

    row: int
    col: int
    core: str
    addon_config: dict = field(default_factory=dict)
    #: points.md #602: the real ICM cell_id this instance was built
    #: from, if any -- needed so a simulated Walker (or anything else
    #: doing live identity discovery) can answer a real "self" ping
    #: with the same identity a real hardware cell would carry.
    #: Previously dropped entirely by from_record() -- a real gap,
    #: found and fixed while building the discovery mechanism that
    #: actually needed it. NOTE: icm_v3.IcmV3Record.cell_id is a real,
    #: human-readable STRING (e.g. "r1@0,0", the DSL compiler's own
    #: convention), NOT the 16-bit int CELL_ID real hardware carries
    #: (#501's own confirmed field) -- kept as whatever type the
    #: record actually has, no invented reformatting here.
    cell_id: Optional[str] = None

    # ── nano: delegated entirely to a real CACell, composition not
    # reinvention. Only set when core=="nano". ──
    _nano: Optional[CACell] = None

    # ── RAM ──
    ram_downstream_mask: int = 0
    ram_upstream_mask: int = 0
    ram_fixed_mode: bool = False
    ram_data_reg: int = 0
    ram_data_valid: bool = False

    # ── adder ──
    adder_downstream_mask: int = 0
    adder_upstream_mask: int = 0
    # #521: subtract_mode is a real RTL field now -- default 0 matches
    # real silicon's own honest reset default (A+B), same discipline
    # already applied to accumulator's step_amount (#519).
    adder_subtract_mode: bool = False
    adder_a_reg: int = 0
    adder_a_arrived: bool = False
    adder_out_buffer: int = 0
    adder_data_valid: bool = False

    # ── accumulator ──
    acc_downstream_mask: int = 0
    acc_inc_dir: int = 0
    acc_dec_dir: int = 0
    acc_total: int = 0          # signed
    acc_out_buffer: int = 0
    # #515's real extension -- step_amount is now data-driven (was
    # hardcoded +-1). Default 0 deliberately matches real silicon's own
    # honest reset default, NOT a Python convenience default of 1 --
    # every real caller must supply it explicitly, same discipline the
    # RTL testbenches already apply throughout (#515/#516/#517/#518).
    acc_step_amount: int = 0
    acc_pulse_mode: bool = False
    acc_threshold: int = 0
    acc_pulse_pending: bool = False   # pulse_mode only -- a real, discrete
                                       # "unconsumed pulse" flag, distinct
                                       # from static mode's "always live"

    # ── comparator ──
    cmp_downstream_mask: int = 0
    cmp_upstream_mask: int = 0
    cmp_threshold: int = 0      # signed
    cmp_out_buffer: int = 0
    cmp_data_valid: bool = False

    # ── latch ──
    latch_downstream_mask: int = 0
    latch_set_dir: int = 0
    latch_clear_dir: int = 0
    # #522: toggle_dir is a real RTL field now -- defaults to 0,
    # matching real silicon's own honest reset default.
    latch_toggle_dir: int = 0
    latch_state: bool = False

    # ── branch (SEL_BRANCH -- real RTL core_select slot since #542,
    # unicell_super_v3.v; VM-provisional from #519 until then). Field
    # names mirror branch_cell_v1.v's own real registers exactly
    # (#500/#504/#497). ──
    br_upstream_dir: int = 0
    br_value_source_low: bool = False
    br_value_source_equal: bool = False
    br_value_source_high: bool = False
    br_fixed_value_low: int = 0
    br_fixed_value_equal: int = 0
    br_fixed_value_high: int = 0
    br_emit_low: bool = False
    br_emit_equal: bool = False
    br_emit_high: bool = False
    br_route_low: int = 0
    br_route_equal: int = 0
    br_route_high: int = 0
    br_rolling_mode: bool = False
    br_ref_value: int = 0        # signed
    br_ref_valid: bool = False
    br_out_buffer: int = 0
    br_data_valid: bool = False
    br_active_route: int = 0     # the REAL routed mask for the current offer,
                                  # latched at capture time (varies by outcome,
                                  # unlike every other core's static downstream_mask)

    # ── sequencer: sequencer_cell_v1.v's own real registers exactly
    # (points.md #609). No upstream field at all -- genuinely no
    # capture side, confirmed directly against the RTL. ──
    seq_value_0: int = 0
    seq_value_1: int = 0
    seq_value_2: int = 0
    seq_value_3: int = 0
    seq_sequence_len_m1: int = 0   # stored as length-1, matching the real RTL exactly
    seq_downstream_mask: int = 0
    seq_index: int = 0
    seq_out_buffer: int = 0
    seq_data_valid: bool = False   # live from config onward, never toggled off
                                     # (this core has nothing to drain-and-reclose --
                                     # it just advances to the next value on drain)

    freeze_in: bool = False
    _shell_pending_ack: int = 0   # non-nano cores' shared pending_ack mask

    # ── the shell-level programming channel (points.md #390's own real
    # RTL, matched here per #391's own flagged VM sync gap) -- gated to
    # only reach nano when it's the CURRENTLY SELECTED core, matching
    # the real RTL's own sel_active_nano convention exactly. Delegates
    # straight to the already-real, already-proven CACell.program_word()
    # -- no new mechanism, just the same shell-level exposure the RTL
    # now has. ──
    @property
    def program_in(self) -> bool:
        return self._nano.program_in if self.core == "nano" else False

    @program_in.setter
    def program_in(self, value: bool) -> None:
        if self.core != "nano":
            raise ValueError(
                f"program_in only applies to nano -- this cell's own core is "
                f"{self.core!r}, matching the real RTL's own sel_active_nano "
                f"gating (#390): the shell-level programming channel only ever "
                f"reaches nano."
            )
        self._nano.program_in = value

    def program_word(self, prog_id: int, data: int) -> None:
        """Shell-level access to nano's own real, already-proven
        incremental PROG_ID-word reprogramming channel. Matches the
        exact same calling convention already established for the
        standalone `CACell` directly:
            cell.program_in = True
            cell.program_word(PROG_ID_CARDINAL_EDGE, new_mask)
            cell.program_word(PROG_ID_COMPLETE, 1)
            cell.program_in = False
        """
        if self.core != "nano":
            raise ValueError(
                f"program_word() only applies to nano -- this cell's own core "
                f"is {self.core!r}, matching the real RTL's own sel_active_nano "
                f"gating (#390): the shell-level programming channel only ever "
                f"reaches nano."
            )
        self._nano.program_word(prog_id, data)

    @property
    def program_done(self) -> bool:
        return bool(self._nano.program_done) if self.core == "nano" else False

    @classmethod
    def from_record(cls, rec: "v3.IcmV3Record") -> "SuperCell":
        core = rec.core
        cfg = rec.core_config
        addon = rec.addon_config
        cell = cls(row=rec.row, col=rec.col, core=core, addon_config=addon, cell_id=rec.cell_id)

        # Real, root-definition-driven validation (points.md #358), not
        # a silent .get(key, default) that would let a typo'd field name
        # pass through as an unnoticed zero. Uses the SAME mechanically-
        # extracted field table generic_field_codec_v1.py already
        # proved equivalent to icm_v3.py's own hand-typed one (#356) --
        # a real, independent check at the VM's own construction
        # boundary, which matters specifically because a record built
        # by hand (bypassing place()/place_composed()'s own validation
        # entirely) reaches this exact point with no other check in
        # front of it.
        if core in v3.CORE_IDS:
            known = set(gfc.field_table(_ROOT_DEFINITION, v3.CORE_IDS[core]))
            unknown = set(cfg) - known
            if unknown:
                raise ValueError(
                    f"SuperCell.from_record(): core={core!r} core_config has "
                    f"unknown field(s) {sorted(unknown)} -- known fields for this "
                    f"core, per root_definition.json: {sorted(known)}"
                )

        def dm(val):
            return v3.pack_dirmask(val) if isinstance(val, (list, tuple, set)) else int(val)

        def single_dir(val):
            """points.md #608: branch's own real upstream_dir is a
            SINGLE direction value (unlike every other core's masks),
            confirmed directly against the real capture logic
            (`d == self.br_upstream_dir`, not a bit test). The generic
            tile-placement mechanism (`super_tile_library_v1.place()`)
            always resolves a port's chosen direction into a
            single-element LIST of letters (the same convention every
            other port uses) -- accepted here and converted to the
            real N/S/E/W index, alongside the pre-existing raw-int form
            for direct core_config construction."""
            if isinstance(val, (list, tuple, set)):
                dirs = list(val)
                if len(dirs) != 1:
                    raise ValueError(f"upstream_dir must resolve to exactly one direction, got {dirs!r}")
                return {"n": N, "s": S, "e": E, "w": W}[str(dirs[0]).lower()]
            return int(val) & 0x3

        if core == "nano":
            cell._nano = CACell(
                row=rec.row, col=rec.col,
                topology=cfg.get("topology", 0),
                start_flag=bool(cfg.get("ready", 0)),
                # points.md #652: real, pre-existing bug found and fixed
                # here, predating this change -- routing_mask/
                # cardinal_edge were never wrapped in `dm()` the way
                # every other core's own dir-fields already are (e.g.
                # `adder_downstream_mask = dm(...)` a few lines above),
                # confirmed directly by testing: a real tile-library-
                # produced record with routing_mask=['e'] silently left
                # `cell._nano.routing_mask` as the raw list `['e']`, not
                # a packed int, before this fix. Never caught before
                # because nothing had yet placed a nano tile through
                # `super_tile_library.place()` and then loaded it via
                # `SuperGrid.from_icm()`/`from_record()` in the same
                # real path -- the same class of untested-combination
                # gap as `#649`'s own `hold_in`/`latch_in` bug.
                routing_mask=dm(cfg.get("routing_mask", 0)),
                cardinal_edge=dm(cfg.get("cardinal_edge", 0)),
                # #522/#543: real ports, previously never wired through
                # from the shell's own core_config -- CACell already
                # fully implements all 5 (#118/#119/#120), this was
                # purely a passthrough gap, not a missing feature.
                hold_in=bool(cfg.get("hold_in", 0)),
                fb_internal_in=bool(cfg.get("fb_internal_in", 0)),
                a_reemit_in=bool(cfg.get("a_reemit_in", 0)),
                a_update_in=bool(cfg.get("a_update_in", 0)),
                a_self_update_in=bool(cfg.get("a_self_update_in", 0)),
                # #650: same real gap, same real fix -- dynamic_route_en/
                # pattern_low/pattern_equal/pattern_high (nano_gate_v4.v's
                # own real comparator-driven routing, needed for #637/
                # #638's own real loop-exit mechanism) were never wired
                # through here either, even after being added to icm_v3.py's
                # own field table and root_definition.json above -- CACell
                # already fully implements this (`#140`), this was again
                # purely a passthrough gap. Confirmed by testing directly:
                # from_record() silently returned dynamic_route_en=False
                # even with it set to 1 in the record, before this fix.
                dynamic_route_en=bool(cfg.get("dynamic_route_en", 0)),
                pattern_low=dm(cfg.get("pattern_low", 0)),
                pattern_equal=dm(cfg.get("pattern_equal", 0)),
                pattern_high=dm(cfg.get("pattern_high", 0)),
            )
        elif core == "ram":
            cell.ram_downstream_mask = dm(cfg.get("downstream_mask", 0))
            cell.ram_upstream_mask = dm(cfg.get("upstream_mask", 0))
            cell.ram_fixed_mode = bool(cfg.get("fixed_mode", 0))
            cell.ram_data_reg = cfg.get("init_data", 0) & _MASK32
            cell.ram_data_valid = bool(cfg.get("load_data_valid", 0))
        elif core == "adder":
            cell.adder_downstream_mask = dm(cfg.get("downstream_mask", 0))
            cell.adder_upstream_mask = dm(cfg.get("upstream_mask", 0))
            cell.adder_subtract_mode = bool(cfg.get("subtract_mode", 0))
        elif core == "accumulator":
            cell.acc_downstream_mask = dm(cfg.get("downstream_mask", 0))
            cell.acc_inc_dir = dm(cfg.get("inc_dir", 0))
            cell.acc_dec_dir = dm(cfg.get("dec_dir", 0))
            cell.acc_step_amount = cfg.get("step_amount", 0) & 0xFF
            cell.acc_pulse_mode = bool(cfg.get("pulse_mode", 0))
            cell.acc_threshold = cfg.get("threshold", 0) & 0xFFFF
        elif core == "comparator":
            cell.cmp_downstream_mask = dm(cfg.get("downstream_mask", 0))
            cell.cmp_upstream_mask = dm(cfg.get("upstream_mask", 0))
            cell.cmp_threshold = cfg.get("threshold", 0)
        elif core == "latch":
            cell.latch_downstream_mask = dm(cfg.get("downstream_mask", 0))
            cell.latch_set_dir = dm(cfg.get("set_dir", 0))
            cell.latch_clear_dir = dm(cfg.get("clear_dir", 0))
            cell.latch_toggle_dir = dm(cfg.get("toggle_dir", 0))
        elif core == "sequencer":
            cell.seq_value_0 = int(cfg.get("VALUE_0", 0)) & 0xFF
            cell.seq_value_1 = int(cfg.get("VALUE_1", 0)) & 0xFF
            cell.seq_value_2 = int(cfg.get("VALUE_2", 0)) & 0xFF
            cell.seq_value_3 = int(cfg.get("VALUE_3", 0)) & 0xFF
            cell.seq_sequence_len_m1 = int(cfg.get("SEQUENCE_LEN", 0)) & 0x3
            cell.seq_downstream_mask = dm(cfg.get("downstream_mask", 0))
            cell.seq_index = 0
            cell.seq_out_buffer = cell.seq_value_0   # value_for_index(0), same real reset-time snapshot the RTL takes
            cell.seq_data_valid = True                # live from the first cycle after config, matching the real RTL exactly
        elif core == "branch":
            cell.br_upstream_dir = single_dir(cfg.get("upstream_dir", 0))
            cell.br_value_source_low = bool(cfg.get("value_source_low", 0))
            cell.br_value_source_equal = bool(cfg.get("value_source_equal", 0))
            cell.br_value_source_high = bool(cfg.get("value_source_high", 0))
            cell.br_fixed_value_low = int(cfg.get("fixed_value_low", 0)) & 0x7F
            cell.br_fixed_value_equal = int(cfg.get("fixed_value_equal", 0)) & 0x7F
            cell.br_fixed_value_high = int(cfg.get("fixed_value_high", 0)) & 0x7F
            cell.br_emit_low = bool(cfg.get("emit_low", 0))
            cell.br_emit_equal = bool(cfg.get("emit_equal", 0))
            cell.br_emit_high = bool(cfg.get("emit_high", 0))
            cell.br_route_low = dm(cfg.get("route_low", 0))
            cell.br_route_equal = dm(cfg.get("route_equal", 0))
            cell.br_route_high = dm(cfg.get("route_high", 0))
            cell.br_rolling_mode = bool(cfg.get("rolling_mode", 0))
        else:
            raise ValueError(f"unsupported core {core!r} for VM dispatch (reserved core_select, #317)")
        return cell

    # ── pending_ack: proxy to the nano CACell when delegated, else the
    # shared shell field every non-nano core uses. ──
    @property
    def pending_ack(self) -> int:
        return self._nano.pending_ack if self.core == "nano" else self._shell_pending_ack

    @pending_ack.setter
    def pending_ack(self, val: int) -> None:
        if self.core == "nano":
            self._nano.pending_ack = val
        else:
            self._shell_pending_ack = val

    @property
    def downstream_mask(self) -> int:
        return {
            "ram": self.ram_downstream_mask, "adder": self.adder_downstream_mask,
            "accumulator": self.acc_downstream_mask, "comparator": self.cmp_downstream_mask,
            "latch": self.latch_downstream_mask,
        }.get(self.core, 0)

    def deliver(self, arrivals: Dict[int, int], injected: Optional[int] = None
                ) -> Tuple[bool, Optional[Tuple[int, int]]]:
        if self.core == "nano":
            self._nano.freeze_in = self.freeze_in
            return self._nano.deliver(arrivals, injected)
        handler = _CORE_HANDLERS.get(self.core)
        if handler is None:
            raise ValueError(f"unsupported core {self.core!r}")
        return handler.deliver(self, arrivals, injected)

    # ── RAM: ram_cell_v1.v ────────────────────────────────────────────
    def _deliver_ram(self, arrivals, injected):
        if self.ram_fixed_mode:
            # capture_now requires !fixed_mode in the real RTL -- a fixed
            # cell never captures, ever, matching that exactly.
            return (False, None) if (arrivals or injected is not None) else (True, None)
        matched = {d: v for d, v in arrivals.items() if (self.ram_upstream_mask >> _DIR_BIT[d]) & 1}
        if not matched and injected is None:
            return (True, None)
        if self.ram_data_valid:
            return (False, None)  # doubly full
        val = 0
        for v in matched.values():
            val |= v & _MASK32
        if injected is not None:
            val |= injected & _MASK32
        self.ram_data_reg = val
        self.ram_data_valid = True
        return (True, None)

    # ── adder: adder_cell_v1.v -- two-stage A-then-B capture. #521's
    # real extension: subtract_mode computes A-B via the same real
    # two's-complement approach the RTL uses (invert B, add 1) --
    # Python's own arbitrary-precision integers don't need a literal
    # carry-chain trick, just the equivalent arithmetic result, wrapped
    # the same way every other signed result in this VM already is. ──
    def _deliver_adder(self, arrivals, injected):
        matched = {d: v for d, v in arrivals.items() if (self.adder_upstream_mask >> _DIR_BIT[d]) & 1}
        if not matched and injected is None:
            return (True, None)
        val = 0
        for v in matched.values():
            val |= v & _MASK32
        if injected is not None:
            val |= injected & _MASK32
        if not self.adder_a_arrived:
            self.adder_a_reg = val
            self.adder_a_arrived = True
            return (True, None)
        if self.adder_data_valid:
            return (False, None)  # doubly full -- B blocked until prior sum drains
        if self.adder_subtract_mode:
            self.adder_out_buffer = (self.adder_a_reg - val) & _MASK32
        else:
            self.adder_out_buffer = (self.adder_a_reg + val) & _MASK32
        self.adder_data_valid = True
        self.adder_a_arrived = False
        return (True, None)

    # ── accumulator: accumulator_cell_v1.v -- unconditional, never
    # blocked. #515's real extension: step_amount is now the data-
    # driven magnitude (was hardcoded +-1), and pulse_mode turns a real
    # threshold crossing into a genuine reset-after-fire pulse -- the
    # internal total hard-resets to 0 in the SAME event, and the
    # crossing VALUE (not the ongoing total) becomes what pulse mode
    # offers downstream (handled in `_offer_state_accumulator` below). ─
    def _deliver_accumulator(self, arrivals, injected):
        if not arrivals:
            return (True, None)   # injected unsupported (no direction => no op), documented limitation
        capture_inc = any((self.acc_inc_dir >> _DIR_BIT[d]) & 1 for d in arrivals)
        capture_dec = any((self.acc_dec_dir >> _DIR_BIT[d]) & 1 for d in arrivals)
        step = self.acc_step_amount
        delta = step if (capture_inc and not capture_dec) else -step if (capture_dec and not capture_inc) else 0
        if capture_inc or capture_dec:
            next_total = _wrap_signed32(self.acc_total + delta)
            abs_next = -next_total if next_total < 0 else next_total
            threshold_hit = self.acc_pulse_mode and self.acc_threshold != 0 and abs_next >= self.acc_threshold
            if self.acc_pulse_mode and threshold_hit:
                self.acc_total = 0
                self.acc_out_buffer = next_total & _MASK32   # the real crossing value, latched
                self.acc_pulse_pending = True
            else:
                self.acc_total = next_total
        return (True, None)

    # ── comparator: compare_cell_v1.v -- single-arrival, stateless result ─
    def _deliver_comparator(self, arrivals, injected):
        matched = {d: v for d, v in arrivals.items() if (self.cmp_upstream_mask >> _DIR_BIT[d]) & 1}
        if not matched and injected is None:
            return (True, None)
        if self.cmp_data_valid:
            return (False, None)
        val = 0
        for v in matched.values():
            val |= v & _MASK32
        if injected is not None:
            val |= injected & _MASK32
        self.cmp_out_buffer = 1 if _wrap_signed32(val) >= self.cmp_threshold else 0
        self.cmp_data_valid = True
        return (True, None)

    # ── latch: latch_cell_v1.v -- unconditional, never blocked. #522's
    # real extension: a genuine TOGGLE trigger, value not checked
    # (matching accumulator's own inc_dir/dec_dir convention -- toggle
    # has no "value" concept the way set's own real #295 fix needed
    # one). Real priority chain: CLEAR > SET > TOGGLE -- the two
    # idempotent, deterministic operations win over the state-dependent
    # one, extending #279/#284's own established "explicit host action
    # wins" rule rather than inventing a new priority scheme. ──
    def _deliver_latch(self, arrivals, injected):
        if not arrivals:
            return (True, None)   # injected unsupported, same as accumulator
        set_triggered = any(((self.latch_set_dir >> _DIR_BIT[d]) & 1) and (v & 1) for d, v in arrivals.items())
        clear_triggered = any((self.latch_clear_dir >> _DIR_BIT[d]) & 1 for d in arrivals)
        toggle_triggered = any((self.latch_toggle_dir >> _DIR_BIT[d]) & 1 for d in arrivals)
        if clear_triggered:
            self.latch_state = False
        elif set_triggered:
            self.latch_state = True
        elif toggle_triggered:
            self.latch_state = not self.latch_state
        return (True, None)

    # ── branch: branch_cell_v1.v -- held-reference two-phase capture +
    # per-outcome A/C/D table (#500/#504/#497). Real RTL core_select
    # slot since #542 (`unicell_super_v3.v`) -- this dispatch logic
    # itself was already correct from the start (#519), modeling the
    # core's own real behavior directly; only needed a real physical
    # RTL home to no longer be VM-provisional. The RTL's own `consumed`
    # latch (guarding against the SAME held arrival being captured
    # twice across multiple clock cycles) has no analog needed here --
    # this VM's own event-driven abstraction calls deliver() exactly
    # once per real pending delivery per tick (this file's own header),
    # so the hazard `consumed` exists to prevent simply doesn't arise
    # at this abstraction level.
    def _deliver_branch(self, arrivals, injected):
        matched = [d for d in arrivals if d == self.br_upstream_dir]
        if not matched:
            return (True, None)   # nothing on our one real fixed direction
        val = arrivals[matched[0]] & _MASK32
        if not self.br_ref_valid:
            self.br_ref_value = _wrap_signed32(val)
            self.br_ref_valid = True
            return (True, None)
        if self.br_data_valid:
            return (False, None)   # doubly full, matches capture_compare's own !data_valid guard
        signed_val = _wrap_signed32(val)
        if signed_val < self.br_ref_value:
            value_source, fixed_value, emit, route = (
                self.br_value_source_low, self.br_fixed_value_low, self.br_emit_low, self.br_route_low)
        elif signed_val == self.br_ref_value:
            value_source, fixed_value, emit, route = (
                self.br_value_source_equal, self.br_fixed_value_equal, self.br_emit_equal, self.br_route_equal)
        else:
            value_source, fixed_value, emit, route = (
                self.br_value_source_high, self.br_fixed_value_high, self.br_emit_high, self.br_route_high)
        if emit:
            self.br_out_buffer = (fixed_value & 0x7F) if value_source else val
            self.br_active_route = route
            self.br_data_valid = True
        # ROLLING MODE: the just-compared value becomes the new held
        # reference, regardless of whether this outcome emitted --
        # matches #504's own real RTL exactly.
        if self.br_rolling_mode:
            self.br_ref_value = signed_val
        return (True, None)

    # ── sequencer: sequencer_cell_v1.v's own real behavior exactly
    # (points.md #609, closing the SEL_SEQ=6 half of #519's own real
    # asymmetry -- the real RTL had existed since unicell_super_v2.v
    # with no VM dispatch at all). No capture side whatsoever --
    # confirmed directly against the RTL: ack_out is tied low on every
    # direction, "there is nothing to acknowledge." ──
    def _deliver_sequencer(self, arrivals, injected):
        # Real RTL: ack_out is tied low on EVERY direction -- this core
        # never genuinely acks an arrival, matching ram_fixed_mode's own
        # established "nothing to capture -> (False, None) when
        # something arrives" pattern exactly (not a free pass -- a real
        # sender wired into a sequencer would see its own offer never
        # ack, staying pending forever, same as real hardware would).
        if arrivals or injected is not None:
            return (False, None)
        return (True, None)

    def _offer_state_sequencer(self) -> Tuple[int, bool, int]:
        return (self.seq_out_buffer, self.seq_data_valid, self.seq_downstream_mask)

    def _clear_valid_sequencer(self) -> None:
        """Called on drain completion via the same real hook every
        other single-shot core uses -- but a REAL, deliberate
        difference from all of them: this does NOT clear
        seq_data_valid (this core is perpetually live, matching the
        real RTL's `data_valid <= 1'b1` that's never toggled off after
        config). Instead advances to the NEXT value in the real
        config-fixed sequence, wrapping after `seq_sequence_len_m1+1`
        values -- exactly the real RTL's own `offer_just_completed ->
        seq_index <= next_seq_index` transition, reusing the drain-
        detection mechanism this VM already has for a genuinely
        different real purpose (advance, not clear)."""
        self.seq_index = 0 if self.seq_index == self.seq_sequence_len_m1 else self.seq_index + 1
        values = (self.seq_value_0, self.seq_value_1, self.seq_value_2, self.seq_value_3)
        self.seq_out_buffer = values[self.seq_index]

    # ── generic offer-pass state, dispatch by core (points.md #358: via
    # the registry, not an if/elif chain -- see _CORE_HANDLERS below) ──
    def _offer_state(self) -> Tuple[int, bool, int]:
        """(value_to_offer, is_valid, downstream_mask) for the current
        core. Continuously-live cores (accumulator/latch/RAM fixed-mode)
        return is_valid=True forever; single-shot cores return whatever
        their own data_valid register currently holds."""
        handler = _CORE_HANDLERS.get(self.core)
        if handler is None or handler.offer_state is None:
            raise ValueError(f"unsupported core {self.core!r}")
        return handler.offer_state(self)

    def _offer_state_ram(self) -> Tuple[int, bool, int]:
        return (self.ram_data_reg, self.ram_data_valid, self.ram_downstream_mask)

    def _offer_state_adder(self) -> Tuple[int, bool, int]:
        return (self.adder_out_buffer, self.adder_data_valid, self.adder_downstream_mask)

    def _offer_state_comparator(self) -> Tuple[int, bool, int]:
        return (self.cmp_out_buffer, self.cmp_data_valid, self.cmp_downstream_mask)

    def _offer_state_accumulator(self) -> Tuple[int, bool, int]:
        if self.acc_pulse_mode:
            # Pulse mode: only ever offers the latched crossing value,
            # gated on a real discrete pulse_pending flag -- never the
            # ongoing running total. Matches #515's RTL exactly.
            return (self.acc_out_buffer, self.acc_pulse_pending, self.acc_downstream_mask)
        self.acc_out_buffer = self.acc_total & _MASK32   # snapshot refresh, matches RTL's own gating
        return (self.acc_out_buffer, True, self.acc_downstream_mask)

    def _offer_state_latch(self) -> Tuple[int, bool, int]:
        return (1 if self.latch_state else 0, True, self.latch_downstream_mask)

    def _offer_state_branch(self) -> Tuple[int, bool, int]:
        # Unlike every other core, the "downstream" here is br_active_route
        # -- the REAL routed mask decided per-outcome at capture time
        # (#497's own multi-direction fan-out), not a static config field.
        return (self.br_out_buffer, self.br_data_valid, self.br_active_route)

    def is_continuously_live(self) -> bool:
        if self.core == "ram" and self.ram_fixed_mode:
            return True   # dynamic per-instance case, not a static per-core-type property
        if self.core == "accumulator" and self.acc_pulse_mode:
            return False   # #515: pulse mode behaves like a genuine single-shot
                            # core -- only the discrete crossing pulse is ever
                            # offered, needing real drain detection to clear
                            # pulse_pending, unlike static mode's always-live default
        handler = _CORE_HANDLERS.get(self.core)
        return handler.continuously_live if handler is not None else False

    def clear_valid_on_drain(self) -> None:
        """Called only for single-shot cores the instant their offer
        fully drains (pending_ack nonzero -> 0) -- matches the real RTL's
        `offer_draining` clearing `data_valid`, freeing the cell to
        capture again."""
        handler = _CORE_HANDLERS.get(self.core)
        if handler is not None and handler.clear_valid is not None:
            handler.clear_valid(self)

    def _clear_valid_ram(self) -> None:
        self.ram_data_valid = False

    def _clear_valid_adder(self) -> None:
        self.adder_data_valid = False

    def _clear_valid_comparator(self) -> None:
        self.cmp_data_valid = False

    def _clear_valid_accumulator(self) -> None:
        # Only ever called in pulse mode (is_continuously_live() returns
        # True for static mode, so Pass 3 never reaches this then) --
        # clears the discrete pulse flag on drain, matching #515's RTL
        # "pulse_consumed" clearing pulse_pending exactly.
        self.acc_pulse_pending = False

    def _clear_valid_branch(self) -> None:
        self.br_data_valid = False

    # ── Real, full runtime checkpoint (points.md #483's own real,
    # mixed-grid extension of #480-482's already-proven DspWrapperCell
    # checkpoint) -- this class has real, deliberate reasons to use
    # dataclass introspection here rather than #480's own hand-typed
    # field-by-field dict: SuperCell carries ~30 real fields across 6
    # cores (every core's own register set is always physically
    # present, matching the real RTL's own "all 6 instantiated"
    # design, #159's own docstring), so a hand-typed list is real,
    # ongoing field-drift risk every time a core gains a field -- the
    # exact "generic over hand-typed" lesson this codebase already
    # committed to for ICM field tables (#356's own generic_field_
    # codec_v1.py, proven bit-for-bit equivalent to icm_v3.py's
    # hand-typed one). `_nano` is the one real special case: it holds
    # a NESTED dataclass (`CACell`), not a plain value, so it gets its
    # own real nested asdict()/reconstruction rather than being
    # swept into the generic loop. ──
    def checkpoint(self) -> dict:
        snap = {}
        for f in dataclasses.fields(self):
            if f.name == "_nano":
                continue
            snap[f.name] = getattr(self, f.name)
        snap["_nano"] = dataclasses.asdict(self._nano) if self._nano is not None else None
        return snap

    @staticmethod
    def restore(snapshot: dict) -> "SuperCell":
        cell = SuperCell(
            row=snapshot["row"], col=snapshot["col"], core=snapshot["core"],
            addon_config=snapshot.get("addon_config", {}),
        )
        for f in dataclasses.fields(cell):
            if f.name in ("row", "col", "core", "addon_config", "_nano"):
                continue
            setattr(cell, f.name, snapshot[f.name])
        nano_state = snapshot.get("_nano")
        cell._nano = CACell(**nano_state) if nano_state is not None else None
        return cell


# ── Core handler registration (`points.md #358`) -- the 5 non-nano
# cores' own real behavior, registered once here at module load time.
# A future core type registers the same way, without ever touching
# SuperCell's own deliver()/_offer_state()/is_continuously_live()/
# clear_valid_on_drain() dispatch methods above. ──────────────────────

register_core_handler("ram", CoreHandler(
    deliver=SuperCell._deliver_ram, offer_state=SuperCell._offer_state_ram,
    continuously_live=False, clear_valid=SuperCell._clear_valid_ram))
register_core_handler("adder", CoreHandler(
    deliver=SuperCell._deliver_adder, offer_state=SuperCell._offer_state_adder,
    continuously_live=False, clear_valid=SuperCell._clear_valid_adder))
register_core_handler("accumulator", CoreHandler(
    deliver=SuperCell._deliver_accumulator, offer_state=SuperCell._offer_state_accumulator,
    continuously_live=True, clear_valid=SuperCell._clear_valid_accumulator))
register_core_handler("comparator", CoreHandler(
    deliver=SuperCell._deliver_comparator, offer_state=SuperCell._offer_state_comparator,
    continuously_live=False, clear_valid=SuperCell._clear_valid_comparator))
register_core_handler("latch", CoreHandler(
    deliver=SuperCell._deliver_latch, offer_state=SuperCell._offer_state_latch,
    continuously_live=True))
register_core_handler("sequencer", CoreHandler(
    deliver=SuperCell._deliver_sequencer, offer_state=SuperCell._offer_state_sequencer,
    # points.md #609: continuously_live=False is a REAL, deliberate
    # choice, not the "single-shot" label it looks like -- this core
    # is genuinely always valid (never actually drained/reclosed), but
    # it needs Pass 3's own drain-detection to fire every time so
    # _clear_valid_sequencer's real advance-to-next-value step runs at
    # the correct moment. Registering continuously_live=True instead
    # would make Pass 3 skip this core entirely, and the sequence
    # would never advance at all.
    continuously_live=False, clear_valid=SuperCell._clear_valid_sequencer))
register_core_handler("branch", CoreHandler(
    deliver=SuperCell._deliver_branch, offer_state=SuperCell._offer_state_branch,
    continuously_live=False, clear_valid=SuperCell._clear_valid_branch))


class SuperGrid:
    """A grid of `SuperCell`s wired to fixed physical neighbors, same
    "no addressing, no shared bus" model as `CAGrid` -- generalized to
    heterogeneous core types via `icm_v3.IcmV3Record.core`."""

    def __init__(self, records: List["v3.IcmV3Record"]):
        self.cells: Dict[Tuple[int, int], SuperCell] = {
            (r.row, r.col): SuperCell.from_record(r) for r in records
        }
        self._pending: Dict[Tuple[int, int], List[Tuple[Optional[Tuple[int, int]], Optional[int], int]]] = {}
        self.tick_count = 0

    @staticmethod
    def from_icm(icm: "v3.IcmV3File") -> "SuperGrid":
        return SuperGrid(icm.records)

    def neighbor_pos(self, row: int, col: int, direction: int) -> Optional[Tuple[int, int]]:
        dr, dc = {N: (-1, 0), S: (1, 0), E: (0, 1), W: (0, -1)}[direction]
        pos = (row + dr, col + dc)
        return pos if pos in self.cells else None

    def inject(self, row: int, col: int, value: int) -> None:
        self._pending.setdefault((row, col), []).append((None, None, value))

    def confirm_read(self, row: int, col: int) -> None:
        """Same terminal-output contract as CAGrid's own confirm_read --
        needed for nano cells with a zero-target fire; non-nano cores
        always route somewhere or don't offer at all, so this mainly
        matters for a nano cell delegated here."""
        cell = self.cells[(row, col)]
        cell.pending_ack = 0
        if cell.core == "nano":
            cell._nano._needs_confirm = False

    def tick(self) -> Dict[Tuple[int, int], bool]:
        active: Dict[Tuple[int, int], bool] = {}
        outgoing: List[Tuple[Tuple[int, int], Tuple[int, int], int, int]] = []
        retry: Dict[Tuple[int, int], List[Tuple[Optional[Tuple[int, int]], Optional[int], int]]] = {}

        pre_tick_pending = {pos: c.pending_ack for pos, c in self.cells.items()}

        current = self._pending
        self._pending = {}

        # ── Pass 1: normal event-driven delivery, same shape as
        # CAGrid.tick()'s own main pass. ──
        for pos, events in current.items():
            cell = self.cells[pos]
            active[pos] = True

            by_dir: Dict[int, Tuple[Optional[Tuple[int, int]], int]] = {}
            injected_val = None
            injected_origin = None
            for origin, from_dir, value in events:
                if from_dir is None:
                    injected_val = (injected_val or 0) | (value & _MASK32)
                    injected_origin = origin
                else:
                    by_dir[from_dir] = (origin, value & _MASK32)

            real_dirs = {d: v for d, (_o, v) in by_dir.items()}
            accepted, result = cell.deliver(real_dirs, injected=injected_val)

            if not accepted:
                for d, (origin, value) in by_dir.items():
                    retry.setdefault(pos, []).append((origin, d, value))
                if injected_val is not None:
                    retry.setdefault(pos, []).append((injected_origin, None, injected_val))
                continue

            for d, (origin, _v) in by_dir.items():
                if origin is not None:
                    opp_bit = _DIR_BIT[_OPPOSITE[d]]
                    self.cells[origin].pending_ack &= ~(1 << opp_bit) & _MASK4

            if result is not None:
                mask, out_value = result
                for direction in _DIRS:
                    if (mask >> _DIR_BIT[direction]) & 1:
                        nb = self.neighbor_pos(pos[0], pos[1], direction)
                        if nb is not None:
                            outgoing.append((nb, pos, direction, out_value))

        for pos, events in retry.items():
            self._pending.setdefault(pos, []).extend(events)

        # ── Pass 2: nano's own internal-feedback continuous pass --
        # unaffected by this file, since ICM v3's nano exposure never
        # sets hold_in/fb_internal_in, but kept for parity/future-proofing
        # if that scope ever widens. ──
        for pos, cell in self.cells.items():
            if cell.core == "nano" and cell._nano.hold_in and cell._nano.fb_internal_in \
                    and not cell._nano.effective_freeze:
                cell._nano.internal_feedback_step()
                active[pos] = True

        # ── Pass 3: drain detection for single-shot non-nano cores --
        # the instant a full drain is detected (pending_ack nonzero ->
        # 0 this tick, not from a brand-new same-tick offer), clear
        # data_valid, matching the real RTL's `offer_draining` exactly. ──
        for pos, cell in self.cells.items():
            if cell.core == "nano" or cell.is_continuously_live():
                continue
            was = pre_tick_pending.get(pos, 0)
            if was != 0 and cell.pending_ack == 0:
                cell.clear_valid_on_drain()
                active[pos] = True

        # ── Pass 4: the generic offer pass -- every non-nano cell with
        # pending_ack==0 and something valid to offer re-arms and fires,
        # whether or not anything was captured this same tick. ──
        for pos, cell in self.cells.items():
            if cell.core == "nano" or cell.pending_ack != 0:
                continue
            value, valid, downstream = cell._offer_state()
            if not valid or downstream == 0:
                continue
            value = apply_addons(value, cell.addon_config)
            cell.pending_ack = downstream & _MASK4
            active[pos] = True
            for direction in _DIRS:
                if (downstream >> _DIR_BIT[direction]) & 1:
                    nb = self.neighbor_pos(pos[0], pos[1], direction)
                    if nb is not None:
                        outgoing.append((nb, pos, direction, value))

        for nb, origin, out_dir, value in outgoing:
            arrive_from = _OPPOSITE[out_dir]
            self._pending.setdefault(nb, []).append((origin, arrive_from, value))

        self.tick_count += 1
        return active

    def run_to_quiescence(self, max_ticks: int = 10000, stop_when_no_pending: bool = True) -> int:
        """Run until nothing is pending. NOTE: a grid containing any
        continuously-live core (accumulator/latch/RAM fixed-mode) with a
        real downstream target NEVER quiesces by construction (it's a
        heartbeat, on purpose) -- calling this on such a grid will raise
        TimeoutError, which is the correct, honest behavior, not a bug to
        work around. Use `tick()` directly for scenarios involving those
        cores, same guidance `CAGrid`'s own docstring already gives for
        nano's internal-feedback mode.

        REAL BUG FOUND AND FIXED (`points.md #359`): the offer pass that
        makes a continuously-live core's grid genuinely non-quiescent
        only runs INSIDE `tick()` -- so a grid that had never been
        ticked even once (`_pending` still legitimately empty at
        construction, before any injection) would have this method
        check `_pending` BEFORE the first tick ever ran, see it empty,
        and return `0` immediately -- silently violating the very
        promise this docstring makes, for exactly the case it claims to
        guard against. Confirmed as a real, reproducible bug (not
        assumed) via `nano/vm_ai_port_v1.py`'s own end-to-end testing --
        the pre-existing test for this method's own heartbeat guarantee
        always called `inject()` first, which populates `_pending`
        directly and happened to mask the gap. Fixed by always running
        at least one tick before the first check (do-while, not
        while-do) -- a grid with genuinely nothing to do still correctly
        reports quiescence, just after one real tick rather than zero."""
        ticks = 0
        while ticks < max_ticks:
            self.tick()
            ticks += 1
            if not self._pending:
                return ticks
        if self._pending:
            raise TimeoutError(f"did not quiesce within {max_ticks} ticks")
        return ticks
