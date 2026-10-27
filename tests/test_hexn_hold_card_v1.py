"""Hex-N core v5 (hold counter behind the bank, commands 0x14 SETHOLD and 0x16 RUNHOLD) in simulation: runs tools/hexn_hold_card_v1.py through tools/hexn_card_run_v4.py --sim (core v5, lattice 18, bank v19). Requires iverilog. About 80 seconds."""
import os, shutil, subprocess, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")
def test_hold_behind_bank_core_v5():
    env = dict(os.environ, HEXN_SIM_CORE="v5", HEXN_SIM_LAT="18")
    r = subprocess.run([sys.executable, "tools/hexn_card_run_v4.py", "--sim", "tools/hexn_hold_card_v1.py", "docs/hex-n/frontend/example_sensors_script_v1.txt", "--per", "4", "--segments", "6"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1200)
    assert "HOLD CHECK PASS" in r.stdout, r.stdout[-1500:] + r.stderr[-500:]
