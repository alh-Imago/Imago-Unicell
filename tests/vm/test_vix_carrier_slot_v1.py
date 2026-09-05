"""
test_vix_carrier_slot_v1.py — points.md #657: `VixCarrierSlot`, the
real, genuine VM model of `#647`'s own real VIX Carrier -- ONE grid
position holding all 9 real core types simultaneously, mutually
exclusive, `core_select` switchable at runtime.

Directly answers Alan's own real question and follow-up instruction:
live programming reaches only whichever core is currently selected (no
core-selection information lives in an ordinary PROG_ID word) -- so
this slot INSISTS the first real word of any fresh programming session
be a raw core-select value, enforced entirely at the receiving end.
Command mode itself stays an unaware, faithful relay throughout.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3
from vix_carrier_automaton_v1 import (
    VixCarrierCell, VixCarrierSlot, PROG_ID_COMPLETE, _INDEX_FROM_SEL,
)
from unicell_automaton_v1 import PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK
from unicell_gate_core import TOPO_PASS_A
from unicell_super_automaton_v1 import SuperGrid

results = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")


def word(prog_id, data):
    return (prog_id << 20) | (data & 0xFFFFF)


def make_command_and_slot(initial_core_select):
    cmd_rec = v3.IcmV3Record(row=0, col=0, core="command", core_config={
        "mode": 1, "polarity": 0, "drive_dir": 2, "toggle_pattern": PROG_ID_COMPLETE,
    }, addon_config={}, cell_id="CMD")
    cmd = VixCarrierCell.from_record(cmd_rec)
    slot = VixCarrierSlot(row=0, col=1, core_select=initial_core_select)
    grid = SuperGrid([])
    grid.cells = {(0, 0): cmd, (0, 1): slot}
    cmd.command_target = slot
    cmd._propagate_freeze(cmd.command_active_r)
    return cmd, slot, grid


# =============================================================================
print("=== Basic construction: all 9 real cores genuinely co-resident ===")
# =============================================================================
slot = VixCarrierSlot(row=0, col=0, core_select="nano")
check("slot starts on the real, requested core", slot.core_select == "nano")
check("slot.core reflects the currently-active core", slot.core == "nano")
check("all 9 real core types genuinely co-resident, not just the selected one",
      set(slot._cores.keys()) == {"nano", "adder", "ram", "comparator", "branch",
                                   "accumulator", "latch", "sequencer", "command"})

slot.boot("adder")
check("real boot() switches core_select", slot.core_select == "adder")
check("real boot() resets the newly-selected core to a clean baseline",
      slot.active.adder_a_arrived is False)


# =============================================================================
print("\n=== The exact scenario raised: a slot starting on the WRONG core ===")
# =============================================================================
cmd, slot, grid = make_command_and_slot(initial_core_select="adder")
check("slot deliberately starts on the wrong core", slot.core_select == "adder")

grid.inject(0, 0, _INDEX_FROM_SEL["nano"])
grid.run_to_quiescence()
check("real, insisted-upon first word correctly redirects to the intended core",
      slot.core_select == "nano")

grid.inject(0, 0, word(PROG_ID_TOPOLOGY, TOPO_PASS_A))
grid.run_to_quiescence()
grid.inject(0, 0, word(PROG_ID_ROUTING_MASK, 0b0100))
grid.run_to_quiescence()
check("real freeze held throughout the whole relay", slot.freeze_in is True)

grid.inject(0, 0, word(PROG_ID_COMPLETE, 1))
grid.run_to_quiescence()
check("real freeze released only on the real COMPLETE word", slot.freeze_in is False)
check("real program_in correctly cleared after the session ends -- the actual bug found",
      slot.active.program_in is False)
check("real target now armed", slot.active._nano.start_flag is True)
check("real fields correctly relayed to the NOW-correct core",
      slot.active._nano.topology == TOPO_PASS_A and slot.active._nano.routing_mask == 0b0100)

grid.inject(0, 1, 0xCAFE0000)
grid.run_to_quiescence()
grid.inject(0, 1, 0xFFFFFFFF)
grid.run_to_quiescence()
check("real, end-to-end functional confirmation despite starting on the wrong core",
      slot.active._nano.out_buffer == 0xCAFE0000)


# =============================================================================
print("\n=== Real, honest error handling -- an invalid first word is rejected, not silently misused ===")
# =============================================================================
cmd2, slot2, grid2 = make_command_and_slot(initial_core_select="nano")
try:
    slot2.begin_programming()
    slot2.relay_word(31)   # not a real, valid core-select index
    check("an invalid core-select index is rejected", False)
except ValueError as e:
    check("an invalid core-select index is rejected with a clear error",
          "core-select" in str(e))

try:
    slot2 = VixCarrierSlot(row=0, col=1)
    slot2.relay_word(word(PROG_ID_TOPOLOGY, 0))   # no begin_programming() first
    check("relay_word() without begin_programming() is rejected", False)
except ValueError as e:
    check("relay_word() without begin_programming() first is rejected with a clear error",
          "begin_programming" in str(e))


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
