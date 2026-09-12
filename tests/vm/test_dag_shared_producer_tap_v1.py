"""
test_dag_shared_producer_tap_v1.py — points.md #706: the real,
isolated proof of the mechanism needed to lift `#701`'s own real,
named restriction ("each producer may be tapped by AT MOST ONE later
consumer") -- daisy-chaining the drop cell itself.

THE REAL IDEA: a drop cell configured with `hold_in=1, a_reemit_in=1`
can be given a `routing_mask` with MORE than one direction. Its own
reemit (`#700`) calls `_emit(self.a_data)` using whatever routing_mask
is configured -- so a drop can deliver to its OWN consumer (say,
north) AND relay onward to a SECOND drop (say, east) on the exact
same trigger event. The second drop then independently holds the
relayed value and waits for its OWN, separate trigger.

Real, honest constraint this introduces, confirmed directly rather
than assumed: the chain is now ORDER-DEPENDENT -- drop 2 cannot
receive anything until drop 1's own trigger has already fired. For
this to work in a real program, the daisy-chain order must match (or
be no earlier than) each consumer's own real need -- not a free-form
fan-out, a real, specific new constraint worth naming plainly.

    producer(1,0) --e--> [ordinary chain, unused here]
         |
         --s--> tap(2,0) --e--> relay(2,1) --e--> drop1(2,2) --n--> consumer1(1,2)
                                                       |
                                                       --e--> drop2(2,3) --n--> consumer2(1,3)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

VALUE = 0x2A


def _build_grid():
    records = [
        v3.IcmV3Record(cell_id="producer", row=1, col=0, core="ram",
                        core_config={"downstream_mask": ["e", "s"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": VALUE}),
        v3.IcmV3Record(cell_id="tap", row=2, col=0, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["n"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="relay", row=2, col=1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="drop1", row=2, col=2, core="nano",
                        core_config={"topology": 0, "ready": 1, "routing_mask": ["n", "e"],
                                     "hold_in": 1, "a_reemit_in": 1}),
        v3.IcmV3Record(cell_id="consumer1", row=1, col=2, core="ram",
                        core_config={"downstream_mask": [], "upstream_mask": ["s"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="drop2", row=2, col=3, core="nano",
                        core_config={"topology": 0, "ready": 1, "routing_mask": ["n"],
                                     "hold_in": 1, "a_reemit_in": 1}),
        v3.IcmV3Record(cell_id="consumer2", row=1, col=3, core="ram",
                        core_config={"downstream_mask": [], "upstream_mask": ["s"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
    ]
    return SuperGrid(records)


def test_drop1_delivers_to_its_own_consumer_and_relays_onward_simultaneously():
    grid = _build_grid()
    grid.run_to_quiescence(max_ticks=30)
    c1 = grid.cells[(1, 2)]
    drop2 = grid.cells[(2, 3)]
    assert c1.ram_data_valid is False
    assert drop2._nano.a_arrived is False

    grid.inject(2, 2, 0)   # trigger drop1
    grid.tick()
    grid.tick()

    assert c1.ram_data_valid is True
    assert c1.ram_data_reg == VALUE
    assert drop2._nano.a_arrived is True
    assert drop2._nano.a_data == VALUE
    c2 = grid.cells[(1, 3)]
    assert c2.ram_data_valid is False


def test_drop2_only_delivers_on_its_own_separate_trigger():
    grid = _build_grid()
    grid.run_to_quiescence(max_ticks=30)
    grid.inject(2, 2, 0)
    grid.tick()
    grid.tick()
    c2 = grid.cells[(1, 3)]
    assert c2.ram_data_valid is False

    for _ in range(20):
        grid.tick()
    assert c2.ram_data_valid is False

    grid.inject(2, 3, 0)
    grid.tick()
    grid.tick()
    assert c2.ram_data_valid is True
    assert c2.ram_data_reg == VALUE


def test_both_consumers_end_up_with_the_correct_value():
    grid = _build_grid()
    grid.run_to_quiescence(max_ticks=30)
    grid.inject(2, 2, 0)
    grid.tick()
    grid.tick()
    grid.inject(2, 3, 0)
    grid.tick()
    grid.tick()
    c1 = grid.cells[(1, 2)]
    c2 = grid.cells[(1, 3)]
    assert c1.ram_data_reg == VALUE and c1.ram_data_valid is True
    assert c2.ram_data_reg == VALUE and c2.ram_data_valid is True


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
