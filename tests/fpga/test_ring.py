"""
test_ring.py — Host-clocked ring with one_shot breakout

Ring: cell0 (NOT, addr0->addr1) + cell1 (NOT, addr1->addr0)
Host kicks each tick — sends A twice to addr0, B twice to addr1.
NOT(NOT(x)) = x — value preserved each full loop.

One_shot observer at addr1 -> addr99: fires once, proves ring completion.
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

def collect(timeout=1.2):
    """Collect all fire events — never clears queue before starting."""
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

def tick(a_in, b_in, label=""):
    """One ring tick — two arrivals to addr0, two arrivals to addr1."""
    if label: print(f"\n  {label}")
    send_twice(0, a_in, f"A={a_in} -> addr0")
    time.sleep(0.1)
    send_twice(1, b_in, f"B={b_in} -> addr1")

print(f"\n=== test_ring on {PORT} auth={AUTH:#05x} ===")
print("Ring: cell0 NOT(addr0->addr1) + cell1 NOT(addr1->addr0)")
print("NOT(NOT(x))=x — value preserved each loop\n")

# ── [1] Single tick ───────────────────────────────────────────────────────────
print("[1] Single tick: A=0 -> NOT -> 1 at addr1, B=1 -> NOT -> 0 at addr0")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1)
configure(1, TOPO_NOT, in_addr=1, out_addr=0)
flush(0.2)

tick(0, 1, "Tick: A=0, B=1")
evts = collect(1.5)
addr1 = [d for a,d in evts if a == 1]
addr0 = [d for a,d in evts if a == 0]
chk("cell0 NOT(0)=1 at addr1", 1 in addr1, True)
chk("cell1 NOT(1)=0 at addr0", 0 in addr0, True)

# ── [2] Four ticks ────────────────────────────────────────────────────────────
print("\n[2] Four ticks — alternating value")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1)
configure(1, TOPO_NOT, in_addr=1, out_addr=0)
flush(0.2)

# Each tick: A and B are complements, value alternates
ticks = [(0,1,1,0),(1,0,0,1),(0,1,1,0),(1,0,0,1)]
for i,(a_in,b_in,exp1,exp0) in enumerate(ticks):
    flush(0.2)
    tick(a_in, b_in, f"Tick {i+1}: A={a_in} B={b_in}")
    evts = collect(1.5)
    addr1 = [d for a,d in evts if a == 1]
    addr0 = [d for a,d in evts if a == 0]
    chk(f"tick{i+1} NOT({a_in})={exp1} at addr1", exp1 in addr1 if addr1 else False, True)
    chk(f"tick{i+1} NOT({b_in})={exp0} at addr0", exp0 in addr0 if addr0 else False, True)

# ── [3] one_shot observer ─────────────────────────────────────────────────────
print("\n[3] one_shot observer at addr1 -> addr99")
print("    Fires exactly once on first ring completion, then disarms")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1)
configure(1, TOPO_NOT, in_addr=1, out_addr=0)
configure(2, TOPO_PASS, in_addr=1, out_addr=99, one_shot=1)
flush(0.2)

# Observer listens on addr1 — fires when cell0 output arrives there
# cell0 output arrives as first arrival to observer, 
# second arrival (B tick) triggers observer
tick(0, 1, "Tick 1 — observer should fire")
evts = collect(1.5)
obs = [(a,d) for a,d in evts if a == 99]
ring1 = [d for a,d in evts if a == 1]
print(f"  ring addr1 events: {ring1}")
print(f"  observer (addr99) events: {obs}")
chk("cell0 fired to addr1", len(ring1) > 0, True)
chk("observer fired once",  len(obs) == 1,  True)

flush(0.3)
tick(0, 1, "Tick 2 — observer should be silent")
evts = collect(1.5)
obs2 = [(a,d) for a,d in evts if a == 99]
print(f"  observer (addr99) events: {obs2}")
chk("observer silent tick2", len(obs2) == 0, True)

print(f"\n=== {pass_count} passed  {fail_count} failed ===")
print("ALL PASSED" if fail_count == 0 else "FAILURES DETECTED")
running = False
time.sleep(0.05)
s.close()
