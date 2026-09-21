"""tests/vm/test_ack_pipeline_v1.py — points.md #813: the ack-driven release applied to a CHAIN OF LINKS, each with its
own latency (a DSP chain, or a BRAM read stage in front of one). No fixed latency anywhere."""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import ack_pipeline_v1 as AP  # noqa: E402

N = 12


def test_a_pipelined_release_runs_at_the_rate_of_the_slowest_link():
    r = AP.run_pipeline([3, 3, 5, 2], N, release="stage_out")
    assert r.done and r.in_order and r.lost == 0
    assert r.interval == 5 and r.max_in_flight == 4                       # the slowest link, with every link busy


def test_releasing_only_on_the_final_result_leaves_one_item_in_flight_at_the_sum_of_the_latencies():
    r = AP.run_pipeline([3, 3, 5, 2], N, release="tail_out")
    assert r.done and r.in_order and r.lost == 0
    assert r.interval == 13 and r.max_in_flight == 1


def test_the_same_mechanism_needs_no_retuning_when_any_links_latency_changes():
    for lat in ([3, 3, 5, 2], [3, 3, 9, 2], [1, 1, 1, 1], [7, 2, 2, 12], [3], [30, 3]):
        r = AP.run_pipeline(lat, N)
        assert r.done and r.in_order and r.lost == 0 and r.interval == max(lat), lat


def test_correctness_never_depends_on_the_latencies():
    rng = random.Random(813)
    for _ in range(40):
        lat = [rng.randint(1, 9) for _ in range(rng.randint(1, 6))]
        for rel in ("stage_out", "tail_out"):
            r = AP.run_pipeline(lat, 9, release=rel)
            assert r.done and r.in_order and r.lost == 0 and len(r.outputs) == 9, (lat, rel)


def test_a_feeder_that_assumes_a_rate_works_until_a_link_gets_slower():
    tuned = AP.run_pipeline([3, 3, 5, 2], N, feeder="fixed", fixed_period=5)
    assert tuned.done and tuned.lost == 0
    slower = AP.run_pipeline([3, 3, 9, 2], N, feeder="fixed", fixed_period=5)
    assert slower.lost == 4 and len(slower.outputs) == 8 and not slower.done


def test_a_feeder_tuned_for_the_worst_case_wastes_throughput_the_ack_does_not():
    slow_tuned = AP.run_pipeline([3, 3, 5, 2], N, feeder="fixed", fixed_period=13)
    ack = AP.run_pipeline([3, 3, 5, 2], N)
    assert slow_tuned.done and slow_tuned.lost == 0 and ack.rounds < slow_tuned.rounds / 2


def test_a_stalled_sink_backs_up_through_the_ack_with_no_loss_while_a_fixed_feeder_drops_targets():
    a = AP.run_pipeline([3, 3, 5, 2], N, sink_stall=(20, 60))
    x = AP.run_pipeline([3, 3, 5, 2], N, feeder="fixed", fixed_period=5, sink_stall=(20, 60))
    assert a.done and a.lost == 0 and a.in_order
    assert x.lost > 0 and len(x.outputs) < N


def test_a_bram_read_stage_in_front_of_dsp_links_is_just_another_link():
    """The BRAM read is stage 0 with its own latency; the same handshake drives the whole thing."""
    for bram in (1, 3, 8):
        r = AP.run_pipeline([bram, 3, 5], N)
        assert r.done and r.lost == 0 and r.interval == max(bram, 3, 5)


def test_zero_items_and_bad_arguments():
    assert AP.run_pipeline([3], 0).done
    with pytest.raises(ValueError):
        AP.run_pipeline([], 3)
    with pytest.raises(ValueError):
        AP.run_pipeline([3, 0], 3)
    with pytest.raises(ValueError):
        AP.run_pipeline([3], 3, feeder="whenever")
    with pytest.raises(ValueError):
        AP.run_pipeline([3], 3, release="sometime")
