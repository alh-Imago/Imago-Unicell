"""tests/vm/test_priority_multiway_v1.py — points.md #769: real tests
establishing what 3-way (single-cell) and 5-way (composed) `priority`
arbitration actually do, built specifically to answer Alan's own
direct question before wiring any of this into the LLVM/DSL compiler:
"test the 3 or 5 way connections first, that will determine how they
are applied."

Real, honest findings this file exists to nail down precisely, not
just assert:
1. A single `priority` cell physically maxes out at 3 real upstream
   directions (4 faces, one reserved for its own output) -- confirmed
   working correctly for real, distinct arrivals, served in rank order
   when all three are simultaneously present.
2. A single, plain two-arrival core (`adder`) fed by an N-way
   `priority` (N>2) does NOT sum all N real values -- it only ever
   combines the FIRST TWO real arrivals into one result; any further
   real arrival starts a genuinely NEW, separate capture round. This
   is the real, central finding that rules out "one wide priority
   feeding one adder" as a way to sum 3+ values.
3. `accumulator` is not a substitute either -- it adds a fixed real
   `step_amount` per arrival, not the arriving value itself, so it
   cannot sum arbitrary, distinct real values.
4. A genuine 5-way convergence requires COMPOSING two real `priority`
   cells (chained, with a real relay bridging any real gap between
   them) -- confirmed working: all 5 real, distinct values are
   delivered, none lost, none duplicated. The real SERVED ORDER is not
   a simple, global rank order across the whole composed structure --
   it is subject to real, genuine timing races (whichever real
   candidate happens to be present first at the moment of arbitration
   wins), a real, honest fact for any future compiler integration to
   account for.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from rats_nest_router_v1 import manhattan_route  # noqa: E402


def test_single_cell_three_way_priority_serves_in_rank_order():
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s", "w"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1, "priority_rank_w": 2,
                             "priority_rank_e": 0, "scheduling_mode": 0},
                     cell_id="pri", rel_row=0, rel_col=0)
    n_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="n_src", rel_row=-1, rel_col=0, preload_value=10)
    s_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="s_src", rel_row=1, rel_col=0, preload_value=20)
    w_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="w_src", rel_row=0, rel_col=-1, preload_value=30)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[pri, n_src, s_src, w_src, sink])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="three_way")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    sink_cell = grid.cells[(0, 1)]
    served = []
    prev_valid = False
    for _ in range(20):
        grid.tick()
        if sink_cell.ram_data_valid and not prev_valid:
            served.append(sink_cell.ram_data_reg)
            sink_cell.ram_data_valid = False
            sink_cell.pending_ack = 0
        prev_valid = sink_cell.ram_data_valid
    assert served == [10, 20, 30]  # exact rank order: n(0), s(1), w(2)


def test_a_plain_adder_only_combines_the_first_two_of_three_arrivals():
    """The real, central finding: feeding 3 real, distinct values
    through one priority arbitrator into one plain, two-arrival adder
    does NOT sum all three. Only the first two combine; the third
    starts a genuinely new, separate capture round."""
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s", "w"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1, "priority_rank_w": 2,
                             "priority_rank_e": 0, "scheduling_mode": 0},
                     cell_id="pri", rel_row=0, rel_col=0)
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "w", "out": "e"}, cell_id="add", rel_row=0, rel_col=1)
    n_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="n_src", rel_row=-1, rel_col=0, preload_value=10)
    s_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="s_src", rel_row=1, rel_col=0, preload_value=20)
    w_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="w_src", rel_row=0, rel_col=-1, preload_value=30)

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[pri, add, n_src, s_src, w_src])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="three_into_adder")
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    add_cell = grid.cells[(0, 1)]
    for _ in range(10):
        grid.tick()
    # The real, correct sum of the first two (10+20=30) is what the
    # adder's own real output holds -- NOT 60 (all three summed).
    assert add_cell.adder_data_valid is True
    assert add_cell.adder_out_buffer == 30  # 10 + 20 only
    # The third real value (30, from w) has already started a genuinely
    # NEW capture round -- confirmed directly, not assumed.
    assert add_cell.adder_a_reg == 30
    assert add_cell.adder_a_arrived is True


def test_composed_two_level_priority_delivers_all_five_values():
    """A genuine 5-way convergence requires composing two real priority
    cells -- confirmed working: all 5 real, distinct values delivered,
    none lost, none duplicated. Required a real relay to bridge the
    real gap between the two priority cells (they were not directly
    adjacent) -- the same real lesson #759 already established for
    relay chains in general."""
    pri1 = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s", "w"], "out": "e"},
                      params={"priority_rank_n": 0, "priority_rank_s": 1, "priority_rank_w": 2,
                              "priority_rank_e": 0, "scheduling_mode": 0},
                      cell_id="pri1", rel_row=0, rel_col=0)
    a = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="a", rel_row=-1, rel_col=0, preload_value=1)
    b = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="b", rel_row=1, rel_col=0, preload_value=2)
    c = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="c", rel_row=0, rel_col=-1, preload_value=3)
    relay = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="relay", rel_row=0, rel_col=1)
    pri2 = vtl.place(vtl.TILE_PRIORITY, {"in": ["w", "n", "s"], "out": "e"},
                      params={"priority_rank_w": 0, "priority_rank_n": 1, "priority_rank_s": 2,
                              "priority_rank_e": 0, "scheduling_mode": 0},
                      cell_id="pri2", rel_row=0, rel_col=2)
    d = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="d", rel_row=-1, rel_col=2, preload_value=4)
    e = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="e", rel_row=1, rel_col=2, preload_value=5)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=3)

    cells = [pri1, a, b, c, relay, pri2, d, e, sink]
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="five_way_composed")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    sink_cell = grid.cells[(0, 3)]
    served = []
    prev_valid = False
    for _ in range(40):
        grid.tick()
        if sink_cell.ram_data_valid and not prev_valid:
            served.append(sink_cell.ram_data_reg)
            sink_cell.ram_data_valid = False
            sink_cell.pending_ack = 0
        prev_valid = sink_cell.ram_data_valid
    # All 5 real, distinct values arrive -- none lost, none duplicated.
    # The real SERVED ORDER is not asserted here beyond that, since it
    # is genuinely subject to real timing races between the two real
    # priority cells, not a simple, global rank order -- a real, honest
    # fact this test exists specifically to surface, not paper over.
    assert sorted(served) == [1, 2, 3, 4, 5]


def test_configured_rank_does_not_override_real_arrival_order():
    """points.md #770: the real, important correction to #751's own
    earlier claim that priority solves non-commutative operand order
    'for free.' That claim was only ever tested with two EQUIDISTANT
    real operands. Confirmed directly here: when the two real paths
    have DIFFERENT real lengths, whichever operand arrives FIRST wins
    the real 'A' slot at a downstream subtractor, REGARDLESS of its own
    configured priority_rank_* -- rank only decides among candidates
    that are genuinely, simultaneously PRESENT at the moment of real
    arbitration; it cannot reach back in time to prefer a candidate
    that simply hasn't arrived yet."""
    occ = {}
    cells = []
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id="pri", rel_row=0, rel_col=0)
    sub = vtl.place(vtl.TILE_SUBTRACTOR, {"in_a": "w", "in_b": "w", "out": "e"}, cell_id="sub", rel_row=0, rel_col=1)
    cells += [pri, sub]
    occ[(0, 0)] = "pri"
    occ[(0, 1)] = "sub"

    # a (value 100): rank 0 -- configured to WIN -- but 3 real relay
    # hops away (should arrive LATE if rank were irrelevant to timing).
    a_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="a_src", rel_row=-4, rel_col=0, preload_value=100)
    cells.append(a_src)
    occ[(-4, 0)] = "a_src"
    cells += manhattan_route((-4, 0), "s", (-1, 0), "s", "ra", occ)

    # b (value 3): rank 1 -- configured to LOSE -- but directly
    # adjacent (0 real hops, arrives immediately).
    b_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="b_src", rel_row=1, rel_col=0, preload_value=3)
    cells.append(b_src)
    occ[(1, 0)] = "b_src"

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="order_race_test")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    sub_cell = grid.cells[(0, 1)]
    for _ in range(15):
        grid.tick()
    # b (rank 1, the configured LOSER) arrives first and becomes "A" --
    # the real result is 3 - 100 (wrapping in 32-bit unsigned), NOT
    # 100 - 3 -- confirming rank alone did NOT determine operand order
    # once the two real paths had different real lengths.
    expected_wrong_order = (3 - 100) & 0xFFFFFFFF
    assert sub_cell.adder_out_buffer == expected_wrong_order
    assert sub_cell.adder_a_reg == 3  # b, the configured loser, became "A"


def test_equalizing_path_lengths_restores_rank_as_the_real_decider():
    """points.md #771: Alan's own direct proposed fix for #770's own
    real finding -- pad the SHORTER real path (right before the
    priority cell, not anywhere else) so both real operands arrive
    with EQUAL real length. Confirmed directly: this genuinely restores
    priority_rank_* as the real decider, since both real candidates are
    now genuinely, simultaneously present at the moment of real
    arbitration, which is the exact real condition #770 found rank
    actually depends on. Same real values and ranks as #770's own
    failing case -- only the real path lengths are now equal."""
    occ = {}
    cells = []
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id="pri", rel_row=0, rel_col=0)
    sub = vtl.place(vtl.TILE_SUBTRACTOR, {"in_a": "w", "in_b": "w", "out": "e"}, cell_id="sub", rel_row=0, rel_col=1)
    cells += [pri, sub]
    occ[(0, 0)] = "pri"
    occ[(0, 1)] = "sub"

    # a (value 100): rank 0 -- 3 real relay hops, same as #770.
    a_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="a_src", rel_row=-4, rel_col=0, preload_value=100)
    cells.append(a_src)
    occ[(-4, 0)] = "a_src"
    cells += manhattan_route((-4, 0), "s", (-1, 0), "s", "ra", occ)

    # b (value 3): rank 1 -- NOW also padded to 3 real relay hops,
    # matching a's own real length exactly (the real fix).
    b_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="b_src", rel_row=4, rel_col=0, preload_value=3)
    cells.append(b_src)
    occ[(4, 0)] = "b_src"
    cells += manhattan_route((4, 0), "n", (1, 0), "n", "rb", occ)

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="equalized_order_test")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    sub_cell = grid.cells[(0, 1)]
    for _ in range(15):
        grid.tick()
    # With equal real path lengths, a (rank 0, the configured winner)
    # now genuinely wins and becomes "A" -- the correct real result.
    assert sub_cell.adder_out_buffer == 97  # 100 - 3, correct
    assert sub_cell.adder_a_reg == 100  # a, the configured winner, correctly became "A"


def test_sequenced_channel_mode_guarantees_order_without_path_equalization():
    """points.md #772: Alan's own direct, alternative proposal to
    #771's path-equalization fix -- a real, third priority mode
    ('sequenced channel', scheduling_mode=2) that doesn't arbitrate by
    rank among whoever's present at all. Instead, much like sequencer's
    own fixed, cyclic seq_index, it holds a real, fixed turn order and
    ONLY ever accepts the currently-due direction, ignoring any other
    real arrival no matter how early it shows up.

    Confirmed directly against the EXACT SAME real scenario #770/#771
    used -- a (value 100) 3 real relay hops away, b (value 3) directly
    adjacent -- but this time with NO path-length equalization at all.
    The sequenced-channel mode correctly waits for a's own turn (4
    real ticks after b has already been sitting, unconsumed, since
    tick 1), then serves b second -- the real, correct result (97,
    100-3), guaranteed by the cell's own real, internal state machine
    rather than by the compiler equalizing physical distance.

    Real, honest, deliberate trade-off named directly: this is REAL,
    genuine head-of-line blocking -- b's own real value sat completely
    unconsumed for the entire real time a's own value was still in
    transit. #771's own path-equalization fix has no such delay (both
    real values arrive together); this mode trades that away for a
    real guarantee that doesn't depend on the compiler getting
    distances exactly right.

    Real, honest scope: this is a real, working VM PROTOTYPE only --
    priority_cell_v4c.v's own real RTL has no such mode today
    (scheduling_mode is a real, single hardware bit, strict/weighted-RR
    only) -- a genuine third mode would need real, separate RTL work,
    not attempted here."""
    import icm_v3 as v3
    from unicell_super_automaton_v1 import N, S

    records = [
        v3.IcmV3Record(cell_id="a_src", row=-4, col=0, core="ram",
                        core_config={"downstream_mask": ["s"], "fixed_mode": 0}, preload_value=100),
        v3.IcmV3Record(cell_id="ra1", row=-3, col=0, core="ram",
                        core_config={"upstream_mask": ["n"], "downstream_mask": ["s"]}),
        v3.IcmV3Record(cell_id="ra2", row=-2, col=0, core="ram",
                        core_config={"upstream_mask": ["n"], "downstream_mask": ["s"]}),
        v3.IcmV3Record(cell_id="ra3", row=-1, col=0, core="ram",
                        core_config={"upstream_mask": ["n"], "downstream_mask": ["s"]}),
        v3.IcmV3Record(cell_id="b_src", row=1, col=0, core="ram",
                        core_config={"downstream_mask": ["n"], "fixed_mode": 0}, preload_value=3),
        v3.IcmV3Record(cell_id="pri", row=0, col=0, core="priority",
                        core_config={"upstream_mask": ["n", "s"], "downstream_mask": ["e"],
                                     "priority_rank_n": 0, "priority_rank_s": 0, "scheduling_mode": 2}),
        v3.IcmV3Record(cell_id="sub", row=0, col=1, core="adder",
                        core_config={"upstream_mask": ["w"], "downstream_mask": [], "subtract_mode": 1}),
    ]
    grid = SuperGrid(records)
    pri_cell = grid.cells[(0, 0)]
    assert pri_cell.pri_scheduling_mode == 2  # confirms the real int, not cast to a bool
    pri_cell.pri_seq_order = (N, S)  # a (north) due first, then b (south)

    sub_cell = grid.cells[(0, 1)]
    for _ in range(15):
        grid.tick()
    assert sub_cell.adder_out_buffer == 97  # 100 - 3, correct
    assert sub_cell.adder_a_reg == 100  # a correctly became "A", despite b arriving first


def test_non_power_of_two_leftover_needs_extra_padding_not_just_equal_hops():
    """points.md #773: Alan's own direct, precise concern -- for a
    non-power-of-2 reduction (N=3 here: (1-2)-3, left-to-right
    subtraction), the 'leftover' value (3) must land as the real
    subtrahend/B at the second real subtractor, with t1's own output
    (1-2) correctly landing as the real minuend/A -- regardless of
    which one physically arrives first.

    Confirmed directly, and confirmed MORE SUBTLE than #771's own
    simple two-leaf case: EQUAL real hop counts are NOT enough here,
    because t1 is a real, COMPOSED piece (a subtractor's own output),
    which becomes ready at a real, LATER tick than a raw, preloaded
    leaf like the leftover -- exactly the real distinction `#765`'s own
    `composed_output_ready_tick()` already names. The leftover's own
    real path needed MORE hops than t1's own path (8 vs 4, empirically
    found here) to correctly arrive second, not merely an equal count."""
    occ = {}
    cells = []
    pri1 = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                      params={"priority_rank_n": 0, "priority_rank_s": 1,
                              "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                      cell_id="pri1", rel_row=0, rel_col=0)
    sub1 = vtl.place(vtl.TILE_SUBTRACTOR, {"in_a": "w", "in_b": "w", "out": "n"}, cell_id="sub1", rel_row=0, rel_col=1)
    cells += [pri1, sub1]
    occ[(0, 0)] = "pri1"
    occ[(0, 1)] = "sub1"
    one = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="one", rel_row=-1, rel_col=0, preload_value=1)
    two = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="two", rel_row=1, rel_col=0, preload_value=2)
    cells += [one, two]
    occ[(-1, 0)] = "one"
    occ[(1, 0)] = "two"

    pri2 = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                      params={"priority_rank_n": 0, "priority_rank_s": 1,
                              "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                      cell_id="pri2", rel_row=0, rel_col=4)
    sub2 = vtl.place(vtl.TILE_SUBTRACTOR, {"in_a": "w", "in_b": "w", "out": "e"}, cell_id="sub2", rel_row=0, rel_col=5)
    cells += [pri2, sub2]
    occ[(0, 4)] = "pri2"
    occ[(0, 5)] = "sub2"

    route_t1 = manhattan_route((0, 1), "n", (-1, 4), "s", "rt1", occ)  # 4 real hops
    cells += route_t1

    # The leftover (3): a real, empirically-confirmed EXTRA-padded
    # path (8 real hops, not the naive "equal to t1's 4") is required
    # to correctly arrive second.
    three_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="three", rel_row=6, rel_col=1, preload_value=3)
    occ[(6, 1)] = "three"
    route_3 = manhattan_route((6, 1), "e", (1, 4), "n", "r3", occ)
    cells.append(three_src)
    cells += route_3

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="n3_subtract")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(25):
        grid.tick()
    sub2_cell = grid.cells[(0, 5)]
    # (1-2)-3 = -4, wrapped in 32-bit unsigned.
    assert sub2_cell.adder_out_buffer == ((-4) & 0xFFFFFFFF)
    assert sub2_cell.adder_a_reg == ((1 - 2) & 0xFFFFFFFF)  # t1's own output, correctly "A"


def test_sequential_fold_for_non_power_of_two_n_hits_the_same_order_race():
    """points.md #773: Alan's own direct, precise prediction confirmed
    directly -- for N that isn't a power of 2 (e.g. N=3), a sequential
    FOLD is needed: t1 = v1-v2 (two raw leaves), then t2 = t1-v3 (t1 is
    now a COMPUTED RESULT, not a raw leaf, converging with a fresh raw
    leaf v3). Alan's own words: 'the arrival order of 1,2,3... now the
    next step is 1, so that value now has to be the second, so the step
    of 3 will become a problem for the two arrival models.'

    Confirmed directly: v3 (ready from tick 1) races ahead of t1's own
    computed result (not ready until tick 3, arriving at t2 even later)
    and wrongly wins the real 'A' slot -- the exact same real hazard
    #770 found for two raw leaves, now confirmed to recur identically
    when one operand is itself a prior computation's own result."""
    import icm_v3 as v3
    records = [
        v3.IcmV3Record(cell_id="v1", row=0, col=-1, core="ram", core_config={"downstream_mask": ["e"], "fixed_mode": 0}, preload_value=10),
        v3.IcmV3Record(cell_id="v2", row=2, col=0, core="ram", core_config={"downstream_mask": ["n"], "fixed_mode": 0}, preload_value=3),
        v3.IcmV3Record(cell_id="v2_relay", row=1, col=0, core="ram", core_config={"upstream_mask": ["s"], "downstream_mask": ["n"]}),
        v3.IcmV3Record(cell_id="t1", row=0, col=0, core="adder",
                        core_config={"upstream_mask": ["w", "s"], "downstream_mask": ["e"], "subtract_mode": 1}),
        v3.IcmV3Record(cell_id="v3", row=1, col=1, core="ram", core_config={"downstream_mask": ["n"], "fixed_mode": 0}, preload_value=2),
        v3.IcmV3Record(cell_id="t2", row=0, col=1, core="adder",
                        core_config={"upstream_mask": ["w", "s"], "downstream_mask": [], "subtract_mode": 1}),
    ]
    grid = SuperGrid(records)
    for _ in range(15):
        grid.tick()
    t2_cell = grid.cells[(0, 1)]
    # v3 wrongly won the real "A" slot -- the real, wrong result is
    # v3 - t1's_result (2 - 7 = -5), NOT the intended t1's_result - v3.
    assert t2_cell.adder_out_buffer == ((2 - 7) & 0xFFFFFFFF)
    assert t2_cell.adder_a_reg == 2  # v3, the raw leaf, wrongly became "A"


def test_sequenced_channel_priority_fixes_the_sequential_fold_order():
    """points.md #773: confirms the sequenced-channel mode (#772)
    generalizes correctly to the sequential-fold case -- inserting one
    real priority cell (scheduling_mode=2) between t1's own result and
    t2, configured to wait specifically for t1's own direction first,
    correctly holds v3 (which arrives far earlier) until t1's own
    result is genuinely ready, regardless of the real timing gap."""
    import icm_v3 as v3
    from unicell_super_automaton_v1 import W, S
    records = [
        v3.IcmV3Record(cell_id="v1", row=0, col=-1, core="ram", core_config={"downstream_mask": ["e"], "fixed_mode": 0}, preload_value=10),
        v3.IcmV3Record(cell_id="v2", row=2, col=0, core="ram", core_config={"downstream_mask": ["n"], "fixed_mode": 0}, preload_value=3),
        v3.IcmV3Record(cell_id="v2_relay", row=1, col=0, core="ram", core_config={"upstream_mask": ["s"], "downstream_mask": ["n"]}),
        v3.IcmV3Record(cell_id="t1", row=0, col=0, core="adder",
                        core_config={"upstream_mask": ["w", "s"], "downstream_mask": ["e"], "subtract_mode": 1}),
        v3.IcmV3Record(cell_id="v3", row=1, col=1, core="ram", core_config={"downstream_mask": ["n"], "fixed_mode": 0}, preload_value=2),
        v3.IcmV3Record(cell_id="pri", row=0, col=1, core="priority",
                        core_config={"upstream_mask": ["w", "s"], "downstream_mask": ["e"],
                                     "priority_rank_n": 0, "priority_rank_s": 0, "scheduling_mode": 2}),
        v3.IcmV3Record(cell_id="t2", row=0, col=2, core="adder",
                        core_config={"upstream_mask": ["w"], "downstream_mask": [], "subtract_mode": 1}),
    ]
    grid = SuperGrid(records)
    pri_cell = grid.cells[(0, 1)]
    pri_cell.pri_seq_order = (W, S)  # t1's own result (west) due first, v3 (south) second
    for _ in range(20):
        grid.tick()
    t2_cell = grid.cells[(0, 2)]
    assert t2_cell.adder_out_buffer == 5  # (10-3)-2, correct
    assert t2_cell.adder_a_reg == 7  # t1's own result correctly became "A"
