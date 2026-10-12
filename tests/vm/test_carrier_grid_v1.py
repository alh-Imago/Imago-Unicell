"""Ledger #1102: the carrier-grid generator (tools/carrier_grid_v1.py) and the finding it produced: in the standard line (the std VM and the carrier's adder) a FIXED constant
feeding an adder pairs with itself (K+K) and the real operand never gets its turn, so the looped CORDIC (fixed constants, built for the flex family) does not run there.
Needs iverilog (the RTL half); the VM half does not."""
import itertools
import os
import shutil
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
for sub in ("tools", "nano", os.path.join("nano", "examples")):
    sys.path.insert(0, os.path.join(ROOT, sub))
import carrier_grid_v1 as G  # noqa: E402
import looped_cordic_v1 as L  # noqa: E402
from icm_v3 import IcmV3Record as Rec  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

needs_iverilog = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")


def mini():
    return [Rec(cell_id="k", row=0, col=0, core="ram", core_config={"downstream_mask": ["E"], "fixed_mode": 1}, addon_config={}, io_name=None, preload_value=1237),
            Rec(cell_id="add", row=0, col=1, core="adder", core_config={"upstream_mask": ["W", "S"], "downstream_mask": ["E"]}, addon_config={}, io_name=None, preload_value=None),
            Rec(cell_id="z", row=1, col=1, core="ram", core_config={"downstream_mask": ["N"], "fixed_mode": 0}, addon_config={}, io_name=None, preload_value=None),
            Rec(cell_id="out", row=0, col=2, core="ram", core_config={"upstream_mask": ["W"], "downstream_mask": ["E"], "fixed_mode": 0}, addon_config={}, io_name=None, preload_value=None)]


def rle(seq):
    return [(k, len(list(g))) for k, g in itertools.groupby(seq)]


def test_std_vm_fixed_constant_pairs_with_itself():
    g = SuperGrid(mini())
    seen = set()
    for t in range(80):
        g.tick()
        if t == 20:
            g.inject(1, 1, 100)
        a = g.cells[(0, 1)]
        seen.add(a.adder_out_buffer)
    assert 2474 in seen and 1337 not in seen          # K+K appears, z+K never does


@needs_iverilog
def test_carrier_rtl_does_the_same_as_the_std_vm():
    r = G.simulate(mini(), "out", 120, loads=[(44, "z", 100)], workdir=tempfile.mkdtemp())
    vals = {v for _, v in r}
    assert 2474 in vals and 1337 not in vals


@needs_iverilog
def test_looped_cordic_on_carriers_is_in_step_with_the_std_vm_and_both_miss_the_model():
    recs = L.build_records()
    g = SuperGrid(recs)
    vm, last = [], False
    for _ in range(120):
        g.tick()
        v = L.entry_value(g)
        if v is not None and not last:
            vm.append(v)
        last = v is not None
    rt = G.simulate(recs, "lp.fb19", 240, workdir=tempfile.mkdtemp())
    a, b = rle(vm), rle([v for _, v in rt])
    assert a[:4] == [(2474, 6), (1236, 3), (-6996, 3), (-6964, a[3][1])] and b[:3] == a[:3] and b[3][0] == -6964   # same values in the same runs; the RTL takes two clocks per VM tick


def test_looped_cordic_in_the_std_vm_does_not_follow_its_model():
    """with z0 injected as in the flex proof, the std VM's feedback entry sees only the K+K stream, never the CORDIC's values."""
    g, _ = L.new_grid(SuperGrid)
    got = [v for _, v in L.run_steps(g, 6)]
    assert got == [2474] * 6 and got != L.model(6)
