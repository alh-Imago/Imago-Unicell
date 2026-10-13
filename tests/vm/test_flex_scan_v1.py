"""Ledger #1145: in-flight capture / restore through the scan chain of the flex looped CORDIC (tools/flex_scan_net_v1.py, wrapper v3). A reduced sweep
(freeze lags x feed delays) must pass, and each deliberate break (zeros shifted in, closing word not restored, one stream bit flipped, one chain link cut) must be caught."""
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
TOOL = os.path.join(ROOT, "tools", "flex_scan_check_v1.py")


def run(*args):
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        pytest.fail("iverilog missing: this test must not pass by skipping")
    return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, timeout=1500)


def test_scan_restore_matches_continuing_original():
    r = run("--lags", "0-3,12", "--k1", "3,4", "--dly", "0-4")
    assert r.returncode == 0 and "SCAN CHECK PASS" in r.stdout and "MISMATCH" not in r.stdout and "DIFFERENT" not in r.stdout, r.stdout[-1500:] + r.stderr[-500:]
    assert r.stdout.count("PATTERN") == 6


@pytest.mark.parametrize("m", ["zeros", "noword", "flip", "chain"])
def test_breaks_are_caught(m):
    r = run("--mutant", m, "--lags", "0-3", "--k1", "3", "--dly", "0-4")
    assert r.returncode == 0 and ("MUTANT %s -> caught" % m) in r.stdout, r.stdout[-1500:] + r.stderr[-500:]
