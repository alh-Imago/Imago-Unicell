"""tests/vm/test_host_lifecycle_v1.py — points.md #821: the HOST-DRIVEN STALL/REFILL LIFECYCLE (`#257`, resolved by
`#279`): run to `safe_to_intervene`, read results out, reload fresh input at the SAME addresses (the counter's own
wrap-to-0 point -- `#279`'s resolved "farthest point"), unfreeze both ends, resume. Multiple laps, proven clean:
no stale data from a previous lap survives a reload.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import sentinel_bram_automaton_v1 as S  # noqa: E402

WRAP_AT = 3   # 4 values per chain per lap, matching #415's own original self-test sizing


def three_chains(bram):
    return [S.SentinelChain("H1", base_addr=0, wrap_at=WRAP_AT, bram=bram),
            S.SentinelChain("H2", base_addr=4, wrap_at=WRAP_AT, bram=bram),
            S.SentinelChain("H3", base_addr=8, wrap_at=WRAP_AT, bram=bram)]


def preload(bram):
    for i in range(12):
        bram.write(i, 100 + i)


def lap_block(offset):
    return [{j: offset + 10 * i + j for j in range(4)} for i in range(3)]


def expect_block(offset):
    return [[offset + 10 * i + j for j in range(4)] for i in range(3)]


# ---- the core lifecycle: multiple laps, each seeing genuinely fresh data --------------------------------------

def test_three_laps_each_see_their_own_fresh_data_not_a_stale_previous_lap():
    bram = S.SharedBram()
    preload(bram)
    chains = three_chains(bram)
    lap_data = [[{}, {}, {}], lap_block(1000), lap_block(9000)]
    per_lap = S.run_host_lifecycle(chains, lap_data)
    assert per_lap == [expect_block(100).__class__([[100, 101, 102, 103], [104, 105, 106, 107], [108, 109, 110, 111]]),
                       expect_block(1000), expect_block(9000)]


def test_a_single_lap_with_no_reload_matches_the_original_self_test_exactly():
    """The original #415 self-test, run through the new lifecycle driver with only one lap -- must reproduce it."""
    bram = S.SharedBram()
    preload(bram)
    chains = three_chains(bram)
    per_lap = S.run_host_lifecycle(chains, [[{}, {}, {}]])
    assert per_lap == [[[100, 101, 102, 103], [104, 105, 106, 107], [108, 109, 110, 111]]]
    for c in chains:
        assert c.accumulator == 4 and c.sentinel.safe_to_intervene and not c.sentinel.err_flag


def test_local_addr_returns_to_zero_every_lap_with_no_reset_input_ever_called():
    """#279 Part 1: the counter already wraps to 0 with no reset input on the module at all -- confirmed here across
    repeated laps, not just once."""
    bram = S.SharedBram()
    preload(bram)
    chains = three_chains(bram)
    S.run_host_lifecycle(chains, [[{}, {}, {}], lap_block(1), lap_block(2), lap_block(3)])
    assert [c.local_addr for c in chains] == [0, 0, 0]


def test_ten_laps_stay_clean_no_staleness_creeps_in_over_many_cycles():
    bram = S.SharedBram()
    preload(bram)
    chains = three_chains(bram)
    lap_data = [[{}, {}, {}]] + [lap_block(1000 * k) for k in range(1, 10)]
    per_lap = S.run_host_lifecycle(chains, lap_data)
    assert len(per_lap) == 10
    for k in range(1, 10):
        assert per_lap[k] == expect_block(1000 * k)
    for c in chains:
        assert not c.sentinel.err_flag


def test_a_single_chain_lifecycle_works_too():
    bram = S.SharedBram()
    bram.write(0, 5)
    bram.write(1, 6)
    chain = [S.SentinelChain("solo", base_addr=0, wrap_at=1, bram=bram)]
    per_lap = S.run_host_lifecycle(chain, [[{}], [{0: 50, 1: 60}]])
    assert per_lap == [[[5, 6]], [[50, 60]]]


# ---- the host's own AND-of-both-flags safety condition (#279 Part 2) -----------------------------------------

def test_safe_to_intervene_is_both_flags_anded_not_out_freeze_alone():
    bram = S.SharedBram()
    preload(bram)
    chains = three_chains(bram)
    S.run_host_lifecycle(chains, [[{}, {}, {}]])
    for c in chains:
        assert c.sentinel.need_data_flag and c.sentinel.results_ready_flag
        assert c.sentinel.safe_to_intervene == (c.sentinel.need_data_flag and c.sentinel.results_ready_flag)


# ---- error paths: a genuine fault must not be papered over ------------------------------------------------------

def test_a_chain_that_never_reaches_safe_to_intervene_raises_naming_which_chain():
    bram = S.SharedBram()
    chains = [S.SentinelChain("stuck", base_addr=0, wrap_at=1000, bram=bram)]
    with pytest.raises(S.HostLifecycleError, match="stuck"):
        S.run_host_lifecycle(chains, [[{}]], max_rounds_per_lap=3)


def test_a_pre_existing_error_is_cleared_by_the_hosts_own_unfreeze_at_lifecycle_start():
    """`run_host_lifecycle` unfreezes every chain before running lap 0 -- exactly the host's 'clear the fault and try
    again' action (#279: host_unfreeze takes PRIORITY over the ongoing condition check). So a fault latched BEFORE
    the lifecycle starts, on its own, does not stop it: this is by design, not a gap."""
    bram = S.SharedBram()
    preload(bram)
    chains = three_chains(bram)
    chains[0].sentinel.err_negative = True                    # a fault from something else, before the host acts
    chains[0].sentinel.out_frozen = True
    per_lap = S.run_host_lifecycle(chains, [[{}, {}, {}]])     # runs clean: the initial unfreeze already cleared it
    assert per_lap == [[[100, 101, 102, 103], [104, 105, 106, 107], [108, 109, 110, 111]]]
    assert not chains[0].sentinel.err_flag


def test_a_genuine_fault_during_a_lap_is_not_papered_over():
    """A persistent diff mismatch (something this simplified same-round harness cannot itself produce through normal
    `take_turn()` calls, since feed and collect always pair up -- but a real, latency-bearing pipeline genuinely
    could) makes `err_negative` re-latch on the very next step and, because that also sets `freeze_out`, the chain
    can never complete a lap again: `run_host_lifecycle` reports it as never reaching `safe_to_intervene`, not as a
    silently-ignored fault."""
    bram = S.SharedBram()
    bram.write(0, 5)
    bram.write(1, 6)
    bram.write(2, 7)
    bram.write(3, 8)
    chain = S.SentinelChain("faulty", base_addr=0, wrap_at=3, bram=bram)
    chain.sentinel.diff = -1
    with pytest.raises(S.HostLifecycleError, match="faulty"):
        S.run_host_lifecycle([chain], [[{}]], max_rounds_per_lap=10)
    assert chain.sentinel.err_negative and chain.sentinel.diff == -1     # the fault is still visible, not hidden


# ---- validation --------------------------------------------------------------------------------------------------

def test_zero_chains_is_refused():
    with pytest.raises(ValueError, match="zero chains"):
        S.run_host_lifecycle([], [])


def test_a_mismatched_reload_block_count_is_caught_before_any_lap_runs():
    bram = S.SharedBram()
    preload(bram)
    chains = three_chains(bram)
    with pytest.raises(ValueError, match="lap 1"):
        S.run_host_lifecycle(chains, [[{}, {}, {}], [{}, {}]])           # lap 1 has only 2 blocks for 3 chains
    # nothing should have run: still frozen at power-on defaults, no turns taken
    assert all(c.local_addr == 0 and c.accumulator == 0 for c in chains)


def test_validation_catches_a_bad_lap_that_is_not_the_first_one_before_any_lap_runs():
    """The upfront-validation fix (points.md #821): a bad block several laps in must be caught before lap 0 even
    starts, not discovered only once the lifecycle is already mid-way through."""
    bram = S.SharedBram()
    preload(bram)
    chains = three_chains(bram)
    with pytest.raises(ValueError, match="lap 2"):
        S.run_host_lifecycle(chains, [[{}, {}, {}], lap_block(1), [{}, {}]])
    assert all(c.accumulator == 0 for c in chains)                        # caught before lap 0 ran at all
