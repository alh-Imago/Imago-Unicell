"""
test_nor_y.py — Y-formation cell feed and input_b_address status

The VM supports input_b_address (two separate input addresses per cell).
The current Verilog only has one input_address — two arrivals at same addr.

What the Verilog CAN do:
  - NOT(A): cell sees A twice at same address, computes NOT(a_data[0])
  - Y-formation delivery: cell0 fires to addr5, cell1 fires to addr5
    cell2 sees first arrival (from cell0) stored in a_data,
    second arrival (from cell1) triggers — computes using a_data only.
  - Result: cell2 outputs NOT(A) where A = cell0's output (first arrival)
    B (cell1's output) only acts as trigger, not in computation.

What requires input_b_address (TODO — Verilog feature):
  - True NOR(A,B) where A and B are different values
  - AND, OR, XOR built from NOR cells

Tests:
  [1] NOT(A) single cell — confirmed
  [2] Y-delivery: cell0->addr5 then cell1->addr5 triggers cell2
      cell2 outputs first arrival value (A path only — B is trigger only)
  [3] Verify B-is-trigger-only: swap A and B, output follows A not B
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

print(f"\n=== test_nor_y on {PORT} auth={AUTH:#05x} ===")
print("Note: Verilog has one input_address. input_b_address is TODO.")
print("      B arrival triggers computation but only A value is used.\n")

# ── [1] NOT(A) ────────────────────────────────────────────────────────────────
print("[1] NOT(A) — single cell, two arrivals same address")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1)
flush()
for a_val, expected in [(0, 1), (1, 0)]:
    flush()
    send_twice(0, a_val, f"NOT({a_val}): A arrives twice at addr 0")
    evts = collect(0.8)
    result = [d for a,d in evts if a == 1]
    chk(f"NOT({a_val})={expected}", expected in result, True)

# ── [2] Y-delivery: A path fires first, B path triggers ─────────────────────
print("\n[2] Y-delivery — cell0 output (A) stored, cell1 output (B) triggers")
print("    cell2 outputs NOT(A) — B is trigger only (input_b_address TODO)")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=5)  # NOT(A) -> addr5
configure(1, TOPO_NOT, in_addr=2, out_addr=5)  # NOT(B) -> addr5 (trigger)
configure(2, TOPO_PASS, in_addr=5, out_addr=6) # PASS(a_data) = NOT(A)
flush(0.2)

# A=0: NOT(A)=1 stored in cell2.a_data, NOT(B) triggers, output=NOT(A)=1
# A=1: NOT(A)=0 stored in cell2.a_data, NOT(B) triggers, output=NOT(A)=0
for a_val, b_val, expected_out in [(0, 1, 1), (1, 0, 0), (0, 0, 1), (1, 1, 0)]:
    print(f"\n  A={a_val} B={b_val} -> NOT(A)={1-a_val} stored, NOT(B)={1-b_val} triggers -> out={expected_out}")
    flush(0.2)
    send_twice(0, a_val, f"A={a_val} -> cell0 -> NOT({a_val})={1-a_val} to addr5")
    time.sleep(0.15)
    send_twice(2, b_val, f"B={b_val} -> cell1 -> NOT({b_val})={1-b_val} to addr5 (trigger)")
    evts = collect(1.0)
    result = [d for a,d in evts if a == 6]
    chk(f"cell2 out=NOT(A)={expected_out}", expected_out in result, True)

# ── [3] B-is-trigger-only confirmation ───────────────────────────────────────
print("\n[3] Confirm B is trigger only — vary B, output follows A not B")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=5)
configure(1, TOPO_NOT, in_addr=2, out_addr=5)
configure(2, TOPO_PASS, in_addr=5, out_addr=6)
flush(0.2)

# Fix A=1 (NOT(A)=0), vary B — output should always be 0 (NOT(A)) regardless of B
print("  Fixed A=1 (NOT(A)=0 stored). Varying B.")
for b_val in [0, 1]:
    flush(0.2)
    send_twice(0, 1, f"A=1 -> NOT(1)=0 to addr5")
    time.sleep(0.15)
    send_twice(2, b_val, f"B={b_val} -> trigger (should not affect output)")
    evts = collect(1.0)
    result = [d for a,d in evts if a == 6]
    chk(f"B={b_val}: out=NOT(A)=0 (B ignored)", 0 in result, True)

print(f"\n=== {pass_count} passed  {fail_count} failed ===")
print("ALL PASSED" if fail_count == 0 else "FAILURES DETECTED")
print("\nNOTE: True NOR(A,B) requires input_b_address in Verilog (TODO)")
running = False
time.sleep(0.05)
s.close()
