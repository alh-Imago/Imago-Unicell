"""
gpu_array_v1.py — GPU/CPU unified array backend for the Unicell-S VM
(`points.md #216` item 3, `#361`). The last real `#216` item, saved for
this session per Alan's own explicit call.

ARCHITECTURE, deliberately following `gpu_array.py`'s own real
precedent shape rather than inventing a new one -- that file's own
header states its scope honestly: "Stage 1: Replace the inner loop with
an array kernel... Stage 2 (future): persistent GPU state... Stage 3
(future): one GPU per card." Read directly before building anything
here, not assumed. The KEY finding from reading it: even that file's own
"Stage 1" only vectorizes the CELL-SELECTION phase (which cells are
armed and have real input to act on) -- the actual per-cell gate logic
evaluation stays a genuine Python loop, even there. This file matches
that same honest scope for Unicell-S's own "Pass 4" (the generic offer
pass, `unicell_super_automaton_v1.py`'s own `SuperGrid.tick()`): vectorize
WHICH cells are ready to offer (`pending_ack==0` and something valid to
send), keep the actual PER-CORE offer-state computation
(`SuperCell._offer_state()`, dispatched through `#358`'s own registry)
as real Python, reused unchanged, not reimplemented.

WHY NOT FURTHER, stated honestly rather than left implicit: the 6 real
cores' own capture/offer semantics genuinely differ (two-stage capture
for the adder, continuously-live heartbeats for accumulator/latch,
single-shot doubly-full guards for RAM/comparator -- `#337`'s own real
RTL-derived behavior). Reducing THAT to one vectorized array kernel
would mean solving the same "genuinely generic, data-driven BEHAVIOR"
problem `#358`'s own docstring already flagged as a separate, much
bigger undertaking (a real hardware-behavior description language) --
not attempted here, same honest boundary carried forward.

REAL, HONEST TESTING LIMIT: this sandbox has no CUDA-capable hardware
(confirmed directly -- `nvidia-smi` absent, `cupy` not installed).
Exactly `gpu_array.py`'s own documented fallback situation. The
NumPy/CPU path is real, tested, and correct; the CuPy/GPU path's own
CODE follows the identical pattern and SHOULD work on real hardware
(`cp.asnumpy()`/array ops mirror NumPy's own API deliberately), but is
genuinely UNVERIFIED here -- stated plainly, not glossed over.

KEPT ADDITIVE ON PURPOSE: nothing in `SuperGrid.tick()` itself is
changed by this file. `#337`'s own already-extensively-tested offer
pass stays exactly as it was; this module provides a real, separately
tested, equivalent vectorized computation of the SAME readiness check,
proven to produce identical results, that COULD be wired into `tick()`
later as a real "Stage 2" -- not done here, to avoid risking the VM's
own proven correctness for a capability with no measurable benefit yet
at this project's current (small) grid sizes.
"""

from __future__ import annotations

from typing import List, Tuple


def _detect_backend():
    """Auto-detect the best available array backend -- CuPy on a real
    CUDA device, NumPy otherwise. Mirrors `gpu_array.py`'s own real
    detection logic exactly (same fallback chain, same reasoning), not
    reinvented."""
    try:
        import cupy as cp
        if cp.cuda.is_available():
            device = cp.cuda.Device(0)
            props = cp.cuda.runtime.getDeviceProperties(device.id)
            name = props["name"].decode() if isinstance(props["name"], bytes) else str(props["name"])
            return cp, name, True
    except ImportError:
        pass
    import numpy as np
    return np, "CPU (NumPy)", False


_xp, DEVICE_NAME, HAS_GPU = _detect_backend()


def compute_ready_mask(pending_ack: "list[int]", valid: "list[bool]"):
    """The one real vectorizable operation in `SuperGrid.tick()`'s own
    Pass 4: `ready = (pending_ack == 0) & valid`. Pure, backend-agnostic
    (works identically on NumPy or CuPy arrays) -- the actual thing
    `#361` set out to vectorize, isolated from everything around it so
    it can be tested on its own, independent of any real `SuperGrid`."""
    pending_arr = _xp.asarray(pending_ack, dtype=_xp.uint8)
    valid_arr = _xp.asarray(valid, dtype=bool)
    return (pending_arr == 0) & valid_arr


class VectorizedOfferSelector:
    """Wraps a real `SuperGrid` (`unicell_super_automaton_v1.py`) and
    computes, via one vectorized array operation, exactly which non-nano
    cells are ready to offer THIS tick -- the same readiness check
    `SuperGrid.tick()`'s own Pass 4 already computes with a plain Python
    loop, proven equivalent by direct comparison (`test_gpu_array_v1.py`
    's own `test_ready_positions_matches_the_real_offer_pass_condition_
    exactly`), not assumed equivalent from the two implementations
    looking similar.

    Does NOT replace or call into `SuperGrid.tick()` -- this is a
    read-only, side-effect-free query over the grid's CURRENT state,
    safe to call at any point without disturbing the VM's own tested
    tick loop."""

    def __init__(self, grid):
        self.grid = grid

    def ready_positions(self) -> List[Tuple[int, int]]:
        """Every `(row, col)` position whose cell is a non-nano core
        with `pending_ack == 0` and something real to offer THIS tick --
        computed via one vectorized backend operation over the whole
        grid, not a per-cell Python `if` chain."""
        positions = []
        pending_acks = []
        valid_flags = []
        for pos, cell in self.grid.cells.items():
            if cell.core == "nano":
                continue
            positions.append(pos)
            pending_acks.append(cell.pending_ack)
            # _offer_state() itself is real, tested, per-core Python
            # (SuperCell's own registry-dispatched method, #358) --
            # reused unchanged here, not reimplemented. Only the FINAL
            # readiness check (pending_ack==0 AND valid) is vectorized.
            _value, valid, downstream = cell._offer_state()
            valid_flags.append(bool(valid and downstream != 0))

        if not positions:
            return []

        mask = compute_ready_mask(pending_acks, valid_flags)
        # CuPy arrays need an explicit host transfer before Python-level
        # indexing/iteration; NumPy arrays are already host-side, so
        # this is a no-op there -- one real, honest CPU/GPU boundary,
        # matching gpu_array.py's own documented "Stage 1" boundary
        # (bus/input lookup stays on the CPU side).
        mask_host = mask.get() if HAS_GPU else mask
        return [positions[i] for i in range(len(positions)) if mask_host[i]]
