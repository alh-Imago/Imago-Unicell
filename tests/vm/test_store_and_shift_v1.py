"""tests/vm/test_store_and_shift_v1.py — points.md #826: the store-and-shift assembler/disassembler `BusPlan`
(`#808`) has flagged as needed and unbuilt whenever a card's bus is narrower than a 32-bit value. Verified against
the exact `#808` worked example, a wide random round-trip sweep, the uneven-split (slack) case, and every error
path.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import fixed_structures_v1 as FS  # noqa: E402
import store_and_shift_v1 as SS  # noqa: E402


def test_the_808_worked_example_26_bit_bus_5_feeds_round_trips_exactly():
    plan = FS.BusSpec(width=26).plan(5)
    assert (plan.data_bits, plan.beats) == (18, 2)
    r = SS.simulate_transfer(0xDEADBEEF, plan)
    assert r.value == 0xDEADBEEF and r.rounds == 2 and len(r.chunks) == 2


def test_one_chain_needs_no_routing_but_still_takes_two_beats_on_a_16_bit_bus():
    plan = FS.BusSpec(width=16).plan(1)
    assert (plan.data_bits, plan.beats) == (16, 2)
    r = SS.simulate_transfer(0x1234, plan)
    assert r.value == 0x1234 and r.rounds == 2


def test_a_40_bit_bus_needs_no_store_and_shift_at_all():
    plan = FS.BusSpec(width=40).plan(5)
    assert plan.beats == 1 and not plan.store_and_shift
    r = SS.simulate_transfer(0xCAFEBEEF, plan)
    assert r.value == 0xCAFEBEEF and r.rounds == 1 and r.chunks == [0xCAFEBEEF]


@pytest.mark.parametrize("width,feeds", [(8, 1), (12, 2), (16, 3), (20, 5), (26, 9), (32, 1), (40, 13)])
def test_random_values_round_trip_exactly_for_every_valid_bus_configuration(width, feeds):
    rng = random.Random(width * 1000 + feeds)
    plan = FS.BusSpec(width=width).plan(feeds)
    for _ in range(30):
        v = rng.randint(0, 0xFFFFFFFF)
        assert SS.simulate_transfer(v, plan).value == v


def test_disassemble_and_assemble_are_exact_inverses_for_every_possible_byte_value_at_a_tight_split():
    """An exhaustive check, not sampled: every value 0-255 through a plan where the split is exact (no slack)."""
    plan = FS.BusPlan(feeds=1, width=8, routing_bits=0, data_bits=8, beats=1, store_and_shift=False, word_bits=8)
    for v in range(256):
        assert SS.simulate_transfer(v, plan).value == v


def test_the_slack_lands_on_the_first_chunk_only_not_reordering_any_bit():
    """26-bit bus, 5 feeds: 18 data bits x 2 beats = 36 bits of capacity for a 32-bit value -- 4 bits of genuine
    slack. It must land as leading zeros on the FIRST chunk; the second chunk must be an untouched, full 18-bit
    low slice."""
    plan = FS.BusSpec(width=26).plan(5)
    value = 0xFFFFFFFF
    chunks = SS.disassemble(value, plan)
    assert chunks[0] == (value >> 18) & ((1 << 18) - 1)          # only 14 real bits fit; masked to 18 shows 4 leading zeros
    assert chunks[0] >> 14 == 0                                   # the slack bits are genuinely zero, not garbage
    assert chunks[1] == value & ((1 << 18) - 1)                   # the low chunk is a full, untouched 18-bit slice


def test_the_first_chunk_received_ends_up_most_significant():
    """The stated convention, checked directly: a shift-in accumulator, first-in becomes most-significant."""
    plan = FS.BusPlan(feeds=1, width=16, routing_bits=0, data_bits=8, beats=2, store_and_shift=True, word_bits=16)
    asm = SS.Assembler(plan)
    asm.feed(0xAB)
    asm.feed(0xCD)
    assert asm.value == 0xABCD


# ---- incremental feed / done / reset --------------------------------------------------------------------------

def test_feed_returns_done_only_on_the_final_chunk():
    plan = FS.BusSpec(width=26).plan(5)
    asm = SS.Assembler(plan)
    chunks = SS.disassemble(0x12345678, plan)
    assert asm.feed(chunks[0]) is False
    assert not asm.done
    assert asm.feed(chunks[1]) is True
    assert asm.done and asm.value == 0x12345678


def test_reading_value_before_done_is_refused():
    plan = FS.BusSpec(width=26).plan(5)
    asm = SS.Assembler(plan)
    with pytest.raises(SS.StoreAndShiftError, match="no value yet"):
        _ = asm.value
    asm.feed(SS.disassemble(1, plan)[0])
    with pytest.raises(SS.StoreAndShiftError, match="no value yet"):
        _ = asm.value


def test_an_extra_chunk_after_done_is_refused():
    plan = FS.BusSpec(width=26).plan(5)
    asm = SS.Assembler(plan)
    for c in SS.disassemble(1, plan):
        asm.feed(c)
    with pytest.raises(SS.StoreAndShiftError, match="extra chunk"):
        asm.feed(0)


def test_reset_lets_the_same_assembler_be_reused_for_the_next_value():
    plan = FS.BusSpec(width=26).plan(5)
    asm = SS.Assembler(plan)
    for c in SS.disassemble(0xAAAA, plan):
        asm.feed(c)
    assert asm.value == 0xAAAA
    asm.reset()
    assert not asm.done
    for c in SS.disassemble(0xBBBB, plan):
        asm.feed(c)
    assert asm.value == 0xBBBB


def test_many_consecutive_values_through_one_reused_assembler():
    plan = FS.BusSpec(width=20).plan(3)
    asm = SS.Assembler(plan)
    rng = random.Random(1)
    for _ in range(50):
        v = rng.randint(0, 0xFFFFFFFF)
        for c in SS.disassemble(v, plan):
            asm.feed(c)
        assert asm.value == v
        asm.reset()


# ---- error paths -----------------------------------------------------------------------------------------------

def test_a_value_too_wide_for_word_bits_is_refused():
    plan = FS.BusSpec(width=26).plan(5)
    with pytest.raises(SS.StoreAndShiftError, match="does not fit in 32 bits"):
        SS.disassemble(1 << 40, plan)
    with pytest.raises(SS.StoreAndShiftError):
        SS.disassemble(-1, plan)


def test_a_chunk_too_wide_for_data_bits_is_refused():
    plan = FS.BusSpec(width=26).plan(5)      # data_bits = 18
    asm = SS.Assembler(plan)
    with pytest.raises(SS.StoreAndShiftError, match="does not fit in 18 bits"):
        asm.feed(1 << 20)
    with pytest.raises(SS.StoreAndShiftError):
        asm.feed(-1)
