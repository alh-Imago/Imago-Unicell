"""Ledger #1098: the save/load board kit: the host script's framing against its software model of the card, and the simulated PC running the four scenarios against the real design
with a deliberate break caught."""
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
KIT = os.path.join(ROOT, "fpga", "board_tests_saveload")


def test_host_selftest_and_committed_state_files():
    r = subprocess.run([sys.executable, os.path.join(KIT, "saveload_host_v2.py"), "--selftest"], capture_output=True, text=True)
    assert r.returncode == 0 and "selftest ok" in r.stdout, r.stdout + r.stderr
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.join(ROOT, "nano"))
    import json
    import looped_cordic_v1 as L
    import flex_tang_bridge_v1 as B
    st = json.load(open(os.path.join(KIT, "tang_state_step300.json")))
    assert st["step"] == 300 and st["word"] == L.model(300)[299] & 0xFFFFFFFF
    d = tempfile.mkdtemp()
    out = os.path.join(d, "s.json")
    B.make_state(os.path.join(KIT, "vm_save_step300.json"), out)
    assert json.load(open(out)) == st
    sys.path.insert(0, KIT)
    import saveload_host as H
    assert H.model(30) == L.model(30)          # the host's own copy of the loop definition equals the project's


def test_simulated_pc_passes_all_four_scenarios_and_catches_a_break():
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        pytest.fail("iverilog missing: this test must not pass by skipping")
    env = dict(os.environ, SL_TMO_NS="400000000")
    out = tempfile.mkdtemp()
    ok = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "board_saveload_v2.py"), "--no-pnr", "--out", out], capture_output=True, text=True, env=env, timeout=900)
    assert ok.returncode == 0 and "SAVELOAD PASS" in ok.stdout and "WRONG" not in ok.stdout, ok.stdout[-1500:] + ok.stderr[-500:]
    bad = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "board_saveload_v2.py"), "--no-pnr", "--mutant", "wrongload", "--out", out], capture_output=True, text=True, env=env, timeout=900)
    assert bad.returncode == 0 and "MUTANT wrongload -> caught" in bad.stdout
