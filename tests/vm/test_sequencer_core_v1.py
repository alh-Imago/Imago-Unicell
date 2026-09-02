"""tests/vm/test_sequencer_core_v1.py — points.md #609: real tests for
the sequencer core's VM dispatch, closing the SEL_SEQ=6 half of #519's
own real asymmetry (real RTL since unicell_super_v2.v, previously no
VM dispatch at all). Matches this project's own "don't just check the
format, run it" discipline -- every test drives a real SuperGrid, not
just SuperCell field assignment.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _seq_record(values, sequence_len, downstream_mask, cell_id="seq", row=0, col=0):
    cfg = {"downstream_mask": downstream_mask}
    for i, v in enumerate(values):
        cfg[f"VALUE_{i}"] = v
    cfg["SEQUENCE_LEN"] = sequence_len - 1
    return v3.IcmV3Record(cell_id=cell_id, row=row, col=col, core="sequencer", core_config=cfg)


def test_from_record_sets_real_fields_correctly():
    rec = _seq_record([10, 20, 30, 40], sequence_len=4, downstream_mask=["e"])
    grid = SuperGrid([rec])
    cell = grid.cells[(0, 0)]
    assert cell.seq_value_0 == 10
    assert cell.seq_value_1 == 20
    assert cell.seq_value_2 == 30
    assert cell.seq_value_3 == 40
    assert cell.seq_sequence_len_m1 == 3
    assert cell.seq_downstream_mask == 4  # E = bit 2 = 4
    assert cell.seq_index == 0
    assert cell.seq_out_buffer == 10   # value_for_index(0), matching the real RTL's own reset snapshot
    assert cell.seq_data_valid is True  # live from the first cycle after config


def test_data_valid_never_toggles_off():
    """Real, direct confirmation of the module's own documented
    difference from every other single-shot core: this cell is
    perpetually live, never actually drained/reclosed."""
    rec = _seq_record([1, 2], sequence_len=2, downstream_mask=["e"])
    grid = SuperGrid([rec])
    cell = grid.cells[(0, 0)]
    for _ in range(20):
        grid.tick()
        cell.pending_ack = 0  # force-simulate an instantaneous ack (no real neighbor here)
        assert cell.seq_data_valid is True


def test_deliver_never_captures_anything():
    """Real RTL fact: ack_out is tied low on EVERY direction -- this
    core never genuinely accepts an arrival, matching ram_fixed_mode's
    own established "nothing to capture" pattern (accepted=False when
    something arrives, not a silent free pass)."""
    rec = _seq_record([5], sequence_len=1, downstream_mask=["e"])
    grid = SuperGrid([rec])
    cell = grid.cells[(0, 0)]
    accepted, forward = cell.deliver({}, None)
    assert accepted is True   # nothing arrived, nothing to reject
    accepted, forward = cell.deliver({0: 999}, None)  # arbitrary arrival on N
    assert accepted is False  # real RTL never acks
    assert cell.seq_out_buffer == 5   # unaffected by the arrival -- genuinely no capture side


def test_real_two_cell_cycle_through_a_real_consumer():
    """The real, whole-point end-to-end confirmation: a sequencer
    feeding a real ram consumer across real ticks, values arriving in
    the real configured order, wrapping correctly."""
    seq = _seq_record([10, 20, 30], sequence_len=3, downstream_mask=["e"], cell_id="seq", row=0, col=0)
    consumer = v3.IcmV3Record(cell_id="consumer", row=0, col=1, core="ram",
                               core_config={"upstream_mask": ["w"], "downstream_mask": [], "fixed_mode": 0})
    grid = SuperGrid([seq, consumer])
    seq_cell = grid.cells[(0, 0)]
    ram_cell = grid.cells[(0, 1)]

    received = []
    for _ in range(10):
        grid.tick()
        if ram_cell.ram_data_valid:
            received.append(ram_cell.ram_data_reg)
            ram_cell.ram_data_valid = False   # consumer "reads" and re-opens
    assert received[:9] == [10, 20, 30, 10, 20, 30, 10, 20, 30]


def test_sequence_length_one_stays_constant():
    rec = _seq_record([42], sequence_len=1, downstream_mask=["e"])
    grid = SuperGrid([rec])
    cell = grid.cells[(0, 0)]
    for _ in range(5):
        grid.tick()
        cell.pending_ack = 0
        assert cell.seq_out_buffer == 42
        assert cell.seq_index == 0


def test_no_downstream_mask_means_no_real_neighbor_ever_receives():
    rec = _seq_record([1, 2], sequence_len=2, downstream_mask=[])
    grid = SuperGrid([rec])
    cell = grid.cells[(0, 0)]
    grid.tick()
    assert cell.pending_ack == 0   # nothing to offer to -- downstream==0 skips the offer pass entirely


def test_pack_unpack_core_config_round_trips_real_uppercase_field_names():
    """Real, direct confirmation this core's own genuinely inconsistent
    RTL comment casing (VALUE_0/SEQUENCE_LEN uppercase, unlike every
    other core's lowercase convention) round-trips correctly through
    icm_v3.py's generic pack/unpack, matching the real, mechanically
    extracted field names exactly -- not silently "corrected.\""""
    packed = v3.pack_core_config("sequencer", {
        "VALUE_0": 1, "VALUE_1": 2, "VALUE_2": 3, "VALUE_3": 4,
        "SEQUENCE_LEN": 3, "downstream_mask": ["n", "s"],
    })
    unpacked = v3.unpack_core_config("sequencer", packed)
    assert unpacked["VALUE_0"] == 1
    assert unpacked["SEQUENCE_LEN"] == 3
    assert set(unpacked["downstream_mask"]) == {"n", "s"}


def test_minimum_shell_version_requires_v2_for_sequencer():
    rec = _seq_record([1], sequence_len=1, downstream_mask=["e"])
    assert v3.minimum_shell_version([rec]) == "unicell_super_v2"
