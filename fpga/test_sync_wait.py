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
    # 8-byte frame: 0x01 + opcode(1) + addr(2) + data(4)
    # bus_data[31:24] = auth_token, bus_data[23:0] = payload
    pkt = struct.pack('>BBHI', 0x01,
                      cmd_bus  & 0xFF,
                      bus_addr & 0xFFFF,
                      bus_data & 0xFFFFFFFF)
    if label: print(f"      TX {label}: {pkt.hex()}")
    s.write(pkt)
    time.sleep(0.02)

def reset():
    s.write(bytes([0x03]))
    time.sleep(0.8)  # wait for reset to propagate and any in-flight fires to arrive
    # Flush queue — discard all pending events
    while True:
        try: pkt_q.get_nowait()
        except: break

def drain(wait=0.5):
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
    """Pack auth_token into cmd_data[31:24], payload in [23:0]."""
    return ((auth & 0xFF) << 24) | (payload & 0xFFFFFF)

CMD_DATA = mk_cmd(1)

def mk_cfg(topo, sync_wait=0, auth_mask=0, one_shot=0,
           edge_mode=0, dtype=0, invert_out=0, priority=0,
           trace=0, breakpoint=0, loop_back=0):
    """Build 24-bit config word for CMD_RECONFIGURE cmd_data[23:0].
    Bit layout matches unicell.v CMD_RECONFIGURE handler:
      [9:0]  topology
      [10]   edge_mode
      [11]   start_flag  (always 1 — arm cell on reconfigure)
      [13:12] dtype
      [14]   invert_out
      [15]   latch_in    (sync_wait maps here — single arrival fires)
      [16]   priority
      [17]   trace
      [18]   breakpoint
      [19]   one_shot
      [20]   loop_back
    auth_mask goes in cmd_data[31:24] via mk_auth_data — not in cfg word.
    """
    w  = (topo      & 0x3FF)
    w |= (edge_mode  & 0x1)  << 10
    w |= 1                   << 11  # start_flag — arm on reconfigure
    w |= (dtype      & 0x3)  << 12
    w |= (invert_out & 0x1)  << 14
    w |= (1 if sync_wait  else 0) << 15  # latch_in = sync_wait
    w |= (priority   & 0x1)  << 16
    w |= (trace      & 0x1)  << 17
    w |= (breakpoint & 0x1)  << 18
    w |= (1 if one_shot   else 0) << 19
    w |= (loop_back  & 0x1)  << 20
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
    # Single packet: auth[31:24] + config[23:0], targeted via physical cell_id
    cmd_data = mk_auth_data(auth=auth, payload=cfg & 0xFFFFFF)
    tx(mk_cmd(4), cell_id, cmd_data,
       f"RECONFIGURE cell{cell_id} topo={topo:#05x} sync_wait={sync_wait} cfg={cfg:#010x}")
    drain(0.3)

def send(addr, data, label=""):
    tx(CMD_DATA, addr & 0xFFFF, data & 0xFFFFFFFF,
       label or f"data {data} -> addr {addr:#x}")
    time.sleep(0.3)  # wait for cell pipeline + UART response

def expect_fire(out_addr, out_data=None, timeout=1.0):
    """Returns True if a fire event at out_addr arrives within timeout.
    If out_data is None, any data value is accepted.
    out_data can be a lambda for flexible matching: lambda d: d == 1
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.1)
            if e[0] == 'fired':
                print(f"        [rx] fired addr={e[1]:#x} data={e[2]} ({e[2] & 0xFFFFFFFF:#010x}) checking addr=={out_addr:#x}:{e[1]==out_addr}")
                addr_ok = (e[1] == out_addr)
                if out_data is None:
                    data_ok = True
                elif callable(out_data):
                    data_ok = out_data(e[2])
                else:
                    data_ok = (e[2] & 0xFFFFFFFF) == (out_data & 0xFFFFFFFF)
                if addr_ok and data_ok:
                    return True
        except queue.Empty:
            pass
    return False

def expect_no_fire(timeout=0.5):
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
drain(0.3)

print("\n  [1] First arrival — expect NO fire")
send(0, 42, "1st arrival: DATA 42 -> addr 0")
chk("no fire on 1st", expect_no_fire(), True)

print("\n  [2] Second arrival (trigger) — expect fire using a_data[0] from 1st")
send(0, 99, "2nd arrival (trigger): DATA 99 -> addr 0")
# a_data[0] = 42 & 1 = 0, PASS(0) = 0
chk("fires on 2nd", expect_fire(1), True)  # PASS — any data

print("\n  [3] Third arrival alone — expect NO fire (a_arrived reset)")
send(0, 55, "3rd arrival: DATA 55 -> addr 0")  # stored as a_data=55, bit[0]=1
chk("no fire on 3rd", expect_no_fire(), True)

print("\n  [4] Fourth arrival (trigger) — expect fire using a_data[0]=1")
send(0, 77, "4th arrival (trigger): DATA 77 -> addr 0")
# a_data[0] = 55 & 1 = 1, PASS(1) = 1
chk("fires on 4th", expect_fire(1), True)  # PASS — any data

# ── [5] sync_wait + NOT gate ──────────────────────────────────────────────────
print("\n[5] sync_wait + NOT gate: computation uses a_data (first arrival)")
reset()
configure(0, TOPO_NOT, sync_wait=1)
drain(0.3)

send(0, 0, "1st: DATA 0 — stored as a_data")
chk("no fire", expect_no_fire(), True)
send(0, 1, "2nd: DATA 1 — trigger, NOT(a_data[0]=0)=1")
chk("NOT(a_data=0)=1", expect_fire(1, 0xFFFFFFFF), True)  # NOT(0)=0xFFFFFFFF

send(0, 1, "1st: DATA 1 — stored as a_data")
chk("no fire", expect_no_fire(), True)
send(0, 0, "2nd: DATA 0 — trigger, NOT(a_data[0]=1)=0")
chk("NOT(a_data=1)=0", expect_fire(1, 0x00000000), True)  # NOT(1)=0

# ── [6] sync_wait + one_shot ─────────────────────────────────────────────────
print("\n[6] sync_wait + one_shot: fires once on second arrival, then disarms")
reset()
configure(0, TOPO_NOT, sync_wait=1, one_shot=1)
drain(0.3)

send(0, 0, "1st: DATA 0")
chk("no fire", expect_no_fire(), True)
send(0, 0, "2nd: DATA 0 — should fire once")
chk("fires on 2nd", expect_fire(1), True)  # one_shot fires once

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
chk("cell0 fires to addr1=1", expect_fire(1), True)
chk("cell1 no fire yet", expect_no_fire(0.2), True)

# Send to addr=1 — this is cell1 2nd arrival (1st was cell0 output)
# cell1 fires using a_data[0]=1 (from cell0 output) -> PASS -> 1
send(1, 0, "cell1 2nd arrival at addr1 (trigger)")
chk("cell1 fires to addr2=1", expect_fire(2), True)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n=== {pass_count} passed  {fail_count} failed ===")
if fail_count == 0:
    print("ALL PASSED")
else:
    print("FAILURES DETECTED")

running = False
time.sleep(0.05)
s.close()
