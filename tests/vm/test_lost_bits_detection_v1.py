"""
test_lost_bits_detection_v1.py — points.md #702: the real, isolated
proof of the second building block Alan's own `ashr` design needs --
detecting whether any of the bits about to be shifted out were `1`,
using `nibble_mask` (already-proven extraction, `#690`/`#697`) feeding
`comparator(threshold=1)` (real, existing tile) to produce the exact
0/1 correction amount directly, with no extra logic cell needed.

    source(0,0) --e--> masker(0,1) --e--> comparator(0,2)
    [preloaded magnitude]  [nibble_mask: keep only
                             the low N bits about
                             to be shifted out]
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _build_grid(magnitude, nibble_mask):
    records = [
        v3.IcmV3Record(cell_id="source", row=0, col=0, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": magnitude}),
        v3.IcmV3Record(cell_id="masker", row=0, col=1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0},
                        addon_config={"mask_en": 1, "nibble_mask": nibble_mask}),
        v3.IcmV3Record(cell_id="comparator", row=0, col=2, core="comparator",
                        core_config={"downstream_mask": [], "upstream_mask": ["w"], "threshold": 1}),
    ]
    return SuperGrid(records)


def _run(magnitude, shift_amount, ticks=15):
    # real, nibble-aligned case: keep only the low `shift_amount`
    # bits by discarding whole nibbles above that point -- matches
    # the real per-nibble granularity nibble_mask actually has.
    nibbles_to_keep = shift_amount // 4
    nibble_mask = (0xFF << nibbles_to_keep) & 0xFF
    grid = _build_grid(magnitude, nibble_mask)
    for _ in range(ticks):
        grid.tick()
    cmp = grid.cells[(0, 2)]
    return cmp.cmp_out_buffer, cmp.cmp_data_valid


def test_no_lost_bits_when_low_bits_are_all_zero():
    # magnitude with a clean low nibble (0x30 -- low 4 bits are 0)
    result, valid = _run(0x30, 4)
    assert valid is True
    assert result == 0


def test_lost_bit_detected_when_a_low_bit_is_set():
    # 0x31 -- low nibble is 0x1, a real bit would be lost on a shift by 4
    result, valid = _run(0x31, 4)
    assert valid is True
    assert result == 1


def test_real_sweep_of_nibble_aligned_shift_amounts():
    for shift_amount in (4, 8, 12, 16, 20):
        for magnitude, expect_lost in [(0x1230, 0), (0x1231, 1), (0xFFFF, 1), (0x0000, 0)]:
            result, valid = _run(magnitude, shift_amount)
            assert valid is True
            low_bits = magnitude & ((1 << shift_amount) - 1)
            expected = 1 if low_bits != 0 else 0
            assert result == expected, (
                f"magnitude={magnitude:#x} shift={shift_amount}: got {result}, expected {expected}"
            )


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
