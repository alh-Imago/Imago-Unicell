"""The host script against a pretend card on a pty (checks the byte framing only, not the hardware)."""
import json, os, pty, sys, threading, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
serial = pytest.importorskip("serial")
import hexn_hexcard_host_v1 as Hh

VEC = {"pattern_id_hex": "90894555", "rows": 7, "tests": [
    {"name": "t", "chain_hex": "a1b2", "inputs": [[1, 5], [2, 7]], "mask": 6, "expected": [[3, 12, 40], [4, 99, 80]]}]}


def fake_card(fd, stop):
    buf = b""; os.set_blocking(fd, False)
    while not stop.is_set():
        try: d = os.read(fd, 100)
        except BlockingIOError: stop.wait(0.005); continue
        buf += d
        while buf:
            c = buf[:1]
            if c == b"I": os.write(fd, (0x90894555).to_bytes(4, "little") + bytes([7])); buf = buf[1:]
            elif c == b"W" or c == b"L" and False: os.write(fd, b"K"); buf = buf[1:]
            elif c == b"B":
                if len(buf) < 3: break
                os.write(fd, b"K"); buf = buf[3:]
            elif c == b"D":
                if len(buf) < 6: break
                os.write(fd, b"K"); buf = buf[6:]
            elif c == b"G":
                if len(buf) < 2: break
                os.write(fd, b"K"); buf = buf[2:]
            elif c == b"L":
                os.write(fd, bytes([2]) + bytes([3]) + (12).to_bytes(4, "little") + (40).to_bytes(2, "little") + bytes([4]) + (99).to_bytes(4, "little") + (80).to_bytes(2, "little")); buf = buf[1:]
            else: buf = buf[1:]


def test_selftest_against_a_pretend_card(monkeypatch):
    m, sl = pty.openpty(); stop = threading.Event(); th = threading.Thread(target=fake_card, args=(m, stop)); th.start()
    try:
        s = serial.Serial(os.ttyname(sl), 115200, timeout=2)
        assert Hh.ident(s) == (0x90894555, 7)
        assert Hh.run_test(s, VEC["tests"][0]) == VEC["tests"][0]["expected"]
    finally:
        stop.set(); th.join()
