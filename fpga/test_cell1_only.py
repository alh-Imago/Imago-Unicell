"""
test_cell1_only.py -- Configure ONLY cell 1, skip cell 0.
If cell 1 works alone, the issue is interaction with cell 0.
If cell 1 fails alone, the issue is in cell 1's bootstrap itself.
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5

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
                pkt_q.put((addr, data))
                buf = buf[10:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                armed = struct.unpack('>H', buf[1:3])[0]
                cycles= struct.unpack('>I', buf[3:7])[0]
                pkt_q.put(('s', armed, cycles))
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

def tx(cmd, ba, bd, label=""):
    s.write(struct.pack('>BIII', 0x01, cmd, ba, bd))
    if label: print(f"  {label}")
    time.sleep(0.020)  # 20ms settle

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

def status():
    s.write(bytes([0x04]))
    time.sleep(0.3)
    for e in drain():
        if e[0]=='s': print(f"  armed={e[1]} cycles={e[2]}")

NA  = lambda c: (c&0xF)|(1<<15)
A   = lambda c: (c&0xF)|((AUTH&0x7FF)<<4)|(1<<15)

print(f"\n=== Cell 1 only test {PORT} ===\n")

# Reset
s.write(bytes([0x03]))
time.sleep(0.5)
drain()
print("Reset done")
status()

# Configure ONLY cell 1 (skip cell 0)
print("\nConfiguring cell 1 only (bus_addr=1)...")
tx(NA(4), 1, AUTH & 0x7FF, "RECONF word0: auth_mask")
tx(NA(0), 1, 0b1,           "RECONF word1: topology=NOT")
tx(A(2),  1, 0x2000,        "SET_IN  0x2000")
tx(A(3),  1, 0x3000,        "SET_OUT 0x3000")

status()

# PING via probe address
print("\nProbe ping cell 1 -> 0xF001...")
tx(A(3), 1, 0xF001, "SET_OUT -> probe 0xF001")
drain(0.1)
tx(NA(9), 1, 0, "PING cell 1")
evts = drain(0.5)
fired = [(a,d) for e in evts if len(e)==2 for a,d in [(e[0],e[1])]]
ok = any(a==0xF001 for a,d in fired)
print(f"  PING: {'PASS ✓' if ok else 'FAIL ✗'}  fired={[(hex(a),d) for a,d in fired]}")
if ok:
    tx(A(3), 1, 0x3000, "Restore SET_OUT 0x3000")

# Direct data write to cell 1
print("\nDirect write to 0x2000 (cell 1 input)...")
drain(0.1)
tx(NA(1), 0x2000, 0, "DATA 0 -> cell1 NOT -> 1 at 0x3000")
evts = drain(0.5)
fired = [(a,d) for e in evts if len(e)==2 for a,d in [(e[0],e[1])]]
ok = any(a==0x3000 and d==1 for a,d in fired)
print(f"  Verify: {'PASS ✓' if ok else 'FAIL ✗'}  fired={[(hex(a),d) for a,d in fired]}")

running = False
time.sleep(0.05)
s.close()
print("\nDone.")
