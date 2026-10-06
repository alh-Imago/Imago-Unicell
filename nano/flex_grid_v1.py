"""flex_grid_v1.py -- FlexGrid: the VM's MIRROR variant for the Flex (handshake) cell family (ledger #965).

Alan's rulings (#960, #963 discussion): in std mode the VM stays exactly as it is; in mirror mode the VM changes to reflect the target, and flex is the only family where width and
behaviour really differ, so the flex mirror is a SEPARATE VM variant, a subclass, never flags in the general VM. `CACell` (the standalone nano v4 model) is left alone.

STEP 1 (this file's first form): the skeleton ONLY. FlexCell has its own handler table that falls back to the std one; the table is EMPTY, so a FlexGrid behaves identically to a
SuperGrid (proved cycle for cycle by tests/vm/test_flex_grid_v1.py). Flex behaviour is added one core at a time, each checked against the GENERATED flex hardware, which is the oracle
for this variant (the reverse of how the flex RTL was checked against the VM).

Why a per-class table and not the shared registry: `register_core_handler` is module-level and raises on a duplicate name, so a flex "adder" could not be registered beside the std one.
"""
from unicell_super_automaton_v1 import SuperCell, SuperGrid, _CORE_HANDLERS

_FLEX_HANDLERS: dict = {}


def register_flex_handler(name: str, handler) -> None:
    """Register flex-specific behaviour for a core name (falls back to the std handler when absent). Duplicates are refused, as in the std registry."""
    if name in _FLEX_HANDLERS:
        raise ValueError(f"flex core handler {name!r} already registered")
    _FLEX_HANDLERS[name] = handler


class FlexCell(SuperCell):
    """A SuperCell whose core behaviour comes from the flex table first, then the std registry."""

    def _handler(self):
        h = _FLEX_HANDLERS.get(self.core)
        return h if h is not None else _CORE_HANDLERS.get(self.core)


class FlexGrid(SuperGrid):
    """A SuperGrid of FlexCells. `family` names the mirror; width is the grid's (default 32)."""
    _cell_class = FlexCell
    family = "flex"
