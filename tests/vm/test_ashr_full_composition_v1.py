"""
test_ashr_full_composition_v1.py — points.md #703: the real, full,
end-to-end assembly of Alan's own sign-magnitude `ashr` design,
chaining together `#702`'s two proven building blocks (conditional
negate via branch+reconvergence, lost-bit detection via nibble_mask+
comparator) with `lshr` (already built, `#690`) and a final
subtract-correction + re-negate stage.

Real, deliberate simplification for this first full build: the "no
correction ever needed for non-negative x" property is used directly
-- the positive/zero path takes a genuinely SHORTER route (just
`lshr`, nothing else), padded with plain relay cells to match the
negative path's own real hop count into the shared final merge
(`#544`'s own hard requirement, confirmed still binding).

Real topology:

  NEGATIVE PATH (branch's own LOW route, x<0):
    branch --e--> subtractor_neg(0-x) --e--> lshr_shift --e--> lshr_sink \\
                        |                                                  --> subtract_correction --> re_negate --> MERGE
                        --s--> lost_bit_masker --e--> lost_bit_comparator /

  POSITIVE/ZERO PATH (branch's own EQUAL/HIGH route, x>=0):
    branch --s--> transit --s--> direct_relay --e--> lshr_shift_pos --e--> lshr_sink_pos --e--> [pad] --e--> [pad] --> MERGE
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from llvm_ir_frontend_v1 import _decompose_shift  # noqa: E402


def _ram(cell_id, row, col, downstream, upstream, init=0, load=0, addon=None):
    return v3.IcmV3Record(
        cell_id=cell_id, row=row, col=col, core="ram",
        core_config={"downstream_mask": downstream, "upstream_mask": upstream,
                     "fixed_mode": 0, "load_data_valid": load, "init_data": init},
        addon_config=addon or {},
    )


def _build_grid(shift_amount):
    coarse, fine = _decompose_shift(shift_amount)
    nibbles_to_keep = shift_amount // 4
    nibble_mask = (0xFF << nibbles_to_keep) & 0xFF

    records = [
        v3.IcmV3Record(cell_id="west_feeder", row=1, col=-1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="branch", row=1, col=0, core="branch",
                        core_config={
                            "upstream_dir": 3,
                            "value_source_low": 0, "value_source_equal": 0, "value_source_high": 0,
                            "fixed_value_low": 0, "fixed_value_equal": 0, "fixed_value_high": 0,
                            "emit_low": 1, "emit_equal": 1, "emit_high": 1,
                            "route_low": ["e"], "route_equal": ["s"], "route_high": ["s"],
                            "rolling_mode": 0,
                        }),

        # ── negative path, row 1 spine ── (re_negate BEFORE the
        # correction subtract -- the same real ordering mistake was
        # caught once already in the Python verification script for
        # this algorithm; the correction must apply to the ALREADY
        # re-negated result, not the other way around)
        v3.IcmV3Record(cell_id="subtractor_neg", row=1, col=1, core="adder",
                        core_config={"downstream_mask": ["e", "s"], "upstream_mask": ["n", "w"],
                                     "subtract_mode": 1}),
        _ram("zero_for_negate", 0, 1, ["s"], [], init=0, load=1),
        _ram("lshr_shift_neg", 1, 2, ["e"], ["w"],
             addon={"shift_en": 1, "direction": 1, "shift_amt": coarse, "shift_fine": fine}),
        _ram("lshr_sink_neg", 1, 3, ["e"], ["w"]),
        v3.IcmV3Record(cell_id="re_negate", row=1, col=4, core="adder",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["n", "w"],
                                     "subtract_mode": 1}),
        _ram("zero_for_renegate", 0, 4, ["s"], [], init=0, load=1),
        v3.IcmV3Record(cell_id="subtract_correction", row=1, col=5, core="adder",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w", "s"],
                                     "subtract_mode": 1}),

        # ── lost-bit spine, row 2, cols 1-3 (real, deliberate extra
        # hop on the comparator's own output so it arrives at
        # subtract_correction strictly AFTER the shifted value,
        # guaranteeing correct A/B assignment) ──
        _ram("lost_bit_masker", 2, 1, ["e"], ["n"], addon={"mask_en": 1, "nibble_mask": nibble_mask}),
        v3.IcmV3Record(cell_id="lost_bit_comparator", row=2, col=2, core="comparator",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"], "threshold": 1}),
        _ram("lost_bit_stagger_a", 2, 3, ["e"], ["w"]),
        _ram("lost_bit_stagger_b", 2, 4, ["e"], ["w"]),
        _ram("lost_bit_stagger_c", 2, 5, ["n"], ["w"]),

        # ── positive/zero path: transit down to row 3, then east ──
        _ram("transit", 2, 0, ["s"], ["n"]),
        _ram("direct_relay", 3, 0, ["e"], ["n"]),
        _ram("lshr_shift_pos", 3, 1, ["e"], ["w"],
             addon={"shift_en": 1, "direction": 1, "shift_amt": coarse, "shift_fine": fine}),
        _ram("lshr_sink_pos", 3, 2, ["e"], ["w"]),
        _ram("pos_pad_1", 3, 3, ["e"], ["w"]),
        _ram("pos_pad_2", 3, 4, ["e"], ["w"]),
        _ram("pos_pad_3", 3, 5, ["e"], ["w"]),
        _ram("pos_pad_4", 3, 6, ["n"], ["w"]),
        _ram("pos_pad_5", 2, 6, ["n"], ["s"]),

        # ── final merge ──
        _ram("merge", 1, 6, [], ["w", "s"]),
    ]
    return SuperGrid(records)


def _run_ashr(x, shift_amount, ticks=40):
    grid = _build_grid(shift_amount)
    grid.inject(1, -1, 0)
    for _ in range(3):
        grid.tick()
    grid.inject(1, -1, x & 0xFFFFFFFF)
    for _ in range(ticks):
        grid.tick()
    merge = grid.cells[(1, 6)]
    return merge.ram_data_reg, merge.ram_data_valid


def _real_ashr(x, n, bits=32):
    x &= (1 << bits) - 1
    if x >= (1 << (bits - 1)):
        x -= (1 << bits)
    return (x >> n) & ((1 << bits) - 1)


def test_negative_value_shift_by_4():
    result, valid = _run_ashr(-5, 4)
    assert valid is True
    assert result == _real_ashr(-5, 4)


def test_positive_value_shift_by_4():
    result, valid = _run_ashr(20, 4)
    assert valid is True
    assert result == _real_ashr(20, 4)


def test_zero_shift_by_4():
    result, valid = _run_ashr(0, 4)
    assert valid is True
    assert result == 0


def test_real_sweep_nibble_aligned():
    for x in [-5, -6, -7, -8, -1, -16, -17, -100, 5, 6, 100, 0, -2147483648]:
        for n in (4, 8):
            result, valid = _run_ashr(x, n)
            expected = _real_ashr(x, n)
            assert valid is True, f"x={x} n={n}: not valid"
            assert result == expected, f"x={x} n={n}: got {result:#x}, expected {expected:#x}"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
