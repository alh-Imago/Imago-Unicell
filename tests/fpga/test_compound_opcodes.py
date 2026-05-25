"""
test_compound_opcodes.py — iCEBreaker validation for v2.2 compound opcodes

Tests:
  1.  Topology presets  — CMD_TOPO_AND, CMD_TOPO_OR etc.
  2.  Cold vs armed     — cold stays disarmed, armed fires
  3.  Latch disable     — latch_a_dis=PASS(B), latch_b_dis=PASS(A)
  4.  Cell state        — CMD_CLEAR_ARRIVED, CMD_RESET_CELL, CMD_SWAP_AB
  5.  SET_TOPO          — topology only, no other flags changed
  6.  Nibble mask       — partial word operations

Usage:
  python tests/fpga/test_compound_opcodes.py COM4 0xA5
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../fpga'))

from fpga_bridge import (
    FPGABridge,
    CMD_TOPO_AND, CMD_TOPO_AND_COLD,
    CMD_TOPO_OR,  CMD_TOPO_OR_COLD,
    CMD_TOPO_NOT_A, CMD_TOPO_PASS_A, CMD_TOPO_PASS_B,
    CMD_TOPO_XOR, CMD_TOPO_NOR, CMD_TOPO_NAND,
    CMD_TOPO_ZERO, CMD_TOPO_ONE,
    CMD_CLEAR_ARRIVED, CMD_RESET_CELL, CMD_SWAP_AB, CMD_SET_TOPO,
    TOPO_AND, TOPO_OR, TOPO_XOR,
    make_cmd
)

CELL  = 0x100   # physical cell ID
IN    = 0x200   # input address
OUT   = 0x300   # output address

passed = 0
failed = 0

def check(label, got, expected):
    global passed, failed
    ok = (got == expected)
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}: got {hex(got) if isinstance(got,int) else got} "
          f"expected {hex(expected) if isinstance(expected,int) else expected}")
    if ok: passed += 1
    else:  failed += 1
    return ok


def test_topology_preset(b, name, opcode, val_a, val_b, expected):
    """Boot with preset opcode, inject two values, check output."""
    b.reset()
    time.sleep(0.1)
    b.boot_cell(CELL, input_addr=IN, output_addr=OUT)
    b.configure_gate(CELL, opcode)
    time.sleep(0.05)
    b.inject(IN, val_a)   # first arrival
    b.inject(IN, val_b)   # second arrival — fires
    r = b.wait_for_fire(1.0)
    got = r[1] if r else -1
    check(name, got, expected)


def test_cold_stays_disarmed(b):
    """CMD_TOPO_AND_COLD should configure but not arm."""
    b.reset(); time.sleep(0.1)
    b.boot_cell(CELL, input_addr=IN, output_addr=OUT)
    b.configure_gate(CELL, CMD_TOPO_AND_COLD)
    time.sleep(0.05)
    b.inject(IN, 0xFF)
    b.inject(IN, 0xFF)
    r = b.wait_for_fire(0.5)
    check("COLD stays disarmed", r, None)


def test_latch_a_disable(b):
    """latch_a_dis=True — live value passes straight through as PASS(B)."""
    b.reset(); time.sleep(0.1)
    b.boot_cell(CELL, input_addr=IN, output_addr=OUT)
    # Configure AND with latch_A disabled — should behave as PASS(B)
    b.configure_gate(CELL, CMD_TOPO_AND, latch_a=True)
    time.sleep(0.05)
    # Single arrival should fire immediately (no A latch needed)
    b.inject(IN, 0xDEADBEEF)
    r = b.wait_for_fire(1.0)
    got = r[1] if r else -1
    check("latch_A_dis=PASS(B) single arrival fires", got, 0xDEADBEEF)


def test_latch_b_disable(b):
    """latch_b_dis=True — stored A value rebroadcast (PASS(A) effect)."""
    b.reset(); time.sleep(0.1)
    b.boot_cell(CELL, input_addr=IN, output_addr=OUT)
    # First load A via normal arrival
    b.configure_gate(CELL, CMD_TOPO_AND_COLD)  # configure AND, disarmed
    b._inject_raw(0x06, CELL, make_cmd(auth=b.auth_token))  # CMD_RELEASE
    time.sleep(0.05)
    b.inject(IN, 0xCAFEBABE)  # first arrival — stores A
    time.sleep(0.05)
    # Now reconfigure with latch_B disabled
    b.configure_gate(CELL, CMD_TOPO_PASS_A, latch_b=True)
    time.sleep(0.05)
    # Any arrival should rebroadcast stored A
    b.inject(IN, 0x00000000)
    r = b.wait_for_fire(1.0)
    got = r[1] if r else -1
    check("latch_B_dis=PASS(A) rebroadcasts stored A", got, 0xCAFEBABE)


def test_clear_arrived(b):
    """CMD_CLEAR_ARRIVED resets first arrival without reconfiguring."""
    b.reset(); time.sleep(0.1)
    b.boot_cell(CELL, input_addr=IN, output_addr=OUT)
    b.configure_gate(CELL, CMD_TOPO_AND)
    time.sleep(0.05)
    b.inject(IN, 0xFF)         # first arrival — stored
    time.sleep(0.05)
    b.clear_arrived(CELL)      # clear it
    time.sleep(0.05)
    b.inject(IN, 0xFF)         # first arrival again — should store not fire
    b.inject(IN, 0xFF)         # second arrival — fires AND(0xFF,0xFF)=0xFF
    r = b.wait_for_fire(1.0)
    got = r[1] if r else -1
    check("CLEAR_ARRIVED resets counter", got, 0xFF)


def test_reset_cell(b):
    """CMD_RESET_CELL clears state and rearms."""
    b.reset(); time.sleep(0.1)
    b.boot_cell(CELL, input_addr=IN, output_addr=OUT)
    b.configure_gate(CELL, CMD_TOPO_AND)
    time.sleep(0.05)
    b.inject(IN, 0xAA)         # first arrival
    b.reset_cell(CELL)         # reset — clears arrived, rearms
    time.sleep(0.05)
    b.inject(IN, 0x55)         # fresh first arrival after reset
    b.inject(IN, 0xFF)         # second arrival — AND(0x55, 0xFF) = 0x55
    r = b.wait_for_fire(1.0)
    got = r[1] if r else -1
    check("RESET_CELL clears and rearms", got, 0x55)


def test_set_topo(b):
    """CMD_SET_TOPO changes topology without touching other flags."""
    b.reset(); time.sleep(0.1)
    b.boot_cell(CELL, input_addr=IN, output_addr=OUT)
    b.configure_gate(CELL, CMD_TOPO_AND)
    time.sleep(0.05)
    # Change to OR without reconfiguring
    b.set_topology(CELL, TOPO_OR)
    time.sleep(0.05)
    b.inject(IN, 0xF0)
    b.inject(IN, 0x0F)
    r = b.wait_for_fire(1.0)
    got = r[1] if r else -1
    check("SET_TOPO changes to OR: 0xF0|0x0F=0xFF", got, 0xFF)


def test_nibble_mask(b):
    """Nibble mask — partial word operation."""
    b.reset(); time.sleep(0.1)
    b.boot_cell(CELL, input_addr=IN, output_addr=OUT)
    b.configure_gate(CELL, CMD_TOPO_PASS_A)
    time.sleep(0.05)
    # Inject with upper nibble mask only (bit7 = nibble7 = bits[31:28])
    b.inject(IN, 0xABCD1234, mask=0b10000000)  # only update upper nibble
    r = b.wait_for_fire(1.0)
    got = r[1] if r else -1
    # Lower nibbles should be 0, upper nibble should be 0xA
    check("Nibble mask upper nibble only", got & 0xF0000000, 0xA0000000)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <port> <auth_hex>")
        sys.exit(1)

    port = sys.argv[1]
    auth = int(sys.argv[2], 0)

    b = FPGABridge(port=port, auth_token=auth)
    if not b.connect():
        sys.exit(1)

    print("\n=== Topology Preset Tests ===")
    test_topology_preset(b, "AND: 0xF0 & 0x0F = 0x00",
                         CMD_TOPO_AND, 0xF0, 0x0F, 0x00)
    test_topology_preset(b, "AND: 0xFF & 0xFF = 0xFF",
                         CMD_TOPO_AND, 0xFF, 0xFF, 0xFF)
    test_topology_preset(b, "OR:  0xF0 | 0x0F = 0xFF",
                         CMD_TOPO_OR,  0xF0, 0x0F, 0xFF)
    test_topology_preset(b, "XOR: 0xFF ^ 0xFF = 0x00",
                         CMD_TOPO_XOR, 0xFF, 0xFF, 0x00)
    test_topology_preset(b, "NOR: ~(0|0)     = 0xFFFFFFFF",
                         CMD_TOPO_NOR, 0x00, 0x00, 0xFFFFFFFF)
    test_topology_preset(b, "NOT: ~0xAAAAAAAA = 0x55555555",
                         CMD_TOPO_NOT_A, 0xAAAAAAAA, 0xAAAAAAAA, 0x55555555)
    test_topology_preset(b, "ZERO: always 0",
                         CMD_TOPO_ZERO, 0xFF, 0xFF, 0x00)
    test_topology_preset(b, "ONE:  always 0xFFFFFFFF",
                         CMD_TOPO_ONE,  0x00, 0x00, 0xFFFFFFFF)

    print("\n=== Cold/Armed Tests ===")
    test_cold_stays_disarmed(b)

    print("\n=== Latch Disable Tests ===")
    test_latch_a_disable(b)
    test_latch_b_disable(b)

    print("\n=== Cell State Control Tests ===")
    test_clear_arrived(b)
    test_reset_cell(b)
    test_set_topo(b)

    print("\n=== Nibble Mask Tests ===")
    test_nibble_mask(b)

    print(f"\n{'='*40}")
    total = passed + failed
    print(f"Results: {passed}/{total} PASS  {failed}/{total} FAIL")
    b.disconnect()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
