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
