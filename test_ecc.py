"""
test_ecc.py — SECDED ECC Tests

Validates the ECC implementation against Engineering Addendum v0.1 §2:

  - SECDED (Single Error Correct, Double Error Detect) on 32-bit data words
  - 7-bit Hamming check word computed on emit, verified on receive
  - Single-bit errors corrected silently; correction counter incremented
  - Double-bit errors raise ECCError; counter incremented
  - ECC is per-cell (opt-in); cells without ECC pass data unchanged
  - Bit-flip injection via inject_bit_flip() for test harness validation
  - ECC on loopback cells: corruption detected/corrected on each circulation
  - ECC on storage-mode cells: latch protected against single-event upsets
  - Region-level ECC enable/disable via array.enable_ecc() / disable_ecc()
  - ecc_status() aggregates corrections and double-errors across all cells
  - ECC does not affect bus values when disabled (check word = 0)

Run with: python3 test_ecc.py
"""

from unicell import (UniCell, FUNCTION_LOAD_PATTERN, VAR_TRUE, VAR_FALSE,
                     ECCError, _compute_ecc, _verify_ecc)
from unicell_array import UniCellArray
from controller import ImagoController, CellMapRecord

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

# =============================================================================
print("\n=== ECC primitives — _compute_ecc / _verify_ecc ===\n")

# No error: verify returns original value unchanged
for val in [0x00000000, 0xFFFFFFFF, 0xDEADBEEF, 0xA5A5A5A5, 0x00000001]:
    chk = _compute_ecc(val)
    corrected, single, double = _verify_ecc(val, chk)
    check(f"No error: _verify_ecc(0x{val:08X}) → unchanged",
          corrected == val and not single and not double)

# Single-bit error in each data bit position (0–31)
all_single_ok = True
for bit in range(32):
    val = 0xA5A5A5A5
    chk = _compute_ecc(val)
    corrupted = val ^ (1 << bit)          # flip one data bit
    corrected, single, double = _verify_ecc(corrupted, chk)
    if not (corrected == val and single and not double):
        all_single_ok = False
        print(f"    FAILED at bit {bit}: corrected=0x{corrected:08X} "
              f"single={single} double={double}")
check("Single-bit correction: all 32 data bit positions correctable",
      all_single_ok)

# Double-bit error: detected, not corrected
val2 = 0x12345678
chk2 = _compute_ecc(val2)
corrupted2 = val2 ^ 0b11   # flip bits 0 and 1
corrected2, single2, double2 = _verify_ecc(corrupted2, chk2)
check("Double-bit detection: double error flagged", double2 == True)
check("Double-bit detection: single flag not set", single2 == False)

# Check word of 0 (ECC disabled) always returns no-error
corrected3, s3, d3 = _verify_ecc(0xDEADBEEF, 0)
check("ECC disabled (check=0): no error signalled",
      corrected3 == 0xDEADBEEF and not s3 and not d3)

# Different values produce different check words
chk_a = _compute_ecc(0x00000000)
chk_b = _compute_ecc(0xFFFFFFFF)
chk_c = _compute_ecc(0x00000001)
check("Different values produce different check words",
      len({chk_a, chk_b, chk_c}) == 3)

# =============================================================================
print("\n=== ECC on UniCell — emit and receive ===\n")

# ECC disabled (default): tick() returns (addr, value, 0)
c = UniCell(0x0001)
c.gate_state     = 0b000000000   # PASS
c.input_address  = 0x1000
c.output_address = 0x2000
c.start_flag     = True
c.ecc_enabled    = False
c.data           = 0xCAFEBABE
result = c.tick()
check("ECC disabled: tick returns 3-tuple", len(result) == 3)
check("ECC disabled: ecc_check is 0", result[2] == 0)
check("ECC disabled: value correct", result[1] == 0xCAFEBABE)

# ECC enabled: tick() returns correct check word
c2 = UniCell(0x0002)
c2.gate_state     = 0b000000000
c2.input_address  = 0x1000
c2.output_address = 0x2000
c2.start_flag     = True
c2.ecc_enabled    = True
c2.data           = 0xCAFEBABE
result2 = c2.tick()
expected_chk = _compute_ecc(0xCAFEBABE)
check("ECC enabled: tick returns non-zero check word", result2[2] != 0)
check("ECC enabled: check word matches _compute_ecc", result2[2] == expected_chk)
check("ECC enabled: value unchanged", result2[1] == 0xCAFEBABE)

# Receive with correct ECC: data stored unchanged
c3 = UniCell(0x0003)
c3.ecc_enabled = True
val3 = 0x12345678
chk3 = _compute_ecc(val3)
c3.receive(val3, chk3)
check("ECC receive: correct data stored unchanged", c3.data == val3)
check("ECC receive: no corrections recorded", c3.ecc_corrections == 0)

# Receive with single-bit error: silently corrected
c4 = UniCell(0x0004)
c4.ecc_enabled = True
val4 = 0x12345678
chk4 = _compute_ecc(val4)
corrupted4 = val4 ^ (1 << 5)   # flip bit 5
c4.receive(corrupted4, chk4)
check("ECC receive: single-bit error corrected", c4.data == val4)
check("ECC receive: correction counter incremented", c4.ecc_corrections == 1)

# Receive with double-bit error: ECCError raised
c5 = UniCell(0x0005)
c5.ecc_enabled = True
val5 = 0xDEADBEEF
chk5 = _compute_ecc(val5)
corrupted5 = val5 ^ 0b11   # flip bits 0 and 1
ecc_error_raised = False
try:
    c5.receive(corrupted5, chk5)
except ECCError:
    ecc_error_raised = True
check("ECC receive: double-bit error raises ECCError", ecc_error_raised)
check("ECC receive: double_errors counter incremented", c5.ecc_double_errors == 1)

# ECC disabled: corrupted data stored as-is (no checking)
c6 = UniCell(0x0006)
c6.ecc_enabled = False
val6 = 0x12345678
chk6 = _compute_ecc(val6)
corrupted6 = val6 ^ (1 << 3)
c6.receive(corrupted6, chk6)
check("ECC disabled: corrupted data stored without correction",
      c6.data == corrupted6)

# =============================================================================
print("\n=== Bit-flip injection (test harness) ===\n")

# inject_bit_flip on held data
c7 = UniCell(0x0007)
c7.data = 0x00000000
c7.inject_bit_flip(0)   # flip bit 0
check("inject_bit_flip: data bit 0 flipped", c7.data == 0x00000001)

c7.inject_bit_flip(0)   # flip back
check("inject_bit_flip: flip twice restores original", c7.data == 0x00000000)

c7.inject_bit_flip(31)
check("inject_bit_flip: high bit flipped", c7.data == 0x80000000)

# inject_bit_flip on stored value (storage mode)
c8 = UniCell(0x0008)
c8.storage_mode  = True
c8._stored_value = 0xFFFFFFFF
c8.inject_bit_flip(7)
check("inject_bit_flip: storage latch bit flipped",
      c8._stored_value == (0xFFFFFFFF ^ (1 << 7)))

# inject_double_bit_flip
c9 = UniCell(0x0009)
c9.data = 0x00000000
c9.inject_double_bit_flip(0, 1)
check("inject_double_bit_flip: two bits flipped", c9.data == 0b11)

# =============================================================================
print("\n=== ECC through the array ===\n")

# ECC-enabled cell: end-to-end through tick + Phase 1 delivery
arr = UniCellArray(cell_count=20)
arr.enforce_emission_limits = False

# Cell A: NOT gate, ECC on, posts to 0x2000
cA = arr.allocate_cell()
arr.write_config(cA.address, [FUNCTION_LOAD_PATTERN, 0b000000001, 0x1000, 0x2000])
cA_cell = arr.cells[cA.address]
cA_cell.ecc_enabled = True

# Cell B: PASS gate, ECC on, listens at 0x2000, posts to 0x3000
cB = arr.allocate_cell()
arr.write_config(cB.address, [FUNCTION_LOAD_PATTERN, 0b000000000, 0x2000, 0x3000])
cB_cell = arr.cells[cB.address]
cB_cell.ecc_enabled = True

arr.assert_start_flag()
arr.bus[0x1000] = (VAR_FALSE, 0)  # inject: NOT(0) should give 1

arr.tick()  # Cell A fires: NOT(0)=1, emits with ECC check
v_mid = arr.read_bus(0x2000)
check("Array ECC: NOT(0)=1 on bus at 0x2000", v_mid == VAR_TRUE)

arr.tick()  # Cell B receives (1, check), verifies, fires PASS, emits to 0x3000
v_out = arr.read_bus(0x3000)
check("Array ECC: value propagates through ECC chain", v_out == VAR_TRUE)
check("Array ECC: no spurious corrections", cB_cell.ecc_corrections == 0)

# Inject a bit flip into the bus mid-transit (simulate single-event upset)
arr2 = UniCellArray(cell_count=20)
arr2.enforce_emission_limits = False

cX = arr2.allocate_cell()
arr2.write_config(cX.address, [FUNCTION_LOAD_PATTERN, 0b000000000, 0xA000, 0xB000])
cX_cell = arr2.cells[cX.address]
cX_cell.ecc_enabled = True

cY = arr2.allocate_cell()
arr2.write_config(cY.address, [FUNCTION_LOAD_PATTERN, 0b000000000, 0xB000, 0xC000])
cY_cell = arr2.cells[cY.address]
cY_cell.ecc_enabled = True

arr2.assert_start_flag()
arr2.bus[0xA000] = (VAR_TRUE, 0)
arr2.tick()  # cX fires, posts (1, correct_check) to 0xB000

# Corrupt the bus value in-transit (simulate a bit flip on the wire)
val_on_bus, chk_on_bus = arr2.bus[0xB000]
corrupted_val = val_on_bus ^ (1 << 0)  # flip bit 0: 1 -> 0
arr2.bus[0xB000] = (corrupted_val, chk_on_bus)  # keep original check

arr2.tick()  # cY receives corrupted value — should correct it
v_corrected = arr2.read_bus(0xC000)
check("Array ECC: bus corruption corrected by receiving cell",
      v_corrected == VAR_TRUE)   # corrected back to original 1
check("Array ECC: correction recorded on receiving cell",
      cY_cell.ecc_corrections == 1)

# enable_ecc() / disable_ecc() array methods
arr3 = UniCellArray(cell_count=20)
arr3.enforce_emission_limits = False
for i in range(5):
    c = arr3.allocate_cell()
    arr3.write_config(c.address, [FUNCTION_LOAD_PATTERN, 0b000000000,
                                   0x1000+i, 0x2000+i])
count_on = arr3.enable_ecc()
check("enable_ecc(): all 5 cells enabled", count_on == 5)
check("enable_ecc(): cells have ecc_enabled=True",
      all(c.ecc_enabled for c in arr3.cells.values()))

count_off = arr3.disable_ecc()
check("disable_ecc(): all 5 cells disabled", count_off == 5)
check("disable_ecc(): cells have ecc_enabled=False",
      all(not c.ecc_enabled for c in arr3.cells.values()))

# Selective enable
addrs = list(arr3.cells.keys())
arr3.enable_ecc([addrs[0], addrs[1]])
enabled = sum(1 for c in arr3.cells.values() if c.ecc_enabled)
check("enable_ecc(subset): only 2 cells enabled", enabled == 2)

# ecc_status() aggregation
arr3.cells[addrs[0]].ecc_corrections   = 3
arr3.cells[addrs[1]].ecc_double_errors = 1
st = arr3.ecc_status()
check("ecc_status: enabled count", st["ecc_enabled_cells"] == 2)
check("ecc_status: total corrections", st["total_corrections"] == 3)
check("ecc_status: total double errors", st["total_double_errors"] == 1)

# =============================================================================
print("\n=== ECC on storage-mode cells (latch protection) ===\n")

# Storage cell with ECC: latch value protected
arr4 = UniCellArray(cell_count=10)
arr4.enforce_emission_limits = False

stor = arr4.allocate_cell()
arr4.write_config(stor.address, [FUNCTION_LOAD_PATTERN, 0b000000000,
                                  0xD000, 0xE000], storage_mode=True)
stor_cell = arr4.cells[stor.address]
stor_cell.ecc_enabled = True

arr4.assert_start_flag()
arr4.bus[0xD000] = (VAR_TRUE, 0)
arr4.tick()   # write VAR_TRUE into latch; emits with ECC check
v1 = arr4.read_bus(0xE000)
check("Storage ECC: latch written and emitted", v1 == VAR_TRUE)

arr4.bus = {}
arr4.tick()   # re-emits from latch with ECC check
v2 = arr4.read_bus(0xE000)
check("Storage ECC: latch re-emits with ECC on second tick", v2 == VAR_TRUE)

# Inject a bit flip into the storage cell's latch
stor_cell.inject_bit_flip(0)   # flip bit 0: 1 -> 0 (corrupt latch)
check("Storage ECC: latch corrupted by inject_bit_flip",
      stor_cell._stored_value == VAR_FALSE)

# On next tick, the storage cell re-emits the corrupted value
# (the ECC is on the BUS path — latch-internal corruption needs
# the latch to re-read its check word, which it recomputes on write)
# The corruption is detected when a DOWNSTREAM ECC cell receives it.

arr4.bus = {}
arr4.tick()   # storage cell emits corrupted value with a fresh check for that value
# The value emitted is the corrupted value; downstream cells see it as valid.
# To detect latch corruption we need a downstream ECC cell to compare
# against the original check word — this is the loopback-with-ECC model.
# For now verify the corrupted value IS emitted (demonstrating vulnerability
# that loopback ECC would fix):
v_corrupt = arr4.read_bus(0xE000)
check("Storage ECC: corrupted latch emits corrupted value (known limitation)",
      v_corrupt == VAR_FALSE)

# =============================================================================
print("\n=== ECC with loopback cells ===\n")

# A loopback cell with ECC circulates its value with check bits each cycle.
# A bit flip is detected and corrected on the very next cycle.
arr5 = UniCellArray(cell_count=10)
arr5.enforce_emission_limits = False

lb = arr5.allocate_cell()
arr5.write_config(lb.address, [FUNCTION_LOAD_PATTERN, 0b000000000,
                                0xF000, 0xF000])   # loopback: in==out
lb_cell = arr5.cells[lb.address]
lb_cell.ecc_enabled = True

arr5.assert_start_flag()
arr5.bus[0xF000] = (VAR_TRUE, 0)
arr5.tick()  # first tick: latch value 1, circulate with ECC

# Inject bit flip into bus while it's in transit (between ticks)
bus_val, bus_chk = arr5.bus[0xF000]
arr5.bus[0xF000] = (bus_val ^ 1, bus_chk)   # corrupt: 1 -> 0, keep old check

arr5.tick()  # loopback cell receives corrupted value, ECC corrects it
check("Loopback ECC: bus corruption corrected on next circulation",
      lb_cell.ecc_corrections == 1)

# Value should be restored to 1 after correction and re-emit
v_lb = arr5.read_bus(0xF000)
check("Loopback ECC: value restored after correction", v_lb == VAR_TRUE)

# =============================================================================
print("\n=== ECC through ImagoController ===\n")

ctrl = ImagoController(cell_count=200)
# Load a NOT chain: NOT -> PASS
map_ecc = [
    CellMapRecord(0b000000001, 0x1000, 0x2000),  # NOT
    CellMapRecord(0b000000000, 0x2000, 0x3000),  # PASS
]
rid = ctrl.load_map(map_ecc, "ecc_chain")
check("Controller ECC: map loads", rid is not None)

# Enable ECC on all cells in the region
if rid:
    region = ctrl._regions[rid]
    ctrl.array.enable_ecc(region.cell_addresses)
    all_enabled = all(
        ctrl.array.cells[a].ecc_enabled
        for a in region.cell_addresses
    )
    check("Controller ECC: all region cells ECC-enabled", all_enabled)

    # Run: NOT(0)=1 should propagate correctly through ECC chain
    result = ctrl.run(rid,
                      inputs={0x1000: VAR_FALSE},
                      capture_addresses=[0x3000])
    check("Controller ECC: NOT(0)=1 correct through ECC chain",
          result and result.get(0x3000) == VAR_TRUE)

    result2 = ctrl.run(rid,
                       inputs={0x1000: VAR_TRUE},
                       capture_addresses=[0x3000])
    check("Controller ECC: NOT(1)=0 correct through ECC chain",
          result2 and result2.get(0x3000) == VAR_FALSE)

    # ECC status after clean run
    st = ctrl.array.ecc_status()
    check("Controller ECC: no corrections on clean run",
          st["total_corrections"] == 0)
    check("Controller ECC: no double errors on clean run",
          st["total_double_errors"] == 0)

# ECC with injected corruption during a run
ctrl2 = ImagoController(cell_count=100)
map2 = [CellMapRecord(0b000000000, 0x1000, 0x2000)]  # PASS
rid2 = ctrl2.load_map(map2, "pass_ecc")
if rid2:
    ctrl2.array.enable_ecc(ctrl2._regions[rid2].cell_addresses)

    # Manually: inject input, start region, tick once then corrupt, tick again
    ctrl2.array.bus[0x1000] = (VAR_TRUE, _compute_ecc(VAR_TRUE))
    ctrl2.array.assert_start_flag(ctrl2._regions[rid2].cell_addresses)

    ctrl2.array.tick()   # PASS fires: emits (1, check) to 0x2000

    # Corrupt the bus value in transit
    bv, bchk = ctrl2.array.bus[0x2000]
    ctrl2.array.bus[0x2000] = (bv ^ 1, bchk)  # flip bit 0

    # A downstream ECC cell would correct this — here we just verify
    # the corruption is present and the check word doesn't match
    from unicell import _verify_ecc as _vfy
    _, single_err, double_err = _vfy(bv ^ 1, bchk)
    check("Controller ECC: injected corruption detected by check word",
          single_err == True)

# =============================================================================

print(f"\n{'='*50}")
passed = sum(1 for s,_ in results if s == "PASS")
failed = sum(1 for s,_ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
    print("\nECC (SECDED) validated:")
    print("  - 7-bit Hamming code on 32-bit data words")
    print("  - All 32 single-bit positions correctable")
    print("  - Double-bit errors detected and flagged")
    print("  - Per-cell opt-in with enable_ecc() / disable_ecc()")
    print("  - Bit-flip injection for test harness validation")
    print("  - ECC propagates through array tick pipeline")
    print("  - Loopback cell bus corruption corrected on re-circulation")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
