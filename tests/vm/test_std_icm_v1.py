"""Ledger #1123: the ICM drives the standard line (-s std standalone shells, -s carrier VIXeN trimmed), ring control generated into the map."""
import os, sys, json, shutil, subprocess, tempfile
import pytest
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
for p in ("tools", "nano", os.path.join("nano", "examples"), "."):
    sys.path.insert(0, os.path.join(ROOT, p))
import std_ring_control_v1 as C
import std_icm_generate_v1 as SG
import looped_cordic_v1 as L
from hierarchical_icm_prototype_loader import load_hierarchical, flatten

needs_iverilog = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
ICM = os.path.join(ROOT, "nano", "examples", "looped_cordic_v1_closed_flex.icm-hier.json")
OPEN = os.path.join(ROOT, "nano", "examples", "looped_cordic_v1_open.icm-hier.json")
ASM = os.path.join(ROOT, "tools", "project_assemble_v1.py")


def _recs(n):
    return C.insert_ring_control(flatten(load_hierarchical(ICM))[0], n)


def test_offset_and_reference_pinned():
    _, info = _recs(20)
    assert (info["offset"], info["reference"]) == (8, 12)


def test_too_few_steps_refused():
    with pytest.raises(C.RingError):
        _recs(8)


@needs_iverilog
@pytest.mark.parametrize("fam", ["std", "carrier"])
def test_rtl_exactly_n_then_one_more_on_release(fam):
    import standalone_grid_v1 as S, carrier_grid_v3 as G
    n = 12
    recs, _ = _recs(n)
    inp = next(r for r in recs if r.io_name == "z_input")
    res = next(r for r in recs if r.io_name == "result")
    rel = next(r for r in recs if r.io_name == "ring_release")
    loads = [(40, inp.cell_id, L.Z0), (9000, rel.cell_id, 0)]
    wd = tempfile.mkdtemp()
    if fam == "std":
        got = S.simulate(recs, res.cell_id, 12000, loads=loads, workdir=wd)
    else:
        got = G.simulate(recs, res.cell_id, 12000, loads=loads, workdir=wd, keep=("ram", "adder", "branch", "accum"))
    vals = [v for _, v in got]
    assert len(vals) == n + 1
    assert vals == L.model(n + 1)[:n + 1]
    assert all(t < 9000 for t, _ in got[:n]) and got[n][0] > 9000


@pytest.mark.parametrize("fam", ["std", "carrier"])
def test_cli_generates_and_maps_io(fam):
    out = tempfile.mkdtemp()
    r = subprocess.run([sys.executable, ASM, "-s", fam, "--icm", ICM, "--allow-rings", "--ring-steps", "20", "--output", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    meta = json.load(open(os.path.join(out, "GRID.json")))
    for k in ("z_input", "result", "ring_release", "ring_stopped"):
        assert k in meta["io"]
    assert meta["ring"]["reference"] == 12
    if fam == "carrier":
        assert set(meta["keep"]) == {"accum", "adder", "branch", "ram"}


def test_cli_refuses_ring_without_control_and_wrong_use():
    out = tempfile.mkdtemp()
    r = subprocess.run([sys.executable, ASM, "-s", "std", "--icm", ICM, "--output", out], capture_output=True, text=True)
    assert r.returncode == 1 and "ring" in r.stderr
    r = subprocess.run([sys.executable, ASM, "-s", "std", "--cells", "4", "--output", out], capture_output=True, text=True)
    assert r.returncode != 0 and "ICM" in r.stderr
    with pytest.raises(ValueError):
        SG.generate(OPEN, out, "std", rings=True, ring_steps=5)       # no ring in the open design
    with pytest.raises(ValueError):
        SG.generate(OPEN, out, "std", ring_steps=5)


@pytest.mark.parametrize("fam", ["std", "carrier"])
def test_open_design_needs_no_control(fam):
    r = SG.generate(OPEN, tempfile.mkdtemp(), fam)
    assert r["ring"] is None and "result" in r["io"]
