"""
test_command_self_reprogram_v1.py -- points.md #868: the VM's own real
model of `command_cell_v4.v`'s incremental SELF-reprogram channel.

Real gap this closes, found by running it rather than reading comments:
`VixCarrierCell.program_word()` raised "no PROG_ID table exists for this
core type" on a command cell. `#866` (and a status note the next morning)
claimed it applied to `command` via COMMAND_PROG_ID_COMPLETE=7 -- that was
inferred from module-level constants and never executed, and was wrong.
The constants existed (PROG_ID_MODE .. COMMAND_PROG_ID_COMPLETE) but were
never wired into a table, so `#863`'s RTL-proven arm/disarm cycle could
not be exercised at the VM level at all.

Mirrors command_cell_v4.v's own `case (prog_id)` block exactly:
  0 MODE -> [0]   1 POLARITY -> [0]   2 DRIVE_DIR -> [2:0]
  3 TOGGLE_PATTERN -> [3:0]   7 COMPLETE -> program_done, armed <= [0]
COMPLETE is the only thing that writes `armed`, and nothing else ever
clears it -- not even finishing a relay sequence (confirmed against the
RTL by grepping every reference to `armed`, #863).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import (  # noqa: E402
    VixCarrierGrid, COMMAND_PROG_ID_COMPLETE as CMD_COMPLETE,
    PROG_ID_MODE, PROG_ID_POLARITY, PROG_ID_DRIVE_DIR, PROG_ID_TOGGLE_PATTERN,
)
from unicell_automaton_v1 import (  # noqa: E402
    PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK, PROG_ID_COMPLETE,
)
from unicell_gate_core import TOPO_NOT_A, TOPO_AND  # noqa: E402


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _lone_command():
    r = _rec("C", 0, 0, "command",
             {"mode": 1, "polarity": 0, "drive_dir": 2, "toggle_pattern": 15})
    return VixCarrierGrid([r]).cells[(0, 0)]


def _set_armed(cell, value):
    cell.program_in = True
    cell.program_word(CMD_COMPLETE, 1 if value else 0)
    cell.program_in = False


def test_complete_writes_armed_and_program_done():
    cell = _lone_command()
    assert cell.command_armed is True, "cfg loading arms unconditionally (real RTL behaviour)"
    _set_armed(cell, False)
    assert cell.command_armed is False and cell.program_done is True
    _set_armed(cell, True)
    assert cell.command_armed is True


def test_field_writes_mask_to_the_real_rtl_widths():
    cell = _lone_command()
    cell.program_word(PROG_ID_MODE, 0b110)            # only bit 0 counts
    assert cell.command_mode is False
    cell.program_word(PROG_ID_POLARITY, 0b011)
    assert cell.command_polarity is True
    cell.program_word(PROG_ID_DRIVE_DIR, 0xFF)        # [2:0]
    assert cell.command_drive_dir == 0x7
    cell.program_word(PROG_ID_TOGGLE_PATTERN, 0xFF)   # [3:0]
    assert cell.command_toggle_pattern == 0xF


def test_unrecognized_id_is_a_noop_like_the_rtl_default_branch():
    cell = _lone_command()
    before = (cell.command_mode, cell.command_polarity, cell.command_drive_dir,
              cell.command_toggle_pattern, cell.command_armed)
    cell.program_word(5, 0xFFFF)                      # not in command's table
    after = (cell.command_mode, cell.command_polarity, cell.command_drive_dir,
             cell.command_toggle_pattern, cell.command_armed)
    assert before == after


def test_program_in_flag_round_trips_for_command():
    cell = _lone_command()
    assert cell.program_in is False
    cell.program_in = True
    assert cell.program_in is True
    cell.program_in = False
    assert cell.program_in is False


def test_other_cores_keep_their_own_unchanged_dispatch():
    grid = VixCarrierGrid([
        _rec("A", 0, 0, "adder", {"downstream_mask": 0b0100, "upstream_mask": 0b0011}),
        _rec("R", 1, 0, "ram", {}),
    ])
    adder, ram = grid.cells[(0, 0)], grid.cells[(1, 0)]
    adder.program_in = True
    adder.program_word(2, 1)                          # adder PROG_ID 2 = subtract_mode
    assert adder.adder_subtract_mode is True
    ram.program_word(3, 0xBEEF)                       # ram PROG_ID 3 = init low half
    assert ram.ram_data_reg & 0xFFFF == 0xBEEF


def _two_cell_programmer_grid():
    cmd = _rec("CMD", 0, 0, "command", {"mode": 1, "polarity": 0, "drive_dir": 2,
                                        "toggle_pattern": PROG_ID_COMPLETE})
    tgt = _rec("TGT", 0, 1, "nano", {})
    grid = VixCarrierGrid([cmd, tgt])
    return grid, grid.cells[(0, 0)], grid.cells[(0, 1)]


def _send_sequence(grid, topology, mask):
    for w in ((PROG_ID_TOPOLOGY << 20) | topology,
              (PROG_ID_ROUTING_MASK << 20) | mask,
              (PROG_ID_COMPLETE << 20) | 1):
        grid.inject(0, 0, w)
        grid.run_to_quiescence()


def test_a_disarmed_command_cell_ignores_a_word_an_armed_one_relays():
    """The VM-level version of #863's steps 1-3."""
    grid, cmd, tgt = _two_cell_programmer_grid()
    _set_armed(cmd, False)

    grid.inject(0, 0, (PROG_ID_TOPOLOGY << 20) | TOPO_NOT_A)
    for _ in range(4):
        grid.tick()
    assert tgt.freeze_in is False and cmd.command_active_r is False, "disarmed: nothing must start"
    assert tgt._nano.topology != TOPO_NOT_A, "disarmed: the word must not have reached the target"
    grid._pending.pop((0, 0), None)                   # withdraw the stalled injection

    _set_armed(cmd, True)
    _send_sequence(grid, TOPO_NOT_A, 0b0100)
    assert tgt._nano.start_flag is True and tgt.freeze_in is False
    assert (tgt._nano.topology, tgt._nano.routing_mask) == (TOPO_NOT_A, 0b0100)


def test_disarm_then_rearm_reprograms_the_same_target_a_second_time():
    """The VM-level version of #863's steps 4-6: a genuine, repeatable
    cycle, not a one-shot -- second pass with different content."""
    grid, cmd, tgt = _two_cell_programmer_grid()
    _send_sequence(grid, TOPO_NOT_A, 0b0100)
    assert (tgt._nano.topology, tgt._nano.routing_mask) == (TOPO_NOT_A, 0b0100)
    assert cmd.command_armed is True, "finishing a sequence must NOT disarm -- only an explicit COMPLETE,0 does"

    _set_armed(cmd, False)
    grid.inject(0, 0, (PROG_ID_TOPOLOGY << 20) | TOPO_AND)
    for _ in range(4):
        grid.tick()
    assert tgt._nano.topology == TOPO_NOT_A, "disarmed: the spurious word must be ignored"
    grid._pending.pop((0, 0), None)

    _set_armed(cmd, True)
    _send_sequence(grid, TOPO_AND, 0b0010)
    assert (tgt._nano.topology, tgt._nano.routing_mask) == (TOPO_AND, 0b0010)
    assert tgt.freeze_in is False and cmd.command_active_r is False
