"""
test_sync_wait.py -- SYNC_WAIT timing test with raw bus tap

Topology:
  Cell 0: NOT  in=0x1000 -> 0x2000  (slow chain start)
  Cell 1: NOT  in=0x2000 -> 0x3000
  Cell 2: NOT  in=0x3000 -> 0x4000
  Cell 3: NOT  in=0x4000 -> 0x5000  (slow -- 4 hops)
  Cell 4: NOT  in=0x6000 -> 0x5000  (fast -- 1 hop, arrives first)
  Cell 5: SYNC_WAIT in=0x5000 -> 0x7000

The raw bus tap streams every internal bus transaction to the host.
The host timestamps each packet as it arrives (UART buffers, order preserved).
Fast path (cell4, data=1) and slow path (cell3, data=0) are distinguishable.
Result at 0x7000 marks the end.
"""

import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5
BAUD = 115200

# Address map
IN0    = 0x1000
BUS01  = 0x2000
BUS12  = 0x3000
BUS23  = 0x4000
BUS35  = 0x5000   # both fast and slow paths arrive here
IN4    = 0x6000
RESULT = 0x7000

# Command codes
CMD_NOP = 0; CMD_SET_IN = 2; CMD_SET_OUT = 3
CMD_RECONF = 4; CMD_DATA = 1; CMD_PING = 9

TOPO_NOT  = 0b0000000001
TOPO_PASS = 0b0000000000

def bcmd(code, auth=0):
    return (code & 0xF) | ((auth & 0x7FF) << 4) | (1 << 15)

def bcfg(topo, sw=False):
    return (topo & 0x3FF) | ((1 if sw else 0) << 10)

# Serial
print(f"Opening {PORT} auth={AUTH:#05x}...")
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
        except Exception:
            break
        while len(buf) >= 10:
            if buf[0] == 0x10 and len(buf) >= 10:
                addr = struct.unpack('>I', buf[1:5])[0]
                data = struct.unpack('>I', buf[5:9])[0]
                pkt_q.put((time.time(), addr, data))
                buf = buf[10:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

t = threading.Thread(target=rx_thread, daemon=True)
t.start()

def inject(cmd_bus, bus_addr, bus_data, label=""):
    pkt = struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data)
    if label: print(f"  TX {label}")
    s.write(pkt)

def configure(cell_id, topo, sw, in_addr, out_addr,
              is_boot=False, label=""):
    print(f"  Cell {cell_id} ({label})")
    cfg = bcfg(topo, sw)
    if is_boot:
        inject(bcmd(CMD_RECONF, auth=0), cell_id, AUTH & 0x7FF)
        time.sleep(0.002)
        inject(bcmd(CMD_NOP),            cell_id, cfg)
    else:
        # Always send auth_mask word after reset
        inject(bcmd(CMD_RECONF, auth=0), cell_id, AUTH & 0x7FF)
        time.sleep(0.005)
        inject(bcmd(CMD_NOP),            cell_id, cfg)
    time.sleep(0.010)
    inject(bcmd(CMD_SET_IN,  auth=AUTH), cell_id, in_addr)
    time.sleep(0.010)
    inject(bcmd(CMD_SET_OUT, auth=AUTH), cell_id, out_addr)
    time.sleep(0.010)

# Address labels
LABEL = {
    0x0000: "host-config",
    IN0:    "IN0(cell0)",
    BUS01:  "->cell1",
    BUS12:  "->cell2",
    BUS23:  "->cell3",
    BUS35:  "->SYNC_WAIT(cell5)",
    IN4:    "IN4(cell4)",
    RESULT: "**RESULT**",
}

print("\n== SYNC_WAIT bus tap test ==")
print("""
  Cell 0-3: NOT chain (slow, 4 hops) -> 0x5000
  Cell 4:   NOT (fast, 1 hop)        -> 0x5000
  Cell 5:   SYNC_WAIT 0x5000         -> 0x7000
  Bus tap streams all transactions to host.
""")

print("-- Configure --")
configure(0, TOPO_NOT,  False, IN0,   BUS01,  is_boot=True,  label="NOT")
configure(1, TOPO_NOT,  False, BUS01, BUS12,  is_boot=False, label="NOT")
configure(2, TOPO_NOT,  False, BUS12, BUS23,  is_boot=False, label="NOT")
configure(3, TOPO_NOT,  False, BUS23, BUS35,  is_boot=False, label="NOT")
configure(4, TOPO_NOT,  False, IN4,   BUS35,  is_boot=False, label="NOT fast")
configure(5, TOPO_PASS, True,  BUS35, RESULT, is_boot=False, label="SYNC_WAIT")
time.sleep(0.15)

# Drain any config noise from tap
while not pkt_q.empty():
    try: pkt_q.get_nowait()
    except: break

print("\n-- PING check (confirm cells armed) --")
time.sleep(0.1)
while not pkt_q.empty():
    try: pkt_q.get_nowait()
    except: break

for cell_id in range(6):
    s.write(struct.pack('>BIII', 0x01,
            bcmd(CMD_PING), cell_id, 0))
    time.sleep(0.05)
    events_ping = []
    deadline_p = time.time() + 0.2
    while time.time() < deadline_p:
        try:
            ts, addr, data = pkt_q.get(timeout=0.05)
            events_ping.append((addr, data))
        except queue.Empty:
            break
    if events_ping:
        print(f"  Cell {cell_id}: responded {[(hex(a),d) for a,d in events_ping]}")
    else:
        print(f"  Cell {cell_id}: no response")

time.sleep(0.1)
while not pkt_q.empty():
    try: pkt_q.get_nowait()
    except: break

print("\n-- Inject (fast first, then slow chain) --")
t0 = time.time()
inject(bcmd(CMD_DATA), IN4, 0, "fast: cell4 in=0 -> NOT -> 1 -> 0x5000")
inject(bcmd(CMD_DATA), IN0, 1, "slow: cell0 in=1 -> chain -> 0x5000")
t_inject = time.time()

print("\n-- Bus tap stream (raw, in arrival order) --")
print(f"  {'seq':>4}  {'t_ms':>8}  {'addr':>12}  {'data':>6}  label")
print(f"  {'-'*4}  {'-'*8}  {'-'*12}  {'-'*6}  {'-'*20}")

events   = []
seq      = 0
deadline = time.time() + 4.0
found_result = False

while time.time() < deadline:
    try:
        ts, addr, data = pkt_q.get(timeout=0.1)
        t_ms = (ts - t0) * 1000
        label = LABEL.get(addr, f"0x{addr:08x}")
        seq += 1
        events.append((t_ms, addr, data, label))
        print(f"  {seq:>4}  {t_ms:>8.2f}  {addr:#012x}  {data:>6}  {label}")
        if addr == RESULT:
            found_result = True
            # keep collecting a bit more
            deadline = min(deadline, time.time() + 0.5)
    except queue.Empty:
        if found_result:
            break

print("\n-- Analysis --")
# Find first arrival at SYNC_WAIT
sw_events = [(t,a,d,l) for t,a,d,l in events if a == BUS35]
results   = [(t,a,d,l) for t,a,d,l in events if a == RESULT]

if sw_events:
    print(f"  SYNC_WAIT arrivals: {len(sw_events)}")
    for i,(t,a,d,l) in enumerate(sw_events):
        path = "fast (cell4)" if d == 1 else "slow (cell3)"
        print(f"    arrival {i+1}: t={t:.2f}ms data={d} -- {path}")
    if len(sw_events) >= 2:
        gap = sw_events[1][0] - sw_events[0][0]
        print(f"    gap = {gap:.2f}ms")

if results:
    t_result = results[0][0]
    print(f"\n  RESULT at 0x7000: t={t_result:.2f}ms data={results[0][2]}  PASS ✓")
    if sw_events:
        print(f"  Time from first SYNC_WAIT arrival to result: "
              f"{t_result - sw_events[0][0]:.2f}ms")
else:
    print(f"\n  No result at 0x7000 ✗")
    if not sw_events:
        print("  SYNC_WAIT never received any input")
    elif len(sw_events) == 1:
        print("  Only one arrival at SYNC_WAIT -- second never came")
        # Show what DID arrive
        chain_addrs = [a for _,a,_,_ in events]
        last = max((a for a in chain_addrs
                    if a in (BUS01,BUS12,BUS23,BUS35)), default=None)
        if last:
            print(f"  Chain reached: {LABEL.get(last, hex(last))}")

print(f"\n  Total bus events seen: {len(events)}")

running = False
time.sleep(0.05)
s.close()
print("Done.")
