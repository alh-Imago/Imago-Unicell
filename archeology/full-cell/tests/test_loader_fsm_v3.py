"""
test_loader_fsm_v3.py — tests for the VM model of loader_fsm_v3.v, the
existing proven boot-time icmP loader.

Cross-checked directly against tb_bram_loader_v3.v's exact scenario: 3
heterogeneous cells (XOR/AND/OR), loaded through the real top-level
transport, completion-gated on the real emit_count pulse.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unicell_array_v3 import UniCellArrayV3
from loader_fsm_v3 import (
    LoaderFSMV3, LoaderConfigEntry, TargetLatchTransport,
    OP_SET_TARGET, OP_LOAD_AT, OP_LOAD_DONE, OP_METH_SET_LANE,
    unpack_topology_word,
)
from unicell_v3 import TOPO_XOR, TOPO_AND, TOPO_OR

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    results.append(("PASS" if ok else "FAIL", name))
    if ok:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name}  got={got!r}  expected={expected!r}")


# =============================================================================
print("=== unpack_topology_word: field-for-field against unicell64_v3.v lines 973-993 ===")
# =============================================================================
# 0x0000_00BC: topology=0x0BC (XOR), nothing else set.
u = unpack_topology_word(0x0000_00BC)
check_eq("topology unpacked", u["topology"], TOPO_XOR)
check("start_flag False when bit11 clear", not u["start_flag"])

# armed XOR: topology=0x0BC, start_flag(bit11)=1 -> 0x8BC
u2 = unpack_topology_word(0x0000_08BC)
check_eq("topology unpacked (armed word)", u2["topology"], TOPO_XOR)
check("start_flag True when bit11 set", u2["start_flag"])

# loop_back (bit22) + invert_out (bit16)
u3 = unpack_topology_word((1 << 22) | (1 << 16))
check("loop_back unpacked", u3["loop_back"])
check("invert_out unpacked", u3["invert_out"])
check("unrelated fields stay False/0", not u3["latch_in"] and u3["dtype"] == 0)


# =============================================================================
print("\n=== TargetLatchTransport: matches the exact whitelist (loader_fsm_v3.v lines 66-85) ===")
# =============================================================================
t = TargetLatchTransport()
t.step(cmd_bus=OP_SET_TARGET, cmd_data=0x0042, cpu_valid=True)
check_eq("load_target latched by SET_TARGET", t.load_target, 0x0042)
check_eq("CMD_LOAD_AT reads the HELD target, not its own cmd_data",
         t.step(cmd_bus=OP_LOAD_AT, cmd_data=0x0000_00BC, cpu_valid=True), 0x0042)
check_eq("METH_SET_LANE ALSO reads the held target (the exact bug this session's "
         "BRAM loader work found and fixed -- opcodes 30-33 must be in this whitelist)",
         t.step(cmd_bus=OP_METH_SET_LANE, cmd_data=0x0, cpu_valid=True), 0x0042)
check_eq("an UNLISTED opcode falls through to cmd_data[15:0] directly",
         t.step(cmd_bus=99, cmd_data=0x1234, cpu_valid=True), 0x1234)
check_eq("opcode 1 (DATA_WRITE) reads the UPPER 16 bits of cmd_data (addr, not target)",
         t.step(cmd_bus=1, cmd_data=(0x5678 << 16) | 0x0001, cpu_valid=True), 0x5678)


# =============================================================================
print("\n=== LoaderFSMV3: exact replay of tb_bram_loader_v3.v's 3-cell scenario ===")
# =============================================================================
arr = UniCellArrayV3(num_cells=4)  # matches tb_bram_loader_v3.v's NUM_CELLS=4

# Cell 0: target=0, topology=XOR(0x0BC). Cell 1: target=1, topology=AND(0x007).
# Cell 2: target=2, topology=OR(0x024). Cycle-2 pad = METH_SET_LANE(0), harmless.
config = [
    LoaderConfigEntry(target=0, c1_bus=OP_LOAD_AT, c1_data=0x0000_00BC,
                       c2_bus=OP_METH_SET_LANE, c2_data=0x0),
    LoaderConfigEntry(target=1, c1_bus=OP_LOAD_AT, c1_data=0x0000_0007,
                       c2_bus=OP_METH_SET_LANE, c2_data=0x0),
    LoaderConfigEntry(target=2, c1_bus=OP_LOAD_AT, c1_data=0x0000_0024,
                       c2_bus=OP_METH_SET_LANE, c2_data=0x0),
]

loader = LoaderFSMV3(arr, config)
loader.start()
loader.run_to_completion()

check("loader reached S_DONE", loader.done)
check_eq("all 3 cells confirmed", loader.cells_confirmed, 3)
check_eq("cell0 topology == XOR", arr.get_cell(0).topology, TOPO_XOR)
check_eq("cell1 topology == AND", arr.get_cell(1).topology, TOPO_AND)
check_eq("cell2 topology == OR", arr.get_cell(2).topology, TOPO_OR)
check("cell3 (never targeted) untouched -- default PASS_A",
      arr.get_cell(3).topology == 0)  # TOPO_PASS_A == 0
check("cell0 load_confirmed set", arr.get_cell(0).load_confirmed)
check("cell1 load_confirmed set", arr.get_cell(1).load_confirmed)
check("cell2 load_confirmed set", arr.get_cell(2).load_confirmed)
check_eq("emit_count == 3 (one confirm per cell, no extras) -- matches "
         "tb_bram_loader_v3.v's own check exactly", loader._emit_count, 3)


# =============================================================================
print("\n=== LoaderFSMV3: cells are heterogeneously configured, not broadcast ===")
# =============================================================================
# The whole point of targeted loading -- confirm cell1/cell2 don't ALSO
# end up XOR (which broadcast CMD_RECONFIGURE would have produced).
check("cell1 is NOT XOR (would indicate accidental broadcast)",
      arr.get_cell(1).topology != TOPO_XOR)
check("cell2 is NOT AND (would indicate accidental broadcast)",
      arr.get_cell(2).topology != TOPO_AND)


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
