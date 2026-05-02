"""
test_addr_latch.py — Extended address latch tests

Tests:
  - GS_ADDR_LATCH constant exists in gate_states
  - UniCell addr_latch flag initialised False
  - Cell returns 4-tuple when addr_latch is set
  - 64-bit address correctly assembled from data + output_address
  - UniCellArray stores extended address in _extended_addresses
  - CommandInterface scope bits in Bus 1
  - build_bus1 / decode_bus1 with scope
  - set_addr_latch() configures bridge cell
  - resolve_extended_address() returns correct 64-bit address
  - Normal cells (addr_latch=False) unaffected — 3-tuple returned
  - All existing array operations unchanged
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from gate_states import GS_ADDR_LATCH, GS_PASS, GS_NOT
from unicell import UniCell
from unicell_array import UniCellArray
from command_interface import (
    build_bus1, decode_bus1, make_system_interface,
    _SCOPE_LOCAL, _SCOPE_SHORE, _SCOPE_EXTENDED,
    CMD_RECONFIGURE,
)
from controller import ImagoController

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    results.append(("PASS" if ok else "FAIL", name))
    if not ok:
        print(f"  [FAIL] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [PASS] {name}")


# =============================================================================
print("\n=== GS_ADDR_LATCH constant ===\n")
# =============================================================================

check("GS_ADDR_LATCH exists",          GS_ADDR_LATCH is not None)
check_eq("GS_ADDR_LATCH = bit 23",     GS_ADDR_LATCH, 1 << 23)
check_eq("GS_ADDR_LATCH hex",          GS_ADDR_LATCH, 0x00800000)

# Does not collide with existing flags
for name, val in [("GS_PASS", GS_PASS), ("GS_NOT", GS_NOT),
                   ("bit11_latch", 1<<11), ("bit31_bp", 1<<31)]:
    check(f"no collision with {name}", GS_ADDR_LATCH & val == 0)


# =============================================================================
print("\n=== UniCell addr_latch initialisation ===\n")
# =============================================================================

cell = UniCell(0x1000)
check("cell.addr_latch default False",     not cell.addr_latch)
check("cell.data default None",            cell.data is None)
check("cell.output_address default 0",     cell.output_address == 0)


# =============================================================================
print("\n=== Normal cell — 3-tuple return unchanged ===\n")
# =============================================================================

normal = UniCell(0x2000)
normal.start_flag     = True
normal.gate_state     = GS_PASS
normal.input_address  = 0x2000
normal.output_address = 0x3000
normal.data           = 1

result = normal.tick()
check("normal cell: result is not None",    result is not None)
check_eq("normal cell: tuple length",       len(result), 3)
output_addr, val, chk = result
check_eq("normal cell: output_addr",        output_addr, 0x3000)
check_eq("normal cell: value",              val, 1)


# =============================================================================
print("\n=== addr_latch cell — 4-tuple return ===\n")
# =============================================================================

bridge = UniCell(0x4000)
bridge.start_flag     = True
bridge.gate_state     = GS_PASS
bridge.addr_latch     = True
bridge.input_address  = 0x4000
bridge.output_address = 0xABCD1234        # lower 32 bits
bridge._config_upper   = 0x00000003        # dedicated upper register
bridge.data           = 1                  # bus input (NOR compute)

result4 = bridge.tick()
check("addr_latch cell: result not None",  result4 is not None)
check_eq("addr_latch: tuple length",       len(result4), 4)

output_addr, val, chk, full_addr = result4
check_eq("addr_latch: output_addr (lower)", output_addr, 0xABCD1234)
check_eq("addr_latch: full 64-bit addr",
          full_addr, (0x00000003 << 32) | 0xABCD1234)

# Verify full_addr assembles correctly
expected_64 = (3 << 32) | 0xABCD1234
check_eq("addr_latch: 64-bit value correct", full_addr, expected_64)
check("addr_latch: upper 32 == 3",          (full_addr >> 32) == 3)
check("addr_latch: lower 32 == 0xABCD1234", (full_addr & 0xFFFFFFFF) == 0xABCD1234)


# =============================================================================
print("\n=== UniCellArray extended address storage ===\n")
# =============================================================================

arr = UniCellArray(cell_count=100)
arr.enforce_emission_limits = False

# Configure a bridge cell with addr_latch
# The cell must have data pre-loaded (upper address) before tick
b_addr = 0x5000
bridge2 = UniCell(b_addr)
bridge2.start_flag     = True
bridge2.gate_state     = GS_PASS
bridge2.addr_latch     = True
bridge2.input_address  = b_addr
bridge2.output_address = 0x00200000   # lower 32: local address on remote stack
bridge2._config_upper   = 0x00000007   # dedicated upper register: stack 7

arr.cells[b_addr] = bridge2
arr.bus[b_addr]   = (1, 0)   # trigger the cell (data flows through GS_PASS)
arr._armed.add(b_addr)
arr.tick_drain()   # compute + drain so _extended_addresses is populated

# Array should have stored the extended address
check("array: _extended_addresses populated",
      b_addr in arr._extended_addresses)
if b_addr in arr._extended_addresses:
    ext = arr._extended_addresses[b_addr]
    check_eq("array: ext upper correct",
              ext >> 32, 0x00000007)
    check_eq("array: ext lower correct",
              ext & 0xFFFFFFFF, 0x00200000)
    check_eq("array: full ext address",
              ext, (7 << 32) | 0x00200000)


# =============================================================================
print("\n=== Bus 1 scope bits ===\n")
# =============================================================================

check_eq("_SCOPE_LOCAL",    _SCOPE_LOCAL,    0b00)
check_eq("_SCOPE_SHORE",    _SCOPE_SHORE,    0b01)
check_eq("_SCOPE_EXTENDED", _SCOPE_EXTENDED, 0b10)

# build_bus1 with scope
b1_local    = build_bus1(CMD_RECONFIGURE, auth=0x7FF, scope=_SCOPE_LOCAL)
b1_shore    = build_bus1(CMD_RECONFIGURE, auth=0x7FF, scope=_SCOPE_SHORE)
b1_extended = build_bus1(CMD_RECONFIGURE, auth=0x7FF, scope=_SCOPE_EXTENDED)

# Scope bits at positions 16-17
check("b1_local:    scope bits = 00",
      ((b1_local >> 16) & 0b11) == _SCOPE_LOCAL)
check("b1_shore:    scope bits = 01",
      ((b1_shore >> 16) & 0b11) == _SCOPE_SHORE)
check("b1_extended: scope bits = 10",
      ((b1_extended >> 16) & 0b11) == _SCOPE_EXTENDED)

# decode_bus1 round-trips scope
cmd_l, auth_l, raw_l, scope_l, _hs_l = decode_bus1(b1_local)
check_eq("decode: scope LOCAL",    scope_l, _SCOPE_LOCAL)

cmd_s, auth_s, raw_s, scope_s, _hs_s = decode_bus1(b1_shore)
check_eq("decode: scope SHORE",    scope_s, _SCOPE_SHORE)

cmd_e, auth_e, raw_e, scope_e, _hs_e = decode_bus1(b1_extended)
check_eq("decode: scope EXTENDED", scope_e, _SCOPE_EXTENDED)

# Backward compat: scope=0 (LOCAL) is default — same as before
b1_default = build_bus1(CMD_RECONFIGURE, auth=0x7FF)
cmd_d, auth_d, raw_d, scope_d, _hs_d = decode_bus1(b1_default)
check_eq("decode: default scope = LOCAL", scope_d, _SCOPE_LOCAL)
check_eq("decode: cmd unchanged",         cmd_d, CMD_RECONFIGURE)
check_eq("decode: auth unchanged",        auth_d, 0x7FF & 0b11111111111)


# =============================================================================
print("\n=== CommandInterface set_addr_latch ===\n")
# =============================================================================

ctrl = ImagoController(cell_count=500)
ci   = make_system_interface(ctrl, auth_token=0x5A5)

# Allocate a bridge cell
bridge_addr = 0x6000
# Load a simple cell at that address
from controller import CellMapRecord
ctrl.load_map([CellMapRecord(GS_PASS, bridge_addr, 0x7000)], "test_bridge")

lower = 0x00200000   # local address on destination stack
upper = 0x0000000A   # stack identifier = 10

ok = ci.set_addr_latch(bridge_addr, lower, upper)
check("set_addr_latch: returns True",      ok is not False)

# Verify extended address
ext = ci.resolve_extended_address(bridge_addr)
check("resolve: ext != 0",                 ext != 0)
check_eq("resolve: lower 32 correct",      ext & 0xFFFFFFFF, lower)
check_eq("resolve: upper 32 correct",      (ext >> 32) & 0xFFFFFFFF, upper)
check_eq("resolve: full 64-bit correct",   ext, (upper << 32) | lower)
check("resolve: full_addr > 32-bit",       ext > 0xFFFFFFFF)


# =============================================================================
print("\n=== Data bus unchanged — 32-bit throughout ===\n")
# =============================================================================

# Multiple normal cells fire and bus is still 32-bit
arr2 = UniCellArray(cell_count=50)
arr2.enforce_emission_limits = False

for i in range(5):
    c = UniCell(0x8000 + i)
    c.start_flag     = True
    c.gate_state     = GS_PASS
    c.addr_latch     = False   # normal compute cell
    c.input_address  = 0x8000 + i
    c.output_address = 0x9000 + i
    c.data           = i
    arr2.cells[0x8000 + i] = c
    arr2.bus[0x8000 + i]   = (i, 0)
    arr2._armed.add(0x8000 + i)

arr2.tick_drain()   # compute + drain so results are on bus

# All outputs on normal 32-bit addresses
for i in range(5):
    out_addr = 0x9000 + i
    check(f"normal cell {i}: in 32-bit bus",
          out_addr in arr2.bus)

# No extended addresses for non-latch cells
check("non-latch: no extended_addresses",
      len(arr2._extended_addresses) == 0)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
