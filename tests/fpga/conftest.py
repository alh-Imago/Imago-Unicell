"""tests/fpga/conftest.py — FPGA test suite path setup."""
import sys, os
repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo)
sys.path.insert(0, os.path.join(repo, 'fpga'))
