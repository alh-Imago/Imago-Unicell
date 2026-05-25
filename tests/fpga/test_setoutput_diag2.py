"""
test_setoutput_diag2.py — Capture EXACT bytes during SET_OUTPUT_ADDR

Usage: python tests/fpga/test_setoutput_diag2.py COM4 0xA5
"""
import sys, struct, time, serial, threading

PORT = sys.argv[1]
AUTH = int(sys.argv[2], 0)

s = serial.Serial(PORT, 115200, timeout=0.1)
time.sleep(0.2)
if s.in_waiting: s.read(s.in_waiting)

all_rx = []
rx_running = True

def rx_monitor():
    while rx_running:
        b = s.read(64)
        if b:
            all_rx.append((time.time(), b))

t = threading.Thread(target=rx_monitor, daemon=True)
t.start()

def tx(opcode, addr, data, label=""):
    pkt = struct.pack('>BBHI', 0x01, opcode & 0xFF,
                      addr & 0xFFFF, data & 0xFFFFFFFF)
    ts = time.time()
    s.write(pkt)
    print(f"  {ts:.3f} TX [{label}]: {pkt.hex()}")

def mk(auth, payload=0):
    return ((auth & 0xFF) << 24) | (payload & 0xFFFFFF)

# Reset
s.write(bytes([0x03])); time.sleep(0.2)
s.write(bytes([0x03])); time.sleep(0.8)
all_rx.clear()

cfg = 0x007 | (1 << 11)

print(f"\n=== Timed capture ===")
tx(0x04, 0, mk(AUTH, cfg), "RECONFIGURE AND")
time.sleep(0.3)
tx(0x03, 0, mk(AUTH, 0x20), "SET_OUTPUT_ADDR 0x20")
time.sleep(0.5)
tx(0x01, 0, 0xFF, "DATA first")
time.sleep(0.2)
tx(0x01, 0, 0xFF, "DATA second")
time.sleep(0.5)

rx_running = False
time.sleep(0.1)

print("\n  All RX bytes (with timestamps):")
for ts, data in all_rx:
    print(f"  {ts:.3f} RX: {data.hex()}")
    # Try to parse
    for i in range(len(data)):
        if data[i] == 0x10 and i+6 < len(data):
            addr = struct.unpack('>H', data[i+1:i+3])[0]
            val  = struct.unpack('>I', data[i+3:i+7])[0]
            print(f"         → FIRED addr={hex(addr)} data={hex(val)}")
        elif data[i] == 0xFF:
            print(f"         → RSP_ERROR at byte {i}")

s.close()
