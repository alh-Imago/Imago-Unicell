"""tests/vm/test_freeze_rtl_v1.py -- ledger #1036 addendum 64: freeze, capture, force into a second copy, resume, in the RTL of the flex CORDIC (simulation).
  capture list is complete: every flip-flop bit of the flattened design is in the capture list or is a configuration register (yosys);
  freeze + capture + force-in gives the same values on the same cycles as the uninterrupted copy at every cut that has an output still to come;
  negative controls: leaving out the valid bits, or the data registers, or both, breaks every one of those cuts.
Requires iverilog (and yosys for the coverage check)."""
import os
import shutil
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import freeze_rtl_v1 as f  # noqa: E402


@pytest.fixture(scope="module")
def built():
    assert shutil.which("iverilog") and shutil.which("vvp") and shutil.which("yosys"), "iverilog and yosys are REQUIRED"
    d = tempfile.mkdtemp(prefix="frzt_")
    vvp, ncell, nreg = f.build(d)
    yield d, vvp, ncell, nreg
    shutil.rmtree(d, ignore_errors=True)


def sweep(vvp, cv, cd):
    same = diff = 0
    for cut in range(1, 31):
        a, b, npre = f.run_cut(vvp, cut, cv, cd)
        a_ok, b_ok, t_ok, npost = f.judge(a, b, npre)
        assert a_ok, (cut, a)                       # the frozen copy itself always matches the Python model
        if npost == 0:
            continue
        if b_ok and t_ok:
            same += 1
        else:
            diff += 1
    return same, diff


def test_capture_list_covers_every_flip_flop(built):
    d, vvp, ncell, nreg = built
    nd, nc, nx = f.ff_coverage(d)
    assert ncell == 40 and nx == 0 and nd > 0 and nc > 0


def test_capture_and_force_in_resumes_identically(built):
    same, diff = sweep(built[1], 1, 1)
    assert diff == 0 and same >= 20


@pytest.mark.parametrize("cv,cd", [(0, 1), (1, 0), (0, 0)])
def test_leaving_out_any_part_of_the_list_breaks_it(built, cv, cd):
    same, diff = sweep(built[1], cv, cd)
    assert same == 0 and diff >= 20
