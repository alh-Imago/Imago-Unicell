#!/usr/bin/env python3
"""
issp_loader.py — Reusable ICM loader for the Arria 10 fabric over JTAG/ISSP.

Reuses the existing ICM JSON format ({records:[{gs,in,out,init}]}) and the
repo's own command encoder (command_interface.build_cmd_bus) as the single
source of truth. Emits a quartus_stp Tcl harness built on the uc_* primitives
from issp_unicell.tcl.

CORRECTED for the v2.3 silicon RECONFIGURE encoding (verified against
fpga/verilog/unicell.v): cmd_data is a COMPACT payload, NOT the cmd_latch
register layout. The old UART test's mk_cfg (start_flag at bit 22) does NOT
arm a v2.3 cell — start_flag is read from cmd_data[11].
"""
import json, sys, os
sys.path.insert(0, "/home/claude/Imago-Unicell")
from command_interface import (build_cmd_bus,
                               CMD_BOOT_COMMIT, CMD_SET_OUTPUT_ADDR,
                               CMD_RECONFIGURE, CMD_ARRAY_RESET, CMD_DATA_WRITE)

# topology bits (one-hot NOR selection) — from unicell.v preset table / gate_states.py
TOPOLOGY = {
    "PASS": 0x000, "PASS_A": 0x000, "PASS_B": 0x02C,
    "NOT": 0x001, "NOR": 0x004, "AND": 0x007, "OR": 0x024,
    "NAND": 0x027, "XNOR": 0x03C, "XOR": 0x0BC,
    "ZERO": 0x030, "ONE": 0x0B0,
}

def pack_reconfigure(topology, start_flag=1, auth_mask=0, one_shot=0,
                     latch_in=0, latch_A_dis=0, latch_B_dis=0,
                     invert_out=0, dtype=0, edge_mode=0):
    """v2.3 CMD_RECONFIGURE cmd_data payload (compact). Verified vs unicell.v:
       [9:0]=topology [10]=edge [11]=start [12]=latchA_dis [13]=latchB_dis
       [15:14]=dtype [16]=invert [17]=latch_in ... [30:23]=auth_mask."""
    w  = (topology   & 0x3FF)
    w |= (edge_mode  & 1) << 10
    w |= (start_flag & 1) << 11
    w |= (latch_A_dis& 1) << 12
    w |= (latch_B_dis& 1) << 13
    w |= (dtype      & 3) << 14
    w |= (invert_out & 1) << 16
    w |= (latch_in   & 1) << 17
    w |= (one_shot   & 1) << 21
    w |= (auth_mask  & 0xFF) << 23
    return w & 0xFFFFFFFF

def boot_commit_data(input_addr, auth_mask, group=0):
    """CMD_BOOT_COMMIT cmd_data: [15:0]=logical addr [23:16]=auth_mask [31:24]=group."""
    return (input_addr & 0xFFFF) | ((auth_mask & 0xFF) << 16) | ((group & 0xFF) << 24)

def config_commands(record, auth):
    """Return [(label, cmd_bus, cmd_data)] to load ONE cell (broadcast).
       Sequence: BOOT_COMMIT -> SET_OUTPUT_ADDR -> RECONFIGURE."""
    topo = TOPOLOGY[record["gs"]] if isinstance(record["gs"], str) else (record["gs"] & 0x3FF)
    in_a = record["in"] & 0xFFFF
    out  = record["out"] & 0xFFFF
    cmds = []
    # BOOT_COMMIT — no auth needed (auth_boot true while auth_mask==0); clears physical_mode
    cmds.append(("BOOT_COMMIT",
                 build_cmd_bus(CMD_BOOT_COMMIT),
                 boot_commit_data(in_a, auth)))
    # SET_OUTPUT_ADDR — auth now required (auth_mask just set to `auth`)
    cmds.append(("SET_OUTPUT_ADDR",
                 build_cmd_bus(CMD_SET_OUTPUT_ADDR, auth=auth),
                 out))
    # RECONFIGURE — compact payload, re-asserts auth_mask, arms the cell
    cmds.append(("RECONFIGURE",
                 build_cmd_bus(CMD_RECONFIGURE, auth=auth),
                 pack_reconfigure(topo, start_flag=1, auth_mask=auth)))
    return cmds

def make_inject_word(addr, payload12, nibbles):
    """Build the single 32-bit DATA_WRITE word for the Arria 10 ISSP path.
       top_arria10.v: bus_addr=cpu_data[31:16], bus_data=cpu_data(full),
                      shift_nibbles=cpu_data[3:0].
       So address, value and shift count SHARE one word:
         [31:16]=addr  [15:4]=free payload  [3:0]=nibble count."""
    return ((addr & 0xFFFF) << 16) | ((payload12 & 0xFFF) << 4) | (nibbles & 0xF)

def inject_cmd(addr, payload12, nibbles, shift_in=True):
    """Return (cpu_bus, cpu_data) for one uc_cmd that performs a (shifted) inject."""
    cpu_bus  = build_cmd_bus(CMD_DATA_WRITE, shift_in_en=(shift_in and nibbles > 0))
    cpu_data = make_inject_word(addr, payload12, nibbles)
    return cpu_bus, cpu_data

if __name__ == "__main__":
    icm = json.load(open("shift_pass.icm"))
    AUTH = 0xA5
    rec = icm["records"][0]
    print(f"ICM: {icm['name']}  ({len(icm['records'])} cell)")
    print("\n--- v2.3 CONFIG command stream (broadcast, correct encoding) ---")
    for label, cb, cd in config_commands(rec, AUTH):
        print(f"  uc_cmd 0x{cb:08X} 0x{cd:08X}   ; {label}")

    print("\n--- decode-check RECONFIGURE payload arms a PASS cell ---")
    rc = pack_reconfigure(TOPOLOGY["PASS"], start_flag=1, auth_mask=AUTH)
    print(f"  reconfigure cmd_data = 0x{rc:08X}")
    print(f"    topology[9:0]   = 0x{rc & 0x3FF:03X}  (PASS=0x000)  {'OK' if (rc&0x3FF)==0 else 'BAD'}")
    print(f"    start_flag[11]  = {(rc>>11)&1}            {'OK (armed)' if (rc>>11)&1 else 'BAD (not armed)'}")
    print(f"    auth_mask[30:23]= 0x{(rc>>23)&0xFF:02X}        {'OK' if ((rc>>23)&0xFF)==AUTH else 'BAD'}")
    print(f"    one_shot[21]    = {(rc>>21)&1}")

    print("\n--- INJECT words for the shift test (Arria 10 single-word encoding) ---")
    A = 0x0100  # cell input_address; inject word top 16 bits MUST equal this
    for payload in (0x000, 0x234, 0xABC):
        cb, cd = inject_cmd(A, payload, nibbles=1, shift_in=True)
        exp = (cd << 4) & 0xFFFFFFFF
        print(f"  uc_cmd 0x{cb:08X} 0x{cd:08X}   ; inject W=0x{cd:08X} (addr=0x{A:04X}, n=1) -> expect 0x{exp:08X}")
    print("  control (no shift):")
    cb, cd = inject_cmd(A, 0x234, nibbles=0, shift_in=False)
    print(f"  uc_cmd 0x{cb:08X} 0x{cd:08X}   ; inject W=0x{cd:08X} no shift -> expect 0x{cd:08X}")
