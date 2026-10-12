"""Ledger #1088: the mutability test 2 generator (tools/board_mutability2_v1.py): carrier v1d subset + standalone command_cell_v4 + standalone sequencer_cell_v4, simulated with a testbench that plays the PC."""
import json
import os
import re
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import make_carrier_subset_v2 as sub  # noqa: E402
import board_mutability2_v1 as bm2  # noqa: E402

pytestmark = pytest.mark.skipif(not __import__("shutil").which("iverilog"), reason="iverilog missing")


def _run(*args):
    d = tempfile.mkdtemp()
    return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "board_mutability2_v1.py"), "--out", d, "--no-pnr", *args], capture_output=True, text=True, timeout=900), d


def test_subset_v2_is_the_v1d_carrier():
    t, removed = sub.make(["adder", "accum", "mul"])
    assert set(removed) == set(sub.CORES) - {"adder", "accum", "mul"}
    assert "module unicell_vix_carrier_v1dm #(" in t and "SEL_ADDON_CONFIG" in t
    for c in ("adder", "accum", "mul"):
        assert "CORE_%s (" % c.upper() in t


def test_every_session_starts_with_the_sacrificial_word_and_ends_with_complete():
    for p in bm2.phases():
        w = p["words"]
        sessions, cur = [], []
        for x in w:
            cur.append(x)
            if (x >> 20) & 7 == 7:
                sessions.append(cur); cur = []
        assert not cur and len(sessions) == 2, p["label"]
        for s in sessions:
            assert s[0] == bm2.SACRIFICE and s[-1] == 0x700001
        assert len(w) <= 12


def test_expected_values_come_from_the_operands():
    s = (bm2.A_WORD + bm2.B_WORD) & bm2.M32
    e = [p["expected"] for p in bm2.phases() if p["kind"] == "d"]
    assert e == [s, (bm2.A_WORD - bm2.B_WORD) & bm2.M32, ~s & bm2.M32, s >> 8, s & ~0xFF & bm2.M32, (bm2.A_WORD * bm2.B_WORD) & bm2.M32, s]
    st = [p for p in bm2.phases() if p["kind"] == "s"]
    assert (st[0]["first"], st[0]["last"]) == (0x12 + 0x34, 0x56 + 0x78) and (st[1]["first"], st[1]["last"]) == (0x12 * 0x34, 0x56 * 0x78)


def test_simulation_passes_and_every_break_is_caught():
    r, d = _run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "UCM2 PASS" in r.stdout and re.search(r"phase 5 core changed to mul: got 88885000", r.stdout)
    assert len(re.findall(r"reprogram took \d+ clocks", r.stdout)) == 9 and "stream 8 stream mul" in r.stdout
    meta = json.load(open(os.path.join(d, "mutability2.json")))
    assert meta["phases"][0]["expected"] == 0x12345678
    for m in ("nocfg", "wrongexp", "nocmd", "noseq"):
        r, _ = _run("--mutant", m)
        assert r.returncode == 0 and "caught (FAIL reported)" in r.stdout, (m, r.stdout)


def test_host_script_selftest():
    if not os.path.exists(os.path.join(ROOT, "fpga", "board_tests_mutability2", "mutability2.json")):
        pytest.skip("run tools/board_mutability2_v1.py first")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "fpga", "board_tests_mutability2", "mutability2_host.py"), "--selftest"], capture_output=True, text=True)
    assert r.returncode == 0 and "selftest ok" in r.stdout, r.stdout + r.stderr
