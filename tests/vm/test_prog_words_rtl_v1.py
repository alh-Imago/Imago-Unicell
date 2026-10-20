"""Ledger #1305: the VM's word-programming tables against the real RTL by simulation (tools/prog_word_rtl_check_v1.py): adder, mul (v5), div, priority, merge, 120 random words each plus every id once.
Needs iverilog (the repository's usual rule: without it a suite that needs it fails rather than skips, see tools/quick_check_v1.py)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_vm_word_programming_is_identical_to_the_rtl():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "prog_word_rtl_check_v1.py"), "--writes", "120"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("IDENTICAL") == 5, r.stdout
