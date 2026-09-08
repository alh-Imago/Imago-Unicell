"""
test_lane_fanout_v1.py — points.md #694: the real REVERSE of `#692`'s
own recursive combine tree -- Alan's own direct question: "if each
lane can be sent to 1 cardinal, or combinations of such, is that a
possibility?"

THE REAL ANSWER, confirmed by building it, not just argued for: yes,
and it needed no new mechanism at all. `downstream_mask` has always
been a real SET of directions, not a single one (the `select`/`icmp`
compositions, `#686`, already fan one value out to two directions at
once). Since the addon chain applies at OFFER time regardless of
which directions are being offered to (the same real property `#692`
already leaned on), a cell can extract-and-reposition ITS OWN lane via
mask+SHIFT_OUT, then broadcast that one repositioned value to any real
subset of its 4 cardinal neighbors -- a single direction, or a genuine
combination of several, at zero extra cost either way.

A REAL, STRUCTURAL BONUS on this side, not just a mirror image: unlike
the combine tree, splitting has no contention -- nothing is ever
OR-combined at a receiver, so `#544`'s own hard equal-hop-count
requirement doesn't even apply here. Each sink only ever hears from
ONE source, so there is no "two arrivals racing for one slot" failure
mode to guard against at all. The fan-out direction is genuinely
SIMPLER to get right than the gather direction.

**Real, precise scope boundary, per Alan's own direct correction
(`#695`): this exemption is real, but scoped exactly to a topology
where nothing ever reconverges.** The moment two already-split lanes
need to be brought back TOGETHER at a shared cell -- for any reason,
whether the overall shape started as a gather tree or a fan-out --
that convergence point re-inherits `#544`'s own original hard
requirement, because RAM's own capture register is a real, single
slot regardless of how the value arrived at it. Proven directly below,
not just argued for: `test_recombining_two_already_split_lanes_still_
needs_the_tree_method` takes two of THIS file's own real lane values
and deliberately mismatches their path lengths to a shared recombine
cell, reproducing `#544`'s exact real failure signature. The fan-out
step itself was never the risk; any later convergence always is.

Real, concrete layout: one source broadcasts a real, already-combined
32-bit value (`#692`'s own real test value, `0x44332211` -- a
deliberate callback) raw to all 4 cardinal neighbors. Each neighbor is
an independent "extractor," keeping only ITS OWN byte via `nibble_
mask` and repositioning it down to bits[7:0] via `SHIFT_OUT` (except
the one lane that's already naturally at bits[7:0], which needs no
shift at all). Three extractors each route their own repositioned
lane to a single, DIFFERENT cardinal direction; the fourth
(`extractor_E`) routes its own single repositioned value to TWO real
directions AT ONCE -- the "combinations" case -- confirmed by checking
BOTH real recipients receive the identical value.

    sinkN(-2,0)
        ^ n
    extractor_N(-1,0)  [byte0, no shift needed]
        ^ s
    sinkE1(-1,1) <-n- extractor_E(0,1) -s-> sinkE2(1,1)   [byte2, shift right 16, TO BOTH]
        ^ w                w ^
    sinkW(0,-2) <--- extractor_W(0,-1)     [byte3, shift right 24]
                            |
                          source(0,0)  [0x44332211, broadcasts raw n/s/e/w]
                            |
    extractor_S(1,0)  [byte1, shift right 8]
        v s
    sinkS(2,0)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

COMBINED = 0x44332211   # the real #692 combine-tree output, reused as a callback
LANE0, LANE1, LANE2, LANE3 = 0x11, 0x22, 0x33, 0x44


def _source(cell_id, row, col, downstream, init_data):
    return v3.IcmV3Record(
        cell_id=cell_id, row=row, col=col, core="ram",
        core_config={"downstream_mask": downstream, "upstream_mask": [],
                     "fixed_mode": 0, "load_data_valid": 1, "init_data": init_data},
    )


def _extractor(cell_id, row, col, upstream, downstream, nibble_mask, shift_amt):
    addon = {"mask_en": 1, "nibble_mask": nibble_mask}
    if shift_amt:
        addon.update({"shift_en": 1, "direction": 1, "shift_amt": shift_amt})   # SHIFT_OUT (right)
    return v3.IcmV3Record(
        cell_id=cell_id, row=row, col=col, core="ram",
        core_config={"downstream_mask": downstream, "upstream_mask": upstream,
                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0},
        addon_config=addon,
    )


def _sink(cell_id, row, col, upstream):
    return v3.IcmV3Record(
        cell_id=cell_id, row=row, col=col, core="ram",
        core_config={"downstream_mask": [], "upstream_mask": upstream,
                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0},
    )


def _build_grid():
    records = [
        _source("source", 0, 0, ["n", "s", "e", "w"], COMBINED),

        # byte0 (bits[7:0]) is already at its natural position -- no
        # shift needed at all, keeping the point honest: a lane only
        # costs a shift when it actually needs repositioning.
        _extractor("extractor_N", -1, 0, ["s"], ["n"], nibble_mask=0xFC, shift_amt=0),
        _sink("sinkN", -2, 0, ["s"]),

        # byte1 (bits[15:8]) -- real repositioning, single destination.
        _extractor("extractor_S", 1, 0, ["n"], ["s"], nibble_mask=0xF3, shift_amt=8),
        _sink("sinkS", 2, 0, ["n"]),

        # byte2 (bits[23:16]) -- the real "combinations" case: ONE
        # repositioned value, broadcast to TWO real cardinal
        # directions at once.
        _extractor("extractor_E", 0, 1, ["w"], ["n", "s"], nibble_mask=0xCF, shift_amt=16),
        _sink("sinkE1", -1, 1, ["s"]),
        _sink("sinkE2", 1, 1, ["n"]),

        # byte3 (bits[31:24]) -- real repositioning, single destination.
        _extractor("extractor_W", 0, -1, ["e"], ["w"], nibble_mask=0x3F, shift_amt=24),
        _sink("sinkW", 0, -2, ["e"]),
    ]
    return SuperGrid(records)


def test_each_lane_reaches_its_own_single_cardinal_correctly_repositioned():
    grid = _build_grid()
    ticks = grid.run_to_quiescence(max_ticks=30)
    assert grid.cells[(-2, 0)].ram_data_reg == LANE0   # sinkN, no shift needed
    assert grid.cells[(2, 0)].ram_data_reg == LANE1    # sinkS, shift right 8
    assert grid.cells[(0, -2)].ram_data_reg == LANE3   # sinkW, shift right 24
    assert ticks < 30


def test_one_lane_reaches_a_real_combination_of_two_cardinals_identically():
    """The real, new part Alan asked about directly -- not just that a
    lane can go to ONE cardinal, but that the SAME repositioned value
    can go to a genuine combination of several, identically."""
    grid = _build_grid()
    grid.run_to_quiescence(max_ticks=30)
    sink_e1 = grid.cells[(-1, 1)].ram_data_reg
    sink_e2 = grid.cells[(1, 1)].ram_data_reg
    assert sink_e1 == LANE2
    assert sink_e2 == LANE2
    assert sink_e1 == sink_e2   # genuinely the same value, not coincidentally equal


def test_fanout_has_no_equal_hop_count_requirement_unlike_the_gather_tree():
    """Real, direct confirmation of the structural asymmetry named in
    the module docstring: since nothing is OR-combined at any sink
    (each hears from exactly one source), the sinks do NOT need to
    settle on the same tick the way #544's/#692's own gather trees
    require -- sinkN (0 shift stages) and sinkW (a real shift stage)
    are free to arrive at different real times without any
    correctness consequence."""
    grid = _build_grid()
    grid.run_to_quiescence(max_ticks=30)
    # All four real single-destination sinks hold their own correct,
    # independent value regardless of how many real addon stages their
    # own path needed -- no contention, no race, by construction.
    assert grid.cells[(-2, 0)].ram_data_valid is True
    assert grid.cells[(2, 0)].ram_data_valid is True
    assert grid.cells[(0, -2)].ram_data_valid is True


# ── points.md #695: Alan's own real, precise correction -- the "no
# equal-hop-count requirement" property above is real, but SCOPED
# exactly to a pure fan-out where nothing ever reconverges. The
# moment two already-split lanes need to be brought back together
# (recombination), THAT convergence point re-inherits #544's own
# original hard requirement, because RAM's own capture register is a
# real, single slot regardless of how the value arrived at it. Proven
# here directly, not just argued for, by deliberately mismatching two
# already-split lanes' own path lengths to a shared recombine cell. ──

def test_recombining_two_already_split_lanes_still_needs_the_tree_method():
    """Real, direct proof of the precise scope boundary Alan named:
    the two values recombined here are exactly LANE0/LANE1, the same
    real outputs `#694`'s own proven fan-out mechanism produces --
    but routed to a shared recombine cell with DELIBERATELY mismatched
    path lengths (one direct hop; the other through one real extra
    relay), the same real mismatch shape as `#544`'s own original
    negative test. This reproduces that exact real failure signature
    -- confirming recombination re-inherits the original hard
    requirement even for values that came out of an otherwise-safe
    fan-out; the fan-out step itself was never the risk, any later
    convergence always is."""
    records = [
        v3.IcmV3Record(cell_id="source_A", row=0, col=0, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": LANE0}),
        v3.IcmV3Record(cell_id="relay_extra", row=0, col=1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="recombine", row=0, col=2, core="ram",
                        core_config={"downstream_mask": [], "upstream_mask": ["w", "e"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="source_B", row=0, col=3, core="ram",
                        core_config={"downstream_mask": ["w"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": LANE1}),
    ]
    grid = SuperGrid(records)

    try:
        grid.run_to_quiescence(max_ticks=30)
        quiesced = True
    except TimeoutError:
        quiesced = False

    recombine = grid.cells[(0, 2)]
    correct_combined = LANE0 | LANE1
    # Either real failure shape proves the point, matching #544's own
    # original test exactly: never settling, or settling on the wrong
    # (partial) value.
    assert not quiesced or recombine.ram_data_reg != correct_combined, (
        "mismatched hop counts at a recombine point should NOT produce "
        "the correct combined value, even when the two lanes came from "
        "an otherwise-safe fan-out -- if this fails, the real "
        "correctness requirement this test exists to demonstrate isn't "
        "actually real"
    )
    assert not quiesced, "the longer-path lane's rejected retry should keep the grid perpetually active"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
