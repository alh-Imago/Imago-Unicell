"""
test_chain2.py -- 2-cell chain test to isolate single-hop feedback.

Cell 0: NOT  in=0x1000 -> 0x2000
Cell 1: NOT  in=0x2000 -> 0x3000  (result)

Input=0 -> NOT -> 1 -> NOT -> 0
Expected: 0x3000 = 0

This is the minimal chain test. If this works, 4-cell works.
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5

s = serial.Serial(PORT, 115200, timeout=3)
time.sleep(0.3)
if s.in_waiting: s.read(s.in_waiting)

# Reset array to clear any state from previous tests
print("Resetting array...")
s.write(bytes([0x03]))
time.sleep(0.2)
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
    if label: print(f"  TX {label}")
    s.write(pkt)
    time.sleep(0.005)

def bcmd(code, auth=0):
    return (code&0xF) | ((auth&0x7FF)<<4) | (1<<15)

def freeze():
    s.write(bytes([0x06]))
    time.sleep(0.05)

def release():
    s.write(bytes([0x07]))
    time.sleep(0.05)

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

print(f"\n2-cell NOT chain on {PORT}")
print("Cell 0: NOT 0x1000->0x2000")
print("Cell 1: NOT 0x2000->0x3000")
print("Expected: 0x3000=0 (NOT(NOT(0))=0)\n")

# Configure each cell: auth_mask word + config word + addresses
# After reset, every cell has auth_mask=0 so every cell needs bootstrap sequence.
def configure(cell_id, topo, in_addr, out_addr):
    """Safe: auth -> addresses -> arm with real topology."""
    # Phase 1: Bootstrap auth, safe arm (PASS topology)
    tx(bcmd(4, auth=0), cell_id, AUTH & 0x7FF)
    tx(bcmd(0),         cell_id, 0)       # PASS -- safe
    # Phase 2: Set addresses
    tx(bcmd(2, AUTH),   cell_id, in_addr)
    tx(bcmd(3, AUTH),   cell_id, out_addr)
    # Phase 3: Arm with real topology
    tx(bcmd(4, AUTH),   cell_id, topo)

freeze()
print("Config cell 0...")
configure(0, 0b1, 0x1000, 0x2000)
print("Config cell 1...")
configure(1, 0b1, 0x2000, 0x3000)

release()
drain(0.3)

# Verify both cells armed
print("\nVerify cells armed...")
for cell_id, out_addr in [(0, 0x2000), (1, 0x3000)]:
    tx(bcmd(9), cell_id, 0)  # PING
    evts = drain(0.2)
    for _,a,d in evts:
        print(f"  Cell {cell_id} PING: addr={a:#x} data={d} "
              f"{'✓' if a==out_addr else '?'}")

# Inject and watch
print("\nInject 0 to cell 0 (0x1000)...")
while not pkt_q.empty():
    try: pkt_q.get_nowait()
    except: break

t0 = time.time()
tx(bcmd(1), 0x1000, 0)

print("Watching (3s)...")
events = []
deadline = time.time() + 3.0
while time.time() < deadline:
    try:
        ts, addr, data = pkt_q.get(timeout=0.1)
        t_ms = (ts-t0)*1000
        events.append((t_ms, addr, data))
        label = {0x2000:"hop1(cell1 in)", 0x3000:"RESULT"}.get(addr, hex(addr))
        print(f"  t={t_ms:.2f}ms  {addr:#x}={data}  {label}")
        if addr == 0x3000:
            print(f"\n  Chain complete! Result={data} "
                  f"{'PASS ✓' if data==0 else 'FAIL ✗'}")
            break
    except queue.Empty:
        pass

if not any(a==0x3000 for _,a,_ in events):
    if any(a==0x2000 for _,a,_ in events):
        print("\n  Stopped at hop1 -- feedback not working ✗")
    else:
        print("\n  No output at all ✗")

running = False
time.sleep(0.05)
s.close()
print("Done.")
