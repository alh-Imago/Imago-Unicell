"""
test_state_inspect.py v4 — preset address boot protocol

Cells boot with:
  input_address  = CELL_ID      (e.g. cell 0 listens on address 0)
  output_address = CELL_ID + 1  (e.g. cell 0 writes to address 1)

Configure sequence:
  1. RECONFIGURE only — boot bypass (auth_mask=0 accepted unconditionally)
     Embeds auth_mask for subsequent commands.
  2. SET_IN/SET_OUT only needed when overriding defaults.

Chain: write to address 0 -> cell0 fires to address 1 -> cell1 fires to address 2.
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

def get_status():
    s.write(bytes([0x04])); time.sleep(0.3)
    for e in drain(0.2):
        if e[0] == 'status': return e[1], e[2]
    return None, None

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

# ── Command bus word builders ──────────────────────────────────────────────────
def mk_cmd(code, auth=0):
    return (code & 0xF) | ((auth & 0x7FF) << 4) | (1 << 15)

CMD_DATA  = mk_cmd(1)
CMD_PING  = mk_cmd(9)

def cmd_reconf(auth=0): return mk_cmd(4, auth)
def cmd_set_in(auth=0): return mk_cmd(2, auth)
def cmd_set_out(auth=0): return mk_cmd(3, auth)

# ── Command latch word builder ─────────────────────────────────────────────────
def mk_cfg(topo, auth_mask=0, sync_wait=0, dtype=0,
           invert_out=0, latch_in=0, priority=0,
           trace=0, breakpoint=0, one_shot=0, loop_back=0):
    w  = (topo & 0x3FF)
    w |= (1 if sync_wait  else 0) << 10
    w |= (auth_mask & 0x7FF)      << 11
    w |= 1                        << 22   # start_flag
    w |= (dtype & 0x3)            << 23
    w |= (1 if invert_out else 0) << 25
    w |= (1 if latch_in   else 0) << 26
    w |= (1 if priority   else 0) << 27
    w |= (1 if trace      else 0) << 28
    w |= (1 if breakpoint else 0) << 29
    w |= (1 if one_shot   else 0) << 30
    w |= (1 if loop_back  else 0) << 31
    return w

TOPO_PASS = 0b0000000000
TOPO_NOT  = 0b0000000001

# ── Configure cell — preset address boot ──────────────────────────────────────
def configure_cell(cell_id, topo, in_addr=None, out_addr=None, auth=AUTH):
    """
    Boot sequence — cells preset to input=CELL_ID, output=CELL_ID+1.
    Only send SET_IN/SET_OUT if overriding defaults.
    RECONFIGURE accepted unconditionally (auth_mask=0 on fresh cell).
    """
    default_in  = cell_id
    default_out = cell_id + 1
    if in_addr  is None: in_addr  = default_in
    if out_addr is None: out_addr = default_out

    print(f"    Cell {cell_id}: topo={topo:#05x}  "
          f"in={in_addr:#010x}  out={out_addr:#010x}")

    if in_addr != default_in:
        tx(cmd_set_in(auth), 0, in_addr, f"SET_INPUT_ADDR  {in_addr:#010x}")
    if out_addr != default_out:
        tx(cmd_set_out(auth), 0, out_addr, f"SET_OUTPUT_ADDR {out_addr:#010x}")

    cfg = mk_cfg(topo, auth_mask=auth)
    tx(cmd_reconf(), 0, cfg, f"RECONFIGURE cfg={cfg:#010x}")

def verify_cell(cell_id, in_addr, out_addr, in_data, expected):
    drain(0.1)
    tx(CMD_DATA, in_addr, in_data,
       f"DATA {in_data} -> cell{cell_id}  expect {expected} at {out_addr:#x}")
    evts = drain(0.4)
    fired = [(e[1], e[2]) for e in evts if e[0] == 'fired']
    ok = any(a == out_addr and d == expected for a, d in fired)
    tag = 'PASS ✓' if ok else 'FAIL ✗'
    print(f"      Verify: {tag}  fired={[(hex(a), d) for a, d in fired]}")
    return ok

# ── MAIN ──────────────────────────────────────────────────────────────────────
print(f"\n=== State inspection v4 on {PORT} auth={AUTH:#05x} ===")
print("  Preset addresses: cell N listens on addr N, writes to addr N+1\n")

print("Step 1: Reset")
reset()
armed, cycles = get_status()
print(f"  armed_count={armed}  cycles={cycles}\n")

# Cell 0: listens on 0, writes to 1
print("Step 2: Configure cell 0 (NOT gate, addr 0 -> addr 1)")
configure_cell(0, TOPO_NOT)
time.sleep(0.1)
armed, _ = get_status()
print(f"  armed_count={armed}")
verify_cell(0, 0, 1, 0, 1)   # NOT(0)=1
verify_cell(0, 0, 1, 1, 0)   # NOT(1)=0

# Cell 1: listens on 1, writes to 2
print("\nStep 3: Configure cell 1 (NOT gate, addr 1 -> addr 2)")
configure_cell(1, TOPO_NOT)
time.sleep(0.1)
armed, _ = get_status()
print(f"  armed_count={armed}")
verify_cell(1, 1, 2, 0, 1)   # NOT(0)=1
verify_cell(1, 1, 2, 1, 0)   # NOT(1)=0

# Chain: write 0 to addr 0 -> cell0 NOT->1 to addr 1 -> cell1 NOT->0 to addr 2
# Chain: write 0 to addr 0 -> cell0 NOT->1 to addr 1 -> cell1 NOT->0 to addr 2
print("\nStep 4: Chain test (addr 0 -> cell0 -> addr 1 -> cell1 -> addr 2)")
print("  Write 0 to addr 0: NOT->1 at addr 1, NOT->0 at addr 2")
drain(0.2)
t0 = time.time()
tx(CMD_DATA, 0, 0, "DATA 0 -> addr 0")
evts = []
deadline = time.time() + 5.0  # 5 second window — chain needs two ticks
while time.time() < deadline:
    try:
        e = pkt_q.get(timeout=0.2)
        if e[0] == 'fired':
            addr, data = e[1], e[2]
            evts.append((time.time() - t0, addr, data))
            label = {1: 'cell0->addr1', 2: 'RESULT at addr2'}.get(addr, hex(addr))
            print(f"    t={(time.time()-t0)*1000:7.2f}ms  addr={addr}  data={data}  {label}")
            if addr == 2:
                break  # got the result, no need to wait longer
    except queue.Empty:
        pass

cell0_fired = any(a == 1 and d == 1 for _, a, d in evts)
cell1_fired = any(a == 2 and d == 0 for _, a, d in evts)
print(f"\n  cell0 fired (addr1=1): {'YES' if cell0_fired else 'NO'}")
print(f"  cell1 fired (addr2=0): {'YES' if cell1_fired else 'NO'}")
print(f"  Chain: {'PASS ✓' if cell1_fired else 'FAIL ✗'}")

print("\nStep 5: PING all cells")
print("  Note: each cell pings to output_address (CELL_ID+1), not a common addr")
print("  Expect responses at addrs 1-8 with data=CELL_ID")
drain(0.1)
tx(CMD_PING, 0, 0, "PING broadcast")
evts = drain(1.0)  # longer wait — 8 cells responding
fired = [(e[1], e[2]) for e in evts if e[0] == 'fired']
print(f"  Responses ({len(fired)}): {[(f'addr={a}', f'data={d}') for a,d in fired]}")

running = False
time.sleep(0.05)
s.close()
print("\nDone.")
