"""
ping_test.py v2 — step by step diagnostic for unicell_v3
Checks each operation independently with raw hex visibility.
"""
import serial, struct, time, sys

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5

print(f"Opening {PORT} auth={AUTH:#05x}...")
s = serial.Serial(PORT, 115200, timeout=2)
time.sleep(0.3)
if s.in_waiting: 
    b = s.read(s.in_waiting)
    print(f"  Startup bytes: {b.hex()} ({b})")

def send_inject(cmd_bus, bus_addr, bus_data, label=""):
    pkt = struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data)
    print(f"  TX {label}: {pkt.hex()}")
    s.write(pkt)

def drain(label, wait=0.3):
    time.sleep(wait)
    buf = bytearray()
    while s.in_waiting:
        buf += s.read(s.in_waiting)
        time.sleep(0.01)
    if buf:
        print(f"  RX {label}: {buf.hex()}")
        # Parse RSP_FIRED (0x10)
        i = 0
        while i < len(buf):
            if buf[i] == 0x10 and i+9 < len(buf):
                addr = struct.unpack('>I', buf[i+1:i+5])[0]
                data = struct.unpack('>I', buf[i+5:i+9])[0]
                print(f"    → FIRED: addr={addr:#010x} data={data:#010x} ({data})")
                i += 10
            elif buf[i] == 0x11 and i+6 < len(buf):
                armed  = struct.unpack('>H', buf[i+1:i+3])[0]
                cycles = struct.unpack('>I', buf[i+3:i+7])[0]
                print(f"    → STATUS: armed={armed} cycles={cycles}")
                i += 7
            else:
                i += 1
    else:
        print(f"  RX {label}: <nothing>")
    return buf

def status(label=""):
    s.write(bytes([0x04]))
    return drain(f"status {label}", 0.3)

# ── Build cmd_bus words ────────────────────────────────────────────────────────
def cmd(code, auth=0, seq=0, ident=0):
    w  = (code & 0xF)
    w |= ((auth & 0x7FF) << 4)
    w |= (1 << 15)          # raw_addr
    w |= ((seq & 0x7F) << 22)
    w |= ((ident & 0x7) << 29)
    return w

CMD_NOP    = 0
CMD_SET_IN = 2
CMD_SET_OUT= 3
CMD_RECONF = 4
CMD_FREEZE = 5
CMD_RELEASE= 6
CMD_DATA   = 1
CMD_PING   = 9

IN_ADDR  = 0x1000
OUT_ADDR = 0x2000

print("\n── Step 1: Status ──")
status("initial")

print("\n── Step 2: Set addresses ──")
send_inject(cmd(CMD_SET_IN),  0, IN_ADDR,  "SET_INPUT_ADDR")
time.sleep(0.05)
send_inject(cmd(CMD_SET_OUT), 0, OUT_ADDR, "SET_OUTPUT_ADDR")
time.sleep(0.05)

print("\n── Step 3: Bootstrap RECONFIGURE ──")
print("  Word 0: auth_mask")
send_inject(cmd(CMD_RECONF, auth=0), 0, AUTH & 0x7FF, "RECONF auth_mask")
time.sleep(0.05)
print("  Word 1: config (GS_NOT=topology bit 0, standard)")
config = 0x00000001  # topology bit 0 only
send_inject(cmd(CMD_NOP), 0, config, "RECONF config_word")
time.sleep(0.05)

print("\n── Step 4: Status after config ──")
status("after config")

print("\n── Step 5: PING ──")
send_inject(cmd(CMD_PING), 0, 0, "PING")
drain("ping", 0.5)

print("\n── Step 6: Data write NOT(0) ──")
send_inject(cmd(CMD_DATA), IN_ADDR, 0, "data 0→NOT(0)=1?")
drain("data 0", 0.5)

print("\n── Step 7: Data write NOT(1) ──")
send_inject(cmd(CMD_DATA), IN_ADDR, 1, "data 1→NOT(1)=0?")
drain("data 1", 0.5)

print("\n── Step 8: Final status ──")
status("final")

s.close()
print("\nDone.")
