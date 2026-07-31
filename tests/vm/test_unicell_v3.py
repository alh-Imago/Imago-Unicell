"""
test_unicell_v3.py — Phase 1 tests for the UniCell v3.1 VM rebuild.

Ground truth: fpga/verilog/unicell64_v3.v. Every test here traces to a
specific verified line/behavior in that file (cited in comments), not to
memory of what the cell "should" do — this is the whole point of rebuilding
the VM against the actual current RTL rather than the retired protocol the
old unicell.py modeled.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unicell_v3 import (
    UniCellV3, compute_gate, AuthError,
    TOPO_PASS_A, TOPO_PASS_B, TOPO_NOT_A, TOPO_NOT_B, TOPO_NOR, TOPO_AND,
    TOPO_OR, TOPO_NAND, TOPO_XOR, TOPO_XNOR, TOPO_ZERO, TOPO_ONE,
)

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
print("=== Topology decode table (unicell64_v3.v lines 740-753) ===")
# =============================================================================
# The RTL's own verification comment (line 736) cites these exact operands.
A, B = 0xDEADBEEF, 0xCAFEBABE
M = 0xFFFFFFFF

check_eq("NOR(A,B)",   compute_gate(TOPO_NOR,   A, B), (~(A | B)) & M)
check_eq("AND(A,B)",   compute_gate(TOPO_AND,   A, B), A & B)
check_eq("OR(A,B)",    compute_gate(TOPO_OR,    A, B), A | B)
check_eq("NAND(A,B)",  compute_gate(TOPO_NAND,  A, B), (~(A & B)) & M)
check_eq("XOR(A,B)",   compute_gate(TOPO_XOR,   A, B), A ^ B)
check_eq("XNOR(A,B)",  compute_gate(TOPO_XNOR,  A, B), (~(A ^ B)) & M)
check_eq("NOT(A)",     compute_gate(TOPO_NOT_A, A, B), (~A) & M)
check_eq("NOT(B)",     compute_gate(TOPO_NOT_B, A, B), (~B) & M)
check_eq("PASS(A)",    compute_gate(TOPO_PASS_A,A, B), A)
check_eq("PASS(B)",    compute_gate(TOPO_PASS_B,A, B), B)
check_eq("ZERO",       compute_gate(TOPO_ZERO,  A, B), 0)
check_eq("ONE",        compute_gate(TOPO_ONE,   A, B), M)
check_eq("unknown topology code falls back to PASS(A) (RTL default: arm)",
         compute_gate(0x3FF, A, B), A)


# =============================================================================
print("\n=== Boot state / addressing defaults (RTL lines 474-478) ===")
# =============================================================================
c = UniCellV3(CELL_ID=5)
check_eq("input_address defaults to CELL_ID", c.input_address, 5)
check_eq("output_address defaults to CELL_ID+1", c.output_address, 6)
check("starts in BOOT state (physical_mode=True)", c.physical_mode)
check("auth_boot True when auth_mask=0", c.auth_boot)
check("auth_ok True in boot-default state (any token)", c.auth_ok(auth_token=0x3FF))


# =============================================================================
print("\n=== CMD_BOOT_COMMIT (RTL lines 1116-1126) ===")
# =============================================================================
c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0x0100, auth_mask_bits=0xA5)
check_eq("input_address set by BOOT_COMMIT", c.input_address, 0x0100)
check_eq("auth_mask set by BOOT_COMMIT (low 8 bits)", c.auth_mask, 0xA5)
check("physical_mode cleared -> RUN state", not c.physical_mode)

# BOOT_COMMIT is a no-op once in RUN state (matches `if (physical_mode)`)
c.boot_commit(logical_addr=0x0200, auth_mask_bits=0x00)
check_eq("BOOT_COMMIT ignored once in RUN state", c.input_address, 0x0100)
check_eq("auth_mask unchanged once in RUN state", c.auth_mask, 0xA5)


# =============================================================================
print("\n=== Auth gating once a real mask is stored ===")
# =============================================================================
c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0, auth_mask_bits=0xA5)
check("auth_ok with matching token", c.auth_ok(auth_token=0xA5))
check("auth_ok False with wrong token", not c.auth_ok(auth_token=0x01))
try:
    c.freeze(auth_token=0x01)
    check("CMD_FREEZE with wrong auth raises AuthError", False)
except AuthError:
    check("CMD_FREEZE with wrong auth raises AuthError", True)
c.freeze(auth_token=0xA5)
check("CMD_FREEZE with correct auth succeeds", c.frozen)


# =============================================================================
print("\n=== addr_match vs config_match (v3 addressing split, lines 805-813) ===")
# =============================================================================
c = UniCellV3(CELL_ID=7)
check("addr_match true at default (input_address==CELL_ID)", c.addr_match(7))
check("config_match true at CELL_ID regardless of listen address", c.config_match(7))
c.set_input_address(0x0200)
check("addr_match now keys on the NEW listen address", c.addr_match(0x0200))
check("addr_match false at old CELL_ID after retargeting", not c.addr_match(7))
check("config_match STILL keys on CELL_ID, unaffected by retargeting", c.config_match(7))
check("config_match false at the new listen address (not identity)", not c.config_match(0x0200))


# =============================================================================
print("\n=== Two-arrival mechanics: NOR gate, basic fire (lines 1397-1445) ===")
# =============================================================================
def make_armed_cell(topology, latch_in=False, one_shot=False, loop_back=False,
                     invert_out=False, latch_A_dis=False, latch_B_dis=False,
                     cell_id=0, addr=0x10):
    c = UniCellV3(CELL_ID=cell_id)
    c.boot_commit(logical_addr=addr, auth_mask_bits=0)
    c.reconfigure(topology=topology, start_flag=True, latch_in=latch_in,
                  one_shot=one_shot, loop_back=loop_back, invert_out=invert_out,
                  latch_A_dis=latch_A_dis, latch_B_dis=latch_B_dis)
    c.set_output_set(True)
    return c

c = make_armed_cell(TOPO_NOR)
r1 = c.receive(0x10, 0xFFFFFFFF)
check("first arrival returns None (no output)", r1 is None)
check("first arrival sets a_arrived", c.a_arrived)
check_eq("first arrival stores a_data", c.a_data, 0xFFFFFFFF)
r2 = c.receive(0x10, 0x00000000)
check_eq("second arrival fires NOR(0xFFFFFFFF, 0x0)", r2, 0x00000000)
check("a_arrived clears after fire (no latch_in)", not c.a_arrived)

c2 = make_armed_cell(TOPO_AND)
c2.receive(0x10, 0xF0F0F0F0)
r = c2.receive(0x10, 0x0F0F0F0F)
check_eq("AND gate via two-arrival", r, 0xF0F0F0F0 & 0x0F0F0F0F)


# =============================================================================
print("\n=== bus_hit gating: address mismatch, not armed, frozen, no output_set ===")
# =============================================================================
c = make_armed_cell(TOPO_NOR, addr=0x10)
r = c.receive(0x20, 0x1234)  # wrong address
check("wrong address: no first-arrival capture", not c.a_arrived)
check("wrong address: receive returns None", r is None)

c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c.reconfigure(topology=TOPO_NOR, start_flag=False)  # NOT armed
c.set_output_set(True)
r = c.receive(0x10, 0x1234)
check("not armed (start_flag=False): no capture", not c.a_arrived)

c = make_armed_cell(TOPO_NOR, addr=0x10)
c.frozen = True
r = c.receive(0x10, 0x1234)
check("frozen: no capture even though armed+addressed", not c.a_arrived)

c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c.reconfigure(topology=TOPO_NOR, start_flag=True)
# output_set NOT called -- defaults False
r = c.receive(0x10, 0x1234)
check("output_set=False: bus_hit blocked, no capture", not c.a_arrived)


# =============================================================================
print("\n=== latch_in: stays armed, updates a_data each fire (line 1434-1436) ===")
# =============================================================================
c = make_armed_cell(TOPO_PASS_B, latch_in=True)
c.receive(0x10, 0x11111111)   # first arrival (dummy, PASS_B ignores stored A anyway)
check("latch_in cell: a_arrived set after first arrival", c.a_arrived)
r1 = c.receive(0x10, 0x22222222)
check_eq("PASS_B fires with the trigger value", r1, 0x22222222)
check("latch_in: a_arrived STAYS set (single-arrival re-fire mode)", c.a_arrived)
check_eq("latch_in: a_data updated to the new arrival", c.a_data, 0x22222222)
# Immediately re-fires on the very next arrival (no second "first arrival" needed)
r2 = c.receive(0x10, 0x33333333)
check_eq("latch_in: re-fires immediately on next arrival", r2, 0x33333333)


# =============================================================================
print("\n=== loop_back precedence over latch_in (verified via RTL statement order) ===")
# =============================================================================
# unicell64_v3.v: latch_in's a_data<=bus_data_r comes BEFORE loop_back's
# a_data<=computed_output in the same always block -- last non-blocking
# write on the same edge wins, so loop_back should override latch_in's
# value when both are set on the same cell.
c = make_armed_cell(TOPO_NOR, latch_in=True, loop_back=True)
c.receive(0x10, 0x00000000)               # first arrival: a_data=0
r = c.receive(0x10, 0x00000000)           # second arrival: NOR(0,0) = all-ones
check_eq("NOR(0,0) fires all-ones", r, M)
check_eq("loop_back WINS over latch_in's write to a_data", c.a_data, M)
check("a_arrived stays set (latch_in re-arm still happens)", c.a_arrived)


# =============================================================================
print("\n=== one_shot: fires once, then start_flag clears permanently ===")
# =============================================================================
c = make_armed_cell(TOPO_NOR, one_shot=True)
c.receive(0x10, 0x00000000)
r1 = c.receive(0x10, 0x00000000)
check("one_shot: first fire succeeds", r1 is not None)
check("one_shot: start_flag cleared after firing", not c.start_flag)
check("one_shot: one_shot_fired latched", c.one_shot_fired)
# Re-arm attempt: even if somehow re-primed, start_flag is off so bus_hit fails
r2 = c.receive(0x10, 0x00000000)
check("one_shot: no second fire (start_flag off blocks bus_hit)", r2 is None)


# =============================================================================
print("\n=== invert_out: applied to OUTPUT only, internal state sees raw value ===")
# =============================================================================
# unicell64_v3.v: invert_out applied at drain stage -- data_reg/loop_back/
# latch_in all see the RAW computed_output, only the externally-fired value
# is inverted.
c = make_armed_cell(TOPO_AND, invert_out=True, loop_back=True)
c.receive(0x10, 0xFFFFFFFF)
r = c.receive(0x10, 0x0F0F0F0F)
raw = 0xFFFFFFFF & 0x0F0F0F0F
check_eq("invert_out: fired value is inverted", r, (~raw) & M)
check_eq("invert_out: internal a_data (via loop_back) sees the RAW value, not inverted",
         c.a_data, raw)
check_eq("invert_out: internal data_reg sees the RAW value too", c.data_reg, raw)


# =============================================================================
print("\n=== latch_A_dis (ACTUALLY wired) vs latch_B_dis (documented, dead in RTL) ===")
# =============================================================================
c = make_armed_cell(TOPO_PASS_B, latch_A_dis=True)
r = c.receive(0x10, 0x1234)
check("latch_A_dis=True: first arrival does NOT store (skipped)", not c.a_arrived)
check("latch_A_dis=True: receive returns None (no fire without a_arrived)", r is None)

# latch_B_dis is stored but has zero effect on firing, matching the real
# silicon exactly (verified: no receive()-path reads self.latch_B_dis at all).
c = make_armed_cell(TOPO_NOR, latch_B_dis=True)
c.receive(0x10, 0x0)
r = c.receive(0x10, 0x0)
check("latch_B_dis=True: fires normally anyway (dead field, matches real RTL)",
      r is not None)


# =============================================================================
print("\n=== Topology presets bundle latch_in per RTL convention (lines 1284-1349) ===")
# =============================================================================
c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c.set_topology_preset("NOR", armed=True)
check_eq("NOR preset sets topology", c.topology, TOPO_NOR)
check("NOR preset: latch_in=False (two-input op)", not c.latch_in)
check("NOR preset armed=True -> start_flag set", c.start_flag)

c.set_topology_preset("PASS_A", armed=False)
check_eq("PASS_A preset sets topology", c.topology, TOPO_PASS_A)
check("PASS_A preset: latch_in=True (single-input op, auto)", c.latch_in)
check("PASS_A preset armed=False (_COLD variant) -> start_flag clear", not c.start_flag)


# =============================================================================
print("\n=== CMD_ARRAY_RESET (lines 939-954) ===")
# =============================================================================
c = UniCellV3(CELL_ID=3)
c.boot_commit(logical_addr=0x99, auth_mask_bits=0xA5)
c.reconfigure(topology=TOPO_XOR, start_flag=True, loop_back=True, auth_token=0xA5)
c.set_output_set(True)
c.frozen = True
c.array_reset(auth_token=0xA5)
check_eq("array_reset: topology back to PASS_A", c.topology, TOPO_PASS_A)
check("array_reset: loop_back cleared", not c.loop_back)
check("array_reset: start_flag cleared", not c.start_flag)
check("array_reset: auth_mask cleared", c.auth_mask == 0)
check_eq("array_reset: input_address back to CELL_ID", c.input_address, 3)
check_eq("array_reset: output_address back to CELL_ID+1", c.output_address, 4)
check("array_reset: frozen cleared", not c.frozen)
check("array_reset: physical_mode restored (BOOT state)", c.physical_mode)
check("array_reset: output_set cleared", not c.output_set)


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
