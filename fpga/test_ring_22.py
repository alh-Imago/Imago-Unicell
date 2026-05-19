"""
test_ring_2.py — Complete 8-Cell Stateful Lock & Streaming Pipeline
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
TOPO_NOT  = 0b0000000001
TOPO_PASS = 0b0000000000

def mk_cfg(topo, auth_mask=0, one_shot=0, latch_in=0, invert_out=0, edge_mode=0):
    w  = (topo & 0x3FF)
    w |= (auth_mask & 0x7FF) << 11
    w |= 1 << 22                       # start_flag
    w |= (1 if edge_mode else 0) << 10 # Bit 10: Edge Mode
    w |= (1 if latch_in else 0) << 26  # Bit 26: Latch In
    w |= (1 if invert_out else 0) << 25 # Bit 25: Invert Out / Negedge
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

def freeze():
    s.write(bytes([0x06]))
    time.sleep(0.05)

def thaw():
    s.write(bytes([0x07]))
    time.sleep(0.05)

def configure(cell_id, topo, in_addr, out_addr, auth=AUTH, one_shot=0, latch_in=0, invert_out=0, edge_mode=0):
    cfg = mk_cfg(topo, auth_mask=auth, one_shot=one_shot, latch_in=latch_in, invert_out=invert_out, edge_mode=edge_mode)
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

def collect(timeout=1.2):
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

# ── 8-CELL STATEFUL SEQUENCE LOCK RUNNER ──────────────────────────────────────
print("\n=== 8-Cell Stateful Sequence Lock ===")
reset()

# --- FREEZE → configure → preload → THAW ---
# Freeze prevents any cell firing during setup.
# All configuration and preloading happens safely inside the freeze window.
# Thaw releases the array — wave propagates cleanly from a known state.

freeze()

# Cells 0-2: comparers — PASS two-arrival, secret preloaded as a_data
configure(0, TOPO_PASS, in_addr=0x30, out_addr=0x0E)
configure(1, TOPO_PASS, in_addr=0x31, out_addr=0x0F)
configure(2, TOPO_PASS, in_addr=0x32, out_addr=0x10)

# Cells 3-6: chain — PASS two-arrival, preloaded with 1 (will fire on upstream arrival)
configure(3, TOPO_PASS, in_addr=0x0E, out_addr=0x11)
configure(4, TOPO_PASS, in_addr=0x11, out_addr=0x12)
configure(5, TOPO_PASS, in_addr=0x12, out_addr=0x13)
configure(6, TOPO_PASS, in_addr=0x13, out_addr=0x28)

# Cell 7: secure output — one_shot so addr99 fires exactly once
configure(7, TOPO_PASS, in_addr=0x28, out_addr=99, one_shot=1)

# Preload secret key into comparers (safe — array frozen, no firing)
print("[Setup] Preloading secret key and arming chain (frozen)...")
tx(CMD_DATA, 0x30, 1)   # comparer 0 a_data = 1
tx(CMD_DATA, 0x31, 0)   # comparer 1 a_data = 0
tx(CMD_DATA, 0x32, 1)   # comparer 2 a_data = 1

# Preload chain cells — each gets one write (first arrival stored as a_data)
# Comparer output will be the second arrival that fires each chain cell
tx(CMD_DATA, 0x0E, 1)   # cell 3 a_data = 1
tx(CMD_DATA, 0x11, 1)   # cell 4 a_data = 1
tx(CMD_DATA, 0x12, 1)   # cell 5 a_data = 1
tx(CMD_DATA, 0x13, 1)   # cell 6 a_data = 1
tx(CMD_DATA, 0x28, 1)   # cell 7 a_data = 1

thaw()  # array live — all cells armed and waiting
flush(0.3)

# --- TEST 1: WRONG CODE ---
print("[Test 1] Injecting incorrect streaming code [0, 0, 0]...")
# Wrong: comparer 0 fires PASS(1, 0)=0 to 0x0E
# Cell 3 sees 0 as second arrival: PASS(1, 0)=0 — chain carries 0 forward
# addr99 would receive 0 — but one_shot cell 7 fires with value 0
# Check: addr99 should NOT fire (or fire with 0 which we reject)
tx(CMD_DATA, 0x30, 0)
tx(CMD_DATA, 0x31, 0)
tx(CMD_DATA, 0x32, 0)
evts = collect(1.0)
unlocked = [d for a,d in evts if a == 99 and d != 0]
chk("Lock blocked unauthorized stream", len(unlocked) == 0, True)

# Re-arm everything under freeze for test 2
freeze()
configure(0, TOPO_PASS, in_addr=0x30, out_addr=0x0E)
configure(1, TOPO_PASS, in_addr=0x31, out_addr=0x0F)
configure(2, TOPO_PASS, in_addr=0x32, out_addr=0x10)
configure(3, TOPO_PASS, in_addr=0x0E, out_addr=0x11)
configure(4, TOPO_PASS, in_addr=0x11, out_addr=0x12)
configure(5, TOPO_PASS, in_addr=0x12, out_addr=0x13)
configure(6, TOPO_PASS, in_addr=0x13, out_addr=0x28)
configure(7, TOPO_PASS, in_addr=0x28, out_addr=99, one_shot=1)
tx(CMD_DATA, 0x30, 1)
tx(CMD_DATA, 0x31, 0)
tx(CMD_DATA, 0x32, 1)
tx(CMD_DATA, 0x0E, 1)
tx(CMD_DATA, 0x11, 1)
tx(CMD_DATA, 0x12, 1)
tx(CMD_DATA, 0x13, 1)
tx(CMD_DATA, 0x28, 1)
thaw()
flush(0.3)

# --- TEST 2: CORRECT CODE ---
print("[Test 2] Injecting correct streaming wavefront [1, 0, 1]...")
tx(CMD_DATA, 0x30, 1)
time.sleep(0.05)
tx(CMD_DATA, 0x31, 0)
time.sleep(0.05)
tx(CMD_DATA, 0x32, 1)
time.sleep(0.05)

evts = collect(1.5)
unlocked = [d for a,d in evts if a == 99 and d != 0]
print(f"\n--- Lock Telemetry ---")
print(f"Secure Output (addr99) pulses: {[hex(d) for d in unlocked]}")

chk("Lock successfully verified formula chain and UNLOCKED", len(unlocked) >= 1, True)

running = False
s.close()
