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

from unicell_super_automaton_v1 import SuperCell, SuperGrid, _CORE_HANDLERS

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

    def _handler(self):
        h = _FLEX_HANDLERS.get(self.core)
        return h if h is not None else _CORE_HANDLERS.get(self.core)

    @classmethod
    def _check_width_support(cls, core, cfg, width):
        """The flex nano (nano_cell_v4sa) is width-parameterised, so unlike the std VM a FlexGrid CAN run a nano at another width -- but only the nano the flex generator translates:
        the plain two-arrival gate with one of its 12 implemented topologies (no relay / hold / update / one-shot modes). Every operation in that subset is BITWISE per bit, so a
        W-bit result is the 32-bit result truncated to W bits, which the grid already does to every value in transit; there is no W-bit arithmetic to define. A nano outside the
        subset has no flex hardware to mirror and its width behaviour is not a known fact, so it is refused. At width 32 nothing is restricted (the std nano model, as always)."""
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


_SHIFT_COARSE = (1, 2, 4, 8, 12, 16, 20, 24, 28)    # the supported coarse taps (the same set the std VM and the generator use)


def flex_addons(value, ad, width):
    """The add-on chain (nibble mask -> fine shift -> coarse shift -> invert) on a W-bit value, as the flex family's separate cores do it (mask_cell_v4sa, shift_stage_v4sa; invert is
    wiring). The std chain is defined on 32-bit lanes; this is the same chain on W bits: the nibble mask covers ceil(W/4) nibbles (mask bits above that are ignored, as in the RTL),
    shifts are logical with zero fill inside W bits, an unsupported coarse amount is a no-op (as in the std chain), invert flips W bits. `lane_cut` (a byte-lane cut) has no W-bit
    definition and no flex cell, so it is refused at W != 32 (see FlexGrid.__init__). At width 32 this is exactly the std function."""
    if width == 32:
        from unicell_super_automaton_v1 import apply_addons
        return apply_addons(value, ad, 32)
    m = (1 << width) - 1
    value &= m
    if ad.get("mask_en"):
        nm = ad.get("nibble_mask", 0)
        for nib in range((width + 3) // 4):
            if (nm >> nib) & 1:
                value &= ~(0xF << (4 * nib)) & m
    shift_en, right = ad.get("shift_en", 0), bool(ad.get("direction", 0))
    fine, amt = ad.get("shift_fine", 0) & 3, ad.get("shift_amt", 0)
    if shift_en:
        total = fine + (amt if amt in _SHIFT_COARSE else 0)
        if total:
            value = (value >> total) if right else ((value << total) & m)
    if ad.get("invert_en"):
        value = ~value & m
    return value


class FlexGrid(SuperGrid):
    """A SuperGrid of FlexCells. `family` names the mirror; width is the grid's (default 32)."""
    _cell_class = FlexCell
    family = "flex"

    def __init__(self, records, width=32, **kw):
        super().__init__(records, width=width, **kw)
        if width != 32:
            for pos, c in self.cells.items():
                if (c.addon_config or {}).get("lane_cut") and (c.addon_config or {}).get("shift_en") and (c.addon_config or {}).get("direction"):
                    raise ValueError(f"flex add-ons at width {width}: lane_cut (a byte-lane cut on right shifts) has no {width}-bit definition and no flex cell; cell {c.cell_id} at {pos} is refused")

    def _addons(self, value, addon_config):
        return flex_addons(value, addon_config, self.width)
