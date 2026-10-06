"""flex_grid_v1.py -- FlexGrid: the VM's MIRROR variant for the Flex (handshake) cell family (ledger #965).

Alan's rulings (#960, #963 discussion): in std mode the VM stays exactly as it is; in mirror mode the VM changes to reflect the target, and flex is the only family where width and
behaviour really differ, so the flex mirror is a SEPARATE VM variant, a subclass, never flags in the general VM. `CACell` (the standalone nano v4 model) is left alone.

STEP 1 (this file's first form): the skeleton ONLY. FlexCell has its own handler table that falls back to the std one; the table is EMPTY, so a FlexGrid behaves identically to a
SuperGrid (proved cycle for cycle by tests/vm/test_flex_grid_v1.py). Flex behaviour is added one core at a time, each checked against the GENERATED flex hardware, which is the oracle
for this variant (the reverse of how the flex RTL was checked against the VM).

Why a per-class table and not the shared registry: `register_core_handler` is module-level and raises on a duplicate name, so a flex "adder" could not be registered beside the std one.
"""
import os
import sys

from dataclasses import replace as _dc_replace

from unicell_super_automaton_v1 import SuperCell, SuperGrid, _CORE_HANDLERS, CoreHandler, _DIR_BIT
from unicell_automaton_v1 import N, S, E, W
from icm_v3 import pack_dirmask as _pack_dirmask

_FLEX_HANDLERS: dict = {}


def register_flex_handler(name: str, handler) -> None:
    """Register flex-specific behaviour for a core name (falls back to the std handler when absent). Duplicates are refused, as in the std registry."""
    if name in _FLEX_HANDLERS:
        raise ValueError(f"flex core handler {name!r} already registered")
    _FLEX_HANDLERS[name] = handler


def _planner():
    """The flex generator's planner module: the single source of truth for what the flex family can build (imported lazily; it lives in tools/)."""
    import importlib
    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    return importlib.import_module("flexsub_icm_generate_v1")


class FlexCell(SuperCell):
    """A SuperCell whose core behaviour comes from the flex table first, then the std registry."""

    merge_mode = "arbitrate"     # set per merge consumer by FlexGrid (the generator's --merge-mode)
    _merge_order = None          # the faces feeding a merging relay, in operand order (A first); None = not a merge
    _merge_rr = 0                # arbitrate: 1 = B has priority when both are valid (the merge core's round-robin flag)

    def _handler(self):
        h = _FLEX_HANDLERS.get(self.core)
        return h if h is not None else _CORE_HANDLERS.get(self.core)

    @classmethod
    def _check_width_support(cls, core, cfg, width):
        """The flex nano (nano_cell_v4sa) is width-parameterised, so unlike the std VM a FlexGrid CAN run a nano at another width -- but only the nano the flex generator translates:
        the plain two-arrival gate with one of its 12 implemented topologies (no relay / hold / update / one-shot modes). Every operation in that subset is BITWISE per bit, so a
        W-bit result is the 32-bit result truncated to W bits, which the grid already does to every value in transit; there is no W-bit arithmetic to define. A nano outside the
        subset has no flex hardware to mirror and its width behaviour is not a known fact, so it is refused. At width 32 nothing is restricted (the std nano model, as always)."""
        if core == "sequencer" and width < 8:
            raise ValueError(f"flex sequencer at width {width}: the real sequencer_cell_v4sa stores 8-bit values and zero-extends them to the data width, and does not elaborate below 8 bits")
        if core != "nano" or width == 32:
            return
        pl = _planner()
        cfg = cfg or {}
        odd = sorted(k for k, v in cfg.items() if k not in pl.NANO_BENIGN_KEYS and v)
        if odd:
            raise ValueError(f"flex nano at width {width}: {odd} (relay/hold/update/one-shot modes) are not translated by the flex generator; only the plain two-arrival gate is mirrored")
        topo = int(cfg.get("topology", 0))
        if topo not in pl.NANO_TOPOLOGIES:
            raise ValueError(f"flex nano at width {width}: topology {topo:#x} is not implemented by the flex nano (its default would silently pass the held value)")


_DIRS_ALL = tuple(range(4))
_SHIFT_COARSE = (1, 2, 4, 8, 12, 16, 20, 24, 28)    # the supported coarse taps (the same set the std VM and the generator use)


def flex_addons(value, ad, width):
    """The add-on chain (nibble mask -> fine shift -> coarse shift -> invert) on a W-bit value, as the flex family's separate cores do it (mask_cell_v4sa, shift_stage_v4sa; invert is
    wiring). The std chain is defined on 32-bit lanes; this is the same chain on W bits: the 8-bit mask word covers the whole width, each mask bit ceil(W/8) data bits (ledger #968; = the nibble at W 25..32; mask bits beyond the last group are ignored, as in the RTL),
    shifts are logical with zero fill inside W bits, ANY amount is wiring (the std chain's sparse coarse taps are a std-VM limit; on a tap the result is identical), invert flips W bits. `lane_cut` (a byte-lane cut) has no W-bit
    definition and no flex cell, so it is refused at W != 32 (see FlexGrid.__init__). At width 32 this is exactly the std function."""
    amt0 = ad.get("shift_amt", 0)
    if width == 32 and not (ad.get("shift_en") and amt0 and amt0 not in _SHIFT_COARSE):
        from unicell_super_automaton_v1 import apply_addons          # the std chain, unchanged, for every config it defines (taps and none)
        return apply_addons(value, ad, 32)
    m = (1 << width) - 1
    value &= m
    if ad.get("mask_en"):
        nm = ad.get("nibble_mask", 0)
        group = (width + 7) // 8                       # ledger #968: the 8-bit mask word covers the whole width, each bit ceil(W/8) data bits (4 = a nibble at W 25..32)
        for g in range((width + group - 1) // group):
            if (nm >> g) & 1:
                value &= ~(((1 << group) - 1) << (group * g)) & m
    shift_en, right = ad.get("shift_en", 0), bool(ad.get("direction", 0))
    fine, amt = ad.get("shift_fine", 0) & 3, ad.get("shift_amt", 0)
    if shift_en:
        total = fine + amt          # FLEX: the shift is pure wiring, so ANY amount 0..W is available (Alan #985), not just the std taps
        if total:
            value = (value >> total) if right else ((value << total) & m)
    if ad.get("invert_en"):
        value = ~value & m
    return value


def _flex_deliver_ram(cell, arrivals, injected):
    """The flex relay/MERGE: ram_cell_v4sa behind a merge_cell_v4sa when two or more sources feed one input (ledger #968+). With one source it is the std relay. With several:
    ARBITRATE (two sources): when both are valid in the same tick, grant ONE (A unless the round-robin flag says B), acknowledge only that one (the other stays pending and is served
    later) -- where the std VM ORs both into one value; the flag then rotates after every grant, so neither starves. JOIN-OR (any number of sources): accept NOTHING until every source
    is presenting, then take them all and OR them. A = the source that comes first in the ICM record list (what the generator does)."""
    order = getattr(cell, "_merge_order", None)
    if cell.ram_fixed_mode or not order or injected is not None:
        return SuperCell._deliver_ram(cell, arrivals, injected)
    present = [d for d in order if d in arrivals and (cell.ram_upstream_mask >> _DIR_BIT[d]) & 1]
    if cell.merge_mode == "join-or":
        if len(present) < len(order):
            return (False, None) if arrivals else (True, None)
        if cell.ram_data_valid:
            return (False, None)
        val = 0
        for d in present:
            val |= arrivals[d] & cell.mask
        cell.ram_data_reg, cell.ram_data_valid = val, True
        return (True, None)
    if not present:
        return (True, None)
    if cell.ram_data_valid:
        return (False, None)
    a, b = order[0], order[1]
    if a in present and b in present:
        win = a if not cell._merge_rr else b
    else:
        win = present[0]
    cell.ram_data_reg, cell.ram_data_valid = arrivals[win] & cell.mask, True
    cell._merge_rr = 1 if win == a else 0
    return ({win}, None)


def _one_operand_at_a_time(cell, arrivals, injected, mask, deliver, what):
    """ledger #989: a two-operand flex cell never ORs two operands that arrive in the SAME tick (the std VM does; the real handshake cell takes both and waits for both). The VM takes ONE (the lower face) and
    acknowledges only that one -- the other stays pending and is taken next. For add and multiply that gives the same result as the RTL (commutative). For a SUBTRACT the order would be a guess, so it is refused."""
    present = sorted((d for d in arrivals if (mask >> _DIR_BIT[d]) & 1), key=lambda d: _DIR_BIT[d])
    if injected is not None or len(present) < 2:
        return deliver(cell, arrivals, injected)
    if what == "subtract":
        raise ValueError("flex VM: both operands of a subtract arrive in the same tick -- there is no operand order (the real cell orders them by arrival); separate their path lengths")
    win = present[0]
    got = deliver(cell, {win: arrivals[win]}, None)
    return ({win}, None) if got[0] is True else got


def _flex_deliver_adder(self, arrivals, injected):
    return _one_operand_at_a_time(self, arrivals, injected, self.adder_upstream_mask, _flex_deliver_adder1, "subtract" if self.adder_subtract_mode else "add")


def _flex_deliver_mul(self, arrivals, injected):
    return _one_operand_at_a_time(self, arrivals, injected, self.mul_upstream_mask, _CORE_HANDLERS["mul"].deliver, "mul")


def _flex_deliver_adder1(self, arrivals, injected):
    """The adder: exactly the std behaviour, plus -- when carry_mode is on (ledger #976) -- the carry-out of the W-bit add is latched with the sum. For subtract it is the raw carry of a + ~b + 1 (NOT-borrow), as in adder_cell_v4sa."""
    matched = {d: v for d, v in arrivals.items() if (self.adder_upstream_mask >> _DIR_BIT[d]) & 1}
    if not matched and injected is None:
        return (True, None)
    val = 0
    for v in matched.values():
        val |= v & self.mask
    if injected is not None:
        val |= injected & self.mask
    if not self.adder_a_arrived:
        self.adder_a_reg = val
        self.adder_a_arrived = True
        return (True, None)
    if self.adder_data_valid:
        return (False, None)
    if self.adder_subtract_mode:
        self.adder_out_buffer = (self.adder_a_reg - val) & self.mask
        raw = self.adder_a_reg + ((~val) & self.mask) + 1
    else:
        self.adder_out_buffer = (self.adder_a_reg + val) & self.mask
        raw = self.adder_a_reg + val
    self.adder_captured_carry = (raw >> self.width) & 1
    self.adder_delivering_carry = False
    self.adder_data_valid = True
    self.adder_a_arrived = False
    return (True, None)


def _flex_clear_valid_adder(self):
    """carry_mode: the sum's drain does NOT finish the round -- the buffer is reloaded with the carry word (0 or 1) and offered to the same downstream; only the carry's own drain clears it (same shape as the multiplier's wide_mode)."""
    if getattr(self, "adder_carry_mode", False) and not getattr(self, "adder_delivering_carry", False):
        self.adder_out_buffer = self.adder_captured_carry
        self.adder_delivering_carry = True
        return
    self.adder_data_valid = False
    self.adder_delivering_carry = False


def _flex_offer_adder(self):
    """ledger #981: while the CARRY (second word) is on offer it leaves by `second_downstream_mask` when one is set; otherwise by downstream_mask like the sum."""
    v, valid, mask = SuperCell._offer_state_adder(self)
    if getattr(self, "adder_delivering_carry", False) and getattr(self, "second_mask", 0):
        mask = self.second_mask
    return (v, valid, mask)


def _flex_offer_mul(self):
    """ledger #981: the HIGH word (second word) leaves by `second_downstream_mask` when one is set."""
    v, valid, mask = SuperCell._offer_state_mul(self)
    if self.mul_delivering_hi and getattr(self, "second_mask", 0):
        mask = self.second_mask
    return (v, valid, mask)


register_flex_handler("mul", _dc_replace(_CORE_HANDLERS["mul"], deliver=_flex_deliver_mul, offer_state=_flex_offer_mul))
register_flex_handler("adder", CoreHandler(deliver=_flex_deliver_adder, offer_state=_flex_offer_adder, continuously_live=False, clear_valid=_flex_clear_valid_adder))
register_flex_handler("ram", CoreHandler(deliver=_flex_deliver_ram, offer_state=SuperCell._offer_state_ram, continuously_live=False, clear_valid=SuperCell._clear_valid_ram))


class FlexGrid(SuperGrid):
    """A SuperGrid of FlexCells. `family` names the mirror; width is the grid's (default 32)."""
    _cell_class = FlexCell
    family = "flex"
    _ALLOWS_CARRY_MODE = True
    _UNVERIFIED_AT_OTHER_WIDTHS = frozenset({"priority"})      # accumulator and branch are checked against the real v4sa cells at W = 16..36 / 4..36 (#970); the priority arbiter is not translated by the flex generator

    def __init__(self, records, width=32, merge_mode="arbitrate", **kw):
        # CROSSING tiles (core "cross", Alan 6 Oct 2026) are pure wiring: a word entering one keeps its direction and leaves by the opposite face, with no state and no tick.
        # They are therefore not cells here at all: neighbor_pos steps THROUGH them (see below), exactly as the netlist splice does for the generated RTL.
        self._cross = {(r.row, r.col) for r in records if r.core == "cross"}
        records = [r for r in records if r.core != "cross"]
        super().__init__(records, width=width, **kw)
        self._setup_merges(records, merge_mode)
        for r in records:                                   # ledger #976: the adder's carry flag (ICM second_output); the cell attribute is read by the flex adder handler
            if r.core == "adder":
                self.cells[(r.row, r.col)].adder_carry_mode = bool((r.core_config or {}).get("second_output", 0))
            if r.core in ("adder", "mul"):                  # ledger #981: where the second word goes (0 = with the first)
                cfg_ = r.core_config or {}
                sm_ = cfg_.get("second_downstream_mask", 0)
                sm_ = _pack_dirmask(sm_) if isinstance(sm_, (list, tuple, set)) else int(sm_)
                if sm_ and not cfg_.get("second_output"):
                    raise ValueError(f"cell {r.cell_id}: second_downstream_mask is set but second_output is off -- there is no second word to route")
                dm_ = cfg_.get("downstream_mask", 0)
                if sm_ and not (_pack_dirmask(dm_) if isinstance(dm_, (list, tuple, set)) else int(dm_)):
                    raise ValueError(f"cell {r.cell_id}: second_downstream_mask needs a non-empty downstream_mask (the first word needs somewhere to go, or the round never drains)")
                self.cells[(r.row, r.col)].second_mask = sm_
        if width != 32:
            for pos, c in self.cells.items():
                if (c.addon_config or {}).get("lane_cut") and (c.addon_config or {}).get("shift_en") and (c.addon_config or {}).get("direction"):
                    raise ValueError(f"flex add-ons at width {width}: lane_cut (a byte-lane cut on right shifts) has no {width}-bit definition and no flex cell; cell {c.cell_id} at {pos} is refused")

    def neighbor_pos(self, row, col, direction):
        dr, dc = {N: (-1, 0), S: (1, 0), E: (0, 1), W: (0, -1)}[direction]
        pos = (row + dr, col + dc)
        while pos in self._cross:
            pos = (pos[0] + dr, pos[1] + dc)
        return pos if pos in self.cells else None

    def _addons(self, value, addon_config):
        return flex_addons(value, addon_config, self.width)

    def _setup_merges(self, records, merge_mode):
        """Find every single-input cell fed by several sources (the generator places a merge core in front of it), record its operand order and its mode (the generator's own parser:
        'arbitrate' | 'join-or' | 'cell=mode,...')."""
        import importlib
        _planner()
        flexmod = importlib.import_module("flexsub_icm_flex_v1")
        modes = flexmod.parse_merge_modes(merge_mode)
        index = {(r.row, r.col): k for k, r in enumerate(records)}
        by_pos = {(r.row, r.col): r for r in records}
        for pos, c in self.cells.items():
            if c.core not in ("ram", "comparator") or c.ram_fixed_mode and c.core == "ram":
                continue
            mask = c.ram_upstream_mask if c.core == "ram" else c.cmp_upstream_mask
            faces = []
            for d in _DIRS_ALL:
                if (mask >> _DIR_BIT[d]) & 1:
                    nb = self.neighbor_pos(pos[0], pos[1], d)
                    src = by_pos.get(nb) if nb is not None else None
                    if src is not None:
                        faces.append((index[nb], d))
            if len(faces) < 2:
                continue
            if c.core != "ram":
                raise ValueError(f"flex merge into a {c.core} ({c.cell_id}) is not mirrored yet: only a relay (ram) behind a merge core is")
            c._merge_order = [d for _i, d in sorted(faces)]
            c.merge_mode = modes.get(c.cell_id, modes["*"])
            if c.merge_mode == "arbitrate" and len(faces) > 2:
                raise ValueError(f"flex merge of {len(faces)} sources into {c.cell_id} in arbitrate mode is a tree of round-robin cores whose grant order is not mirrored; join-or of any number of sources is")
