"""tests/vm/test_sub_ring_v1.py -- ledger #1111: closed rings in generated SUB RTL (fixed 1-clock cells, no ack, nothing can hold a word back), `project_assemble_v1.py -s sub --allow-rings --ring-steps N`.

Alan's design: the ring completes ONE lap, HALTS at the measure point (a flowing ram that holds the word), and is REFIRED; so the ring's length / timing never has to be known. Control = sub cells only
(latch: a word is held; accumulator: laps counted; latch: stop level). Checked against the independent model `looped_cordic_v1.model`: from z0, from the two saved words (8138 at step 300, -5748 at step 600)
to step 1000 = 7170, stop after exactly N laps, the Nth word held, release continues, the zero-lag negative control, refusals. Needs iverilog (fails loudly without it, #965)."""
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
for sub in ("tools", "nano", os.path.join("nano", "examples")):
    sys.path.insert(0, os.path.join(ROOT, sub))
import looped_cordic_v1 as L  # noqa: E402

ICM = os.path.join(ROOT, "nano", "examples", "looped_cordic_v1_closed_flex.icm-hier.json")
TB = os.path.join(ROOT, "sub", "verilog", "tb_looped_cordic_closed_sub_v1.v")
ASM = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
_CACHE = {}


def build(n):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"
    if n not in _CACHE:
        out = tempfile.mkdtemp()
        r = subprocess.run(ASM + ["-s", "sub", "--allow-rings", "--ring-steps", str(n), "--icm", ICM, "--output", out, "--top", "ring_sub"], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-600:]
        _CACHE[n] = out
    return _CACHE[n]


def run(d, z0, steps, release=False, maxcyc=80000):
    exe = os.path.join(d, "t_%d_%d_%d.vvp" % (z0 & 0xFFFFFFFF, steps, release))
    srcs = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".v")]
    c = subprocess.run(["iverilog", "-g2012", "-DTOP=ring_sub", f"-DZ0=32'd{z0 & 0xFFFFFFFF}", f"-DNSTEPS={steps}", f"-DMAXCYC={maxcyc}"] + (["-DRELEASE"] if release else []) + ["-o", exe, TB] + srcs,
                       capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[-600:]
    out = subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=900).stdout
    return [int(l.split()[2]) for l in out.splitlines() if l.startswith("R ")], out


def stop_n(out):
    for l in out.splitlines():
        if l.startswith("S "):
            return int(l.split()[2][2:])
    return None


def test_sub_ring_from_z0_equals_the_model():
    vals, _ = run(build(1 << 15), L.Z0, 40)
    assert vals == L.model(40)


@pytest.mark.parametrize("start,word", [(300, 8138), (600, -5748)])
def test_sub_ring_from_a_saved_word_reaches_step_1000(start, word):
    vals, _ = run(build(1 << 15), word, 1000 - start)
    assert vals == L.model(1000)[start:1000] and vals[-1] == 7170


@pytest.mark.parametrize("n", [1, 2, 3, 10, 20])
def test_stops_after_exactly_n_laps_and_holds_the_nth(n):
    vals, out = run(build(n), L.Z0, n + 3, maxcyc=4000)
    assert vals == L.model(n) and stop_n(out) == n
    assert "TIMEOUT n=%d stopped=1 held=1 word=%d" % (n, L.model(n)[-1]) in out     # stopped, still holding, the held word IS the Nth model value


def test_release_continues_from_the_same_state():
    vals, out = run(build(10), L.Z0, 25, release=True, maxcyc=8000)
    assert vals == L.model(25) and stop_n(out) == 10


@pytest.mark.parametrize("start,word", [(300, 8138), (600, -5748)])
def test_stop_and_release_from_a_saved_word_still_reach_step_1000(start, word):
    vals, _ = run(build(50), word, 1000 - start, release=True)
    assert vals == L.model(1000)[start:1000] and vals[-1] == 7170


def test_the_ring_is_physically_broken_without_a_refire():
    # a one-lap control (N=1): after the first lap the word sits in the measure point and NOTHING moves until release -- 4000 clocks later still exactly one result
    vals, out = run(build(1), L.Z0, 4, maxcyc=4000)
    assert vals == L.model(1) and "TIMEOUT n=1 stopped=1 held=1" in out


def test_control_negative_zero_lag_overruns():
    d = build(10)
    bad = tempfile.mkdtemp()
    for f in os.listdir(d):
        if f.endswith(".v"):
            shutil.copy(os.path.join(d, f), bad)
    t = open(os.path.join(bad, "ring_sub.v")).read()
    assert "localparam RING_LAG = 1;" in t
    open(os.path.join(bad, "ring_sub.v"), "w").write(t.replace("localparam RING_LAG = 1;", "localparam RING_LAG = 0;"))
    vals, _ = run(bad, L.Z0, 13, maxcyc=4000)
    assert len(vals) == 11                                           # lag 0: the refire beats the stop by one clock, one lap too many


def test_a_sub_ring_without_a_control_is_refused():
    r = subprocess.run(ASM + ["-s", "sub", "--allow-rings", "--icm", ICM, "--output", tempfile.mkdtemp(), "--top", "x"], capture_output=True, text=True)
    assert r.returncode != 0 and "no control mechanism" in r.stderr


def test_without_the_flag_a_cycle_is_still_refused():
    r = subprocess.run(ASM + ["-s", "sub", "--icm", ICM, "--output", tempfile.mkdtemp()], capture_output=True, text=True)
    assert r.returncode != 0 and "has a cycle" in r.stderr
