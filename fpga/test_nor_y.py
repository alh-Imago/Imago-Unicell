"""
test_nor_y.py — Y-formation AND(A,B) = NOR(NOT(A), NOT(B))

Single cell only computes single-input functions — input_val is one wire.
True two-input logic needs a Y-formation:

  cell0: NOT(A) — fires to addr=5
  cell1: NOT(B) — fires to addr=5
  cell2: NOR(NOT(A), NOT(B)) = AND(A,B) — listens on addr=5

AND truth table:
  AND(0,0)=0  AND(0,1)=0  AND(1,0)=0  AND(1,1)=1
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
        except:
            break
        while len(buf) >= 9:
            if buf[0] == 0x10 and len(buf) >= 9:
                addr = struct.unpack('>I', buf[1:5])[0]
                data = struct.unpack('>I', buf[5:9])[0]
                pkt_q.put(('fired', addr, data))
                buf = buf[9:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

BROADCAST = 0x7FF
def mk_cmd(code, auth=0, cell_id=BROADCAST):
    return (code & 0xF) | ((auth & 0x7FF) << 4) | (1 << 15) | ((cell_id & 0x7FF) << 16)

CMD_DATA = mk_cmd(1)
TOPO_PASS = 0b0000000000
TOPO_NOT  = 0b0000000001
TOPO_NOR  = 0b0000000100

def mk_cfg(topo, auth_mask=0, one_shot=0):
    w  = (topo & 0x3FF)
    w |= (auth_mask & 0x7FF) << 11
    w |= 1 << 22
    w |= (1 if one_shot else 0) << 30
    return w

def tx(cmd, addr, data, label=""):
    if label: print(f"      {label}")
    s.write(struct.pack('>BIII', 0x01, cmd, addr, data))
    time.sleep(0.025)

def reset():
    s.write(bytes([0x03]))
    time.sleep(0.5)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def flush(wait=0.15):
    time.sleep(wait)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def configure(cell_id, topo, in_addr, out_addr, auth=AUTH, one_shot=0):
    cfg = mk_cfg(topo, auth_mask=auth, one_shot=one_shot)
    tx(mk_cmd(2, auth, cell_id), 0, in_addr)
    tx(mk_cmd(3, auth, cell_id), 0, out_addr)
    tx(mk_cmd(4, auth, cell_id), 0, cfg,
       f"cell{cell_id}: topo={topo:#05x} in={in_addr:#x} out={out_addr:#x}")
    time.sleep(0.05)

def send_twice(addr, data, label=""):
    if label: print(f"      {label}")
    tx(CMD_DATA, addr, data)
    time.sleep(0.03)
    tx(CMD_DATA, addr, data)

def collect(timeout=1.0):
    evts = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired':
                evts.append((e[1], e[2]))
                print(f"        [rx] addr={e[1]:#x} data={e[2]}")
        except queue.Empty:
            pass
    return evts

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

print(f"\n=== test_nor_y on {PORT} auth={AUTH:#05x} ===\n")

# ── [1] NOT(A) baseline ───────────────────────────────────────────────────────
print("[1] NOT(A) — single cell, two arrivals")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1)
flush()
for a_val, expected in [(0, 1), (1, 0)]:
    flush()
    send_twice(0, a_val, f"NOT({a_val}): two arrivals at addr 0")
    evts = collect(0.8)
    result = [d for a,d in evts if a == 1]
    chk(f"NOT({a_val})={expected}", expected in result, True)

# ── [2] AND(A,B) = NOR(NOT(A),NOT(B)) — Y-formation ─────────────────────────
print("\n[2] AND(A,B) = NOR(NOT(A),NOT(B)) — 3-cell Y-formation")
print("    cell0 NOT(A) -> addr5, cell1 NOT(B) -> addr5, cell2 NOR -> addr6")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=5)
configure(1, TOPO_NOT, in_addr=2, out_addr=5)
configure(2, TOPO_NOR, in_addr=5, out_addr=6)
flush(0.2)

for a_val, b_val, expected in [(0,0,0),(0,1,0),(1,0,0),(1,1,1)]:
    print(f"\n  AND({a_val},{b_val})={expected}")
    flush(0.2)
    # A path: send A twice -> cell0 fires NOT(A) to addr5 (cell2 1st arrival)
    send_twice(0, a_val, f"A={a_val} -> cell0 -> NOT({a_val})={1-a_val} to addr5")
    time.sleep(0.15)
    # B path: send B twice -> cell1 fires NOT(B) to addr5 (cell2 2nd arrival)
    send_twice(2, b_val, f"B={b_val} -> cell1 -> NOT({b_val})={1-b_val} to addr5")
    evts = collect(1.0)
    result = [d for a,d in evts if a == 6]
    chk(f"AND({a_val},{b_val})={expected}", expected in result, True)

print(f"\n=== {pass_count} passed  {fail_count} failed ===")
print("ALL PASSED" if fail_count == 0 else "FAILURES DETECTED")
running = False
time.sleep(0.05)
s.close()
