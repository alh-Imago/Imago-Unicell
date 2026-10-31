"""Bit-true check of rtl/hexn_neural_v1.v against the Python integer model (needs iverilog; refuses to pass without it)."""
import os, sys, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_neural_check_v1 as K
def test_neural_rtl_equals_model():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog missing"
    for WB in (14, 10):
        for seed in (1, 2):
            bad, n, _, _ = K.run(WB, seed, 300); assert n == 300 and bad == 0, (WB, seed, bad)
