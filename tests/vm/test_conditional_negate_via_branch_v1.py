"""
test_conditional_negate_via_branch_v1.py — points.md #702: the real,
isolated proof of the "conditional negate" building block `ashr`
needs (Alan's own sign-magnitude design, #701's follow-on), using
branch + reconvergence rather than select.

THE REAL REASON select CAN'T DO THIS JOB, confirmed directly against
its own real tile registration before building anything else: `select`
(`#686`) takes `true_val`/`false_val` as real, COMPILE-TIME PRELOADED
constants -- it cannot choose between two DYNAMICALLY COMPUTED values
(here: `x` itself, and `0 - x`). Alan's own real proposal instead:
use branch to ROUTE `x` down one of two physical paths based on its
own sign (negate-then-continue, or pass-through), then RECONVERGE the
two paths -- the same real lane-combine mechanism `#692` already
proved, applied to a control-flow decision instead of a data lane.

Real topology, hop-count-matched (`#544`'s own hard requirement,
confirmed still binding here): both the "negate" path (branch ->
subtractor -> merge) and the "direct" path (branch -> relay -> merge)
are exactly 2 hops from branch to merge.

    west_feeder(1,-1) --e--> branch(1,0) --e--> subtractor(1,1) --s--> \\
       [injected twice: ref=0, then x]    |                             merge(2,1)
                                          --s--> relay(2,0) --e-------> /
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _build_grid():
    records = [
        v3.IcmV3Record(cell_id="west_feeder", row=1, col=-1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        # branch: upstream_dir=W(3); LOW (x<0) routes east to the
        # subtractor; EQUAL/HIGH (x>=0) route south to the direct
        # relay. value_source=0 (relay the real compared value, x
        # itself) for every outcome -- never a fixed constant.
        v3.IcmV3Record(cell_id="branch", row=1, col=0, core="branch",
                        core_config={
                            "upstream_dir": 3,
                            "value_source_low": 0, "value_source_equal": 0, "value_source_high": 0,
                            "fixed_value_low": 0, "fixed_value_equal": 0, "fixed_value_high": 0,
                            "emit_low": 1, "emit_equal": 1, "emit_high": 1,
                            "route_low": ["e"], "route_equal": ["s"], "route_high": ["s"],
                            "rolling_mode": 0,
                        }),
        v3.IcmV3Record(cell_id="subtractor_neg", row=1, col=1, core="adder",
                        core_config={"downstream_mask": ["s"], "upstream_mask": ["n", "w"],
                                     "subtract_mode": 1}),
        v3.IcmV3Record(cell_id="zero_for_negate", row=0, col=1, core="ram",
                        core_config={"downstream_mask": ["s"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": 0}),
        v3.IcmV3Record(cell_id="direct_relay", row=2, col=0, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["n"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="merge", row=2, col=1, core="ram",
                        core_config={"downstream_mask": [], "upstream_mask": ["n", "w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
    ]
    return SuperGrid(records)


def _run_conditional_negate(x, ticks=30):
    grid = _build_grid()
    # ref=0 delivered first (becomes branch's own real reference) --
    # a raw injection, since west_feeder has no real physical
    # neighbor of its own (it's a genuine external entry point).
    grid.inject(1, -1, 0)
    for _ in range(3):
        grid.tick()
    # x delivered second (the real compare value branch classifies).
    grid.inject(1, -1, x & 0xFFFFFFFF)
    for _ in range(ticks):
        grid.tick()
    merge = grid.cells[(2, 1)]
    return merge.ram_data_reg, merge.ram_data_valid


def test_negative_value_gets_negated_to_its_positive_magnitude():
    result, valid = _run_conditional_negate(-5)
    assert valid is True
    assert result == 5


def test_positive_value_passes_through_unchanged():
    result, valid = _run_conditional_negate(7)
    assert valid is True
    assert result == 7


def test_zero_passes_through_unchanged():
    result, valid = _run_conditional_negate(0)
    assert valid is True
    assert result == 0


def test_real_range_of_values_both_signs():
    for x in [-1, -2, -100, -2147483648, 1, 2, 100, 2147483647]:
        result, valid = _run_conditional_negate(x)
        expected = ((-x) & 0xFFFFFFFF) if x < 0 else (x & 0xFFFFFFFF)
        assert valid is True, f"x={x}: not valid"
        assert result == expected, f"x={x}: got {result:#x}, expected {expected:#x}"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
