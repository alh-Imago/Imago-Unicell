"""
test_noauth.py -- Strip everything back. No auth token.
Just configure and fire, see what happens.

Also tests: can we change config with wrong auth? (should be rejected)
And: does raw data write work without any command preamble?
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
BAUD = 115200

s = serial.Serial(PORT, BAUD, timeout=3)
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
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

def tx(cmd_bus, bus_addr, bus_data, label=""):
    pkt = struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data)
    if label: print(f"  {label}")
    s.write(pkt)
    time.sleep(0.005)

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

def reset():
    s.write(bytes([0x03]))
    time.sleep(0.3)
    if s.in_waiting: s.read(s.in_waiting)

# Command codes -- no auth, raw_addr bit set
NOP   = (0 << 0) | (1 << 15)   # CMD_NOP
SET_IN = (2 << 0) | (1 << 15)  # CMD_SET_INPUT_ADDR
SET_OUT= (3 << 0) | (1 << 15)  # CMD_SET_OUTPUT_ADDR
RECONF = (4 << 0) | (1 << 15)  # CMD_RECONFIGURE (no auth token)
DATA   = (1 << 0) | (1 << 15)  # CMD_DATA_WRITE
PING   = (9 << 0) | (1 << 15)  # CMD_PING

TOPO_NOT = 0b0000000001

print(f"\n=== No-auth test on {PORT} ===\n")

# ── Test 1: Configure with NO auth token ──────────────────────────────────────
print("TEST 1: Configure cell 0 with no auth token")
reset()

# Bootstrap: word 0 = auth_mask (set to 0 -- no auth)
tx(RECONF, 0, 0,           "RECONF word0: auth_mask=0 (no auth)")
# Word 1 = config
tx(NOP,    0, TOPO_NOT,    "RECONF word1: topology=NOT")
tx(SET_IN, 0, 0x1000,      "SET_IN  0x1000")
tx(SET_OUT,0, 0x2000,      "SET_OUT 0x2000")

# Ping
drain(0.1)
tx(PING, 0, 0, "PING cell 0")
evts = drain()
for _,a,d in evts:
    print(f"  PING response: addr={a:#x} data={d} "
          f"{'✓ output_addr=0x2000' if a==0x2000 else '?'}")

# Data write
drain(0.1)
tx(DATA, 0x1000, 0, "DATA 0 -> cell0 -> NOT -> 1")
evts = drain()
for _,a,d in evts:
    print(f"  Fired: addr={a:#x} data={d} "
          f"{'PASS ✓' if a==0x2000 and d==1 else 'FAIL ✗'}")

# ── Test 2: Try to reconfigure with wrong auth (should be rejected) ───────────
print("\nTEST 2: Try wrong auth reconfig (should be rejected)")
WRONG_AUTH = 0x123
RECONF_WRONG = (4 << 0) | ((WRONG_AUTH & 0x7FF) << 4) | (1 << 15)

tx(RECONF_WRONG, 0, 0x1FF, "RECONF wrong auth: try set auth_mask=0x1FF")
tx(NOP, 0, 0b0,            "RECONF word1: topology=PASS (should be rejected)")
tx(SET_IN,  0, 0x9999,     "SET_IN wrong addr (should be rejected)")
tx(SET_OUT, 0, 0x8888,     "SET_OUT wrong addr (should be rejected)")

# Now try data write -- should still work if rejection worked
drain(0.1)
tx(DATA, 0x1000, 1, "DATA 1 -> cell0 -> NOT -> 0 (if config unchanged)")
evts = drain()
for _,a,d in evts:
    print(f"  Fired: addr={a:#x} data={d} "
          f"{'Config unchanged PASS ✓' if a==0x2000 and d==0 else 'Config changed FAIL ✗'}")

# ── Test 3: 2-cell chain, no auth ─────────────────────────────────────────────
print("\nTEST 3: 2-cell chain, no auth")
reset()

tx(RECONF, 0, 0,        "Cell0: auth_mask=0")
tx(NOP,    0, TOPO_NOT, "Cell0: topology=NOT")
tx(SET_IN, 0, 0x1000,   "Cell0: in=0x1000")
tx(SET_OUT,0, 0x2000,   "Cell0: out=0x2000")

tx(RECONF, 1, 0,        "Cell1: auth_mask=0")
tx(NOP,    1, TOPO_NOT, "Cell1: topology=NOT")
tx(SET_IN, 1, 0x2000,   "Cell1: in=0x2000")
tx(SET_OUT,1, 0x3000,   "Cell1: out=0x3000")

drain(0.2)

# Ping both
for cell_id, expected_out in [(0, 0x2000), (1, 0x3000)]:
    tx(PING, cell_id, 0)
    evts = drain(0.2)
    # Filter for the expected response
    for _,a,d in evts:
        if d == cell_id:  # CELL_ID matches
            print(f"  Cell {cell_id} PING: addr={a:#x} "
                  f"{'✓' if a==expected_out else f'WRONG (expected {expected_out:#x})'}")

# Chain test
drain(0.1)
t0 = time.time()
tx(DATA, 0x1000, 0, "Inject 0 -> cell0 -> NOT -> 1 -> cell1 -> NOT -> 0")
evts = []
deadline = time.time() + 3.0
while time.time() < deadline:
    try:
        ts, addr, data = pkt_q.get(timeout=0.1)
        evts.append((ts-t0, addr, data))
        label = {0x2000:"hop1", 0x3000:"RESULT"}.get(addr, hex(addr))
        print(f"  t={( ts-t0)*1000:.2f}ms  {addr:#x}={data}  {label}")
        if addr == 0x3000:
            print(f"  Chain PASS ✓" if data==0 else f"  Chain FAIL ✗")
            break
    except queue.Empty:
        pass

if not any(a==0x3000 for _,a,_ in evts):
    if any(a==0x2000 for _,a,_ in evts):
        print("  Still stopped at hop1 ✗")
    else:
        print("  No output ✗")

running = False
time.sleep(0.05)
s.close()
print("\nDone.")
