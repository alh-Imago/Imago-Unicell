"""Simulation: several JtagLink sessions in a row on the same card (the card keeps its byte counters between sessions; unread bytes are left behind on purpose). The host must line up with the card at the start of each session. The old host (before the _sync fix) hangs on the second session."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_jtag_host_v1 as J, hexn_jtag_check_v1 as C
ex = J.SimExec(C.build(), ["+flip=0"]); r = random.Random(9); bad = 0
for sess in range(4):
    link = J.JtagLink(ex.scan)
    for _ in range(12):
        k = r.randint(1, 20); data = bytes(r.randrange(255) for _ in range(k)); link.write(data); got = link.read(k)
        if got != bytes((x + 1) & 255 for x in data): bad += 1
    print("session", sess, "ok" if not bad else "MISMATCH")
    if sess == 1: link.write(bytes([5, 6, 7]))   # leave unread bytes on the card: the next session must discard them
ex.close(); print("TWO-SESSION TEST", "PASS" if not bad else "FAIL"); sys.exit(bool(bad))
