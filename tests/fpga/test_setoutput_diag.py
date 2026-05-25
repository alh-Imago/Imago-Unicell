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


# ── Test D: STATUS between RECONFIGURE and SET_OUTPUT_ADDR ───────────────────
print("\n=== Test D: STATUS query timing ===")

import serial as _s2
s2 = _s2.Serial(PORT, 115200, timeout=1)
time.sleep(0.2)
if s2.in_waiting: s2.read(s2.in_waiting)

def tx2(opcode, addr, data, label=""):
    pkt = struct.pack('>BBHI', 0x01, opcode & 0xFF,
                      addr & 0xFFFF, data & 0xFFFFFFFF)
    print(f"  TX [{label}]: {pkt.hex()}")
    s2.write(pkt)

def status():
    s2.write(bytes([0x04]))
    time.sleep(0.2)
    raw = s2.read(s2.in_waiting)
    print(f"  STATUS raw: {raw.hex()}")

# Reset
s2.write(bytes([0x03])); time.sleep(0.1)
s2.write(bytes([0x03])); time.sleep(0.5)
s2.read(s2.in_waiting)

tx2(0x04, 0, mk(AUTH, cfg), "RECONFIGURE AND")
time.sleep(0.2)
print("  Status after RECONFIGURE:")
status()

tx2(0x03, 0, mk(AUTH, 0x20), "SET_OUTPUT_ADDR -> 0x20")
time.sleep(0.2)
junk = s2.read(s2.in_waiting)
if junk: print(f"  Spurious after SET_OUTPUT_ADDR: {junk.hex()}")

print("  Status after SET_OUTPUT_ADDR:")
status()

s2.close()


# ── Test E: SET_OUTPUT_ADDR without RECONFIGURE ────────────────────────────────
print("\n=== Test E: SET_OUTPUT_ADDR only (no RECONFIGURE) ===")
import serial as _s3
s3 = _s3.Serial(PORT, 115200, timeout=1)
time.sleep(0.2)
if s3.in_waiting: s3.read(s3.in_waiting)

s3.write(bytes([0x03])); time.sleep(0.1)
s3.write(bytes([0x03])); time.sleep(0.5)
s3.read(s3.in_waiting)

# No RECONFIGURE — just SET_OUTPUT_ADDR
pkt = struct.pack('>BBHI', 0x01, 0x03, 0, mk(AUTH, 0x20))
print(f"  TX SET_OUTPUT_ADDR: {pkt.hex()}")
s3.write(pkt)
time.sleep(0.5)
junk = s3.read(s3.in_waiting)
print(f"  RX: {junk.hex() if junk else '(nothing)'}")

# Test F: RECONFIGURE with start_flag=0 then SET_OUTPUT_ADDR
print("\n=== Test F: RECONFIGURE start_flag=0, then SET_OUTPUT_ADDR ===")
s3.write(bytes([0x03])); time.sleep(0.1)
s3.write(bytes([0x03])); time.sleep(0.5)
s3.read(s3.in_waiting)

cfg_no_arm = 0x007  # AND topology, NO start_flag (bit 11 = 0)
pkt = struct.pack('>BBHI', 0x01, 0x04, 0, mk(AUTH, cfg_no_arm))
print(f"  TX RECONFIGURE (no start_flag): {pkt.hex()}")
s3.write(pkt)
time.sleep(0.2)

pkt = struct.pack('>BBHI', 0x01, 0x03, 0, mk(AUTH, 0x20))
print(f"  TX SET_OUTPUT_ADDR: {pkt.hex()}")
s3.write(pkt)
time.sleep(0.5)
junk = s3.read(s3.in_waiting)
print(f"  RX: {junk.hex() if junk else '(nothing)'}")

s3.close()
