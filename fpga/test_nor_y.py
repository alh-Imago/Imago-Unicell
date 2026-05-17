"""
test_nor_y.py — Silicon validation of Y-formation NOR(A,B)

The Y-formation:
  cell0 (addr 0 → addr 5): carries input A
  cell1 (addr 2 → addr 5): carries input B
  cell2 (addr 5 → addr 6): computes NOR(A, B)

Both cell0 and cell1 write to addr=5 (wired-OR bus).
cell2 listens on addr=5 — first arrival stores A, second fires NOR(A,B).

NOR truth table:
  NOR(0,0) = 1
  NOR(0,1) = 0
  NOR(1,0) = 0
  NOR(1,1) = 0

Tests all four input combinations.
Also verifies NOT(A) = NOR(A,A) using single cell with two arrivals.
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5

s = serial.Serial(PORT, 115200, timeout=3)
time.sleep(0.3)
if s.in_waiting: s.read(s.in_waiting)

pkt_q   = queue.Queue()
running = True

def rx_thread():
    buf = bytearray()
    while running:
        try:
            if s.in_waiting:
                buf += s.read(s.in_waiting)
        except: break
        while len(buf) >= 9:
            if buf[0] == 0x10 and len(buf) >= 9:
                addr = struct.unpack('>I', buf[1:5])[0]
                data = struct.unpack('>I', buf[5:9])[0]
                pkt_q.put(('fired', addr, data))
                buf = buf[9:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                armed  = struct.unpack('>H', buf[1:3])[0]
                cycles = struct.unpack('>I', buf[3:7])[0]
                pkt_q.put(('status', armed, cycles))
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

BROADCAST = 0x7FF
def mk_cmd(code, auth=0, cell_id=BROADCAST):
    return (code & 0xF) | ((auth & 0x7FF) << 4) | (1 << 15) | ((cell_id & 0x7FF) << 16)

CMD_DATA = mk_cmd(1)

def mk_cfg(topo, auth_mask=0, one_shot=0):
    w  = (topo & 0x3FF)
    w |= (auth_mask & 0x7FF) << 11
    w |= 1                   << 22   # start_flag
    w |= (1 if one_shot else 0) << 30
    return w

TOPO_PASS = 0b0000000000
TOPO_NOT  = 0b0000000001
TOPO_NOR  = 0b0000000100   # NOR(g0,g1) = NOR(NOT(A), NOT(B)) — AND gate
                            # For true NOR(A,B) use topology 0b000000100

def tx(cmd_bus, bus_addr, bus_data, label=""):
    pkt = struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data)
    if label: print(f"      {label}")
    s.write(pkt)
    time.sleep(0.02)

def reset():
    s.write(bytes([0x03])); time.sleep(0.5)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

def configure(cell_id, topo, in_addr, out_addr, auth=AUTH, one_shot=0):
    cfg = mk_cfg(topo, auth_mask=auth, one_shot=one_shot)
    tx(mk_cmd(2, auth, cell_id), 0, in_addr,
       f"SET_IN  cell{cell_id} addr={in_addr:#x}")
    tx(mk_cmd(3, auth, cell_id), 0, out_addr,
       f"SET_OUT cell{cell_id} addr={out_addr:#x}")
    tx(mk_cmd(4, auth, cell_id), 0, cfg,
       f"RECONF  cell{cell_id} topo={topo:#05x} cfg={cfg:#010x}")
    drain(0.1)

def send(addr, data, label=""):
    drain(0.05)
    tx(CMD_DATA, addr, data, label or f"DATA {data} -> addr {addr:#x}")
    time.sleep(0.05)

def expect_fire(out_addr, out_data, timeout=0.8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.1)
            if e[0] == 'fired':
                print(f"        [rx] fired addr={e[1]:#x} data={e[2]}")
                if e[1] == out_addr and e[2] == out_data:
                    return True
        except queue.Empty:
            pass
    return False

def expect_no_fire(timeout=0.3):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired':
                print(f"        [rx] UNEXPECTED fire addr={e[1]:#x} data={e[2]}")
                return False
        except queue.Empty:
            pass
    return True

pass_count = 0
fail_count = 0

def chk(name, got, exp):
    global pass_count, fail_count
    if got == exp:
        print(f"  PASS {name}")
        pass_count += 1
    else:
        print(f"  FAIL {name}  got={got}  exp={exp}")
        fail_count += 1

# ── MAIN ──────────────────────────────────────────────────────────────────────
print(f"\n=== test_nor_y on {PORT} auth={AUTH:#05x} ===\n")

# ── [1] NOT(A) = NOR(A,A) — single cell, two arrivals ────────────────────────
print("[1] NOT(A) = NOR(A,A) — confirmed Y-formation baseline")
print("    cell0: addr 0 -> addr 1, PASS gate (A arrives twice at addr 0)")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1)
drain(0.1)

for a_val, expected in [(0, 1), (1, 0)]:
    send(0, a_val, f"A={a_val} first arrival")
    send(0, a_val, f"A={a_val} second arrival (trigger)")
    chk(f"NOT({a_val})={expected}", expect_fire(1, expected), True)

# ── [2] Y-formation: NOR(A,B) with two separate input cells ──────────────────
print("\n[2] Y-formation NOR(A,B)")
print("    cell0: addr 0 -> addr 5  (carries A)")
print("    cell1: addr 2 -> addr 5  (carries B)")
print("    cell2: addr 5 -> addr 6  (computes NOR on two arrivals at addr 5)")
reset()
# cell0 and cell1 use PASS (just relay their input value)
# Each needs two arrivals at its own input address first
configure(0, TOPO_PASS, in_addr=0, out_addr=5)
configure(1, TOPO_PASS, in_addr=2, out_addr=5)
# cell2 listens on addr=5, computes NOR topology
configure(2, TOPO_NOR,  in_addr=5, out_addr=6)
drain(0.2)

nor_table = [(0,0,1), (0,1,0), (1,0,0), (1,1,0)]
for a_val, b_val, expected in nor_table:
    print(f"\n  NOR({a_val},{b_val})={expected}")
    # Inject A into cell0 (two arrivals to get cell0 to fire to addr=5)
    send(0, a_val, f"A={a_val} -> cell0 1st")
    send(0, a_val, f"A={a_val} -> cell0 2nd (cell0 fires to addr5)")
    time.sleep(0.1)  # wait for cell0 output to arrive at addr=5 (cell2 1st arrival)
    # Inject B into cell1 (two arrivals to get cell1 to fire to addr=5)
    send(2, b_val, f"B={b_val} -> cell1 1st")
    send(2, b_val, f"B={b_val} -> cell1 2nd (cell1 fires to addr5, triggers cell2)")
    chk(f"NOR({a_val},{b_val})={expected}", expect_fire(6, expected), True)
    drain(0.2)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n=== {pass_count} passed  {fail_count} failed ===")
if fail_count == 0:
    print("ALL PASSED")
else:
    print("FAILURES DETECTED")

running = False
time.sleep(0.05)
s.close()
