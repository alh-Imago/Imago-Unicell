"""
test_vix_carrier_mesh_v1.py — points.md #658: the real "carrier
speaking to carrier" case Alan directly asked about -- does the
mapping from one VIX Carrier's own command core all the way through to
a NEIGHBORING carrier's currently-selected core actually work, or does
it stop somewhere along the way?

Confirmed real gaps BEFORE fixing, not assumed: (1) the RTL array
generator (`project_assemble_v1.py`) ties every carrier's own real
`program_in`/`prog_arrived_in` to an anti-pruning constant and leaves
`program_out_n/s/e/w` completely unconnected to any neighbor -- real
carrier-to-carrier wiring doesn't exist there yet, a real, separate,
RTL-side gap. (2) `#657`'s own test wired one command cell to one slot
by hand -- no general mechanism existed for a command core embedded
INSIDE a `VixCarrierSlot` to reach a NEIGHBORING slot dynamically,
especially since core_select can itself change at runtime (the very
mechanism `#657` built). This file proves the VM-side fix.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from vix_carrier_automaton_v1 import build_vix_slot_grid, _INDEX_FROM_SEL
from unicell_automaton_v1 import PROG_ID_TOPOLOGY, PROG_ID_ROUTING_MASK, PROG_ID_COMPLETE
from unicell_gate_core import TOPO_PASS_A

results = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")


def word(prog_id, data):
    return (prog_id << 20) | (data & 0xFFFFF)


# =============================================================================
print("=== Real carrier-to-carrier: slot A's own command core targets neighbor slot B ===")
# =============================================================================
grid = build_vix_slot_grid({(0, 0): "command", (0, 1): "adder"})
slot_a = grid.cells[(0, 0)]
slot_b = grid.cells[(0, 1)]

cmd = slot_a.active
cmd.command_mode = True
cmd.command_drive_dir = 2   # E
cmd.command_toggle_pattern = PROG_ID_COMPLETE
cmd.command_armed = True

check("real, static neighbor wiring resolved correctly", slot_a.neighbors[2] is slot_b)
check("real, dynamic target resolution reaches the actual neighbor SLOT, not a fixed cell",
      cmd._resolve_command_target() is slot_b)
check("slot B deliberately starts on the wrong core", slot_b.core_select == "adder")

grid.inject(0, 0, _INDEX_FROM_SEL["nano"])
grid.run_to_quiescence()
check("real, insisted-upon first word reaches THROUGH the mesh and redirects the real neighbor",
      slot_b.core_select == "nano")

grid.inject(0, 0, word(PROG_ID_TOPOLOGY, TOPO_PASS_A))
grid.run_to_quiescence()
grid.inject(0, 0, word(PROG_ID_ROUTING_MASK, 0b0100))
grid.run_to_quiescence()
check("real freeze held across the mesh throughout the whole relay", slot_b.freeze_in is True)

grid.inject(0, 0, word(PROG_ID_COMPLETE, 1))
grid.run_to_quiescence()
check("real freeze released across the mesh only on the real COMPLETE word",
      slot_b.freeze_in is False)
check("real target now armed", slot_b.active._nano.start_flag is True)
check("real fields correctly relayed across the mesh to the now-correct core",
      slot_b.active._nano.topology == TOPO_PASS_A and slot_b.active._nano.routing_mask == 0b0100)

grid.inject(0, 1, 0xCAFE0000)
grid.run_to_quiescence()
grid.inject(0, 1, 0xFFFFFFFF)
grid.run_to_quiescence()
check("real, end-to-end carrier-to-carrier functional confirmation",
      slot_b.active._nano.out_buffer == 0xCAFE0000)


# =============================================================================
print("\n=== Real, dynamic re-resolution: the target neighbor's own active core can change again later ===")
# =============================================================================
# Points.md #658: a real, necessary property this design must have --
# since a slot's OWN core_select can change again LATER (e.g. a
# DIFFERENT command cell elsewhere reprogramming it), the SAME command
# core's own target resolution must reflect that fresh state on its
# NEXT use, not a value cached from the earlier programming session.
slot_b.boot("ram")
check("real, dynamic re-resolution reflects the neighbor's CURRENT state, not a cached one",
      cmd._resolve_command_target() is slot_b and slot_b.core_select == "ram")


# =============================================================================
print("\n=== Real, carrier-to-carrier programming a NON-NANO target (#660) ===")
# =============================================================================
# Points.md #660: the exact scenario #658 explicitly left as a real,
# stated, standing gap -- "field-tweak relaying still only works
# against a real nano target." Live PROG_ID reprogramming has since
# been extended to all 9 core types; this proves the full mesh path
# genuinely reaches a non-nano target end to end, not just that the
# first (core-select) word can redirect to one.
grid3 = build_vix_slot_grid({(0, 0): "command", (0, 1): "nano"})
slot_c, slot_d = grid3.cells[(0, 0)], grid3.cells[(0, 1)]
cmd3 = slot_c.active
cmd3.command_mode = True
cmd3.command_drive_dir = 2
cmd3.command_toggle_pattern = 7   # adder's own real COMPLETE id (3-bit table)
cmd3.command_armed = True

grid3.inject(0, 0, _INDEX_FROM_SEL["adder"])
grid3.run_to_quiescence()
check("real first word redirects the neighbor to a non-nano core",
      slot_d.core_select == "adder")

grid3.inject(0, 0, word(0, 0b000100))   # downstream_mask = E
grid3.run_to_quiescence()
grid3.inject(0, 0, word(1, 0b000011))   # upstream_mask = N|S
grid3.run_to_quiescence()
grid3.inject(0, 0, word(7, 1))          # COMPLETE
grid3.run_to_quiescence()
check("real fields correctly relayed to the non-nano target across the mesh",
      slot_d.active.adder_downstream_mask == 0b000100 and slot_d.active.adder_upstream_mask == 0b000011)
check("real freeze released after the non-nano target's own COMPLETE word",
      slot_d.freeze_in is False)

grid3.inject(0, 1, 3)
grid3.run_to_quiescence()
grid3.inject(0, 1, 4)
grid3.run_to_quiescence()
check("real, end-to-end functional confirmation -- a non-nano target, programmed across the mesh, genuinely works",
      slot_d.active.adder_out_buffer == 7)


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
