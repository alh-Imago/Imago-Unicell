"""
test_dag_relay_trigger_v1.py — points.md #700: the real, isolated
proof of the "arrival trigger" mechanism Alan asked for while scoping
general DAG routing (the "actual hard, unsolved part"
`llvm_ir_frontend_v1.py`'s own docstring already named).

THE REAL PROBLEM, stated precisely: relaying a value from an earlier
instruction's result cell to a later, non-adjacent instruction takes a
NUMBER OF HOPS that varies with distance -- a reference 5 instructions
back travels further than one 2 instructions back. If the relayed
value is simply delivered the moment it arrives, its ARRIVAL ORDER
relative to the consuming instruction's OTHER operand (a compile-time
constant, delivered by direct injection, near-instantaneous) becomes
distance-dependent and unpredictable -- for order-sensitive ops
(subtraction), whichever operand arrives FIRST becomes A; an
accidentally-reversed arrival order would silently compute the wrong
result.

ALAN'S OWN REAL FIX: don't let arrival trigger delivery. Hold the
relayed value at its destination the moment it arrives (nano's own
real, RTL-confirmed `hold_in` mechanism, already proven in `#638`'s
own bounded loop ring, `#649`), and deliver it only when a SEPARATE,
EXPLICIT trigger event arrives (`a_reemit_in`) -- an event the
compiler times independently, at exactly the moment the consuming
instruction needs it, regardless of how many hops the original relay
took to get there. Path length and delivery timing become genuinely
decoupled.

THE MECHANISM, confirmed directly against `unicell_automaton_v1.
deliver()` before building this, not assumed: nano's own capture
logic checks `hold_in and a_reemit_in and a_arrived` FIRST, before its
normal capture/compute path -- so once a nano cell configured with
`hold_in=1, a_reemit_in=1` has captured one real value (`a_arrived`
becomes true), ANY subsequent arrival (from any direction at all --
nano has no upstream_mask, it accepts from whichever real neighbor
delivers, or even a raw injection with no real neighbor) immediately
re-emits the ALREADY-HELD value, completely bypassing the normal two-
operand gate computation. The reemit path calls `_emit(self.a_data)`
directly, so `topology` is irrelevant for this cell's real role here.

Real, concrete layout, cardinal-only, no diagonal shortcuts:

    source(0,0) --e--> relay1(0,1) --e--> relay2(0,2) --e--> drop(0,3) --s--> consumer(1,3)
                                                                 ^
                                                    [external trigger, injected directly]

`source` broadcasts a real value through a 2-hop relay chain (standing
in for "however many instructions back the reference is") into
`drop`, a real nano cell configured with `hold_in`/`a_reemit_in`. Only
once an EXPLICIT, SEPARATE trigger is injected does `drop` deliver its
held value south into `consumer` -- proven by checking `consumer`
holds nothing right after the relay chain settles, and holds the
correct value only after the trigger.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

VALUE = 0x42


def _build_grid():
    records = [
        v3.IcmV3Record(cell_id="source", row=0, col=0, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": VALUE}),
        v3.IcmV3Record(cell_id="relay1", row=0, col=1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="relay2", row=0, col=2, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        # drop: the real "arrival trigger" cell -- holds whatever
        # arrives first (the relayed value), then re-emits south only
        # on a SEPARATE, later arrival (the explicit trigger).
        v3.IcmV3Record(cell_id="drop", row=0, col=3, core="nano",
                        core_config={"topology": 0, "ready": 1, "routing_mask": ["s"],
                                     "hold_in": 1, "a_reemit_in": 1}),
        v3.IcmV3Record(cell_id="consumer", row=1, col=3, core="ram",
                        core_config={"downstream_mask": [], "upstream_mask": ["n"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
    ]
    return SuperGrid(records)


def test_relayed_value_is_held_not_delivered_before_the_trigger():
    grid = _build_grid()
    grid.run_to_quiescence(max_ticks=30)
    drop_cell = grid.cells[(0, 3)]
    consumer = grid.cells[(1, 3)]
    # The relay chain has fully settled -- drop is holding the real
    # value, but nothing has been delivered to consumer yet.
    assert drop_cell._nano.a_arrived is True
    assert drop_cell._nano.a_data == VALUE
    assert consumer.ram_data_valid is False


def test_explicit_trigger_delivers_the_held_value_to_the_consumer():
    grid = _build_grid()
    grid.run_to_quiescence(max_ticks=30)
    consumer = grid.cells[(1, 3)]
    assert consumer.ram_data_valid is False   # confirmed not yet delivered

    # The real, explicit trigger -- a raw injection with no real
    # neighbor at all, exactly the same real mechanism the whole
    # project already uses for external, one-time deliveries.
    grid.inject(0, 3, 0)   # value is irrelevant -- ANY arrival triggers reemit
    grid.tick()
    grid.tick()

    assert consumer.ram_data_valid is True
    assert consumer.ram_data_reg == VALUE


def test_relay_path_length_does_not_affect_when_delivery_happens():
    """The real point of this whole mechanism: delivery timing is
    controlled by the trigger, not by how many hops the relay took.
    Confirmed directly by ticking WELL PAST when the relay chain would
    have settled and confirming consumer STILL holds nothing until the
    trigger, no matter how long we wait."""
    grid = _build_grid()
    for _ in range(20):   # far more ticks than the 2-hop relay needs
        grid.tick()
    consumer = grid.cells[(1, 3)]
    assert consumer.ram_data_valid is False, (
        "consumer must not receive anything until explicitly triggered, "
        "regardless of how long the relay chain has had to settle"
    )
    grid.inject(0, 3, 0)
    grid.tick()
    grid.tick()
    assert consumer.ram_data_reg == VALUE


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
