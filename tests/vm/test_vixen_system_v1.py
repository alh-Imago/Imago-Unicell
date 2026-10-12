"""tests/vm/test_vixen_system_v1.py -- ledger #1105: VIXeN at system level. The ICM key `join_mode` (adder / mul / div), the std VM honouring it, and the looped CORDIC with join adders:
the std VM and the carrier RTL grid (unicell_vixen_v1) both follow the independent model, which the old carrier could not do (#1102). RTL half needs iverilog."""
import os
import shutil
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
for sub in ("tools", "nano", os.path.join("nano", "examples")):
    sys.path.insert(0, os.path.join(ROOT, sub))
import carrier_grid_v2 as G  # noqa: E402
import looped_cordic_v1 as L  # noqa: E402
from icm_v3 import IcmV3Record as Rec  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

needs_iverilog = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")


def mini(join):
    cc = {"upstream_mask": ["W", "S"], "downstream_mask": ["E"]}
    if join:
        cc["join_mode"] = 1
    return [Rec(cell_id="k", row=0, col=0, core="ram", core_config={"downstream_mask": ["E"], "fixed_mode": 1}, addon_config={}, io_name=None, preload_value=1237),
            Rec(cell_id="add", row=0, col=1, core="adder", core_config=cc, addon_config={}, io_name=None, preload_value=None),
            Rec(cell_id="z", row=1, col=1, core="ram", core_config={"downstream_mask": ["N"], "fixed_mode": 0}, addon_config={}, io_name=None, preload_value=None),
            Rec(cell_id="out", row=0, col=2, core="ram", core_config={"upstream_mask": ["W"], "downstream_mask": ["E"], "fixed_mode": 0}, addon_config={}, io_name=None, preload_value=None)]


def _seen(join):
    g = SuperGrid(mini(join))
    seen = set()
    for t in range(80):
        g.tick()
        if t == 20:
            g.inject(1, 1, 100)
        seen.add(g.cells[(0, 1)].adder_out_buffer)
    return seen


def test_vm_join_adds_the_real_operand_and_never_pairs_the_constant_with_itself():
    assert 2474 in _seen(False) and 1337 not in _seen(False)       # standard capture: K+K
    j = _seen(True)
    assert 1337 in j and 2474 not in j                              # join: z + K only


def test_vm_looped_cordic_with_join_adders_follows_the_model():
    g, _ = L.new_grid(SuperGrid, join=True)
    assert [v for _, v in L.run_steps(g, 40)] == L.model(40)


@needs_iverilog
def test_vixen_carrier_grid_runs_the_full_looped_cordic_and_follows_the_model():
    recs = L.build_records(join=True)
    inp = next(r for r in recs if r.io_name == "z_input")
    rt = G.simulate(recs, "lp.fb19", 900, loads=[(40, inp.cell_id, L.Z0)], workdir=tempfile.mkdtemp())
    vals = [v for _, v in rt]
    assert len(vals) >= 9 and vals == L.model(len(vals))


@needs_iverilog
def test_old_v1d_carrier_still_cannot_run_it():
    """the unchanged v1d carrier ignores join_mode (the bit is reserved there) and keeps the K+K junk -- VIXeN is what fixes it."""
    recs = L.build_records(join=True)
    inp = next(r for r in recs if r.io_name == "z_input")
    rt = G.simulate(recs, "lp.fb19", 500, loads=[(40, inp.cell_id, L.Z0)], workdir=tempfile.mkdtemp(), carrier="v1d")
    vals = [v for _, v in rt]
    assert vals[:3] != L.model(3)


def _latch_only_records():
    import json
    recs = L.build_records(join=True)
    d = tempfile.mkdtemp()
    G.generate(recs, d, "grid", "lp.fb19")
    return G.records_from_latch(os.path.join(d, "GRID.json"))


def _run_vm(recs, z0, n):
    g = SuperGrid(recs)
    for _ in range(L.SETTLE_TICKS):
        g.tick()
    inp = next(r for r in recs if r.io_name == "z_input")
    g.inject(inp.row, inp.col, z0 & 0xFFFFFFFF)
    return [v for _, v in L.run_steps(g, n)]


def test_a_vm_built_from_the_carrier_latch_words_alone_runs_the_cordic_and_takes_a_passed_back_word():
    """card -> VM: records decoded from the 160-bit VIX_LATCH words only; the step-1000 word (7170, found by the RTL run in #1105) continues the model from step 1001."""
    recs = _latch_only_records()
    m = L.model(1100)
    assert _run_vm(recs, L.Z0, 40) == m[:40]
    assert _run_vm(recs, m[999], 40) == m[1000:1040]
