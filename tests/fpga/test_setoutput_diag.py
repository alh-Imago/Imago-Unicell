"""
test_setoutput_diag.py — Diagnose SET_OUTPUT_ADDR issue
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

def wait_bytes(timeout=2.0):
    deadline = time.time() + timeout
    buf = bytearray()
    while time.time() < deadline:
        if s.in_waiting:
            buf += s.read(s.in_waiting)
            if len(buf) >= 7: break
        else:
            time.sleep(0.01)
    return bytes(buf)

cfg = 0x007 | (1 << 11)  # AND + start_flag

# ── Test A: RECONFIGURE only ──────────────────────────────────────────────────
print("\n=== Test A: RECONFIGURE only ===")
reset()
tx(0x04, 0, mk(AUTH, cfg), "RECONFIGURE AND")
time.sleep(0.2)
tx(0x01, 0, 0xFF, "DATA first")
time.sleep(0.1)
tx(0x01, 0, 0xFF, "DATA second")
raw = wait_bytes(2.0)
print(f"  RX: {raw.hex()}")

# ── Test B: With SET_OUTPUT_ADDR, flush before DATA ───────────────────────────
print("\n=== Test B: +SET_OUTPUT_ADDR, flush between cmd and data ===")
reset()
tx(0x04, 0, mk(AUTH, cfg), "RECONFIGURE AND")
time.sleep(0.2)
tx(0x03, 0, mk(AUTH, 0x20), "SET_OUTPUT_ADDR -> 0x20")
time.sleep(0.5)
junk = s.read(s.in_waiting)
if junk: print(f"  Flushed spurious: {junk.hex()}")
else:     print(f"  Nothing spurious after SET_OUTPUT_ADDR")
tx(0x01, 0, 0xFF, "DATA first")
time.sleep(0.1)
tx(0x01, 0, 0xFF, "DATA second")
raw = wait_bytes(2.0)
print(f"  RX: {raw.hex()}")

# ── Test C: With SET_INPUT_ADDR ───────────────────────────────────────────────
print("\n=== Test C: +SET_INPUT_ADDR to 0x10 ===")
reset()
tx(0x04, 0, mk(AUTH, cfg), "RECONFIGURE AND")
time.sleep(0.2)
tx(0x02, 0, mk(AUTH, 0x10), "SET_INPUT_ADDR -> 0x10")
time.sleep(0.5)
junk = s.read(s.in_waiting)
if junk: print(f"  Flushed spurious: {junk.hex()}")
tx(0x01, 0x10, 0xFF, "DATA first to 0x10")
time.sleep(0.1)
tx(0x01, 0x10, 0xFF, "DATA second to 0x10")
raw = wait_bytes(2.0)
print(f"  RX: {raw.hex()}")

s.close()
