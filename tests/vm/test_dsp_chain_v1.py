"""tests/vm/test_dsp_chain_v1.py — points.md #815: the Arria 10 DSP chain's actual topology -- a fixed physical chain
programmed once, tapped in and out anywhere along it, with a single-feed-per-chain exclusivity that no choice of
tap can get around. Per-block latency is a card property and is kept loose unless supplied."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import card_fit_v1 as C  # noqa: E402
import dsp_blackbox_v1 as D  # noqa: E402
import dsp_chain_v1 as DC  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAN = os.path.join(HERE, "..", "..", "docs", "man", "mustang-f100-a10.man.json")


# ---- the MAN file: chain length is a recorded card property, latency stays loose --------------------------------

def test_the_chain_length_is_read_from_the_man_file_as_a_card_property():
    card = C.dsp_chain_from_man(MAN)
    assert card.max_length == 27 and card.total_blocks == 1687
    assert "spine" in card.reason.lower()


def test_per_block_latency_is_left_loose_when_the_man_file_has_no_figure():
    card = C.dsp_chain_from_man(MAN)
    assert card.latency_per_block is None                                  # #815: not assumed for this card


def test_a_man_file_with_no_chain_entry_is_refused_not_treated_as_unbounded():
    import json
    man = json.load(open(MAN))
    del man["device"]["dsp"]["chain"]
    with pytest.raises(ValueError, match="max_length"):
        C.dsp_chain_from_man(man)


def test_chains_available_is_an_upper_bound_from_the_real_card_numbers():
    card = C.dsp_chain_from_man(MAN)
    assert DC.chains_available(card.total_blocks, card.max_length) == 1687 // 27 == 62
    with pytest.raises(ValueError):
        DC.chains_available(-1, 27)
    with pytest.raises(ValueError):
        DC.chains_available(100, 0)


# ---- tapping: programmed once, entered and left anywhere ---------------------------------------------------------

def test_a_chain_is_programmed_once_and_a_tap_reads_a_sub_sequence_without_reprogramming():
    chain = DC.DspChain(27, ops=tuple(f"mac{i}" for i in range(27)))
    seg = chain.tap(5, 12)
    assert seg.ops == tuple(f"mac{i}" for i in range(5, 13)) and seg.span == 8
    assert chain.ops == tuple(f"mac{i}" for i in range(27))                 # the programming is untouched by tapping


def test_you_can_enter_at_any_block_and_leave_at_any_later_block():
    chain = DC.DspChain(27)
    assert chain.tap(0, 26).span == 27                                     # the whole chain
    assert chain.tap(0, 0).span == 1                                       # a single block
    assert chain.tap(26, 26).span == 1                                     # the last block alone
    assert chain.tap(3, 3).ops == chain.ops[3:4]


@pytest.mark.parametrize("entry,exit", [(-1, 5), (5, 3), (0, 27), (27, 27)])
def test_an_out_of_range_or_backwards_tap_is_refused(entry, exit):
    chain = DC.DspChain(27)
    with pytest.raises(ValueError):
        chain.tap(entry, exit)


def test_a_chain_must_have_at_least_one_block_and_ops_must_match_its_length():
    with pytest.raises(ValueError):
        DC.DspChain(0)
    with pytest.raises(ValueError):
        DC.DspChain(5, ops=("a", "b"))


# ---- the exclusivity rule: one feed per chain, whatever tap is used --------------------------------------------

def test_feeding_one_tap_makes_the_whole_chain_busy_for_every_other_tap():
    """The point Alan made: entry/exit choice never changes this -- a DISJOINT tap is refused just as much as an
    overlapping one."""
    chain = DC.DspChain(27)
    chain.feed(0, 5)
    assert chain.busy
    with pytest.raises(DC.ChainBusyError):
        chain.feed(20, 26)                                                 # disjoint from (0, 5) -- still refused
    with pytest.raises(DC.ChainBusyError):
        chain.feed(0, 5)                                                   # even the identical tap again


def test_releasing_frees_the_chain_for_a_new_tap_anywhere():
    chain = DC.DspChain(27)
    chain.feed(0, 8)
    chain.release()
    assert not chain.busy
    seg = chain.feed(20, 26)
    assert (seg.entry, seg.exit) == (20, 26)


def test_feeding_the_whole_chain_or_one_block_costs_the_same_exclusivity():
    """'no matter how much you use' -- span size is irrelevant to the busy state."""
    whole = DC.DspChain(27)
    whole.feed(0, 26)
    with pytest.raises(DC.ChainBusyError):
        whole.feed(13, 13)
    one = DC.DspChain(27)
    one.feed(13, 13)
    with pytest.raises(DC.ChainBusyError):
        one.feed(0, 26)


# ---- a pool of chains: parallelism comes from MORE CHAINS, not more taps -----------------------------------------

def test_a_pool_lets_as_many_concurrent_feeds_as_it_has_chains_and_no_more():
    pool = DC.ChainPool.of_max_length_chains(3, 27)
    for _ in range(3):
        pool.feed_any_free(0, 5)
    assert pool.free_count == 0
    with pytest.raises(DC.ChainBusyError, match="all 3 chains"):
        pool.feed_any_free(0, 5)


def test_releasing_one_chain_in_a_pool_frees_exactly_one_slot():
    pool = DC.ChainPool.of_max_length_chains(2, 27)
    pool.feed_any_free(0, 5)
    _, seg = pool.feed_any_free(0, 5)
    pool.chains[0].release()
    assert pool.free_count == 1
    idx, _ = pool.feed_any_free(10, 15)
    assert idx == 0


# ---- ties into #814's black-box monitor: a segment's latencies ARE its `links` ------------------------------------

def test_a_tapped_segments_latencies_feed_straight_into_the_814_monitor():
    chain = DC.DspChain(27)
    seg = chain.tap(4, 9)                                                   # 6 blocks
    links = seg.links(latency_per_block=3.0)
    assert links == [3.0] * 6
    r = D.run_dsp(links, 8, monitored=True, return_slots=2)
    assert r.ok and len(r.returned) == 8


def test_different_taps_on_the_same_programmed_chain_give_different_link_lists():
    chain = DC.DspChain(27)
    short = chain.tap(0, 2).links(2.0)
    long = chain.tap(0, 20).links(2.0)
    assert len(short) == 3 and len(long) == 21 and D.total_latency(long) > D.total_latency(short)


def test_asking_for_links_with_no_latency_set_refuses_rather_than_guessing():
    seg = DC.DspChain(27).tap(0, 5)
    with pytest.raises(DC.ChainLatencyUnknownError, match="loose"):
        seg.links(None)
    with pytest.raises(DC.ChainLatencyUnknownError):
        seg.links(latency_per_block=None)


def test_a_chain_built_with_a_latency_still_lets_links_be_read_without_repeating_it_per_tap():
    chain = DC.DspChain(27, latency_per_block=4.0)
    assert chain.tap(0, 5).links(chain.latency_per_block) == [4.0] * 6
