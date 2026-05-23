"""
test_sync_wait.py — Silicon validation of sync_wait feature

sync_wait (cmd_latch[10], folded into topology word):
  - Cell requires TWO sequential bus arrivals at input_address before firing
  - First arrival: stored in a_data, a_arrived flag set — NO output
  - Second arrival: fires normally, a_arrived reset for next pair
  - Third arrival alone: stored again, no fire
  - Fourth arrival: fires again

Tests:
  [1] Single arrival — no fire
  [2] Second arrival — fires
  [3] Third arrival alone — no fire (reset confirmed)
  [4] Fourth arrival — fires again
  [5] sync_wait + NOT gate — correct computation on second arrival
  [6] sync_wait + one_shot — fires once on second arrival, then disarms
  [7] Interleaved: two sync_wait cells, verify no cross-triggering
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5

s = serial.Serial(PORT, 115200, timeout=3)
time.sleep(0.3)
if s.in_waiting: s.read(s.in_waiting)

pkt_q   = queue.Queue()
running = True

def rx_thread():
    buf = bytearray()
    while running:
        try:
            if s.in_waiting:
                buf += s.read(s.in_waiting)
        except: break
        while len(buf) >= 8:
            if buf[0] == 0x10 and len(buf) >= 8:
                # New fired response: 0x10 + addr(2) + data(4) + pad(2)
                addr = struct.unpack('>H', buf[1:3])[0]
                data = struct.unpack('>I', buf[3:7])[0]
                pkt_q.put(('fired', addr, data))
                buf = buf[8:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                armed  = struct.unpack('>H', buf[1:3])[0]
                cycles = struct.unpack('>I', buf[3:7])[0]
                pkt_q.put(('status', armed, cycles))
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

def tx(cmd_bus, bus_addr, bus_data, label=""):
    # New 6-byte frame: 0x01 + opcode(1) + addr(2) + data(2)
    # cmd_bus is now 8-bit opcode only
    # bus_addr is 16-bit
    # bus_data is 16-bit (carries auth_token in [15:5] for auth commands)
    pkt = struct.pack('>BBHH', 0x01,
                      cmd_bus  & 0xFF,
                      bus_addr & 0xFFFF,
                      bus_data & 0xFFFF)
    if label: print(f"      TX {label}: {pkt.hex()}")
    s.write(pkt)
    time.sleep(0.02)

def reset():
    s.write(bytes([0x03])); time.sleep(0.5)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

BROADCAST = 0xFFFF  # broadcast to all cells (use physical addr 0xFFFF)
def mk_cmd(code, auth=0, cell_id=BROADCAST):
    """Return 8-bit opcode. Auth now carried in cmd_data[15:5]."""
    return code & 0xFF

def mk_auth_data(auth=0, payload=0):
    """Pack auth_token into cmd_data[15:5], payload in [4:0]."""
    return ((auth & 0x7FF) << 5) | (payload & 0x1F)

CMD_DATA = mk_cmd(1)

def mk_cfg(topo, sync_wait=0, auth_mask=0, one_shot=0):
    w  = (topo & 0x3FF)
    w |= (1 if sync_wait else 0) << 10
    w |= (auth_mask & 0x7FF)    << 11
    w |= 1                      << 22   # start_flag
    w |= (1 if one_shot  else 0) << 30
    return w

TOPO_PASS = 0b0000000000
TOPO_NOT  = 0b0000000001

pass_count = 0
fail_count = 0

def chk(name, got, exp):
    global pass_count, fail_count
    if got == exp:
        print(f"  PASS {name}")
        pass_count += 1
    else:
        print(f"  FAIL {name}  got={got}  exp={exp}")
        fail_count += 1

def configure(cell_id, topo, sync_wait=0, one_shot=0, auth=AUTH):
    cfg = mk_cfg(topo, sync_wait=sync_wait, auth_mask=auth, one_shot=one_shot)
    # auth_token in cmd_data[15:5], cell targeted via physical ID on bus_addr
    # Send RECONFIGURE with auth token
    auth_data = mk_auth_data(auth=auth)
    tx(mk_cmd(4), cell_id, auth_data,
       f"RECONFIGURE cell{cell_id} auth")
    drain(0.05)
    # Send config word lower 16 bits via NOP
    tx(mk_cmd(0), cell_id, cfg & 0xFFFF,
       f"cfg_lo cell{cell_id} topo={topo:#05x} sync_wait={sync_wait} cfg={cfg:#010x}")
    drain(0.05)
    # Send config word upper 16 bits via NOP
    tx(mk_cmd(0), cell_id, (cfg >> 16) & 0xFFFF,
       f"cfg_hi cell{cell_id}")
    drain(0.15)

def send(addr, data, label=""):
    drain(0.05)
    tx(CMD_DATA, addr & 0xFFFF, data & 0xFFFF,
       label or f"data {data} -> addr {addr:#x}")
    time.sleep(0.05)

def expect_fire(out_addr, out_data, timeout=0.5):
    """Returns True if a matching fire event arrives within timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.1)
            if e[0] == 'fired':
                print(f"        [rx] fired addr={e[1]:#x} data={e[2]}")
                if e[1] == out_addr and e[2] == out_data:
                    return True
        except queue.Empty:
            pass
    return False

def expect_no_fire(timeout=0.3):
    """Returns True if NO fire event arrives within timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired':
                print(f"        [rx] UNEXPECTED fire addr={e[1]:#x} data={e[2]}")
                return False
        except queue.Empty:
            pass
    return True

# ── MAIN ──────────────────────────────────────────────────────────────────────
print(f"\n=== test_sync_wait on {PORT} auth={AUTH:#05x} ===\n")

reset()

# ── [1-4] Basic sync_wait behaviour — PASS gate, cell 0 ──────────────────────
print("[1-4] Basic sync_wait: PASS gate, cell 0 (addr 0 -> addr 1)")
configure(0, TOPO_PASS, sync_wait=1)
drain(0.1)

print("\n  [1] First arrival — expect NO fire")
send(0, 42, "1st arrival: DATA 42 -> addr 0")
chk("no fire on 1st", expect_no_fire(), True)

print("\n  [2] Second arrival (trigger) — expect fire using a_data[0] from 1st")
send(0, 99, "2nd arrival (trigger): DATA 99 -> addr 0")
# a_data[0] = 42 & 1 = 0, PASS(0) = 0
chk("fires on 2nd", expect_fire(1, 0), True)

print("\n  [3] Third arrival alone — expect NO fire (a_arrived reset)")
send(0, 55, "3rd arrival: DATA 55 -> addr 0")  # stored as a_data=55, bit[0]=1
chk("no fire on 3rd", expect_no_fire(), True)

print("\n  [4] Fourth arrival (trigger) — expect fire using a_data[0]=1")
send(0, 77, "4th arrival (trigger): DATA 77 -> addr 0")
# a_data[0] = 55 & 1 = 1, PASS(1) = 1
chk("fires on 4th", expect_fire(1, 1), True)

# ── [5] sync_wait + NOT gate ──────────────────────────────────────────────────
print("\n[5] sync_wait + NOT gate: computation uses a_data (first arrival)")
configure(0, TOPO_NOT, sync_wait=1)
drain(0.1)

send(0, 0, "1st: DATA 0 — stored as a_data")
chk("no fire", expect_no_fire(), True)
send(0, 1, "2nd: DATA 1 — trigger, NOT(a_data[0]=0)=1")
chk("NOT(a_data=0)=1", expect_fire(1, 1), True)

send(0, 1, "1st: DATA 1 — stored as a_data")
chk("no fire", expect_no_fire(), True)
send(0, 0, "2nd: DATA 0 — trigger, NOT(a_data[0]=1)=0")
chk("NOT(a_data=1)=0", expect_fire(1, 0), True)

# ── [6] sync_wait + one_shot ─────────────────────────────────────────────────
print("\n[6] sync_wait + one_shot: fires once on second arrival, then disarms")
configure(0, TOPO_NOT, sync_wait=1, one_shot=1)
drain(0.1)

send(0, 0, "1st: DATA 0")
chk("no fire", expect_no_fire(), True)
send(0, 0, "2nd: DATA 0 — should fire once")
chk("fires on 2nd", expect_fire(1, 1), True)

# Now disarmed — further pairs should not fire
send(0, 0, "1st after disarm")
chk("no fire after disarm 1st", expect_no_fire(), True)
send(0, 0, "2nd after disarm")
chk("no fire after disarm 2nd", expect_no_fire(), True)

# ── [7] Two sync_wait cells — chain behaviour ────────────────────────────────
print("\n[7] Two sync_wait cells — chain behaviour")
print("  cell0 output at addr=1 counts as cell1 first arrival")
reset()
configure(0, TOPO_PASS, sync_wait=1)  # cell0: addr 0 -> addr 1
configure(1, TOPO_PASS, sync_wait=1)  # cell1: addr 1 -> addr 2
drain(0.2)

# Drive cell0 once — no fire from either cell
send(0, 1, "cell0 1st arrival (data=1, bit0=1)")
chk("cell0 no fire", expect_no_fire(), True)

# Drive cell0 twice — cell0 fires (a_data[0]=1 -> PASS -> 1) to addr=1
# cell0 output at addr=1 is cell1 first arrival (a_arrived set in cell1)
send(0, 1, "cell0 2nd arrival")
chk("cell0 fires to addr1=1", expect_fire(1, 1), True)
chk("cell1 no fire yet", expect_no_fire(0.2), True)

# Send to addr=1 — this is cell1 2nd arrival (1st was cell0 output)
# cell1 fires using a_data[0]=1 (from cell0 output) -> PASS -> 1
send(1, 0, "cell1 2nd arrival at addr1 (trigger)")
chk("cell1 fires to addr2=1", expect_fire(2, 1), True)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n=== {pass_count} passed  {fail_count} failed ===")
if fail_count == 0:
    print("ALL PASSED")
else:
    print("FAILURES DETECTED")

running = False
time.sleep(0.05)
s.close()
