"""
test_sync_wait.py -- SYNC_WAIT timing test for unicell_v3

Topology:
  Cell 0: NOT  in=0x1000 -> 0x2000
  Cell 1: NOT  in=0x2000 -> 0x3000
  Cell 2: NOT  in=0x3000 -> 0x4000
  Cell 3: NOT  in=0x4000 -> 0x5000  (slow path -- 4 hops)

  Cell 4: NOT  in=0x6000 -> 0x5000  (fast path -- 1 hop, arrives FIRST)

  Cell 5: SYNC_WAIT  in=0x5000 -> 0x7000
          Holds after cell 4 arrives. Fires when cell 3 arrives.

Expected: result at 0x7000 after slow chain catches up.
Ordering: 0x5000 fired twice (cell4 first, cell3 second), then 0x7000.
"""

import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5
BAUD = 115200

# -- Address map ---------------------------------------------------------------
IN0    = 0x1000
BUS01  = 0x2000
BUS12  = 0x3000
BUS23  = 0x4000
BUS35  = 0x5000   # slow path (cell 3) AND fast path (cell 4) both arrive here
IN4    = 0x6000
RESULT = 0x7000

# -- Command constants ---------------------------------------------------------
CMD_NOP    = 0
CMD_SET_IN = 2
CMD_SET_OUT= 3
CMD_RECONF = 4
CMD_DATA   = 1
CMD_PING   = 9

TOPO_NOT  = 0b0000000001
TOPO_PASS = 0b0000000000

CTYPE_STANDARD = 0b00
DTYPE_NUMERIC  = 0b00

def build_cmd(code, auth=0):
    w  = (code & 0xF)
    w |= ((auth & 0x7FF) << 4)
    w |= (1 << 15)  # raw_addr
    return w

def build_config(topo, sw=False):
    w  = (topo & 0x3FF)
    w |= ((1 if sw else 0) << 10)
    return w

# -- Serial --------------------------------------------------------------------
print(f"Opening {PORT} auth={AUTH:#05x}...")
s = serial.Serial(PORT, BAUD, timeout=3)
time.sleep(0.3)
if s.in_waiting: s.read(s.in_waiting)

fired_q = queue.Queue()
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
            if buf[0] == 0x10:
                addr = struct.unpack('>I', buf[1:5])[0]
                data = struct.unpack('>I', buf[5:9])[0]
                fired_q.put((time.time(), addr, data))
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
    if label:
        print(f"  TX {label}")
    s.write(pkt)

def configure(cell_id, topo, sw, in_addr, out_addr,
              is_boot=False, label=""):
    print(f"  Cell {cell_id} ({label}): "
          f"topo={topo:#05x} sw={sw} "
          f"in={in_addr:#010x} out={out_addr:#010x}")
    cfg = build_config(topo, sw)
    if is_boot:
        inject(build_cmd(CMD_RECONF, auth=0), cell_id, AUTH & 0x7FF)
        time.sleep(0.002)
        inject(build_cmd(CMD_NOP), cell_id, cfg)
    else:
        inject(build_cmd(CMD_RECONF, auth=AUTH), cell_id, cfg)
    time.sleep(0.002)
    inject(build_cmd(CMD_SET_IN,  auth=AUTH), cell_id, in_addr)
    time.sleep(0.001)
    inject(build_cmd(CMD_SET_OUT, auth=AUTH), cell_id, out_addr)
    time.sleep(0.001)

# -- Configure -----------------------------------------------------------------
print("\n== SYNC_WAIT timing test ==")
print("""
  Cell 0: NOT  0x1000->0x2000
  Cell 1: NOT  0x2000->0x3000
  Cell 2: NOT  0x3000->0x4000
  Cell 3: NOT  0x4000->0x5000  (slow -- 4 hops)
  Cell 4: NOT  0x6000->0x5000  (fast -- 1 hop, arrives first)
  Cell 5: SYNC_WAIT  0x5000->0x7000
""")

print("-- Configure cells --")
configure(0, TOPO_NOT,  False, IN0,   BUS01,  is_boot=True,  label="NOT")
configure(1, TOPO_NOT,  False, BUS01, BUS12,  is_boot=False, label="NOT")
configure(2, TOPO_NOT,  False, BUS12, BUS23,  is_boot=False, label="NOT")
configure(3, TOPO_NOT,  False, BUS23, BUS35,  is_boot=False, label="NOT")
configure(4, TOPO_NOT,  False, IN4,   BUS35,  is_boot=False, label="NOT fast")
configure(5, TOPO_PASS, True,  BUS35, RESULT, is_boot=False, label="SYNC_WAIT")
time.sleep(0.1)

# -- Inject inputs -------------------------------------------------------------
print("\n-- Inject inputs --")
while not fired_q.empty():
    try: fired_q.get_nowait()
    except: break

t0 = time.time()
# Fire fast path first, then slow path
inject(build_cmd(CMD_DATA), IN4,  0, "fast path: cell 4 in=0 -> NOT -> 1")
inject(build_cmd(CMD_DATA), IN0,  1, "slow path: cell 0 in=1 -> chain...")

# -- Watch propagation ---------------------------------------------------------
print("\n-- Propagation --")
name = {
    BUS01:  "0x2000 cell1 in",
    BUS12:  "0x3000 cell2 in",
    BUS23:  "0x4000 cell3 in",
    BUS35:  "0x5000 cell5 in (SYNC_WAIT)",
    RESULT: "0x7000 RESULT",
}

events = []
deadline = time.time() + 5.0
while time.time() < deadline:
    try:
        ts, addr, data = fired_q.get(timeout=0.1)
        rel = ts - t0
        label = name.get(addr, f"{addr:#010x}")
        events.append((rel, addr, data))
        print(f"  t={rel:.4f}s  {label} = {data}")
        # keep collecting all events
    except queue.Empty:
        pass

# -- Result --------------------------------------------------------------------
print("\n-- Result --")
sw_events = [(t,a,d) for t,a,d in events if a == BUS35]
result    = [(t,a,d) for t,a,d in events if a == RESULT]

if len(sw_events) >= 2:
    print(f"  SYNC_WAIT arrival 1: t={sw_events[0][0]:.4f}s data={sw_events[0][2]}")
    print(f"  SYNC_WAIT arrival 2: t={sw_events[1][0]:.4f}s data={sw_events[1][2]}")
    gap = sw_events[1][0] - sw_events[0][0]
    print(f"  Gap between arrivals: {gap*1000:.2f}ms -- fast arrived first, slow caught up")
elif len(sw_events) == 1:
    print(f"  Only 1 arrival at SYNC_WAIT -- chain incomplete")
else:
    print(f"  No arrivals at SYNC_WAIT")

if result:
    print(f"\n  RESULT at 0x7000 = {result[0][2]}  t={result[0][0]:.4f}s  PASS ✓")
else:
    print(f"\n  No result at 0x7000 ✗")
    print(f"  Total events: {len(events)}")
    for t,a,d in events:
        print(f"    t={t:.4f}s  {a:#010x}={d}")

test_single_chain(s, fired_q, AUTH)
running = False
time.sleep(0.05)
s.close()
print("\nDone.")


def test_single_chain(s, fired_q, AUTH):
    """Simplest possible chain: cell 0 NOT -> cell 1 NOT -> result."""
    print("\n\n== SINGLE CHAIN TEST (2 hops) ==")
    print("  Cell 0: NOT in=0x1000 -> 0x2000")
    print("  Cell 1: NOT in=0x2000 -> 0x3000")

    def inj(cmd_bus, bus_addr, bus_data):
        s.write(struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data))
        time.sleep(0.002)

    def bcmd(code, auth=0):
        return (code & 0xF) | ((auth & 0x7FF) << 4) | (1 << 15)

    # Reconfigure cell 0 (already has auth set)
    inj(bcmd(4, AUTH), 0, 0b0000000001)           # RECONF topology=NOT
    inj(bcmd(2, AUTH), 0, 0x1000)                  # SET_IN
    inj(bcmd(3, AUTH), 0, 0x2000)                  # SET_OUT
    # Reconfigure cell 1
    inj(bcmd(4, AUTH), 1, 0b0000000001)
    inj(bcmd(2, AUTH), 1, 0x2000)
    inj(bcmd(3, AUTH), 1, 0x3000)
    time.sleep(0.1)

    # Clear queue
    while not fired_q.empty():
        try: fired_q.get_nowait()
        except: break

    t0 = time.time()
    inj(bcmd(1), 0x1000, 0)   # DATA_WRITE: 0 -> cell 0 -> NOT -> 1

    events = []
    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            ts, addr, data = fired_q.get(timeout=0.1)
            events.append((ts-t0, addr, data))
            print(f"  t={ts-t0:.4f}s  {addr:#010x} = {data}")
        except queue.Empty:
            pass

    if any(a == 0x3000 for _,a,_ in events):
        print("  Chain propagated to 0x3000 PASS ✓")
    elif any(a == 0x2000 for _,a,_ in events):
        print("  Only reached 0x2000 -- chain stopped at 1 hop ✗")
    else:
        print("  No output ✗")
