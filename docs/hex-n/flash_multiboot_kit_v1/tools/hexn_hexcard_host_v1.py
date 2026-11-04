#!/usr/bin/env python3
"""Talk to a hex card on a real board over its serial port (4 Nov 2026). Needs only pyserial and the JSON from hexn_hexcard_vector_v1.py.
  python3 hexn_hexcard_host_v1.py id    [--port /dev/ttyUSB1]            read PATTERN_ID and ROWS ('I'), print them
  python3 hexn_hexcard_host_v1.py watch [--port ...]                     read 'I' every second until Ctrl-C (use while tapping RECONFIG_N)
  python3 hexn_hexcard_host_v1.py selftest VECTOR.json [--port ...]      run every test in the vector, compare words and ticks
Protocol (hexn_frame_v2): I -> 4 bytes id LE + 1 byte rows; W -> K; B + chain bytes -> K; D row b0..b3 -> K; G mask -> K; L -> n, then n x (row, 4 data bytes LE, 2 tick bytes LE).
The card ignores a byte that arrives while it is still answering, so every command waits for its reply before the next is sent. Baud 115200 (the card divides 27 MHz by 234 = 115,385 baud, 0.16 % fast)."""
import argparse, json, sys, time
import serial


def rd(s, n, what):
    b = s.read(n)
    if len(b) != n: raise SystemExit("timeout waiting for %s (got %d of %d bytes: %s)" % (what, len(b), n, b.hex()))
    return b


def ident(s):
    s.reset_input_buffer(); s.write(b"I"); b = rd(s, 5, "'I' reply")
    return int.from_bytes(b[:4], "little"), b[4]


def k(s, what):
    b = rd(s, 1, what + " (K)")
    if b != b"K": raise SystemExit("%s: expected K, got %r" % (what, b))


def run_test(s, t):
    s.write(b"W"); k(s, "wipe")
    chain = bytes.fromhex(t["chain_hex"]); s.write(b"B" + chain); k(s, "chain load")
    for row, word in t["inputs"]:
        s.write(bytes([ord("D"), row]) + word.to_bytes(4, "little")); k(s, "D row %d" % row)
    s.write(bytes([ord("G"), t["mask"]])); k(s, "G")
    time.sleep(0.3)
    s.write(b"L"); n = rd(s, 1, "L count")[0]; got = []
    for _ in range(n):
        e = rd(s, 7, "L entry"); got.append([e[0], int.from_bytes(e[1:5], "little"), int.from_bytes(e[5:7], "little")])
    return got


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["id", "watch", "selftest"]); ap.add_argument("vector", nargs="?")
    ap.add_argument("--port", default="/dev/ttyUSB1"); ap.add_argument("--baud", type=int, default=115200)
    a = ap.parse_args(); s = serial.Serial(a.port, a.baud, timeout=2)
    if a.cmd == "id":
        pid, rows = ident(s); print("pattern id %08X rows %d" % (pid, rows))
    elif a.cmd == "watch":
        try:
            while True:
                try: pid, rows = ident(s); print(time.strftime("%H:%M:%S"), "pattern id %08X rows %d" % (pid, rows), flush=True)
                except SystemExit as e: print(time.strftime("%H:%M:%S"), "no answer:", e, flush=True)
                time.sleep(1)
        except KeyboardInterrupt: pass
    else:
        v = json.load(open(a.vector)); pid, rows = ident(s)
        print("card: id %08X rows %d; vector: id %s rows %d" % (pid, rows, v["pattern_id_hex"], v["rows"]))
        ok = pid == int(v["pattern_id_hex"], 16) and rows == v["rows"]
        if not ok: print("ID MISMATCH: wrong image on the card?")
        for t in v["tests"]:
            got = run_test(s, t); good = got == t["expected"]; ok &= good
            print("%-8s %s  words %s" % (t["name"], "PASS" if good else "FAIL", [hex(w) for _, w, _ in got]))
            if not good: print("   expected", t["expected"], "\n   got     ", got)
        print("SELFTEST", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
