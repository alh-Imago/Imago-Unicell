"""tests/vm/test_shared_bus_v1.py — points.md #814: one shared RAM bus, two chain ends (feed-in and return), and Alan's
side thought: a priority cell instead of the RTL arbiter. The round-robin replica is checked against the REAL VM cell."""
import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import icm_vix_v1 as vix  # noqa: E402
import shared_bus_v1 as SB  # noqa: E402
import vix_tile_library_v1 as vtl  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def vm_sequence(rank_n, rank_s, mode, ticks=340, b_gap=0):
    """Two ends ALWAYS ready into the REAL priority cell; who is served, in order. A = north (feed-in), B = south (return)."""
    cells = [vix.HierCell(cell_id="a", rel_row=4, rel_col=5, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["s"]}),
             vix.HierCell(cell_id="b", rel_row=6, rel_col=5, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["n"]}),
             vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                       params={"priority_rank_n": rank_n, "priority_rank_s": rank_s, "priority_rank_e": 0, "priority_rank_w": 0,
                               "scheduling_mode": mode}, cell_id="pri", rel_row=5, rel_col=5),
             vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=5, rel_col=6)]
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                         placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))], name="t")
    g = SuperGrid(icm.flatten()[0])
    seq, ka, kb, tb = [], 0, 0, 0
    for t in range(ticks):
        a, b = g.cells[(4, 5)], g.cells[(6, 5)]
        if not a.ram_data_valid:
            a.ram_data_reg, a.ram_data_valid = 1000 + ka, True
            ka += 1
        if not b.ram_data_valid and t >= tb:
            b.ram_data_reg, b.ram_data_valid = 2000 + kb, True
            kb += 1
        g.tick()
        s = g.cells[(5, 6)]
        if s.ram_data_valid:
            who = "A" if 1000 <= s.ram_data_reg < 2000 else "B"
            seq.append(who)
            s.ram_data_valid = False
            if who == "B":
                tb = t + b_gap
    return "".join(seq)


# ---- the replica IS the real cell ----------------------------------------------------------------------------

@pytest.mark.parametrize("wa,wb", list(itertools.product((1, 2, 3), repeat=2)))
def test_the_weighted_round_robin_replica_reproduces_the_real_cell_exactly(wa, wb):
    vm = vm_sequence(wa, wb, mode=1)
    rep = SB.run_bus("weighted", rounds=len(vm) + 4, weights=(wa, wb)).sequence[: len(vm)]
    assert vm == rep and len(vm) > 100


@pytest.mark.parametrize("ra,rb", [(0, 0), (0, 1), (1, 0), (0, 3), (3, 0), (1, 2), (2, 1)])
def test_the_strict_replica_reproduces_the_real_cell_exactly(ra, rb):
    vm = vm_sequence(ra, rb, mode=0)
    rep = SB.run_bus("strict", rounds=len(vm) + 4, weights=(ra, rb)).sequence[: len(vm)]
    assert vm == rep


def test_a_strict_priority_cell_starves_one_end_completely_under_saturation():
    """Measured on the real cell: 100% to one end, 0% to the other -- at equal ranks (the fixed N>S tie-break) and at unequal ones."""
    assert set(vm_sequence(0, 0, mode=0)) == {"A"} and set(vm_sequence(0, 1, mode=0)) == {"A"}
    assert set(vm_sequence(1, 0, mode=0)) == {"B"}


def test_the_weighted_mode_keeps_both_ends_moving_with_the_share_set_by_the_weights():
    """The side thought holds, provided the cell is in mode 1: 1:1 alternates ABAB..., 3:1 gives exactly 75/25."""
    assert vm_sequence(1, 1, mode=1).startswith("ABABABAB")
    s = vm_sequence(3, 1, mode=1)
    assert abs(s.count("A") / len(s) - 0.75) < 0.02 and s.startswith("AAABAAAB")


def test_the_real_cell_silently_masks_a_weight_to_two_bits_the_trap_the_replica_refuses():
    """Config field is 2 bits: a weight of 5 behaves as 1 and 7 as 3 -- the real cell says nothing. So the largest share is 3:1."""
    assert vm_sequence(5, 2, mode=1) == vm_sequence(1, 2, mode=1)
    assert vm_sequence(1, 7, mode=1) == vm_sequence(1, 3, mode=1)
    with pytest.raises(ValueError, match="2-bit"):
        SB.SurplusRoundRobin({"A": 5, "B": 1})
    with pytest.raises(ValueError, match="2-bit"):
        SB.run_bus("weighted", 10, weights=(1, 7))


# ---- the single bus: what each policy does to the two chain ends --------------------------------------------------

def test_the_rtl_arbiters_write_priority_starves_the_feed_in_end_when_returns_saturate():
    r = SB.run_bus("write_priority", 200)
    assert r.served == {"A": 0, "B": 200} and r.starved == ["A"]


def test_strict_read_priority_starves_the_return_end():
    r = SB.run_bus("read_priority", 200)
    assert r.served == {"A": 200, "B": 0} and r.starved == ["B"]


def test_a_priority_cell_in_weighted_mode_serves_both_ends_at_the_rate_of_the_ram():
    r = SB.run_bus("weighted", 300, weights=(1, 1))
    assert r.served == {"A": 150, "B": 150} and r.starved == [] and max(r.max_wait.values()) <= 1
    assert sum(r.served.values()) == 300                                     # the RAM is never idle: its rate is the total


def test_weights_set_the_share_and_the_wait_of_the_weaker_end():
    r = SB.run_bus("weighted", 400, weights=(3, 1))
    assert r.served == {"A": 300, "B": 100} and r.max_wait["B"] == 3


def test_an_end_that_offers_only_occasionally_is_served_every_time_under_weighted_mode():
    weighted = SB.run_bus("weighted", 300, weights=(1, 1), gap_b=6)
    strict = SB.run_bus("strict", 300, weights=(0, 1), gap_b=6)              # feed-in higher rank
    assert weighted.served["B"] >= weighted.offers["B"] - 1
    assert strict.served["B"] == 0 and strict.starved == ["B"]


def test_a_slower_ram_lowers_the_total_rate_but_not_the_share():
    fast = SB.run_bus("weighted", 300, weights=(1, 1), service=1)
    slow = SB.run_bus("weighted", 300, weights=(1, 1), service=3)
    assert sum(slow.served.values()) * 3 <= sum(fast.served.values()) + 3
    assert abs(slow.share("A") - 0.5) < 0.02


def test_bus_arguments_are_validated():
    with pytest.raises(ValueError):
        SB.run_bus("lottery")
    with pytest.raises(ValueError):
        SB.run_bus("weighted", 10, service=0)
    with pytest.raises(ValueError):
        SB.SurplusRoundRobin({"A": 1, "B": 1}, mode=2)


def test_the_credit_arithmetic_matches_the_cells_source_on_a_hand_worked_sequence():
    """Pins what saturation cannot show -- an ABSENT side and a lone candidate -- with values worked out by hand from
    `unicell_super_automaton_v1.py` (every side's credit gains its weight; the winner pays the total weight of the CANDIDATES,
    floored at 0). Derived from the source, not measured on the VM."""
    srr = SB.SurplusRoundRobin({"A": 3, "B": 1})
    assert srr.pick(["B"]) == "B" and srr.credit == {"A": 3, "B": 0}      # A absent still gains 3; B pays only its own 1
    assert srr.pick(["A", "B"]) == "A" and srr.credit == {"A": 2, "B": 1}  # inc A=6, B=1; total 4; A pays 4
    assert srr.pick(["A"]) == "A" and srr.credit == {"A": 2, "B": 2}      # a LONE candidate pays only its own weight (5 - 3)
    assert srr.pick([]) is None and srr.credit == {"A": 2, "B": 2}


def test_an_absent_end_banks_credit_and_is_owed_a_burst_when_it_returns():
    """The replicated (not separately VM-measured) consequence: an end that was absent gains credit at every arbitration."""
    srr = SB.SurplusRoundRobin({"A": 1, "B": 1})
    for _ in range(6):
        srr.pick(["A"])
    assert srr.credit["B"] == 6
    wins = "".join(srr.pick(["A", "B"]) for _ in range(6))
    assert wins.count("B") > wins.count("A")
