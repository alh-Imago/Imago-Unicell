"""
test_setoutput_diag.py — Diagnose SET_OUTPUT_ADDR issue

Prints every raw byte received to see if fire response comes back at all.

Usage: python tests/fpga/test_setoutput_diag.py COM4 0xA5
"""
import sys, struct, time, serial

PORT = sys.argv[1]
AUTH = int(sys.argv[2], 0)

s = serial.Serial(PORT, 115200, timeout=3)
time.sleep(0.2)
if s.in_waiting: s.read(s.in_waiting)

def tx(opcode, addr, data, label=""):
    pkt = struct.pack('>BBHI', 0x01, opcode & 0xFF,
                      addr & 0xFFFF, data & 0xFFFFFFFF)
    print(f"  TX [{label}]: {pkt.hex()}")
    s.write(pkt)

def mk(auth, payload=0):
    return ((auth & 0xFF) << 24) | (payload & 0xFFFFFF)

def reset():
    s.write(bytes([0x03])); time.sleep(0.1)
    s.write(bytes([0x03])); time.sleep(0.5)
    if s.in_waiting:
        print(f"  flush: {s.read(s.in_waiting).hex()}")

def wait_bytes(n=7, timeout=2.0):
    deadline = time.time() + timeout
    buf = bytearray()
    while time.time() < deadline and len(buf) < n:
        if s.in_waiting:
            buf += s.read(s.in_waiting)
        else:
            time.sleep(0.01)
    return bytes(buf)

# ── Test A: RECONFIGURE only ──────────────────────────────────────────────────
print("\n=== Test A: RECONFIGURE only, inject, expect fire ===")
reset()
cfg = 0x007 | (1 << 11)  # AND + start_flag
tx(0x04, 0, mk(AUTH, cfg), "RECONFIGURE AND cell 0")
time.sleep(0.1)
tx(0x01, 0, 0xFF, "DATA_WRITE first")
time.sleep(0.1)
tx(0x01, 0, 0xFF, "DATA_WRITE second")
time.sleep(0.3)
raw = wait_bytes(7, 1.0)
print(f"  RX raw: {raw.hex() if raw else '(nothing)'}")
if raw and raw[0] == 0x10:
    addr = struct.unpack('>H', raw[1:3])[0]
    data = struct.unpack('>I', raw[3:7])[0]
    print(f"  FIRED: addr={hex(addr)} data={hex(data)}")

# ── Test B: RECONFIGURE + SET_OUTPUT_ADDR ─────────────────────────────────────
print("\n=== Test B: RECONFIGURE + SET_OUTPUT_ADDR to 0x20, inject ===")
reset()
tx(0x04, 0, mk(AUTH, cfg), "RECONFIGURE AND cell 0")
time.sleep(0.1)
tx(0x03, 0, mk(AUTH, 0x20), "SET_OUTPUT_ADDR -> 0x20")
time.sleep(0.1)
tx(0x01, 0, 0xFF, "DATA_WRITE first")
time.sleep(0.1)
tx(0x01, 0, 0xFF, "DATA_WRITE second")
time.sleep(0.3)
raw = wait_bytes(14, 2.0)  # might get 2 fires
print(f"  RX raw: {raw.hex() if raw else '(nothing)'}")
if raw:
    for i in range(0, len(raw)-6, 7):
        if raw[i] == 0x10:
            addr = struct.unpack('>H', raw[i+1:i+3])[0]
            data = struct.unpack('>I', raw[i+3:i+7])[0]
            print(f"  FIRED: addr={hex(addr)} data={hex(data)}")

s.close()
