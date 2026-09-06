"""
test_vix_carrier_automaton_v1.py — points.md #655: the VM's own real
proof of the command core, `VixCarrierCell`/`VixCarrierGrid`'s only
genuinely new mechanism (every other core type is inherited unchanged
from `SuperCell`, already proven elsewhere). Matches `command_cell_v4.v`'s
own real RTL state machine (`#628`/`#641`-`#645`) field-by-field.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3
from vix_carrier_automaton_v1 import VixCarrierGrid, VixCarrierCell
from unicell_automaton_v1 import PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK, PROG_ID_COMPLETE
from unicell_gate_core import TOPO_PASS_A

results = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")


# =============================================================================
print("=== Real class identity, #654's own actual point, not just an import-path alias ===")
# =============================================================================
cmd_rec = v3.IcmV3Record(row=0, col=0, core="command", core_config={
    "mode": 0, "polarity": 0, "drive_dir": 2, "toggle_pattern": 0xF,
}, addon_config={}, cell_id="CMD")
nano_rec = v3.IcmV3Record(row=0, col=1, core="nano", core_config={
    "topology": TOPO_PASS_A, "ready": 1, "routing_mask": 0,
}, addon_config={}, cell_id="TARGET")

grid = VixCarrierGrid([cmd_rec, nano_rec])
cmd = grid.cells[(0, 0)]
target = grid.cells[(0, 1)]
check("real, genuine subclass identity: type(cmd).__name__ == 'VixCarrierCell'",
      type(cmd).__name__ == "VixCarrierCell")
check("real, genuine subclass identity: type(target).__name__ == 'VixCarrierCell'",
      type(target).__name__ == "VixCarrierCell")
check("real, second-pass-resolved command_target reference", cmd.command_target is target)


# =============================================================================
print("\n=== TRIGGER mode: real toggle, real freeze-drive against a real nano target ===")
# =============================================================================
check("real, immediate initial propagation (polarity=0 -> rest frozen)",
      target.freeze_in is True)

grid.inject(0, 1, 5)
for _ in range(3):
    grid.tick()
check("real stall while frozen: a real arrival is genuinely not consumed",
      target._nano.a_arrived is False)
grid._pending.pop((0, 1), None)   # withdraw the stalled injection before continuing

matching_word = 0xF << 20
grid.inject(0, 0, matching_word)
grid.run_to_quiescence()
check("real toggle: a matching word flips freeze off", target.freeze_in is False)

grid.inject(0, 1, 5)
grid.run_to_quiescence()
check("real, functional confirmation: the target genuinely accepts arrivals once unfrozen",
      target._nano.a_arrived is True)

grid.inject(0, 0, matching_word)
grid.run_to_quiescence()
check("real toggle back: a second matching word flips freeze back on",
      target.freeze_in is True)


# =============================================================================
print("\n=== PROGRAMMER mode: real, end-to-end proof -- programming a fresh, ===")
print("=== never-configured nano target from scratch, matching #644's own real RTL proof ===")
# =============================================================================
cmd_rec2 = v3.IcmV3Record(row=0, col=0, core="command", core_config={
    "mode": 1, "polarity": 0, "drive_dir": 2, "toggle_pattern": PROG_ID_COMPLETE,
}, addon_config={}, cell_id="CMD2")
fresh_rec = v3.IcmV3Record(row=0, col=1, core="nano", core_config={}, addon_config={}, cell_id="FRESH")

grid2 = VixCarrierGrid([cmd_rec2, fresh_rec])
fresh = grid2.cells[(0, 1)]
check("real, fresh target starts genuinely unconfigured", fresh._nano.start_flag is False)

grid2.inject(0, 0, (PROG_ID_TOPOLOGY << 20) | TOPO_PASS_A)
grid2.run_to_quiescence()
check("real freeze held during relay", fresh.freeze_in is True)

grid2.inject(0, 0, (PROG_ID_ROUTING_MASK << 20) | 0b0100)
grid2.run_to_quiescence()

grid2.inject(0, 0, (PROG_ID_COMPLETE << 20) | 1)
grid2.run_to_quiescence()
check("real freeze released only on the real COMPLETE word", fresh.freeze_in is False)
check("real target now armed", fresh._nano.start_flag is True)
check("real topology correctly relayed", fresh._nano.topology == TOPO_PASS_A)
check("real routing_mask correctly relayed", fresh._nano.routing_mask == 0b0100)

grid2.inject(0, 1, 0xCAFE0000)
grid2.run_to_quiescence()
grid2.inject(0, 1, 0xFFFFFFFF)
grid2.run_to_quiescence()
check("real, end-to-end functional confirmation: the freshly-programmed target genuinely works",
      fresh._nano.out_buffer == 0xCAFE0000)


# =============================================================================
print("\n=== Real, existing 8 core types genuinely unchanged, inherited for free ===")
# =============================================================================
adder_rec = v3.IcmV3Record(row=5, col=5, core="adder", core_config={
    "downstream_mask": 0b0100, "upstream_mask": 0b0011,
}, addon_config={}, cell_id="ADD")
grid3 = VixCarrierGrid([adder_rec])
adder = grid3.cells[(5, 5)]
grid3.inject(5, 5, 3)
grid3.run_to_quiescence()
grid3.inject(5, 5, 4)
grid3.run_to_quiescence()
check("real, unchanged adder behavior, inherited from SuperCell", adder.adder_out_buffer == 7)


# =============================================================================
print("\n=== Real, shell-level freeze gate (#656): 'if it works on one it should work on all' ===")
# =============================================================================
cmd_rec3 = v3.IcmV3Record(row=0, col=0, core="command", core_config={
    "mode": 0, "polarity": 0, "drive_dir": 2, "toggle_pattern": 0xF,
}, addon_config={}, cell_id="CMD3")
# The SAME real freeze-drive mechanism, now targeting a non-nano core
# (adder) -- the exact gap #655 left open, closed here at the one real
# shared dispatch point (SuperCell.deliver()), not per-core.
adder_rec2 = v3.IcmV3Record(row=0, col=1, core="adder", core_config={
    "downstream_mask": 0b0100, "upstream_mask": 0b0011,
}, addon_config={}, cell_id="TARGET_ADD")

grid4 = VixCarrierGrid([cmd_rec3, adder_rec2])
cmd3 = grid4.cells[(0, 0)]
target_adder = grid4.cells[(0, 1)]
check("real, immediate initial propagation reaches a non-nano target too",
      target_adder.freeze_in is True)

grid4.inject(0, 1, 3)
for _ in range(3):
    grid4.tick()
check("real stall: a non-nano target genuinely rejects a real arrival while frozen",
      target_adder.adder_a_arrived is False)
grid4._pending.pop((0, 1), None)   # withdraw the stalled injection before continuing

grid4.inject(0, 0, 0xF << 20)
grid4.run_to_quiescence()
check("real toggle off reaches the non-nano target", target_adder.freeze_in is False)

grid4.inject(0, 1, 3)
grid4.run_to_quiescence()
grid4.inject(0, 1, 4)
grid4.run_to_quiescence()
check("real, functional confirmation: the non-nano target genuinely works once unfrozen",
      target_adder.adder_out_buffer == 7)


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
