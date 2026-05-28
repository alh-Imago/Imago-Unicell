"""tests/conftest.py — ensures repo root is on path for all sub-packages."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
