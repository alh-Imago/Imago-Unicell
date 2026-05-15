"""
test_state_inspect.py v2 -- Cell state inspection with correct auth protocol.

The correct configure sequence after reset:
  1. Bootstrap (auth_mask=0 on cell): send auth_mask word + config word
  2. After bootstrap, cell has auth_mask set -- ALL subsequent commands need AUTH
  3. SET_IN and SET_OUT must include AUTH token in cmd_bus

This test verifies each step explicitly.
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5

s = serial.Serial(PORT, 115200, timeout=3)
time.sleep(0.3)
if s.in_waiting: s.read(s.in_waiting)

pkt_q  = queue.Queue()
running = True

def rx_thread():
    buf = bytearray()
    while running:
        try:
            if s.in_waiting:
                buf += s.read(s.in_waiting)
        except: break
        while len(buf) >= 10:
            if buf[0] == 0x10:
                addr = struct.unpack('>I', buf[1:5])[0]
                data = struct.unpack('>I', buf[5:9])[0]
                pkt_q.put(('fired', addr, data))
                buf = buf[10:]
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
    pkt = struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data)
    if label: print(f"    {label}")
    s.write(pkt)
    time.sleep(0.015)  # 15ms settle

def freeze():
    s.write(bytes([0x06]))
    time.sleep(0.05)

def release():
    s.write(bytes([0x07]))
    time.sleep(0.05)

def drain(wait=0.4):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

def reset():
    s.write(bytes([0x03]))
    time.sleep(0.5)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def get_status():
    s.write(bytes([0x04]))
    time.sleep(0.3)
    for e in drain():
        if e[0]=='status':
            return e[1], e[2]
    return None, None

# Build command bus words
def cmd_noauth(code): return (code&0xF)|(1<<15)
def cmd_auth(code):   return (code&0xF)|((AUTH&0x7FF)<<4)|(1<<15)

NOP    = cmd_noauth(0)
PING   = cmd_noauth(9)
DATA   = cmd_noauth(1)
NOT_TOPO = 0b0000000001

def configure_cell(cell_id, topo, in_addr, out_addr):
    """
    Safe configure: set auth, addresses THEN arm.
    No cell fires during configuration of others.

    Phase 1: Bootstrap auth_mask only (cell disarmed)
    Phase 2: Set addresses (cell still disarmed)
    Phase 3: Arm with topology (cell now live)
    """
    print(f"    Configuring cell {cell_id}: topo={topo:#05x} "
          f"in={in_addr:#010x} out={out_addr:#010x}")

    # Phase 1: Set auth_mask only -- pass topology=0 (PASS, no fire)
    # Cell enters RCFG_CONFIG waiting for config word
    tx(cmd_noauth(4), cell_id, AUTH & 0x7FF, f"  word0: auth_mask={AUTH:#05x}")
    # Send topology=0 (PASS) -- cell arms but won't fire (no match yet)
    tx(NOP,           cell_id, 0,             f"  word1: topology=PASS (safe arm)")

    # Phase 2: Set addresses (auth_mask now set, use AUTH)
    tx(cmd_auth(2), cell_id, in_addr,  f"  SET_IN  {in_addr:#010x}")
    tx(cmd_auth(3), cell_id, out_addr, f"  SET_OUT {out_addr:#010x}")

    # Phase 3: Now arm with real topology (cell_id targeted)
    tx(cmd_auth(4), cell_id, topo, f"  ARM topology={topo:#05x}")

def verify_cell(cell_id, in_addr, out_addr, in_data, expected_out_data):
    """Write to cell input, verify it fires to correct output address."""
    drain(0.1)
    tx(DATA, in_addr, in_data,
       f"  DATA {in_data} -> cell{cell_id} -> expect {expected_out_data} at {out_addr:#x}")
    evts = drain(0.4)
    fired = [(a,d) for e in evts if e[0]=='fired' for a,d in [(e[1],e[2])]]
    ok = any(a==out_addr and d==expected_out_data for a,d in fired)
    status = 'PASS ✓' if ok else 'FAIL ✗'
    print(f"    Verify: {status}  fired={[(hex(a),d) for a,d in fired]}")
    return ok

def state_save(label):
    """Show armed_count and test each cell responds to PING."""
    print(f"\n  ── STATE: {label} ──")
    armed, cycles = get_status()
    print(f"    armed_count={armed}  cycles={cycles}")

    # Individual cell verification via targeted data writes
    # (PING has no addr_match so all cells respond simultaneously)
    print(f"    {'Cell':>4}  {'Status':>8}")
    for cell_id in range(6):
        # PING to see if cell is alive
        drain(0.05)
        tx(PING, cell_id, 0)
        evts = drain(0.2)
        fired = [(a,d) for e in evts if e[0]=='fired' for a,d in [(e[1],e[2])]]
        # Cell responds with data=CELL_ID
        mine = [d for a,d in fired if d==cell_id]
        print(f"    {cell_id:>4}  {'ALIVE' if mine else 'silent':>8}  "
              f"out_addr={fired[0][0]:#010x if fired else 0:#010x}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
print(f"\n=== State inspection v2 on {PORT} auth={AUTH:#05x} ===\n")

print("Step 1: Reset")
reset()
armed, cycles = get_status()
print(f"  armed_count={armed}  cycles={cycles}")

print("\nFreezing array during configuration...")
freeze()
print("\nStep 2: Configure cell 0 (NOT, 0x1000->0x2000)")
configure_cell(0, NOT_TOPO, 0x1000, 0x2000)
armed, _ = get_status()
print(f"  armed_count after cell0 config: {armed}")
verify_cell(0, 0x1000, 0x2000, 0, 1)  # NOT(0)=1
verify_cell(0, 0x1000, 0x2000, 1, 0)  # NOT(1)=0

print("\nStep 3: Configure cell 1 (NOT, 0x2000->0x3000)")
configure_cell(1, NOT_TOPO, 0x2000, 0x3000)
armed, _ = get_status()
print(f"  armed_count after cell1 config: {armed}")
verify_cell(1, 0x2000, 0x3000, 0, 1)  # NOT(0)=1
verify_cell(1, 0x2000, 0x3000, 1, 0)  # NOT(1)=0

print("\nStep 4: Chain test (cell0 out -> cell1 in -> result)")
print("  Expected: write 0 to 0x1000 -> NOT->1 -> NOT->0 at 0x3000")
drain(0.2)
t0 = time.time()
tx(DATA, 0x1000, 0, "DATA 0 to cell0 input")
evts = []
deadline = time.time() + 5.0
while time.time() < deadline:
    try:
        e = pkt_q.get(timeout=0.2)
        if e[0] == 'fired':
            addr, data = e[1], e[2]
            evts.append((time.time()-t0, addr, data))
            label = {0x2000:'cell0->cell1', 0x3000:'RESULT'}.get(addr, hex(addr))
            print(f"  t={(time.time()-t0)*1000:7.2f}ms  {addr:#010x}={data}  {label}")
    except queue.Empty:
        pass

ok = any(a==0x3000 and d==0 for _,a,d in evts)
print(f"\n  Chain: {'PASS ✓' if ok else 'FAIL ✗'}")

running = False
time.sleep(0.05)
s.close()
print("Done.")
