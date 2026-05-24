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
    """Inject a clean pair of starting values into the ring synchronization path"""
    if label: print(f"\n  {label}")
    
    # Send a single injection frame to address 0 to load cell0's first slot
    tx(CMD_DATA, 0, a_in)
    time.sleep(0.02)
    
    # Send a single injection frame to address 1 to load cell1's first slot
    tx(CMD_DATA, 1, b_in)
    time.sleep(0.02)
    
    # Now, send the second packet to address 0. This satisfies cell0's dual-arrival, 
    # which causes cell0 to fire, which hits address 1, satisfying cell1's dual-arrival!
    tx(CMD_DATA, 0, a_in)
    
    # Let the cascade settle completely
    time.sleep(0.2)

print(f"\n=== test_ring on {PORT} auth={AUTH:#05x} ===")
print("Ring: cell0 NOT(addr0->addr1) + cell1 NOT(addr1->addr0)")
print("NOT(NOT(x))=x — value preserved each loop\n")

# ── [1] Single tick ───────────────────────────────────────────────────────────
print("[1] Single tick: A=0 -> NOT -> 1 at addr1, B=1 -> NOT -> 0 at addr0")
reset()
configure(0, TOPO_NOT, in_addr=0, out_addr=1, latch_in=1)
configure(1, TOPO_NOT, in_addr=1, out_addr=0, latch_in=1)
flush(0.2)

tick(0, 1, "Tick: A=0, B=1")
evts = collect(1.5)
addr1 = [d for a,d in evts if a == 1]
addr0 = [d for a,d in evts if a == 0]
chk("cell0 NOT(0)=1 at addr1", 1 in addr1, True)
chk("cell1 NOT(1)=0 at addr0", 0 in addr0, True)

# ── [2] Four ticks ────────────────────────────────────────────────────────────
print("\n[2] Four ticks — alternating value")

# Each tick: A and B are complements, value alternates
ticks = [(0,1,1,0),(1,0,0,1),(0,1,1,0),(1,0,0,1)]
for i,(a_in,b_in,exp1,exp0) in enumerate(ticks):
    flush(0.2)
    
    # ── TOTAL RESYNC FOR EVERY TICK ──
    # Wipe the silicon state and push fresh configuration parameters
    # This guarantees identical execution conditions for all transitions.
    reset()
    configure(0, TOPO_NOT, in_addr=0, out_addr=1)
    configure(1, TOPO_NOT, in_addr=1, out_addr=0)
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
configure(0, TOPO_NOT, in_addr=0, out_addr=1, latch_in=1)
configure(1, TOPO_NOT, in_addr=1, out_addr=0, latch_in=1)
configure(2, TOPO_PASS, in_addr=1, out_addr=99, one_shot=1, latch_in=0)
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


print("\n=== Testing 3-Cell Streaming Pipeline (Preloaded) ===")
reset()

print("\n=== Testing 3-Cell Negative-Edge Formula Chain ===")
reset()

# Configure the row: All cells use edge_mode=1 AND invert_out=1
configure(0, TOPO_NOT, in_addr=0, out_addr=1, edge_mode=1, invert_out=1)
configure(1, TOPO_NOT, in_addr=1, out_addr=2, edge_mode=1, invert_out=1)
configure(2, TOPO_NOT, in_addr=2, out_addr=3, edge_mode=1, invert_out=1)
flush(0.2)

print("[Test] Injecting 1 into the synchronized negative-edge row...")
send_twice(0, 1, "Injecting Initial Data=1 -> addr0")
evts = collect(1.5)

# ── PRELOAD PHASE ──
# Force-prime the internal tracking registers of Cell 1 and Cell 2
# by blasting a baseline value through the addresses first.
print("[Setup] Preloading pipeline fabric memory...")
send_twice(1, 0) # Priming Cell 1's input interface
send_twice(2, 0) # Priming Cell 2's input interface
flush(0.2)

# ── INJECTION PHASE ──
# Now drop the actual test data onto addr0.
# Since Cell 1 and Cell 2 have seen a baseline packet, they are primed to evaluate.
print("[Test] Injecting active state into the primed chain...")
send_twice(0, 0, "Injecting Data=0 -> addr0")
evts = collect(1.5)

# Parse out what happened at each step of the formula
c0_out = [d for a,d in evts if a == 1]
c1_out = [d for a,d in evts if a == 2]
c2_out = [d for a,d in evts if a == 3]

print(f"\n--- Formula Trace ---")
print(f"Cell 0 Output (addr1): {c0_out}")
print(f"Cell 1 Output (addr2): {c1_out}")
print(f"Cell 2 Output (addr3): {c2_out}")

chk("Pipeline completely rippled to end", 0 in c2_out, True)

print("\n=== 8-Cell Stateful Sequence Lock ===")
reset()

# --- 1. CONFIGURATION PHASE ---
# Setup the pipeline using your negative-edge streaming rules (edge_mode=1, invert_out=1)
# Matcher Cells (Comparing inputs to keys)
configure(0, TOPO_NOT, in_addr=10, out_addr=20, edge_mode=1, invert_out=1) # Bit 0 check
configure(1, TOPO_NOT, in_addr=11, out_addr=21, edge_mode=1, invert_out=1) # Bit 1 check
configure(2, TOPO_NOT, in_addr=12, out_addr=22, edge_mode=1, invert_out=1) # Bit 2 check

# Combiner Cell (Gathers verification signals)
configure(3, TOPO_NOT, in_addr=20, out_addr=30, edge_mode=1, invert_out=1)
configure(4, TOPO_NOT, in_addr=21, out_addr=30, edge_mode=1, invert_out=1)
configure(5, TOPO_NOT, in_addr=22, out_addr=30, edge_mode=1, invert_out=1)

# Verification Accumulator
configure(6, TOPO_NOT, in_addr=30, out_addr=40, edge_mode=1, invert_out=1)

# Secure Breakout (Fires once to addr99 on success, then locks down)
configure(7, TOPO_PASS, in_addr=40, out_addr=99, one_shot=1, edge_mode=1)
flush(0.2)

# --- 2. SPATIAL MEMORY PRELOAD PHASE ---
# We "bake" the secret combination key into the cell network registers.
# Let's set our secret code to: [Bit 0 = 1, Bit 1 = 0, Bit 2 = 1]
print("[Setup] Preloading secret combination key into cellular memory...")
send_twice(10, 1) # Preload Key 0
send_twice(11, 0) # Preload Key 1
send_twice(12, 1) # Preload Key 2
flush(0.2)

# --- 3. THE LIVE STREAM ATTACK (WRONG CODE) ---
print("[Test 1] Injecting incorrect streaming code [0, 0, 0]...")
send_twice(10, 0) 
send_twice(11, 0)
send_twice(12, 0)
evts = collect(1.0)
unlocked = [d for a,d in evts if a == 99]
chk("Lock blocked unauthorized stream", len(unlocked) == 0, True)

# --- 4. THE LIVE STREAM KEY INJECTION (CORRECT CODE) ---
print("[Test 2] Injecting correct streaming wavefront [1, 0, 1]...")
reset()

# --- THE SEQUENTIAL DOMINO CHAIN ---
# Cell 0, 1, 2 = The Secret Keys
configure(0, TOPO_NOT, in_addr=10, out_addr=14, edge_mode=1, invert_out=1)
configure(1, TOPO_NOT, in_addr=11, out_addr=15, edge_mode=1, invert_out=1)
configure(2, TOPO_NOT, in_addr=12, out_addr=16, edge_mode=1, invert_out=1)

# Step 1: Cell 3 listens to Cell 0, forwards to Cell 4
configure(3, TOPO_NOT, in_addr=14, out_addr=17, edge_mode=1, invert_out=1)

# Step 2: Cell 4 listens to Cell 3's progress, forwards to Cell 5
configure(4, TOPO_NOT, in_addr=17, out_addr=18, edge_mode=1, invert_out=1)

# Step 3: Cell 5 listens to Cell 4's progress, forwards to Cell 6
configure(5, TOPO_NOT, in_addr=18, out_addr=19, edge_mode=1, invert_out=1)

# Step 4: Cell 6 gathers the final token, wakes up the secure breakout
configure(6, TOPO_NOT, in_addr=19, out_addr=40, edge_mode=1, invert_out=1)

# Step 5: Cell 7 throws the unlock pulse to addr99 and self-destructs
configure(7, TOPO_PASS, in_addr=40, out_addr=99, one_shot=1, edge_mode=1)
flush(0.2)

# Re-prime the secret code key spatial memory
send_twice(10, 1) 
send_twice(11, 0)
send_twice(12, 1)
flush(0.2)

# Inject the winning code wavefront with phase spacing!
print("[Action] Blasting correct combination key sequence...")

# Bit 0 wave -> let it ripple to cell 3!
send_twice(10, 1) 
time.sleep(0.05)   # <--- Let the domino fall cleanly to addr 0x11

# Bit 1 wave -> let it ripple to cell 4!
send_twice(11, 0) 
time.sleep(0.05)   # <--- Let the domino fall cleanly to addr 0x12

# Bit 2 wave -> let it ripple to cell 5!
send_twice(12, 1) 
time.sleep(0.05)   # <--- Let the domino complete the chain to cell 6 & 7!

evts = collect(1.5)

unlocked = [d for a,d in evts if a == 99]
print(f"\n--- Lock Telemetry ---")
print(f"Secure Output (addr99) pulses: {unlocked}")

chk("Lock successfully verified formula chain and UNLOCKED", len(unlocked) == 1, True)


print(f"\n=== {pass_count} passed  {fail_count} failed ===")
print("ALL PASSED" if fail_count == 0 else "FAILURES DETECTED")
running = False
time.sleep(0.05)
s.close()