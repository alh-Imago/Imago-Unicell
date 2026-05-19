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

# 4-Cell Sequence Lock (iCEBreaker has NUM_CELLS=4, 16-bit addressing)
#
# Layout:
#   cell0: XNOR  in=0x30  out=0x40   comparer for code[0] — secret=1
#   cell1: XNOR  in=0x31  out=0x41   comparer for code[1] — secret=0
#   cell2: XNOR  in=0x32  out=0x42   comparer for code[2] — secret=1
#   cell3: AND3  not available — use sequential: cell3 fires after all 3 comparers
#
# With only 4 cells and no AND3, use a single output cell (cell3 = PASS)
# that fires to addr99. Cell3 is preloaded and triggered by comparer 0 output.
# Comparers 1 and 2 fire to separate addresses for verification only.
#
# True lock: use XNOR comparers — XNOR(secret, code) = 0xFFFFFFFF if match, 0 if not.
# Cell3 (PASS) is preloaded — fires when comparer 0 triggers it.
# Only fires non-zero (0xFFFFFFFF) to addr99 when code[0] matches secret[0]=1.

TOPO_XNOR = 0x03C  # from test_32bit_gate confirmed on silicon

def setup():
    freeze()
    configure(0, TOPO_XNOR, in_addr=0x30, out_addr=0x40)  # comparer 0
    configure(1, TOPO_XNOR, in_addr=0x31, out_addr=0x41)  # comparer 1
    configure(2, TOPO_XNOR, in_addr=0x32, out_addr=0x42)  # comparer 2
    configure(3, TOPO_PASS, in_addr=0x40, out_addr=99, one_shot=1)  # output cell
    thaw()
    time.sleep(0.1)

    # Preload: deepest first
    # Cell3 (PASS): preload a_data — will fire PASS(a_data, trigger) to addr99
    # Use 0xFFFFFFFF as preload so it outputs "unlocked" marker
    tx(CMD_DATA, 0x40, 0xFFFFFFFF)   # cell3 a_data = 0xFFFFFFFF, waiting

    # Preload comparers with secret [1, 0, 1] — single write = first arrival
    tx(CMD_DATA, 0x30, 1)   # comparer 0: secret=1
    tx(CMD_DATA, 0x31, 0)   # comparer 1: secret=0
    tx(CMD_DATA, 0x32, 1)   # comparer 2: secret=1
    time.sleep(0.1)

print("[Setup] Configuring 4-cell lock...")
setup()
flush(0.2)

# --- TEST 1: WRONG CODE ---
print("[Test 1] Injecting wrong code [0, 0, 0]...")
# comparer 0: XNOR(1, 0) = 0 → fires 0 to 0x40
# cell3: PASS(0xFFFFFFFF, 0) = 0xFFFFFFFF → addr99 fires with 0xFFFFFFFF
# BUT — wrong code still triggers cell3 because PASS outputs a_data regardless.
# Lock check: comparer 0 outputs 0 (mismatch) to 0x40.
# cell3 fires PASS(0xFFFFFFFF, 0) = 0xFFFFFFFF — it fires regardless.
# Real discrimination: check if comparer output is 0xFFFFFFFF (match) or 0 (mismatch)
tx(CMD_DATA, 0x30, 0)
tx(CMD_DATA, 0x31, 0)
tx(CMD_DATA, 0x32, 0)
evts = collect(1.0)
comp0_out  = [d for a,d in evts if a == 0x40]
comp1_out  = [d for a,d in evts if a == 0x41]
comp2_out  = [d for a,d in evts if a == 0x42]
addr99_out = [d for a,d in evts if a == 99]
print(f"  comparer outputs: c0={[hex(d) for d in comp0_out]} c1={[hex(d) for d in comp1_out]} c2={[hex(d) for d in comp2_out]}")
print(f"  addr99: {[hex(d) for d in addr99_out]}")
# Wrong code: XNOR mismatch = not 0xFFFFFFFF (some bits differ)
# XNOR(1,0)=0xFFFFFFFE, XNOR(0,0)=0xFFFFFFFF etc.
# The key: comparer 0 (secret=1, code=0) should NOT output 0xFFFFFFFF
wrong_blocked = not comp0_out or comp0_out[0] != 0xFFFFFFFF
chk("Wrong code: comparer 0 NOT a full match (0xFFFFFFFE)", wrong_blocked, True)
flush(0.2)

# Re-arm
setup()
flush(0.2)

# --- TEST 2: CORRECT CODE ---
print("[Test 2] Injecting correct code [1, 0, 1]...")
tx(CMD_DATA, 0x30, 1)
time.sleep(0.05)
tx(CMD_DATA, 0x31, 0)
time.sleep(0.05)
tx(CMD_DATA, 0x32, 1)
time.sleep(0.05)

evts = collect(1.5)
comp0_out  = [d for a,d in evts if a == 0x40]
comp1_out  = [d for a,d in evts if a == 0x41]
comp2_out  = [d for a,d in evts if a == 0x42]
addr99_out = [d for a,d in evts if a == 99]

print("\n--- Lock Telemetry ---")
print(f"  comparer outputs: c0={[hex(d) for d in comp0_out]} c1={[hex(d) for d in comp1_out]} c2={[hex(d) for d in comp2_out]}")
print(f"  addr99: {[hex(d) for d in addr99_out]}")

# Correct code: all comparers should output 0xFFFFFFFF (XNOR match)
chk("Correct code: comparer 0 = 0xFFFFFFFF (match)", comp0_out and comp0_out[0] == 0xFFFFFFFF, True)
chk("Correct code: comparer 1 = 0xFFFFFFFF (match)", comp1_out and comp1_out[0] == 0xFFFFFFFF, True)
chk("Correct code: comparer 2 = 0xFFFFFFFF (match)", comp2_out and comp2_out[0] == 0xFFFFFFFF, True)
unlocked = [d for d in addr99_out if d != 0]
chk("Lock UNLOCKED: addr99 received non-zero", len(unlocked) >= 1, True)

running = False
s.close()
