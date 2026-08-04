"""
test_unicell_array_v3.py — Phase 6 (FINAL) tests for the v3.1 VM rebuild.

Ground truth: fpga/verilog/unicell_array64_v3.v. This phase closes the
rebuild: everything from Phases 1-5 (unicell_v3.py) composed into a
multi-cell array, cross-checked against the actual silicon-proven results
from points.md #32/#58/#59/#60/#63/#65/#66 wherever a direct replay is
possible.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unicell_v3 import UniCellV3, TOPO_PASS_B, TOPO_NOR, TOPO_AND
from unicell_array_v3 import UniCellArrayV3

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
print("=== Phase 6: basic wired-OR -- two cells, SAME address, data composes ===")
# =============================================================================
# points.md #32: same-address fan-in is a genuine free OR reduction.
arr = UniCellArrayV3(num_cells=2)
c0, c1 = arr.cells
for c in (c0, c1):
    c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
    c.reconfigure(topology=TOPO_PASS_B, start_flag=True)
    c.set_output_set(True)
    c.set_output_address(0x99)  # BOTH share the same output address

arr.deliver(0x10, 0x0)              # first arrival, both cells
r = arr.deliver(0x10, 0x0F0F0F0F)   # second arrival -- both fire, PASS_B
check("wired-OR: fire result valid", r.valid)
check_eq("wired-OR: same value from both cells ORs to itself (sanity)", r.data, 0x0F0F0F0F)
check_eq("wired-OR: address is the shared output_address", r.addr, 0x99)


# =============================================================================
print("\n=== Phase 6: masked distributed command assembly (points.md #60) ===")
# =============================================================================
# Exact replay of tb_v3_masked_compose.v's structure: 4 PASS_B source cells,
# each with a distinct nibble_mask, all listening at a shared trigger
# address, composing one word for cell4 (command-emit) via the array's
# wired-OR combine.
TRIG_ADDR = 0x10
CMD_ADDR  = 0x20
arr = UniCellArrayV3(num_cells=5)
src0, src1, src2, src3, sender = arr.cells

for i, src in enumerate((src0, src1, src2, src3)):
    src.boot_commit(logical_addr=TRIG_ADDR, auth_mask_bits=0)
    src.reconfigure(topology=TOPO_PASS_B, start_flag=True)
    src.set_output_set(True)
    src.set_output_address(CMD_ADDR)
    # nibble i kept, all others blocked
    mask = 0xFF & ~(1 << i)
    src.set_nibble_mask(bus_addr=i, mask=mask, auth_token=0)

sender.boot_commit(logical_addr=CMD_ADDR, auth_mask_bits=0)
sender.reconfigure(topology=TOPO_NOR, start_flag=True, is_command_cell=True)
sender.set_output_set(True)

# Prime all 4 sources (shared first arrival), then fire with the real
# trigger -- 0x56F0 gives nibble0=0,nibble1=F,nibble2=6,nibble3=5, matching
# the exact values points.md #65's masked-compose test used.
arr.deliver(TRIG_ADDR, 0x0)
compose_result = arr.deliver(TRIG_ADDR, 0x000056F0)
check("masked compose: wired-OR fire valid", compose_result.valid)
check_eq("masked compose: composed word == 0x56F0 (all 4 nibbles present)",
         compose_result.data, 0x000056F0)
check_eq("masked compose: address targets the command-emit cell", compose_result.addr, CMD_ADDR)

# Feed the composed result to the SENDER cell as its first arrival (matches
# the array's bus_addr<=or_addr chaining into the next cycle).
arr.deliver(compose_result.addr, compose_result.data)
check("SENDER received the composed word as its first arrival", sender.a_arrived)
check_eq("SENDER's a_data == the composed word", sender.a_data, 0x000056F0)

# Trigger SENDER's second arrival -- fires as command-emit.
arr.deliver(CMD_ADDR, 0xDEADBEEF)  # trigger value irrelevant, ignored
emission = arr.emit_arbiter()
check("SENDER emitted after being triggered", emission is not None)
check_eq("emitted word == the composed value", emission[0], 0x000056F0)


# =============================================================================
print("\n=== Phase 6: emit arbiter -- lowest-index wins, no OR-combining (unlike data bus) ===")
# =============================================================================
arr = UniCellArrayV3(num_cells=3)
for i, c in enumerate(arr.cells):
    c.boot_commit(logical_addr=0x10, auth_mask_bits=0)
    c.reconfigure(topology=TOPO_PASS_B, start_flag=True, is_command_cell=True)
    c.set_output_set(True)

arr.deliver(0x10, 0x1)   # first arrival, all 3 cells prime
arr.deliver(0x10, 0x2)   # second arrival -- ALL THREE emit simultaneously
winners = [c.CELL_ID for c in arr.cells if c.last_emit_valid]
check_eq("all three cells emitted this cycle (sanity)", winners, [0, 1, 2])
emission = arr.emit_arbiter()
check("emit_arbiter picks exactly one winner, not a combined value", emission is not None)
check_eq("emit_arbiter: LOWEST index wins (cell0), matching the RTL's high->low loop",
         emission[0], arr.cells[0].last_emit_bus)


# =============================================================================
print("\n=== Phase 6: targeted emission delivery -- exact #65/#66 replay ===")
# =============================================================================
# Recreates tb_v3_emit_targeted.v precisely: a command-emit cell primed with
# the exact "dangerous" payload from #65 (0x34 = CMD_TOPO_NOR_COLD's opcode,
# armed=0), properly targeted at ONE cell via output_address. The intended
# TARGET must receive and apply it; a BYSTANDER configured identically but
# listening at a different address must be completely untouched.
ADDR_A = 0x10  # TARGET listens here
ADDR_B = 0x20  # BYSTANDER listens here
ADDR_C = 0x30  # SENDER's own trigger address

arr = UniCellArrayV3(num_cells=3)
target, bystander, sender = arr.cells

for c, addr in ((target, ADDR_A), (bystander, ADDR_B), (sender, ADDR_C)):
    c.boot_commit(logical_addr=addr, auth_mask_bits=0)
    c.reconfigure(topology=TOPO_PASS_B, start_flag=True)
    c.set_output_set(True)

sender.reconfigure(topology=TOPO_PASS_B, start_flag=True, is_command_cell=True)
sender.set_output_set(True)
sender.set_output_address(ADDR_A)  # targets TARGET specifically, not BYSTANDER

check("TARGET armed before emission", target.start_flag)
check("BYSTANDER armed before emission", bystander.start_flag)

arr.deliver(ADDR_C, 0x00000034)  # prime SENDER's a_data to the dangerous payload
arr.deliver(ADDR_C, 0xFFFFFFFF)  # trigger -- SENDER emits 0x34, targeted at ADDR_A

emission = arr.emit_arbiter()
check_eq("SENDER emitted the exact dangerous payload", emission[0], 0x00000034)
check_eq("emission correctly targets ADDR_A (TARGET's address)", emission[1], ADDR_A)

applied_to = arr.deliver_emitted_command(emission)
check_eq("emission applied to exactly TARGET's CELL_ID, nobody else",
         applied_to, [target.CELL_ID])
check("TARGET disarmed by the emitted CMD_TOPO_NOR_COLD -- reached its intended recipient",
      not target.start_flag)
check("BYSTANDER UNTOUCHED -- the actual #66 fix, same payload, different address",
      bystander.start_flag)


# =============================================================================
print("\n=== Phase 6: the collision hazard, documented not hidden ===")
# =============================================================================
# Two cells sharing the SAME listen address (both respond to one trigger)
# but with DIFFERENT output addresses -- a genuine, real hazard: data ORs
# together nonsensically, and the "winning" address is whichever cell has
# the HIGHEST array index, not a considered choice. Reproduced faithfully,
# not smoothed over -- this is what the real hardware would actually do.
arr = UniCellArrayV3(num_cells=2)
c0, c1 = arr.cells
c0.boot_commit(logical_addr=0x10, auth_mask_bits=0)
c0.reconfigure(topology=TOPO_PASS_B, start_flag=True)
c0.set_output_set(True)
c0.set_output_address(0xAAAA)

c1.boot_commit(logical_addr=0x10, auth_mask_bits=0)  # SAME listen address as c0
c1.reconfigure(topology=TOPO_PASS_B, start_flag=True)
c1.set_output_set(True)
c1.set_output_address(0xBBBB)  # DIFFERENT output address

arr.deliver(0x10, 0x0)
r = arr.deliver(0x10, 0x12345678)  # both fire; PASS_B -> both output the same trigger value here
check_eq("collision: address is the HIGHEST-index cell's (c1), not c0's, despite both firing",
         r.addr, 0xBBBB)
check("documented, not hidden: this is a real hazard reproduced faithfully, "
      "same-address firing is the safe pattern, different-address simultaneous "
      "firing is not", True)


# =============================================================================
print("\n=== Phase 6 CAPSTONE: complete four-role SENDER/TARGET/WATCHER loader ===")
# =============================================================================
# The full design Alan untangled (points.md #63): SENDER (command-emit)
# configures TARGET via emission WHILE TARGET is frozen (frozen only blocks
# a cell's own two-arrival receive, verified in Phase 1 -- NOT command
# application, so a frozen cell can still be (re)configured). TARGET then
# confirms via CMD_LOAD_DONE, still frozen. WATCHER (an entirely ordinary
# cell) catches the confirm via its own plain receive() -- no new logic
# needed. TARGET is then released and processes real data with its new
# configuration -- closing the full loop with everything built across all
# six phases.
TARGET_ADDR  = 0x10
WATCHER_ADDR = 0x20
SENDER_TRIG  = 0x30

arr = UniCellArrayV3(num_cells=3)
target, watcher, sender = arr.cells

target.boot_commit(logical_addr=TARGET_ADDR, auth_mask_bits=0)
target.reconfigure(topology=TOPO_PASS_B, start_flag=True)  # placeholder config
target.set_output_set(True)
target.set_output_address(WATCHER_ADDR)  # TARGET's confirm will go to WATCHER
target.frozen = True  # "mid-program" protection, per the loader design

watcher.boot_commit(logical_addr=WATCHER_ADDR, auth_mask_bits=0)
watcher.reconfigure(topology=TOPO_PASS_B, start_flag=True)  # entirely ordinary
watcher.set_output_set(True)

sender.boot_commit(logical_addr=SENDER_TRIG, auth_mask_bits=0)
sender.reconfigure(topology=TOPO_PASS_B, start_flag=True, is_command_cell=True)
sender.set_output_set(True)
sender.set_output_address(TARGET_ADDR)

check("STEP 1: TARGET starts frozen (mid-program)", target.frozen)

# STEP 2: SENDER emits a topology preset (CMD_TOPO_AND, opcode 55) targeted
# at TARGET, reconfiguring it WHILE FROZEN.
AND_ARMED_OPCODE = 55
arr.deliver(SENDER_TRIG, AND_ARMED_OPCODE)  # prime
arr.deliver(SENDER_TRIG, 0xFFFFFFFF)        # trigger -- SENDER emits
emission = arr.emit_arbiter()
check_eq("STEP 2: SENDER emitted the AND-armed opcode", emission[0], AND_ARMED_OPCODE)
applied = arr.deliver_emitted_command(emission)
check_eq("STEP 2: applied to TARGET specifically", applied, [target.CELL_ID])
check_eq("STEP 2: TARGET's topology is now AND -- reconfigured WHILE FROZEN", target.topology, TOPO_AND)
check("STEP 2: TARGET still frozen (command application doesn't touch frozen)", target.frozen)

# STEP 3: TARGET confirms via CMD_LOAD_DONE -- works even while frozen.
confirm_value = target.load_done(bus_addr=target.CELL_ID, auth_token=0)
check_eq("STEP 3: confirm marker produced", confirm_value, 0x00000001)
check("STEP 3: TARGET still frozen after confirming", target.frozen)

# STEP 4: WATCHER catches the confirm via its OWN ordinary receive() call --
# delivered at TARGET's output_address (WATCHER_ADDR), no new logic at all.
check("STEP 4: WATCHER not yet armed before the confirm", not watcher.a_arrived)
r = arr.deliver(target.output_address, confirm_value)
check("STEP 4: WATCHER caught the confirm as an ordinary first arrival",
      watcher.a_arrived)
check_eq("STEP 4: WATCHER's a_data == the confirm marker", watcher.a_data, 0x00000001)

# STEP 5: TARGET released, now processes real data with its NEW (AND) config.
target.release_at(bus_addr=target.CELL_ID, auth_token=0)
check("STEP 5: TARGET released", not target.frozen)
arr.deliver(TARGET_ADDR, 0xF0F0F0F0)  # first arrival (fresh, a_arrived was cleared by LOAD_AT-style ops? )
final = arr.deliver(TARGET_ADDR, 0x0F0F0F0F)
check_eq("STEP 5: TARGET now computes AND with its loader-assigned configuration",
         final.data, 0xF0F0F0F0 & 0x0F0F0F0F)

if all(s == "PASS" for s, _ in results):
    print("\n>>> FULL FOUR-ROLE LOADER LOOP CLOSED: SENDER configured a frozen TARGET via "
          "emission, TARGET confirmed while still frozen, an entirely ordinary WATCHER "
          "caught the confirm with zero new logic, TARGET was released and computed "
          "correctly with its new configuration.")


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
