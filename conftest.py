"""
conftest.py — pytest root configuration for Imago UniCell

Adds the repo root to sys.path so all test files can import VM modules
directly (from fp_tiles import ..., from controller import ..., etc.)
without needing to install the package first.

Works for both:
  pytest                         (discovers all tests/)
  pytest tests/vm/test_array.py  (explicit path)
  python3 tests/vm/test_fp_tiles.py  (script-style)
"""
import sys
import os

# Ensure repo root is first on sys.path
repo_root = os.path.dirname(os.path.abspath(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
