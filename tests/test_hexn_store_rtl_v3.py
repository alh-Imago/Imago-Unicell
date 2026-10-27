"""RTL of store v5 against its bit-true model: four cases, every command and the whole memory must match. Refuses to pass without iverilog (a skip would look like a pass). A few minutes."""
import os, sys, subprocess, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def test_toolchain_present():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog/vvp missing"
def test_store_v5_rtl_matches_model():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hexn_store_rtl_check_v3.py")], capture_output=True, text=True, timeout=1500)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("mismatches 0") == 4, r.stdout
