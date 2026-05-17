"""
test_state_inspect.py v3 — unicell v2 command latch protocol

Configure sequence (v2):
  1. CMD_SET_INPUT_ADDR  (code 2, no auth needed)
  2. CMD_SET_OUTPUT_ADDR (code 3, no auth needed)
  3. CMD_RECONFIGURE     (code 4, boot: auth_mask=0 so accepted unconditionally)
     payload = full 32-bit command latch word (mk_cfg)

All in one pass — no two-word bootstrap, no separate arm step.
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
        while len(buf) >= 9:
            if buf[0] == 0x10 and len(buf) >= 9:
                addr = struct.unpack('>I', buf[1:5])[0]
                data = struct.unpack('>I', buf[5:9])[0]
                pkt_q.put(('fired', addr, data))
                buf = buf[9:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                armed  = struct.unpack('>H', buf[1:3])[0]
                cycles = struct.unpack('>I', buf[3:7])[0]
                pkt_q.put(('status', armed, cycles))
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

# ── Packet format: 0x01 + cmd_bus(4BE) + bus_addr(4BE) + bus_data(4BE) ────────
def tx(cmd_bus, bus_addr, bus_data, label=""):
    pkt = struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data)
    if label: print(f"      {label}")
    s.write(pkt)
    time.sleep(0.02)

# ── Single-byte control commands ──────────────────────────────────────────────
def reset():
    s.write(bytes([0x03])); time.sleep(0.5)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def get_status():
    s.write(bytes([0x04])); time.sleep(0.3)
    for e in drain(0.2):
        if e[0] == 'status': return e[1], e[2]
    return None, None

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

# ── Command bus word builders ──────────────────────────────────────────────────
# cmd_bus[3:0]  = command code
# cmd_bus[14:4] = auth token
# cmd_bus[15]   = raw_addr (always 1 from host)
def mk_cmd(code, auth=0):
    return (code & 0xF) | ((auth & 0x7FF) << 4) | (1 << 15)

CMD_NOP     = mk_cmd(0)
CMD_DATA    = mk_cmd(1)
CMD_PING    = mk_cmd(9)

def cmd_reconf(auth=0):         return mk_cmd(4, auth)
def cmd_set_in(cell_id=0):     return (mk_cmd(2) | ((cell_id & 0x7FF) << 16))
def cmd_set_out(cell_id=0):    return (mk_cmd(3) | ((cell_id & 0x7FF) << 16))
def cmd_freeze(auth=0):        return mk_cmd(5, auth)
def cmd_release(auth=0):       return mk_cmd(6, auth)

# ── Command latch word builder (32-bit) ───────────────────────────────────────
# bit 9:0   topology
# bit 10    sync_wait
# bit 21:11 auth_mask (stored in cell, zeroed in debug)
# bit 22    start_flag (1=armed)
# bit 24:23 dtype
# bit 25    invert_out
# bit 26    latch_in
# bit 27    priority
# bit 28    trace
# bit 29    breakpoint
# bit 30    one_shot
# bit 31    loop_back
def mk_cfg(topo, auth_mask=0, sync_wait=0, dtype=0,
           invert_out=0, latch_in=0, priority=0,
           trace=0, breakpoint=0, one_shot=0, loop_back=0):
    w  = (topo & 0x3FF)
    w |= (1 if sync_wait  else 0) << 10
    w |= (auth_mask & 0x7FF)      << 11
    w |= 1                        << 22   # start_flag always set
    w |= (dtype & 0x3)            << 23
    w |= (1 if invert_out else 0) << 25
    w |= (1 if latch_in   else 0) << 26
    w |= (1 if priority   else 0) << 27
    w |= (1 if trace      else 0) << 28
    w |= (1 if breakpoint else 0) << 29
    w |= (1 if one_shot   else 0) << 30
    w |= (1 if loop_back  else 0) << 31
    return w

# Topology constants
TOPO_PASS = 0b0000000000
TOPO_NOT  = 0b0000000001
TOPO_NOR  = 0b0000000100

# ── Configure a cell — v2 protocol ───────────────────────────────────────────
def configure_cell(cell_id, topo, in_addr, out_addr, auth=AUTH):
    """
    v2 configure sequence:
      1. SET_INPUT_ADDR  — no auth needed
      2. SET_OUTPUT_ADDR — no auth needed
      3. RECONFIGURE     — boot: auth_mask=0 so accepted unconditionally
                           payload = full command latch word with auth embedded
    """
    print(f"    Cell {cell_id}: topo={topo:#05x}  "
          f"in={in_addr:#010x}  out={out_addr:#010x}")

    # Step 1+2: set addresses (no auth required)
    tx(cmd_set_in(cell_id),  0, in_addr,  f"SET_INPUT_ADDR  {in_addr:#010x}")
    tx(cmd_set_out(cell_id), 0, out_addr, f"SET_OUTPUT_ADDR {out_addr:#010x}")

    # Step 3: reconfigure — boot bypass (auth_mask=0 on fresh cell)
    # Embed auth into latch so subsequent commands need it
    cfg = mk_cfg(topo, auth_mask=auth)
    tx(cmd_reconf(), 0, cfg, f"RECONFIGURE  cfg={cfg:#010x}  (boot, auth_mask=0)")

def verify_cell(cell_id, in_addr, out_addr, in_data, expected):
    drain(0.1)
    tx(CMD_DATA, in_addr, in_data,
       f"DATA {in_data} -> cell{cell_id}  expect {expected} at {out_addr:#x}")
    evts = drain(0.4)
    fired = [(e[1], e[2]) for e in evts if e[0] == 'fired']
    ok = any(a == out_addr and d == expected for a, d in fired)
    tag = 'PASS ✓' if ok else 'FAIL ✗'
    print(f"      Verify: {tag}  "
          f"fired={[(hex(a), d) for a, d in fired]}")
    return ok

# ── MAIN ──────────────────────────────────────────────────────────────────────
print(f"\n=== State inspection v3 on {PORT} auth={AUTH:#05x} ===\n")

print("Step 1: Reset")
reset()
armed, cycles = get_status()
print(f"  armed_count={armed}  cycles={cycles}\n")

print("Step 2: Configure cell 0 (NOT gate, 0x1000 -> 0x2000)")
configure_cell(0, TOPO_NOT, 0x1000, 0x2000)
time.sleep(0.1)
armed, _ = get_status()
print(f"  armed_count={armed}")
verify_cell(0, 0x1000, 0x2000, 0, 1)   # NOT(0)=1
verify_cell(0, 0x1000, 0x2000, 1, 0)   # NOT(1)=0

print("\nStep 3: Configure cell 1 (NOT gate, 0x2000 -> 0x3000)")
configure_cell(1, TOPO_NOT, 0x2000, 0x3000)
time.sleep(0.1)
armed, _ = get_status()
print(f"  armed_count={armed}")
verify_cell(1, 0x2000, 0x3000, 0, 1)   # NOT(0)=1
verify_cell(1, 0x2000, 0x3000, 1, 0)   # NOT(1)=0

print("\nStep 4: Chain test (cell0 -> cell1 -> result)")
print("  Write 0 to 0x1000: NOT->1 at 0x2000, NOT->0 at 0x3000")
drain(0.2)
t0 = time.time()
tx(CMD_DATA, 0x1000, 0, "DATA 0 -> 0x1000")
evts = []
deadline = time.time() + 3.0
while time.time() < deadline:
    try:
        e = pkt_q.get(timeout=0.2)
        if e[0] == 'fired':
            addr, data = e[1], e[2]
            evts.append((time.time() - t0, addr, data))
            label = {0x2000: 'cell0 out', 0x3000: 'RESULT'}.get(addr, hex(addr))
            print(f"    t={( time.time()-t0)*1000:7.2f}ms  {addr:#010x}={data}  {label}")
    except queue.Empty:
        pass

ok = any(a == 0x3000 and d == 0 for _, a, d in evts)
print(f"\n  Chain: {'PASS ✓' if ok else 'FAIL ✗'}")

print("\nStep 5: PING all cells")
drain(0.1)
tx(CMD_PING, 0, 0, "PING broadcast")
evts = drain(0.5)
fired = [(e[1], e[2]) for e in evts if e[0] == 'fired']
print(f"  Responses: {[(hex(a), d) for a, d in fired]}")
print(f"  Cells responding: {len(fired)}/8")

running = False
time.sleep(0.05)
s.close()
print("\nDone.")
