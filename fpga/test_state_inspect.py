"""
test_state_inspect.py -- Cell state inspection test.

Steps:
  1. Reset array
  2. Set auth (bootstrap cell 0)
  3. STATE SAVE 1: show all cell latches
  4. Configure cell 0 (NOT, in=0x1000, out=0x2000)
  5. STATE SAVE 2: show all cell latches
  6. Configure cell 1 (NOT, in=0x2000, out=0x3000)
  7. STATE SAVE 3: show all cell latches

State is read via PING (shows output_addr_latch) and
direct data writes (shows if cell fires = confirms input_addr_latch,
topology, and armed state).

No freeze. No data injection after config. Pure state inspection.
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
                pkt_q.put((time.time(), addr, data))
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
    if label: print(f"    TX {label}")
    s.write(pkt)
    time.sleep(0.010)  # 10ms settle between every packet

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

def reset():
    print("  Sending reset (0x03)...")
    s.write(bytes([0x03]))
    time.sleep(0.5)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break
    print("  Reset done.")

def status():
    s.write(bytes([0x04]))
    time.sleep(0.3)
    evts = drain()
    for e in evts:
        if isinstance(e, tuple) and e[0] == 'status':
            print(f"    Status: armed_count={e[1]} cycles={e[2]}")

# Command words
NOP    = (0<<0)|(1<<15)
SET_IN = (2<<0)|(1<<15)
SET_OUT= (3<<0)|(1<<15)
RECONF = (4<<0)|(1<<15)
DATA   = (1<<0)|(1<<15)
PING   = (9<<0)|(1<<15)
NOT_TOPO = 0b0000000001  # GS_NOT topology

NUM_CELLS = 6

def state_save(label):
    """Read state of all cells via PING and test writes."""
    print(f"\n  ── STATE SAVE: {label} ──")
    drain(0.1)

    print(f"  {'Cell':>4}  {'PING addr':>12}  {'PING data':>10}  {'armed?':>8}")
    print(f"  {'----':>4}  {'--------':>12}  {'---------':>10}  {'------':>8}")

    for cell_id in range(NUM_CELLS):
        # PING: fires to output_addr_latch, data=CELL_ID
        drain(0.05)
        tx(PING, cell_id, 0)
        time.sleep(0.1)
        evts = drain(0.1)

        # Collect fired events
        fired = [(a,d) for _,a,d in evts if isinstance(_, float)]

        # Find response matching this cell's CELL_ID
        cell_resp = [(a,d) for a,d in fired if d == cell_id]
        other     = [(a,d) for a,d in fired if d != cell_id]

        if cell_resp:
            a, d = cell_resp[0]
            print(f"  {cell_id:>4}  {a:#012x}  {d:>10}  {'YES' if d==cell_id else '?':>8}")
        elif fired:
            # Got a response but CELL_ID doesn't match -- another cell responded
            print(f"  {cell_id:>4}  {'(collision)':>12}  {fired[0][1]:>10}  {'?':>8}  ← got addr={fired[0][0]:#x}")
        else:
            print(f"  {cell_id:>4}  {'<no response>':>12}  {'':>10}  {'NO':>8}")

    status()

# ── MAIN ──────────────────────────────────────────────────────────────────────
print(f"\n=== State inspection test on {PORT} auth={AUTH:#05x} ===\n")

# ── Step 1: Reset ─────────────────────────────────────────────────────────────
print("Step 1: Reset")
reset()
state_save("after reset")

# ── Step 2: Set auth on cell 0 (bootstrap) ───────────────────────────────────
print("\nStep 2: Bootstrap cell 0 (set auth_mask)")
tx(RECONF, 0, AUTH & 0x7FF, "RECONF word0: auth_mask")
# Config word: just arm with NO topology yet (pass-through)
tx(NOP,    0, 0b0,           "RECONF word1: topology=PASS, arm")
drain(0.2)
state_save("after bootstrap cell 0 (auth set, no input/output addr yet)")

# ── Step 3: Full config of cell 0 ────────────────────────────────────────────
print("\nStep 3: Configure cell 0 (NOT, in=0x1000, out=0x2000)")
tx(RECONF, 0, AUTH & 0x7FF, "RECONF word0: auth (cell already has it)")
tx(NOP,    0, NOT_TOPO,     "RECONF word1: topology=NOT")
tx(SET_IN, 0, 0x1000,       "SET_IN  0x1000")
tx(SET_OUT,0, 0x2000,       "SET_OUT 0x2000")
drain(0.2)

# Verify by writing to input and checking output
print("  Verifying cell 0: write 0 to 0x1000, expect 1 at 0x2000")
drain(0.1)
tx(DATA, 0x1000, 0, "DATA 0 -> cell0 NOT -> 1?")
evts = drain(0.3)
fired = [(a,d) for _,a,d in evts if isinstance(_,float)]
ok = any(a==0x2000 and d==1 for a,d in fired)
print(f"  Verify: {'PASS ✓' if ok else 'FAIL ✗'}  fired={[(hex(a),d) for a,d in fired]}")

state_save("after cell 0 configured (NOT, 0x1000->0x2000)")

# ── Step 4: Configure cell 1 ─────────────────────────────────────────────────
print("\nStep 4: Configure cell 1 (NOT, in=0x2000, out=0x3000)")
tx(RECONF, 1, AUTH & 0x7FF, "RECONF word0: auth_mask (cell1 bootstrap)")
tx(NOP,    1, NOT_TOPO,     "RECONF word1: topology=NOT")
tx(SET_IN, 1, 0x2000,       "SET_IN  0x2000")
tx(SET_OUT,1, 0x3000,       "SET_OUT 0x3000")
drain(0.2)

# Verify cell 1
print("  Verifying cell 1: write 1 to 0x2000, expect 0 at 0x3000")
drain(0.1)
tx(DATA, 0x2000, 1, "DATA 1 -> cell1 NOT -> 0?")
evts = drain(0.3)
fired = [(a,d) for _,a,d in evts if isinstance(_,float)]
ok = any(a==0x3000 and d==0 for a,d in fired)
print(f"  Verify: {'PASS ✓' if ok else 'FAIL ✗'}  fired={[(hex(a),d) for a,d in fired]}")

state_save("after cell 1 configured (NOT, 0x2000->0x3000)")

# ── Step 5: Chain test ────────────────────────────────────────────────────────
print("\nStep 5: Chain test (cell0->cell1 via feedback)")
print("  Expected: 0 -> NOT -> 1 -> NOT -> 0 at 0x3000")
drain(0.1)
t0 = time.time()
tx(DATA, 0x1000, 0, "DATA 0 -> cell0 chain...")
evts = []
deadline = time.time() + 5.0
while time.time() < deadline:
    try:
        ts, addr, data = pkt_q.get(timeout=0.2)
        if isinstance(ts, float):
            evts.append((ts-t0, addr, data))
            print(f"  t={(ts-t0)*1000:7.2f}ms  {addr:#010x} = {data}  "
                  f"{  {0x2000:'cell0 out',0x3000:'RESULT'}.get(addr,'')}")
    except queue.Empty:
        pass

ok = any(a==0x3000 and d==0 for _,a,d in evts)
print(f"\n  Chain: {'PASS ✓' if ok else 'FAIL ✗'}")

running = False
time.sleep(0.05)
s.close()
print("\nDone.")
