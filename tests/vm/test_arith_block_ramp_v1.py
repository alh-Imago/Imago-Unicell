"""Ledger #1080: the ramp pipe (arith_blocks_v1.ramp_pipe), Alan's feed-pipe design: a start value goes in at the top; tap k gets start + k * step, in order."""
import json
import os
import shutil
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "..", "nano"), os.path.join(_HERE, "..", "..", "tools")):
    sys.path.insert(0, _p)

import arith_blocks_v1 as AB  # noqa: E402
import flex_rtl_harness_v1 as _h  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

M = 0xFFFFFFFF


def _vm(n, step, start):
    recs, inj, taps = AB.ramp_pipe(n, step)
    g = SuperGrid(recs)
    for (r, c) in inj["start"]:
        g.cells[(r, c)].ram_data_reg = start & M
        g.cells[(r, c)].ram_data_valid = True
    for _ in range(max(300, 10 * len(recs))):
        g.tick()
    return [g.cells[t].ram_data_reg for t in taps]


@pytest.mark.parametrize("n", range(2, 13))
def test_cell_count_and_distinct_squares(n):
    recs, inj, taps = AB.ramp_pipe(n, 1)
    assert len(recs) == AB.ramp_pipe_cell_count(n) == 5 * n - 3
    assert len({(r.row, r.col) for r in recs}) == len(recs) and len({r.cell_id for r in recs}) == len(recs)
    assert len(taps) == n


@pytest.mark.parametrize("n,step,start", [(4, 1, 1), (10, 1, 1), (6, 5, 100), (5, 3, M - 3), (3, 0, 42), (4, M, 10), (7, 1 << 31, 5), (2, 9, 0)])
def test_taps_hold_start_plus_k_times_step(n, step, start):
    assert _vm(n, step, start) == [(start + k * step) & M for k in range(n)]


def test_the_ramp_one_to_ten_in_steps_of_one():
    assert _vm(10, 1, 1) == list(range(1, 11))


def test_refuses_fewer_than_two_taps():
    with pytest.raises(ValueError):
        AB.ramp_pipe(1, 1)


def test_ramp_pipe_as_generated_flex_rtl_streams_in_order():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    n, step = 4, 3
    starts = [1, 100, M - 4, 0, 7]
    recs, inj, taps = AB.ramp_pipe(n, step)
    tmp = tempfile.mkdtemp(prefix="ramp_")
    try:
        d, res = _h.build(tmp, "rp", recs, 32)
        assert res.returncode == 0, (res.stderr or res.stdout)[:500]
        _, got = _h.run_level(d, {"main_ramp_s0": starts}, "plain", 3, settle=600, cycles=60000, width=32)
        assert {k: v for k, v in got.items()} == {f"main_tap{k}": [(s + k * step) & M for s in starts] for k in range(n)}, got
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
