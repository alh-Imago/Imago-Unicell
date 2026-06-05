"""
test_nibble_shift.py — iCEBreaker silicon validation for shift_sel bits

Tests cmd_bus[20:19] shift_sel on a single PASS cell.

Protocol: 9-byte frame — 0x01 + cmd_bus(4BE) + cmd_data(4BE)
DATA_WRITE: cmd_data[31:16]=bus_addr, cmd_data[15:0]=bus_data (16-bit)

shift_in_en  (cmd_bus[19]): bus_data shifted LEFT  by N nibbles before gate
shift_out_en (cmd_bus[20]): output   shifted RIGHT by N nibbles before emit
shift_nibbles = cmd_data[3:0] — low nibble of the data word

Usage:
    python tests/fpga/test_nibble_shift.py COM4
    python tests/fpga/test_nibble_shift.py COM4 0xA5
"""

import sys, os, time, struct, serial, threading, queue

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0xA5

IN_ADDR  = 0x1000
OUT_ADDR = 0x2000

# ── UART setup ────────────────────────────────────────────────────────────────

s       = serial.Serial(PORT, 115200, timeout=3)
pkt_q   = queue.Queue()
running = True

time.sleep(0.3)
if s.in_waiting:
    s.read(s.in_waiting)

def rx_thread():
    buf = bytearray()
    while running:
        try:
            if s.in_waiting:
                buf += s.read(s.in_waiting)
        except:
            break
        while len(buf) >= 7:
            if buf[0] == 0x10 and len(buf) >= 7:
                addr = struct.unpack('>H', buf[1:3])[0]
                data = struct.unpack('>I', buf[3:7])[0]
                pkt_q.put(('fired', addr, data))
                buf = buf[7:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

# ── Protocol helpers ──────────────────────────────────────────────────────────

CMD_ARRAY_RESET  = 0x08
CMD_BOOT_COMMIT  = 0x09
CMD_SET_OUTPUT   = 0x0A
CMD_RECONFIGURE  = 0x04
CMD_RESET_CELL   = 0x11
CMD_DATA_WRITE   = 0x01
CMD_NOP          = 0x00

TOPO_PASS = 0x000
TOPO_NOT  = 0x001

SHIFT_IN_EN  = 1 << 19
SHIFT_OUT_EN = 1 << 20

def send_raw(cmd_bus, cmd_data):
    pkt = struct.pack('>BII', 0x01, cmd_bus & 0xFFFFFFFF, cmd_data & 0xFFFFFFFF)
    s.write(pkt)
    time.sleep(0.03)

def send_cmd(opcode, cmd_data=0):
    cb = (opcode & 0xFF) | ((AUTH & 0xFF) << 21)
    send_raw(cb, cmd_data)

def send_data(bus_addr, bus_data, shift_in=False, shift_out=False, shift_nibbles=0):
    """Send DATA_WRITE with optional shift modifier."""
    cb = CMD_DATA_WRITE | ((AUTH & 0xFF) << 21)
    if shift_in:  cb |= SHIFT_IN_EN
    if shift_out: cb |= SHIFT_OUT_EN
    # cmd_data: [31:16]=bus_addr, [15:0]=data value
    # Note: cmd_data[3:0] also serves as shift_nibbles — low nibble of data
    # So data value must have low nibble = shift_nibbles for correct shift amount
    cd = ((bus_addr & 0xFFFF) << 16) | (bus_data & 0xFFFF)
    send_raw(cb, cd)

def reset():
    cb = CMD_ARRAY_RESET | ((AUTH & 0xFF) << 21)
    send_raw(cb, 0)
    time.sleep(0.3)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def configure_cell():
    """Boot and configure cell 0 as PASS at IN_ADDR -> OUT_ADDR."""
    # BOOT_COMMIT: set logical addr + auth
    boot_data = (IN_ADDR & 0xFFFF) | ((AUTH & 0xFF) << 16)
    send_cmd(CMD_BOOT_COMMIT, boot_data)
    time.sleep(0.05)
    # SET_OUTPUT_ADDR
    send_cmd(CMD_SET_OUTPUT, OUT_ADDR)
    time.sleep(0.05)
    # RECONFIGURE: PASS topology, armed
    cfg  = TOPO_PASS
    cfg |= (1 << 11)               # start_flag
    cfg |= ((AUTH & 0xFF) << 23)
    send_cmd(CMD_RECONFIGURE, cfg)
    time.sleep(0.05)

def reset_cell():
    send_cmd(CMD_RESET_CELL, 0)
    time.sleep(0.1)

def collect(timeout=0.5):
    evts = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired':
                evts.append((e[1], e[2]))
        except queue.Empty:
            pass
    return evts

# ── Test infrastructure ───────────────────────────────────────────────────────

passed = 0
failed = 0

def check(label, got, expected):
    global passed, failed
    if got == expected:
        print(f"  [PASS] {label}")
        passed += 1
    else:
        print(f"  [FAIL] {label}: got={got:#06x} expected={expected:#06x}")
        failed += 1

# ── Tests ─────────────────────────────────────────────────────────────────────

print(f"\n=== Nibble Shift Silicon Validation ({PORT}) ===\n")

reset()
configure_cell()

# ── Test 1: baseline PASS, no shift ──────────────────────────────────────────
print("--- Test 1: PASS no shift (baseline) ---")
reset_cell()
send_data(IN_ADDR, 0x1234)   # first arrival — stores a_data
send_data(IN_ADDR, 0x1234)   # second arrival — fires
evts = collect()
fired = [d for a, d in evts if a == OUT_ADDR]
if fired:
    check("PASS(0x1234) = 0x1234", fired[0], 0x1234)
else:
    print("  [FAIL] baseline: no output received")
    failed += 1

# ── Test 2: shift_in_en, 1 nibble ────────────────────────────────────────────
# Send 0x00F1 with shift_in_en: low nibble=1 (shift count), value bits=0xF0
# gate sees 0xF0 << 4 = 0x0F00 (left shift by 4 bits = 1 nibble)
# But data is 16-bit on iCEBreaker so gate sees (0x00F1 << 4) & 0xFFFF = 0x0F10
# PASS(a, b) = b = shifted_input
print("\n--- Test 2: shift_in_en, 1 nibble ---")
print("  data=0x00F1, low nibble=1 (shift count)")
print("  gate sees 0x00F1 << 4 = 0x0F10")
reset_cell()
send_data(IN_ADDR, 0x00F1, shift_in=True, shift_nibbles=1)  # first arrival
send_data(IN_ADDR, 0x00F1, shift_in=True, shift_nibbles=1)  # second arrival fires
evts = collect()
fired = [d for a, d in evts if a == OUT_ADDR]
if fired:
    check("shift_in 1 nibble: PASS(0x00F1) → 0x0F10", fired[0], 0x0F10)
else:
    print("  [FAIL] shift_in_en: no output received")
    failed += 1

# ── Test 3: shift_in_en, 2 nibbles ───────────────────────────────────────────
# Send 0x00F2 with shift_in_en: low nibble=2, value bits=0xF0
# gate sees 0x00F2 << 8 = 0xF200 (left shift by 8 bits = 2 nibbles)
print("\n--- Test 3: shift_in_en, 2 nibbles ---")
print("  data=0x00F2, low nibble=2 (shift count)")
print("  gate sees 0x00F2 << 8 = 0xF200")
reset_cell()
send_data(IN_ADDR, 0x00F2, shift_in=True)
send_data(IN_ADDR, 0x00F2, shift_in=True)
evts = collect()
fired = [d for a, d in evts if a == OUT_ADDR]
if fired:
    check("shift_in 2 nibbles: PASS(0x00F2) → 0xF200", fired[0], 0xF200)
else:
    print("  [FAIL] shift_in_en 2 nibbles: no output received")
    failed += 1

# ── Test 4: shift_out_en, 1 nibble ───────────────────────────────────────────
# Send 0x0F10 (16-bit), shift_out by 1 nibble (low nibble=0, but need shift count)
# Actually: data=0x0F00, low nibble=0, but we need nibble count in low bits
# Use 0x0F01: value=0x0F0_, low nibble=1 = shift count
# PASS computes B=0x0F01, shift_out shifts right 4: output = 0x00F0
print("\n--- Test 4: shift_out_en, 1 nibble ---")
print("  data=0x0F01, low nibble=1 (shift count)")
print("  PASS(0x0F01) >> 4 = 0x00F0")
reset_cell()
send_data(IN_ADDR, 0x0F01, shift_out=True)
send_data(IN_ADDR, 0x0F01, shift_out=True)
evts = collect()
fired = [d for a, d in evts if a == OUT_ADDR]
if fired:
    check("shift_out 1 nibble: PASS(0x0F01) >> 4 = 0x00F0", fired[0], 0x00F0)
else:
    print("  [FAIL] shift_out_en: no output received")
    failed += 1

# ── Test 5: shift=0 leaves value unchanged ───────────────────────────────────
print("\n--- Test 5: shift_in_en with nibble=0 (no shift) ---")
reset_cell()
send_data(IN_ADDR, 0x1230, shift_in=True)  # low nibble=0 = no shift
send_data(IN_ADDR, 0x1230, shift_in=True)
evts = collect()
fired = [d for a, d in evts if a == OUT_ADDR]
if fired:
    check("shift_in nibble=0: PASS(0x1230) = 0x1230", fired[0], 0x1230)
else:
    print("  [FAIL] shift=0 baseline: no output received")
    failed += 1

# ── Summary ───────────────────────────────────────────────────────────────────

running = False
s.close()

total = passed + failed
print(f"\n=== Results: {passed} passed, {failed} failed out of {total} ===")
if failed == 0:
    print("ALL PASSED — shift_sel confirmed on iCEBreaker silicon.")
else:
    print("FAILURES — check Verilog cmd_bus bit positions and data format.")
