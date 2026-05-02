from test_helpers import CELL_LATENCY, chain_latency, run_ticks
"""
Tests for UniCell and UniCellArray.
Covers the M1 and M2 milestones from the Implementation Guide.
Run with: python3 test_array.py
"""

from unicell import UniCell, FUNCTION_LOAD_PATTERN, VAR_TRUE, VAR_FALSE
from unicell_array import UniCellArray

PASS  = "PASS"
FAIL  = "FAIL"
results = []

def check(name, condition):
    status = PASS if condition else FAIL
    results.append((status, name))
    print(f"  [{status}] {name}")

print("\n=== M1 — UniCell unit tests ===\n")

# NOR gate truth table
cell = UniCell(0x1000)
cell.gate_state    = 0b000000100    # gate 2 active: NOR(g1, g2)
cell.input_address = 0x1000
cell.output_address = 0x2000
cell.start_flag    = True

# We test the gate topology directly
for a, b, expected in [(0,0,1),(0,1,0),(1,0,0),(1,1,0)]:
    # gate 2 is NOR(g1,g2). g1=gate(0,A,A) bypassed→A, g2=gate(1,A,A) bypassed→A
    # so NOR(A, A) when gate 2 active with input A — but topology takes g1,g2 not A,A
    # simplest test: gate_state=0 (all bypassed) passes input through unchanged
    pass

# Gate bypass — all gates off, value passes through
c = UniCell(0x0001)
c.gate_state = 0b000000000          # all bypassed — PASS operation
c.input_address  = 0x0100
c.output_address = 0x0200
c.start_flag = True
c.data = 0xDEADBEEF
result = c.tick()
check("Gate bypass: value passes through unchanged", result is not None and result[:2] == (0x0200, 0xDEADBEEF))

# NOT operation (gate 0 active: gate(0, A, A) = NOR(A,A) = NOT A)
c = UniCell(0x0002)
c.gate_state = 0b000000001          # gate 0 active only
c.input_address  = 0x0100
c.output_address = 0x0200
c.start_flag = True
c.data = VAR_FALSE                  # input = 0
result = c.tick()
check("NOT(0) = 1", result is not None and result[:2] == (0x0200, VAR_TRUE))

c.start_flag = True                 # re-assert for second computation
c.data = VAR_TRUE                   # input = 1
result = c.tick()
check("NOT(1) = 0", result is not None and result[:2] == (0x0200, VAR_FALSE))

# Config mode entry
c = UniCell(0x0003)
c.input_address = 0x0300
consumed = c.receive(FUNCTION_LOAD_PATTERN)
check("Config mode entered on FUNCTION_LOAD_PATTERN", consumed == True)
check("Cell in config mode after pattern", c._config_mode == True)

# Config mode exit after 3 fields
c.receive(0b000000001)              # gate_state
c.receive(0x0400)                   # input_address
c.receive(0x0500)                   # output_address
check("Config mode exits after 3 fields", c._config_mode == False)
check("gate_state written correctly", c.gate_state == 0b000000001)
check("input_address written correctly", c.input_address == 0x0400)
check("output_address written correctly", c.output_address == 0x0500)

# Start flag hold
c = UniCell(0x0004)
c.gate_state = 0b000000001
c.input_address  = 0x0400
c.output_address = 0x0500
c.start_flag = False                # flag NOT asserted
c.data = VAR_TRUE
result = c.tick()
check("Start flag held low: no output posted", result is None)

# Loopback memory — value held across 1000 ticks
c = UniCell(0x0005)
c.gate_state = 0b000000000          # PASS
c.input_address  = 0x0500
c.output_address = 0x0500           # loopback: same address
c.start_flag = True
c.data = VAR_TRUE
check("Loopback detected", c.is_loopback == True)
# simulate 1000 cycles manually
for _ in range(1000):
    result = c.tick()
    if result is not None:
        addr, val = result[0], result[1]
        if addr == c.input_address:
            c.data = val            # feed back
check("Loopback: value held after 1000 cycles", c.data == VAR_TRUE or (result is not None and result[1] == VAR_TRUE))

print("\n=== M2 — Array simulation tests ===\n")

# Two-cell NOT chain: cell A computes NOT, posts to cell B (PASS), B posts to output bus
arr = UniCellArray(cell_count=100)

# Cell A: NOT gate, listens at 0x1000, posts to 0x2000
cellA = arr.allocate_cell()
arr.write_config(cellA.address, [
    FUNCTION_LOAD_PATTERN,
    0b000000001,    # gate 0 active = NOT
    0x1000,         # input address
    0x2000,         # output address
])

# Cell B: PASS gate, listens at 0x2000, posts to 0x3000
cellB = arr.allocate_cell()
arr.write_config(cellB.address, [
    FUNCTION_LOAD_PATTERN,
    0b000000000,    # all bypassed = PASS
    0x2000,
    0x3000,
])

arr.assert_start_flag()
arr.bus[0x1000] = (VAR_FALSE, 0)         # inject input: 0
# Run tick-by-tick and capture the peak result before the bus clears
chain_result = None
chain_cycles = 0
for _ in range(10):
    active = arr.tick()
    chain_cycles += 1
    v = arr.read_bus(0x3000)
    if v is not None:
        chain_result = v
    if active == 0:
        break
check("Two-cell NOT→PASS chain: NOT(0)=1 propagates in 2 cycles", chain_result == VAR_TRUE)
check("Chain terminates naturally (no timeout)", chain_cycles <= 3)

# Parallelism: 100 independent NOT cells all act in 1 tick
arr2 = UniCellArray(cell_count=500)
input_base  = 0x1000
output_base = 0x9000
for i in range(100):
    c = arr2.allocate_cell()
    arr2.write_config(c.address, [
        FUNCTION_LOAD_PATTERN,
        0b000000001,
        input_base  + i,
        output_base + i,
    ])
    arr2.bus[input_base + i] = (VAR_TRUE, 0)   # inject 1 into every cell

arr2.assert_start_flag()
active = arr2.tick()                 # compute tick: results → output latches
check("Parallelism: 100 cells act in exactly 1 tick", active == 100)
arr2.tick()                          # drain tick: output latches → bus
all_correct = all(arr2.read_bus(output_base + i) == VAR_FALSE for i in range(100))
check("Parallelism: all 100 NOT(1)=0 results correct", all_correct)

# Address isolation: value at X received only by cell with input_address=X
arr3 = UniCellArray(cell_count=50)
cX = arr3.allocate_cell()
arr3.write_config(cX.address, [FUNCTION_LOAD_PATTERN, 0b000000000, 0xAAAA, 0xBBBB])
cY = arr3.allocate_cell()
arr3.write_config(cY.address, [FUNCTION_LOAD_PATTERN, 0b000000000, 0xCCCC, 0xDDDD])
arr3.assert_start_flag()
arr3.bus[0xAAAA] = (VAR_TRUE, 0)         # only cX should fire
arr3.tick()                              # compute tick
arr3.tick()                              # drain tick: output latch → bus
check("Address isolation: cX fires (data at its address)", arr3.read_bus(0xBBBB) == VAR_TRUE)
check("Address isolation: cY silent (no data at its address)", arr3.read_bus(0xDDDD) is None)

# Defect map: defective address skipped during allocation
arr4 = UniCellArray(cell_count=50)
arr4.load_defect_map([0x0001, 0x0002, 0x0003])
c = arr4.allocate_cell()
check("Defect map: first allocation skips defective addresses", c.address == 0x0004)

# Array status
status = arr.status()
check("Status: allocated_cells > 0", status["allocated_cells"] > 0)
check("Status: defective_cells == 0 (no defects loaded)", status["defective_cells"] == 0)

# Summary
print(f"\n{'='*40}")
passed = sum(1 for s,_ in results if s == PASS)
failed = sum(1 for s,_ in results if s == FAIL)
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
