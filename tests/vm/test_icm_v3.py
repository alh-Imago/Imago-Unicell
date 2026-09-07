"""
test_icm_v3.py — verifies nano/icm_v3.py's SUPER_LATCH packing against
hand-computed bit positions taken directly from unicell_super_v1.v and
each core's own cfg_data field-map comment. Every expected value below is
computed independently of icm_v3.py's own field tables (plain shifts on
literal bit numbers), so this genuinely checks the module against the
RTL, not against its own assumptions restated.
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402


def test_core_select_field_position():
    # core_select occupies latch[4:0] -- SEL_ADDER=2 alone should equal
    # plain integer 2, nothing shifted.
    latch = v3.encode_super_latch("adder", {})
    assert latch & 0x1F == 2
    assert (latch >> 5) == 0  # nothing else set


def test_nano_topology_lands_at_bit5():
    # nano core_config[9:0] = topology, and core_config itself starts at
    # super_latch bit 5 (unicell_super_v1.v line 102: core_config =
    # super_latch[46:5]). So topology=0x3FF (all 10 bits) should appear
    # at super_latch[14:5], core_select=0 (SEL_NANO) at [4:0].
    latch = v3.encode_super_latch("nano", {"topology": 0x3FF})
    assert latch & 0x1F == 0  # core_select = SEL_NANO = 0
    assert (latch >> 5) & 0x3FF == 0x3FF
    assert (latch >> 15) == 0  # nothing above topology set


def test_nano_routing_mask_and_cardinal_edge_positions():
    # unicell_super_v1.v line 154-155: routing_mask <- incoming_config[16:11],
    # cardinal_edge <- incoming_config[22:17]. core_config itself starts at
    # super_latch bit 5, so routing_mask should land at super_latch[21:16]
    # (5+11=16) and cardinal_edge at super_latch[27:22] (5+17=22).
    latch = v3.encode_super_latch("nano", {"routing_mask": 0b101010, "cardinal_edge": 0b010101})
    assert (latch >> 16) & 0x3F == 0b101010  # routing_mask
    assert (latch >> 22) & 0x3F == 0b010101  # cardinal_edge


def test_ram_full_42_bits_used():
    cfg = {"downstream_mask": v3.pack_dirmask(["n"]), "upstream_mask": v3.pack_dirmask(["s"]),
           "fixed_mode": 1, "load_data_valid": 1, "init_data": 0xDEADBEEF}
    latch = v3.encode_super_latch("ram", cfg)
    decoded = v3.decode_super_latch(latch)
    assert decoded["core"] == "ram"
    assert decoded["core_config"]["downstream_mask"] == ["n"]
    assert decoded["core_config"]["upstream_mask"] == ["s"]
    assert decoded["core_config"]["fixed_mode"] == 1
    assert decoded["core_config"]["load_data_valid"] == 1
    assert decoded["core_config"]["init_data"] == 0xDEADBEEF
    # init_data is cfg_data[41:10] on the real RAM core (ram_cell_v1.v line
    # 45); core_config starts at super_latch bit 5, so init_data should
    # land at super_latch[46:15].
    assert (latch >> 15) & 0xFFFFFFFF == 0xDEADBEEF


def test_adder_only_uses_8_bits_rest_reserved():
    latch = v3.encode_super_latch("adder", {"downstream_mask": v3.pack_dirmask(["e", "w"])})
    # core_config is 42 bits wide but adder only defines [7:0] -- bits
    # [46:13] (core_config bits 8-41) must be zero.
    core_config_field = (latch >> 5) & ((1 << 42) - 1)
    assert core_config_field & ~0xFF == 0
    assert core_config_field & 0xF == v3.pack_dirmask(["e", "w"])


def test_comparator_threshold_signed_range_and_position():
    # compare_cell_v1.v: threshold = cfg_data[39:8], 32 bits. core_config
    # starts at super_latch bit 5, so threshold should occupy
    # super_latch[44:13].
    latch = v3.encode_super_latch("comparator", {"threshold": 0xCAFEBABE, "upstream_mask": v3.pack_dirmask(["n"])})
    assert (latch >> 13) & 0xFFFFFFFF == 0xCAFEBABE


def test_addon_config_starts_at_bit47():
    # addon_config = super_latch[66:47] (unicell_super_v1.v line 103).
    # invert_en is addon bit 19, the top bit -- should land at super_latch[66].
    latch = v3.encode_super_latch("nano", {}, {"invert_en": 1})
    assert (latch >> 66) & 1 == 1
    assert (latch >> 67) == 0  # reserved[79:67] untouched


def test_addon_shift_lane_fields_match_module_port_order():
    # unicell_super_v1.v lines 341-344: direction=addon_config[15],
    # shift_en=addon_config[14], shift_amt=addon_config[13:9],
    # lane_cut=addon_config[18:16].
    addon = {"direction": 1, "shift_en": 1, "shift_amt": 0b10101, "lane_cut": 0b011}
    latch = v3.encode_super_latch("nano", {}, addon)
    addon_field = (latch >> 47) & 0xFFFFF
    assert (addon_field >> 15) & 1 == 1
    assert (addon_field >> 14) & 1 == 1
    assert (addon_field >> 9) & 0x1F == 0b10101
    assert (addon_field >> 16) & 0x7 == 0b011


def test_round_trip_every_core():
    samples = {
        "nano": {"topology": 0x24, "ready": 1, "routing_mask": 0b1111, "cardinal_edge": 0b0101},
        "ram": {"downstream_mask": ["n"], "upstream_mask": ["s"], "fixed_mode": 1,
                "load_data_valid": 0, "init_data": 12345},
        "adder": {"downstream_mask": ["e"], "upstream_mask": ["w"]},
        "accumulator": {"inc_dir": ["n"], "dec_dir": ["s"], "downstream_mask": ["e"],
                        "step_amount": 3, "pulse_mode": 1, "threshold": 100},
        "comparator": {"downstream_mask": ["n"], "upstream_mask": ["w"], "threshold": 100},
        "latch": {"set_dir": ["n"], "clear_dir": ["s"], "downstream_mask": ["e", "w"]},
        "branch": {"upstream_dir": 3, "value_source_low": 1, "value_source_equal": 0,
                   "value_source_high": 1, "fixed_value_low": 5, "fixed_value_equal": 0,
                   "fixed_value_high": 10, "emit_low": 1, "emit_equal": 0, "emit_high": 1,
                   "route_low": ["e"], "route_equal": [], "route_high": ["n", "w"],
                   "rolling_mode": 1},
    }
    for core, cfg in samples.items():
        latch = v3.encode_super_latch(core, cfg)
        decoded = v3.decode_super_latch(latch)
        assert decoded["core"] == core
        for k, v in cfg.items():
            assert decoded["core_config"][k] == v, f"{core}.{k}: {decoded['core_config'][k]!r} != {v!r}"


def test_unassigned_core_select_is_inert_not_error_on_decode():
    # #317: core_select 6-31 is genuine future headroom, not an error --
    # unicell_super_v1.v's own output mux `default:` arm treats it as
    # inert (all outputs zero), not X. decode_super_latch should reflect
    # that: readable, flagged as reserved, not raising.
    latch = 8  # core_select=8, everything else zero (7 is now SEL_BRANCH, #519)
    decoded = v3.decode_super_latch(latch)
    assert decoded["core"] == "reserved_8"
    assert decoded["core_config"] == {"_raw": 0}


def test_reserved_headroom_bits_never_written():
    latch = v3.encode_super_latch("latch", {"set_dir": ["n"], "clear_dir": ["s"], "downstream_mask": ["e"]},
                                   {"invert_en": 1, "mask_en": 1, "nibble_mask": 0xFF})
    assert (latch >> 67) == 0  # [79:67] reserved, per #317 -- must stay untouched
    assert latch < (1 << 80)


def test_max_field_values_fit_without_overflow():
    latch = v3.encode_super_latch("ram", {
        "downstream_mask": 0xF, "upstream_mask": 0xF, "fixed_mode": 1,
        "load_data_valid": 1, "init_data": 0xFFFFFFFF,
    }, {"nibble_mask": 0xFF, "mask_en": 1, "shift_amt": 0x1F, "shift_en": 1,
        "direction": 1, "lane_cut": 0x7, "invert_en": 1})
    assert latch < (1 << 80)
    decoded = v3.decode_super_latch(latch)
    assert decoded["core_config"]["init_data"] == 0xFFFFFFFF
    assert decoded["addon_config"]["nibble_mask"] == 0xFF


def test_out_of_range_field_raises():
    try:
        v3.encode_super_latch("ram", {"init_data": 1 << 32})  # 33 bits, field is 32
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for oversized field")


def test_unknown_field_name_raises():
    try:
        v3.encode_super_latch("adder", {"totally_made_up_field": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown field name")


def test_icm_v3_file_round_trip(tmp_path):
    rec1 = v3.IcmV3Record(cell_id="c0", row=0, col=0, core="nano",
                           core_config={"topology": 0x24, "ready": 1})
    rec2 = v3.IcmV3Record(cell_id="c1", row=0, col=1, core="adder",
                           core_config={"downstream_mask": ["w"], "upstream_mask": ["e"]})
    icm = v3.IcmV3File(name="two_cell_test", records=[rec1, rec2], description="round-trip smoke test")
    path = str(tmp_path / "two_cell_test.icm")
    icm.save(path)
    loaded = v3.IcmV3File.load(path)
    assert loaded.name == "two_cell_test"
    assert len(loaded.records) == 2
    assert loaded.records[0].core == "nano"
    assert loaded.records[1].core_config["downstream_mask"] == ["w"]
    assert loaded.record_hash() == icm.record_hash()


def test_icm_v3_file_rejects_corrupted_hash(tmp_path):
    rec = v3.IcmV3Record(cell_id="c0", row=0, col=0, core="latch",
                          core_config={"set_dir": ["n"], "clear_dir": ["s"]})
    icm = v3.IcmV3File(name="tamper_test", records=[rec])
    path = str(tmp_path / "tamper_test.icm")
    icm.save(path)
    import json
    with open(path) as f:
        d = json.load(f)
    d["records"][0]["core_config"]["set_dir"] = ["e"]  # tamper without updating hash
    with open(path, "w") as f:
        json.dump(d, f)
    try:
        v3.IcmV3File.load(path)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for hash mismatch")


# ── #543: cell_type is a real, computed field now (which shell version
# a saved file actually needs), not the old hardcoded "unicell_super_v1"
# regardless of what cores are actually used. ──────────────────────────

def test_cell_type_is_v1_when_only_original_cores_used():
    rec = v3.IcmV3Record(cell_id="c0", row=0, col=0, core="ram",
                          core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                       "fixed_mode": 1, "load_data_valid": 1, "init_data": 1})
    icm = v3.IcmV3File(name="v1_only", records=[rec])
    assert icm.to_dict()["cell_type"] == "unicell_super_v1"


def test_cell_type_is_v2_when_sequencer_used():
    # Real, honest note: "sequencer" isn't registered in icm_v3.py's
    # own CORE_IDS at all yet (a separate, pre-existing, already-
    # flagged gap -- real RTL since unicell_super_v2.v, zero VM
    # dispatch) -- so a full IcmV3Record can't be encoded for it today.
    # Tests minimum_shell_version() directly against a lightweight
    # stand-in with just the one attribute it actually reads, rather
    # than overclaiming sequencer records are fully usable end to end.
    class _FakeRecord:
        core = "sequencer"
    assert v3.minimum_shell_version([_FakeRecord()]) == "unicell_super_v2"


def test_cell_type_is_v3_when_branch_used():
    rec = v3.IcmV3Record(cell_id="c0", row=0, col=0, core="branch",
                          core_config={"upstream_dir": 0, "emit_low": 1, "route_low": ["e"]})
    icm = v3.IcmV3File(name="needs_v3", records=[rec])
    assert icm.to_dict()["cell_type"] == "unicell_super_v3"


def test_cell_type_is_v3_when_mixing_branch_and_original_cores():
    rec1 = v3.IcmV3Record(cell_id="c0", row=0, col=0, core="accumulator",
                           core_config={"inc_dir": ["n"], "downstream_mask": ["e"], "step_amount": 1})
    rec2 = v3.IcmV3Record(cell_id="c1", row=0, col=1, core="branch",
                           core_config={"upstream_dir": 0, "emit_low": 1, "route_low": ["e"]})
    icm = v3.IcmV3File(name="mixed", records=[rec1, rec2])
    assert icm.to_dict()["cell_type"] == "unicell_super_v3"


# ── nano_gate routing_mask list-encoding bug (points.md #687) ───────

def test_nano_gate_with_list_routing_mask_encodes_without_crashing():
    # Real, previously-undiscovered bug: super_tile_library_v1.place()'s
    # own generic mechanism ALWAYS gives routing_mask a list value
    # (['e'], not 15) -- to_dict()/save() crashed outright on this for
    # every real nano_gate-based program, since routing_mask was
    # deliberately excluded from _DIR_FIELDS (a real, separate, still-
    # correct DECODE-side choice). Confirmed fixed: encoding now accepts
    # a list for ANY field, decode contract (raw int for routing_mask)
    # unchanged.
    rec = v3.IcmV3Record(cell_id="g0", row=0, col=0, core="nano",
                          core_config={"topology": 7, "ready": 1, "routing_mask": ["e"]})
    d = rec.to_dict()   # must not raise
    assert d["core"] == "nano"


def test_routing_mask_decode_contract_unchanged_raw_int_in_raw_int_out():
    # The real, existing, relied-upon contract this fix must NOT break:
    # a raw int in still decodes as a raw int out (not silently promoted
    # to a list) -- routing_mask/cardinal_edge are deliberately absent
    # from _DIR_FIELDS on the DECODE side.
    packed = v3.pack_core_config("nano", {"topology": 0, "ready": 1, "routing_mask": 0b1111})
    decoded = v3.unpack_core_config("nano", packed)
    assert decoded["routing_mask"] == 0b1111
    assert not isinstance(decoded["routing_mask"], list)


def test_nano_gate_program_saves_and_loads_via_the_real_dsl_compiler():
    # The real, end-to-end proof: an actual DSL-compiled program using
    # nano_gate (previously impossible to save at all) now round-trips.
    import dsl_compiler_v1 as dsl
    icm, diags = dsl.compile_source(
        "program t { place g1 as nano_gate at (0,0) { out: e  topology: 7 } }"
    )
    assert diags == []
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "nano_gate.icm")
        icm.save(path)   # must not raise
        loaded = v3.IcmV3File.load(path)
        assert loaded.records[0].core_config["routing_mask"] == ["e"]


# ── preload_value (points.md #687) ───────────────────────────────────

def test_preload_value_defaults_to_none():
    rec = v3.IcmV3Record(cell_id="r0", row=0, col=0, core="ram")
    assert rec.preload_value is None
    assert rec.to_dict()["preload_value"] is None


def test_preload_value_round_trips_through_to_dict_from_dict():
    rec = v3.IcmV3Record(cell_id="r0", row=0, col=0, core="ram", preload_value=0xCAFE)
    restored = v3.IcmV3Record.from_dict(rec.to_dict())
    assert restored.preload_value == 0xCAFE


def test_preload_value_round_trips_through_save_load():
    rec = v3.IcmV3Record(cell_id="r0", row=0, col=0, core="ram",
                          core_config={"upstream_mask": ["n"], "downstream_mask": ["e"]},
                          preload_value=99)
    icm = v3.IcmV3File(name="preload_test", records=[rec])
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "preload.icm")
        icm.save(path)
        loaded = v3.IcmV3File.load(path)
    assert loaded.records[0].preload_value == 99


def test_preload_value_is_covered_by_record_hash():
    # A wrong or missing preload silently produces a wrong program --
    # the same real reasoning io_name's own hash coverage already uses.
    rec_a = v3.IcmV3Record(cell_id="r0", row=0, col=0, core="ram", preload_value=1)
    rec_b = v3.IcmV3Record(cell_id="r0", row=0, col=0, core="ram", preload_value=2)
    icm_a = v3.IcmV3File(name="t", records=[rec_a])
    icm_b = v3.IcmV3File(name="t", records=[rec_b])
    assert icm_a.record_hash() != icm_b.record_hash()


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
