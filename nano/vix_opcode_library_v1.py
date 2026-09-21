"""
vix_opcode_library_v1.py — points.md #793: the real, first formalized
"library entry" structure, per Alan's own direct synthesis of this
whole session's own conversation: a library entry is a known Target
(the desired effect), a known Shape, known In/Out, known Timing, with
the ICM-format description of the actual cores and their programming
as the one, complete, self-sufficient artifact -- reusing the ICM
format rather than inventing a new one, since a finished ICM entry
already carries everything the VM or Composer ever needs to load and
run it.

Real, honest, precise correction made while building this, confirmed
directly against Alan's own question: "Shape" is not one field -- it
is two, already-proven, genuinely separate things that this structure
keeps distinct rather than conflating:
- `shape` (`ConvergenceShape`, `#777`): HOW multiple real operands
  meet -- decided by commutativity and whether real arrival timing is
  knowable. A property of the relationship BETWEEN operands.
- `port_style` (`#792`'s own real, confirmed distinction): HOW the
  entry's own tile physically wires to its real neighbors -- named
  ports (`adder`'s `in_a`/`in_b`) vs unconditional acceptance
  (`nano_gate`, confirmed directly against `nano_gate_v4c.v` to have
  no real `upstream_mask` field at all, `#718`/`#781`). A property of
  the TILE itself, independent of what's converging into it.

`timing` (`arrivals_needed`, `#757`) is pulled directly from each
entry's own real `VixTileSpec` -- never duplicated or restated here,
matching the same "the ICM/tile description is the one, complete
truth" principle the rest of this module follows.

Real, honest scope: this formalizes SELECTION (which real shape does
this opcode need) as a real, named, inspectable structure, separate
from PLACEMENT (`vix_dag_dispatcher_v1.py`'s own `Frontier`/`_pad()`/
`manhattan_route()` machinery, which stays completely unaware of which
opcode or tile it's connecting -- confirmed directly, unchanged by
this entry). A real, deliberately NOT-yet-attempted extension, named
directly: a `target` (hardware family -- Arria 10 vs Gowin, etc.)
dimension, so the same opcode could resolve to a different real tile
(a dedicated DSP-wrapper cell instead of a generic `core_select`
value) depending on what silicon is actually available -- real,
separate, larger work than this entry attempts, matching `#792`'s own
scoping note about the already-existing, already-proven `dsp_wrapper_
tile_library_v1.py`/`sentinel_bram_automaton_v1.py` infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import vix_tile_library_v1 as vtl
from vix_convergence_shapes_v1 import ConvergenceShape


@dataclass
class LibraryEntry:
    """One real, named library entry. `target` (the opcode string) is
    the desired effect; `is_commutative` and `port_style` are the two
    real, separate facts `#777`'s shape catalog and `#792`'s placement
    logic each need; `tile` is the real ICM-format description (the
    one, complete, self-sufficient artifact `#792`'s comment reused
    directly -- `timing` is read from `tile.arrivals_needed`, never
    stored twice)."""
    target: str
    tile: "vtl.VixTileSpec"
    is_commutative: bool
    port_style: str  # "named" (adder-style in_a/in_b), "unconditional" (nano_gate-style), or "unary_addon"
    extra_params: dict
    #: points.md #797: number of DATA operands. Two for every entry so far;
    #: a shift has ONE -- its amount is compile-time configuration carried
    #: in `DagInstr.params`, never a second data operand.
    arity: int = 2
    #: for `arity == 1` entries: turns `DagInstr.params` into the real
    #: `addon_config` of the cell that performs the op.
    addon_builder: Optional[Callable[[dict], dict]] = None
    #: for `arity == 1` entries: turns `DagInstr.params` into the tile's own
    #: real core params (e.g. a comparator's `threshold`). points.md #798.
    param_builder: Optional[Callable[[dict], dict]] = None
    #: does the op need a SECOND cell to land its result in? True for an
    #: addon transform (applied at offer time, #690); False for a core whose
    #: own output buffer already IS the result (a comparator).
    needs_capture: bool = True

    @property
    def timing(self) -> int:
        """Real, direct pull from the tile's own real contract field
        (`#757`) -- never duplicated here, matching this whole
        module's own "the ICM description is the one truth" principle."""
        return self.tile.arrivals_needed


_LIBRARY: Dict[str, LibraryEntry] = {}


def register(entry: LibraryEntry) -> LibraryEntry:
    _LIBRARY[entry.target] = entry
    return entry


def lookup(opcode: str) -> Optional[LibraryEntry]:
    """Real, direct library lookup -- the one place a compiler
    frontend (LLVM IR, DSL, or any future one) asks "do you have an
    entry for this?" A `None` result is the real, honest signal to
    escalate (`#752`'s own already-scoped ladder: local library ->
    shared library -> AI research -> user/Composer), never a silent
    guess standing in for a real, tested entry."""
    return _LIBRARY.get(opcode)


# ── Real, first entries: add/sub/mul (named-port, "adder-style") and
# and/or/xor (unconditional, "nano_gate-style") -- every one of these
# already proven correct through the real dispatcher (#790/#792). ──
register(LibraryEntry(target="add", tile=vtl.TILE_ADDER, is_commutative=True,
                       port_style="named", extra_params={}))
register(LibraryEntry(target="sub", tile=vtl.TILE_SUBTRACTOR, is_commutative=False,
                       port_style="named", extra_params={}))
register(LibraryEntry(target="mul", tile=vtl.TILE_MUL, is_commutative=True,
                       port_style="named", extra_params={}))
register(LibraryEntry(target="and", tile=vtl.TILE_NANO_GATE, is_commutative=True,
                       port_style="unconditional", extra_params={"topology": 0x007}))
register(LibraryEntry(target="or", tile=vtl.TILE_NANO_GATE, is_commutative=True,
                       port_style="unconditional", extra_params={"topology": 0x024}))
register(LibraryEntry(target="xor", tile=vtl.TILE_NANO_GATE, is_commutative=True,
                       port_style="unconditional", extra_params={"topology": 0x0BC}))


# ── points.md #797: shifts. ONE data operand; the amount is compile-time
# configuration. Realized as the old frontend's own proven two-cell shape
# (#690/#705): a `ram_flowing` cell carrying the shift addon, then a
# `ram_flowing` capture cell (addons apply at OFFER time, so the shifted
# value needs a second cell to land in). `is_commutative=True` is vacuous
# here -- there is no second operand whose order could be wrong. ──
_COARSE_TAPS = (0, 1, 2, 4, 8, 12, 16, 20, 24, 28)


def decompose_shift(amount: int):
    """Split 0-31 into (coarse tap, fine 0-3): the largest real coarse tap
    <= amount (shift_lane_addon_v2's own sparse taps), remainder by
    construction 0-3 (no gap between adjacent taps exceeds 4). Same rule
    as `llvm_ir_frontend_v1._decompose_shift` (#690), restated here so the
    new path does not import a private helper from the old frontend."""
    if not 0 <= amount <= 31:
        raise ValueError(f"shift amount {amount} outside 0-31")
    coarse = max(t for t in _COARSE_TAPS if t <= amount)
    return coarse, amount - coarse


def _shift_addon(direction: int) -> Callable[[dict], dict]:
    def build(params: dict) -> dict:
        coarse, fine = decompose_shift(params["amount"])
        return {"shift_en": 1, "direction": direction, "shift_amt": coarse, "shift_fine": fine}
    return build


register(LibraryEntry(target="shl", tile=vtl.TILE_RAM_FLOWING, is_commutative=True,
                       port_style="unary_addon", extra_params={}, arity=1, addon_builder=_shift_addon(0)))
register(LibraryEntry(target="lshr", tile=vtl.TILE_RAM_FLOWING, is_commutative=True,
                       port_style="unary_addon", extra_params={}, arity=1, addon_builder=_shift_addon(1)))


# ── points.md #798: the comparator as a one-operand entry, `cmp_ge`:
# result = 1 if signed(value) >= threshold else 0. NOT an LLVM opcode -- an
# INTERNAL building block the frontend's `icmp` expansion composes with a
# `sub` (diff, then compare), exactly the old frontend's own diff->comparator
# shape (#611/#613) expressed as two library entries instead of a special
# case. The comparator's own output buffer is already the 0/1 result, so no
# capture cell (`needs_capture=False`). ──
register(LibraryEntry(target="cmp_ge", tile=vtl.TILE_COMPARATOR, is_commutative=True,
                       port_style="unary", extra_params={}, arity=1,
                       param_builder=lambda p: {"threshold": p["threshold"]}, needs_capture=False))


# ── points.md #802: `copy` -- a one-cell pass-through (a `ram_flowing` cell that just holds and
# offers what it received). INTERNAL, like `cmp_ge`: the frontend expands `zext i1 -> i32` to it,
# because an i1 value is already a canonical 0/1 in a 32-bit cell, so widening changes no bits. ──
register(LibraryEntry(target="copy", tile=vtl.TILE_RAM_FLOWING, is_commutative=True,
                       port_style="unary", extra_params={}, arity=1, needs_capture=False))
