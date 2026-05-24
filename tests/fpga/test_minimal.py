"""
test_minimal.py -- Absolute minimal test: single cell, configure, fire.
Replaces the NOT gate test from ping_test but using the bus tap.
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5
BAUD = 115200

s = serial.Serial(PORT, BAUD, timeout=3)
time.sleep(0.3)
if s.in_waiting: s.read(s.in_waiting)

# Reset array
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
    if label: print(f"  TX {label}: cmd={cmd_bus:#010x} addr={bus_addr:#010x} data={bus_data:#010x}")
    s.write(pkt)
    time.sleep(0.005)  # 5ms between each packet -- plenty of settling time

def bcmd(code, auth=0):
    return (code&0xF) | ((auth&0x7FF)<<4) | (1<<15)

def drain():
    time.sleep(0.2)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

print(f"\nMinimal single-cell test on {PORT}")
print("Cell 0: NOT  in=0x1000 out=0x2000\n")

# Step 1: Bootstrap RECONFIGURE cell 0
print("Step 1: Bootstrap (auth_mask + config)")
tx(bcmd(4, auth=0),   0, AUTH & 0x7FF, "RECONF word0 auth_mask")
tx(bcmd(0),           0, 0b0000000001,  "RECONF word1 config(NOT)")

# Step 2: Set addresses
print("Step 2: Set addresses")
tx(bcmd(2, auth=AUTH), 0, 0x1000, "SET_INPUT_ADDR  0x1000")
tx(bcmd(3, auth=AUTH), 0, 0x2000, "SET_OUTPUT_ADDR 0x2000")

# Step 3: PING -- should fire to output_addr_latch=0x2000, data=0 (CELL_ID)
print("Step 3: PING")
drain()  # clear any config noise
tx(bcmd(9), 0, 0, "PING")
evts = drain()
for ts, addr, data in evts:
    print(f"  Event: addr={addr:#010x} data={data}")
    if addr == 0x2000 and data == 0:
        print("  PING -> 0x2000 data=CELL_ID(0) PASS ✓")
    else:
        print(f"  Unexpected event")

# Step 4: Data write -- NOT(0) should give 1 at 0x2000
print("Step 4: Data write NOT(0)")
drain()
tx(bcmd(1), 0x1000, 0, "DATA_WRITE addr=0x1000 data=0")
evts = drain()
fired = False
for ts, addr, data in evts:
    print(f"  Event: addr={addr:#010x} data={data}")
    if addr == 0x2000:
        fired = True
        print(f"  Cell fired: NOT(0)={data} {'PASS ✓' if data==1 else 'FAIL ✗'}")
if not fired:
    print("  No fire ✗")

# Step 5: Data write -- NOT(1) should give 0 at 0x2000
print("Step 5: Data write NOT(1)")
drain()
tx(bcmd(1), 0x1000, 1, "DATA_WRITE addr=0x1000 data=1")
evts = drain()
fired = False
for ts, addr, data in evts:
    print(f"  Event: addr={addr:#010x} data={data}")
    if addr == 0x2000:
        fired = True
        print(f"  Cell fired: NOT(1)={data} {'PASS ✓' if data==0 else 'FAIL ✗'}")
if not fired:
    print("  No fire ✗")

running = False
time.sleep(0.05)
s.close()
print("\nDone.")
