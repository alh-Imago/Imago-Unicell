"""tests/vm/test_board_tests_v1.py -- ledger #1023: the on-board test package generator (tools/board_tests_v1.py). Every test wrapper must PASS in simulation (UART text decoded in iverilog), and the checker must
actually be able to FAIL: a wrong expected word, a missing word and a timeout each give res=F. Place-and-route is not run here (the tool does that when it writes the package). Requires iverilog and FAILS without it."""
import os
import re
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import board_tests_v1 as bt  # noqa: E402


@pytest.fixture(scope="module")
def out():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="bt_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("t", bt.TESTS, ids=[t[0] for t in bt.TESTS])
def test_every_test_passes_in_simulation_with_the_uart_line_decoded(t, out):
    name, desc, mk, streams, gaps, stalls = t
    r = bt.build_one(name, desc, mk, streams, gaps, stalls, out, pnr=False)
    assert re.search(r"res=P n=([0-9A-F]{4}) e=\1 bad=0000 to=0", r["sim_line"] + " "), r["sim_line"]
    assert len(r["expected"]) >= 1


def _sim_with(out, name, exp, streams, mk):
    import json, subprocess
    work = os.path.join(out, "neg_" + name)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    recs = mk()
    bt.IcmV3File(name=name, records=recs).save(os.path.join(work, name + ".icm"))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", os.path.join(work, name + ".icm"), "--output", os.path.join(work, "gen")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    rec = json.load(open(os.path.join(work, "gen", "ASSEMBLY.json")))
    srcs = [os.path.join(work, "gen", f) for f in rec["files"] if f.endswith(".v")]
    open(os.path.join(work, "board_uart_tx.v"), "w").write(bt.UART_V)
    open(os.path.join(work, f"board_top_{name}.v"), "w").write(bt.wrapper(name, rec["top"], streams, "O", exp, False, False, bt.CPB, bt.SETTLE, bt.TIMEOUT))
    sim = bt.simulate(work, name, [os.path.join(work, "board_uart_tx.v"), os.path.join(work, f"board_top_{name}.v")] + srcs)
    return next((l for l in sim.splitlines() if l.startswith("UCT")), sim[-200:])


def test_the_checker_fails_on_a_wrong_missing_or_extra_word(out):
    name, desc, mk, streams, gaps, stalls = bt.TESTS[0]
    exp = bt.expected(mk(), streams)
    assert " res=P " in _sim_with(out, name, exp, streams, mk) + " "
    wrong = list(exp)
    wrong[3] ^= 1
    assert " res=F " in _sim_with(out, name, wrong, streams, mk) + " "
    assert " res=F " in _sim_with(out, name, exp + [123], streams, mk) + " "        # one more expected word than ever arrives: timeout
    assert " res=F " in _sim_with(out, name, exp[:-1], streams, mk) + " "           # one word too few expected: the extra arrival is a failure


def test_the_expected_words_are_independent_of_the_simulation():
    """the expected words come from FlexGrid (the VM), not from running the wrapper: spot-check three by hand."""
    by = {t[0]: t for t in bt.TESTS}
    t = by["adder_stream"]
    assert bt.expected(t[2](), t[3])[:4] == [11, 22, 33, 0]               # 1+10, 2+20, 3+30, 0xFFFFFFFF+1 wraps to 0
    t = by["ram_hold"]
    assert bt.expected(t[2](), t[3]) == [8, 9, 10, 11, 12, 13]
    t = by["priority_strict"]
    assert bt.expected(t[2](), t[3])[:6] == [21, 22, 23, 24, 25, 26]      # west (rank 0) is served first, all six
