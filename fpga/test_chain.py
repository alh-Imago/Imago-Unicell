"""
test_chain.py -- Simple 4-cell NOT chain, no SYNC_WAIT.

Cell 0: NOT  in=0x1000 -> 0x2000
Cell 1: NOT  in=0x2000 -> 0x3000
Cell 2: NOT  in=0x3000 -> 0x4000
Cell 3: NOT  in=0x4000 -> 0x5000  (result)

Input: 0 -> NOT -> 1 -> NOT -> 0 -> NOT -> 1 -> NOT -> 0
Expected result at 0x5000: data=0 (4 NOTs of 0)
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
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

def tx(cmd_bus, bus_addr, bus_data):
    s.write(struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data))
    time.sleep(0.005)

def bcmd(code, auth=0):
    return (code&0xF) | ((auth&0x7FF)<<4) | (1<<15)

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

def configure(cell_id, in_addr, out_addr, is_boot=False):
    cfg = 0b0000000001  # NOT topology
    if is_boot:
        tx(bcmd(4, auth=0),    cell_id, AUTH & 0x7FF)
        tx(bcmd(0),            cell_id, cfg)
    else:
        tx(bcmd(4, auth=AUTH), cell_id, cfg)
    tx(bcmd(2, auth=AUTH), cell_id, in_addr)
    tx(bcmd(3, auth=AUTH), cell_id, out_addr)

LABEL = {
    0x2000: "hop1 (cell1 in)",
    0x3000: "hop2 (cell2 in)",
    0x4000: "hop3 (cell3 in)",
    0x5000: "RESULT (cell3 out)",
}

print(f"\n4-cell NOT chain on {PORT}")
print("Cell 0->1->2->3, input=0, expected result=0 (4x NOT)\n")

print("Configuring...")
configure(0, 0x1000, 0x2000, is_boot=True)
configure(1, 0x2000, 0x3000)
configure(2, 0x3000, 0x4000)
configure(3, 0x4000, 0x5000)
drain(0.3)

print("Injecting input=0 to cell 0...")
t0 = time.time()
tx(bcmd(1), 0x1000, 0)

print("\nWatching bus (5 seconds)...")
events = []
deadline = time.time() + 5.0
while time.time() < deadline:
    try:
        ts, addr, data = pkt_q.get(timeout=0.1)
        t_ms = (ts - t0) * 1000
        label = LABEL.get(addr, f"{addr:#010x}")
        events.append((t_ms, addr, data))
        print(f"  t={t_ms:8.2f}ms  {addr:#012x}  data={data}  {label}")
        if addr == 0x5000:
            print(f"\n  Chain complete! Result={data} "
                  f"{'PASS ✓' if data==0 else 'FAIL ✗'}")
            deadline = min(deadline, time.time() + 0.5)
    except queue.Empty:
        pass

if not any(a==0x5000 for _,a,_ in events):
    last = max((a for _,a,_ in events
                if a in (0x2000,0x3000,0x4000,0x5000)), default=None)
    if last:
        print(f"\n  Chain stopped at: {LABEL.get(last, hex(last))}")
    else:
        print("\n  No propagation at all")

running = False
time.sleep(0.05)
s.close()
print("Done.")
