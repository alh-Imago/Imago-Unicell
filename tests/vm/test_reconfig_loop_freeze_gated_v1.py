"""
test_reconfig_loop_freeze_gated_v1.py -- points.md #870: the reconfiguration
loop gated by a TRIGGER-MODE command cell freezing the word chain's head,
instead of arming/disarming the programming cell (#868/#869).

Design, matching how Alan described the original command core: "a start,
then a sequence of commands, then an end command that stops it, requiring a
fresh trigger for the next round."
  * The word store is ONE serialized `ram` chain (all rounds' words preloaded,
    nearest-the-head speaks first); the chain head fans out to BOTH the
    programmer-mode command cell and a trigger-mode command cell.
  * The trigger-mode cell (polarity 0 = frozen at rest) holds the chain HEAD
    frozen. A frozen cell neither captures nor offers (the VM gate mirrors the
    RTL's `want_to_offer = ... && !effective_freeze`), so the whole chain is
    stalled behind it.
  * The programming cell is left ARMED for the entire run -- no arm/disarm
    word is ever sent. It just has nothing to react to while the head is quiet.
  * One toggle word (0xF00001: nano's COMPLETE, [23:20]=15) flips the freeze
    in BOTH directions: the section's drain pulse carries it and UNFREEZES the
    head (start); the sequence's own final word, passing the trigger cell as
    it goes to the programming cell, RE-FREEZES it (stop, ready for the next
    trigger). Topology/mask words in the stream do not match and are ignored.

Why this beats #869's arm/disarm route: that needed an extra end-of-cycle
event to deliver a disarm word (nothing auto-clears `armed`, confirmed in the
RTL); here the sequence's own final word IS the end-of-cycle event, and one
word does both jobs.

REAL, HONEST SCOPE:
  * The section's payload IS the toggle word (the drain pulse doubles as the
    start word). Real fold data can't be that -- the general design triggers a
    hold+reemit source preloaded with the toggle word (#382). Not built here.
  * ROUND 2's TRIGGER IS INJECTED (`grid.inject`), standing in for a second
    drain pulse. The section carries only one item, so it cannot produce one.
  * The reconfigure TARGET is a separate nano, not a cell of the section being
    drained -- in a real fold the target belongs to the section itself.
  * VM only; command-into-freeze-gated-chain has not been run in RTL.
  * The trigger cell sees a COPY of every word; any non-final word whose
    [23:20] equalled the toggle pattern would toggle it early. Safe for a nano
    target (only its COMPLETE has id 15); other target types need their own
    pattern (3-bit ids: 7).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from vix_carrier_automaton_v1 import VixCarrierGrid  # noqa: E402
from unicell_automaton_v1 import (  # noqa: E402
    PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK, PROG_ID_COMPLETE,
)
from unicell_gate_core import TOPO_NOT_A, TOPO_AND  # noqa: E402

TOGGLE = (PROG_ID_COMPLETE << 20) | 1     # 0xF00001: round-start marker AND end marker


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _round_words(topology, mask):
    return [(PROG_ID_TOPOLOGY << 20) | topology, (PROG_ID_ROUTING_MASK << 20) | mask, TOGGLE]


def _build(rounds, head_row=9, with_ctl_fanout=True):
    """`rounds`: list of (topology, mask). Returns (grid, head_row)."""
    seq = [w for (t, m) in rounds for w in _round_words(t, m)]
    n = len(seq)
    top = head_row - (n - 1)
    cells = [
        # drain section; its payload is the toggle word
        _rec("src", 0, -1, "ram", {"init_data": TOGGLE, "load_data_valid": 1, "downstream_mask": ["e"]}),
        _rec("head", 0, 0, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
        _rec("tail", 0, 1, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e", "s"]}),
        _rec("sink", 0, 2, "ram", {"upstream_mask": ["w"], "downstream_mask": []}),
        _rec("relay_r", 1, 1, "ram", {"upstream_mask": ["n"], "downstream_mask": ["e"]}),
        _rec("t1", 1, 2, "ram", {"upstream_mask": ["w"], "downstream_mask": ["s"]}),
    ]
    # trigger path: column 2 down to the trigger-mode cell
    cells += [_rec(f"t{r}", r, 2, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"]})
              for r in range(2, head_row)]
    # serialized word store, column 1; the head (row == head_row) also fans out east to the trigger cell
    for i, w in enumerate(reversed(seq)):
        r = top + i
        down = ["s", "e"] if (r == head_row and with_ctl_fanout) else ["s"]
        cells.append(_rec(f"w{r}", r, 1, "ram", {
            "init_data": w, "load_data_valid": 1,
            "upstream_mask": [] if r == top else ["n"], "downstream_mask": down}))
    cells += [
        _rec("CTL", head_row, 2, "command", {"mode": 0, "polarity": 0, "drive_dir": 3,     # trigger mode, drives WEST -> chain head
                                             "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("CMD1", head_row + 1, 1, "command", {"mode": 1, "polarity": 0, "drive_dir": 1,  # programmer mode, stays armed
                                                  "toggle_pattern": PROG_ID_COMPLETE}),
        _rec("TGT", head_row + 2, 1, "nano", {}),
    ]
    return VixCarrierGrid(cells), head_row


def _handles(grid, head_row):
    return (grid.cells[(head_row, 2)], grid.cells[(head_row + 1, 1)],
            grid.cells[(head_row + 2, 1)], grid.cells[(head_row, 1)])


def _snap(tgt):
    return (tgt._nano.topology, tgt._nano.routing_mask, tgt._nano.start_flag)


def _waiting(grid, head_row, n_words):
    return sum(int(grid.cells[(r, 1)].ram_data_valid) for r in range(head_row - n_words + 1, head_row + 1))


def _run_until_halted(grid, head_row, cap=80):
    """Tick until a round has fully run and the head is frozen again."""
    ctl, cmd1, tgt, head = _handles(grid, head_row)
    unfroze = False
    for t in range(cap):
        grid.tick()
        unfroze |= not head.freeze_in
        if unfroze and head.freeze_in and not cmd1.command_active_r and _snap(tgt)[2]:
            return t
    return None


def test_rest_state_the_head_is_frozen_the_programmer_stays_armed_and_nothing_leaks():
    grid, hr = _build([(TOPO_NOT_A, 0b0100)])
    ctl, cmd1, tgt, head = _handles(grid, hr)
    assert head.freeze_in is True, "the trigger-mode cell holds the chain head frozen at rest"
    assert cmd1.command_armed is True, "the programming cell is left armed -- never touched"
    before = _snap(tgt)
    for _ in range(7):                    # before the drain pulse can possibly arrive
        grid.tick()
    assert _snap(tgt) == before and tgt.freeze_in is False and cmd1.command_active_r is False
    assert _waiting(grid, hr, 3) == 3, "not one word may leave the frozen chain"


def test_the_drain_pulse_releases_the_chain_and_the_final_word_halts_it_again():
    grid, hr = _build([(TOPO_NOT_A, 0b0100)])
    ctl, cmd1, tgt, head = _handles(grid, hr)
    unfroze = refroze_early = target_frozen_in_burst = False
    done = None
    for t in range(80):
        grid.tick()
        if not head.freeze_in:
            unfroze = True
        if unfroze and head.freeze_in and not _snap(tgt)[2]:
            refroze_early = True          # would mean a non-final word toggled the trigger cell
        if cmd1.command_active_r:
            target_frozen_in_burst |= tgt.freeze_in
        if unfroze and head.freeze_in and not cmd1.command_active_r and _snap(tgt)[2]:
            done = t
            break
    assert unfroze, "the section's drain pulse must release the head with no host action"
    assert refroze_early is False, "topology/mask words must NOT toggle the trigger cell"
    assert done is not None, "the round must complete"
    assert target_frozen_in_burst is True, "target frozen while the relay is active"
    assert _snap(tgt) == (TOPO_NOT_A, 0b0100, True) and tgt.freeze_in is False
    assert head.freeze_in is True, "the sequence's own final word re-froze the head"
    assert cmd1.command_armed is True, "and the programming cell was NEVER disarmed -- no arm/disarm anywhere"
    assert _waiting(grid, hr, 3) == 0, "every word consumed exactly once"


def test_two_rounds_from_one_preloaded_store_with_the_gate_holding_between_them():
    """The decisive test: no reload of the word store between rounds."""
    grid, hr = _build([(TOPO_NOT_A, 0b0100), (TOPO_AND, 0b0010)])
    ctl, cmd1, tgt, head = _handles(grid, hr)
    assert _waiting(grid, hr, 6) == 6

    assert _run_until_halted(grid, hr) is not None, "round 1 must complete on the section's own drain pulse"
    assert _snap(tgt) == (TOPO_NOT_A, 0b0100, True)
    assert _waiting(grid, hr, 6) == 3, "round-2 words are still waiting behind the frozen head"

    for _ in range(20):                   # idle: the gate must hold with the programmer cell still armed
        grid.tick()
    assert _snap(tgt) == (TOPO_NOT_A, 0b0100, True) and _waiting(grid, hr, 6) == 3
    assert cmd1.command_armed is True and head.freeze_in is True

    grid.inject(hr, 2, TOGGLE)            # STAND-IN for round 2's drain pulse (the section only carries one item)
    assert _run_until_halted(grid, hr) is not None, "round 2 must complete on the second trigger"
    assert _snap(tgt) == (TOPO_AND, 0b0010, True) and tgt.freeze_in is False
    assert _waiting(grid, hr, 6) == 0 and head.freeze_in is True


def test_without_the_fanout_to_the_trigger_cell_the_final_word_cannot_halt_the_chain():
    """Negative control: proves the halt really comes from the trigger cell
    seeing the final word, not from something else. Drop the head's fan-out
    east and the head is never re-frozen."""
    grid, hr = _build([(TOPO_NOT_A, 0b0100), (TOPO_AND, 0b0010)], with_ctl_fanout=False)
    ctl, cmd1, tgt, head = _handles(grid, hr)
    for _ in range(60):
        grid.tick()
    # released by the drain pulse, never re-frozen -> BOTH rounds run back to back, ungated
    assert _snap(tgt) == (TOPO_AND, 0b0010, True), "round 2's content arrived with no second trigger -- the gate is gone"
    assert head.freeze_in is False
    assert _waiting(grid, hr, 6) == 0
