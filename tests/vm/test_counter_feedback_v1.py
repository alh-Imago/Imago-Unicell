"""tests/vm/test_counter_feedback_v1.py — points.md #810: the counter mechanism WITH FEEDBACK (Alan): per-chain
counters gated by the sentinel's in-flight count, backpressure from a stalled chain, the priority cell versus a
fixed-order scan, and the shared single port. The priority-cell semantics are checked on the REAL VM cell.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import counter_feedback_v1 as CF  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
import vix_tile_library_v1 as vtl  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from vix_dag_dispatcher_v1 import _dir_const  # noqa: E402

M = 0xFFFFFFFF
F = lambda x: (x * 3 + 1) & M                                                       # noqa: E731
INPUTS = [[10, 11, 12, 13, 14, 15], [20, 21, 22, 23, 24, 25]]
EXPECT = [[F(x) for x in row] for row in INPUTS]
STALL0 = {0: (4, 70)}                                                              # chain 0 cannot hand over, rounds 4..69


def cfgs(n=2, **kw):
    return [CF.ChainCfg(**kw) for _ in range(n)]


# ---- the priority cell, on the REAL VM ------------------------------------------------------------------

def _priority_vm(mode, feed_a, feed_b):
    cells = [
        vix.HierCell(cell_id="srcA", rel_row=4, rel_col=5, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["s"]}),
        vix.HierCell(cell_id="srcB", rel_row=6, rel_col=5, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["n"]}),
        vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                  params={"priority_rank_n": 0, "priority_rank_s": 0, "priority_rank_e": 0, "priority_rank_w": 0,
                          "scheduling_mode": mode}, cell_id="pri", rel_row=5, rel_col=5),
        vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=5, rel_col=6),
    ]
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                         placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))], name="t")
    g = SuperGrid(icm.flatten()[0])
    if mode == 2:
        g.cells[(5, 5)].pri_seq_order = (_dir_const("n"), _dir_const("s"))     # serve NORTH first
    if feed_a:
        g.cells[(4, 5)].ram_data_reg, g.cells[(4, 5)].ram_data_valid = 111, True
    if feed_b:
        g.cells[(6, 5)].ram_data_reg, g.cells[(6, 5)].ram_data_valid = 222, True
    for _ in range(80):
        g.tick()
    s = g.cells[(5, 6)]
    return s.ram_data_reg, s.ram_data_valid


def test_a_priority_cell_serves_the_live_source_when_the_other_never_offers():
    """The stalled part (A) never offers. PRIORITY passes B; a fixed-order SEQUENCER passes NOTHING -- one stalled
    part stops everything. This is the real cell, not the model."""
    assert _priority_vm(0, feed_a=False, feed_b=True) == (222, True)
    assert _priority_vm(2, feed_a=False, feed_b=True) == (0, False)


def test_both_scheduling_modes_agree_when_nothing_is_stalled():
    assert _priority_vm(0, True, True) == _priority_vm(2, True, True) == (111, True)


# ---- baseline ---------------------------------------------------------------------------------------------

def test_two_chains_with_no_stall_complete_correctly_in_order_with_the_window_respected():
    r = CF.run(cfgs(), INPUTS, F)
    assert r.done and not r.deadlocked and r.per_chain == EXPECT
    assert r.max_in_flight == [1, 1] and r.sentinel_errors == [] and r.tree_blocked_rounds == 0
    assert sorted(r.bram_out) == list(range(12))                          # densely packed: an address advances only on a capture
    assert {(c, s) for c, s, _ in r.bram_out.values()} == {(c, s) for c in (0, 1) for s in range(6)}


def test_a_larger_credit_window_lets_more_items_be_in_flight_and_finishes_sooner():
    slow = CF.run(cfgs(window=1, in_depth=2, out_depth=2), INPUTS, F)
    fast = CF.run(cfgs(window=2, in_depth=2, out_depth=2), INPUTS, F)
    assert slow.max_in_flight == [1, 1] and max(fast.max_in_flight) == 2
    assert fast.rounds < slow.rounds and fast.per_chain == slow.per_chain == EXPECT


# ---- the stalled chain: the 2 x 2 --------------------------------------------------------------------------

def test_priority_arbitration_keeps_the_healthy_chain_moving_while_the_other_is_stalled():
    r = CF.run(cfgs(), INPUTS, F, arbiter="priority", feedback=True, stall_out=STALL0)
    assert r.finished_round(1) < 40                                        # the healthy chain finishes long BEFORE the stall clears
    assert r.tree_blocked_rounds == 0 and r.read_wait_rounds == 0 and r.sentinel_errors == []
    assert r.done and r.per_chain == EXPECT                                # and everything completes once the stall clears


def test_a_fixed_order_scan_lets_the_stalled_chain_stop_the_healthy_one_head_of_line_blocking():
    r = CF.run(cfgs(), INPUTS, F, arbiter="scan", feedback=True, stall_out=STALL0)
    assert r.finished_round(1) > 70                                       # the healthy chain STARVES until the stall clears
    assert r.progress_between(1, 10, 60) == 0
    assert r.read_wait_rounds > 50
    assert r.done and r.per_chain == EXPECT                               # not a deadlock: it resumes when the stall clears


def test_feedback_stops_ram_requests_stalling_themselves_on_a_loaded_chain():
    on = CF.run(cfgs(), INPUTS, F, arbiter="priority", feedback=True, stall_out=STALL0)
    off = CF.run(cfgs(), INPUTS, F, arbiter="priority", feedback=False, stall_out=STALL0)
    assert on.tree_blocked_rounds == 0
    assert off.tree_blocked_rounds > 50                                   # an item for the full chain sits IN the tree
    assert off.finished_round(1) > on.finished_round(1)


def test_a_free_running_counter_overruns_its_window_and_the_sentinel_latches_it():
    off = CF.run(cfgs(), INPUTS, F, feedback=False, stall_out=STALL0)
    on = CF.run(cfgs(), INPUTS, F, feedback=True, stall_out=STALL0)
    assert off.sentinel_errors and any("overflow=True" in e for e in off.sentinel_errors)
    assert on.sentinel_errors == []


def test_backpressure_stops_the_stalled_chains_own_counter_at_its_credit_limit():
    r = CF.run(cfgs(), INPUTS, F, arbiter="priority", feedback=True, stall_out=STALL0)
    assert r.max_in_flight[0] <= 1                                        # it never took more than its window
    stalled_at = r.collected_by_round[40]
    assert stalled_at[0] <= 3                                             # and made little progress while blocked


def test_an_input_side_stall_is_isolated_by_priority_and_starves_the_scan():
    stall_in = {0: (3, 60)}
    pri = CF.run(cfgs(), INPUTS, F, arbiter="priority", feedback=True, stall_in=stall_in)
    scan = CF.run(cfgs(), INPUTS, F, arbiter="scan", feedback=True, stall_in=stall_in)
    assert pri.finished_round(1) < 40 and scan.finished_round(1) > 60
    assert pri.done and scan.done


def test_a_stall_that_never_clears_only_ever_holds_up_its_own_chain_under_priority():
    r = CF.run(cfgs(), INPUTS, F, arbiter="priority", feedback=True, stall_out={0: (2, 10 ** 6)}, max_rounds=200)
    assert r.per_chain[1] == EXPECT[1]                                    # the healthy chain still finishes everything
    assert not r.done and len(r.per_chain[0]) < 6


def test_the_write_side_gather_needs_the_priority_cell_too():
    scan = CF.run(cfgs(), INPUTS, F, arbiter="priority", gather="scan", feedback=True, stall_out=STALL0)
    pri = CF.run(cfgs(), INPUTS, F, arbiter="priority", gather="priority", feedback=True, stall_out=STALL0)
    assert pri.finished_round(1) < scan.finished_round(1)


# ---- the single (shared) port --------------------------------------------------------------------------------

def test_a_shared_port_completes_correctly_with_reads_deferred_behind_writes():
    """NOTE the limit of this model: the RTL hazard `shared_bram_arbiter_v1.v` guards against -- a single-cycle read
    command pulse silently LOST inside the splitter when it loses the port -- cannot occur at this abstraction (the
    counter only advances on an actual issue, so a deferred read is simply retried; dropping the queue changes
    nothing observable here, checked by mutation). So this test shows correctness and the COST of sharing, not that
    the queue prevents loss."""
    r = CF.run(cfgs(), INPUTS, F, ports=1)
    assert r.done and r.per_chain == EXPECT and r.sentinel_errors == []
    assert r.reads_deferred > 0                                           # a read lost the port to a write ...
    assert sorted(r.bram_out) == list(range(12)) and len(r.bram_out) == 12   # ... but every item was processed exactly once
    assert r.writes_delayed_by_reads == 0                                 # structural: writes are evaluated first (write priority)


def test_the_shared_port_costs_rounds_the_two_port_plan_does_not():
    one = CF.run(cfgs(), INPUTS, F, ports=1)
    two = CF.run(cfgs(), INPUTS, F, ports=2)
    assert one.rounds > two.rounds and one.per_chain == two.per_chain == EXPECT


def test_a_shared_port_still_isolates_a_stalled_chain_under_priority_and_not_under_scan():
    pri = CF.run(cfgs(), INPUTS, F, ports=1, arbiter="priority", stall_out=STALL0)
    scan = CF.run(cfgs(), INPUTS, F, ports=1, arbiter="scan", stall_out=STALL0)
    assert pri.finished_round(1) < 50 and scan.finished_round(1) > 70
    assert pri.done and scan.done and pri.per_chain == EXPECT


# ---- generality and honesty about the limit -----------------------------------------------------------------

@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_the_model_runs_any_number_of_chains_the_limit_of_two_is_not_derived_here(n):
    inputs = [[100 * c + k for k in range(4)] for c in range(n)]
    r = CF.run(cfgs(n), inputs, F, max_rounds=400)
    assert r.done and r.per_chain == [[F(x) for x in row] for row in inputs]


def test_with_more_chains_a_stalled_one_still_only_holds_up_itself_under_priority():
    inputs = [[100 * c + k for k in range(4)] for c in range(4)]
    r = CF.run(cfgs(4), inputs, F, arbiter="priority", stall_out={2: (3, 90)}, max_rounds=400)
    assert all(r.finished_round(c) is not None and r.finished_round(c) < 60 for c in (0, 1, 3))   # the three healthy chains finish early
    assert r.finished_round(2) > 90 or r.finished_round(2) is None                              # only the stalled one waits


def test_invalid_arguments_are_refused():
    with pytest.raises(ValueError):
        CF.run(cfgs(), INPUTS, F, arbiter="lottery")
    with pytest.raises(ValueError):
        CF.run(cfgs(), INPUTS, F, ports=3)


# ---- ONE shared credit-return link instead of a feedback line per chain (points.md #811) -----------------------

def _mk(w, d):
    return [CF.ChainCfg(window=w, in_depth=d, out_depth=d) for _ in range(2)]


def test_a_shared_credit_return_link_is_correct_but_slower_at_a_small_window():
    per_chain = CF.run(_mk(1, 1), INPUTS, F)
    shared = CF.run(_mk(1, 1), INPUTS, F, credit_link=2)
    assert shared.per_chain == per_chain.per_chain == EXPECT and shared.sentinel_errors == []
    assert shared.rounds > per_chain.rounds                                # credits arrive late and one at a time


def test_a_bigger_window_and_buffers_cover_the_return_latency_and_recover_the_throughput():
    """The COST of the single shared channel is buffer depth, not correctness."""
    per_chain = CF.run(_mk(3, 3), INPUTS, F)
    for delay in (2, 5):
        shared = CF.run(_mk(3, 3), INPUTS, F, credit_link=delay)
        assert shared.per_chain == EXPECT and shared.rounds <= per_chain.rounds + 2 + delay // 2
    small = CF.run(_mk(1, 1), INPUTS, F, credit_link=5)
    assert small.rounds > 2 * per_chain.rounds


def test_a_longer_return_route_costs_more_rounds_at_the_same_window():
    rounds = [CF.run(_mk(1, 1), INPUTS, F, credit_link=d).rounds for d in (0, 2, 5)]
    assert rounds[0] < rounds[1] < rounds[2]


def test_the_shared_link_still_isolates_a_stalled_chain_under_priority():
    r = CF.run(_mk(2, 2), INPUTS, F, arbiter="priority", stall_out=STALL0, credit_link=3)
    assert r.finished_round(1) < 45 and r.tree_blocked_rounds == 0 and r.sentinel_errors == []
    assert r.done and r.per_chain == EXPECT


# ---- the BRAM side: read latency, and the control that says "the feed's out, here is the next address" (#812) -------

ONE = [[10, 11, 12, 13, 14, 15, 16, 17]]
ONE_EXPECT = [[F(x) for x in ONE[0]]]


def _one(**kw):
    return CF.run([CF.ChainCfg(window=8, in_depth=8, out_depth=8, latency=1)], ONE, F, feedback=False, **kw)


@pytest.mark.parametrize("latency", [1, 2, 3])
def test_ack_driven_advance_absorbs_any_bram_latency_without_losing_a_read(latency):
    """`addr_counter_v1`'s advance_en is driven by the genuine ack, never a cycle count (#256); when the real latency
    doubled (#284) nothing else had to change. The results are identical at every latency; only the time differs."""
    r = _one(bram_latency=latency, advance="ack", outstanding=1)
    assert r.per_chain == ONE_EXPECT and r.lost_reads == 0 and r.done


def test_ack_driven_time_grows_with_the_latency_and_nothing_else_changes():
    rounds = [_one(bram_latency=lat, advance="ack", outstanding=1).rounds for lat in (1, 2, 3)]
    assert rounds[0] < rounds[1] < rounds[2]


def test_a_counter_that_assumes_the_latency_works_until_the_latency_changes():
    """A free-running counter with one command per round is right for a 1-cycle BRAM and silently loses reads on a 2-cycle
    one -- exactly the assumption `absorb the latency, do not assume it` (#243/#285) exists to avoid."""
    assert _one(bram_latency=1, advance="fixed", fixed_period=1, outstanding=1).per_chain == ONE_EXPECT
    bad = _one(bram_latency=2, advance="fixed", fixed_period=1, outstanding=1)
    assert bad.lost_reads > 0 and bad.per_chain != ONE_EXPECT and len(bad.per_chain[0]) < 8
    assert not bad.done and not bad.deadlocked                             # it is DATA LOSS, not a deadlock


def test_a_fixed_period_tuned_for_one_latency_breaks_at_a_slower_one():
    assert _one(bram_latency=2, advance="fixed", fixed_period=2, outstanding=1).per_chain == ONE_EXPECT
    bad = _one(bram_latency=3, advance="fixed", fixed_period=2, outstanding=1)
    assert bad.lost_reads == 4 and len(bad.per_chain[0]) == 4


def test_the_next_address_is_released_the_round_the_previous_feed_comes_out():
    """'ok, the feed's out, here's the next address': with one read in the interface the next command is issued no
    earlier than the delivery of the previous data."""
    r = _one(bram_latency=2, advance="ack", outstanding=1)
    issue = [t for t, _, _ in r.issue_log]
    out = [t for t, _, _ in r.deliver_log]
    assert all(issue[k + 1] >= out[k] for k in range(len(issue) - 1))
    assert all(out[k] - issue[k] == 2 for k in range(len(issue)))          # the latency is honoured exactly


def test_holding_at_least_latency_reads_in_the_interface_restores_one_item_per_round():
    """`#256`: the counter has already advanced and the next pair's read is already in flight -- 2-cycle latency,
    1-cycle throughput at steady state."""
    for latency in (2, 3):
        slow = _one(bram_latency=latency, advance="ack", outstanding=1).rounds
        fast = _one(bram_latency=latency, advance="ack", outstanding=latency).rounds
        assert fast < slow and fast <= 8 + latency + 3
        assert _one(bram_latency=latency, advance="ack", outstanding=latency).per_chain == ONE_EXPECT


def test_credit_gating_counts_reads_still_in_the_bram_so_nothing_overruns_the_chain():
    cfg2 = [CF.ChainCfg(window=2, in_depth=2, out_depth=2) for _ in range(2)]
    r = CF.run(cfg2, INPUTS, F, bram_latency=3, advance="ack", outstanding=3, feedback=True)
    assert r.per_chain == EXPECT and r.lost_reads == 0 and r.sentinel_errors == []
    assert r.tree_blocked_rounds == 0 and max(r.max_in_flight) <= 2


def test_the_stalled_chain_is_still_isolated_with_a_bram_latency_and_priority():
    cfg2 = [CF.ChainCfg(window=2, in_depth=2, out_depth=2) for _ in range(2)]
    pri = CF.run(cfg2, INPUTS, F, arbiter="priority", bram_latency=2, outstanding=2, stall_out=STALL0)
    scan = CF.run(cfg2, INPUTS, F, arbiter="scan", bram_latency=2, outstanding=2, stall_out=STALL0)
    assert pri.finished_round(1) < 45 and scan.finished_round(1) > 65
    assert pri.done and scan.done and pri.per_chain == EXPECT and pri.lost_reads == scan.lost_reads == 0


# ---- the address supply: a counter, or a simple RAM that passes addresses through ------------------------------

BRAM = {a: 100 + a for a in range(20)}


def test_an_address_ram_supplies_any_sequence_through_the_same_handshake():
    order = [[7, 2, 9, 4], [15, 11, 13, 12]]
    cfgs2 = [CF.ChainCfg(window=4, in_depth=4, out_depth=4) for _ in range(2)]
    r = CF.run(cfgs2, [[0] * 4, [0] * 4], F, addresses=order, bram=BRAM, addr_source="ram", bram_latency=2, outstanding=2)
    assert r.per_chain == [[F(BRAM[a]) for a in row] for row in order] and r.lost_reads == 0


def test_a_counter_can_only_supply_sequential_addresses():
    cfgs2 = [CF.ChainCfg() for _ in range(2)]
    seq = [[3, 4, 5, 6], [10, 11, 12, 13]]
    ok = CF.run(cfgs2, [[0] * 4, [0] * 4], F, addresses=seq, bram=BRAM, addr_source="counter", bram_latency=1)
    assert ok.per_chain == [[F(BRAM[a]) for a in row] for row in seq]
    with pytest.raises(ValueError, match="SEQUENTIAL"):
        CF.run(cfgs2, [[0] * 4, [0] * 4], F, addresses=[[3, 5, 4, 6], [10, 11, 12, 13]], bram=BRAM, addr_source="counter")


def test_the_counter_and_the_address_ram_have_identical_timing_only_the_address_order_differs():
    """Both need the same control mechanism; the RAM is the flexible one, the counter the simpler."""
    seq = [[3, 4, 5, 6], [10, 11, 12, 13]]
    cfgs2 = [CF.ChainCfg(window=4, in_depth=4, out_depth=4) for _ in range(2)]
    a = CF.run(cfgs2, [[0] * 4] * 2, F, addresses=seq, bram=BRAM, addr_source="counter", bram_latency=2, outstanding=2)
    b = CF.run(cfgs2, [[0] * 4] * 2, F, addresses=seq, bram=BRAM, addr_source="ram", bram_latency=2, outstanding=2)
    assert a.rounds == b.rounds and a.per_chain == b.per_chain and a.issue_log == b.issue_log


def test_bram_side_arguments_are_validated():
    with pytest.raises(ValueError):
        CF.run(cfgs(), INPUTS, F, bram_latency=65)                        # a sanity bound only: the latency is NOT a fixed value
    assert CF.run(cfgs(), INPUTS, F, bram_latency=4, max_rounds=300).done   # 4 is fine (was refused when 1-3 was assumed)
    with pytest.raises(ValueError):
        CF.run(cfgs(), INPUTS, F, bram_latency=[2, 0, 3])                 # every per-read entry must be >= 1
    with pytest.raises(ValueError):
        CF.run(cfgs(), INPUTS, F, advance="whenever")
    with pytest.raises(ValueError, match="need the bram"):
        CF.run(cfgs(), INPUTS, F, addresses=[[1], [2]])


def test_reads_still_in_the_bram_must_count_against_a_stalled_chains_credit():
    """The case that matters: a chain that has stopped draining while several reads are still in the BRAM pipeline. If the
    credit ignored those, the counter would keep issuing, the data would arrive at a full chain and block the delivery path
    for everyone, and the sentinel would latch overflow. Counting them keeps the stalled chain's issues within its window."""
    tight = [CF.ChainCfg(window=1, in_depth=1, out_depth=1) for _ in range(2)]
    r = CF.run(tight, INPUTS, F, arbiter="priority", bram_latency=3, outstanding=3, feedback=True,
               stall_out={0: (2, 80)}, max_rounds=400)
    assert r.tree_blocked_rounds == 0 and r.sentinel_errors == []
    assert max(r.max_in_flight) <= 1                                      # never more than the window, including reads in flight
    assert r.finished_round(1) < 40                                       # the healthy chain is not held up by the stalled one
    assert r.done and r.per_chain == EXPECT and r.lost_reads == 0


# ---- NO FIXED LATENCY, and WHICH ack releases the next address (points.md #813) --------------------------------

LATS = [1, 5, 2, 8, 3, 1, 6, 2]
CH2 = lambda: [CF.ChainCfg(window=2, in_depth=2, out_depth=2, latency=2) for _ in range(2)]   # noqa: E731
I8 = [[10, 11, 12, 13, 14, 15, 16, 17], [20, 21, 22, 23, 24, 25, 26, 27]]
E8 = [[F(x) for x in row] for row in I8]


def test_alans_rule_for_which_ack_releases_the_next_address():
    """BRAM on two buses -> feed in; BRAM on one bus -> feed out; DSP -> feed out. Mapped onto 'delivered' (data into the
    chain) and 'result_out' (result left the chain) -- my reading of his words, not yet confirmed by him."""
    assert CF.default_release(2, "bram") == "delivered"
    assert CF.default_release(1, "bram") == "result_out"
    assert CF.default_release(1, "dsp") == CF.default_release(2, "dsp") == "result_out"
    with pytest.raises(ValueError):
        CF.default_release(3, "bram")
    with pytest.raises(ValueError):
        CF.default_release(2, "flash")


def test_release_selects_the_feedback_style():
    a = CF.run(CH2(), I8, F, bram_latency=3, outstanding=2, release="result_out")
    b = CF.run(CH2(), I8, F, bram_latency=3, outstanding=2, feedback=True)
    c = CF.run(CH2(), I8, F, bram_latency=3, outstanding=2, release="delivered")
    d = CF.run(CH2(), I8, F, bram_latency=3, outstanding=2, feedback=False)
    assert (a.rounds, a.per_chain) == (b.rounds, b.per_chain) and (c.rounds, c.per_chain) == (d.rounds, d.per_chain)
    with pytest.raises(ValueError):
        CF.run(CH2(), I8, F, release="both")


def test_a_per_read_latency_sequence_is_absorbed_with_no_loss_and_no_retuning():
    r = CF.run(CH2(), I8, F, bram_latency=LATS, outstanding=2, release="delivered", ports=2)
    assert r.done and r.per_chain == E8 and r.lost_reads == 0
    assert CF.run(CH2(), I8, F, bram_latency=lambda c, q: 1 + (7 * q + 3 * c) % 8, outstanding=2).per_chain == E8


def test_results_do_not_depend_on_any_of_the_latencies():
    outs = {tuple(map(tuple, CF.run(CH2(), I8, F, bram_latency=lats, outstanding=2, max_rounds=800).per_chain))
            for lats in ([1], [3], [8], LATS, [12, 1, 1, 12], [2, 9, 4])}
    assert outs == {tuple(map(tuple, E8))}


def test_the_bram_interface_returns_data_in_order_a_short_read_waits_behind_a_long_one():
    r = CF.run([CF.ChainCfg(window=4, in_depth=4, out_depth=4)], [[1, 2, 3, 4]], F, bram_latency=[8, 1, 1, 1],
               outstanding=4, feedback=False)
    out = [t for t, _, _ in r.deliver_log]
    assert out == sorted(out) and out[1] >= out[0]                        # never reordered
    assert r.per_chain == [[F(x) for x in (1, 2, 3, 4)]]


def test_a_counter_that_assumes_a_latency_loses_reads_when_a_read_takes_longer():
    bad = CF.run(CH2(), I8, F, bram_latency=LATS, advance="fixed", fixed_period=3, outstanding=2, release="delivered",
                 max_rounds=300)
    assert bad.lost_reads > 0 and bad.per_chain != E8


def test_on_either_bus_count_only_result_out_release_isolates_a_stalled_chain():
    """What releasing on feed in GIVES UP: with a chain stalled, 'delivered' lets its item block the delivery path for the
    healthy chain on one bus and on two; 'result_out' does not. (No throughput difference otherwise, in this model.)"""
    for ports in (2, 1):
        d = CF.run(CH2(), I8, F, ports=ports, bram_latency=3, outstanding=2, release="delivered",
                   stall_out={0: (4, 70)}, max_rounds=400)
        o = CF.run(CH2(), I8, F, ports=ports, bram_latency=3, outstanding=2, release="result_out",
                   stall_out={0: (4, 70)}, max_rounds=400)
        assert d.finished_round(1) > 65 and d.tree_blocked_rounds > 30 and d.sentinel_errors
        assert o.finished_round(1) < 40 and o.tree_blocked_rounds == 0 and not o.sentinel_errors
        assert d.per_chain == o.per_chain == E8


def test_without_a_stall_the_two_release_points_cost_the_same_in_this_model():
    for ports in (2, 1):
        a = CF.run(CH2(), I8, F, ports=ports, bram_latency=3, outstanding=2, release="delivered")
        b = CF.run(CH2(), I8, F, ports=ports, bram_latency=3, outstanding=2, release="result_out")
        assert a.rounds == b.rounds and a.per_chain == b.per_chain == E8
