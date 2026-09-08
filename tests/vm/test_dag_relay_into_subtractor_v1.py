"""
test_dag_relay_into_subtractor_v1.py — points.md #700: the real,
integrated proof that `test_dag_relay_trigger_v1.py`'s own hold+
trigger mechanism actually solves the problem it was built for --
controlling OPERAND ARRIVAL ORDER into a real, order-sensitive op
(subtraction: A-B, where A is whichever operand arrives first),
regardless of how many hops the relayed operand's own path took.

THE REAL RISK THIS CLOSES: without an explicit trigger, a relayed
value's arrival time is a function of relay distance -- unpredictable
at the point the compiler decides which operand should be A vs B. By
holding the relayed value and delivering it only on an explicit,
separately-timed trigger, the compiler regains full control over
arrival order: fire the trigger BEFORE injecting the second (compile-
time) operand, and the relayed value is GUARANTEED to become A, no
matter how long its own relay path was.

    source(0,0) --e--> relay1(0,1) --e--> relay2(0,2) --e--> drop(0,3) --s--> SUBTRACTOR(1,3)

(drop feeds the subtractor from its own north input; the compile-time
constant is injected directly, timed to arrive strictly AFTER the
trigger fires)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

RELAYED_VALUE = 100   # will become A -- the minuend
CONST_VALUE = 23      # will become B -- the subtrahend
EXPECTED = RELAYED_VALUE - CONST_VALUE   # = 77


def _build_grid():
    records = [
        v3.IcmV3Record(cell_id="source", row=0, col=0, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": RELAYED_VALUE}),
        v3.IcmV3Record(cell_id="relay1", row=0, col=1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="relay2", row=0, col=2, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="drop", row=0, col=3, core="nano",
                        core_config={"topology": 0, "ready": 1, "routing_mask": ["s"],
                                     "hold_in": 1, "a_reemit_in": 1}),
        v3.IcmV3Record(cell_id="subtractor", row=1, col=3, core="adder",
                        core_config={"downstream_mask": [], "upstream_mask": ["n"],
                                     "subtract_mode": 1}),
    ]
    return SuperGrid(records)


def test_relayed_value_correctly_becomes_the_first_operand_via_the_trigger():
    grid = _build_grid()
    grid.run_to_quiescence(max_ticks=30)
    sub = grid.cells[(1, 3)]
    assert sub.adder_a_arrived is False   # nothing delivered yet -- drop is holding

    # Fire the trigger FIRST -- the relayed value (100) is delivered
    # and becomes A.
    grid.inject(0, 3, 0)
    grid.tick()
    grid.tick()
    assert sub.adder_a_arrived is True
    assert sub.adder_a_reg == RELAYED_VALUE

    # THEN inject the compile-time second operand -- becomes B,
    # triggering the real subtraction A-B.
    grid.inject(1, 3, CONST_VALUE)
    grid.tick()
    grid.tick()

    assert sub.adder_out_buffer == EXPECTED
    assert sub.adder_data_valid is True


def test_a_longer_relay_path_produces_the_identical_correct_result():
    """Real, direct confirmation that path length is genuinely
    irrelevant to correctness -- rebuild with 3 extra relay hops
    (a stand-in for a reference much further back in the chain) and
    confirm the exact same real result, using the exact same real
    trigger-then-constant sequencing."""
    records = [
        v3.IcmV3Record(cell_id="source", row=0, col=0, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": RELAYED_VALUE}),
        v3.IcmV3Record(cell_id="relay1", row=0, col=1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="relay2", row=0, col=2, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="relay3", row=0, col=3, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="relay4", row=0, col=4, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="relay5", row=0, col=5, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="drop", row=0, col=6, core="nano",
                        core_config={"topology": 0, "ready": 1, "routing_mask": ["s"],
                                     "hold_in": 1, "a_reemit_in": 1}),
        v3.IcmV3Record(cell_id="subtractor", row=1, col=6, core="adder",
                        core_config={"downstream_mask": [], "upstream_mask": ["n"],
                                     "subtract_mode": 1}),
    ]
    grid = SuperGrid(records)
    grid.run_to_quiescence(max_ticks=30)
    sub = grid.cells[(1, 6)]

    grid.inject(0, 6, 0)
    grid.tick(); grid.tick()
    assert sub.adder_a_reg == RELAYED_VALUE   # identical to the 2-hop case

    grid.inject(1, 6, CONST_VALUE)
    grid.tick(); grid.tick()
    assert sub.adder_out_buffer == EXPECTED


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
