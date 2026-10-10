"""tests/vm/test_unicell_vs_pure_v1.py -- ledger #1036 addendum 59: the CORDIC example as a test bed for the arguments for UniCell against a pure Verilog design.
  streaming: hand pipeline, flex and sub designs all stream 64 items correctly in order; steady rate 1.0 cycle per item except flex, 2.0 (the ack).
  agree:     the standard VM and FlexGrid give the model's answer on 67 inputs and both take 20 ticks, equal to the flex RTL's 20 cycles (and the sub RTL takes 16).
  freeze:    cut the run at every tick, save the cells to a file, reload into a fresh grid, finish: same value, same finish tick (80 cuts per grid mode);
             the same cuts WITHOUT the grid's in-flight words all fail, so the checkpoint file is incomplete without them.
Requires iverilog."""
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import unicell_vs_pure_v1 as u  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def need_iverilog():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"


def test_streaming_rates_and_correctness():
    d = tempfile.mkdtemp(prefix="uvpt_")
    try:
        ff, _ = u.assemble("flex", os.path.join(d, "f"))
        sf, _ = u.assemble("sub", os.path.join(d, "s"))
        want = {"pipe": (1.0, 4), "hs": (1.0, 4), "flex": (2.0, 20), "sub": (1.0, 16)}
        files = {"pipe": u.HAND("cordic_z_pipe_v1.v"), "hs": u.HAND("cordic_z_hs_v1.v"), "flex": ff, "sub": sf}
        for kind, (rate, lat) in want.items():
            r = u.run_stream(kind, files[kind])
            assert r["results_out"] == 64 and r["correct_in_order"] == 64, (kind, r)
            assert r["steady_cycles_per_item"] == rate and r["latency_first_result_after_first_in"] == lat, (kind, r)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_vm_modes_agree_with_the_model_and_the_rtl_latency():
    r = u.agree()
    assert r["inputs"] == 67
    for mode in ("standard_vm_SuperGrid", "FlexGrid"):
        assert r[mode]["wrong"] == 0 and r[mode]["ticks_to_result_values_seen"] == [20], (mode, r[mode])


def test_freeze_save_reload_finish_at_every_tick():
    r = u.freeze()
    for mode in ("standard_vm_SuperGrid", "FlexGrid"):
        m = r[mode]
        assert m["cuts_tested"] == 80 and m["wrong_value"] == 0 and m["wrong_finish_tick"] == 0, (mode, m)
        c = m["same_cuts_but_cells_only_no_pending_words"]
        assert c["tested"] == 80 and c["wrong"] == 80, (mode, c)       # the bite: without the in-flight words the restored run never matches
