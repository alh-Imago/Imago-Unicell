"""tests/vm/test_dsp_chain_placement_v1.py — points.md #816: placing dsp_chain_v1.DspChain objects on a card's real
DSP sites, respecting the spine-region chain-length limit. Site adjacency needs no fabric routing (the cascade is a
dedicated hard-silicon connection, #26) -- this module only answers WHERE each block of a chain physically sits.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import card_fit_v1 as C  # noqa: E402
import dsp_chain_placement_v1 as P  # noqa: E402
import dsp_chain_v1 as DC  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAN = os.path.join(HERE, "..", "..", "docs", "man", "mustang-f100-a10.man.json")


def target():
    return C.target_from_man(MAN, rows=224, cols=150)


def card():
    return C.dsp_chain_from_man(MAN)


# ---- grouping and contiguity ---------------------------------------------------------------------------------

def test_dsp_sites_group_into_eight_columns_matching_the_real_man_file():
    cols = P.group_by_column(target().sites["dsp"])
    assert sorted(cols) == [26, 40, 46, 58, 64, 96, 118, 128]
    assert len(cols[26]) == 223 and len(cols[96]) == 167                    # the truncated column (points.md docs)


def test_a_columns_sites_are_returned_sorted_by_row_the_physical_die_order():
    cols = P.group_by_column(target().sites["dsp"])
    rows = [r for r, _ in cols[26]]
    assert rows == sorted(rows) == list(range(1, 224))


def test_a_non_contiguous_column_is_refused_not_silently_chained_across_a_gap():
    sites = [(1, 5), (2, 5), (5, 5), (6, 5)]                                 # a gap at rows 3-4
    with pytest.raises(ValueError, match="not contiguous"):
        P.group_by_column(sites)


# ---- placement: real chains from real sites ------------------------------------------------------------------

def test_placing_chains_on_the_real_mustang_dsp_sites():
    chains = P.place_chains(target(), card())
    assert len(chains) == P.chain_count(target(), card()) == 70
    assert all(pc.length <= 27 for pc in chains)
    assert sum(pc.length for pc in chains) == len(target().sites["dsp"])    # every site accounted for, none doubled


def test_column_26_splits_into_eight_full_chains_and_one_remainder():
    chains = [pc for pc in P.place_chains(target(), card()) if pc.column == 26]
    assert [pc.length for pc in chains] == [27] * 8 + [7]                   # 223 = 8*27 + 7


def test_the_truncated_column_96_still_chunks_correctly():
    chains = [pc for pc in P.place_chains(target(), card()) if pc.column == 96]
    assert sum(pc.length for pc in chains) == 167 and all(pc.length <= 27 for pc in chains)


def test_a_placed_chains_positions_are_physically_consecutive_in_the_column():
    chains = P.place_chains(target(), card())
    for pc in chains:
        rows = [r for r, _ in pc.positions]
        assert rows == list(range(rows[0], rows[0] + pc.length))
        assert all(c == pc.column for _, c in pc.positions)


def test_the_real_site_derived_count_and_the_block_derived_upper_bound_are_both_approximations_and_differ():
    """Neither is ground truth: chain_count() comes from the SITE list, which card_fit_v1's own provenance already
    flags as an upper bound (1728 sites vs 1687 real DSP blocks, points.md #806); chains_available() comes from the
    block COUNT instead. They need not (and here do not) agree."""
    c = card()
    real = P.chain_count(target(), c)
    optimistic = DC.chains_available(c.total_blocks, c.max_length)
    assert real == 70 and optimistic == 62 and real != optimistic


# ---- a placed chain is exactly a dsp_chain_v1.DspChain, positioned ------------------------------------------

def test_a_placed_chains_dsp_chain_behaves_exactly_like_any_other():
    pc = P.place_chains(target(), card())[0]
    assert pc.chain.max_length == pc.length == 27
    seg = pc.chain.feed(0, 4)
    assert seg.span == 5
    with pytest.raises(DC.ChainBusyError):
        pc.chain.feed(10, 12)                                                # exclusivity, unchanged from #815


def test_tap_positions_returns_the_real_physical_cells_a_tap_occupies():
    pc = P.place_chains(target(), card())[0]
    assert pc.tap_positions(0, 5) == pc.positions[0:6]
    assert pc.tap_positions(21, 26) == pc.positions[21:27]


def test_tap_positions_validates_through_the_same_dsp_chain_bounds_check():
    pc = P.place_chains(target(), card())[0]
    with pytest.raises(ValueError):
        pc.tap_positions(-1, 5)
    with pytest.raises(ValueError):
        pc.tap_positions(0, 27)


def test_position_of_a_single_block():
    pc = P.place_chains(target(), card())[0]
    assert pc.position_of(0) == pc.positions[0] and pc.position_of(26) == pc.positions[26]
    with pytest.raises(ValueError):
        pc.position_of(27)


# ---- validation ------------------------------------------------------------------------------------------------

def test_a_target_with_no_dsp_sites_is_refused():
    t = C.CardTarget("no-dsp", 10, 10, cell_budget=1000, sites={})
    with pytest.raises(ValueError, match="no DSP sites"):
        P.place_chains(t, card())


def test_a_zero_length_chain_card_is_refused():
    with pytest.raises(ValueError, match="max_length"):
        P.place_chains(target(), C.DspChainCard(max_length=0, total_blocks=100))


def test_placing_with_a_looser_or_tighter_max_length_changes_the_chain_count_predictably():
    t, c = target(), card()
    loose = C.DspChainCard(max_length=50, total_blocks=c.total_blocks)
    tight = C.DspChainCard(max_length=10, total_blocks=c.total_blocks)
    assert P.chain_count(t, loose) < P.chain_count(t, c) < P.chain_count(t, tight)
