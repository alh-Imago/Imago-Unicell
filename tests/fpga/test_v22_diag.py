"""
test_v22_diag.py — Step by step diagnostic for v2.2 cell boot + preset

Usage: python tests/fpga/test_v22_diag.py COM4 0xA5
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../fpga'))

from fpga_bridge import (
    FPGABridge, make_cmd,
    CMD_RECONFIGURE, CMD_SET_LOGICAL, CMD_SET_OUTPUT_ADDR, CMD_RELEASE,
    CMD_DATA_WRITE, CMD_TOPO_AND, CMD_TOPO_AND_COLD,
    TOPO_AND, build_config_word
)

CELL = 0x100
IN   = 0x200
OUT  = 0x300

def main():
    port = sys.argv[1]
    auth = int(sys.argv[2], 0)
    b = FPGABridge(port=port, auth_token=auth)
    if not b.connect(): sys.exit(1)

    print(f"\nAuth token: {hex(auth)}")
    print(f"Cell ID:    {hex(CELL)}")
    print(f"Input addr: {hex(IN)}")
    print(f"Output addr:{hex(OUT)}")

    # ── Test 1: Does basic v2.1 AND gate still work? ──────────────────────────
    print("\n--- Test 1: Basic AND via CMD_RECONFIGURE (v2.1 style) ---")
    b.reset(); time.sleep(0.2)

    cfg = build_config_word(topology=TOPO_AND)
    cmd_data = make_cmd(auth=auth, payload=cfg)
    print(f"  RECONFIGURE cmd_data: {hex(cmd_data)}")
    b._inject_raw(CMD_RECONFIGURE, CELL, cmd_data)
    time.sleep(0.01)

    b._inject_raw(CMD_SET_LOGICAL, CELL, make_cmd(auth=auth, payload=IN))
    time.sleep(0.01)
    b._inject_raw(CMD_SET_OUTPUT_ADDR, CELL, make_cmd(auth=auth, payload=OUT))
    time.sleep(0.01)
    b._inject_raw(CMD_RELEASE, CELL, make_cmd(auth=auth))
    time.sleep(0.05)

    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    r = b.wait_for_fire(2.0)
    print(f"  Result: {r} (expected (0x{OUT:x}, 0xff))")

    # ── Test 2: Same but using boot_cell() ────────────────────────────────────
    print("\n--- Test 2: boot_cell() then inject ---")
    b.reset(); time.sleep(0.2)
    b.boot_cell(CELL, topology=TOPO_AND, input_addr=IN, output_addr=OUT)
    time.sleep(0.1)
    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    r = b.wait_for_fire(2.0)
    print(f"  Result: {r} (expected (0x{OUT:x}, 0xff))")

    # ── Test 3: boot_cell then CMD_TOPO_AND preset ───────────────────────────
    print("\n--- Test 3: boot_cell + CMD_TOPO_AND preset ---")
    b.reset(); time.sleep(0.2)
    b.boot_cell(CELL, topology=TOPO_AND, input_addr=IN, output_addr=OUT)
    time.sleep(0.1)

    # Send preset to logical address IN
    preset_data = make_cmd(auth=auth)
    print(f"  CMD_TOPO_AND ({hex(CMD_TOPO_AND)}) to addr {hex(IN)}, data {hex(preset_data)}")
    b._inject_raw(CMD_TOPO_AND, IN, preset_data)
    time.sleep(0.05)

    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    r = b.wait_for_fire(2.0)
    print(f"  Result: {r} (expected (0x{OUT:x}, 0xff))")

    # ── Test 4: check if cell_inst.input_address is accessible ───────────────
    print("\n--- Test 4: CMD_TOPO_AND to physical CELL addr ---")
    b.reset(); time.sleep(0.2)
    b.boot_cell(CELL, topology=TOPO_AND, input_addr=IN, output_addr=OUT)
    time.sleep(0.1)

    # Try targeting physical ID instead
    b._inject_raw(CMD_TOPO_AND, CELL, make_cmd(auth=auth))
    time.sleep(0.05)

    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    r = b.wait_for_fire(2.0)
    print(f"  Result: {r} (expected (0x{OUT:x}, 0xff))")

    # ── Test 5: broadcast preset (no address filter) ─────────────────────────
    print("\n--- Test 5: broadcast CMD_TOPO_AND (addr=0) ---")
    b.reset(); time.sleep(0.2)
    b.boot_cell(CELL, topology=TOPO_AND, input_addr=IN, output_addr=OUT)
    time.sleep(0.1)

    b._inject_raw(CMD_TOPO_AND, 0, make_cmd(auth=auth))
    time.sleep(0.05)

    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    b._inject_raw(CMD_DATA_WRITE, IN, 0xFF)
    r = b.wait_for_fire(2.0)
    print(f"  Result: {r} (expected (0x{OUT:x}, 0xff))")

    b.disconnect()

if __name__ == "__main__":
    main()
