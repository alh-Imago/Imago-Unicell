#!/usr/bin/env python3
"""(v2, 4 Nov 21:10: clone of v1 with a FINE probe: while waiting for the card it asks 'I' with a short read timeout (--probe 0.05 s) every --poll (0.05 s), instead of v1's 1 s read timeout + 0.3 s sleep which made every figure jump from 0 to 1.3 s; and it prints how long the loader command itself ran.) Hop through the flash ring from the PC and check every card that comes up (4 Nov 2026). No wire: each hop is `openFPGALoader -b tangnano20k -r`
(measured 4 Nov 20:45: it follows the ring like the pin 9 tap). After a hop the chip reloads and the card is silent for a moment (Alan 20:45: 'these have to be
run with a pause between, gives it time to switch and settle, or the id fails'), so the script waits --settle seconds, then asks 'I' every 0.3 s until the card answers
(or --timeout runs out); v2 polls every 0.05 s. The id picks the vector file; the vector's selftest is run; the program and state are reloaded by the vector each time, as a hop wipes the chip.
  python3 hexn_ring_cycle_v2.py VECTOR.json [VECTOR.json ...] [--rounds 6] [--settle 3] [--timeout 15] [--port /dev/ttyUSB1] [--no-hop-first] [--loader "openFPGALoader -b tangnano20k -r"]
Round 0 checks the card that is already running (no hop). Each later round hops once, then waits, reads the id, requires a DIFFERENT id from the one before (a ring of two or more), and runs that card's selftest.
Prints one line per round: round, id, seconds from the end of the loader command to the first answer (a coarse upper bound on the reload time, includes --settle), PASS/FAIL. Exit 0 only if every round passes.
Nothing here writes flash."""
import argparse, json, shlex, subprocess, sys, time
import hexn_hexcard_host_v1 as Hh


def try_id(s):
    """one 'I' try: (pid, rows) or None if the card did not answer in time"""
    s.reset_input_buffer(); s.write(b"I"); b = s.read(5)
    return (int.from_bytes(b[:4], "little"), b[4]) if len(b) == 5 else None


def wait_id(s, settle, timeout, sleep=time.sleep, clock=time.monotonic, probe=0.05, poll=0.05):
    t0 = clock(); sleep(settle); old = getattr(s, "timeout", None)
    try:
        if old is not None: s.timeout = probe
        while True:
            r = try_id(s)
            if r: return r, clock() - t0
            if clock() - t0 > timeout: return None, clock() - t0
            sleep(poll)
    finally:
        if old is not None: s.timeout = old


def selftest(s, v):
    ok = True
    try:
        for t in v["tests"]:
            got = Hh.run_test(s, t); ok &= got == t["expected"]
    except SystemExit:      # the host helper raises this when the card stops answering mid-test
        return False
    return ok


def cycle(s, vectors, rounds, settle, timeout, hop, out=print, sleep=time.sleep, clock=time.monotonic, probe=0.05, poll=0.05):
    """vectors: {pattern_id: vector dict}. Returns list of (round, id or None, seconds, ok)."""
    res = []; prev = None; allok = True
    for n in range(rounds + 1):
        ld = 0.0
        if n == 0: r, dt = wait_id(s, 0, timeout, sleep, clock, probe, poll)
        else:
            t1 = clock(); hop(); ld = clock() - t1
            r, dt = wait_id(s, settle, timeout, sleep, clock, probe, poll)
        ok = False; pid = None
        if r is None: why = "NO ANSWER"
        else:
            pid, rows = r
            v = vectors.get(pid)
            if v is None: why = "UNKNOWN ID (no vector given for it)"
            elif rows != v["rows"]: why = "ROWS MISMATCH"
            elif n > 0 and pid == prev: why = "SAME CARD (no hop happened)"
            else:
                ok = selftest(s, v); why = "PASS" if ok else "SELFTEST FAIL"
        out("round %d  id %s  loader ran %.2fs, first answer %.2fs after it ended  %s" % (n, "%08X" % pid if pid is not None else "--------", ld, dt, why) if n else "round %d  id %s  (already running)  %s" % (n, "%08X" % pid if pid is not None else "--------", why))
        res.append((n, pid, dt, ok)); allok &= ok; prev = pid
        if r is None: break
    out("RING CYCLE %s  (%d of %d rounds passed)" % ("PASS" if allok else "FAIL", sum(1 for x in res if x[3]), rounds + 1))
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("vectors", nargs="+"); ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--settle", type=float, default=3.0); ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--probe", type=float, default=0.05); ap.add_argument("--poll", type=float, default=0.05); ap.add_argument("--port", default="/dev/ttyUSB1"); ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--loader", default="openFPGALoader -b tangnano20k -r")
    a = ap.parse_args(); import serial
    vecs = {}
    for p in a.vectors: v = json.load(open(p)); vecs[int(v["pattern_id_hex"], 16)] = v
    s = serial.Serial(a.port, a.baud, timeout=1.0)
    def hop():
        # the serial port is released by the card while it reloads; the loader uses the other (JTAG) channel
        subprocess.run(shlex.split(a.loader), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res = cycle(s, vecs, a.rounds, a.settle, a.timeout, hop, probe=a.probe, poll=a.poll)
    sys.exit(0 if all(x[3] for x in res) else 1)


if __name__ == "__main__":
    main()
