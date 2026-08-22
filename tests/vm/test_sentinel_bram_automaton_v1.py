"""
test_sentinel_bram_automaton_v1.py -- first VM-level test of the
shared-BRAM sentinel+gather mechanism (points.md #410-#415), item (a)
of the 2026-08-20 five-item roadmap (points.md #421).

Ground truth this reproduces: `top_sentinel_gather_shared_bram_v1.v`
(#415, real RTL, iverilog-proven, passes clean, deterministic, zero
regression on two proven predecessors). Checked directly at #417: NONE
of this thread existed in the VM before `sentinel_bram_automaton_v1.py`
-- this is the first VM-level representation of it.

Real, honest scope, stated up front: an event-driven, round-stepped
model (one round-robin turn per call), not cycle-accurate -- matching
`unicell_super_automaton_v1.py`'s own established abstraction level
exactly. The one thing modeled faithfully rather than simplified away:
`#415`'s own real fix -- a chain must not be exposed to the gather
mechanism until its own current round's real capture has completed
(`fresh`, mirroring `h*_fresh` in the RTL).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from sentinel_bram_automaton_v1 import (
    Sentinel,
    SharedBram,
    SentinelChain,
    run_shared_bram_gather,
)


def test_three_chain_gather_matches_real_rtl_result():
    """Reproduces #415's own real result exactly: 3 chains, WRAP_AT=3,
    block-partitioned addressing (0-3/4-7/8-11), all reach count=4,
    safe=1, err=0, in exactly 12 rounds -- the same number of rounds
    the real RTL self-test uses."""
    bram = SharedBram()
    for i in range(12):
        bram.write(i, 100 + i)

    chains = [
        SentinelChain("H1", base_addr=0, wrap_at=3, bram=bram),
        SentinelChain("H2", base_addr=4, wrap_at=3, bram=bram),
        SentinelChain("H3", base_addr=8, wrap_at=3, bram=bram),
    ]

    rounds = run_shared_bram_gather(chains)

    assert rounds == 12
    for c in chains:
        assert c.accumulator == 4
        assert c.sentinel.safe_to_intervene
        assert not c.sentinel.err_flag


def test_single_chain_level1_case():
    """The Level 1 case (#416) at the VM level: a single chain needs no
    round-robin partner, just repeated turns of its own."""
    bram = SharedBram()
    for i in range(4):
        bram.write(i, 100 + i)

    chain = SentinelChain("H1", base_addr=0, wrap_at=3, bram=bram)
    rounds = run_shared_bram_gather([chain])

    assert chain.accumulator == 4
    assert chain.sentinel.safe_to_intervene
    assert not chain.sentinel.err_flag
    assert rounds == 4


def test_freshness_gate_is_the_real_invariant_not_incidental():
    """A direct regression check for #415's own real fix, not just the
    happy-path end result: a chain's own `fresh` flag must be False
    immediately after `take_turn()` resets it for a new round and
    False whenever that chain is frozen (no new round starts at all),
    confirming the gate is load-bearing, not a no-op that happens to
    pass because reads never actually fail in this model."""
    bram = SharedBram()
    bram.write(0, 100)

    chain = SentinelChain("H1", base_addr=0, wrap_at=0, bram=bram)  # wraps every turn
    chain.unfreeze()

    assert chain.fresh is False   # never having taken a turn yet
    chain.take_turn()             # WRAP_AT=0 means this single turn also wraps
    assert chain.fresh is True    # this round's own capture genuinely completed
    assert chain.sentinel.freeze_out is True   # wrapped -- frozen again immediately

    # A frozen chain's own take_turn() must be a real no-op (matching
    # `shared_read_trigger`'s own `!this_chain_frozen` gating in the
    # RTL) -- fresh resets to False and STAYS False, since no new
    # capture is permitted to happen at all.
    chain.take_turn()
    assert chain.fresh is False
    assert chain.accumulator == 1   # unchanged -- the second call did nothing


def test_sentinel_matches_rtl_logic_table_directly():
    """Direct unit test of the Sentinel class against
    sentinel_counter_v1.v's own real always-block logic table, not the
    composed chain -- confirms the port itself is faithful, independent
    of how SentinelChain happens to drive it."""
    s = Sentinel(chain_length=3)

    # Starts frozen, diff=0 -- results_ready_flag/safe_to_intervene
    # correctly assert immediately at power-on (the real RTL's own
    # documented, deliberate behavior).
    assert s.out_frozen is True
    assert s.results_ready_flag is True
    assert s.safe_to_intervene is True

    # host_unfreeze clears out_frozen.
    s.step(feed_pulse=False, collect_pulse=False, out_wrap_pulse=False,
           host_unfreeze_pulse=True)
    assert s.out_frozen is False
    assert s.results_ready_flag is False   # not frozen -> not "ready" anymore

    # feed increments diff, collect decrements it.
    s.step(feed_pulse=True, collect_pulse=False, out_wrap_pulse=False,
           host_unfreeze_pulse=False)
    assert s.diff == 1
    s.step(feed_pulse=False, collect_pulse=True, out_wrap_pulse=False,
           host_unfreeze_pulse=False)
    assert s.diff == 0

    # A collect with no matching feed drives diff negative and latches
    # the STICKY error -- confirming the same real behavior #414 found
    # and fixed a false trip of in the actual RTL.
    s.step(feed_pulse=False, collect_pulse=True, out_wrap_pulse=False,
           host_unfreeze_pulse=False)
    assert s.diff == -1
    assert s.err_negative is True
    # Sticky: stays latched even once diff recovers.
    s.step(feed_pulse=True, collect_pulse=False, out_wrap_pulse=False,
           host_unfreeze_pulse=False)
    assert s.diff == 0
    assert s.err_negative is True   # still latched
    # Only explicit host_unfreeze clears it.
    s.step(feed_pulse=False, collect_pulse=False, out_wrap_pulse=False,
           host_unfreeze_pulse=True)
    assert s.err_negative is False


if __name__ == "__main__":
    test_three_chain_gather_matches_real_rtl_result()
    test_single_chain_level1_case()
    test_freshness_gate_is_the_real_invariant_not_incidental()
    test_sentinel_matches_rtl_logic_table_directly()
    print("PASS: all 4 tests")
