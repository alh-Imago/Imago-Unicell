"""Quick ping test to check if cell responds at all."""
import serial, struct, time, sys

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
BAUD = 115200

print(f"Opening {PORT}...")
s = serial.Serial(PORT, BAUD, timeout=2)
time.sleep(0.2)

# Flush
if s.in_waiting: s.read(s.in_waiting)

def inject(cmd_bus, bus_addr, bus_data):
    pkt = struct.pack('>BIII', 0x01, cmd_bus, bus_addr, bus_data)
    print(f"  TX: {pkt.hex()}")
    s.write(pkt)

def read_response(label, timeout=1.0):
    deadline = time.time() + timeout
    buf = bytearray()
    while time.time() < deadline:
        if s.in_waiting:
            buf += s.read(s.in_waiting)
        time.sleep(0.01)
    if buf:
        print(f"  RX ({label}): {buf.hex()}")
    else:
        print(f"  RX ({label}): <nothing>")
    return buf

# 1. Status query
print("\n[1] Status query")
s.write(bytes([0x04]))
read_response("status")

# 2. CMD_PING (code=9, no auth needed)
print("\n[2] CMD_PING to cell 0")
CMD_PING = 9
cmd_bus = CMD_PING  # just the code, no auth
inject(cmd_bus, 0, 0)
read_response("ping response")

# 3. Try CMD_SET_INPUT_ADDR (code=2)
print("\n[3] CMD_SET_INPUT_ADDR = 0x1000")
CMD_SET_INPUT = 2
inject(CMD_SET_INPUT, 0, 0x1000)
time.sleep(0.05)

# 4. CMD_SET_OUTPUT_ADDR (code=3)  
print("\n[4] CMD_SET_OUTPUT_ADDR = 0x2000")
CMD_SET_OUTPUT = 3
inject(CMD_SET_OUTPUT, 0, 0x2000)
time.sleep(0.05)

# 5. Bootstrap RECONFIGURE word 0: auth_mask=0x2A5
print("\n[5] CMD_RECONFIGURE bootstrap word 0 (auth_mask)")
CMD_RECONFIG = 4
AUTH = 0x2A5
cmd_bus_reconfig = CMD_RECONFIG | ((AUTH & 0x7FF) << 4)
print(f"  cmd_bus = {cmd_bus_reconfig:#010x}")
inject(cmd_bus_reconfig, 0, AUTH & 0x7FF)
time.sleep(0.05)

# 6. Bootstrap RECONFIGURE word 1: config (GS_NOT topology=1, standard)
print("\n[6] CMD_RECONFIGURE bootstrap word 1 (config)")
config = 0x00000001  # topology bit 0 = GS_NOT, all else 0
inject(0, 0, config)  # CMD_NOP, cell already in RCFG_CONFIG state
time.sleep(0.05)

# 7. Status again
print("\n[7] Status after config")
s.write(bytes([0x04]))
read_response("status after config")

# 8. PING after config
print("\n[8] CMD_PING after config")
inject(CMD_PING, 0, 0)
read_response("ping after config")

# 9. Data write: send 0 to 0x1000, expect output at 0x2000
print("\n[9] Data write: 0 to 0x1000 (expect NOT(0)=1 at 0x2000)")
CMD_DATA = 1
cmd_data = CMD_DATA  # no auth
inject(cmd_data, 0x1000, 0)
read_response("data write response", timeout=2.0)

s.close()
