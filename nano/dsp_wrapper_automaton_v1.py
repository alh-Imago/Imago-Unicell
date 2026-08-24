"""
dsp_wrapper_automaton_v1.py — VM dispatch for the DSP wrapper family
(`dsp_arith_wrapper_v1.v`/`dsp_compare_wrapper_v1.v`), the first real
piece of `points.md #479`'s own agreed pipeline ("easier addons to the
VM side" first, no real hardware dependency).

GROUND TRUTH, read directly before writing anything here: the real,
hardware-confirmed RTL (`dsp_arith_wrapper_v1.v`, `#472`) and its real,
confirmed per-operation Intel data (`#469`/`#462`).

REAL, DELIBERATE ARCHITECTURAL CHOICE, not an oversight: this is a
SEPARATE class from `SuperCell`, not a new `core` value inside it.
Matches the real, already-agreed hardware architecture (`#453`/`#474`):
DSP wrappers are dedicated, command-wrapped infrastructure, explicitly
NOT baked into the super carrier shell's own `core_select` mux. Keeping
that same distinction in the VM, even in free mode where real placement
constraints don't apply, avoids creating an inconsistency for a future
mirror mode, which DOES need to honestly reflect that a real card's own
DSP wrappers are placement-anchored, dedicated cells, not just another
core_select option any super carrier cell could become.

REAL IMPROVEMENT OVER THE RTL SIMULATION STUBS, stated plainly: the
real Quartus sim stubs (`tb_stub_alterafpf_*_v1.v`) deliberately do NOT
perform real IEEE-754 arithmetic -- they only reproduce real, confirmed
TIMING, since verifying the RTL's own protocol logic was the point, not
re-implementing a hardware float unit in a testbench. This VM class has
no such constraint -- Python's own `struct` module gives genuine
IEEE-754 single-precision arithmetic directly, so this is actually
MORE correct than the RTL testbenches for the real computed VALUE,
matching this whole VM's own stated design philosophy ("correctness of
protocol, ordering, and computed results, not cycle-for-cycle timing",
see `unicell_super_automaton_v1.py`'s own module docstring).

REAL, HONEST SCOPE: this models real per-operation RESULT correctness
and real two-port capture protocol. It does NOT model the real,
per-operation cycle latency (5/5/4/1/1/0 cycles, #469) -- consistent
with this whole VM's own event-driven, not cycle-accurate, abstraction
level.

The watchdog IS modeled (added below), but honestly re-based: it
counts VM TICKS of inactivity, not real hardware clock cycles. #472's
own real finding (a threshold sized for simulation false-trips
against real JTAG-paced hardware) doesn't disappear just because this
is a VM -- but the PROTECTIVE PURPOSE (catch genuine, sustained
inactivity; never trip on real, ongoing progress) transfers cleanly to
tick-counting even though the specific NUMBER has no real hardware-
cycle meaning. Call `watchdog_tick()` once per real grid tick, after
`grid.tick()` itself -- this is NOT auto-invoked by `SuperGrid.tick()`
(that engine stays completely untouched), it's an explicit, separate
call the driver makes.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from unicell_automaton_v1 import N, S, E, W, _DIRS, _DIR_BIT, _MASK32

# ── Real, confirmed per-operation `n` selector and grouping (Intel's
# own official table, #469) -- reused here as the real, honest source
# of truth for which real operations exist and what class each is. ──
ARITH_OPS = {"ADD": 253, "SUB": 254, "MUL": 252}
COMPARE_OPS = {"GE": 228, "LE": 230, "NEQ": 226}
ALL_OPS = {**ARITH_OPS, **COMPARE_OPS}


def _bits_to_float(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits & _MASK32))[0]


def _float_to_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def compute_real_result(op: str, bits_a: int, bits_b: int) -> int:
    """Real IEEE-754 single-precision arithmetic/comparison, matching
    the real hard/soft-logic IP's own confirmed real per-`n` behavior
    (#469/#472) -- not a placeholder, the genuine computed value."""
    a = _bits_to_float(bits_a)
    b = _bits_to_float(bits_b)
    if op == "ADD":
        return _float_to_bits(a + b)
    if op == "SUB":
        return _float_to_bits(a - b)
    if op == "MUL":
        return _float_to_bits(a * b)
    if op == "GE":
        return 1 if a >= b else 0
    if op == "LE":
        return 1 if a <= b else 0
    if op == "NEQ":
        return 1 if a != b else 0
    raise ValueError(f"unknown DSP wrapper operation {op!r} -- real, confirmed ops are {sorted(ALL_OPS)}")


@dataclass
class DspWrapperCell:
    """One real DSP wrapper instance (`dsp_arith_wrapper_v1.v`/
    `dsp_compare_wrapper_v1.v`) -- a genuine, separate real fabric
    element, NOT a `SuperCell` core. Duck-types the same real interface
    `SuperGrid.tick()` already expects (`deliver()`, `_offer_state()`,
    `is_continuously_live()`, `clear_valid_on_drain()`, `pending_ack`)
    so it can sit in the same real grid as ordinary `SuperCell`s
    without `SuperGrid` itself needing to change."""

    row: int
    col: int
    op: str                          # "ADD" | "SUB" | "MUL" | "GE" | "LE" | "NEQ"
    a_dir: int                       # real cardinal direction operand A arrives from
    b_dir: int                       # real cardinal direction operand B arrives from
    downstream_mask: int = 0
    core: str = field(default="dsp_wrapper", init=False)
    addon_config: dict = field(default_factory=dict)   # DSP wrappers have no real ADDON wrapping in the current architecture -- an empty dict is a correct, honest no-op through SuperGrid's own generic apply_addons() pass, not a workaround

    _latched_a: int = field(default=0, init=False)
    _primed_a: bool = field(default=False, init=False)
    _latched_b: int = field(default=0, init=False)
    _primed_b: bool = field(default=False, init=False)
    _result: int = field(default=0, init=False)
    _result_valid: bool = field(default=False, init=False)
    _shell_pending_ack: int = field(default=0, init=False)

    # ── Real, programmable watchdog (#464's own real design ported
    # here) -- None means disabled, matching the real RTL's own default
    # "max threshold, never trips until configured" behavior. Counts VM
    # TICKS, not real clock cycles -- see this module's own docstring. ──
    watchdog_threshold: Optional[int] = None
    _watchdog_count: int = field(default=0, init=False)
    _watchdog_timeout: bool = field(default=False, init=False)
    _activity_this_tick: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.op not in ALL_OPS:
            raise ValueError(f"DspWrapperCell: unknown op {self.op!r} -- real, confirmed ops are {sorted(ALL_OPS)}")
        if self.a_dir == self.b_dir:
            raise ValueError(
                "DspWrapperCell: a_dir and b_dir must be real, distinct cardinal "
                "directions -- matching the real RTL's own two, genuinely "
                "separate cardinal-style input ports."
            )

    @property
    def pending_ack(self) -> int:
        return self._shell_pending_ack

    @pending_ack.setter
    def pending_ack(self, val: int) -> None:
        self._shell_pending_ack = val

    def deliver(self, arrivals: Dict[int, int], injected: Optional[int] = None
                ) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """Real, honest capture: each operand latches independently off
        its own real, configured direction, whichever arrives first --
        no assumption either side arrives before the other, matching
        the real RTL's own real, patient, event-driven discipline
        (`dsp_arith_wrapper_v1.v`'s own real `ack_out_a`/`ack_out_b`
        logic, `#463`). Gated on `not self._result_valid`, matching the
        real RTL's own `!computing` condition exactly -- a wrapper still
        holding an undrained result does not accept new operands."""
        if not self._result_valid:
            was_primed_a, was_primed_b = self._primed_a, self._primed_b
            if self.a_dir in arrivals and not self._primed_a:
                self._latched_a = arrivals[self.a_dir] & _MASK32
                self._primed_a = True
            if self.b_dir in arrivals and not self._primed_b:
                self._latched_b = arrivals[self.b_dir] & _MASK32
                self._primed_b = True

            # ── Real watchdog activity -- matches the real RTL's own
            # `ack_out_a || ack_out_b` half of its real activity_pulse
            # definition (#465): any genuine NEW capture counts, not
            # just a full pair completing. ──
            if (self._primed_a and not was_primed_a) or (self._primed_b and not was_primed_b):
                self._activity_this_tick = True

            if self._primed_a and self._primed_b:
                self._result = compute_real_result(self.op, self._latched_a, self._latched_b) & _MASK32
                self._result_valid = True

        return (True, None)

    def _offer_state(self) -> Tuple[int, bool, int]:
        return (self._result, self._result_valid, self.downstream_mask)

    def is_continuously_live(self) -> bool:
        return False   # single-shot, same real shape as adder/comparator

    def clear_valid_on_drain(self) -> None:
        """Called the instant a full drain is detected -- frees the
        wrapper to capture a real, new pair of operands, matching the
        real RTL's own `will_fire && ack_in` re-arm exactly (`#463`).
        Also real watchdog activity -- matches the other half of the
        real RTL's own `activity_pulse` definition (#465)."""
        self._result_valid = False
        self._primed_a = False
        self._primed_b = False
        self._activity_this_tick = True

    def configure_watchdog(self, threshold: Optional[int]) -> None:
        """Real, programmable threshold -- matches the real RTL's own
        `cfg_valid`-loaded design (`#464`): reconfiguring also resets
        any in-flight count, same as the real hardware. `threshold=
        None` disables the watchdog (never trips), matching the real
        RTL's own unconfigured-default behavior."""
        self.watchdog_threshold = threshold
        self._watchdog_count = 0
        self._watchdog_timeout = False

    def watchdog_tick(self) -> bool:
        """Call once per real grid tick, after `grid.tick()` itself --
        NOT auto-invoked by `SuperGrid.tick()`, an explicit, separate
        step the driver takes. Advances the real, tick-counted
        watchdog and returns the current timeout state. See this
        module's own docstring for why ticks, not real clock cycles."""
        if self.watchdog_threshold is None:
            self._activity_this_tick = False
            return False
        if self._activity_this_tick:
            self._watchdog_count = 0
            self._watchdog_timeout = False
        else:
            self._watchdog_count += 1
            if self._watchdog_count >= self.watchdog_threshold:
                self._watchdog_timeout = True
        self._activity_this_tick = False
        return self._watchdog_timeout

    @property
    def watchdog_timeout(self) -> bool:
        return self._watchdog_timeout

    @property
    def watchdog_count(self) -> int:
        return self._watchdog_count

    def checkpoint(self) -> dict:
        """Real, full RUNTIME state snapshot -- not just the static
        config used to build a fresh cell (that's what an ICM record
        already covers), but the actual, current, possibly mid-flight
        state: a captured-but-undrained operand, a held result, live
        watchdog count. Real, deliberate scope: this project's own
        established checkpoint principle for the DSP side ("cell
        states yes, DSP states no" -- a real hard-DSP block's own
        internal pipeline state is never meant to be captured, only
        drained-and-settled cell state) doesn't directly apply here in
        the same form, since this VM's own DspWrapperCell has no real
        multi-cycle pipeline to model in the first place (#480's own
        stated scope) -- there is no "mid-computation" state to ever
        NOT capture; a captured operand pair resolves to a result
        within the SAME `deliver()` call. So the honest, real scope
        here is simpler and complete: every field that affects future
        behavior is captured, nothing is silently dropped."""
        return {
            "row": self.row, "col": self.col, "op": self.op,
            "a_dir": self.a_dir, "b_dir": self.b_dir,
            "downstream_mask": self.downstream_mask,
            "latched_a": self._latched_a, "primed_a": self._primed_a,
            "latched_b": self._latched_b, "primed_b": self._primed_b,
            "result": self._result, "result_valid": self._result_valid,
            "shell_pending_ack": self._shell_pending_ack,
            "watchdog_threshold": self.watchdog_threshold,
            "watchdog_count": self._watchdog_count,
            "watchdog_timeout": self._watchdog_timeout,
        }

    @staticmethod
    def restore(snapshot: dict) -> "DspWrapperCell":
        """Real, exact reconstruction from a real checkpoint dict --
        every field restored, not just the static constructor
        arguments, so execution can genuinely resume mid-flight."""
        cell = DspWrapperCell(
            row=snapshot["row"], col=snapshot["col"], op=snapshot["op"],
            a_dir=snapshot["a_dir"], b_dir=snapshot["b_dir"],
            downstream_mask=snapshot["downstream_mask"],
            watchdog_threshold=snapshot.get("watchdog_threshold"),
        )
        cell._latched_a = snapshot["latched_a"]
        cell._primed_a = snapshot["primed_a"]
        cell._latched_b = snapshot["latched_b"]
        cell._primed_b = snapshot["primed_b"]
        cell._result = snapshot["result"]
        cell._result_valid = snapshot["result_valid"]
        cell._shell_pending_ack = snapshot["shell_pending_ack"]
        cell._watchdog_count = snapshot["watchdog_count"]
        cell._watchdog_timeout = snapshot["watchdog_timeout"]
        return cell


def save_model(cells: Dict[Tuple[int, int], "DspWrapperCell"], path: str, name: str = "") -> None:
    """Real, full checkpoint save for a whole model -- a dict of
    `(row, col) -> DspWrapperCell`, matching `SuperGrid.cells`'s own
    real shape so this can extend to a real mixed grid later without a
    format change. Same JSON + hash-verification discipline already
    established for `icm_v3.IcmV3File` (`nano/icm_v3.py`), not a
    different, one-off scheme."""
    import hashlib
    import json as _json

    snapshots = [cell.checkpoint() for cell in cells.values()]
    canon = _json.dumps(snapshots, sort_keys=True, separators=(",", ":"))
    payload = {
        "format": "dsp-wrapper-checkpoint-v1",
        "name": name,
        "cells": snapshots,
        "checkpoint_hash": hashlib.sha256(canon.encode()).hexdigest(),
    }
    with open(path, "w") as f:
        _json.dump(payload, f, indent=2)


def load_model(path: str) -> Dict[Tuple[int, int], "DspWrapperCell"]:
    """Real, exact reconstruction from a real checkpoint file --
    verifies the same real hash `save_model()` computed, matching
    `IcmV3File.load()`'s own real corruption/tamper check (a real,
    reused discipline, not invented fresh here)."""
    import hashlib
    import json as _json

    with open(path) as f:
        payload = _json.load(f)
    if payload.get("format") != "dsp-wrapper-checkpoint-v1":
        raise ValueError(f"not a real dsp-wrapper-checkpoint-v1 file: format={payload.get('format')!r}")

    snapshots = payload["cells"]
    canon = _json.dumps(snapshots, sort_keys=True, separators=(",", ":"))
    real_hash = hashlib.sha256(canon.encode()).hexdigest()
    stored_hash = payload.get("checkpoint_hash")
    if stored_hash is not None and stored_hash != real_hash:
        raise ValueError(
            f"checkpoint_hash mismatch on load: file says {stored_hash}, "
            f"recomputed {real_hash} -- file may be corrupted or hand-edited"
        )

    return {(s["row"], s["col"]): DspWrapperCell.restore(s) for s in snapshots}
