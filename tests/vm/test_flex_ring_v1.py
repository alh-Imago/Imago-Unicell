"""tests/vm/test_flex_ring_v1.py -- ledger #1109: closed rings (genuine feedback) in generated FLEX RTL, `project_assemble_v1.py -s flex --allow-rings --icm ...`.

The looped CORDIC is built closed (no wrapper register; `nano/examples/looped_cordic_v1_closed_flex.icm-hier.json`, join adders). The generated hardware gets a host port for the entry and an
observation port `result`; the host injects z0 once and acks every result. Checked against the independent model (`looped_cordic_v1.model`): from z0, and from the two saved words used in
#1105 (the VM's step-300 word 8138 and the Tang's step-600 word -5748) all the way to step 1000 (7170). Also the refusals and the negative control. Needs iverilog (fails loudly without it, #965)."""
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
TB = os.path.join(ROOT, "sub", "verilog", "tb_looped_cordic_closed_flex_v1.v")
MAN = os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json")
ASM = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]


@pytest.fixture(scope="module")
def built():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"
    out = tempfile.mkdtemp()
    r = subprocess.run(ASM + ["-s", "flex", "--allow-rings", "--icm", ICM, "--man", MAN, "--output", out, "--top", "ring_flex"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]
    return out


def run(built, z0, steps, ack="1'b1", maxcyc=60000):
    exe = os.path.join(built, "t_%d_%d_%s.vvp" % (z0 & 0xFFFFFFFF, steps, "a" if ack == "1'b1" else "n"))
    srcs = [os.path.join(built, f) for f in os.listdir(built) if f.endswith(".v")]
    c = subprocess.run(["iverilog", "-g2012", "-DTOP=ring_flex", f"-DZ0=32'd{z0 & 0xFFFFFFFF}", f"-DNSTEPS={steps}", f"-DMAXCYC={maxcyc}", f"-DACK={ack}", "-o", exe, TB] + srcs, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[-600:]
    out = subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=900).stdout
    return [int(l.split()[2]) for l in out.splitlines() if l.startswith("R ")], out


def test_closed_ring_from_z0_equals_the_model(built):
    vals, _ = run(built, L.Z0, 40)
    assert vals == L.model(40)


@pytest.mark.parametrize("start,word", [(300, 8138), (600, -5748)])
def test_closed_ring_from_a_saved_word_reaches_step_1000(built, start, word):
    assert L.model(start)[start - 1] == word                      # the word really is the model's value at that step
    vals, _ = run(built, word, 1000 - start)
    assert vals == L.model(1000)[start:1000] and vals[-1] == 7170


def test_a_host_that_never_acks_stalls_the_ring(built):
    vals, out = run(built, L.Z0, 5, ack="1'b0", maxcyc=3000)
    assert vals == [] and "TIMEOUT n=0" in out                    # the first result is offered and held; with no ack the ring waits for the host


def test_without_the_flag_a_cycle_is_still_refused_with_its_reason():
    r = subprocess.run(ASM + ["-s", "flex", "--icm", ICM, "--man", MAN, "--output", tempfile.mkdtemp()], capture_output=True, text=True)
    assert r.returncode != 0 and "has a cycle" in r.stderr


def test_sub_does_not_accept_rings_yet():
    r = subprocess.run(ASM + ["-s", "sub", "--allow-rings", "--icm", ICM, "--output", tempfile.mkdtemp()], capture_output=True, text=True)
    assert r.returncode != 0 and "flex only" in r.stderr


def test_the_flag_changes_nothing_for_an_acyclic_design():
    src = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence.icm-hier.json")
    outs = []
    for extra in ([], ["--allow-rings"]):
        d = tempfile.mkdtemp()
        r = subprocess.run(ASM + ["-s", "flex", "--icm", src, "--man", MAN, "--output", d, "--top", "same"] + extra, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-400:]
        outs.append(open(os.path.join(d, "same.v")).read())
    assert outs[0] == outs[1]
