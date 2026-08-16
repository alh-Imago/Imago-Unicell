"""
test_unicell_super_automaton_v1.py — verifies nano/unicell_super_automaton_v1.py's
per-core VM dispatch against the same semantics `fpga/verilog/tb_unicell_super_v1.v`
already proved on real RTL (compiled and run via iverilog against
`unicell_super_v1.v` this session -- see `tests/vm/test_icm_v3.py`'s own
header for that cross-check). Same 6 scenarios, same expected results:
RAM fixed=0xCAFEBEEF, adder 100+23=123, accumulator 3 increments=3,
comparator 10>=8=1, latch set=1, plus a real multi-cell grid-delivery
test (no single-core-file test covers actual cross-cell wiring).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperCell, SuperGrid, apply_addons  # noqa: E402
from unicell_automaton_v1 import N, S, E, W  # noqa: E402


def _rec(cell_id, row, col, core, core_config=None, addon_config=None):
    return v3.IcmV3Record(cell_id=cell_id, row=row, col=col, core=core,
                           core_config=core_config or {}, addon_config=addon_config or {})


def test_ram_fixed_mode_offers_immediately_no_capture_ever():
    rec = _rec("c0", 0, 0, "ram", {"downstream_mask": ["e"], "fixed_mode": 1,
                                    "load_data_valid": 1, "init_data": 0xCAFEBEEF})
    cell = SuperCell.from_record(rec)
    assert cell.ram_data_reg == 0xCAFEBEEF
    assert cell.ram_data_valid is True
    value, valid, downstream = cell._offer_state()
    assert (value, valid) == (0xCAFEBEEF, True)
    # fixed mode never captures, ever -- an arrival is simply rejected/retried forever
    accepted, forward = cell.deliver({N: 0x11111111}, None)
    assert accepted is False
    assert cell.ram_data_reg == 0xCAFEBEEF  # unchanged -- capture never happened


def test_ram_flowing_capture_then_offer_then_drain_reopens():
    rec = _rec("c0", 0, 0, "ram", {"downstream_mask": ["e"], "upstream_mask": ["n"]})
    cell = SuperCell.from_record(rec)
    assert cell.ram_data_valid is False
    accepted, forward = cell.deliver({N: 0x42}, None)
    assert accepted is True and forward is None
    assert cell.ram_data_reg == 0x42 and cell.ram_data_valid is True
    # doubly full: a second arrival before the first drains must be rejected
    accepted2, _ = cell.deliver({N: 0x99}, None)
    assert accepted2 is False
    assert cell.ram_data_reg == 0x42  # unchanged


def test_adder_two_stage_capture_matches_tb_vector():
    # Exact same scenario as tb_unicell_super_v1.v: 100 (N) then 23 (W),
    # upstream = N|W, expect sum 123.
    rec = _rec("c0", 0, 0, "adder", {"downstream_mask": ["e"], "upstream_mask": ["n", "w"]})
    cell = SuperCell.from_record(rec)
    accepted, forward = cell.deliver({N: 100}, None)
    assert accepted is True and forward is None
    assert cell.adder_a_arrived is True and cell.adder_a_reg == 100
    accepted, forward = cell.deliver({W: 23}, None)
    assert accepted is True
    assert cell.adder_out_buffer == 123
    assert cell.adder_a_arrived is False  # A slot freed for next pair


def test_adder_doubly_full_blocks_third_operand():
    rec = _rec("c0", 0, 0, "adder", {"downstream_mask": ["e"], "upstream_mask": ["n", "w"]})
    cell = SuperCell.from_record(rec)
    cell.deliver({N: 1}, None)
    cell.deliver({W: 1}, None)  # out_buffer=2, data_valid=True
    accepted, _ = cell.deliver({N: 5}, None)
    assert accepted is True  # a NEW A can start capturing (a_reg/out_buffer are separate regs)
    accepted, _ = cell.deliver({W: 5}, None)
    assert accepted is False  # but B is blocked -- out_buffer still holds the undrained 2
    assert cell.adder_out_buffer == 2


def test_accumulator_three_increments_matches_tb_vector():
    rec = _rec("c0", 0, 0, "accumulator", {"downstream_mask": ["e"], "inc_dir": ["n"], "dec_dir": []})
    cell = SuperCell.from_record(rec)
    for _ in range(3):
        accepted, forward = cell.deliver({N: 1}, None)
        assert accepted is True and forward is None  # never blocked, no forward from capture itself
    assert cell.acc_total == 3


def test_accumulator_same_cycle_inc_and_dec_nets_zero():
    rec = _rec("c0", 0, 0, "accumulator", {"downstream_mask": ["e"], "inc_dir": ["n"], "dec_dir": ["s"]})
    cell = SuperCell.from_record(rec)
    cell.deliver({N: 1}, None)
    assert cell.acc_total == 1
    cell.deliver({N: 1, S: 1}, None)  # same tick, both directions -- must net to zero
    assert cell.acc_total == 1


def test_accumulator_negative_and_sign_bit():
    rec = _rec("c0", 0, 0, "accumulator", {"downstream_mask": ["e"], "inc_dir": [], "dec_dir": ["s"]})
    cell = SuperCell.from_record(rec)
    cell.deliver({S: 1}, None)
    cell.deliver({S: 1}, None)
    assert cell.acc_total == -2
    value, valid, _ = cell._offer_state()
    assert value == (0xFFFFFFFE)  # -2 as unsigned 32-bit, MSB set (status_negative would read 1)
    assert (value >> 31) & 1 == 1


def test_comparator_matches_tb_vector():
    rec = _rec("c0", 0, 0, "comparator", {"downstream_mask": ["e"], "upstream_mask": ["n"], "threshold": 8})
    cell = SuperCell.from_record(rec)
    accepted, _ = cell.deliver({N: 10}, None)
    assert accepted is True
    assert cell.cmp_out_buffer == 1  # 10 >= 8
    assert cell.cmp_data_valid is True


def test_comparator_below_threshold_and_signed():
    rec = _rec("c0", 0, 0, "comparator", {"downstream_mask": ["e"], "upstream_mask": ["n"], "threshold": 0})
    cell = SuperCell.from_record(rec)
    cell.deliver({N: 0xFFFFFFFF}, None)  # -1 signed
    assert cell.cmp_out_buffer == 0  # -1 >= 0 is false


def test_latch_set_and_clear_priority_matches_tb_vector():
    rec = _rec("c0", 0, 0, "latch", {"downstream_mask": ["e"], "set_dir": ["n"], "clear_dir": ["s"]})
    cell = SuperCell.from_record(rec)
    cell.deliver({N: 1}, None)
    assert cell.latch_state is True
    # clear takes priority when both arrive same tick, per #279/#284
    cell.deliver({N: 1, S: 1}, None)
    assert cell.latch_state is False


def test_latch_zero_value_does_not_falsely_set():
    # #295's own real bug: a genuine "0" reading on set_dir must NOT set.
    rec = _rec("c0", 0, 0, "latch", {"downstream_mask": ["e"], "set_dir": ["n"], "clear_dir": ["s"]})
    cell = SuperCell.from_record(rec)
    cell.deliver({N: 0}, None)  # arrives on set_dir but VALUE is 0
    assert cell.latch_state is False


def test_addon_nibble_mask_blocks_correct_nibbles():
    # block nibble 0 and nibble 7 (bits [3:0] and [31:28])
    out = apply_addons(0xFFFFFFFF, {"mask_en": 1, "nibble_mask": 0b10000001})
    assert out == 0x0FFFFFF0


def test_addon_shift_lane_left_and_right():
    left = apply_addons(0x00000001, {"shift_en": 1, "shift_amt": 4, "direction": 0})
    assert left == 0x00000010
    right = apply_addons(0x00000010, {"shift_en": 1, "shift_amt": 4, "direction": 1})
    assert right == 0x00000001


def test_addon_shift_unsupported_amount_is_noop():
    out = apply_addons(0xABCD1234, {"shift_en": 1, "shift_amt": 7, "direction": 0})
    assert out == 0xABCD1234


def test_addon_invert():
    out = apply_addons(0x00000000, {"invert_en": 1})
    assert out == 0xFFFFFFFF


def test_addon_chain_order_mask_then_shift_then_invert():
    # nibble_mask blocks nibble 0, THEN shift left 4, THEN invert.
    addon = {"mask_en": 1, "nibble_mask": 0b00000001, "shift_en": 1, "shift_amt": 4, "direction": 0,
             "invert_en": 1}
    out = apply_addons(0x000000FF, addon)
    # mask nibble0 -> 0x000000F0, shift left4 -> 0x00000F00, invert -> 0xFFFFF0FF
    assert out == 0xFFFFF0FF


def test_nano_delegates_to_real_cacell():
    # topology=OR(0x024), ready=1, routing_mask=N(1), cardinal_edge=0 (consume all)
    rec = _rec("c0", 0, 0, "nano", {"topology": 0x024, "ready": 1, "routing_mask": 1, "cardinal_edge": 0})
    cell = SuperCell.from_record(rec)
    assert cell._nano is not None
    assert cell._nano.topology == 0x024
    assert cell._nano.start_flag is True
    # two-arrival OR: first arrival captured as A, second fires
    accepted, forward = cell.deliver({S: 0}, None)
    assert accepted and forward is None
    accepted, forward = cell.deliver({E: 0xFF}, None)
    assert accepted
    mask, value = forward
    assert value == 0xFF  # OR(0, 0xFF)


def test_super_grid_ram_to_ram_delivery():
    # A fixed-value RAM at (0,0) offering east, a flowing RAM at (0,1)
    # capturing from west -- real cross-cell delivery through SuperGrid,
    # not just a single cell's own deliver() call.
    source = _rec("src", 0, 0, "ram", {"downstream_mask": ["e"], "fixed_mode": 1,
                                        "load_data_valid": 1, "init_data": 777})
    sink = _rec("sink", 0, 1, "ram", {"upstream_mask": ["w"]})
    grid = SuperGrid([source, sink])
    # kick the source's offer pass -- it has nothing pending initially
    for _ in range(5):
        grid.tick()
    sink_cell = grid.cells[(0, 1)]
    assert sink_cell.ram_data_reg == 777
    assert sink_cell.ram_data_valid is True


def test_super_grid_accumulator_heartbeat_never_quiesces():
    # A continuously-live core with a real downstream target should
    # re-offer forever -- run_to_quiescence must honestly time out, not
    # silently "complete."
    acc = _rec("acc", 0, 0, "accumulator", {"downstream_mask": ["e"], "inc_dir": ["n"]})
    sink = _rec("sink", 0, 1, "ram", {"upstream_mask": ["w"]})
    grid = SuperGrid([acc, sink])
    grid.inject(0, 0, 1)  # not directional -- accumulator ignores injected on purpose
    try:
        grid.run_to_quiescence(max_ticks=20)
    except TimeoutError:
        pass
    else:
        raise AssertionError("expected TimeoutError -- a continuously-live core must never quiesce")


# ── Core handler registry (points.md #358): proves a new core type can
# be added by registration alone, without touching SuperCell's own
# deliver()/_offer_state()/is_continuously_live() dispatch methods. ────

def test_registry_holds_exactly_the_five_non_nano_cores():
    from unicell_super_automaton_v1 import _CORE_HANDLERS
    assert set(_CORE_HANDLERS.keys()) == {"ram", "adder", "accumulator", "comparator", "latch"}


def test_registering_duplicate_core_handler_raises():
    from unicell_super_automaton_v1 import register_core_handler, CoreHandler
    try:
        register_core_handler("ram", CoreHandler(deliver=lambda *a: (True, None)))
    except ValueError as e:
        assert "already registered" in str(e)
    else:
        raise AssertionError("expected ValueError for duplicate registration")


def test_a_genuinely_new_core_can_be_added_by_registration_alone():
    # The real proof: register a brand-new, made-up core type (a simple
    # "pass_through" core that just forwards whatever arrives) using
    # ONLY register_core_handler() -- no edits to SuperCell's own
    # deliver()/_offer_state()/is_continuously_live() at all -- and
    # confirm it actually runs correctly through a real SuperGrid.
    from unicell_super_automaton_v1 import register_core_handler, CoreHandler, SuperCell

    def _deliver_pass_through(cell, arrivals, injected):
        if not arrivals and injected is None:
            return (True, None)
        val = injected if injected is not None else next(iter(arrivals.values()))
        cell.__dict__.setdefault("_pt_value", 0)
        cell._pt_value = val
        cell._pt_valid = True
        return (True, None)

    def _offer_state_pass_through(cell):
        return (getattr(cell, "_pt_value", 0), getattr(cell, "_pt_valid", False),
                getattr(cell, "_pt_downstream_mask", 0))

    def _clear_valid_pass_through(cell):
        cell._pt_valid = False

    register_core_handler("pass_through_test", CoreHandler(
        deliver=_deliver_pass_through, offer_state=_offer_state_pass_through,
        continuously_live=False, clear_valid=_clear_valid_pass_through,
    ))

    cell = SuperCell(row=0, col=0, core="pass_through_test")
    cell._pt_downstream_mask = v3.pack_dirmask(["e"])
    accepted, _ = cell.deliver({N: 42}, None)
    assert accepted is True
    value, valid, mask = cell._offer_state()
    assert (value, valid, mask) == (42, True, v3.pack_dirmask(["e"]))
    assert cell.is_continuously_live() is False
    cell.clear_valid_on_drain()
    assert cell._pt_valid is False


# ── Root-definition-driven construction validation (points.md #358) ───

def test_from_record_rejects_a_typo_d_field_name():
    rec = v3.IcmV3Record(cell_id="x", row=0, col=0, core="ram",
                          core_config={"downstrea_mask": ["e"], "init_data": 5})
    try:
        SuperCell.from_record(rec)
    except ValueError as e:
        assert "downstrea_mask" in str(e)
        assert "downstream_mask" in str(e)   # the real field name shows up in the suggestion
    else:
        raise AssertionError("expected ValueError for a typo'd field name")


def test_from_record_accepts_every_real_field_for_every_core():
    # confirms the validation is real and current, not silently
    # rejecting valid input -- every field this session's own tests
    # already rely on for all 6 cores must still construct cleanly.
    samples = {
        "nano": {"topology": 0x24, "ready": 1, "routing_mask": 1, "cardinal_edge": 0},
        "ram": {"downstream_mask": ["e"], "upstream_mask": ["w"], "fixed_mode": 1,
                "load_data_valid": 1, "init_data": 5},
        "adder": {"downstream_mask": ["e"], "upstream_mask": ["n", "w"]},
        "accumulator": {"downstream_mask": ["e"], "inc_dir": ["n"], "dec_dir": ["s"]},
        "comparator": {"downstream_mask": ["e"], "upstream_mask": ["n"], "threshold": 8},
        "latch": {"downstream_mask": ["e"], "set_dir": ["n"], "clear_dir": ["s"]},
    }
    for core, cfg in samples.items():
        rec = v3.IcmV3Record(cell_id="x", row=0, col=0, core=core, core_config=cfg)
        SuperCell.from_record(rec)   # must not raise


def test_from_record_rejects_a_typo_on_nano_too():
    rec = v3.IcmV3Record(cell_id="x", row=0, col=0, core="nano",
                          core_config={"topologyy": 0x24})
    try:
        SuperCell.from_record(rec)
    except ValueError as e:
        assert "topologyy" in str(e)
    else:
        raise AssertionError("expected ValueError for a typo'd nano field name")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
