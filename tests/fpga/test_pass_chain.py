"""
test_pass_chain.py — Minimal PASS chain test
Confirms preloaded PASS cells propagate correctly on silicon.

Cell 0: PASS  in=0x100  out=0x200  (preloaded a_data=1)
Cell 1: PASS  in=0x200  out=0x300  (preloaded a_data=1)

Inject 1 at 0x100 → cell 0 fires PASS(1,1)=1 → 0x200
                  → cell 1 fires PASS(1,1)=1 → 0x300
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
    return (code&0xF) | ((auth&0x7FF)<<4) | (1<<15) | ((cell_id&0x7FF)<<16)

CMD_DATA = mk_cmd(1)

def mk_cfg(topo, auth_mask=0, one_shot=0):
    w  = (topo & 0x3FF)
    w |= (auth_mask & 0x7FF) << 11
    w |= 1 << 22
    w |= (1 if one_shot else 0) << 30
    return w

def tx(cmd, addr, data):
    s.write(struct.pack('>BIII', 0x01, cmd, addr, data))
    time.sleep(0.025)

def freeze():
    s.write(bytes([0x06]))
    time.sleep(0.05)

def thaw():
    s.write(bytes([0x07]))
    time.sleep(0.05)

def reset():
    s.write(bytes([0x03]))
    time.sleep(0.5)
    while not pkt_q.empty():
        try: pkt_q.get_nowait()
        except: break

def collect(timeout=1.0):
    evts = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired':
                print(f"  [rx] addr={e[1]:#x} data={e[2]:#x}")
                evts.append((e[1], e[2]))
        except queue.Empty:
            pass
    return evts

def configure(cell_id, topo, in_addr, out_addr, one_shot=0):
    cfg = mk_cfg(topo, auth_mask=AUTH, one_shot=one_shot)
    tx(mk_cmd(2, AUTH, cell_id), 0, in_addr)
    tx(mk_cmd(3, AUTH, cell_id), 0, out_addr)
    tx(mk_cmd(4, AUTH, cell_id), 0, cfg)
    print(f"  cell{cell_id}: topo={topo:#05x} in={in_addr:#x} out={out_addr:#x}")

TOPO_PASS = 0x000

print(f"\n=== PASS Chain Test ({PORT}) ===\n")
reset()

# --- Test 1: single PASS cell with preload ---
print("Test 1: single PASS cell, preload a_data=1, inject 1")
freeze()
configure(0, TOPO_PASS, in_addr=0x100, out_addr=0x200)
thaw()
tx(CMD_DATA, 0x100, 1)   # first arrival → a_data=1
time.sleep(0.05)
tx(CMD_DATA, 0x100, 1)   # second arrival → fires PASS(1,1)=1
evts = collect(0.5)
hit = any(a==0x200 for a,d in evts)
print(f"  {'PASS' if hit else 'FAIL'} cell fired to 0x200: {hit}")

# --- Test 2: two PASS cells chained ---
print("\nTest 2: two PASS cells, both preloaded, chain")
reset()
freeze()
configure(0, TOPO_PASS, in_addr=0x100, out_addr=0x200)
configure(1, TOPO_PASS, in_addr=0x200, out_addr=0x300)
thaw()
# Preload cell 1 first (single write = first arrival)
tx(CMD_DATA, 0x200, 1)   # cell 1 a_data=1, waiting
time.sleep(0.05)
# Preload cell 0 and fire it twice
tx(CMD_DATA, 0x100, 1)   # cell 0 first arrival
time.sleep(0.05)
tx(CMD_DATA, 0x100, 1)   # cell 0 fires → 0x200=1 → cell 1 second arrival → fires
evts = collect(0.8)
hit0 = any(a==0x200 for a,d in evts)
hit1 = any(a==0x300 for a,d in evts)
print(f"  {'PASS' if hit0 else 'FAIL'} cell 0 fired to 0x200: {hit0}")
print(f"  {'PASS' if hit1 else 'FAIL'} cell 1 fired to 0x300: {hit1}")

# --- Test 3: what does PASS(a,b) actually output? ---
print("\nTest 3: PASS output value — a_data=0xDEAD, inject 0xBEEF")
reset()
freeze()
configure(0, TOPO_PASS, in_addr=0x100, out_addr=0x200)
thaw()
tx(CMD_DATA, 0x100, 0xDEAD)  # first arrival → a_data=0xDEAD
time.sleep(0.05)
tx(CMD_DATA, 0x100, 0xBEEF)  # second arrival → fires
evts = collect(0.5)
for a,d in evts:
    if a == 0x200:
        print(f"  PASS(a_data=0xDEAD, B=0xBEEF) = {d:#010x}")
        print(f"  {'PASS(A)=0xDEAD' if d==0xDEAD else 'PASS(B)=0xBEEF' if d==0xBEEF else 'unexpected'}")

running = False
s.close()
