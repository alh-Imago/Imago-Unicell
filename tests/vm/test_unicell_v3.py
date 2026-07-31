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
    shift_in_left, shift_out_right, apply_nibble_mask, compute_lane_kill,
    select_pattern, compute_effective_routing, compute_transit_only,
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
c.set_output_set(False)  # reconfigure() correctly sets output_set=True as a
                          # side effect (matches the RTL exactly) -- force it
                          # back off explicitly to test this gate in isolation
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
print("\n=== Phase 2: shift/nibble-mask helper functions in isolation ===")
# =============================================================================
check_eq("shift_in_left by 8, enabled", shift_in_left(0x000000FF, 8, True), 0x0000FF00)
check_eq("shift_in_left disabled: passthrough", shift_in_left(0x000000FF, 8, False), 0x000000FF)
check_eq("shift_in_left unsupported amount (5): passthrough", shift_in_left(0xFF, 5, True), 0xFF)
check_eq("shift_in_left truncates overflow to 32 bits", shift_in_left(0xFFFFFFFF, 4, True), 0xFFFFFFF0)

check_eq("shift_out_right by 8, enabled", shift_out_right(0x0000FF00, 8, True), 0x000000FF)
check_eq("shift_out_right disabled: passthrough", shift_out_right(0x0000FF00, 8, False), 0x0000FF00)
check_eq("shift_out_right unsupported amount (7): passthrough", shift_out_right(0xFF00, 7, True), 0xFF00)
check_eq("shift_out_right zero-fills from the top", shift_out_right(0xFFFFFFFF, 16, True), 0x0000FFFF)

check_eq("nibble_mask blocks nibble 0 (mask bit0=1)",
         apply_nibble_mask(0x12345678, 0b00000001, True), 0x12345670)
check_eq("nibble_mask blocks nibbles 0 and 7 (mask=0x81)",
         apply_nibble_mask(0x12345678, 0b10000001, True), 0x02345670)
check_eq("nibble_mask disabled: passthrough regardless of mask bits",
         apply_nibble_mask(0x12345678, 0xFF, False), 0x12345678)
check_eq("nibble_mask all-pass (mask=0): unchanged",
         apply_nibble_mask(0x12345678, 0x00, True), 0x12345678)

check_eq("lane_kill all cuts 0: all-ones (no-op, RTL's own regression-safety property)",
         compute_lane_kill(shift_amt=8, lane_cut=0b000), 0xFFFFFFFF)
check_eq("lane_kill shift_amt=0: no-op regardless of cut bits",
         compute_lane_kill(shift_amt=0, lane_cut=0b111), 0xFFFFFFFF)


# =============================================================================
print("\n=== Phase 2: shift_in + nibble_mask applied to the GATE'S B OPERAND ONLY ===")
# =============================================================================
# PASS_B with shift_in+mask: the FIRED value should reflect the transform,
# but the STORED a_data (via latch_in rearm) must NOT -- verified against
# the RTL's `a_data <= bus_data_r` (raw) vs `second_val` (transformed) split.
c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c.reconfigure(topology=TOPO_PASS_B, start_flag=True, latch_in=True)
c.set_output_set(True)
c.set_shift_in(bus_addr=0, amount=8, auth_token=0)
c.set_nibble_mask(bus_addr=0, mask=0b00000001, auth_token=0)  # block nibble 0

c.receive(0x10, 0x00000000)  # first arrival (dummy for PASS_B)
r = c.receive(0x10, 0x000000FF)   # trigger: shift left 8 -> 0x0000FF00, mask nibble0 -> 0x0000FF00 (unaffected, nibble0 already 0)
check_eq("PASS_B fires the shifted+masked value", r, 0x0000FF00)
check_eq("latch_in rearm stores the RAW trigger, NOT shifted/masked", c.a_data, 0x000000FF)

# A case where masking actually changes something, to be sure it's not
# coincidentally passing because nibble0 was already 0.
c2 = UniCellV3(CELL_ID=0)
c2.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c2.reconfigure(topology=TOPO_PASS_B, start_flag=True, latch_in=True)
c2.set_output_set(True)
c2.set_nibble_mask(bus_addr=0, mask=0b00000001, auth_token=0)  # block nibble 0, no shift
c2.receive(0x10, 0x0)
r2 = c2.receive(0x10, 0x000000FF)
check_eq("nibble_mask actually blocks nibble0 in the fired value", r2, 0x000000F0)
check_eq("latch_in rearm still stores the RAW (unmasked) trigger", c2.a_data, 0x000000FF)

# First-arrival store must ALSO be unaffected by shift_in/nibble_mask.
c3 = UniCellV3(CELL_ID=0)
c3.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c3.reconfigure(topology=TOPO_NOR, start_flag=True)
c3.set_output_set(True)
c3.set_nibble_mask(bus_addr=0, mask=0xFF, auth_token=0)  # block EVERYTHING
c3.receive(0x10, 0x000000FF)
check_eq("first-arrival store uses RAW bus_data, ignores nibble_mask entirely",
         c3.a_data, 0x000000FF)


# =============================================================================
print("\n=== Phase 2: shift_out + lane_cut applied to the EMITTED VALUE ONLY ===")
# =============================================================================
# Internal state (data_reg, loop_back's a_data) must see the RAW gate
# result -- only the returned/emitted value gets shift_out+lane_cut+invert.
c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c.reconfigure(topology=TOPO_ONE, start_flag=True, loop_back=True)  # ONE = all-ones, easy to see shifted
c.set_output_set(True)
c.set_shift_out(bus_addr=0, amount=8, auth_token=0)
c.receive(0x10, 0x0)
r = c.receive(0x10, 0x0)
check_eq("ONE gate shifted-out by 8: top byte zeroed", r, 0x00FFFFFF)
check_eq("internal a_data (via loop_back) sees the RAW, unshifted gate result",
         c.a_data, 0xFFFFFFFF)
check_eq("internal data_reg sees the RAW, unshifted gate result too",
         c.data_reg, 0xFFFFFFFF)

# lane_cut zeroes the window that crossed a cut boundary during the shift.
c2 = UniCellV3(CELL_ID=0)
c2.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c2.reconfigure(topology=TOPO_ONE, start_flag=True)
c2.set_output_set(True)
c2.set_shift_out(bus_addr=0, amount=8, auth_token=0)
c2.set_lane_cut(bus_addr=0, bits=0b001, auth_token=0)  # cut boundary 8
c2.receive(0x10, 0x0)
r2 = c2.receive(0x10, 0x0)
expected = compute_lane_kill(8, 0b001) & shift_out_right(0xFFFFFFFF, 8, True)
check_eq("lane_cut zeroes the crossed-boundary window on top of shift_out", r2, expected)

# shift_out + invert_out interaction: invert applies AFTER shift_out/lane_cut.
c3 = UniCellV3(CELL_ID=0)
c3.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c3.reconfigure(topology=TOPO_ZERO, start_flag=True, invert_out=True)
c3.set_output_set(True)
c3.set_shift_out(bus_addr=0, amount=8, auth_token=0)  # ZERO shifted is still ZERO
c3.receive(0x10, 0x0)
r3 = c3.receive(0x10, 0x0)
check_eq("invert_out applies AFTER shift_out (inverted zero = all-ones)", r3, 0xFFFFFFFF)


# =============================================================================
print("\n=== Phase 2: config_match gating on methodology setters ===")
# =============================================================================
c = UniCellV3(CELL_ID=9)
try:
    c.set_nibble_mask(bus_addr=0, mask=0xFF, auth_token=0)  # wrong address (not CELL_ID)
    check("METH_SET_MASK with wrong bus_addr raises AuthError (config_match fails)", False)
except AuthError:
    check("METH_SET_MASK with wrong bus_addr raises AuthError (config_match fails)", True)
c.set_nibble_mask(bus_addr=9, mask=0xFF, auth_token=0)  # correct CELL_ID
check("METH_SET_MASK with correct bus_addr (==CELL_ID) succeeds", c.mask_en)


# =============================================================================
print("\n=== Phase 2: CMD_ARRAY_RESET clears methodology fields too ===")
# =============================================================================
c = UniCellV3(CELL_ID=2)
c.boot_commit(logical_addr=0, auth_mask_bits=0xA5)
c.set_nibble_mask(bus_addr=2, mask=0xFF, auth_token=0xA5)
c.set_shift_in(bus_addr=2, amount=8, auth_token=0xA5)
c.set_shift_out(bus_addr=2, amount=8, auth_token=0xA5)
c.set_lane_cut(bus_addr=2, bits=0b111, auth_token=0xA5)
c.array_reset(auth_token=0xA5)
check("array_reset clears mask_en", not c.mask_en)
check_eq("array_reset clears nibble_mask", c.nibble_mask, 0)
check_eq("array_reset clears shift_amt", c.shift_amt, 0)
check("array_reset clears shift_in_en", not c.shift_in_en)
check("array_reset clears shift_out_en", not c.shift_out_en)
check_eq("array_reset clears lane_cut", c.lane_cut, 0)


# =============================================================================
print("\n=== Phase 3: comparator + effective_routing helper functions ===")
# =============================================================================
check_eq("select_pattern: LOW when bus_data < a_data", select_pattern(0x10, 0x50, 4, 1, 5), 4)
check_eq("select_pattern: EQUAL when bus_data == a_data", select_pattern(0x50, 0x50, 4, 1, 5), 1)
check_eq("select_pattern: HIGH when bus_data > a_data", select_pattern(0x90, 0x50, 4, 1, 5), 5)
check_eq("select_pattern: comparison is UNSIGNED (matches Verilog default)",
         select_pattern(0xFFFFFFFF, 0x1, 4, 1, 5), 5)  # 0xFFFFFFFF > 1 unsigned

check_eq("effective_routing: dynamic_route_en=0 collapses to routing_mask alone",
         compute_effective_routing(False, selected_pattern=0b111111, routing_mask=0b0101), 0b0101)
check_eq("effective_routing: dynamic_route_en=1 ANDs pattern with routing_mask",
         compute_effective_routing(True, selected_pattern=0b0100, routing_mask=0b0101), 0b0100)
check_eq("effective_routing: pattern bit outside routing_mask's open set is masked out",
         compute_effective_routing(True, selected_pattern=0b1010, routing_mask=0b0101), 0b0000)

check("transit_only: false when effective_routing is zero (nothing to suppress)",
      not compute_transit_only(effective_routing=0, cardinal_edge=0b1111))
check("transit_only: true when ALL active directions are cardinal-only",
      compute_transit_only(effective_routing=0b0101, cardinal_edge=0b0101))
check("transit_only: FALSE when even one active direction is NOT cardinal-only "
      "(the actual #58 capability -- a single global bit couldn't express this)",
      not compute_transit_only(effective_routing=0b0101, cardinal_edge=0b0100))


# =============================================================================
print("\n=== Phase 3: full cell, replicating the exact #59 silicon-proven scenario ===")
# =============================================================================
# routing_mask=N|E(0b0101), cardinal_edge=0 (all local), pattern_low=E-only(4),
# pattern_equal=N-only(1), pattern_high=N|E(5), dynamic_route_en=1.
# Threshold (a_data) = 0x50; three injected values 0x10/0x50/0x90 -- this is
# the EXACT scenario zone1_route_latch_isolated.tcl proved on real Arria 10
# silicon (points.md #59), replayed here as a direct sim/silicon cross-check.

def make_routing_cell():
    c = UniCellV3(CELL_ID=0)
    c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
    c.reconfigure(topology=TOPO_PASS_B, start_flag=True)
    c.set_output_set(True)
    c.set_route_latch(routing_mask=0b0101, cardinal_edge=0b0000,
                       pattern_low=0b0100, pattern_equal=0b0001, pattern_high=0b0101,
                       dynamic_route_en=True)
    return c

# LOW case: 0x10 < 0x50 -> pattern_low (E-only) -> effective_routing=E-only,
# cardinal_edge=0 -> transit_only=False (local still fires).
c = make_routing_cell()
c.receive(0x10, 0x50)             # prime threshold
r = c.receive(0x10, 0x10)         # inject LOW
check_eq("LOW case: effective_routing == E-only (matches silicon: east only)",
         c.last_fire_routing, 0b0100)
check("LOW case: transit_only False (local bus fires, matches silicon)",
      not c.last_fire_transit)

# EQUAL case: 0x50 == 0x50 -> pattern_equal (N-only).
c = make_routing_cell()
c.receive(0x10, 0x50)
r = c.receive(0x10, 0x50)
check_eq("EQUAL case: effective_routing == N-only (matches silicon: north only)",
         c.last_fire_routing, 0b0001)
check("EQUAL case: transit_only False (local bus fires, matches silicon)",
      not c.last_fire_transit)

# HIGH case: 0x90 > 0x50 -> pattern_high (N|E).
c = make_routing_cell()
c.receive(0x10, 0x50)
r = c.receive(0x10, 0x90)
check_eq("HIGH case: effective_routing == N|E (matches silicon: both)",
         c.last_fire_routing, 0b0101)
check("HIGH case: transit_only False (local bus fires, matches silicon)",
      not c.last_fire_transit)


# =============================================================================
print("\n=== Phase 3: the actual #58 capability -- mixed cardinal-only/local edges ===")
# =============================================================================
# routing_mask=N|E, cardinal_edge=E-only(0b0100): E is cardinal-only, N is
# not -- local should STILL present because N keeps it alive, even while E
# is a pure conduit on the SAME fire. A single global transit_only bit could
# never express this -- this is the actual thing #58 was built to prove.
c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c.reconfigure(topology=TOPO_PASS_B, start_flag=True)
c.set_output_set(True)
c.set_route_latch(routing_mask=0b0101, cardinal_edge=0b0100, dynamic_route_en=False)
c.receive(0x10, 0x0)
c.receive(0x10, 0x0)
check_eq("mixed-edge case: effective_routing == N|E (static, dynamic_route_en=0)",
         c.last_fire_routing, 0b0101)
check("mixed-edge case: transit_only FALSE -- N (not cardinal-only) keeps local alive "
      "even though E on the SAME fire is a pure conduit",
      not c.last_fire_transit)

# Control: cardinal_edge=N|E (both cardinal-only) -- legacy-equivalent, local suppressed.
c2 = UniCellV3(CELL_ID=0)
c2.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c2.reconfigure(topology=TOPO_PASS_B, start_flag=True)
c2.set_output_set(True)
c2.set_route_latch(routing_mask=0b0101, cardinal_edge=0b0101, dynamic_route_en=False)
c2.receive(0x10, 0x0)
c2.receive(0x10, 0x0)
check("control case: transit_only TRUE when every active direction IS cardinal-only",
      c2.last_fire_transit)


# =============================================================================
print("\n=== Phase 3: comparator uses the RAW trigger, gate uses the shift/mask-transformed one ===")
# =============================================================================
# A single fire where shift_in+nibble_mask are active: the GATE result must
# reflect the transform, but the COMPARATOR's routing decision must be based
# on the untransformed value -- two different "B"s on the same fire.
c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c.reconfigure(topology=TOPO_PASS_B, start_flag=True)
c.set_output_set(True)
c.set_shift_in(bus_addr=0, amount=8, auth_token=0)  # gate sees the trigger shifted left 8
c.set_route_latch(routing_mask=0b0101, cardinal_edge=0b0000,
                   pattern_low=0b0100, pattern_equal=0b0001, pattern_high=0b0101,
                   dynamic_route_en=True)
c.receive(0x10, 0x50)              # prime threshold (a_data), unaffected by shift_in
r = c.receive(0x10, 0x10)          # inject: RAW=0x10 < a_data=0x50 -> should route LOW (E-only)
check_eq("gate result reflects the shift_in transform", r, 0x10 << 8)
check_eq("comparator's routing decision uses the RAW (unshifted) trigger, not the gate's operand",
         c.last_fire_routing, 0b0100)  # LOW/E-only, based on raw 0x10 < 0x50


# =============================================================================
print("\n=== Phase 3: config_match gating + METH_SET_TRANSIT legacy convenience ===")
# =============================================================================
c = UniCellV3(CELL_ID=4)
try:
    c.set_routing_mask(bus_addr=0, mask=0b1111, auth_token=0)
    check("METH_SET_ROUTING with wrong bus_addr raises AuthError", False)
except AuthError:
    check("METH_SET_ROUTING with wrong bus_addr raises AuthError", True)
c.set_routing_mask(bus_addr=4, mask=0b0101, auth_token=0)
check_eq("METH_SET_ROUTING with correct bus_addr succeeds", c.routing_mask, 0b0101)

c.set_transit(bus_addr=4, all_cardinal=True, auth_token=0)
check_eq("METH_SET_TRANSIT(all_cardinal=True) sets ALL cardinal_edge bits uniformly",
         c.cardinal_edge, 0b111111)
c.set_transit(bus_addr=4, all_cardinal=False, auth_token=0)
check_eq("METH_SET_TRANSIT(all_cardinal=False) clears ALL cardinal_edge bits",
         c.cardinal_edge, 0)

# CMD_SET_ROUTE_LATCH is BROADCAST -- auth_ok only, no config_match needed.
c2 = UniCellV3(CELL_ID=99)
c2.set_route_latch(routing_mask=0b1111, auth_token=0)  # no bus_addr param at all
check_eq("CMD_SET_ROUTE_LATCH is broadcast (auth_ok only, no addressing needed)",
         c2.routing_mask, 0b1111)


# =============================================================================
print("\n=== Phase 3: CMD_ARRAY_RESET clears the routing latch too ===")
# =============================================================================
c = UniCellV3(CELL_ID=1)
c.boot_commit(logical_addr=0, auth_mask_bits=0xA5)
c.set_route_latch(routing_mask=0b1111, cardinal_edge=0b1111, pattern_low=1,
                   pattern_equal=2, pattern_high=3, dynamic_route_en=True, auth_token=0xA5)
c.array_reset(auth_token=0xA5)
check_eq("array_reset clears routing_mask", c.routing_mask, 0)
check_eq("array_reset clears cardinal_edge", c.cardinal_edge, 0)
check_eq("array_reset clears pattern_low", c.pattern_low, 0)
check_eq("array_reset clears pattern_equal", c.pattern_equal, 0)
check_eq("array_reset clears pattern_high", c.pattern_high, 0)
check("array_reset clears dynamic_route_en", not c.dynamic_route_en)


# =============================================================================
print("\n=== Phase 4: full-word overwrite semantics (regression for a real bug caught) ===")
# =============================================================================
# CMD_RECONFIGURE/CMD_LOAD_AT write cmd_data as a COMPLETE 32-bit word every
# time in the real RTL -- an unspecified field defaults to 0, it does NOT
# preserve whatever a PREVIOUS reconfigure() call set. An earlier version of
# this VM modeled the wrong ("only touch what's passed") behavior -- caught
# and fixed while building Phase 4, before any dependent code existed.
c = UniCellV3(CELL_ID=0)
c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c.reconfigure(topology=TOPO_NOR, start_flag=True, loop_back=True, invert_out=True)
check("first reconfigure: loop_back set", c.loop_back)
check("first reconfigure: invert_out set", c.invert_out)
c.reconfigure(topology=TOPO_AND, start_flag=True)  # loop_back/invert_out NOT mentioned
check("second reconfigure: loop_back correctly RESET (full-word overwrite, not preserved)",
      not c.loop_back)
check("second reconfigure: invert_out correctly RESET too", not c.invert_out)
check_eq("second reconfigure: topology updated to the new value", c.topology, TOPO_AND)


# =============================================================================
print("\n=== Phase 4: CMD_LOAD_AT -- field-identical to CMD_RECONFIGURE, config_match-gated ===")
# =============================================================================
c = UniCellV3(CELL_ID=7)
c.physical_mode = False  # simulate already-booted, matches RUN-state LOAD_AT usage
try:
    c.load_at(bus_addr=0, topology=TOPO_NOR, start_flag=True)  # wrong address
    check("CMD_LOAD_AT with wrong bus_addr raises AuthError (config_match fails)", False)
except AuthError:
    check("CMD_LOAD_AT with wrong bus_addr raises AuthError (config_match fails)", True)
check_eq("rejected LOAD_AT left topology untouched", c.topology, TOPO_PASS_A)

c.load_at(bus_addr=7, topology=TOPO_NOR, start_flag=True, loop_back=True)
check_eq("CMD_LOAD_AT with correct bus_addr (==CELL_ID) applies topology", c.topology, TOPO_NOR)
check("CMD_LOAD_AT applies loop_back too (field-identical to RECONFIGURE)", c.loop_back)
check("CMD_LOAD_AT side effects match RECONFIGURE: output_set set", c.output_set)
check("CMD_LOAD_AT side effects match RECONFIGURE: frozen cleared", not c.frozen)


# =============================================================================
print("\n=== Phase 4: the actual point -- per-cell heterogeneous config (exclusion property) ===")
# =============================================================================
# Two cells, SAME bus_addr issued to both (as a real shared bus would
# broadcast the address+command to every cell) -- only the one whose own
# CELL_ID matches should apply it. This is the exact property
# zone_target.tcl already proved on real silicon for CMD_LOAD_AT.
cell_a = UniCellV3(CELL_ID=0); cell_a.physical_mode = False
cell_b = UniCellV3(CELL_ID=1); cell_b.physical_mode = False

TARGET_BUS_ADDR = 0  # targets cell_a specifically
for c in (cell_a, cell_b):
    try:
        c.load_at(bus_addr=TARGET_BUS_ADDR, topology=TOPO_XOR, start_flag=True)
    except AuthError:
        pass  # cell_b will reject -- expected, not a test failure

check_eq("cell_a (CELL_ID==bus_addr): topology applied", cell_a.topology, TOPO_XOR)
check_eq("cell_b (CELL_ID!=bus_addr): UNTOUCHED -- exclusion property, fusion impossible",
         cell_b.topology, TOPO_PASS_A)


# =============================================================================
print("\n=== Phase 4: CMD_SET_ROUTE_LATCH_AT -- same pattern for the routing latch ===")
# =============================================================================
cell_a = UniCellV3(CELL_ID=2); cell_a.physical_mode = False
cell_b = UniCellV3(CELL_ID=3); cell_b.physical_mode = False
for c in (cell_a, cell_b):
    try:
        c.set_route_latch_at(bus_addr=2, routing_mask=0b0100, cardinal_edge=0b0100)
    except AuthError:
        pass

check_eq("cell_a (targeted): routing_mask applied", cell_a.routing_mask, 0b0100)
check_eq("cell_b (not targeted): routing_mask UNTOUCHED", cell_b.routing_mask, 0)


# =============================================================================
print("\n=== Phase 4: CMD_FREEZE_AT/CMD_RELEASE_AT -- replicates the silicon-proven hole test ===")
# =============================================================================
# Mirrors tb_v3_masked_compose_freeze.v (points.md #65): freezing one cell
# via the TARGETED opcode must leave every other cell's frozen state alone.
cell1 = UniCellV3(CELL_ID=1); cell1.physical_mode = False
cell2 = UniCellV3(CELL_ID=2); cell2.physical_mode = False
cell3 = UniCellV3(CELL_ID=3); cell3.physical_mode = False

cell1.freeze_at(bus_addr=1)
check("cell1 (targeted): frozen", cell1.frozen)
check("cell2 (not targeted): UNAFFECTED -- exactly the property #65 proved in silicon",
      not cell2.frozen)
check("cell3 (not targeted): UNAFFECTED", not cell3.frozen)

cell1.release_at(bus_addr=1)
check("cell1: un-frozen via CMD_RELEASE_AT", not cell1.frozen)


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
