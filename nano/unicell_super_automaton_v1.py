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
    latch_state: bool = False

    freeze_in: bool = False
    _shell_pending_ack: int = 0   # non-nano cores' shared pending_ack mask

    @staticmethod
    def from_record(rec: "v3.IcmV3Record") -> "SuperCell":
        core = rec.core
        cfg = rec.core_config
        addon = rec.addon_config
        cell = SuperCell(row=rec.row, col=rec.col, core=core, addon_config=addon)

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

        if core == "nano":
            cell._nano = CACell(
                row=rec.row, col=rec.col,
                topology=cfg.get("topology", 0),
                start_flag=bool(cfg.get("ready", 0)),
                routing_mask=cfg.get("routing_mask", 0),
                cardinal_edge=cfg.get("cardinal_edge", 0),
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
        elif core == "accumulator":
            cell.acc_downstream_mask = dm(cfg.get("downstream_mask", 0))
            cell.acc_inc_dir = dm(cfg.get("inc_dir", 0))
            cell.acc_dec_dir = dm(cfg.get("dec_dir", 0))
        elif core == "comparator":
            cell.cmp_downstream_mask = dm(cfg.get("downstream_mask", 0))
            cell.cmp_upstream_mask = dm(cfg.get("upstream_mask", 0))
            cell.cmp_threshold = cfg.get("threshold", 0)
        elif core == "latch":
            cell.latch_downstream_mask = dm(cfg.get("downstream_mask", 0))
            cell.latch_set_dir = dm(cfg.get("set_dir", 0))
            cell.latch_clear_dir = dm(cfg.get("clear_dir", 0))
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

    # ── adder: adder_cell_v1.v -- two-stage A-then-B capture ──────────
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
        self.adder_out_buffer = (self.adder_a_reg + val) & _MASK32
        self.adder_data_valid = True
        self.adder_a_arrived = False
        return (True, None)

    # ── accumulator: accumulator_cell_v1.v -- unconditional, never blocked ─
    def _deliver_accumulator(self, arrivals, injected):
        if not arrivals:
            return (True, None)   # injected unsupported (no direction => no op), documented limitation
        capture_inc = any((self.acc_inc_dir >> _DIR_BIT[d]) & 1 for d in arrivals)
        capture_dec = any((self.acc_dec_dir >> _DIR_BIT[d]) & 1 for d in arrivals)
        delta = 1 if (capture_inc and not capture_dec) else -1 if (capture_dec and not capture_inc) else 0
        if delta:
            self.acc_total = _wrap_signed32(self.acc_total + delta)
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

    # ── latch: latch_cell_v1.v -- unconditional, never blocked, CLEAR wins ─
    def _deliver_latch(self, arrivals, injected):
        if not arrivals:
            return (True, None)   # injected unsupported, same as accumulator
        # #295's own real bug fix: only an arrival that actually CARRIES a
        # 1 on the value triggers a set -- a genuine 0 reading must not
        # re-latch.
        set_triggered = any(((self.latch_set_dir >> _DIR_BIT[d]) & 1) and (v & 1) for d, v in arrivals.items())
        clear_triggered = any((self.latch_clear_dir >> _DIR_BIT[d]) & 1 for d in arrivals)
        if clear_triggered:
            self.latch_state = False
        elif set_triggered:
            self.latch_state = True
        return (True, None)

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
        self.acc_out_buffer = self.acc_total & _MASK32   # snapshot refresh, matches RTL's own gating
        return (self.acc_out_buffer, True, self.acc_downstream_mask)

    def _offer_state_latch(self) -> Tuple[int, bool, int]:
        return (1 if self.latch_state else 0, True, self.latch_downstream_mask)

    def is_continuously_live(self) -> bool:
        if self.core == "ram" and self.ram_fixed_mode:
            return True   # dynamic per-instance case, not a static per-core-type property
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
    continuously_live=True))
register_core_handler("comparator", CoreHandler(
    deliver=SuperCell._deliver_comparator, offer_state=SuperCell._offer_state_comparator,
    continuously_live=False, clear_valid=SuperCell._clear_valid_comparator))
register_core_handler("latch", CoreHandler(
    deliver=SuperCell._deliver_latch, offer_state=SuperCell._offer_state_latch,
    continuously_live=True))


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
