"""
test_noauth.py -- Diagnostic tests, no auth complexity.
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
s = serial.Serial(PORT, 115200, timeout=3)
time.sleep(0.3)
if s.in_waiting: s.read(s.in_waiting)

pkt_q = queue.Queue()
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
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

# Command bus words (no auth)
NOP    = (0<<0)|(1<<15)
SET_IN = (2<<0)|(1<<15)
SET_OUT= (3<<0)|(1<<15)
RECONF = (4<<0)|(1<<15)
DATA   = (1<<0)|(1<<15)
PING   = (9<<0)|(1<<15)
NOT    = 0b0000000001

print(f"\n=== Diagnostic tests on {PORT} ===\n")

# ── TEST 1: Single cell works ─────────────────────────────────────────────────
print("TEST 1: Single cell (cell 0)")
reset()
tx(RECONF, 0, 0,    "auth_mask=0")
tx(NOP,    0, NOT,  "topology=NOT")
tx(SET_IN, 0, 0x1000, "in=0x1000")
tx(SET_OUT,0, 0x2000, "out=0x2000")
drain(0.1)
tx(DATA, 0x1000, 0, "write 0 -> NOT -> 1")
evts = drain()
ok = any(a==0x2000 and d==1 for _,a,d in evts)
print(f"  {'PASS ✓' if ok else 'FAIL ✗'}  fired={[(hex(a),d) for _,a,d in evts]}")

# ── TEST 2: Direct write to cell 1 (no chain, just check cell 1 arms) ─────────
print("\nTEST 2: Cell 1 armed and fires on direct host write")
reset()
# Configure both cells
for cell_id, in_addr, out_addr in [(0,0x1000,0x2000),(1,0x2000,0x3000)]:
    tx(RECONF,  cell_id, 0,        f"cell{cell_id} auth_mask=0")
    tx(NOP,     cell_id, NOT,      f"cell{cell_id} topology=NOT")
    tx(SET_IN,  cell_id, in_addr,  f"cell{cell_id} in={in_addr:#x}")
    tx(SET_OUT, cell_id, out_addr, f"cell{cell_id} out={out_addr:#x}")
drain(0.2)

# Write directly to cell 1's input from host
tx(DATA, 0x2000, 1, "Direct host write to 0x2000 (cell1 input)")
evts = drain()
ok = any(a==0x3000 and d==0 for _,a,d in evts)
print(f"  Cell1 direct: {'PASS ✓' if ok else 'FAIL ✗'}  "
      f"fired={[(hex(a),d) for _,a,d in evts]}")

# ── TEST 3: Chain with filtered addresses ────────────────────────────────────
# Cell 0 outputs to 0x0100 (filtered, not forwarded to UART)
# Cell 1 outputs to 0x5000 (above filter >= 0x3000, forwarded)
# This ensures uart_bridge is idle when cell 1 fires
print("\nTEST 3: 2-cell chain (cell0->0x0100 filtered, cell1->0x5000 visible)")
reset()
tx(RECONF, 0, 0,       "cell0 auth")
tx(NOP,    0, NOT,     "cell0 topo")
tx(SET_IN, 0, 0x1000,  "cell0 in=0x1000")
tx(SET_OUT,0, 0x0100,  "cell0 out=0x0100 (filtered)")
tx(RECONF, 1, 0,       "cell1 auth")
tx(NOP,    1, NOT,     "cell1 topo")
tx(SET_IN, 1, 0x0100,  "cell1 in=0x0100")
tx(SET_OUT,1, 0x5000,  "cell1 out=0x5000 (visible)")
drain(0.2)

t0 = time.time()
tx(DATA, 0x1000, 0, "write 0 -> cell0 NOT -> 1 -> cell1 NOT -> 0 at 0x5000")
evts = []
deadline = time.time() + 2.0
while time.time() < deadline:
    try:
        ts,addr,data = pkt_q.get(timeout=0.1)
        evts.append((ts-t0, addr, data))
        print(f"  t={(ts-t0)*1000:.2f}ms  {addr:#x}={data}")
    except queue.Empty:
        pass

ok = any(a==0x5000 and d==0 for _,a,d in evts)
print(f"  Chain: {'PASS ✓' if ok else 'FAIL ✗'}  "
      f"(expected 0x5000=0)  fired={[(hex(a),d) for _,a,d in evts]}")

# ── TEST 4: Wrong auth rejected ───────────────────────────────────────────────
print("\nTEST 4: Wrong auth reconfig rejected")
reset()
tx(RECONF, 0, 0,    "cell0 auth_mask=0")
tx(NOP,    0, NOT,  "cell0 topology=NOT")
tx(SET_IN, 0, 0x1000, "cell0 in=0x1000")
tx(SET_OUT,0, 0x2000, "cell0 out=0x2000")
drain(0.1)

# Confirm working
tx(DATA, 0x1000, 0)
evts = drain()
print(f"  Before wrong auth: fired={[(hex(a),d) for _,a,d in evts]}")

# Try wrong auth reconfig
WRONG = (4<<0)|(0x123<<4)|(1<<15)
tx(WRONG, 0, 0x1FF, "wrong auth: try set auth_mask=0x1FF")
tx(NOP,   0, 0b0,   "wrong config word: topology=PASS")
tx(SET_IN, 0, 0x9999, "wrong SET_IN")
drain(0.1)

# Should still fire as before
tx(DATA, 0x1000, 1)
evts = drain()
ok = any(a==0x2000 and d==0 for _,a,d in evts)
print(f"  After wrong auth: fired={[(hex(a),d) for _,a,d in evts]}")
print(f"  Auth rejected: {'PASS ✓' if ok else 'FAIL ✗'}")

running = False
time.sleep(0.05)
s.close()
print("\nDone.")
