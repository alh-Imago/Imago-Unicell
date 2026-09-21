"""tests/vm/test_dsp_blackbox_v1.py — points.md #814: the DSP chain as a black box with variable per-link latency and NO internal
backpressure; the two monitors (feed-in and return) that stop collisions the substrate cannot otherwise see."""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import dsp_blackbox_v1 as D  # noqa: E402

N = 12


def test_a_chains_total_latency_is_the_sum_of_its_links_and_at_least_one():
    assert D.total_latency([3]) == 3 and D.total_latency([0, 1, 8, 2]) == 11 and D.total_latency([0, 0]) == 1
    with pytest.raises(ValueError):
        D.total_latency([])
    with pytest.raises(ValueError):
        D.total_latency([3, -1])


def test_variable_latency_alone_is_not_the_hazard_a_paced_return_takes_everything():
    """Honest finding: with a return side that keeps pace, even a 27-round chain fed at the RAM's rate collides with nothing."""
    for links in ([3], [5, 3], [0, 1, 8, 2], [9, 9, 9]):
        r = D.run_dsp(links, N, monitored=False, return_slots=1)
        assert r.collisions == 0 and len(r.returned) == N and r.ok, links


def test_an_unmonitored_feeder_collides_when_the_return_side_stalls_and_the_monitor_does_not():
    u = D.run_dsp([5, 3], N, monitored=False, return_stall=(6, 40))
    m = D.run_dsp([5, 3], N, monitored=True, return_stall=(6, 40))
    assert u.lost_return >= 8 and len(u.returned) < N and not u.ok
    assert m.collisions == 0 and m.returned == list(range(N)) and m.ok


def test_an_unmonitored_feeder_collides_when_the_return_side_is_slower_than_the_feed():
    u = D.run_dsp([2], N, monitored=False, return_period=3)
    m = D.run_dsp([2], N, monitored=True, return_period=3)
    assert u.lost_return > 0 and len(u.returned) < N
    assert m.collisions == 0 and len(m.returned) == N


def test_feeding_inside_the_initiation_interval_corrupts_items_the_monitor_respects_it():
    u = D.run_dsp([5, 3], N, monitored=False, ii=4, return_slots=8)
    m = D.run_dsp([5, 3], N, monitored=True, ii=4, return_slots=8)
    assert u.lost_feed >= 8 and len(u.returned) < N
    assert m.collisions == 0 and len(m.returned) == N


def test_the_monitor_is_correct_for_any_latency_profile_including_zero_links_and_over_eight():
    rng = random.Random(814)
    for _ in range(50):
        links = [rng.choice([0, 1, 2, 3, 5, 8, 9, 12]) for _ in range(rng.randint(1, 5))]
        slots = rng.choice([1, 2, 4])
        stall = (rng.randint(3, 20), rng.randint(21, 80)) if rng.random() < 0.5 else None
        r = D.run_dsp(links, 8, monitored=True, return_slots=slots, return_stall=stall, ii=rng.choice([1, 2, 3]),
                      return_period=rng.choice([1, 2]))
        assert r.collisions == 0 and r.returned == list(range(8)), (links, slots, stall)


def test_the_monitor_never_needs_the_latency_its_rate_follows_littles_law():
    """rate ~ return_slots / total latency: the monitor learns nothing about the chain, yet in flight never exceeds the slots."""
    rounds = []
    for slots in (1, 2, 4):
        r = D.run_dsp([0, 1, 8, 2], 40, monitored=True, return_slots=slots)
        assert r.collisions == 0 and r.max_in_flight <= slots
        assert abs(r.rounds - 40 * 11 / slots) / (40 * 11 / slots) < 0.06
        rounds.append(r.rounds)
    assert rounds[0] > rounds[1] > rounds[2]


def test_reprogramming_the_chain_needs_no_retuning_of_the_monitor():
    slow = D.run_dsp([9, 9, 9], 10, monitored=True, return_slots=2)
    fast = D.run_dsp([1], 10, monitored=True, return_slots=2)
    assert slow.collisions == fast.collisions == 0 and fast.rounds < slow.rounds


def test_the_two_monitor_counters_agree_at_the_end():
    r = D.run_dsp([4, 4], N, monitored=True, return_stall=(3, 30))
    assert r.monitor_counts == (N, N)


def test_dsp_arguments_are_validated():
    with pytest.raises(ValueError):
        D.run_dsp([3], 4, ii=0)
    with pytest.raises(ValueError):
        D.run_dsp([3], 4, return_slots=0)


def test_a_feed_hazard_is_physical_it_applies_to_a_monitor_that_ignores_the_initiation_interval_too():
    """The hazard is in the block, not in the feeder: any feed inside `ii` corrupts, so a broken monitor is caught."""
    d = D.run_dsp([5, 3], N, monitored=True, ii=4, return_slots=8)
    assert d.lost_feed == 0 and d.ok
