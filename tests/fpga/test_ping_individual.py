"""
test_ping_individual.py -- Ping each cell individually with unique response addresses.

For each cell:
  1. Temporarily set output_addr to a unique probe address (0xF000 + cell_id)
  2. Send PING
  3. Wait for response at that probe address
  4. Report: cell alive, actual CELL_ID in data
  5. Restore output_addr (send SET_OUT with original address)

This avoids wired-OR collisions entirely.

Usage: python test_ping_individual.py COM4 0x2A5
       (run AFTER configuring cells with another test)
"""
import serial, struct, time, sys, threading, queue

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5
BAUD = 115200

s = serial.Serial(PORT, BAUD, timeout=3)
time.sleep(0.3)
if s.in_waiting: s.read(s.in_waiting)

pkt_q  = queue.Queue()
running = True

def rx_thread():
    buf = bytearray()
    while running:
        try:
            if s.in_waiting:
                buf += s.read(s.in_waiting)
        except: break
        while len(buf) >= 10:
            if buf[0] == 0x10:
                addr = struct.unpack('>I', buf[1:5])[0]
                data = struct.unpack('>I', buf[5:9])[0]
                pkt_q.put((addr, data))
                buf = buf[10:]
            elif buf[0] == 0x11 and len(buf) >= 7:
                buf = buf[7:]
            else:
                buf = buf[1:]
        time.sleep(0.001)

threading.Thread(target=rx_thread, daemon=True).start()

def tx(cmd_bus, bus_addr, bus_data):
    s.write(struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data))
    time.sleep(0.015)  # 15ms settle

def freeze():
    s.write(bytes([0x06]))
    time.sleep(0.05)

def release():
    s.write(bytes([0x07]))
    time.sleep(0.05)

def drain(wait=0.3):
    time.sleep(wait)
    evts = []
    while not pkt_q.empty():
        try: evts.append(pkt_q.get_nowait())
        except: break
    return evts

def cmd_noauth(code): return (code & 0xF) | (1 << 15)
def cmd_auth(code):   return (code & 0xF) | ((AUTH & 0x7FF) << 4) | (1 << 15)

SET_OUT = cmd_auth(3)
SET_OUT_NA = cmd_noauth(3)   # for cells with auth_mask=0
PING = cmd_noauth(9)

NUM_CELLS = 6
PROBE_BASE = 0xF000  # unique probe addresses: 0xF000, 0xF001, ...

def ping_cell(cell_id, original_out_addr, has_auth=True):
    """
    Ping a specific cell by routing its output to a unique probe address.
    Returns (alive, cell_id_reported, actual_out_addr_before_probe)
    """
    probe_addr = PROBE_BASE + cell_id

    # Set output to probe address
    so = SET_OUT if has_auth else SET_OUT_NA
    tx(so, cell_id, probe_addr)

    # Clear queue
    drain(0.05)

    # Send PING
    tx(PING, cell_id, 0)

    # Wait for response at probe address
    deadline = time.time() + 0.5
    while time.time() < deadline:
        try:
            addr, data = pkt_q.get(timeout=0.1)
            if addr == probe_addr:
                # Restore original output address
                tx(so, cell_id, original_out_addr)
                return True, data, probe_addr
        except queue.Empty:
            pass

    # No response -- restore anyway
    tx(so, cell_id, original_out_addr)
    return False, None, probe_addr


print(f"\n=== Individual cell ping on {PORT} auth={AUTH:#05x} ===\n")
print("Assumes cells already configured. Temporarily redirects")
print("each cell's output to a unique probe address.\n")

# Expected output addresses (adjust if different)
# These are the addresses from test_sync_wait topology
expected_out = {
    0: 0x2000,   # BUS01
    1: 0x3000,   # BUS12
    2: 0x4000,   # BUS23
    3: 0x5000,   # BUS35
    4: 0x5000,   # fast path
    5: 0x7000,   # RESULT
}

print(f"  {'Cell':>4}  {'Alive':>6}  {'CELL_ID':>8}  {'Status':>10}")
print(f"  {'----':>4}  {'-----':>6}  {'-------':>8}  {'------':>10}")

for cell_id in range(NUM_CELLS):
    orig = expected_out.get(cell_id, 0)
    alive, reported_id, probe = ping_cell(cell_id, orig, has_auth=True)

    if alive:
        id_ok = (reported_id == cell_id)
        print(f"  {cell_id:>4}  {'YES':>6}  {reported_id:>8}  "
              f"{'CELL_ID OK ✓' if id_ok else f'CELL_ID={reported_id} ✗':>10}")
    else:
        print(f"  {cell_id:>4}  {'NO':>6}  {'---':>8}  {'no response ✗':>10}")

print("\nDone.")
running = False
time.sleep(0.05)
s.close()
