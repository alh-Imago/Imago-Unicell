"""tests/vm/test_freeze_pure_v1.py -- ledger #1036 addendum 65: freeze + scan chain on the PURE Verilog CORDIC (no cells).
  both hand designs (no back-pressure, and valid/ack): freeze at every cut with an output still to come, shift the 132-bit state out of A into a never-fed B,
  release: B gives the same values on the same cycles as A and A matches the model; loading zeros instead breaks every one of those cuts;
  the scan chain adds look-up tables but no flip-flops (yosys, system tool).
Requires iverilog and yosys."""
import os
import shutil
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import freeze_pure_v1 as p  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def need_tools():
    assert shutil.which("iverilog") and shutil.which("vvp") and shutil.which("yosys"), "iverilog and yosys are REQUIRED"


@pytest.mark.parametrize("kind", ["pipe_frz", "hs_frz"])
def test_scan_out_and_in_resumes_identically(kind):
    d = tempfile.mkdtemp(prefix="frzpt_")
    try:
        vvp = p.build(d, kind)
        same, diff = p.sweep(vvp, 1)
        assert diff == 0 and same >= 5
        same0, diff0 = p.sweep(vvp, 0)
        assert same0 == 0 and diff0 >= 5
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_scan_chain_costs_luts_not_flip_flops():
    B = lambda n: [os.path.join(p.BASE, n + ".v")]
    for plain, frz in (("cordic_z_pipe_v1", "cordic_z_pipe_frz_v1"), ("cordic_z_hs_v1", "cordic_z_hs_frz_v1")):
        a, b = p.cb.synth_counts(B(plain), plain), p.cb.synth_counts(B(frz), frz)
        assert a["DFF"] == b["DFF"] == 132 and b["LUT"] > a["LUT"]
