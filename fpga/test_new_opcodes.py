"""
test_new_opcodes.py — Silicon validation of new opcodes

Tests:
  [1]  CMD_LATCH_IN_ON  (10) — switch to single-arrival mode
  [2]  CMD_LATCH_IN_OFF (11) — restore two-arrival mode
  [3]  CMD_REARM        (13) — rearm one-shot cell for reuse
  [4]  CMD_MEM_CALL     (12) — memory on call (latch+one_shot+rearm)
  [5]  CMD_SET_LOGICAL  (14) — switch from physical to logical address
  [6]  output_set gate  —     cell silent until SET_OUTPUT_ADDR

Usage: python test_new_opcodes.py COM4 0x2A5
"""

import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5

s = serial.Serial(PORT, 115200, timeout=3)
pkt_q = queue.Queue()
running = True

# ── Opcodes ───────────────────────────────────────────────────────────────────
CMD_NOP             = 0x00
CMD_DATA_WRITE      = 0x01
CMD_SET_INPUT_ADDR  = 0x02
CMD_SET_OUTPUT_ADDR = 0x03
CMD_RECONFIGURE     = 0x04
CMD_FREEZE          = 0x05
CMD_RELEASE         = 0x06
CMD_PING            = 0x09
CMD_LATCH_IN_ON     = 0x0A
CMD_LATCH_IN_OFF    = 0x0B
CMD_MEM_CALL        = 0x0C
CMD_REARM           = 0x0D
CMD_SET_LOGICAL     = 0x0E

TOPO_PASS = 0x000
TOPO_NOT  = 0x001

# ── RX thread ─────────────────────────────────────────────────────────────────
def rx_thread():
    buf = bytearray()
    while running:
        try:
            if s.in_waiting:
                buf += s.read(s.in_waiting)
        except: break
        while len(buf) >= 7:
            if buf[0] == 0x10 and len(buf) >= 7:
                addr = struct.unpack('>H', buf[1:3])[0]
                data = struct.unpack('>I', buf[3:7])[0]
                pkt_q.put(('fired', addr, data))
                buf = buf[7:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                armed  = struct.unpack('>H', buf[1:3])[0]
                cycles = struct.unpack('>I', buf[3:7])[0]
                pkt_q.put(('status', armed, cycles))
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

# ── Helpers ───────────────────────────────────────────────────────────────────
def tx(opcode, addr, data, label=""):
    pkt = struct.pack('>BBHI', 0x01, opcode & 0xFF,
                      addr & 0xFFFF, data & 0xFFFFFFFF)
    if label: print(f"      TX {label}: {pkt.hex()}")
    s.write(pkt)
    time.sleep(0.3)

def mk_auth_data(auth=0, payload=0):
    return ((auth & 0xFF) << 24) | (payload & 0xFFFFFF)

def mk_cfg(topo=0, one_shot=0, loop_back=0, latch_in=0):
    w  = (topo & 0x3FF)
    w |= 1 << 11   # start_flag
    w |= (1 if latch_in  else 0) << 15
    w |= (1 if one_shot  else 0) << 19
    w |= (1 if loop_back else 0) << 20
    return w

def configure(cell_id, topo=TOPO_PASS, one_shot=0, loop_back=0, latch_in=0, auth=AUTH):
    cfg = mk_cfg(topo, one_shot=one_shot, loop_back=loop_back, latch_in=latch_in)
    cmd_data = mk_auth_data(auth=auth, payload=cfg & 0xFFFFFF)
    tx(CMD_RECONFIGURE, cell_id, cmd_data,
       f"RECONFIGURE cell{cell_id} topo={topo:#05x} cfg={cfg:#010x}")

def send_cmd(opcode, cell_id, auth=AUTH, payload=0, label=""):
    cmd_data = mk_auth_data(auth=auth, payload=payload & 0xFFFFFF)
    tx(opcode, cell_id, cmd_data, label or f"CMD {opcode:#04x} cell{cell_id}")

def send(addr, data, label=""):
    tx(CMD_DATA_WRITE, addr, data, label or f"DATA {data} -> addr {addr:#x}")

def reset():
    s.write(bytes([0x03]))
    time.sleep(0.05)
    s.write(bytes([0x03]))
    time.sleep(0.8)
    while True:
        try: pkt_q.get_nowait()
        except: break

def drain(wait=0.5):
    time.sleep(wait)
    while True:
        try: pkt_q.get_nowait()
        except: break

def expect_fire(out_addr, out_data=None, timeout=1.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.1)
            if e[0] == 'fired':
                print(f"        [rx] fired addr={e[1]:#x} data={e[2]:#010x}")
                addr_ok = (e[1] == out_addr)
                data_ok = True if out_data is None else \
                          ((e[2] & 0xFFFFFFFF) == (out_data & 0xFFFFFFFF))
                if addr_ok and data_ok:
                    return True
        except queue.Empty:
            pass
    return False

def expect_no_fire(timeout=0.6):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired':
                print(f"        [rx] UNEXPECTED fire addr={e[1]:#x} data={e[2]:#010x}")
                return False
        except queue.Empty:
            pass
    return True

pass_count = 0
fail_count = 0

def chk(name, got, exp):
    global pass_count, fail_count
    ok = got == exp
    if ok:
        pass_count += 1
        print(f"  PASS {name}")
    else:
        fail_count += 1
        print(f"  FAIL {name}  got={got}  exp={exp}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
print(f"\n=== test_new_opcodes on {PORT} auth={AUTH:#05x} ===\n")
reset()

# ── [1] CMD_LATCH_IN_ON — single arrival fires ─────────────────────────────
print("[1] CMD_LATCH_IN_ON: after first pair, stays ready (single arrival fires)")
configure(0, TOPO_PASS)
send_cmd(CMD_LATCH_IN_ON, 0, label="LATCH_IN_ON cell0")
drain(0.2)
# First pair — latch_in means a_arrived stays set after firing
send(0, 42, "1st arrival — stores a_data=42, no fire yet")
chk("latch_in: no fire on 1st arrival", expect_no_fire(), True)
send(0, 99, "2nd arrival — fires, a_arrived stays set")
chk("latch_in: fires on 2nd arrival", expect_fire(1, 42), True)
# Now a_arrived stays set — next single arrival fires immediately
send(0, 55, "3rd arrival — fires immediately (a_arrived held)")
chk("latch_in: fires on 3rd (single arrival)", expect_fire(1, 99), True)
send(0, 77, "4th arrival — fires immediately")
chk("latch_in: fires on 4th (single arrival)", expect_fire(1, 55), True)

# ── [2] CMD_LATCH_IN_OFF — restore two-arrival mode ───────────────────────
print("\n[2] CMD_LATCH_IN_OFF: restore two-arrival mode")
reset()
configure(0, TOPO_PASS)
send_cmd(CMD_LATCH_IN_ON,  0, label="LATCH_IN_ON  cell0")
send_cmd(CMD_LATCH_IN_OFF, 0, label="LATCH_IN_OFF cell0")
drain(0.2)
send(0, 10, "1st arrival — should NOT fire")
chk("no fire on 1st after LATCH_IN_OFF", expect_no_fire(), True)
send(0, 20, "2nd arrival — should fire")
chk("fires on 2nd after LATCH_IN_OFF", expect_fire(1), True)

# ── [3] CMD_REARM — rearm one-shot without full reconfigure ───────────────
print("\n[3] CMD_REARM: rearm one-shot cell for reuse as delay")
reset()
configure(0, TOPO_PASS, one_shot=1)
drain(0.2)
# First pair — fires once
send(0, 1, "1st arrival")
chk("one_shot: no fire on 1st", expect_no_fire(), True)
send(0, 2, "2nd arrival — fires once")
chk("one_shot: fires on 2nd", expect_fire(1), True)
# Now disarmed — should not fire
send(0, 3, "3rd arrival — disarmed")
chk("one_shot: no fire after disarm 1st", expect_no_fire(), True)
send(0, 4, "4th arrival — still disarmed")
chk("one_shot: no fire after disarm 2nd", expect_no_fire(), True)
# Rearm and fire again
send_cmd(CMD_REARM, 0, label="REARM cell0")
drain(0.5)
send(0, 5, "1st arrival after REARM")
chk("rearmed: no fire on 1st", expect_no_fire(), True)
send(0, 6, "2nd arrival after REARM — fires again")
chk("rearmed: fires on 2nd", expect_fire(1), True)
# Disarmed again
send(0, 7, "3rd arrival — disarmed again")
chk("rearmed+disarmed: no fire", expect_no_fire(), True)

# ── [4] CMD_MEM_CALL — memory on call ─────────────────────────────────────
print("\n[4] CMD_MEM_CALL: cell sleeps after one-shot, wakes on MEM_CALL")
reset()
# Configure as one_shot only — fires once then sleeps
# latch_in not needed — standard two-arrival, one_shot disarms after fire
configure(0, TOPO_PASS, one_shot=1)
drain(0.2)
# Prime the cell — two arrivals to first fire
send(0, 10, "1st arrival — prime")
chk("mem: no fire on 1st", expect_no_fire(), True)
send(0, 20, "2nd arrival — fires once, then disarms")
chk("mem: fires on 2nd (one_shot)", expect_fire(1, 10), True)
# Cell now sleeping — subsequent pairs should not fire
send(0, 1, "sleeping: 1st arrival")
chk("mem: silent 1st while sleeping", expect_no_fire(), True)
send(0, 2, "sleeping: 2nd arrival")
chk("mem: silent 2nd while sleeping", expect_no_fire(), True)
# MEM_CALL — rearms for one more fire
send_cmd(CMD_MEM_CALL, 0, label="MEM_CALL cell0")
drain(0.5)
send(0, 30, "1st after MEM_CALL")
chk("mem: no fire on 1st after MEM_CALL", expect_no_fire(), True)
send(0, 40, "2nd after MEM_CALL — fires once")
chk("mem: fires on 2nd after MEM_CALL", expect_fire(1, 30), True)
# Sleeping again
send(0, 1, "sleeping again: 1st")
chk("mem: silent again 1st", expect_no_fire(), True)
send(0, 2, "sleeping again: 2nd")
chk("mem: silent again 2nd", expect_no_fire(), True)
# Second MEM_CALL
send_cmd(CMD_MEM_CALL, 0, label="MEM_CALL cell0 again")
drain(0.5)
send(0, 50, "1st after 2nd MEM_CALL")
chk("mem: no fire on 1st after 2nd MEM_CALL", expect_no_fire(), True)
send(0, 60, "2nd after 2nd MEM_CALL — fires")
chk("mem: fires on 2nd after 2nd MEM_CALL", expect_fire(1, 50), True)

# ── [5] CMD_SET_LOGICAL — physical to logical address switch ──────────────
print("\n[5] CMD_SET_LOGICAL: switch cell from physical to logical address mode")
reset()
# Configure cell 0 — in physical mode, listens on CELL_ID=0
configure(0, TOPO_PASS)
drain(0.2)
# Confirm it responds to addr=0 (physical ID) in physical mode
send(0, 42, "1st arrival at physical addr 0")
chk("physical mode: no fire on 1st", expect_no_fire(), True)
send(0, 99, "2nd arrival at physical addr 0")
chk("physical mode: fires at physical addr", expect_fire(1), True)
# Now switch to logical address 0x10
send_cmd(CMD_SET_LOGICAL, 0,
         payload=0x0010,
         label="SET_LOGICAL cell0 -> logical addr 0x10")
drain(0.3)
# Addr 0 (old physical) should no longer trigger
send(0, 1, "arrival at old physical addr 0 — should be ignored")
chk("logical mode: ignores old physical addr", expect_no_fire(), True)
send(0, 2, "2nd at old physical — still ignored")
chk("logical mode: still ignores physical", expect_no_fire(), True)
# Logical addr 0x10 should now trigger
send(0x10, 10, "1st arrival at logical addr 0x10")
chk("logical mode: no fire on 1st at logical addr", expect_no_fire(), True)
send(0x10, 20, "2nd arrival at logical addr 0x10")
chk("logical mode: fires at logical addr", expect_fire(1), True)

# ── Results ───────────────────────────────────────────────────────────────────
running = False
s.close()
print(f"\n=== {pass_count} passed  {fail_count} failed ===")
if fail_count == 0:
    print("ALL PASSED")
else:
    print("FAILURES DETECTED")
