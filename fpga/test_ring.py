"""
test_ring.py — Host-clocked ring with one_shot breakout

Architecture:
  cell0: addr 0 -> addr 1  (NOT gate, arms on reset)
  cell1: addr 1 -> addr 0  (NOT gate, feeds back to cell0)

  Host kicks the ring by sending two arrivals to addr=0.
  cell0 fires NOT(A) to addr=1.
  Host sends one more arrival to addr=1 (gives cell1 its B input).
  cell1 fires NOT(B) back to addr=0.
  Each full loop: NOT(NOT(x)) = x (double NOT = identity).

  Ring runs for N host-clocked ticks then stops.
  A one_shot cell at addr=1 -> addr=99 counts one ring completion.

  This is a host-assisted ring — not autonomous (requires host trigger each tick).
  True autonomous ring needs a broadcast/splitter cell (future work).

Tests:
  [1] Single ring tick — cell0 fires, cell1 fires
  [2] N=4 ticks — value alternates correctly each tick
  [3] one_shot observer — counts ring completions
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
    w |= 1                   << 22
    w |= (1 if one_shot else 0) << 30
    return w

TOPO_PASS = 0b0000000000
TOPO_NOT  = 0b0000000001

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
    tx(mk_cmd(2, auth, cell_id), 0, in_addr)
    tx(mk_cmd(3, auth, cell_id), 0, out_addr)
    tx(mk_cmd(4, auth, cell_id), 0, cfg,
       f"RECONF cell{cell_id} topo={topo:#05x} in={in_addr:#x} out={out_addr:#x}")
    drain(0.1)

def send(addr, data, label=""):
    drain(0.05)
    tx(CMD_DATA, addr, data, label or f"DATA {data} -> addr {addr:#x}")
    time.sleep(0.05)

def collect(timeout=0.5):
    """Collect all fire events within timeout."""
    evts = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired':
                evts.append((e[1], e[2]))
                print(f"        [rx] fired addr={e[1]:#x} data={e[2]}")
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

def tick(a_input, b_input, label=""):
    """One ring tick — send A to addr=0 twice, B to addr=1 twice."""
    if label: print(f"\n  {label}")
    send(0, a_input, f"A={a_input} -> addr0 (1st)")
    send(0, a_input, f"A={a_input} -> addr0 (2nd, fires cell0)")
    time.sleep(0.1)
    send(1, b_input, f"B={b_input} -> addr1 (1st)")
    send(1, b_input, f"B={b_input} -> addr1 (2nd, fires cell1)")

# ── MAIN ──────────────────────────────────────────────────────────────────────
print(f"\n=== test_ring on {PORT} auth={AUTH:#05x} ===\n")
print("Host-clocked ring: cell0 (NOT, addr0->addr1) <-> cell1 (NOT, addr1->addr0)")
print("Each tick: host sends A to addr0 twice, then B to addr1 twice")
print("NOT(NOT(x)) = x — value preserved each full loop\n")

reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1)
configure(1, TOPO_NOT, in_addr=1, out_addr=0)
drain(0.2)

# ── [1] Single tick ───────────────────────────────────────────────────────────
print("[1] Single tick — A=0 in, expect NOT(0)=1 at addr1, NOT(1)=0 at addr0")
tick(0, 1, "Tick 1: A=0 -> NOT -> 1 -> NOT -> 0")
evts = collect(1.0)
addr1_data = [d for a,d in evts if a == 1]
addr0_data = [d for a,d in evts if a == 0]
chk("cell0 NOT(0)=1 at addr1", 1 in addr1_data, True)
chk("cell1 NOT(1)=0 at addr0", 0 in addr0_data, True)

# ── [2] Four ticks — value alternates ────────────────────────────────────────
print("\n[2] Four ticks — value alternates: 0->1->0->1")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1)
configure(1, TOPO_NOT, in_addr=1, out_addr=0)
drain(0.2)

# Sequence: inject 0, expect alternating output
# Tick N: A=prev_cell1_output (or 0 for first)
# We track the expected values manually
expected_seq = [(0, 1, 0), (1, 0, 1), (0, 1, 0), (1, 0, 1)]
# (a_in, expected_at_addr1, expected_at_addr0)

for i, (a_in, exp1, exp0) in enumerate(expected_seq):
    b_in = 1 - a_in  # B is complement of A (previous cell1 output)
    print(f"\n  Tick {i+1}: A={a_in} B={b_in}")
    tick(a_in, b_in)
    evts = collect(1.0)
    addr1_data = [d for a,d in evts if a == 1]
    addr0_data = [d for a,d in evts if a == 0]
    chk(f"tick{i+1} addr1={exp1}", exp1 in addr1_data if addr1_data else False, True)
    chk(f"tick{i+1} addr0={exp0}", exp0 in addr0_data if addr0_data else False, True)

# ── [3] one_shot observer ─────────────────────────────────────────────────────
print("\n[3] one_shot observer at addr1 -> addr99")
print("    Fires exactly once when ring completes first loop, then disarms")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1)
configure(1, TOPO_NOT, in_addr=1, out_addr=0)
# cell2: one_shot observer — listens on addr1, fires once to addr99
configure(2, TOPO_PASS, in_addr=1, out_addr=99, one_shot=1)
drain(0.2)

# First tick — observer should fire once
tick(0, 1, "Tick 1 — observer armed")
evts = collect(1.0)
obs_fires = [(a,d) for a,d in evts if a == 99]
chk("observer fires once", len(obs_fires) == 1, True)

# Second tick — observer should be silent (one_shot disarmed)
drain(0.2)
tick(0, 1, "Tick 2 — observer should be silent")
evts = collect(1.0)
obs_fires2 = [(a,d) for a,d in evts if a == 99]
chk("observer silent after one_shot", len(obs_fires2) == 0, True)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n=== {pass_count} passed  {fail_count} failed ===")
if fail_count == 0:
    print("ALL PASSED")
else:
    print("FAILURES DETECTED")

running = False
time.sleep(0.05)
s.close()
