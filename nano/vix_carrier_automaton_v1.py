"""
vix_carrier_automaton_v1.py — points.md #654/#655: the VM's own real
9-core VixCarrier extension, resolving the naming decision made in
`#654` BEFORE this file existed: `VixCarrierCell`/`VixCarrierGrid`, not
`SuperCell`/`SuperGrid` (those remain untouched, still modeling the OLD
core lineage exactly as before -- `unicell_super_v1.v`-`v8.v`).

Real, deliberate reuse, not a parallel reimplementation: `VixCarrierCell`
genuinely SUBCLASSES `SuperCell` -- the 8 already-modeled core types
(nano/adder/ram/compare/branch/accumulator/latch/sequencer) keep their
own real, already-proven dispatch logic completely unchanged, inherited
for free. `SuperCell.from_record()` was made a real `@classmethod`
(`cls(...)`, not a hardcoded `SuperCell(...)`) precisely so a subclass
constructs genuine INSTANCES OF ITSELF, not disguised `SuperCell`s --
`type(cell).__name__` genuinely reads `VixCarrierCell`, not just the
import path, the actual point of resolving the naming question in
`#654` rather than a cosmetic re-export alias.

The ONLY genuinely NEW mechanism here is the 9th core, `command` --
`command_cell_v4.v`'s own real state machine (points.md `#628`/`#641`-
`#645`), confirmed field-by-field against that RTL directly before
writing this, not assumed from memory:
  - TRIGGER mode (`mode=0`): a real, symmetric toggle -- every real
    arrival is acked unconditionally (a pure passive observer), but the
    freeze level only flips on a MATCHING arrival (`watch_val[23:20]
    == toggle_pattern`). The toggled level drives `freeze_out` toward
    whichever real neighbor `drive_dir` names.
  - PROGRAMMER mode (`mode=1`): starts relaying on a plain first
    arrival while idle, holds freeze on the target for the WHOLE
    relay, and only releases it once a word matching `toggle_pattern`
    (config-fixed to the target's own real `PROG_ID_COMPLETE`) has
    been relayed and confirmed.

Real, honest, stated scope limit, not silently glossed over: the VM's
own live PROG_ID reprogramming channel (`SuperCell.program_word()`)
only exists for `core="nano"` today (`SuperCell.program_in`'s own
setter explicitly raises for every other core type) -- so PROGRAMMER
mode's own real relay-and-apply behavior is only genuinely exercised
here against a real nano target. Extending live reprogramming to the
other 7 core types is real, separate, later work, not attempted here.

Real, deliberate VM-level simplification, stated plainly: the real
RTL's own multi-cycle prog_data_out/prog_arrived_out/prog_ack_in
handshake is collapsed here into one instantaneous logical transaction
per word (assert program_in, apply the one PROG_ID word, and -- only
on the real PROG_ID_COMPLETE word -- drop program_in) -- the VM already
abstracts away real signal-level timing everywhere else (e.g. cfg_valid's
own real multi-cycle SUPER_LATCH commit is a single Python assignment),
and this is the same real category of abstraction, not a new one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import icm_v3 as v3
from unicell_super_automaton_v1 import (
    SuperCell, SuperGrid, CoreHandler, register_core_handler, N, S, E, W,
)

# Real, RTL-confirmed constants (command_cell_v4.v's own real PROG_ID
# table for its OWN receive-side config channel -- distinct from the
# watched/relayed word's own PROG_ID, which is the TARGET's, not this
# cell's own).
PROG_ID_MODE = 0
PROG_ID_POLARITY = 1
PROG_ID_DRIVE_DIR = 2
PROG_ID_TOGGLE_PATTERN = 3
PROG_ID_COMPLETE = 7   # shared convention -- matches nano's own PROG_ID_COMPLETE

_DIR_FROM_CODE = {0: N, 1: S, 2: E, 3: W}


@dataclass
class VixCarrierCell(SuperCell):
    """Real subclass, not an alias -- see module docstring. Adds the
    command core's own real fields; every other core type's own fields
    (already on `SuperCell`) are inherited unchanged."""
    command_mode: bool = False
    command_polarity: bool = False
    command_drive_dir: int = 0
    command_toggle_pattern: int = 0
    command_armed: bool = False
    command_freeze_state: bool = False
    command_active_r: bool = False
    command_held_word: int = 0
    command_word_pending: bool = False
    #: real, second-pass-resolved reference to the actual neighbor cell
    #: object `drive_dir` names -- see `VixCarrierGrid._wire_command_targets()`.
    #: A direct Python object reference, not a simulated wire -- the VM
    #: has no need to model real inter-cell wiring delay for this.
    command_target: Optional["VixCarrierCell"] = None

    @classmethod
    def from_record(cls, rec: "v3.IcmV3Record") -> "VixCarrierCell":
        """Real, deliberate override, kept entirely within this file --
        for the 8 already-modeled core types, reuses `SuperCell.
        from_record()`'s own real dispatch body DIRECTLY (via
        `.__func__`, with `cls=VixCarrierCell` so it genuinely
        constructs an instance of THIS class, `#654`'s own real point).
        `core="command"` is built directly here instead -- the parent's
        own dispatch body has a real, deliberate catch-all `raise` for
        any core it doesn't recognize (`#317`), so it's never called
        for command at all, keeping every real v4-generation-specific
        concern in this file and the old lineage's own file completely
        unaware of it."""
        if rec.core == "command":
            cfg = rec.core_config
            cell = cls(row=rec.row, col=rec.col, core="command",
                       addon_config=rec.addon_config, cell_id=rec.cell_id)
            cell.command_mode = bool(cfg.get("mode", 0))
            cell.command_polarity = bool(cfg.get("polarity", 0))
            cell.command_drive_dir = int(cfg.get("drive_dir", 0))
            cell.command_toggle_pattern = int(cfg.get("toggle_pattern", 0))
            # Real, RTL-confirmed reset behavior (command_cell_v4.v's
            # own real cfg_valid branch): armed<=1, freeze_state<=
            # !polarity, active_r/held_word/word_pending all clear.
            cell.command_armed = True
            cell.command_freeze_state = not cell.command_polarity
            cell.command_active_r = False
            cell.command_held_word = 0
            cell.command_word_pending = False
            return cell
        return SuperCell.from_record.__func__(cls, rec)


def _watch_select(arrivals: Dict[int, int], injected: Optional[int]):
    """Real, direction-agnostic recognition, priority N>S>E>W on
    simultaneous arrival -- matching `command_cell_v4.v`'s own real
    `watch_sel_n`/`watch_sel_s`/`watch_sel_e`/`watch_sel_w` exactly."""
    for d in (N, S, E, W):
        if d in arrivals:
            return arrivals[d]
    if injected is not None:
        return injected
    return None


def _deliver_command(self: VixCarrierCell, arrivals, injected):
    watch_val = _watch_select(arrivals, injected)
    watch_any_arrived = watch_val is not None
    effective_freeze = self.freeze_in
    effective_armed = self.command_armed

    if not watch_any_arrived:
        return (False, None)

    if self.command_mode:
        watch_capture_now = (not self.command_word_pending) and (not effective_freeze) and effective_armed
    else:
        watch_capture_now = (not effective_freeze) and effective_armed

    if not watch_capture_now:
        # Real, RTL-matching behavior: trigger mode acks (consumes)
        # every real arrival unconditionally once armed and unfrozen --
        # a pure passive observer that never blocks the buffer's own
        # real offer. Programmer mode only acks when ready to capture
        # (ordinary "consume when ready" semantics). Either way, if
        # `watch_capture_now` is false here, this arrival is genuinely
        # not consumed -- matching the real RTL's own `!program_in`/
        # armed/freeze gating exactly.
        return (False, None)

    toggle_match = ((watch_val >> 20) & 0xF) == self.command_toggle_pattern

    if not self.command_mode:
        # ── TRIGGER mode: genuine symmetric toggle, only on a real match. ──
        if toggle_match:
            self.command_freeze_state = not self.command_freeze_state
            self._propagate_freeze(self.command_freeze_state)
    else:
        # ── PROGRAMMER mode: start relaying on a plain first arrival
        # while idle -- freeze the target for the WHOLE relay. ──
        self.command_held_word = watch_val
        self.command_word_pending = True
        self.command_active_r = True
        self._propagate_freeze(True)
        self._relay_word(watch_val, toggle_match)

    return (True, None)


def _propagate_freeze(self: VixCarrierCell, level: bool) -> None:
    """Real, direct Python object reference, standing in for the real
    RTL's own physical freeze_out wire -- see module docstring.

    Points.md #656: simplified -- freeze-gating now happens uniformly
    at `SuperCell.deliver()`'s own real dispatch point (the VM's own
    "shell" equivalent, matching the real RTL's own shell wiring
    exactly), covering all 9 core types from ONE place. No core-
    specific special-casing needed here anymore; setting the outer
    `freeze_in` field alone is now sufficient for every real target
    type, not just nano."""
    if self.command_target is not None:
        self.command_target.freeze_in = level


def _relay_word(self: VixCarrierCell, word: int, toggle_match: bool) -> None:
    """Real, deliberate VM-level simplification of the real RTL's own
    multi-cycle prog_data_out/prog_arrived_out/prog_ack_in handshake --
    see module docstring. Only genuinely exercised against a real nano
    target today (`SuperCell.program_word()`'s own real, stated scope).

    Points.md #657: polymorphic over the real target's own real shape
    -- a `VixCarrierSlot` (see its own class docstring) gets the raw,
    un-split word directly, letting IT decide whether this is the
    real, insisted-upon core-select word or an ordinary field tweak;
    a plain, fixed-type cell keeps the original, simpler prog_id/
    prog_word split. Command mode itself stays unaware of which shape
    it's talking to either way -- a genuinely unaware, faithful relay,
    exactly as designed."""
    target = self.command_target
    if target is None:
        self.command_word_pending = False
        if toggle_match:
            self.command_active_r = False
            self._propagate_freeze(False)
        return

    if isinstance(target, VixCarrierSlot):
        if not target._prog_in_active:
            target.begin_programming()
        target.relay_word(word)
        self.command_word_pending = False
        if toggle_match:
            target.end_programming()
            self.command_active_r = False
            self._propagate_freeze(False)
        return

    if target.core != "nano":
        raise NotImplementedError(
            f"command cell's own programmer-mode relay only works against a real "
            f"nano target today -- {target.core!r} has no live PROG_ID reprogramming "
            f"modeled yet (SuperCell.program_word()'s own real, stated scope, #654) -- "
            f"real, separate, later work, not silently skipped here"
        )
    prog_id = (word >> 20) & 0x7
    prog_word = word & 0xFFFFF
    target.program_in = True
    target.program_word(prog_id, prog_word)
    self.command_word_pending = False
    if toggle_match:
        target.program_in = False
        self.command_active_r = False
        self._propagate_freeze(False)


def _offer_state_command(self: VixCarrierCell):
    return (0, False, 0)   # command has no ordinary cardinal data_out/fire -- see module docstring


def _clear_valid_command(self: VixCarrierCell) -> None:
    pass


VixCarrierCell._propagate_freeze = _propagate_freeze
VixCarrierCell._relay_word = _relay_word

register_core_handler("command", CoreHandler(
    deliver=_deliver_command, offer_state=_offer_state_command, clear_valid=_clear_valid_command,
))


class VixCarrierGrid(SuperGrid):
    """Real subclass, not an alias -- see module docstring. Builds real
    `VixCarrierCell` instances (via the now-classmethod `from_record()`,
    `#654`), then real, second-pass-resolves every command cell's own
    `command_target` reference to whichever real neighbor `drive_dir`
    names -- the SAME real "multi-pass grid wiring" convention already
    established elsewhere in this VM (e.g. `SuperGrid`'s own nano
    internal-feedback pass)."""

    def __init__(self, records: List["v3.IcmV3Record"]):
        self.cells: Dict[Tuple[int, int], VixCarrierCell] = {
            (r.row, r.col): VixCarrierCell.from_record(r) for r in records
        }
        self._pending: Dict[Tuple[int, int], List[Tuple[Optional[Tuple[int, int]], Optional[int], int]]] = {}
        self.tick_count = 0
        self._wire_command_targets()

    def _wire_command_targets(self) -> None:
        for (row, col), cell in self.cells.items():
            if cell.core != "command":
                continue
            direction = _DIR_FROM_CODE.get(cell.command_drive_dir)
            if direction is None:
                continue
            target_pos = self.neighbor_pos(row, col, direction)
            cell.command_target = self.cells.get(target_pos) if target_pos else None
            # Real, necessary initial propagation -- the real RTL's own
            # freeze_out is a continuous, combinational signal (always
            # reflecting the current state), not something that only
            # updates on an arrival event. Confirmed directly: without
            # this, a fresh trigger-mode cell with polarity=0 (rest
            # frozen) left its own real target's freeze_in at its
            # Python-level default (False) until the first real toggle,
            # not the real, immediate "start frozen" behavior.
            cell._propagate_freeze(
                cell.command_active_r if cell.command_mode else cell.command_freeze_state
            )


_ALL_CORE_NAMES = ("nano", "adder", "ram", "comparator", "branch",
                   "accumulator", "latch", "sequencer", "command")
_SEL_FROM_INDEX = {i: name for i, name in enumerate(_ALL_CORE_NAMES)}
_INDEX_FROM_SEL = {name: i for i, name in _SEL_FROM_INDEX.items()}


def _blank_core(row: int, col: int, core: str) -> VixCarrierCell:
    """A freshly-reset, blank-configured cell of the given core type --
    the real, minimal semantic `VixCarrierSlot.boot()` needs (matching
    the real RTL's own `cfg_valid` reset: a whole-word commit clears
    the cell to a known, blank baseline, ready for incremental PROG_ID
    configuration to follow)."""
    rec = v3.IcmV3Record(row=row, col=col, core=core, core_config={}, addon_config={}, cell_id=None)
    return VixCarrierCell.from_record(rec)


@dataclass
class VixCarrierSlot:
    """Points.md #657: the real, genuine VM model of `#647`'s own real
    VIX Carrier -- ONE physical grid position holding all 9 real core
    types SIMULTANEOUSLY (matching the real RTL's own "all 9 physically
    present, mutually exclusive" design exactly, `#647`'s own real
    header), `core_select` switchable at runtime via a real `boot()`
    operation, every other real behavior (deliver/offer/freeze/
    programming) delegated to whichever core is CURRENTLY selected --
    matching the real RTL's own output mux and per-core gating
    (`sel_nano && ...`, `sel_adder && ...`, etc.) exactly, confirmed
    directly against `unicell_vix_carrier_v1.v` before writing this.

    Real, deliberate design answering Alan's own real question and
    follow-up instruction directly: live programming (`program_word`)
    reaches ONLY whichever core is currently selected -- it carries no
    core-selection information of its own, exactly matching the real
    RTL's own `sel_X && program_in` gating (confirmed: no core's own
    `program_in` port includes anything encoding which core it's meant
    for). Rather than inventing a new carrier-level PROG_ID reserved
    value (which would necessarily collide with SOME core's own real,
    existing PROG_ID assignment -- the 3-bit PROG_ID space is genuinely
    shared/reused across all 9 cores' own field tables, so no value is
    ever free), this slot instead treats the FIRST real word of any
    fresh live-programming session specially: a raw core-select value,
    not an ordinary PROG_ID word. Only after that first word does it
    route subsequent words to whichever core it just selected, via the
    ordinary, already-proven PROG_ID mechanism, completely unchanged.
    This "insist core-select first" rule is enforced ENTIRELY here, at
    the receiving slot -- command mode itself (`#655`) stays an
    unaware, faithful relay of whatever real words it's given, in
    order; it never needs to know this convention exists at all."""
    row: int
    col: int
    core_select: str = "nano"
    freeze_in: bool = False
    cell_id: Optional[str] = None
    _cores: Dict[str, VixCarrierCell] = field(default_factory=dict)
    _prog_awaiting_select: bool = field(default=False, init=False)
    _prog_in_active: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not self._cores:
            self._cores = {name: _blank_core(self.row, self.col, name) for name in _ALL_CORE_NAMES}

    @property
    def active(self) -> VixCarrierCell:
        return self._cores[self.core_select]

    def boot(self, core_select: str) -> None:
        """Real, minimal 'whole-word commit' semantic -- matches the
        real RTL's own `cfg_valid`: switches `core_select` and resets
        that core to a clean, blank baseline, ready for incremental
        PROG_ID configuration to follow. Deliberately does NOT accept
        a full config dict here -- this models the real, narrow "first
        word selects the core" step specifically, not a full boot-load;
        ordinary field configuration continues via the SAME real,
        already-proven PROG_ID channel immediately afterward."""
        if core_select not in _ALL_CORE_NAMES:
            raise ValueError(f"unknown core {core_select!r} -- must be one of {_ALL_CORE_NAMES}")
        self.core_select = core_select
        self._cores[core_select] = _blank_core(self.row, self.col, core_select)
        self._cores[core_select].freeze_in = self.freeze_in

    # ── Real programming-channel interception -- see class docstring. ──
    def begin_programming(self) -> None:
        """Real, rising-edge equivalent of `program_in` going high --
        marks the start of a fresh session, so the very next word is
        treated as the real core-select value, not an ordinary PROG_ID
        word."""
        self._prog_in_active = True
        self._prog_awaiting_select = True

    def end_programming(self) -> None:
        # points.md #657: real, necessary fix, found by testing -- the
        # real RTL's own program_in is "a live external wire, top
        # priority" that suspends ordinary captures entirely while
        # asserted (confirmed directly: unicell_automaton_v1.py's own
        # header states this exactly). relay_word() asserts program_in
        # on the currently-active core for every word; without
        # clearing it back here, the target stays permanently stuck
        # "mid-programming" forever after the session ends, silently
        # rejecting every real, ordinary arrival -- confirmed directly
        # by a real infinite-stall reproduction before fixing.
        self.active.program_in = False
        self._prog_in_active = False
        self._prog_awaiting_select = False

    def relay_word(self, word: int) -> None:
        """Real, raw 32-bit word, NOT pre-split into (prog_id, data) --
        this slot decides for itself how to interpret it, unlike a
        plain, fixed-type cell's own `program_word(prog_id, data)`."""
        if not self._prog_in_active:
            raise ValueError("relay_word() called with no active programming session -- "
                              "call begin_programming() first, matching the real RTL's own "
                              "program_in-must-be-asserted-first convention")
        if self._prog_awaiting_select:
            core_select = _SEL_FROM_INDEX.get(word & 0x1F)
            if core_select is None:
                raise ValueError(f"first word of a programming session must be a real, valid "
                                  f"core-select value (0-8), got {word & 0x1F!r}")
            self.boot(core_select)
            self._prog_awaiting_select = False
            return
        prog_id = (word >> 20) & 0x7
        prog_word = word & 0xFFFFF
        self.active.program_in = True
        self.active.program_word(prog_id, prog_word)

    # ── Real duck-typed grid interface -- delegates to whichever core
    # is CURRENTLY selected, matching the real RTL's own output mux and
    # per-core gating exactly. Same real pattern `DspWrapperCell`
    # already established for sitting in the same real grid as ordinary
    # `SuperCell`s without `SuperGrid` itself needing to change. ──
    @property
    def core(self) -> str:
        return self.core_select

    @property
    def _nano(self):
        return self.active._nano

    @property
    def addon_config(self) -> dict:
        return self.active.addon_config

    @property
    def pending_ack(self) -> int:
        return self.active.pending_ack

    @pending_ack.setter
    def pending_ack(self, value: int) -> None:
        self.active.pending_ack = value

    def deliver(self, arrivals, injected=None):
        self.active.freeze_in = self.freeze_in
        return self.active.deliver(arrivals, injected)

    def _offer_state(self):
        return self.active._offer_state()

    def is_continuously_live(self) -> bool:
        return self.active.is_continuously_live()

    def clear_valid_on_drain(self) -> None:
        self.active.clear_valid_on_drain()
