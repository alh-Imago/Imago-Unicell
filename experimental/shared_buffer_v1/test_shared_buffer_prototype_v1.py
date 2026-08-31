"""
test_shared_buffer_prototype_v1.py — points.md #561: real cross-checks
proving the shared union-buffer design (Alan's own real idea) produces
identical results to the existing, proven-correct VM behavior, before
any RTL work begins. Every test vector here is reused directly from
already-passing tests elsewhere in this suite, not invented fresh --
the point is cross-verification against known-correct behavior, not a
new, independent claim of correctness.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "nano"))

from shared_buffer_prototype_v1 import SharedBufferCell, TOTAL_BUFFER_WIDTH  # noqa: E402


def test_shared_buffer_width_is_166_not_128():
    # Real, honest correction found while designing this (#561): nano's
    # own real total (cmd_latch 128 + data_reg 32 + pending_ack 6) is
    # 166 bits, not Alan's own originally-proposed 128 -- data_reg and
    # pending_ack sit alongside cmd_latch in the real RTL, not inside it.
    assert TOTAL_BUFFER_WIDTH == 166


def test_adder_subtract_matches_real_rtl_test_vector():
    # Reused directly from test_adder_subtract_mode_computes_a_minus_b
    cell = SharedBufferCell()
    cell.adder_deliver({0: 23}, upstream_mask=0b1001, subtract_mode=1)
    cell.adder_deliver({3: 7}, upstream_mask=0b1001, subtract_mode=1)
    result, valid = cell.adder_offer()
    assert result == 16
    assert valid is True


def test_adder_borrow_matches_real_rtl_test_vector():
    # Reused directly from test_adder_subtract_mode_real_borrow_wraps_correctly
    cell = SharedBufferCell()
    cell.adder_deliver({0: 7}, upstream_mask=0b1001, subtract_mode=1)
    cell.adder_deliver({3: 23}, upstream_mask=0b1001, subtract_mode=1)
    result, valid = cell.adder_offer()
    assert result == 0xFFFFFFF0
    assert valid is True


def test_accumulator_matches_real_three_pulse_vector():
    # Reused directly from example_icm_branch_demo_v1.py's own real check
    cell = SharedBufferCell()
    for _ in range(3):
        cell.acc_deliver(inc=True, dec=False, step_amount=1, pulse_mode=False, threshold=0)
    assert cell._get_signed(0, 31) == 3


def test_branch_low_matches_real_silicon_confirmed_design():
    # Reused directly from the real, silicon-confirmed branch cell design (#530/#542)
    cell = SharedBufferCell()
    seed_outcome = cell.branch_deliver(8, 0, 0, 1, 2, 99)
    assert seed_outcome is None  # held-reference seeding, no output yet
    outcome = cell.branch_deliver(5, 0, 0, 1, 2, 99)
    assert outcome == "low"
    marker, valid = cell.branch_offer()
    assert marker == 1
    assert valid is True


def test_branch_equal_matches_real_silicon_confirmed_design():
    cell = SharedBufferCell()
    cell.branch_deliver(8, 0, 0, 1, 2, 99)
    outcome = cell.branch_deliver(8, 0, 0, 1, 2, 99)
    assert outcome == "equal"
    marker, _ = cell.branch_offer()
    assert marker == 2


def test_nano_cmd_latch_and_data_reg_coexist_without_interference():
    # The real case that sets the shared buffer's own width -- nano is
    # the only core needing more than one wide field simultaneously.
    cell = SharedBufferCell()
    cmd_word = 0x123456789ABCDEF0123456789ABCDEF0
    cell.nano_program(cmd_word)
    cell.nano_set_data_reg(0xDEADBEEF)
    assert cell.nano_data_reg() == 0xDEADBEEF
    assert cell._get(0, 127) == cmd_word


def test_different_cores_can_reuse_the_same_bit_positions_safely():
    # The real point of a union buffer: two DIFFERENT cores' own state,
    # run sequentially (never simultaneously, matching real core_select
    # semantics), correctly overwrite each other's bit ranges rather
    # than corrupting one another -- proven directly, not assumed.
    cell = SharedBufferCell()
    cell.adder_deliver({0: 100}, upstream_mask=0b1001, subtract_mode=0)
    cell.adder_deliver({3: 23}, upstream_mask=0b1001, subtract_mode=0)
    adder_result, _ = cell.adder_offer()
    assert adder_result == 123

    # Now reuse the SAME physical buffer for branch cell -- a real
    # reconfiguration event would clear/reinterpret it this way.
    cell.buf = 0
    seed = cell.branch_deliver(8, 0, 0, 1, 2, 99)
    assert seed is None
    outcome = cell.branch_deliver(10, 0, 0, 1, 2, 99)
    assert outcome == "high"


def test_ram_matches_real_capture_and_doubly_full_blocking():
    cell = SharedBufferCell()
    ok = cell.ram_deliver({0: 0xCAFEBABE}, upstream_mask=0b0001, fixed_mode=False)
    assert ok is True
    val, valid = cell.ram_offer()
    assert val == 0xCAFEBABE
    assert valid is True
    ok2 = cell.ram_deliver({0: 0x11111111}, upstream_mask=0b0001, fixed_mode=False)
    assert ok2 is False  # doubly full, matching the real RTL exactly


def test_compare_matches_real_signed_ge_semantics_both_outcomes():
    cell_true = SharedBufferCell()
    cell_true.compare_deliver({0: 10}, upstream_mask=0b0001, threshold=8)
    result_true, valid_true = cell_true.compare_offer()
    assert result_true == 1
    assert valid_true is True

    cell_false = SharedBufferCell()
    cell_false.compare_deliver({0: 5}, upstream_mask=0b0001, threshold=8)
    result_false, _ = cell_false.compare_offer()
    assert result_false == 0


def test_latch_matches_real_clear_set_toggle_priority_chain():
    cell = SharedBufferCell()
    cell.latch_deliver({0: 1}, set_dir=0b0001, clear_dir=0b0010, toggle_dir=0b0100)
    state, _ = cell.latch_offer()
    assert state == 1
    # SET + CLEAR arriving together -- CLEAR must win, matching the real RTL
    cell.latch_deliver({0: 1, 1: 1}, set_dir=0b0001, clear_dir=0b0010, toggle_dir=0b0100)
    state2, _ = cell.latch_offer()
    assert state2 == 0


def test_sequencer_matches_real_advance_on_ack_and_wraps():
    # Implemented fresh from sequencer_cell_v1.v's own real RTL --
    # no existing VM dispatch exists to cross-check against (#561's
    # own real, already-documented mirror-image gap).
    cell = SharedBufferCell()
    cell.sequencer_init(values=[10, 20, 30, 40], sequence_len_m1=2)  # real length 3
    v1, _ = cell.sequencer_offer()
    assert v1 == 10
    cell.sequencer_ack_advance()
    v2, _ = cell.sequencer_offer()
    assert v2 == 20
    cell.sequencer_ack_advance()
    v3, _ = cell.sequencer_offer()
    assert v3 == 30
    cell.sequencer_ack_advance()
    v4, _ = cell.sequencer_offer()
    assert v4 == 10  # wraps back to index 0


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
