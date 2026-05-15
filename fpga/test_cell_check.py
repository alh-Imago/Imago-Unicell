"""
test_cell_check.py -- Verify each cell's input/output address configuration.

For each cell:
  1. Write data to its expected input address
  2. Check if it fires to its expected output address
  3. Report pass/fail

This tells us exactly which cells are configured correctly.
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5
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

def tx(cmd_bus, bus_addr, bus_data):
    s.write(struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data))
    time.sleep(0.005)

def bcmd(code, auth=0):
    return (code&0xF) | ((auth&0x7FF)<<4) | (1<<15)

def drain(wait=0.15):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

def configure(cell_id, topo, sw, in_addr, out_addr, is_boot=False):
    """Safe: auth -> addresses -> arm with real topology."""
    cfg = (topo & 0x3FF) | ((1 if sw else 0) << 10)
    # Phase 1: Bootstrap auth, safe arm (PASS topology)
    tx(bcmd(4, auth=0), cell_id, AUTH & 0x7FF)
    tx(bcmd(0),         cell_id, 0)       # PASS -- safe
    # Phase 2: Set addresses
    tx(bcmd(2, auth=AUTH), cell_id, in_addr)
    tx(bcmd(3, auth=AUTH), cell_id, out_addr)
    # Phase 3: Arm with real topology
    tx(bcmd(4, auth=AUTH), cell_id, cfg)

# Address map
IN0=0x1000; BUS01=0x2000; BUS12=0x3000; BUS23=0x4000
BUS35=0x5000; IN4=0x6000; RESULT=0x7000

print(f"\nCell configuration check on {PORT}\n")

# Configure all 6 cells
print("Configuring...")
configure(0, 0b1, False, IN0,   BUS01,  is_boot=True)
configure(1, 0b1, False, BUS01, BUS12)
configure(2, 0b1, False, BUS12, BUS23)
configure(3, 0b1, False, BUS23, BUS35)
configure(4, 0b1, False, IN4,   BUS35)
configure(5, 0b0, True,  BUS35, RESULT)
drain(0.3)

# Cell config table
cell_cfg = [
    (0, IN0,   BUS01,  "NOT"),
    (1, BUS01, BUS12,  "NOT"),
    (2, BUS12, BUS23,  "NOT"),
    (3, BUS23, BUS35,  "NOT"),
    (4, IN4,   BUS35,  "NOT fast"),
    (5, BUS35, RESULT, "SYNC_WAIT"),
]

print(f"{'Cell':>4}  {'in_addr':>12}  {'out_addr':>12}  {'type':>10}  {'result':>10}")
print(f"{'----':>4}  {'-------':>12}  {'--------':>12}  {'----':>10}  {'------':>10}")

all_pass = True
for cell_id, in_addr, out_addr, ctype in cell_cfg:
    # Write to input address, check for fire at output address
    drain(0.05)
    tx(bcmd(1), in_addr, 0)  # CMD_DATA_WRITE
    evts = drain(0.2)

    fired_at = [(a,d) for _,a,d in evts]
    correct = any(a == out_addr for a,d in fired_at)
    wrong   = [(a,d) for a,d in fired_at if a != out_addr]

    status = "PASS ✓" if correct else "FAIL ✗"
    if not correct: all_pass = False

    fired_str = f"{out_addr:#010x}" if correct else \
                (f"fired at {fired_at[0][0]:#010x}" if fired_at else "no fire")

    print(f"  {cell_id:>2}  {in_addr:#012x}  {out_addr:#012x}  {ctype:>10}  {status} {fired_str}")

    if wrong:
        for a,d in wrong:
            print(f"      also fired: {a:#010x} data={d}")

print()
if all_pass:
    print("All cells configured correctly ✓")
else:
    print("Some cells misconfigured -- check above")

running = False
time.sleep(0.05)
s.close()
print("Done.")
