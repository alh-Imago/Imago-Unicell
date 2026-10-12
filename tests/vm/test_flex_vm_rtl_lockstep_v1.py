"""Ledger #1095: the FlexGrid VM and the assembler-generated flex RTL (iverilog) run side by side on the open-ring looped CORDIC; their states are the same register for register whenever the loop value
sits in the feedback relays or a stage's gather relay (94 of 157 ticks), differ by a one-clock skew only in the stage work cells (branch, adders, turn relays) while a value passes through them, and the
two places where the VM keeps state the RTL does not have (adder first operand = a constant, branch reference = a constant) hold exactly the constants."""
import os
import shutil
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))


def test_vm_and_rtl_states_agree_whenever_the_value_sits_in_a_relay():
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        pytest.fail("iverilog missing: this test must not pass by skipping")
    import flex_vm_rtl_lockstep_v1 as X
    r = X.lockstep(158)
    eq = set(r["equal_ticks"])
    assert r["n_compared"] == 157 and r["n_equal"] == 94
    for lo, hi in ((20, 40), (60, 80), (100, 120), (140, 158)):          # the value is in the 20-relay way back: every compared cell agrees
        assert set(range(lo + 1 if lo == 20 else lo, hi + 1)) <= eq
    assert all(c.split(".")[1] in ("branch", "add_neg", "add_pos", "turn_neg", "turn_pos") for c in r["mismatch_cells"])      # no relay (fb*, gather) ever disagrees
    assert r["merge_rr_differs_at_equal_ticks"] == []
    assert r["branch_ref_loaded_in_rtl"] == ["0"] and r["branch_ref_valid_in_vm"] == [True]      # the VM's loaded reference has no RTL register: the reference is the constant source
    assert r["n_adder_waiting_non_constant"] == 0                                                 # the only first operand an adder ever holds in the VM here is a constant (no RTL register either)


def test_a_self_halted_loop_settles_to_one_word_in_the_exit_relay():
    """Ledger #1096 (Alan: the card cannot be stopped at an exact tick, so the cut must be an event inside the design). Stop acknowledging after step 3: after 400 clocks the only non-constant cell
    still holding a word is the exit relay `lp.fb19`, and the word is the model's third value."""
    import subprocess
    import tempfile
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        pytest.fail("iverilog missing: this test must not pass by skipping")
    sys.path.insert(0, os.path.join(ROOT, "nano"))
    import looped_cordic_v1 as L
    d = tempfile.mkdtemp()
    shutil.copy(os.path.join(ROOT, "nano", "examples", "looped_cordic_v1_open.icm-hier.json"), os.path.join(d, "open.icm-hier.json"))
    out = os.path.join(d, "rtl")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", os.path.join(d, "open.icm-hier.json"), "--output", out, "--top", "icm_open_flex"], check=True, capture_output=True)
    vvp = os.path.join(d, "h.vvp")
    srcs = [os.path.join(out, f) for f in os.listdir(out) if f.endswith(".v")] + [os.path.join(ROOT, "sub", "verilog", "tb_looped_cordic_open_flex_halt_v1.v")]
    subprocess.run(["iverilog", "-g2012", "-o", vvp] + srcs, check=True, capture_output=True)
    lines = [l for l in subprocess.run(["vvp", vvp], check=True, capture_output=True, text=True).stdout.splitlines() if l.startswith(("HALT", "BUSY"))]
    assert lines == ["HALT n=2 od=%d ov=1" % L.model(3)[2], "BUSY c_lp_fb19"]


def test_self_stop_by_back_pressure_and_by_freeze_then_release_resumes_exactly():
    """Ledger #1097: the loop closed by a one-word register, stopped by an accumulator (counting steps) feeding a latch (the stop level), the host releasing the latch. Every case: stop at the
    programmed step, release, run on, and every result equals the Python model."""
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        pytest.fail("iverilog missing: this test must not pass by skipping")
    sys.path.insert(0, os.path.join(ROOT, "nano"))
    import tempfile
    import looped_cordic_v1 as L
    import flex_stop_run_v1 as S
    w = tempfile.mkdtemp()
    S.build(w)
    model = L.model(10)

    def go(**kw):
        lines = S.run(w, **kw).splitlines()
        res = [int(l.split()[2]) for l in lines if l.startswith("R ")]
        assert res == model[:len(res)] and len(res) >= 6
        assert not [l for l in lines if l.startswith("TIMEOUT")]
        return [l for l in lines if l.startswith("STOP ")][0], [l.split()[1] for l in lines if l.startswith("BUSY")]
    # back pressure only: the grid runs down to nothing, the word sits in the loop-closing register
    stop, busy = go(mode=1, dly=4, n=3, m=3)
    assert stop == "STOP steps=3 held=%d valid=1 busy=0" % model[2] and busy == []
    # freeze only, the word still in the closing register when the freeze lands
    stop, busy = go(mode=2, dly=4, n=3, m=3)
    assert stop == "STOP steps=3 held=%d valid=1 busy=0" % model[2] and busy == []
    # freeze caught with the word inside the grid: exactly one cell holds it, and which cell depends on when the freeze lands
    seen = set()
    for lag in (0, 12, 25):
        stop, busy = go(mode=2, dly=0, n=3, m=3, lag=lag)
        assert stop == "STOP steps=3 held=%d valid=0 busy=1" % model[2] and len(busy) == 1
        seen.add(busy[0])
    assert len(seen) == 3
    # back pressure alone, stop landing late: the stall reaches the closing register one step later (stop at count 4, not 3), still event-defined and still exact
    stop, busy = go(mode=1, dly=0, n=3, m=3, lag=25)
    assert stop.startswith("STOP steps=4 ")
