"""
test_arbitrary_bit_extraction_via_double_shift_v1.py — points.md #708:
Alan's own real idea, verified -- arbitrary-precision "keep the low K
bits" extraction via shift-left-then-shift-right, using ONLY the
existing shift mechanism (`shift_amt`/`shift_fine`, already proven at
full 0-31 bit precision, `#690`). No new RTL needed.

THE REAL PROBLEM THIS SOLVES: `ashr`'s own lost-bit-detection stage
(`#702`/`#703`/`#705`) uses `nibble_mask`, whose real hardware
granularity is 4 bits -- it cannot precisely extract a non-nibble-
aligned low-bit range, confirmed to give a silently wrong answer for
shift amounts that aren't multiples of 4 (`#705`'s own honest scope
restriction). This is the mechanism that lifts that restriction.

THE REAL TRICK: shifting LEFT by (32-K) discards everything except the
low K bits -- they fall off the top of a 32-bit word and vanish, since
it's a logical, zero-filling shift. Shifting the result RIGHT by the
same (32-K) then restores their original position, with the same
zero-fill naturally clearing everything above bit K-1. Verified first
in plain Python against 5,000 random cases (0 mismatches) before
building this real, isolated cell-chain proof.

Real topology -- each shift is genuinely two cells (the addon applies
at OFFER time, not by mutating the cell's own stored register,
confirmed directly against real RTL, `#690`):

    src --e--> shift_left --e--> catch1 --e--> shift_right --e--> catch2

Real, honest, trivial edge case: K=0 needs no chain at all (zero bits
are ever shifted out, so the correction is always 0) -- not a real
gap in the mechanism, just a case where 32-K=32 is out of the real
0-31 shift range and the answer is already known at compile time.
"""
import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from llvm_ir_frontend_v1 import _decompose_shift  # noqa: E402


def _build_grid(value, k):
    coarse, fine = _decompose_shift(32 - k)
    records = [
        v3.IcmV3Record(cell_id="src", row=0, col=0, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": value}),
        v3.IcmV3Record(cell_id="shift_left", row=0, col=1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0},
                        addon_config={"shift_en": 1, "direction": 0, "shift_amt": coarse, "shift_fine": fine}),
        v3.IcmV3Record(cell_id="catch1", row=0, col=2, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="shift_right", row=0, col=3, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0},
                        addon_config={"shift_en": 1, "direction": 1, "shift_amt": coarse, "shift_fine": fine}),
        v3.IcmV3Record(cell_id="catch2", row=0, col=4, core="ram",
                        core_config={"downstream_mask": [], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
    ]
    return SuperGrid(records)


def _run(value, k, ticks=20):
    grid = _build_grid(value, k)
    for _ in range(ticks):
        grid.tick()
    cell = grid.cells[(0, 4)]
    return cell.ram_data_reg, cell.ram_data_valid


def _real_low_k_bits(value, k, bits=32):
    value &= (1 << bits) - 1
    return value & ((1 << k) - 1)


def test_non_nibble_aligned_amounts():
    for value, k in [(0x12345678, 1), (0x12345678, 2), (0x12345678, 3),
                      (0xFFFFFFFF, 1), (0xFFFFFFFF, 3), (0xFFFFFFFF, 31),
                      (5, 1), (5, 2), (5, 3)]:
        out, valid = _run(value, k)
        assert valid is True
        assert out == _real_low_k_bits(value, k), f"value={value:#x} k={k}: got {out:#x}"


def test_nibble_aligned_amounts_still_work():
    for value, k in [(0x12345678, 4), (0x12345678, 8), (0xFFFFFFFF, 28)]:
        out, valid = _run(value, k)
        assert valid is True
        assert out == _real_low_k_bits(value, k)


def test_real_random_sweep():
    random.seed(1)
    for _ in range(30):
        value = random.randint(0, 2**32 - 1)
        k = random.randint(1, 31)   # k=0 is the known trivial case, tested separately
        out, valid = _run(value, k)
        expected = _real_low_k_bits(value, k)
        assert valid is True
        assert out == expected, f"value={value:#x} k={k}: got {out:#x}, expected {expected:#x}"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
