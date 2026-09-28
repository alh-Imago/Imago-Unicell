"""
test_reconfig_loop_v1.py -- points.md #868: `#843`'s reconfiguration LOOP
assembled in ONE real VM grid for the first time -- `#858`'s drain-detection
latch and `#862`/`#863`'s command-cell live-reconfigure (arm/disarm cycle),
which until now were proven separately, in different simulation domains.

Topology (one `VixCarrierGrid`):
  * DRAIN SECTION (#858 exactly): src -> head -> tail -> sink, with a wrapped
    relay tail->relay_r->latch's CLEAR and head's south fan-out into the
    latch's SET. The latch's own output is left UNCONNECTED on purpose: a
    continuously-live latch offering into a command cell would start a relay
    on ANY arrival while armed (programmer mode needs no match to start).
  * WORD SOURCE: a SERIALIZED chain of three `ram` cells feeding the command
    cell from the north -- nearest speaks first, each cell's value shifting
    forward as the one ahead is consumed. This is the "buffer chain" the
    command-core design note describes.
  * COMMAND CELL (programmer mode, drive_dir=S) + a fresh, never-configured
    `nano` target below it.

Real design history, kept honest:
  A first version fed the command cell from THREE PARALLEL neighbours. It
  failed in a specific, informative way: the VM acked all three offers in one
  tick but processed only the priority winner (N>S>E>W), so the mask and
  COMPLETE words were silently dropped and the target stayed frozen forever.
  The RTL acks ONLY the selected direction (`ack_out_n = watch_capture_now &&
  watch_sel_n`), so the RTL would have delivered all three in priority order:
  this is a genuine VM-vs-RTL fidelity gap (see the last test), and the same
  family as the known simultaneous-arrival hazard (#750/#764/#776). The
  serialized chain sidesteps it AND matches the design intent.

REAL, HONEST SCOPE -- what is and is not proven here:
  PROVEN: the latch, the serialized word chain, the command cell and the
  target coexist and compose in one grid; a DISARMED command cell holds a
  full chain of words without touching the target while the section runs and
  drains; arming it after the drain delivers the whole sequence in order,
  freezes the target only for the burst, and releases it on COMPLETE; the
  whole loop repeats with different content.
  NOT PROVEN (still host-driven, standing in for wiring that does not exist):
    - The arm decision is the HOST observing `latch_state`. No cell carries
      the latch's SET/CLEAR into the command cell's reprogram channel.
    - Between passes the HOST reloads the chain, reloads the source and
      drains the sink via `program_word()`.
  Those two are the remaining distance to a fully unattended fold.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import (  # noqa: E402
    VixCarrierGrid, COMMAND_PROG_ID_COMPLETE as CMD_COMPLETE,
)
from unicell_automaton_v1 import (  # noqa: E402
    PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK, PROG_ID_COMPLETE,
)
from unicell_gate_core import TOPO_NOT_A, TOPO_AND  # noqa: E402

# Grid coordinates the tests share.
LAT = (1, 0)
CMD = (7, 1)
TGT = (8, 1)
CHAIN_ROWS = (4, 5, 6)       # (4,1) speaks LAST (COMPLETE), (6,1) speaks FIRST (topology)


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _words(topology, mask):
    """(topology word, mask word, COMPLETE word) for a nano target."""
    return ((PROG_ID_TOPOLOGY << 20) | topology,
            (PROG_ID_ROUTING_MASK << 20) | mask,
            (PROG_ID_COMPLETE << 20) | 1)


def _build(ws):
    w_topo, w_mask, w_done = ws
    return VixCarrierGrid([
        _rec("src", 0, -1, "ram", {"init_data": 43, "load_data_valid": 1, "downstream_mask": ["e"]}),
        _rec("head", 0, 0, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e", "s"]}),
        _rec("tail", 0, 1, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e", "s"]}),
        _rec("sink", 0, 2, "ram", {"upstream_mask": ["w"], "downstream_mask": []}),
        _rec("relay_r", 1, 1, "ram", {"upstream_mask": ["n"], "downstream_mask": ["w"]}),
        _rec("lat", 1, 0, "latch", {"set_dir": ["n"], "clear_dir": ["e"], "downstream_mask": []}),
        _rec("c3", 4, 1, "ram", {"init_data": w_done, "load_data_valid": 1,
                                 "upstream_mask": [], "downstream_mask": ["s"]}),
        _rec("c2", 5, 1, "ram", {"init_data": w_mask, "load_data_valid": 1,
                                 "upstream_mask": ["n"], "downstream_mask": ["s"]}),
        _rec("c1", 6, 1, "ram", {"init_data": w_topo, "load_data_valid": 1,
                                 "upstream_mask": ["n"], "downstream_mask": ["s"]}),
        _rec("CMD", 7, 1, "command", {"mode": 1, "polarity": 0, "drive_dir": 1,
                                      "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("TGT", 8, 1, "nano", {}),
    ])


def _set_armed(cmd, value):
    cmd.program_in = True
    cmd.program_word(CMD_COMPLETE, 1 if value else 0)
    cmd.program_in = False


def _reload_word(cell, word):
    """Host stand-in: reload one ram cell's stored word and mark it valid,
    via the same generic, real program_word() channel every core has."""
    cell.program_in = True
    cell.program_word(3, word & 0xFFFF)            # init_data low half
    cell.program_word(4, (word >> 16) & 0xFFFF)    # init_data high half
    cell.program_word(6, 1)                        # data_valid
    cell.program_in = False


def _snap(tgt):
    return (tgt._nano.topology, tgt._nano.routing_mask, tgt._nano.start_flag)


def _run_pass(grid, want, cap=60):
    """Tick until the latch has gone occupied -> drained, arm on that edge,
    then tick until the target holds `want`. Returns observations."""
    cmd, tgt, lat = grid.cells[CMD], grid.cells[TGT], grid.cells[LAT]
    before = _snap(tgt)
    seen_occupied = False
    arm_tick = None
    active_before_arm = False
    disturbed_before_arm = False
    for t in range(cap):
        grid.tick()
        if arm_tick is None:
            active_before_arm |= cmd.command_active_r
            disturbed_before_arm |= (_snap(tgt) != before) or tgt.freeze_in
        if lat.latch_state:
            seen_occupied = True
        if arm_tick is None and seen_occupied and not lat.latch_state:
            _set_armed(cmd, True)
            arm_tick = t
        if (arm_tick is not None and not cmd.command_active_r
                and _snap(tgt)[:2] == want and _snap(tgt)[2] and not tgt.freeze_in):
            return {"seen_occupied": seen_occupied, "arm_tick": arm_tick, "done_tick": t,
                    "active_before_arm": active_before_arm,
                    "disturbed_before_arm": disturbed_before_arm}
    return {"seen_occupied": seen_occupied, "arm_tick": arm_tick, "done_tick": None,
            "active_before_arm": active_before_arm,
            "disturbed_before_arm": disturbed_before_arm}


def test_a_disarmed_command_cell_holds_a_full_word_chain_while_the_section_drains():
    """The gate, in one grid: the latch really cycles occupied -> drained
    around a command cell that is disarmed and has a full chain of words
    waiting -- and the target is never touched."""
    grid = _build(_words(TOPO_NOT_A, 0b0100))
    cmd, tgt, lat = grid.cells[CMD], grid.cells[TGT], grid.cells[LAT]
    _set_armed(cmd, False)
    before = _snap(tgt)
    saw_occupied = False
    for _ in range(20):
        grid.tick()
        saw_occupied |= lat.latch_state
    assert saw_occupied and lat.latch_state is False, "the drain latch must genuinely cycle in this grid"
    assert _snap(tgt) == before and tgt.freeze_in is False and cmd.command_active_r is False
    assert [grid.cells[(r, 1)].ram_data_valid for r in CHAIN_ROWS] == [True, True, True], \
        "disarmed: not one word may have been consumed"


def test_arming_on_the_drain_edge_delivers_the_whole_sequence_in_order():
    grid = _build(_words(TOPO_NOT_A, 0b0100))
    cmd, tgt = grid.cells[CMD], grid.cells[TGT]
    _set_armed(cmd, False)
    res = _run_pass(grid, (TOPO_NOT_A, 0b0100))
    assert res["seen_occupied"], "the section must have been observed occupied first"
    assert res["done_tick"] is not None, "the reconfigure must complete"
    assert res["arm_tick"] < res["done_tick"]
    assert res["active_before_arm"] is False and res["disturbed_before_arm"] is False, \
        "nothing may happen to the command cell or target before the drain edge"
    assert _snap(tgt) == (TOPO_NOT_A, 0b0100, True)
    assert tgt.freeze_in is False and cmd.command_active_r is False
    assert [grid.cells[(r, 1)].ram_data_valid for r in CHAIN_ROWS] == [False, False, False], \
        "every word consumed exactly once"


def test_the_target_is_frozen_only_for_the_burst():
    grid = _build(_words(TOPO_NOT_A, 0b0100))
    cmd, tgt = grid.cells[CMD], grid.cells[TGT]
    _set_armed(cmd, False)
    frozen_during_relay = False
    # drive manually so the freeze can be observed tick by tick
    lat = grid.cells[LAT]
    seen_occupied, armed = False, False
    for _ in range(60):
        grid.tick()
        seen_occupied |= lat.latch_state
        if seen_occupied and not lat.latch_state and not armed:
            _set_armed(cmd, True)
            armed = True
        if cmd.command_active_r:
            frozen_during_relay |= tgt.freeze_in
        if armed and not cmd.command_active_r and _snap(tgt)[2]:
            break
    assert frozen_during_relay is True, "target must be frozen while the relay is active"
    assert tgt.freeze_in is False, "and released once COMPLETE has been delivered"


def test_the_loop_repeats_with_different_content_and_the_gate_holds_between_passes():
    """The decisive test: not a one-shot. Disarm, reload the chain with NEW
    words, re-run the section, and confirm (a) the target keeps its old
    config while the new words sit waiting, (b) the latch re-detects the
    next drain, (c) arming then delivers the NEW content."""
    grid = _build(_words(TOPO_NOT_A, 0b0100))
    cmd, tgt = grid.cells[CMD], grid.cells[TGT]
    _set_armed(cmd, False)
    first = _run_pass(grid, (TOPO_NOT_A, 0b0100))
    assert first["done_tick"] is not None

    # Host stand-ins for the wiring that doesn't exist yet.
    _set_armed(cmd, False)
    for row, word in zip((6, 5, 4), _words(TOPO_AND, 0b0010)):
        _reload_word(grid.cells[(row, 1)], word)
    src, sink = grid.cells[(0, -1)], grid.cells[(0, 2)]
    src.program_in = True; src.program_word(6, 1); src.program_in = False
    sink.program_in = True; sink.program_word(6, 0); sink.program_in = False
    assert _snap(tgt)[:2] == (TOPO_NOT_A, 0b0100), "still pass-1 config while pass-2 words wait"

    second = _run_pass(grid, (TOPO_AND, 0b0010))
    assert second["seen_occupied"], "the latch must re-detect occupancy on the second pass"
    assert second["done_tick"] is not None, "the second reconfigure must complete"
    assert second["active_before_arm"] is False and second["disturbed_before_arm"] is False, \
        "gate held: the full chain of NEW words did not touch the target before the second drain edge"
    assert _snap(tgt) == (TOPO_AND, 0b0010, True)
    assert tgt.freeze_in is False


def test_known_vm_gap_parallel_word_sources_are_all_consumed_but_only_one_processed():
    """A DOCUMENTED divergence, asserted as current behaviour so it cannot
    silently change -- same discipline as the underflow-gap tests. Three
    neighbours offering to one command cell on the same tick: the VM acks
    all three but the cell processes only the priority winner, so the target
    is left frozen forever. The RTL acks only the selected direction
    (`ack_out_x = watch_capture_now && watch_sel_x`) and would deliver all
    three in priority order. If this test starts failing because the VM was
    fixed to ack per direction, update it -- that would be an improvement."""
    w_topo, w_mask, w_done = _words(TOPO_NOT_A, 0b0100)
    grid = VixCarrierGrid([
        _rec("wA", 3, 1, "ram", {"init_data": w_topo, "load_data_valid": 1, "downstream_mask": ["s"]}),
        _rec("wB", 4, 2, "ram", {"init_data": w_mask, "load_data_valid": 1, "downstream_mask": ["w"]}),
        _rec("wC", 4, 0, "ram", {"init_data": w_done, "load_data_valid": 1, "downstream_mask": ["e"]}),
        _rec("CMD", 4, 1, "command", {"mode": 1, "polarity": 0, "drive_dir": 1,
                                      "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("TGT", 5, 1, "nano", {}),
    ])
    tgt = grid.cells[(5, 1)]
    for _ in range(20):
        grid.tick()
    consumed = [not grid.cells[c].ram_data_valid for c in ((3, 1), (4, 2), (4, 0))]
    assert consumed == [True, True, True], "the VM over-consumes: all three acked in one tick"
    assert tgt._nano.start_flag is False, "but COMPLETE was never processed"
    assert tgt.freeze_in is True, "so the target is left frozen -- the reconfigure never finishes"


def _build_unattended():
    """The same loop with NO host trigger. The value travelling through the
    drain section IS the arm word; the pulse that clears the latch (relay_r's
    one-shot offer) also runs down a relay column to a second command cell,
    whose target is the first command cell, directly west of it."""
    arm_word = (CMD_COMPLETE << 20) | 1          # PROG_ID 7, armed <= 1; bit0=1 also satisfies latch SET
    w_topo, w_mask, w_done = _words(TOPO_NOT_A, 0b0100)
    cells = [
        _rec("src", 0, -1, "ram", {"init_data": arm_word, "load_data_valid": 1, "downstream_mask": ["e"]}),
        _rec("head", 0, 0, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e", "s"]}),
        _rec("tail", 0, 1, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e", "s"]}),
        _rec("sink", 0, 2, "ram", {"upstream_mask": ["w"], "downstream_mask": []}),
        _rec("relay_r", 1, 1, "ram", {"upstream_mask": ["n"], "downstream_mask": ["w", "e"]}),
        _rec("lat", 1, 0, "latch", {"set_dir": ["n"], "clear_dir": ["e"], "downstream_mask": []}),
        _rec("t1", 1, 2, "ram", {"upstream_mask": ["w"], "downstream_mask": ["s"]}),
    ]
    cells += [_rec(f"t{r}", r, 2, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"]}) for r in range(2, 7)]
    cells += [
        _rec("CMD2", 7, 2, "command", {"mode": 1, "polarity": 0, "drive_dir": 3,
                                       "toggle_pattern": CMD_COMPLETE}),
        _rec("c3", 4, 1, "ram", {"init_data": w_done, "load_data_valid": 1,
                                 "upstream_mask": [], "downstream_mask": ["s"]}),
        _rec("c2", 5, 1, "ram", {"init_data": w_mask, "load_data_valid": 1,
                                 "upstream_mask": ["n"], "downstream_mask": ["s"]}),
        _rec("c1", 6, 1, "ram", {"init_data": w_topo, "load_data_valid": 1,
                                 "upstream_mask": ["n"], "downstream_mask": ["s"]}),
        _rec("CMD1", 7, 1, "command", {"mode": 1, "polarity": 0, "drive_dir": 1,
                                       "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("TGT", 8, 1, "nano", {}),
    ]
    return VixCarrierGrid(cells)


def test_no_host_needed_after_setup_the_drain_pulse_arms_the_command_cell_in_grid():
    """THE missing trigger, closed for one pass. After ONE setup step (cfg
    loading always arms a command cell, so command cell #1 is disarmed once)
    there is no host action anywhere in the loop: the drain pulse itself
    reaches command cell #2, which relays the arm word into command cell #1,
    which then delivers its word chain to the target.

    REAL, HONEST SIMPLIFICATIONS -- do not read this as a general fold yet:
      * The section's payload IS the arm word, so the drain pulse doubles as
        the trigger word. A real fold carries real data, so the general design
        would use the tail's pulse as the TRIGGER for a hold+reemit source
        preloaded with the arm word (the proven #382 primitive; the trigger's
        content is irrelevant) -- not built or tested here.
      * Only pass 1. Reloading the chain/section for a second pass is still
        host-driven, and nothing yet disarms command cell #1 in-grid.
      * VM only: command-into-command relay has not been run in RTL."""
    grid = _build_unattended()
    cmd1, cmd2 = grid.cells[(7, 1)], grid.cells[(7, 2)]
    tgt, lat = grid.cells[TGT], grid.cells[LAT]
    _set_armed(cmd1, False)                      # the ONE-TIME setup step
    assert cmd2._resolve_command_target() is cmd1

    before = _snap(tgt)
    saw_occupied = saw_drained = False
    drained_at = armed_at = done_at = None
    armed_before_drain = disturbed_before_arm = False
    for t in range(80):
        grid.tick()
        if lat.latch_state:
            saw_occupied = True
        if saw_occupied and not lat.latch_state and drained_at is None:
            drained_at = t
        if cmd1.command_armed and armed_at is None:
            armed_at = t
            armed_before_drain = drained_at is None
        if armed_at is None:
            disturbed_before_arm |= (_snap(tgt) != before) or tgt.freeze_in
        if armed_at is not None and _snap(tgt) == (TOPO_NOT_A, 0b0100, True) \
                and not tgt.freeze_in and not cmd1.command_active_r:
            done_at = t
            break

    assert saw_occupied and drained_at is not None, "the drain latch must cycle"
    assert armed_at is not None, "command cell #1 must get armed with no host action"
    assert armed_before_drain is False and armed_at > drained_at, \
        "it must be armed only AFTER the section has drained, never before"
    assert disturbed_before_arm is False, "the target must be untouched until armed"
    assert done_at is not None and done_at > armed_at, "the full sequence must then complete"
    assert _snap(tgt) == (TOPO_NOT_A, 0b0100, True) and tgt.freeze_in is False
    assert cmd2.command_active_r is False and cmd1.command_active_r is False
