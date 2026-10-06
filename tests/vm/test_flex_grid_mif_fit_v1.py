"""tests/vm/test_flex_grid_mif_fit_v1.py -- ledger #978: do the new second ports (adder carry, mul high word) fit the MIF / fp32 split-float design?

A FlexGrid at WIDTH 24 (the significand width) runs the REAL mantissa arithmetic of nano/fp32_mul_v1.py and nano/fp32_add_v1.py:
  * a 24x24 significand multiply with the mul's `wide_mode` flag: word 1 = product bits 0..23, word 2 = bits 24..47. The product the cell hands out is EXACTLY the integer fp32_mul computes, so its
    normalise test (`product & (1 << 47)` = the top bit of the HIGH word) and its rounding bits can be read off the two words; the whole fp32 multiply rebuilt on top of the cell equals fp32_mul.
  * a 24+24 significand add with the adder's `carry_mode` flag: the carry word is EXACTLY fp32_add's mantissa-overflow normalise trigger (`(sum >> 24) & 1` at the aligned integer position).
Cell-level only (VM); the generated RTL is a 32-bit build, and the cell RTL at WIDTH 24 is covered by the sweep builds, not by this test.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "nano"))
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402
from fp32_boundary_v1 import unpack, pack, restore_implicit_one, strip_implicit_one, round_to_nearest_even  # noqa: E402
from fp32_mul_v1 import fp32_mul  # noqa: E402

ram = h.ram
W = 24


def two_word_cell(core, **cfg):
    mid = IcmV3Record(cell_id="M", row=1, col=1, core=core, core_config=dict({"upstream_mask": ["n", "w"], "downstream_mask": ["e"]}, **cfg))
    recs = [ram("X", 0, 0, [], ["e"]), ram("P", 0, 1, ["w"], ["s"]), ram("Y", 1, 0, [], ["e"]), mid, ram("E", 1, 2, ["w"], [])]
    return recs


def run_pair(recs, a, b):
    g = fg.FlexGrid(recs, width=W)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    e, seen = g.cells[pos["E"]], []
    g.inject(*pos["Y"], a)
    g.inject(*pos["X"], b)
    for _ in range(80):
        g.tick()
        if e.ram_data_valid:
            seen.append(e.ram_data_reg)
            e.ram_data_valid = False
        if len(seen) >= 2:
            break
    return seen


def sigs(rng):
    return (1 << 23) | rng.getrandbits(23), (1 << 23) | rng.getrandbits(23)


def test_mul_two_words_are_the_48_bit_significand_product():
    rng, recs = random.Random(978), two_word_cell("mul", wide_mode=1)
    cases = [((1 << 24) - 1, (1 << 24) - 1), (1 << 23, 1 << 23), (1 << 23, (1 << 24) - 1)] + [sigs(rng) for _ in range(60)]
    for a, b in cases:
        lo, hi = run_pair(recs, a, b)
        assert (hi << W) | lo == a * b
        assert (hi >> 23) & 1 == (1 if a * b & (1 << 47) else 0)     # fp32_mul's normalise test is the top bit of the HIGH word


def test_fp32_multiply_rebuilt_on_the_cell_equals_fp32_mul():
    rng, recs = random.Random(979), two_word_cell("mul", wide_mode=1)
    n = 0
    for _ in range(150):
        a_bits, b_bits = rng.getrandbits(32), rng.getrandbits(32)
        a_se, a_m = unpack(a_bits)
        b_se, b_m = unpack(b_bits)
        a_exp, b_exp = a_se & 0xFF, b_se & 0xFF
        if not (1 <= a_exp <= 254 and 1 <= b_exp <= 254):
            continue
        lo, hi = run_pair(recs, restore_implicit_one(a_exp, a_m), restore_implicit_one(b_exp, b_m))
        product = (hi << W) | lo
        exp_sum = a_exp + b_exp - 127
        shift = 24 if (hi >> 23) & 1 else 23
        exp_sum += 1 if shift == 24 else 0
        out_sig = product >> shift
        guard = (product >> (shift - 1)) & 1
        sticky = 1 if product & ((1 << (shift - 1)) - 1) else 0
        out_sig = round_to_nearest_even(out_sig, guard, sticky)
        if out_sig & (1 << 24):
            out_sig >>= 1
            exp_sum += 1
        sign = ((a_se >> 8) ^ (b_se >> 8)) & 1
        got = pack((sign << 8) | (exp_sum & 0xFF), strip_implicit_one(out_sig & 0xFFFFFF))
        assert got == fp32_mul(a_bits, b_bits)
        n += 1
    assert n > 100


def test_adder_carry_is_the_mantissa_overflow_normalise_trigger():
    rng, recs = random.Random(980), two_word_cell("adder", carry_mode=1)
    seen_carry = seen_clear = 0
    for _ in range(80):
        big, small = sigs(rng)
        small >>= rng.randrange(0, 4)           # the aligned integer part of the smaller significand
        s, c = run_pair(recs, big, small)
        assert s == (big + small) & ((1 << W) - 1)
        assert c == ((big + small) >> W) & 1     # fp32_add's `(raw_sum >> EXTRA) & (1 << 24)` test
        seen_carry += c
        seen_clear += 1 - c
    assert seen_carry and seen_clear
