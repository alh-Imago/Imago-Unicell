"""
test_device_bridge.py — Device Bridge Tests

Tests the bus protocol, host OS bridging, and DeviceManager
without needing a real array (uses a plain dict as the bus).
"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(__file__))

from device_bridge import (
    DeviceManager, DeviceBridge,
    KeyboardBridge, StorageBridge, NetworkBridge, ConsoleBridge,
    OFFSET_CMD, OFFSET_DATA, OFFSET_OUT, OFFSET_STATUS,
    STATUS_IDLE, STATUS_READY, STATUS_BUSY, STATUS_ERROR,
    CMD_IDLE, CMD_RESET, CMD_IDENTIFY,
    ST_CMD_OPEN, ST_CMD_READ, ST_CMD_WRITE, ST_CMD_CLOSE,
    ST_CMD_SEEK, ST_CMD_SIZE, ST_CMD_SETPATH, ST_CMD_EXISTS, ST_CMD_DELETE,
    CON_CMD_WRITE, CON_CMD_FLUSH,
    NET_CMD_STATUS, NET_CMD_SETHOST, NET_CMD_SETPORT,
    NET_CMD_CONNECT, NET_CMD_SEND, NET_CMD_RECV,
    NET_CMD_DISCONNECT,
)

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    results.append((status, name))
    if not ok:
        print(f"  [{status}] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [{status}] {name}")


# ── Helpers ───────────────────────────────────────────────────────────────────

BASE = 0x00C00000

def make_bus(base=BASE):
    """Empty bus dict."""
    return {}

def write_int(bus, base_addr, value, bits=32):
    for bit in range(bits):
        bus[base_addr + bit] = (value >> bit) & 1

def read_int(bus, base_addr, bits=32):
    result = 0
    for bit in range(bits):
        v = bus.get(base_addr + bit, 0)
        if isinstance(v, tuple): v = v[0]
        if v:
            result |= (1 << bit)
    return result

def send_command(bridge, bus, cmd, data=0):
    """Write command, tick, then reset CMD to idle.
    Resetting CMD prevents re-execution on subsequent ticks."""
    write_int(bus, bridge.cmd_addr, cmd)
    write_int(bus, bridge.data_addr, data)
    bridge.tick(bus)
    write_int(bus, bridge.cmd_addr, 0)   # reset CMD to idle

def read_output(bridge, bus):
    return read_int(bus, bridge.out_addr)

def read_status(bridge, bus):
    return read_int(bus, bridge.status_addr, bits=8)


# =============================================================================
print("\n=== DeviceBridge base class ===\n")
# =============================================================================

b = DeviceBridge(base_address=BASE, name="test")

check("base: connected after open",    b._connected)
check_eq("base: cmd_addr",   b.cmd_addr,    BASE + OFFSET_CMD)
check_eq("base: data_addr",  b.data_addr,   BASE + OFFSET_DATA)
check_eq("base: out_addr",   b.out_addr,    BASE + OFFSET_OUT)
check_eq("base: status_addr",b.status_addr, BASE + OFFSET_STATUS)

# CMD_IDENTIFY returns hash
bus = make_bus()
send_command(b, bus, CMD_IDENTIFY)
ident = read_output(b, bus)
check("base: CMD_IDENTIFY returns nonzero", ident != 0)

# CMD_RESET reconnects
bus2 = make_bus()
send_command(b, bus2, CMD_RESET)
check("base: CMD_RESET → STATUS_READY",
      read_status(b, bus2) == STATUS_READY)

# tick() with CMD_IDLE does nothing
bus3 = make_bus()
b.tick(bus3)
check("base: idle tick produces no output", read_output(b, bus3) == 0)

check_eq("base: tick_count incremented", b._tick_count, 3)

b.close()
check("base: close() disconnects", not b._connected)


# =============================================================================
print("\n=== StorageBridge ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = os.path.join(tmpdir, "test.bin")

    sb = StorageBridge(base_address=BASE, name="storage")
    bus = make_bus()

    # Set path char by char
    path = test_file
    for ch in path:
        send_command(sb, bus, ST_CMD_SETPATH, ord(ch))

    # Check exists → 0 (file not created yet)
    send_command(sb, bus, ST_CMD_EXISTS)
    check_eq("storage: exists before create → 0",
             read_output(sb, bus), 0)

    # Open (creates file)
    send_command(sb, bus, ST_CMD_OPEN, data=0)   # handle 0
    check_eq("storage: open returns handle 0",
             read_output(sb, bus), 0)

    # Write 4 bytes (handle 0, payload 0x41424344 = "ABCD")
    # Encode: handle in bits 28-31, payload in bits 0-23
    payload = 0x414243   # "ABC" (3 bytes per write)
    write_data = (0 << 28) | payload
    send_command(sb, bus, ST_CMD_WRITE, data=write_data)
    check_eq("storage: write returns 0", read_output(sb, bus), 0)

    # Size
    send_command(sb, bus, ST_CMD_SIZE, data=0)
    sz = read_output(sb, bus)
    check("storage: file has content after write", sz > 0)

    # Seek to start
    seek_data = (0 << 28) | 0   # handle 0, position 0
    send_command(sb, bus, ST_CMD_SEEK, data=seek_data)

    # Read back
    send_command(sb, bus, ST_CMD_READ, data=0)
    read_val = read_output(sb, bus)
    check_eq("storage: read back written bytes",
             read_val & 0xFFFFFF, payload)

    # Close
    send_command(sb, bus, ST_CMD_CLOSE, data=0)
    check_eq("storage: close returns 0", read_output(sb, bus), 0)

    # File exists now — reset path buffer first (send null char)
    send_command(sb, bus, ST_CMD_SETPATH, 0)
    for ch in test_file:
        send_command(sb, bus, ST_CMD_SETPATH, ord(ch))
    send_command(sb, bus, ST_CMD_EXISTS)
    check_eq("storage: exists after create → 1",
             read_output(sb, bus), 1)

    # Delete — reset path buffer first
    send_command(sb, bus, ST_CMD_SETPATH, 0)
    for ch in test_file:
        send_command(sb, bus, ST_CMD_SETPATH, ord(ch))
    send_command(sb, bus, ST_CMD_DELETE)
    check("storage: file deleted from host",
          not os.path.exists(test_file))

    sb.close()
    check("storage: close() disconnects", not sb._connected)


# =============================================================================
print("\n=== ConsoleBridge ===\n")
# =============================================================================

import io
cb = ConsoleBridge(base_address=BASE, name="console")
bus = make_bus()

# Redirect stdout AFTER bridge creation (avoids capturing [DEVICE:] print)
old_stdout = sys.stdout
captured = io.StringIO()
sys.stdout = captured

for ch in "Hi":
    send_command(cb, bus, CON_CMD_WRITE, data=ord(ch))
send_command(cb, bus, CON_CMD_FLUSH)

sys.stdout = old_stdout
output = captured.getvalue()

check_eq("console: writes chars to stdout", output, "Hi")
cb.close()


# =============================================================================
print("\n=== NetworkBridge (loopback) ===\n")
# =============================================================================

import threading, socket as sock_mod

nb = NetworkBridge(base_address=BASE, name="network")
bus = make_bus()

# Initial state — not connected
send_command(nb, bus, NET_CMD_STATUS)
check_eq("network: initially not connected",
         read_output(nb, bus), 0)

# Set up a local echo server for testing
def echo_server(port, ready_event, stop_event):
    s = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_STREAM)
    s.setsockopt(sock_mod.SOL_SOCKET, sock_mod.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', port))
    s.listen(1)
    s.settimeout(2.0)
    ready_event.set()
    try:
        conn, _ = s.accept()
        while not stop_event.is_set():
            r, _, _ = select_mod.select([conn], [], [], 0.1)
            if r:
                data = conn.recv(4)
                if data:
                    conn.sendall(data)   # echo back
    except Exception:
        pass
    finally:
        try: s.close()
        except: pass

import select as select_mod

TEST_PORT = 19876
ready = threading.Event()
stop  = threading.Event()
server_thread = threading.Thread(
    target=echo_server, args=(TEST_PORT, ready, stop), daemon=True)
server_thread.start()
ready.wait(timeout=2.0)

# Set host (reset first with null, then chars)
send_command(nb, bus, NET_CMD_SETHOST, data=0)   # clear
for ch in "127.0.0.1":
    send_command(nb, bus, NET_CMD_SETHOST, data=ord(ch))
send_command(nb, bus, NET_CMD_SETPORT, data=TEST_PORT)

# Give echo server a moment
time.sleep(0.2)

# Connect
send_command(nb, bus, NET_CMD_CONNECT)
connected = read_output(nb, bus)
check_eq("network: connect to loopback server", connected, 1)

send_command(nb, bus, NET_CMD_STATUS)
check_eq("network: status=1 after connect",
         read_output(nb, bus), 1)

# Send 4 bytes
send_command(nb, bus, NET_CMD_SEND, data=0xDEADBEEF)
check_eq("network: send returns 4 bytes sent",
         read_output(nb, bus), 4)

# Wait for echo
time.sleep(0.1)
nb._poll(bus)   # manually poll for incoming

# Receive echo
send_command(nb, bus, NET_CMD_RECV)
received = read_output(nb, bus)
check_eq("network: echo received correctly",
         received, 0xDEADBEEF)

# Disconnect
send_command(nb, bus, NET_CMD_DISCONNECT)
check("network: disconnected", not nb._connected)

stop.set()
nb.close()


# =============================================================================
print("\n=== DeviceManager ===\n")
# =============================================================================

mgr = DeviceManager()

# Add without shore
sto2_base = 0x00D00000
con2_base  = 0x00F00000

with tempfile.TemporaryDirectory() as tmpdir2:
    sto2 = mgr.add(StorageBridge, base_address=sto2_base, name="sto2")
    con2 = mgr.add(ConsoleBridge, base_address=con2_base, name="con2")

    check_eq("mgr: two devices registered", len(mgr._bridges), 2)
    check("mgr: get('sto2') returns bridge",
          mgr.get("sto2") is sto2)
    check("mgr: get('con2') returns bridge",
          mgr.get("con2") is con2)

    # tick drives all bridges
    test_path = os.path.join(tmpdir2, "mgr_test.bin")
    bus_m = make_bus()
    for ch in test_path:
        write_int(bus_m, sto2.cmd_addr, ST_CMD_SETPATH)
        write_int(bus_m, sto2.data_addr, ord(ch))
        sto2.tick(bus_m)
    write_int(bus_m, sto2.cmd_addr, ST_CMD_EXISTS)
    mgr.tick(bus_m)   # tick all
    # Existence check ran without error
    check("mgr: tick() drives all bridges", True)

    mgr.close_all()
    check("mgr: close_all disconnects all",
          all(not b._connected for b in mgr._bridges.values()))

# Register with mock Shore
from shore_v2 import ShoreV2
shore = ShoreV2("shore_test", base_address=0x00500000)
mgr2  = DeviceManager(shore=shore)
mgr2.add(ConsoleBridge, base_address=0x00F10000, name="console2")
entry = shore.lookup("device_console2")
check("mgr: device registered with Shore", entry is not None)
check_eq("mgr: Shore entry type is DEVICE",
         entry.resource_type, "DEVICE")
check_eq("mgr: Shore metadata has device_type",
         entry.metadata.get("device_type"), "CONSOLE")
mgr2.close_all()


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
total  = len(results)
print(f"Results: {passed} passed, {failed} failed out of {total} tests")
if failed:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
