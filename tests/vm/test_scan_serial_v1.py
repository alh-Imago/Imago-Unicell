"""Ledger #1146: in-flight capture / restore over the CRC-framed serial protocol, on the real design in simulation (tools/board_scan_v1.py, scan_host_v1.py, scan_flow_check_v1.py)."""
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
TOOL = os.path.join(ROOT, "tools", "scan_flow_check_v1.py")
sys.path.insert(0, os.path.join(ROOT, "tools"))


def flow(*args):
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        pytest.fail("iverilog missing: this test must not pass by skipping")
    return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, timeout=1500)


def test_host_crc_and_frames_match_the_documented_format():
    import scan_host_v1 as h
    f = h.w_frame(0x0102, 5, bytes(range(32)))
    assert len(f) == 40 + 1 and f[:1] == b"W" and f[1:5] == bytes([1, 2, 5, 8])
    assert int.from_bytes(f[-4:], "big") == h.crc32(bytes([1, 2, 5, 8]) + bytes(range(32)))
    line = b"UCS lcordic ses=0001 seq=3 of=8 d=" + b"00" * 32 + b" crc=12345678\r\n"
    assert h.LINE.search(line) and not h.LINE.search(line.replace(b"lcordic", b"other"))


def test_clean_round_trip_then_damage_on_the_wire():
    # clean, then a damaged chunk each way, a lost byte, a damaged reply: every one must end identical to the undamaged run
    for sc in ("clean", "dump_flip", "write_flip", "write_drop", "reply_flip"):
        r = flow("--scenario", sc)
        assert r.returncode == 0 and (sc + " -> PASS") in r.stdout, r.stdout[-800:] + r.stderr[-500:]


def test_persistent_damage_is_refused_not_hidden():
    for sc in ("persistent_write", "persistent_dump"):
        r = flow("--scenario", sc)
        assert r.returncode == 0 and "ScanError" in r.stdout and "PASS" not in r.stdout, r.stdout[-800:]


def test_card_without_crc_check_is_caught_by_the_read_back():
    r = flow("--scenario", "write_flip", "--mutant", "nocrc")
    assert "READ-BACK DIFFERS" in r.stdout and "PASS" not in r.stdout, r.stdout[-800:]
