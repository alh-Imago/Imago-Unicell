"""tests/vm/test_mixed_div_v1.py -- ledger #1171: the DIVISION core in a standard / carrier region of a mixed design (flexsub_mixed_v3, standalone_grid_v2, carrier_grid_v4).
Built through the real assembler command; run with the board wrapper in iverilog (random exit stalls): every word equals 1000000 // (x + 1000) + 5 (one word divides by zero -> all ones).
Bite: a wrong expected word makes the wrapper report FAIL. v2 of the mixed generator is untouched and still refuses a div region. Requires iverilog."""
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import board_loops_v1 as BL  # noqa: E402
import board_mixed_div_v1 as BD  # noqa: E402


@pytest.fixture(scope="module")
def work():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="mixdiv_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("name,what,icm", BD.CASES)
def test_divider_between_two_flex_regions_in_simulation(work, name, what, icm):
    top, files = BL.assemble(["-s", "flex", "--icm", os.path.join(ROOT, "nano", "examples", icm), "--top", "mix"], os.path.join(work, "g_" + name))
    out = os.path.join(work, "o_" + name)
    os.makedirs(out)
    r = BL.build(name, what, "stream", top, files, None, BD.expected(BD.XS), BD.XS, out, False, 1, work)
    assert " res=P " in r["sim_line"] + " " and "n=0009" in r["sim_line"] and "bad=0000" in r["sim_line"]


def test_the_expected_words_include_the_division_by_zero_rule():
    e = BD.expected(BD.XS)
    assert e[0] == 1000000 // 1005 + 5 and e[-1] == (0xFFFFFFFF + 5) & 0xFFFFFFFF


def test_bite_a_wrong_expected_word_fails(work):
    name, what, icm = BD.CASES[0]
    top, files = BL.assemble(["-s", "flex", "--icm", os.path.join(ROOT, "nano", "examples", icm), "--top", "mix"], os.path.join(work, "g_bite"))
    bad = BD.expected(BD.XS)
    bad[3] ^= 1
    out = os.path.join(work, "o_bite")
    os.makedirs(out)
    with pytest.raises(RuntimeError):
        BL.build("bite_div", what, "stream", top, files, None, bad, BD.XS, out, False, 1, work)


def test_v2_still_refuses_a_div_region():
    import flexsub_mixed_v2 as v2
    import flexsub_mixed_v3 as v3
    assert "div" not in v2.STD_CORES and "div" in v3.STD_CORES
