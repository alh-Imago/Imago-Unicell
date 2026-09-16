"""
test_priority_core_v1.py — verifies the priority core's real VM model
(points.md #751), built specifically to test Alan's own real insight:
priority's own real "ack the winner, leave the loser genuinely
pending" arbitration can replace relay-path-length engineering for
resolving real DAG convergence points (#750's own hand-solved diamond
example), since it guarantees sequenced, non-simultaneous delivery
regardless of whether the two competing sources are equidistant.

Also verifies the real, backward-compatible extension to `tick()`'s
own shared delivery dispatch this required (a real SET of accepted
directions, not just True/False) introduces zero behavioral change
for every other existing core -- see the broader test suite for that;
this file is scoped to priority's own new, real behavior specifically.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def test_strict_priority_picks_the_higher_ranked_arrival_first():
    """rank 0 = highest priority -- n (rank 0) should win over w (rank 1)."""
    records = [
        v3.IcmV3Record(cell_id="n_src", row=-1, col=0, core="ram",
                        core_config={"downstream_mask": ["s"], "fixed_mode": 0}, preload_value=100),
        v3.IcmV3Record(cell_id="w_src", row=0, col=-1, core="ram",
                        core_config={"downstream_mask": ["e"], "fixed_mode": 0}, preload_value=200),
        v3.IcmV3Record(cell_id="pri", row=0, col=0, core="priority",
                        core_config={"upstream_mask": ["n", "w"], "downstream_mask": [],
                                     "priority_rank_n": 0, "priority_rank_w": 1, "scheduling_mode": 0}),
    ]
    grid = SuperGrid(records)
    pri = grid.cells[(0, 0)]
    for _ in range(3):
        grid.tick()
    assert pri.pri_data_valid
    assert pri.pri_data_reg == 100  # n's own value, the higher-ranked winner
    assert pri.pri_winning_dir == 0  # N


def test_the_loser_is_genuinely_held_and_served_on_its_own_later_turn():
    """The real, central claim this whole design depends on: a losing
    candidate's own offer is NOT dropped -- it stays pending, and gets
    captured once priority drains and re-arms."""
    records = [
        v3.IcmV3Record(cell_id="n_src", row=-1, col=0, core="ram",
                        core_config={"downstream_mask": ["s"], "fixed_mode": 0}, preload_value=100),
        v3.IcmV3Record(cell_id="w_src", row=0, col=-1, core="ram",
                        core_config={"downstream_mask": ["e"], "fixed_mode": 0}, preload_value=200),
        v3.IcmV3Record(cell_id="pri", row=0, col=0, core="priority",
                        core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"],
                                     "priority_rank_n": 0, "priority_rank_w": 1, "scheduling_mode": 0}),
        v3.IcmV3Record(cell_id="sink", row=0, col=1, core="ram",
                        core_config={"upstream_mask": ["w"]}),
    ]
    grid = SuperGrid(records)
    pri = grid.cells[(0, 0)]
    sink = grid.cells[(0, 1)]
    winners = []
    prev_valid = False
    for _ in range(6):
        grid.tick()
        if pri.pri_data_valid and not prev_valid:
            winners.append(pri.pri_data_reg)
        prev_valid = pri.pri_data_valid
    assert winners == [100, 200]  # n first (higher rank), then the held w, on its own later turn
    assert sink.ram_data_reg == 100  # only the first real offer reached sink in this window


def test_weighted_round_robin_produces_the_documented_surplus_pattern():
    """points.md #730's own documented result: a 3:1 weight ratio
    produces N,N,N,W,N,N,N,W... -- re-confirmed here through the real
    VM model, not just the original RTL simulation."""
    records = [
        v3.IcmV3Record(cell_id="n_src", row=-1, col=0, core="ram",
                        core_config={"downstream_mask": ["s"], "fixed_mode": 1, "init_data": 1, "load_data_valid": 1}),
        v3.IcmV3Record(cell_id="w_src", row=0, col=-1, core="ram",
                        core_config={"downstream_mask": ["e"], "fixed_mode": 1, "init_data": 2, "load_data_valid": 1}),
        v3.IcmV3Record(cell_id="pri", row=0, col=0, core="priority",
                        core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"],
                                     "priority_rank_n": 3, "priority_rank_w": 1, "scheduling_mode": 1}),
        v3.IcmV3Record(cell_id="sink", row=0, col=1, core="ram",
                        core_config={"upstream_mask": ["w"]}),
    ]
    grid = SuperGrid(records)
    pri = grid.cells[(0, 0)]
    sink = grid.cells[(0, 1)]
    prev_valid = False
    sequence = []
    for _ in range(40):
        grid.tick()
        if pri.pri_data_valid and not prev_valid:
            sequence.append("N" if pri.pri_winning_dir == 0 else "W")
        prev_valid = pri.pri_data_valid
        if sink.ram_data_valid:  # simulate a real, external consumer periodically draining
            sink.ram_data_valid = False
            sink.pending_ack = 0
    assert "".join(sequence[:8]) == "NNNWNNNW"


# ---- the real payoff: priority as a DAG-convergence primitive, no relay-path engineering needed ----

def test_priority_resolves_a_two_way_convergence_with_no_path_padding():
    """Direct confirmation of Alan's own real insight: two operand
    sources feeding ONE priority cell, which feeds an adder from a
    SINGLE direction, correctly computes the sum -- with zero relay-
    path-length engineering, unlike #750's own hand-padded solution."""
    records = [
        v3.IcmV3Record(cell_id="a_src", row=-1, col=0, core="ram",
                        core_config={"downstream_mask": ["s"], "fixed_mode": 0}, preload_value=3),
        v3.IcmV3Record(cell_id="b_src", row=0, col=-1, core="ram",
                        core_config={"downstream_mask": ["e"], "fixed_mode": 0}, preload_value=5),
        v3.IcmV3Record(cell_id="pri", row=0, col=0, core="priority",
                        core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"],
                                     "priority_rank_n": 0, "priority_rank_w": 1, "scheduling_mode": 0}),
        v3.IcmV3Record(cell_id="t1_adder", row=0, col=1, core="adder",
                        core_config={"upstream_mask": ["w"], "downstream_mask": []}),
    ]
    grid = SuperGrid(records)
    t1 = grid.cells[(0, 1)]
    for _ in range(6):
        grid.tick()
    assert t1.adder_out_buffer == 8  # 3 + 5


def test_priority_resolves_the_full_three_level_diamond_dag():
    """The real, complete rebuild of #750's own hand-padded diamond
    (t3 = (a+b) + (c+d)), using priority cells at every real
    convergence point instead -- direct adjacency throughout, no
    engineered path lengths at all."""
    records = [
        v3.IcmV3Record(cell_id="a_src", row=-1, col=0, core="ram",
                        core_config={"downstream_mask": ["s"], "fixed_mode": 0}, preload_value=3),
        v3.IcmV3Record(cell_id="b_src", row=0, col=-1, core="ram",
                        core_config={"downstream_mask": ["e"], "fixed_mode": 0}, preload_value=5),
        v3.IcmV3Record(cell_id="pri1", row=0, col=0, core="priority",
                        core_config={"upstream_mask": ["n", "w"], "downstream_mask": ["e"],
                                     "priority_rank_n": 0, "priority_rank_w": 1, "scheduling_mode": 0}),
        v3.IcmV3Record(cell_id="t1_adder", row=0, col=1, core="adder",
                        core_config={"upstream_mask": ["w"], "downstream_mask": ["s"]}),

        v3.IcmV3Record(cell_id="c_src", row=1, col=0, core="ram",
                        core_config={"downstream_mask": ["s"], "fixed_mode": 0}, preload_value=10),
        v3.IcmV3Record(cell_id="d_src", row=3, col=0, core="ram",
                        core_config={"downstream_mask": ["n"], "fixed_mode": 0}, preload_value=20),
        v3.IcmV3Record(cell_id="pri2", row=2, col=0, core="priority",
                        core_config={"upstream_mask": ["n", "s"], "downstream_mask": ["e"],
                                     "priority_rank_n": 0, "priority_rank_s": 1, "scheduling_mode": 0}),
        v3.IcmV3Record(cell_id="t2_adder", row=2, col=1, core="adder",
                        core_config={"upstream_mask": ["w"], "downstream_mask": ["n"]}),

        v3.IcmV3Record(cell_id="pri3", row=1, col=1, core="priority",
                        core_config={"upstream_mask": ["n", "s"], "downstream_mask": ["e"],
                                     "priority_rank_n": 0, "priority_rank_s": 1, "scheduling_mode": 0}),
        v3.IcmV3Record(cell_id="t3_adder", row=1, col=2, core="adder",
                        core_config={"upstream_mask": ["w"], "downstream_mask": []}),
    ]
    grid = SuperGrid(records)
    t3 = grid.cells[(1, 2)]
    for _ in range(15):
        grid.tick()
    assert t3.adder_out_buffer == 38  # (3+5) + (10+20)
