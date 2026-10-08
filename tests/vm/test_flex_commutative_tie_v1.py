"""tests/vm/test_flex_commutative_tie_v1.py -- ledger #1036: the flex generator accepts two operands reaching a COMMUTATIVE pair core on the same tick (mul, add), and still refuses it for subtract.
X and Y sit the same distance from M, so the pair is a tie. The generated RTL (iverilog) must give the plain arithmetic result. Requires iverilog."""
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flex_rtl_harness_v1 as h  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402

ram = h.ram
M32 = 0xFFFFFFFF


def tie(core, **cfg):
    m = IcmV3Record(cell_id="M", row=1, col=1, core=core, core_config=dict({"upstream_mask": ["n", "w"], "downstream_mask": ["e"]}, **cfg))
    return [ram("X", 0, 1, [], ["s"]), ram("Y", 1, 0, [], ["e"]), m, ram("E", 1, 2, ["w"], [])]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="fgtie_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


PAIRS = [(5, 3), (M32, 1), (0, 0), (0x12345678, 0x9ABCDEF0), (7, 7)]


@pytest.mark.parametrize("core,fn", [("adder", lambda a, b: (a + b) & M32), ("mul", lambda a, b: (a * b) & M32)])
@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_a_same_tick_pair_on_a_commutative_core_gives_the_arithmetic_result(tmp, core, fn, mode):
    d, r = h.build(tmp, f"tie_{core}_{mode}", tie(core))
    assert r.returncode == 0, r.stderr[:500]
    _, got = h.run_level(d, {"X": [a for a, _ in PAIRS], "Y": [b for _, b in PAIRS]}, mode, 3, settle=300)
    assert got["E"] == [fn(a, b) for a, b in PAIRS]


def test_a_same_tick_pair_on_a_subtract_is_still_refused(tmp):
    d, r = h.build(tmp, "tie_sub", tie("adder", subtract_mode=1))
    assert r.returncode != 0 and "no arbiter" in (r.stderr + r.stdout)
