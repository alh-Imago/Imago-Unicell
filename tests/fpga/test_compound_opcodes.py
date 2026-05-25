"""
test_compound_opcodes.py — iCEBreaker validation for v2.2 compound opcodes

Uses cell 0 default addresses (input=0, output=1) via direct RECONFIGURE.
No SET_OUTPUT_ADDR or SET_LOGICAL — proven working approach from test_sync_wait.

Tests:
  1.  Topology presets  — CMD_TOPO_AND, CMD_TOPO_OR etc.
  2.  Cold vs armed     — cold stays disarmed, armed fires
  3.  Cell state        — CMD_CLEAR_ARRIVED, CMD_RESET_CELL
  4.  SET_TOPO          — topology change without full reconfigure

Usage:
  python tests/fpga/test_compound_opcodes.py COM4 0xA5
"""

import sys, os, time, struct, threading, queue, serial

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0xA5

# Cell 0: default input=0, output=1
CELL = 0
IN   = 0   # cell 0 default input address
OUT  = 1   # cell 0 default output address

s       = serial.Serial(PORT, 115200, timeout=3)
pkt_q   = queue.Queue()
running = True

def rx_thread():
    buf = bytearray()
    while running:
        try:
            if s.in_waiting:
                buf += s.read(s.in_waiting)
            while len(buf) >= 7:
                if buf[0] == 0x10:
                    addr = struct.unpack('>H', buf[1:3])[0]
                    data = struct.unpack('>I', buf[3:7])[0]
                    pkt_q.put(('fired', addr, data))
                    buf = buf[7:]
                elif buf[0] == 0x11:
                    buf = buf[7:]
                else:
                    buf = buf[1:]
            time.sleep(0.001)
        except: break

threading.Thread(target=rx_thread, daemon=True).start()
time.sleep(0.2)

def tx(opcode, addr, data):
    pkt = struct.pack('>BBHI', 0x01, opcode & 0xFF,
                      addr & 0xFFFF, data & 0xFFFFFFFF)
    s.write(pkt)
    time.sleep(0.02)

def mk(auth, payload=0):
    return ((auth & 0xFF) << 24) | (payload & 0xFFFFFF)

def mk_cfg(topo, latch_in=False, one_shot=False, loop_back=False):
    """v2.2 config word — start_flag always set."""
    w  = topo & 0x3FF
    w |= 1 << 11                              # start_flag
    w |= (1 if latch_in   else 0) << 17       # latch_in  (v2.2 pos)
    w |= (1 if one_shot   else 0) << 21       # one_shot  (v2.2 pos)
    w |= (1 if loop_back  else 0) << 22       # loop_back (v2.2 pos)
    return w

def reconfigure(topo, latch_in=False, one_shot=False):
    """RECONFIGURE cell 0 with topology — arms cell, uses default addresses."""
    cfg = mk_cfg(topo, latch_in=latch_in, one_shot=one_shot)
    tx(0x04, CELL, mk(AUTH, cfg))
    time.sleep(0.05)

def reset():
    s.write(bytes([0x03])); time.sleep(0.05)
    s.write(bytes([0x03])); time.sleep(0.5)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def send(data):
    tx(0x01, IN, data & 0xFFFFFFFF)
    time.sleep(0.05)

def wait_fire(timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = pkt_q.get(timeout=0.1)
            if r[0] == 'fired': return (r[1], r[2])
        except queue.Empty: pass
    return None

passed = failed = 0

def check(label, got, expected):
    global passed, failed
    ok = (got == expected)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: "
          f"got {hex(got) if isinstance(got,int) else got} "
          f"expected {hex(expected) if isinstance(expected,int) else expected}")
    if ok: passed += 1
    else:  failed += 1


print(f"\n[FPGA] PORT={PORT} AUTH={hex(AUTH)}")
time.sleep(0.3)

# ── Topology preset tests ──────────────────────────────────────────────────────
print("\n=== Topology Preset Tests ===")

TOPO_AND  = 0x007
TOPO_OR   = 0x024
TOPO_XOR  = 0x0BC
TOPO_NOR  = 0x004
TOPO_NOT  = 0x001
TOPO_ZERO = 0x030
TOPO_ONE  = 0x0B0

# CMD_TOPO_* opcode constants
CMD_TOPO_AND      = 55
CMD_TOPO_AND_COLD = 54
CMD_TOPO_OR       = 57
CMD_TOPO_XOR      = 65
CMD_TOPO_NOR      = 53
CMD_TOPO_NOT_A    = 51
CMD_TOPO_ZERO     = 67
CMD_TOPO_ONE      = 69

def test_preset(name, topo_opcode, val_a, val_b, expected):
    """Boot with RECONFIGURE PASS, then use preset opcode, inject, check."""
    reset()
    # First boot with PASS topology so auth gets set
    reconfigure(0x000)  # PASS(A) — gets auth set
    time.sleep(0.05)
    # Send preset opcode to cell 0 input addr (logical=physical=0 after reconfigure)
    tx(topo_opcode, IN, mk(AUTH))
    time.sleep(0.05)
    send(val_a)
    send(val_b)
    r = wait_fire(2.0)
    got = r[1] if r else -1
    check(name, got, expected)

test_preset("AND: 0xF0 & 0x0F = 0x00", CMD_TOPO_AND, 0xF0, 0x0F, 0x00)
test_preset("AND: 0xFF & 0xFF = 0xFF", CMD_TOPO_AND, 0xFF, 0xFF, 0xFF)
test_preset("OR:  0xF0 | 0x0F = 0xFF", CMD_TOPO_OR,  0xF0, 0x0F, 0xFF)
test_preset("XOR: 0xFF ^ 0xFF = 0x00", CMD_TOPO_XOR, 0xFF, 0xFF, 0x00)
test_preset("NOR: ~(0|0)=0xFFFFFFFF",  CMD_TOPO_NOR, 0, 0, 0xFFFFFFFF)

# ── Cold/armed tests ───────────────────────────────────────────────────────────
print("\n=== Cold/Armed Tests ===")
reset()
reconfigure(0x000)  # set auth
tx(CMD_TOPO_AND_COLD, IN, mk(AUTH))  # configure AND, stay disarmed
time.sleep(0.05)
send(0xFF); send(0xFF)
r = wait_fire(0.5)
check("COLD stays disarmed", r, None)

reset()
reconfigure(0x000)
tx(CMD_TOPO_AND, IN, mk(AUTH))  # configure AND, arm
time.sleep(0.05)
send(0xFF); send(0xFF)
r = wait_fire(1.0)
got = r[1] if r else -1
check("ARMED fires", got, 0xFF)

# ── Cell state control ─────────────────────────────────────────────────────────
print("\n=== Cell State Control Tests ===")

# CMD_CLEAR_ARRIVED
reset()
reconfigure(TOPO_AND)
send(0xAA)                          # first arrival stored
tx(0x10, IN, mk(AUTH))              # CMD_CLEAR_ARRIVED
time.sleep(0.05)
send(0x55)                          # fresh first arrival
send(0xFF)                          # second — AND(0x55, 0xFF) = 0x55
r = wait_fire(1.0)
got = r[1] if r else -1
check("CLEAR_ARRIVED resets state: AND(0x55,0xFF)=0x55", got, 0x55)

# CMD_RESET_CELL
reset()
reconfigure(TOPO_AND)
send(0xAA)                          # first arrival stored
tx(0x11, IN, mk(AUTH))              # CMD_RESET_CELL
time.sleep(0.05)
send(0x55); send(0xFF)              # fresh pair after reset
r = wait_fire(1.0)
got = r[1] if r else -1
check("RESET_CELL then AND(0x55,0xFF)=0x55", got, 0x55)

# CMD_SET_TOPO
print("\n=== SET_TOPO Test ===")
reset()
reconfigure(TOPO_AND)               # start as AND
tx(0x14, IN, mk(AUTH, TOPO_OR))     # CMD_SET_TOPO — change to OR
time.sleep(0.05)
send(0xF0); send(0x0F)              # OR(0xF0, 0x0F) = 0xFF
r = wait_fire(1.0)
got = r[1] if r else -1
check("SET_TOPO AND→OR: 0xF0|0x0F=0xFF", got, 0xFF)

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*40}")
print(f"Results: {passed}/{passed+failed} PASS  {failed}/{passed+failed} FAIL")
running = False
s.close()
sys.exit(0 if failed == 0 else 1)
