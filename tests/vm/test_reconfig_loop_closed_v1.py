"""
test_reconfig_loop_closed_v1.py -- points.md #871: the reconfiguration loop
CLOSED in the VM -- two rounds, no injected trigger, no host action of any
kind after the grid is built. Builds on #870's freeze-gated word chain by
also gating item ADMISSION, so round 2 is triggered by a genuine drain pulse.

Why admission needs its own gate (found by thinking it through before
building): with item 2 simply waiting behind item 1 in the source, it would
enter the section right behind item 1 and both drain pulses would arrive
almost together -- long before round 1 had reconfigured anything. The same
trigger-mode trick gates it: a second trigger-mode command cell (CTL2, polarity
1 = unfrozen at rest) sits beside the source head S1; S1 fans a copy of each
item out to CTL2, so an item's own copy freezes S1 immediately (exactly one item
leaves), and the final word of a reconfigure sequence -- a copy of it is routed
to CTL2 -- unfreezes it again. The two events strictly alternate, so one
toggle word does both jobs on both controllers:

    CTL  (word-chain head, polarity 0):  drain pulse -> RUN,   final word -> HALT
    CTL2 (source head,     polarity 1):  item copy   -> HOLD,  final word -> RELEASE

Loop: item 1 leaves and freezes the source -> crosses the section -> drain
pulse runs round 1 -> its final word halts the chain AND releases item 2 ->
item 2 crosses -> its drain pulse runs round 2. Item 2 provably cannot enter
until round 1's reconfigure is complete.

Bonus over #869: nothing is ever armed or disarmed, so the one-time setup
disarm #869 needed is gone -- polarity in the config does all the initial work.

REAL, HONEST SCOPE -- what this is and is not:
  * Item payload == the toggle word (0xF00001). The item's copy toggles CTL2
    and the drain pulse (the item itself) toggles CTL, so both controllers
    react to the DATA. Real fold data cannot be a marker; the general design
    needs hold+reemit sources (#382) to generate markers from unmarked data.
    Not built.
  * The reconfigure TARGET is a separate nano, NOT a cell of the section being
    drained. So "item 2 is processed by the reconfigured section" is proven
    only as a SCHEDULING property (it cannot be admitted before the
    reconfigure completes), not as a data-dependent one. Making the target a
    cell of the section is the actual fold and is still to do.
  * VM only. Not run in RTL. Layout is generous and arbitrary (long relay
    paths so each controller has a free face); cell count is not optimized.
  * Two items only; nothing here proves N rounds, though each round repeats
    the same alternating pair of events.
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

TOGGLE = (PROG_ID_COMPLETE << 20) | 1
ROUND1 = (TOPO_NOT_A, 0b0100)
ROUND2 = (TOPO_AND, 0b0010)


def _rec(cid, row, col, core, cfg=None):
    return v3.IcmV3Record(cell_id=cid, row=row, col=col, core=core,
                          core_config=cfg or {}, addon_config={})


def _words(t, m):
    return [(PROG_ID_TOPOLOGY << 20) | t, (PROG_ID_ROUTING_MASK << 20) | m, TOGGLE]


def _build(rounds=(ROUND1, ROUND2), gate_admission=True):
    seq = [w for (t, m) in rounds for w in _words(t, m)]
    n = len(seq)
    top = -(n - 1)
    cells = []
    # word store, column 0; head at row 0 fans out W (programmer), E (CTL), S (copy path to CTL2)
    for i, w in enumerate(reversed(seq)):
        r = top + i
        cells.append(_rec(f"w{r}", r, 0, "ram", {
            "init_data": w, "load_data_valid": 1,
            "upstream_mask": [] if r == top else ["n"],
            "downstream_mask": ["w", "e", "s"] if r == 0 else ["s"]}))
    cells += [
        _rec("CMD1", 0, -1, "command", {"mode": 1, "polarity": 0, "drive_dir": 3,
                                        "toggle_pattern": PROG_ID_COMPLETE}),   # programmer, stays ARMED
        _rec("TGT", 0, -2, "nano", {}),
        _rec("CTL", 0, 1, "command", {"mode": 0, "polarity": 0, "drive_dir": 3,
                                      "toggle_pattern": PROG_ID_COMPLETE}),      # frozen at rest -> holds word head
        # final-word copy path to CTL2
        _rec("c1", 1, 0, "ram", {"upstream_mask": ["n"], "downstream_mask": ["e"]}),
        _rec("c2", 1, 1, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
        _rec("c3", 1, 2, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
        # admission gate
        _rec("CTL2", 1, 3, "command", {"mode": 0, "polarity": 1, "drive_dir": 1,
                                       "toggle_pattern": PROG_ID_COMPLETE}),     # unfrozen at rest -> item 1 goes
        _rec("S1", 2, 3, "ram", {"init_data": TOGGLE, "load_data_valid": 1, "upstream_mask": ["e"],
                                 "downstream_mask": ["s", "n"] if gate_admission else ["s"]}),
        _rec("S2", 2, 4, "ram", {"init_data": TOGGLE, "load_data_valid": 1,
                                 "upstream_mask": [], "downstream_mask": ["w"]}),
        # the drain section, flowing south from S1
        _rec("head", 3, 3, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"]}),
        _rec("tail", 4, 3, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s", "e"]}),
        _rec("O1", 5, 3, "ram", {"upstream_mask": ["n"], "downstream_mask": ["s"]}),
        _rec("O2", 6, 3, "ram", {"upstream_mask": ["n"], "downstream_mask": []}),
        # drain pulse path: tail tap east -> up column 5 -> west along row 0 into CTL from its east
        _rec("p1", 4, 4, "ram", {"upstream_mask": ["w"], "downstream_mask": ["e"]}),
        _rec("p2", 4, 5, "ram", {"upstream_mask": ["w"], "downstream_mask": ["n"]}),
    ]
    cells += [_rec(f"p{i}", r, 5, "ram", {"upstream_mask": ["s"], "downstream_mask": ["n"]})
              for i, r in enumerate((3, 2, 1), start=3)]
    cells += [_rec("p6", 0, 5, "ram", {"upstream_mask": ["s"], "downstream_mask": ["w"]})]
    cells += [_rec(f"p{i}", 0, c, "ram", {"upstream_mask": ["e"], "downstream_mask": ["w"]})
              for i, c in enumerate((4, 3, 2), start=7)]
    return VixCarrierGrid(cells)


class _H:
    """Named handles onto the interesting cells."""
    def __init__(self, g):
        self.g = g
        self.head = g.cells[(0, 0)]
        self.cmd1 = g.cells[(0, -1)]
        self.tgt = g.cells[(0, -2)]
        self.S1, self.S2 = g.cells[(2, 3)], g.cells[(2, 4)]
        self.O1, self.O2 = g.cells[(5, 3)], g.cells[(6, 3)]

    def snap(self):
        return (self.tgt._nano.topology, self.tgt._nano.routing_mask, self.tgt._nano.start_flag)

    def settled(self, want):
        return self.snap() == (want[0], want[1], True) and not self.tgt.freeze_in \
            and not self.cmd1.command_active_r


def _run(grid, cap=160, quiet=0):
    """Tick and log the key events. Stops `quiet` ticks after round 2 completes."""
    h = _H(grid)
    ev = {"pulse1": None, "pulse2": None, "item2_admitted": None,
          "round1_done": None, "round2_done": None,
          "s2_valid_before_pulse1": True, "disturbed_before_pulse1": False,
          "out_items_before_pulse1": None}
    prev_frozen = h.head.freeze_in
    initial = h.snap()
    end = None
    for t in range(cap):
        grid.tick()
        frozen = h.head.freeze_in
        if prev_frozen and not frozen:
            if ev["pulse1"] is None:
                ev["pulse1"] = t
                ev["out_items_before_pulse1"] = int(h.O1.ram_data_valid) + int(h.O2.ram_data_valid)
            elif ev["pulse2"] is None:
                ev["pulse2"] = t
        prev_frozen = frozen
        if ev["pulse1"] is None:
            ev["s2_valid_before_pulse1"] &= bool(h.S2.ram_data_valid)
            ev["disturbed_before_pulse1"] |= (h.snap() != initial) or h.tgt.freeze_in
        if ev["item2_admitted"] is None and not h.S2.ram_data_valid:
            ev["item2_admitted"] = t
        if ev["round1_done"] is None and h.settled(ROUND1):
            ev["round1_done"] = t
        if ev["round2_done"] is None and h.settled(ROUND2):
            ev["round2_done"] = t
            end = t + quiet
        if end is not None and t >= end:
            break
    return h, ev


def test_item_two_is_held_back_while_item_one_crosses_the_section():
    """The admission gate: exactly one item leaves the source, and item 2 waits
    behind the frozen source head until round 1 has run."""
    grid = _build()
    h, ev = _run(grid)
    assert ev["pulse1"] is not None, "item 1's drain pulse must arrive"
    assert ev["s2_valid_before_pulse1"] is True, "item 2 must still be parked behind the source head"
    assert ev["out_items_before_pulse1"] == 1, "exactly ONE item may have crossed the section by the first pulse"
    assert ev["disturbed_before_pulse1"] is False, "the target must be untouched before the first pulse"


def test_item_two_is_admitted_only_after_round_one_has_reconfigured_the_target():
    """The property the whole loop exists for: the next item cannot enter until
    the reconfigure that precedes it has COMPLETED."""
    grid = _build()
    h, ev = _run(grid)
    assert ev["round1_done"] is not None and ev["item2_admitted"] is not None
    assert ev["round1_done"] < ev["item2_admitted"], \
        "item 2 must be admitted strictly AFTER round 1's reconfigure completed"


def test_round_two_is_triggered_by_a_genuine_drain_pulse_with_no_injection_or_host_action():
    """No grid.inject, no program_word, no disarm -- the test only builds the grid and ticks."""
    grid = _build()
    h, ev = _run(grid)
    assert ev["pulse2"] is not None and ev["item2_admitted"] is not None
    assert ev["pulse2"] > ev["item2_admitted"], "round 2's trigger must come from item 2 crossing the section"
    assert ev["round2_done"] is not None, "round 2 must complete"
    assert h.snap() == (ROUND2[0], ROUND2[1], True) and h.tgt.freeze_in is False
    assert h.O1.ram_data_valid and h.O2.ram_data_valid, "both items crossed the section exactly once each"
    assert h.cmd1.command_armed is True, "the programmer cell was never touched"


def test_the_loop_halts_cleanly_and_stays_quiet_afterwards():
    grid = _build()
    h, ev = _run(grid, quiet=40)
    assert ev["round2_done"] is not None
    assert h.snap() == (ROUND2[0], ROUND2[1], True)
    assert h.head.freeze_in is True, "the word chain ends halted, ready for a next trigger"
    assert h.tgt.freeze_in is False and h.cmd1.command_active_r is False
    assert not h.S1.ram_data_valid and not h.S2.ram_data_valid, "nothing left to admit, nothing runaway"


def test_without_the_admission_gate_item_two_races_ahead_of_the_reconfigure():
    """Negative control: drop S1's copy to CTL2 and nothing freezes the source
    after item 1, so item 2 follows straight behind it. Observed: admitted at
    tick 2 (vs tick 21 gated) -- before even the FIRST drain pulse. The two
    pulses then land nearly together, CTL toggles straight back, round 1 never
    completes, and the target is left half-programmed and never started
    (topology written, no COMPLETE). This is the hazard the gate exists for,
    asserted as an actual failure rather than a timing inequality."""
    grid = _build(gate_admission=False)
    h, ev = _run(grid, cap=160)
    assert ev["item2_admitted"] is not None and ev["pulse1"] is not None
    assert ev["item2_admitted"] < ev["pulse1"], \
        "ungated: item 2 is already in the section before the FIRST drain pulse"
    assert ev["round1_done"] is None and ev["round2_done"] is None, "ungated: neither round completes"
    assert h.snap() != (ROUND2[0], ROUND2[1], True), "ungated: the target does not end correctly configured"
    assert h.snap()[2] is False, "ungated: the target is left half-programmed and never started"
