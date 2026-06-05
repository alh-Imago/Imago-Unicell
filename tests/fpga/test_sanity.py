"""
test_sanity.py — iCEBreaker comprehensive sanity check

Tests all confirmed functionality in one pass.
Reconfigures between tests. Run after every reflash.

Confirmed functionality tested:
  1.  Two-arrival model — cell fires on second arrival only
  2.  NOT gate — bitwise NOT of 32-bit word
  3.  AND gate — bitwise AND
  4.  OR gate  — bitwise OR
  5.  XOR gate — bitwise XOR
  6.  PASS — word passthrough
  7.  latch_in — cell stores first arrival, fires on second
  8.  one_shot — fires once then disarms
  9.  invert_out — output inverted before emission
  10. preload_sel — preload a_data in one transaction (v2.3)
  11. shift_out_en — output shifted right by N nibbles (v2.3)
  12. CMD_ARRAY_RESET — authenticated system-wide reset
  13. CMD_BOOT_COMMIT — logical address assignment
  14. CMD_SET_OUTPUT — output address assignment
  15. CMD_RECONFIGURE — topology change
  16. CMD_RESET_CELL — cell state reset

Protocol: 9-byte frame — 0x01 + cmd_bus(4BE) + cmd_data(4BE)
Response: 0x10 + addr(2BE) + data(4BE) = 7 bytes

Usage:
    python tests/fpga/test_sanity.py COM4
    python tests/fpga/test_sanity.py COM4 0xA5
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
                pkt_q.put(('fired', addr, data & 0xFFFF))
                buf = buf[7:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

# ── Protocol ──────────────────────────────────────────────────────────────────

CMD_ARRAY_RESET = 0x08
CMD_BOOT_COMMIT = 0x07
CMD_SET_OUTPUT  = 0x03
CMD_RECONFIGURE = 0x04
CMD_RESET_CELL  = 0x11
CMD_DATA_WRITE  = 0x01
CMD_NOP         = 0x00

TOPO_PASS  = 0x000
TOPO_NOT   = 0x001
TOPO_NOR   = 0x004
TOPO_AND   = 0x007
TOPO_OR    = 0x024
TOPO_NAND  = 0x027
TOPO_XOR   = 0x0BC
TOPO_XNOR  = 0x03C

PRELOAD_SEL_ZERO = 0b01 << 17
PRELOAD_SEL_ONES = 0b10 << 17
SHIFT_OUT_EN     = 1 << 20

def raw(cmd_bus, cmd_data):
    pkt = struct.pack('>BII', 0x01,
                      cmd_bus  & 0xFFFFFFFF,
                      cmd_data & 0xFFFFFFFF)
    s.write(pkt)
    time.sleep(0.025)

def cmd(opcode, data=0):
    raw((opcode & 0xFF) | ((AUTH & 0xFF) << 21), data)

def data_write(bus_addr, bus_data, modifiers=0):
    cb = CMD_DATA_WRITE | ((AUTH & 0xFF) << 21) | modifiers
    cd = ((bus_addr & 0xFFFF) << 16) | (bus_data & 0xFFFF)
    raw(cb, cd)

def array_reset():
    raw(CMD_ARRAY_RESET | ((AUTH & 0xFF) << 21), 0)
    time.sleep(0.3)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def boot():
    """Boot cell to logical address IN_ADDR with output OUT_ADDR."""
    boot_data = (IN_ADDR & 0xFFFF) | ((AUTH & 0xFF) << 16)
    raw(CMD_BOOT_COMMIT, boot_data)
    time.sleep(0.05)
    cmd(CMD_SET_OUTPUT, OUT_ADDR)
    time.sleep(0.05)

# ── Topology preset opcodes (single command, no bit-twiddling) ────────────────
CMD_TOPO_PASS_A  = 49   # PASS(A), latch_in=1, armed
CMD_TOPO_NOT_A   = 51   # NOT(A),  latch_in=1, armed
CMD_TOPO_NOR     = 53   # NOR(A,B), armed
CMD_TOPO_AND     = 55   # AND(A,B), armed
CMD_TOPO_OR      = 57   # OR(A,B),  armed
CMD_TOPO_NAND    = 59   # NAND(A,B), armed
CMD_TOPO_PASS_B  = 61   # PASS(B), armed
CMD_TOPO_XNOR    = 63   # XNOR(A,B), armed
CMD_TOPO_XOR     = 65   # XOR(A,B), armed

def reconfig(preset_opcode):
    """Reconfigure cell using topology preset opcode — single command."""
    cmd(preset_opcode, 0)
    time.sleep(0.05)

def reconfigure_full(topo, latch_in=False, one_shot=False, invert_out=False):
    """Full RECONFIGURE for flags not covered by presets (one_shot, invert_out)."""
    # Bit positions from unicell.v CMD_RECONFIGURE decode:
    # cmd_data[9:0]   = topology
    # cmd_data[11]    = start_flag
    # cmd_data[16]    = invert_out
    # cmd_data[17]    = latch_in
    # cmd_data[21]    = one_shot
    # cmd_data[30:23] = auth_mask
    cfg  = topo & 0x3FF
    cfg |= (1 << 11)
    cfg |= (1 << 16) if invert_out else 0
    cfg |= (1 << 17) if latch_in   else 0
    cfg |= (1 << 21) if one_shot   else 0
    cfg |= ((AUTH & 0xFF) << 23)
    cmd(CMD_RECONFIGURE, cfg)
    time.sleep(0.05)

def reset_cell():
    cmd(CMD_RESET_CELL, 0)
    time.sleep(0.1)

def inject(val):
    data_write(IN_ADDR, val)

def collect(timeout=0.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired' and e[1] == OUT_ADDR:
                return e[2]
        except queue.Empty:
            pass
    return None

def collect_none(timeout=0.3):
    """Return True if nothing fires within timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired' and e[1] == OUT_ADDR:
                return False
        except queue.Empty:
            pass
    return True

# ── Test infrastructure ───────────────────────────────────────────────────────

passed = 0
failed = 0
section_fails = 0

def check(label, got, expected):
    global passed, failed, section_fails
    ok = (got == expected)
    status = 'PASS' if ok else 'FAIL'
    if not ok:
        got_str = 'None' if got is None else f'{got:#06x}'
        exp_str = 'None' if expected is None else f'{expected:#06x}'
        print(f"  [{status}] {label}: got={got_str} expected={exp_str}")
        failed += 1
        section_fails += 1
    else:
        print(f"  [{status}] {label}")
        passed += 1

def check_none(label, fired):
    global passed, failed, section_fails
    if fired:
        print(f"  [PASS] {label}")
        passed += 1
    else:
        print(f"  [FAIL] {label}: unexpected output received")
        failed += 1
        section_fails += 1

def section(title):
    global section_fails
    section_fails = 0
    print(f"\n--- {title} ---")
    # Full reset between sections — ensures clean state
    array_reset()
    boot()

# ── Tests ─────────────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print(f"  iCEBreaker Sanity Check  ({PORT}  auth={AUTH:#04x})")
print(f"{'='*60}\n")

# Record start time and get initial cycle count for tick timing
test_start = time.time()

# Measure tick duration — read cycle counter twice with known delay
s.write(bytes([0x04]))  # status request
time.sleep(0.02)
buf1 = bytearray()
deadline = time.time() + 0.3
while time.time() < deadline:
    if s.in_waiting: buf1 += s.read(s.in_waiting)
    time.sleep(0.005)
cycles1 = None
for i in range(len(buf1)):
    if buf1[i] == 0x11 and i+6 < len(buf1):
        cycles1 = struct.unpack('>I', buf1[i+3:i+7])[0]
        break

time.sleep(0.5)  # known delay

s.write(bytes([0x04]))
time.sleep(0.02)
buf2 = bytearray()
deadline = time.time() + 0.3
while time.time() < deadline:
    if s.in_waiting: buf2 += s.read(s.in_waiting)
    time.sleep(0.005)
cycles2 = None
for i in range(len(buf2)):
    if buf2[i] == 0x11 and i+6 < len(buf2):
        cycles2 = struct.unpack('>I', buf2[i+3:i+7])[0]
        break

if cycles1 is not None and cycles2 is not None:
    delta_cycles = cycles2 - cycles1
    tick_ns = round(500_000_000 / delta_cycles) if delta_cycles > 0 else 0
    tick_mhz = round(delta_cycles / 500_000, 2)
    print(f"  Clock: {delta_cycles} ticks in 500ms → {tick_mhz} MHz  ({tick_ns} ns/tick)")
else:
    print("  Clock: could not measure")
print()

# ── 1. Two-arrival model ──────────────────────────────────────────────────────
section("1. Two-arrival model")
reconfig(CMD_TOPO_NOT_A)
inject(0x0000)
r = collect(0.3)
check_none("single arrival does not fire", r is None)
inject(0x0000)
r = collect()
check("second arrival fires NOT(0) = 0xFFFF", r, 0xFFFF)

# ── 2. NOT gate ───────────────────────────────────────────────────────────────
section("2. NOT gate")
reconfig(CMD_TOPO_NOT_A)
reset_cell(); inject(0x0000); inject(0x0000)
check("NOT(0x0000) = 0xFFFF", collect(), 0xFFFF)
reset_cell(); inject(0xFFFF); inject(0xFFFF)
check("NOT(0xFFFF) = 0x0000", collect(), 0x0000)
reset_cell(); inject(0xA5A5); inject(0xA5A5)
check("NOT(0xA5A5) = 0x5A5A", collect(), 0x5A5A)

# ── 3. AND gate ───────────────────────────────────────────────────────────────
section("3. AND gate")
reconfig(CMD_TOPO_AND)
reset_cell(); inject(0xFF00); inject(0x0FF0)
check("AND(0xFF00, 0x0FF0) = 0x0F00", collect(), 0x0F00)
reset_cell(); inject(0xFFFF); inject(0xFFFF)
check("AND(0xFFFF, 0xFFFF) = 0xFFFF", collect(), 0xFFFF)
reset_cell(); inject(0xFFFF); inject(0x0000)
check("AND(0xFFFF, 0x0000) = 0x0000", collect(), 0x0000)

# ── 4. OR gate ────────────────────────────────────────────────────────────────
section("4. OR gate")
reconfig(CMD_TOPO_OR)
reset_cell(); inject(0xFF00); inject(0x00FF)
check("OR(0xFF00, 0x00FF) = 0xFFFF", collect(), 0xFFFF)
reset_cell(); inject(0x0000); inject(0x0000)
check("OR(0x0000, 0x0000) = 0x0000", collect(), 0x0000)
reset_cell(); inject(0xA5A5); inject(0x5A5A)
check("OR(0xA5A5, 0x5A5A) = 0xFFFF", collect(), 0xFFFF)

# ── 5. XOR gate ───────────────────────────────────────────────────────────────
section("5. XOR gate")
reconfig(CMD_TOPO_XOR)
reset_cell(); inject(0xFFFF); inject(0xFFFF)
check("XOR(0xFFFF, 0xFFFF) = 0x0000", collect(), 0x0000)
reset_cell(); inject(0xFF00); inject(0x00FF)
check("XOR(0xFF00, 0x00FF) = 0xFFFF", collect(), 0xFFFF)
reset_cell(); inject(0xA5A5); inject(0xA5A5)
check("XOR(0xA5A5, 0xA5A5) = 0x0000", collect(), 0x0000)

# ── 6. PASS ───────────────────────────────────────────────────────────────────
section("6. PASS")
reconfig(CMD_TOPO_PASS_A)
reset_cell(); inject(0x1234); inject(0x1234)
check("PASS(0x1234) = 0x1234", collect(), 0x1234)
reset_cell(); inject(0xBEEF); inject(0xBEEF)
check("PASS(0xBEEF) = 0xBEEF", collect(), 0xBEEF)
reset_cell(); inject(0x0000); inject(0x0000)
check("PASS(0x0000) = 0x0000", collect(), 0x0000)

# ── 7. latch_in ───────────────────────────────────────────────────────────────
section("7. latch_in — stores first arrival as a_data")
# CMD_TOPO_PASS_A already includes latch_in=1
reconfig(CMD_TOPO_PASS_A)
inject(0xAAAA)           # first arrival stores a_data=0xAAAA
inject(0x5555)           # second arrival fires PASS(a=0xAAAA, b=0x5555)
r = collect()            # PASS outputs A = 0xAAAA
check("latch_in PASS: output is first arrival (A)", r, 0xAAAA)
reset_cell()
inject(0x1111)
inject(0x2222)
check("latch_in PASS: output is stored A value", collect(), 0x1111)

# ── 8. one_shot ───────────────────────────────────────────────────────────────
section("8. one_shot — fires once then disarms until reset")
reconfigure_full(0x001, one_shot=True)   # NOT + one_shot (no preset for this)
inject(0x0000); inject(0x0000)
r1 = collect()
check("one_shot: fires first time NOT(0)=0xFFFF", r1, 0xFFFF)
inject(0x0000); inject(0x0000)
r2 = collect(0.3)
check("one_shot: does not fire second time without reset", r2, None)

# ── 9. invert_out ─────────────────────────────────────────────────────────────
section("9. invert_out — output inverted before emission")
reconfigure_full(0x000, invert_out=True)  # PASS + invert_out (no preset)
reset_cell(); inject(0x0000); inject(0x0000)
check("PASS+invert_out(0x0000) = 0xFFFF", collect(), 0xFFFF)
reset_cell(); inject(0xFFFF); inject(0xFFFF)
check("PASS+invert_out(0xFFFF) = 0x0000", collect(), 0x0000)
reset_cell(); inject(0xA5A5); inject(0xA5A5)
check("PASS+invert_out(0xA5A5) = 0x5A5A", collect(), 0x5A5A)

# ── 10. preload_sel ───────────────────────────────────────────────────────────
section("10. preload_sel — preload a_data in one transaction (v2.3)")
reconfig(CMD_TOPO_NOT_A)
reset_cell()
cb_preload = CMD_NOP | ((AUTH & 0xFF) << 21) | PRELOAD_SEL_ONES
raw(cb_preload, 0)
time.sleep(0.05)
inject(0x0000)
check("preload_sel ONES then NOT fires: NOT(0xFFFF)=0x0000", collect(), 0x0000)

reset_cell()
cb_preload_zero = CMD_NOP | ((AUTH & 0xFF) << 21) | PRELOAD_SEL_ZERO
raw(cb_preload_zero, 0)
time.sleep(0.05)
inject(0xFFFF)
check("preload_sel ZERO then NOT fires: NOT(0x0000)=0xFFFF", collect(), 0xFFFF)

# ── 11. shift_out_en ─────────────────────────────────────────────────────────
section("11. shift_out_en — output shifted right by N nibbles (v2.3)")
reconfig(CMD_TOPO_PASS_A)
reset_cell()
data_write(IN_ADDR, 0x0F01, modifiers=SHIFT_OUT_EN)
data_write(IN_ADDR, 0x0F01, modifiers=SHIFT_OUT_EN)
check("shift_out 1 nibble: 0x0F01 >> 4 = 0x00F0", collect(), 0x00F0)

reset_cell()
data_write(IN_ADDR, 0x1230, modifiers=SHIFT_OUT_EN)
data_write(IN_ADDR, 0x1230, modifiers=SHIFT_OUT_EN)
check("shift_out nibble=0: 0x1230 unchanged", collect(), 0x1230)

# ── 12. CMD_ARRAY_RESET ───────────────────────────────────────────────────────
section("12. CMD_ARRAY_RESET — clears all cells")
reconfig(CMD_TOPO_NOT_A)
reset_cell(); inject(0x0000); inject(0x0000)
r = collect()
check("cell fires before reset", r, 0xFFFF)
array_reset()
boot()
reconfig(CMD_TOPO_NOT_A)
inject(0x0000)
r = collect(0.3)
check_none("after array_reset: single arrival does not fire", r is None)
inject(0x0000)
check("after array_reset: cell correctly re-armed and fires", collect(), 0xFFFF)

# ── Summary ───────────────────────────────────────────────────────────────────
running = False
s.close()

elapsed = time.time() - test_start
total = passed + failed
print(f"\n{'='*60}")
print(f"  Results: {passed} passed, {failed} failed out of {total}")
print(f"  Elapsed: {elapsed:.1f}s")
if cycles1 is not None and cycles2 is not None:
    print(f"  Clock:   {tick_mhz} MHz  ({tick_ns} ns/tick)")
if failed == 0:
    print(f"  ALL PASSED — iCEBreaker fully operational")
else:
    print(f"  FAILURES DETECTED — investigate before proceeding")
print(f"{'='*60}")

sys.exit(0 if failed == 0 else 1)
