"""Hex-N core v6 (hold v2: skip-unknown mode, command 0x17 SETHOLDM) in simulation: the earlier hold check still passes on core v6 (strict mode is the default), and the exact-match + hold check runs both modes against the hold rules. Requires iverilog. About 3.5 minutes."""
import os, shutil, subprocess, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pytestmark = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")
def run(script, *extra):
    env = dict(os.environ, HEXN_SIM_CORE="v6", HEXN_SIM_LAT="18")
    return subprocess.run([sys.executable, "tools/hexn_card_run_v5.py", "--sim", script, "docs/hex-n/frontend/example_sensors_script_v1.txt", *extra], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1500)
def test_core_v6_old_hold_check():
    r = run("tools/hexn_hold_card_v1.py", "--per", "4", "--segments", "6"); assert "HOLD CHECK PASS" in r.stdout, r.stdout[-1500:] + r.stderr[-500:]
def test_core_v6_exact_plus_hold_both_modes():
    r = run("tools/hexn_exact_hold_card_v2.py", "--segments", "6"); assert "EXACT+HOLD CHECK PASS" in r.stdout, r.stdout[-1500:] + r.stderr[-500:]
