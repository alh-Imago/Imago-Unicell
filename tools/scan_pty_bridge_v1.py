#!/usr/bin/env python3
"""tools/scan_pty_bridge_v1.py -- ledger #1147: puts the simulated card (board_scan_v1.SimCard, the real Verilog in iverilog) behind a pseudo serial port, so the card-side host script
(fpga/board_tests_scan/scan_card_host.py) can be run end to end without the board.  Prints the port path on the first line, then serves until stdin closes.
  python3 tools/scan_pty_bridge_v1.py     (run in the background; pass the printed path to scan_card_host.py)"""
import os, pty, select, sys, termios, time, tty
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_scan_v1 as bs  # noqa: E402

m, s = pty.openpty()
tty.setraw(m); tty.setraw(s)
print(os.ttyname(s), flush=True)
card = bs.SimCard(cpb=8, tmo=3000, kind=(sys.argv[1] if len(sys.argv) > 1 else 'unicell'))
pending, last = b"", time.time()
try:
    while True:
        r, _, _ = select.select([m, sys.stdin], [], [], 0.02)
        if sys.stdin in r and not sys.stdin.readline():
            break
        if m in r:
            try:
                pending += os.read(m, 4096)
            except OSError:
                time.sleep(0.05)
            last = time.time()
        if pending and time.time() - last > 0.03:     # the host has stopped writing: hand the whole command to the card
            card.send(pending); pending = b""
            out = card.drain()
            if out:
                os.write(m, out)
finally:
    card.close()
