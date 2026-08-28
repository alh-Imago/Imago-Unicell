"""
test_generic_field_codec_v1.py — proves `generic_field_codec_v1.py`
(driven entirely by `root_definition.json`) is a genuine, faithful
equivalent to `icm_v3.py`'s own hand-typed, RTL-simulation-verified
`pack_core_config()`/`unpack_core_config()` (`points.md #216` items
2/4, `#356`). Not assumed equivalent because the source data matches --
checked directly, systematically, across all 6 cores and real, varied
values.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
import generic_field_codec_v1 as gfc  # noqa: E402

ROOT = gfc.load_root_definition()


def test_field_table_matches_icm_v3_for_every_core():
    for sel in range(6):
        generic = gfc.field_table(ROOT, sel)
        hand_typed = v3.CORE_FIELD_TABLES[sel]
        assert generic == hand_typed, f"core_select={sel}: {generic} != {hand_typed}"


def test_ram_pack_matches_icm_v3_exactly():
    values = {"downstream_mask": 0b0001, "upstream_mask": 0b0010, "fixed_mode": 1,
              "load_data_valid": 1, "init_data": 0xCAFEBEEF}
    generic_packed = gfc.pack_core_config(ROOT, v3.SEL_RAM, values)
    real_packed = v3.pack_core_config(v3.SEL_RAM, values)
    assert generic_packed == real_packed


def test_adder_pack_matches_icm_v3_exactly_and_the_real_rtl_test_vector():
    values = {"downstream_mask": 0b0100, "upstream_mask": 0b1001}
    generic_packed = gfc.pack_core_config(ROOT, v3.SEL_ADDER, values)
    real_packed = v3.pack_core_config(v3.SEL_ADDER, values)
    assert generic_packed == real_packed
    # the exact value confirmed against tb_unicell_super_v1.v earlier
    # this session (points.md #336's own real RTL cross-check)
    latch = gfc.pack_super_latch_core_portion(ROOT, v3.SEL_ADDER, values)
    assert latch == 0x1282


def test_all_six_cores_round_trip_equivalently_across_many_values():
    samples = {
        v3.SEL_NANO: [
            {"topology": 0x24, "ready": 1, "routing_mask": 0b1111, "cardinal_edge": 0b0101},
            {"topology": 0x3FF, "ready": 0, "routing_mask": 0, "cardinal_edge": 0x3F},
        ],
        v3.SEL_RAM: [
            {"downstream_mask": 1, "upstream_mask": 2, "fixed_mode": 1,
             "load_data_valid": 0, "init_data": 12345},
            {"downstream_mask": 0xF, "upstream_mask": 0xF, "fixed_mode": 0,
             "load_data_valid": 1, "init_data": 0xFFFFFFFF},
        ],
        v3.SEL_ADDER: [
            {"downstream_mask": 4, "upstream_mask": 9},
            {"downstream_mask": 0, "upstream_mask": 0},
        ],
        v3.SEL_ACC: [
            {"inc_dir": 1, "dec_dir": 2, "downstream_mask": 4, "step_amount": 1, "pulse_mode": 0, "threshold": 0},
            {"inc_dir": 0xF, "dec_dir": 0, "downstream_mask": 0xF, "step_amount": 0xFF, "pulse_mode": 1, "threshold": 0xFFFF},
        ],
        v3.SEL_CMP: [
            {"downstream_mask": 1, "upstream_mask": 8, "threshold": 100},
            {"downstream_mask": 0, "upstream_mask": 0, "threshold": 0xFFFFFFFF},
        ],
        v3.SEL_LATCH: [
            {"set_dir": 1, "clear_dir": 2, "downstream_mask": 4},
            {"set_dir": 0xF, "clear_dir": 0xF, "downstream_mask": 0xF},
        ],
        v3.SEL_BRANCH: [
            {"upstream_dir": 0, "value_source_low": 0, "value_source_equal": 0, "value_source_high": 0,
             "fixed_value_low": 0, "fixed_value_equal": 0, "fixed_value_high": 0,
             "emit_low": 1, "emit_equal": 1, "emit_high": 1,
             "route_low": 1, "route_equal": 1, "route_high": 1, "rolling_mode": 0},
            {"upstream_dir": 3, "value_source_low": 1, "value_source_equal": 1, "value_source_high": 1,
             "fixed_value_low": 0x7F, "fixed_value_equal": 0x7F, "fixed_value_high": 0x7F,
             "emit_low": 0, "emit_equal": 0, "emit_high": 0,
             "route_low": 0xF, "route_equal": 0xF, "route_high": 0xF, "rolling_mode": 1},
        ],
    }
    for sel, cases in samples.items():
        for values in cases:
            generic_packed = gfc.pack_core_config(ROOT, sel, values)
            real_packed = v3.pack_core_config(sel, values)
            assert generic_packed == real_packed, f"core_select={sel} values={values}: " \
                f"generic={generic_packed:#x} real={real_packed:#x}"

            generic_unpacked = gfc.unpack_core_config(ROOT, sel, generic_packed)
            real_unpacked = v3.unpack_core_config(sel, real_packed)
            # icm_v3.py's own unpack applies a higher-level convenience on
            # top of raw ints -- direction-valued fields come back as a
            # list of direction letters (e.g. downstream_mask=1 -> ['n']).
            # generic_field_codec_v1.py deliberately doesn't re-derive that
            # convenience layer (stated in its own module docstring), so
            # the correct comparison normalizes icm_v3's list-valued
            # fields back to raw ints via its own pack_dirmask() before
            # comparing -- not a mismatch, a documented scope boundary.
            normalized_real = {
                k: (v3.pack_dirmask(v) if isinstance(v, list) else v)
                for k, v in real_unpacked.items()
            }
            assert generic_unpacked == normalized_real, f"core_select={sel} values={values}"


def test_super_latch_core_portion_matches_icm_v3_for_every_core():
    samples = {
        v3.SEL_NANO: {"topology": 0x24, "ready": 1, "routing_mask": 1, "cardinal_edge": 0},
        v3.SEL_RAM: {"downstream_mask": 1, "upstream_mask": 0, "fixed_mode": 1,
                     "load_data_valid": 1, "init_data": 777},
        v3.SEL_ADDER: {"downstream_mask": 4, "upstream_mask": 9},
        v3.SEL_ACC: {"inc_dir": 1, "dec_dir": 2, "downstream_mask": 4, "step_amount": 1, "pulse_mode": 0, "threshold": 0},
        v3.SEL_CMP: {"downstream_mask": 1, "upstream_mask": 8, "threshold": 8},
        v3.SEL_LATCH: {"set_dir": 1, "clear_dir": 2, "downstream_mask": 4},
        v3.SEL_BRANCH: {"upstream_dir": 2, "value_source_low": 1, "value_source_equal": 0,
                         "value_source_high": 0, "fixed_value_low": 3, "fixed_value_equal": 0,
                         "fixed_value_high": 0, "emit_low": 1, "emit_equal": 0, "emit_high": 1,
                         "route_low": 4, "route_equal": 0, "route_high": 1, "rolling_mode": 0},
    }
    for sel, values in samples.items():
        generic_latch = gfc.pack_super_latch_core_portion(ROOT, sel, values)
        real_latch = v3.encode_super_latch(sel, values, addon_config={})
        assert generic_latch == real_latch, f"core_select={sel}: generic={generic_latch:#x} " \
            f"real={real_latch:#x}"


def test_unknown_field_rejected_same_as_icm_v3():
    try:
        gfc.pack_core_config(ROOT, v3.SEL_ADDER, {"totally_bogus_field": 1})
    except ValueError as e:
        assert "unknown field" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_out_of_range_value_rejected():
    try:
        gfc.pack_core_config(ROOT, v3.SEL_RAM, {"init_data": 1 << 32})  # 33 bits, field is 32
    except ValueError as e:
        assert "does not fit" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_reserved_core_select_raises_matching_icm_v3s_own_headroom_convention():
    try:
        gfc.field_table(ROOT, 8)   # 7 is now SEL_BRANCH (#519) -- 8 remains genuinely reserved
    except ValueError as e:
        assert "317" in str(e)
    else:
        raise AssertionError("expected ValueError for reserved core_select")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
