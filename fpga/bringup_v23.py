"""
bringup_v23.py — v2.3 iCEBreaker bring-up diagnostic
Tests v2.3 9-byte UART_INJECT frame with full cmd_bus word.

Usage:
    python3 fpga/bringup_v23.py COM4
    python3 fpga/bringup_v23.py COM4 0xA5
"""
import serial, struct, time, sys

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0xA5

print(f"Opening {PORT} auth={AUTH:#04x} — v2.3 9-byte frames")
s = serial.Serial(PORT, 115200, timeout=2)
time.sleep(0.3)
if s.in_waiting:
    b = s.read(s.in_waiting)
    print(f"  Startup bytes: {b.hex()}")

# ── v2.3 packet builders ──────────────────────────────────────────────────────

def build_cmd_bus(opcode, auth=0, bus_addr=0,
                  preload_sel=0, shift_in=False, shift_out=False):
    """
    Build 32-bit unified cmd_bus word (v2.3).
    bus_addr goes in bits 15:0 — used by array as cpu_addr for DATA_WRITE
    and as cell target for command ops.
    """
    w  = (opcode   & 0xFF)
    w |= ((bus_addr & 0xFFFF) << 0)   # bits 15:0 carry address
    # Note: opcode is bits 7:0, addr overlaps — for DATA_WRITE (0x01)
    # the array uses cpu_addr=cpu_bus[15:0] and data from cmd_data.
    # For command ops the addr field is in cmd_data[15:0] instead.
    # So keep it simple: cmd_bus carries opcode+auth+modifiers,
    # cmd_data carries address or payload depending on opcode.
    w  = (opcode & 0xFF)
    w |= ((preload_sel & 0x3) << 17)
    w |= (0x80000 if shift_in else 0)
    w |= (0x100000 if shift_out else 0)
    w |= ((auth & 0xFF) << 21)
    return w

def send(opcode, cmd_data=0, auth=AUTH, label="",
         preload_sel=0, bus_addr=0, bus_data=0):
    """
    Send 9-byte UART_INJECT: 0x01 + cmd_bus(4) + cmd_data(4).

    DATA_WRITE (opcode 0x01) packet layout:
      cmd_bus[7:0]    = 0x01
      cmd_bus[28:21]  = auth
      cmd_data[31:16] = bus_addr (16-bit logical address)
      cmd_data[15:0]  = bus_data (16-bit value, zero-extended to 32-bit on bus)

    All other opcodes:
      cmd_bus[7:0]    = opcode
      cmd_bus[28:21]  = auth
      cmd_data[15:0]  = target address (for address-setting commands)
      cmd_data[31:0]  = payload (for RECONFIGURE etc)
    """
    if opcode == 0x01:  # DATA_WRITE
        cb = (0x01) | (preload_sel << 17) | ((auth & 0xFF) << 21)
        cd = ((bus_addr & 0xFFFF) << 16) | (bus_data & 0xFFFF)
    else:
        cb = build_cmd_bus(opcode, auth=auth, preload_sel=preload_sel)
        cd = cmd_data
    pkt = struct.pack('>BII', 0x01, cb & 0xFFFFFFFF, cd & 0xFFFFFFFF)
    print(f"  TX {label}: {pkt.hex()}")
    s.write(pkt)

def drain(label, wait=0.4):
    time.sleep(wait)
    buf = bytearray()
    while s.in_waiting:
        buf += s.read(s.in_waiting)
        time.sleep(0.01)
    if buf:
        print(f"  RX {label}: {buf.hex()}")
        i = 0
        while i < len(buf):
            if buf[i] == 0x10 and i+6 < len(buf):
                addr = struct.unpack('>H', buf[i+1:i+3])[0]
                data = struct.unpack('>I', buf[i+3:i+7])[0]
                print(f"    → FIRED: addr={addr:#06x} data={data:#010x} ({data})")
                i += 7
            elif buf[i] == 0x11 and i+6 < len(buf):
                armed  = struct.unpack('>H', buf[i+1:i+3])[0]
                cycles = struct.unpack('>I', buf[i+3:i+7])[0]
                print(f"    → STATUS: armed={armed} cycles={cycles}")
                i += 7
            else:
                i += 1
    else:
        print(f"  RX {label}: <nothing>")
    return buf

def status(label=""):
    s.write(bytes([0x04]))
    return drain(f"status {label}", 0.3)

# ── Opcodes ───────────────────────────────────────────────────────────────────
CMD_NOP         = 0x00
CMD_DATA_WRITE  = 0x01
CMD_SET_INPUT   = 0x02
CMD_SET_OUTPUT  = 0x03
CMD_RECONFIGURE = 0x04
CMD_BOOT_COMMIT = 0x07
CMD_PING        = 0x09

IN_ADDR  = 0x1000
OUT_ADDR = 0x2000

# ── Tests ─────────────────────────────────────────────────────────────────────

print("\n── Step 1: Status (single-byte — unchanged v2.2/v2.3) ──")
status("initial")

print("\n── Step 2: CMD_BOOT_COMMIT — set logical addr + auth, → RUN state ──")
# cmd_data: [15:0]=logical_addr  [23:16]=auth_mask  [31:24]=group_tag
boot_data = (IN_ADDR & 0xFFFF) | ((AUTH & 0xFF) << 16) | (0 << 24)
send(CMD_BOOT_COMMIT, cmd_data=boot_data, auth=0, label="BOOT_COMMIT")
time.sleep(0.05)

print("\n── Step 3: CMD_SET_OUTPUT_ADDR ──")
send(CMD_SET_OUTPUT, cmd_data=OUT_ADDR, label="SET_OUTPUT")
time.sleep(0.05)

print("\n── Step 4: CMD_RECONFIGURE — NOT topology, armed ──")
# cmd_data: [9:0]=topology  [11]=start_flag  [30:23]=auth_mask
cfg  = 0x001            # topology = NOT (bit 0)
cfg |= (1 << 11)        # start_flag = arm
cfg |= ((AUTH & 0xFF) << 23)
send(CMD_RECONFIGURE, cmd_data=cfg, label="RECONF NOT+armed")
time.sleep(0.05)

print("\n── Step 5: Status after config ──")
status("after config")

print("\n── Step 6: PING ──")
send(CMD_PING, label="PING")
drain("ping", 0.5)

print("\n── Step 7: Two-arrival NOT test ──")
print("  Send 0x0000 twice to 0x1000 — NOT cell fires NOT(A,B)")
print("  First arrival stores A=0. Second arrival fires NOT(0)=0xFFFF")
send(CMD_DATA_WRITE, bus_addr=IN_ADDR, bus_data=0x0000,
     label="DATA first arrival (A)")
time.sleep(0.05)
send(CMD_DATA_WRITE, bus_addr=IN_ADDR, bus_data=0x0000,
     label="DATA second arrival (B) → fires")
drain("NOT(0x0000) → expect 0xFFFF", 0.8)

print("\n── Step 8: Reset cell, test NOT(0xFFFF) → 0x0000 ──")
send(0x11, label="CMD_RESET_CELL")
time.sleep(0.05)
send(CMD_DATA_WRITE, bus_addr=IN_ADDR, bus_data=0xFFFF,
     label="DATA first arrival")
time.sleep(0.05)
send(CMD_DATA_WRITE, bus_addr=IN_ADDR, bus_data=0xFFFF,
     label="DATA second arrival → fires")
drain("NOT(0xFFFF) → expect 0x0000", 0.8)

print("\n── Step 9: preload_sel test (v2.3 feature) ──")
print("  preload_sel=0b10 loads 0xFFFF into a_data in one transaction")
send(0x11, label="RESET_CELL")
time.sleep(0.05)
send(CMD_NOP, preload_sel=0b10, label="PRELOAD_ONES (v2.3)")
time.sleep(0.05)
send(CMD_DATA_WRITE, bus_addr=IN_ADDR, bus_data=0x0000,
     label="DATA trigger B=0 → NOT fires")
drain("preload_sel NOT → expect 0xFFFF", 0.8)

print("\n── Step 10: Final status ──")
status("final")

s.close()
print("\nDone.")
