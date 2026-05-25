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

CELL = 0     # Physical cell ID 0 (valid on 8-cell iCEBreaker)
IN   = 0x10  # Logical input address
OUT  = 0x20  # Logical output address

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


    # ── Test 6: Exact replication of test_sync_wait approach ─────────────────
    print("\n--- Test 6: Exact test_sync_wait style (no SET_LOGICAL) ---")
    b.reset(); time.sleep(0.2)

    # Cell 0: default input=0, output=1, just RECONFIGURE
    import struct
    def mk_auth_data(auth, payload):
        return ((auth & 0xFF) << 24) | (payload & 0xFFFFFF)

    def mk_cfg(topo):
        w = topo & 0x3FF
        w |= 1 << 11  # start_flag
        return w

    cfg = mk_cfg(0x007)  # AND
    cmd_data = mk_auth_data(auth, cfg)
    print(f"  RECONFIGURE cell 0, cmd_data={hex(cmd_data)}")
    b._inject_raw(0x04, 0, cmd_data)  # CMD_RECONFIGURE to cell 0
    time.sleep(0.3)

    # Inject to address 0 (cell 0 default input)
    b._inject_raw(0x01, 0, 0xFF)  # DATA_WRITE addr=0 data=0xFF
    time.sleep(0.1)
    b._inject_raw(0x01, 0, 0xFF)  # second arrival
    r = b.wait_for_fire(2.0)
    print(f"  Result: {r} (expected fire at addr 1, data 0xFF)")

    # ── Test 7: What addresses are cells actually using? ──────────────────────
    print("\n--- Test 7: Status check ---")
    s = b.get_status()
    print(f"  Status: {s}")

    # ── Test 8: Step by step with raw TX and timing ───────────────────────────
    print("\n--- Test 8: Step by step raw TX ---")
    b.reset(); time.sleep(0.5)

    auth = int(sys.argv[2], 0)

    def mk_auth(auth, payload=0):
        return ((auth & 0xFF) << 24) | (payload & 0xFFFFFF)

    # Step 1: RECONFIGURE cell 0 with AND topology, start_flag=1
    cfg = 0x007 | (1 << 11)  # AND + start_flag
    b._inject_raw(0x04, 0, mk_auth(auth, cfg))
    time.sleep(0.1)
    print(f"  1. RECONFIGURE cell 0: {hex(mk_auth(auth, cfg))}")

    # Step 2: SET_OUTPUT_ADDR to 0x20
    b._inject_raw(0x03, 0, mk_auth(auth, 0x20))
    time.sleep(0.1)
    print(f"  2. SET_OUTPUT_ADDR cell 0 -> 0x20")

    # Step 3: Inject to address 0 (default input)
    b._inject_raw(0x01, 0, 0xFF)
    time.sleep(0.1)
    print(f"  3. DATA_WRITE addr=0 data=0xFF (first arrival)")
    b._inject_raw(0x01, 0, 0xFF)
    time.sleep(0.1)
    print(f"  4. DATA_WRITE addr=0 data=0xFF (second arrival)")

    r = b.wait_for_fire(2.0)
    print(f"  Result: {r} (expected fire at addr 0x20, data 0xFF)")

    # ── Test 9: SET_LOGICAL then inject ───────────────────────────────────────
    print("\n--- Test 9: RECONFIGURE + SET_LOGICAL + inject to new addr ---")
    b.reset(); time.sleep(0.5)

    b._inject_raw(0x04, 0, mk_auth(auth, cfg))  # RECONFIGURE
    time.sleep(0.1)
    b._inject_raw(0x0E, 0, mk_auth(auth, 0x10)) # SET_LOGICAL addr=0x10
    time.sleep(0.1)
    print(f"  SET_LOGICAL to 0x10")

    # inject to new logical addr
    b._inject_raw(0x01, 0x10, 0xFF)
    time.sleep(0.1)
    b._inject_raw(0x01, 0x10, 0xFF)
    r = b.wait_for_fire(2.0)
    print(f"  Result: {r} (expected fire at addr 1 still, data 0xFF)")
    b.disconnect()

if __name__ == "__main__":
    main()
