"""Ledger #1086: the mutability test 1 generator (tools/board_mutability_v1.py): the carrier subset, the two wrappers in simulation, the deliberate breaks, the host script's framing."""
import json
import os
import re
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import make_carrier_subset_v1 as sub  # noqa: E402
import board_mutability_v1 as bm  # noqa: E402

pytestmark = pytest.mark.skipif(not __import__("shutil").which("iverilog"), reason="iverilog missing")


def _run(*args):
    d = tempfile.mkdtemp()
    return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "board_mutability_v1.py"), "--out", d, "--no-pnr", *args], capture_output=True, text=True, timeout=900), d


def test_subset_keeps_only_the_named_cores():
    t, removed = sub.make(["adder", "accum", "mul"])
    assert set(removed) == set(sub.CORES) - {"adder", "accum", "mul"}
    for c in ("adder", "accum", "mul"):
        assert "CORE_%s (" % c.upper() in t
    for c in removed:
        assert "CORE_%s (" % c.upper() not in t
    assert "module unicell_vix_carrier_v1m #(" in t and "assign nano_dn = 0;" in t
    with pytest.raises(SystemExit):
        sub.make(["adder", "nosuch"])


def test_expected_words_come_from_the_operands():
    s = (bm.A_WORD + bm.B_WORD) & bm.M32
    e = [p[4] for p in bm.phases()]
    assert e == [s, (bm.A_WORD - bm.B_WORD) & bm.M32, ~s & bm.M32, s >> 8, s & ~0xFF & bm.M32, (bm.A_WORD * bm.B_WORD) & bm.M32, s]
    assert e[0] == e[6] and len(set(e)) == 6


def test_both_wrappers_pass_in_simulation_and_the_breaks_are_caught():
    r, d = _run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "res=P ok=7F to=00" in r.stdout and "UCMH PASS" in r.stdout
    assert re.search(r"phase 5 core changed to mul: got 88885000", r.stdout)
    meta = json.load(open(os.path.join(d, "mutability1.json")))
    assert [p["expected"] for p in meta["phases"]][0] == 0x12345678 and len(meta["phases"][0]["cfg_word_hex"]) == 40
    for m in ("nocfg", "wrongexp"):
        r, _ = _run("--mutant", m)
        assert r.returncode == 0 and r.stdout.count("caught (FAIL reported)") == 2, (m, r.stdout)
    r, _ = _run("--mutant", "nocfg")
    assert "phase 1 adder subtract: got 12345678 want 12345588 WRONG" in r.stdout        # without the new configuration the old result stays


def test_host_script_framing_selftest():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "fpga", "board_tests_mutability", "mutability_host.py"), "--selftest"], capture_output=True, text=True)
    if not os.path.exists(os.path.join(ROOT, "fpga", "board_tests_mutability", "mutability1.json")):
        pytest.skip("run tools/board_mutability_v1.py first")
    assert r.returncode == 0 and "selftest ok" in r.stdout, r.stdout + r.stderr
