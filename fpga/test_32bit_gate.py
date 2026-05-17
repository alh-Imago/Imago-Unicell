"""
test_32bit_gate.py — 32-bit gate tree validation

Confirms the gate tree operates on full 32-bit words, not just bit 0.

Every test uses a word with multiple bits set (e.g. 0xDEADBEEF) where the
1-bit result and 32-bit result are clearly different:

  1-bit NOT(0xDEADBEEF): NOT(bit0=1)        = 0x00000000
  32-bit NOT(0xDEADBEEF): ~0xDEADBEEF       = 0x21524110

If any test returns a 1-bit result (0x00000000 or 0x00000001) the gate
tree is still operating on bit 0 only and the fix did not take.

Usage:
    python test_32bit_gate.py COM4
    python test_32bit_gate.py COM4 0x2A5

Cell map:
    cell 0: PASS  addr 0x10 -> 0x20   (word passthrough)
    cell 1: NOT   addr 0x10 -> 0x20   (bitwise NOT)
    cell 2: NOT   addr 0x30 -> 0x31   (NOT chain stage 1)
    cell 3: NOT   addr 0x31 -> 0x32   (NOT chain stage 2 — NOT(NOT(x))=x)
    cell 4: PASS  addr 0x40 -> 0x41   (latch_in store/read)
    cell 5: PASS  addr 0x50 -> 0x51   (one_shot: fires once)
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
M32 = 0xFFFFFFFF

def mk_cmd(code, auth=0, cell_id=BROADCAST):
    return (code & 0xF) | ((auth & 0x7FF) << 4) | (1 << 15) | ((cell_id & 0x7FF) << 16)

CMD_DATA = mk_cmd(1)
TOPO_NOT  = 0b0000000001
TOPO_PASS = 0b0000000000
TOPO_AND  = 0b0000000111
TOPO_OR   = 0b0000100100
TOPO_XOR  = 0b0010111100
TOPO_XNOR = 0b0000111100

def mk_cfg(topo, auth_mask=0, one_shot=0, latch_in=0, invert_out=0, edge_mode=0):
    w  = (topo & 0x3FF)
    w |= (auth_mask & 0x7FF) << 11
    w |= 1 << 22
    w |= (1 if edge_mode  else 0) << 10
    w |= (1 if latch_in   else 0) << 26
    w |= (1 if invert_out else 0) << 25
    w |= (1 if one_shot   else 0) << 30
    return w

def tx(cmd, addr, data):
    s.write(struct.pack('>BIII', 0x01, cmd, addr, data))
    time.sleep(0.030)   # 12 MHz — slightly more relaxed timing

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

def configure(cell_id, topo, in_addr, out_addr, auth=AUTH,
              one_shot=0, latch_in=0, invert_out=0, edge_mode=0):
    cfg = mk_cfg(topo, auth_mask=auth, one_shot=one_shot,
                 latch_in=latch_in, invert_out=invert_out, edge_mode=edge_mode)
    tx(mk_cmd(2, auth, cell_id), 0, in_addr)
    tx(mk_cmd(3, auth, cell_id), 0, out_addr)
    tx(mk_cmd(4, auth, cell_id), 0, cfg)
    time.sleep(0.05)

def send_twice(addr, data):
    """Two arrivals at same address — triggers two-arrival model."""
    tx(CMD_DATA, addr, data)
    time.sleep(0.03)
    tx(CMD_DATA, addr, data)

def send_ab(addr, a, b):
    """Send A then B to same address — binary op (AND/OR/XOR etc)."""
    tx(CMD_DATA, addr, a)   # first arrival: stored as a_data
    time.sleep(0.03)
    tx(CMD_DATA, addr, b)   # second arrival: triggers gate(a_data, b)

def collect(timeout=1.0):
    evts = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            e = pkt_q.get(timeout=0.05)
            if e[0] == 'fired':
                evts.append((e[1], e[2]))
        except queue.Empty:
            pass
    return evts

# ── Test scaffolding ──────────────────────────────────────────────────────────

pass_count = 0
fail_count = 0

def chk(name, got, exp):
    global pass_count, fail_count
    note = ""
    if got is None:
        print(f"  FAIL  {name}")
        print(f"        got=NOTHING  exp={exp:#010x}  <-- no output received")
        fail_count += 1
        return
    if got in (0x00000000, 0x00000001) and exp not in (0x00000000, 0x00000001):
        note = "  <-- LOOKS LIKE 1-BIT RESULT"
    if got == exp:
        print(f"  PASS  {name}")
        pass_count += 1
    else:
        print(f"  FAIL  {name}")
        print(f"        got={got:#010x}  exp={exp:#010x}{note}")
        fail_count += 1

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ── Test words — chosen so 1-bit and 32-bit results are unambiguous ───────────
A = 0xDEADBEEF   # bit0=1, many bits set
B = 0xCAFEBABE   # bit0=0, many bits set
C = 0xA5A5A5A5   # alternating bits
D = 0x12345678   # bit0=0, ascending

NOT_A  = (~A) & M32   # 0x21524110
NOT_B  = (~B) & M32   # 0x35014541
AND_AB = A & B         # 0xCAADBAAE
OR_AB  = A | B         # 0xDEFFBEFF
XOR_AB = A ^ B         # 0x14530451
XNOR_AB = (~XOR_AB) & M32  # 0xEBACFBAE

# ─────────────────────────────────────────────────────────────────────────────
section("1. PASS — full word passthrough")
# If 1-bit: output = bit0 of A = 1 = 0x00000001
# If 32-bit: output = 0xDEADBEEF
reset()
configure(0, TOPO_PASS, in_addr=0x10, out_addr=0x20)
send_twice(0x10, A)
evts = collect()
got = next((d for a,d in evts if a == 0x20), None)
print(f"  PASS(0x{A:08X}): got {('0x'+format(got,'08X')) if got is not None else 'NOTHING'}")
chk("PASS(A) = A", got, A)

# ─────────────────────────────────────────────────────────────────────────────
section("2. NOT — bitwise complement")
# If 1-bit: NOT(bit0=1) = 0 = 0x00000000
# If 32-bit: NOT(0xDEADBEEF) = 0x21524110
reset()
configure(0, TOPO_NOT, in_addr=0x10, out_addr=0x20)
send_twice(0x10, A)
evts = collect()
got = next((d for a,d in evts if a == 0x20), None)
print(f"  NOT(0x{A:08X}): got {('0x'+format(got,'08X')) if got is not None else 'NOTHING'}")
print(f"  expected 0x{NOT_A:08X}")
chk("NOT(A) = ~A", got, NOT_A)

# Word with bit0=0: NOT should give bit0=1 in result
reset()
configure(0, TOPO_NOT, in_addr=0x10, out_addr=0x20)
send_twice(0x10, B)
evts = collect()
got = next((d for a,d in evts if a == 0x20), None)
print(f"  NOT(0x{B:08X}): got {('0x'+format(got,'08X')) if got is not None else 'NOTHING'}")
print(f"  expected 0x{NOT_B:08X}")
chk("NOT(B) = ~B", got, NOT_B)

# ─────────────────────────────────────────────────────────────────────────────
section("3. NOT(NOT(A)) = A  — two-cell chain")
# Two-arrival model: each cell needs TWO arrivals at its input_address.
# stage1 (cell0): needs 2x at 0x10 — send_twice provides this, cell0 fires once -> 0x11
# stage2 (cell1): needs 2x at 0x11 — must send_twice again so cell0 fires twice
# Each send_twice(0x10, A) causes cell0 to fire once onto 0x11.
# Two send_twice calls give cell1 both its arrivals.
reset()
configure(0, TOPO_NOT, in_addr=0x10, out_addr=0x11)
configure(1, TOPO_NOT, in_addr=0x11, out_addr=0x12)
send_twice(0x10, A)   # cell0 first fire -> NOT(A) onto 0x11 (cell1 first arrival)
time.sleep(0.05)
send_twice(0x10, A)   # cell0 second fire -> NOT(A) onto 0x11 (cell1 second arrival -> fires)
evts = collect(1.5)
hits_11 = [d for a,d in evts if a == 0x11]
hits_12 = [d for a,d in evts if a == 0x12]
mid = hits_11[-1] if hits_11 else None   # last value at 0x11
got = hits_12[-1] if hits_12 else None   # last value at 0x12
print(f"  stage1 (0x11): {('0x'+format(mid,'08X')) if mid is not None else 'NOTHING'} (expected 0x{NOT_A:08X})")
print(f"  stage2 (0x12): {('0x'+format(got,'08X')) if got is not None else 'NOTHING'} (expected 0x{A:08X})")
chk("NOT(NOT(A)) = A (stage1 correct)", mid, NOT_A)
chk("NOT(NOT(A)) = A (stage2 correct)", got, A)

# ─────────────────────────────────────────────────────────────────────────────
section("4. AND — bitwise AND of two words")
# If 1-bit: AND(1,0) = 0 = 0x00000000
# If 32-bit: AND(0xDEADBEEF, 0xCAFEBABE) = 0xCAADBAAE
reset()
configure(0, TOPO_AND, in_addr=0x10, out_addr=0x20)
send_ab(0x10, A, B)   # A first (stored), B second (trigger)
evts = collect()
got = next((d for a,d in evts if a == 0x20), None)
print(f"  AND(0x{A:08X}, 0x{B:08X})")
print(f"  got      {('0x'+format(got,'08X')) if got is not None else 'NOTHING'}")
print(f"  expected 0x{AND_AB:08X}")
chk("AND(A,B) = A&B", got, AND_AB)

# ─────────────────────────────────────────────────────────────────────────────
section("5. OR — bitwise OR of two words")
reset()
configure(0, TOPO_OR, in_addr=0x10, out_addr=0x20)
send_ab(0x10, A, B)
evts = collect()
got = next((d for a,d in evts if a == 0x20), None)
print(f"  OR(0x{A:08X}, 0x{B:08X})")
print(f"  got      {('0x'+format(got,'08X')) if got is not None else 'NOTHING'}")
print(f"  expected 0x{OR_AB:08X}")
chk("OR(A,B) = A|B", got, OR_AB)

# ─────────────────────────────────────────────────────────────────────────────
section("6. XOR — bitwise XOR of two words")
reset()
configure(0, TOPO_XOR, in_addr=0x10, out_addr=0x20)
send_ab(0x10, A, B)
evts = collect()
got = next((d for a,d in evts if a == 0x20), None)
print(f"  XOR(0x{A:08X}, 0x{B:08X})")
print(f"  got      {('0x'+format(got,'08X')) if got is not None else 'NOTHING'}")
print(f"  expected 0x{XOR_AB:08X}")
chk("XOR(A,B) = A^B", got, XOR_AB)

# ─────────────────────────────────────────────────────────────────────────────
section("7. XNOR — equality / comparator")
# This is the key one: single cell 32-bit equality comparator
# If 1-bit: XNOR(1,0) = 0 = 0x00000000
# If 32-bit: XNOR(A,A) should give 0xFFFFFFFF (all bits equal)
reset()
configure(0, TOPO_XNOR, in_addr=0x10, out_addr=0x20)
send_ab(0x10, A, A)   # same word both arrivals: all bits equal
evts = collect()
got = next((d for a,d in evts if a == 0x20), None)
print(f"  XNOR(A,A): got {('0x'+format(got,'08X')) if got is not None else 'NOTHING'}")
print(f"  expected 0xFFFFFFFF (all bits equal)")
chk("XNOR(A,A) = 0xFFFFFFFF", got, M32)

reset()
configure(0, TOPO_XNOR, in_addr=0x10, out_addr=0x20)
send_ab(0x10, A, B)   # different words: XNOR gives ~(A^B)
evts = collect()
got = next((d for a,d in evts if a == 0x20), None)
print(f"  XNOR(A,B): got {('0x'+format(got,'08X')) if got is not None else 'NOTHING'}")
print(f"  expected 0x{XNOR_AB:08X}")
chk("XNOR(A,B) = ~(A^B)", got, XNOR_AB)

# ─────────────────────────────────────────────────────────────────────────────
section("8. latch_in — stores word, re-emits on each arrival")
# Write a word, read it back — confirms full word survives storage
reset()
configure(0, TOPO_PASS, in_addr=0x40, out_addr=0x41, latch_in=1)
send_twice(0x40, A)       # first pair: stores A, fires PASS(A)=A
evts = collect()
got1 = next((d for a,d in evts if a == 0x41), None)
print(f"  stored 0x{A:08X}, read back {('0x'+format(got1,'08X')) if got1 is not None else 'NOTHING'}")
chk("latch_in PASS(A) = A", got1, A)

# Overwrite with C, confirm new value
send_twice(0x40, C)
evts = collect()
got2 = next((d for a,d in evts if a == 0x41), None)
print(f"  overwrite 0x{C:08X}, read back {('0x'+format(got2,'08X')) if got2 is not None else 'NOTHING'}")
chk("latch_in overwrite PASS(C) = C", got2, C)

# ─────────────────────────────────────────────────────────────────────────────
section("9. invert_out — bitwise NOT on output word")
# invert_out flips all 32 bits of the result on drain
# With PASS topology: output = ~A
reset()
configure(0, TOPO_PASS, in_addr=0x10, out_addr=0x20, invert_out=1)
send_twice(0x10, A)
evts = collect()
got = next((d for a,d in evts if a == 0x20), None)
print(f"  PASS+invert_out(0x{A:08X}): got {('0x'+format(got,'08X')) if got is not None else 'NOTHING'}")
print(f"  expected 0x{NOT_A:08X}")
chk("PASS+invert_out(A) = ~A", got, NOT_A)

# ─────────────────────────────────────────────────────────────────────────────
section("10. loop_back — result feeds back as next a_data")
# NOT + loop_back: first fire NOT(A)=~A, second fire NOT(~A)=A, oscillates
reset()
configure(0, TOPO_NOT, in_addr=0x10, out_addr=0x20, latch_in=1)
# Seed with A
send_twice(0x10, A)
evts = collect(0.5)
got1 = next((d for a,d in evts if a == 0x20), None)
# Trigger again — latch_in means single arrival fires using loop_back a_data
tx(CMD_DATA, 0x10, 0)   # trigger value doesn't matter for NOT — a_data used
evts = collect(0.5)
got2 = next((d for a,d in evts if a == 0x20), None)
print(f"  seed=0x{A:08X}")
print(f"  fire1: {('0x'+format(got1,'08X')) if got1 is not None else 'NOTHING'}  (expected NOT_A=0x{NOT_A:08X})")
print(f"  fire2: {('0x'+format(got2,'08X')) if got2 is not None else 'NOTHING'}  (expected A=0x{A:08X})")
chk("latch NOT fire1 = ~A", got1, NOT_A)
chk("latch NOT fire2 = A (oscillates)", got2, A)

# ─────────────────────────────────────────────────────────────────────────────
section("SUMMARY")
print(f"\n  {pass_count} passed   {fail_count} failed")
if fail_count == 0:
    print("\n  32-BIT GATE TREE CONFIRMED ON SILICON")
    print("  All operations produce full 32-bit results.")
else:
    print(f"\n  {fail_count} FAILURES — check for 1-bit result pattern (0x00000000 or 0x00000001)")
    print("  if results are only 0/1, gate tree fix did not synthesise correctly.")

running = False
time.sleep(0.05)
s.close()
