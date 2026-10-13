"""Ledger #1124: a small designed-from-ICM circuit (4-input sum tree with an exit cell) tested in the VM, on the standalone-shell RTL, on the trimmed-carrier RTL, and through the board wrapper."""
import os, sys, shutil, tempfile, subprocess
import pytest
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
for p in ("tools", "nano", os.path.join("nano", "examples"), "."):
    sys.path.insert(0, os.path.join(ROOT, p))
from hierarchical_icm_prototype_loader import load_hierarchical, flatten
needs = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
ICM = os.path.join(ROOT, "nano", "examples", "reduction_tree4_exit_v1.icm-hier.json")
VECS = [(1, 2, 3, 4), (100, -50, 7, 0), (-1, -2, -3, -4), (1000, 2000, 3000, 4000), (123456, -654321, 42, 17)]


def _recs():
    recs = flatten(load_hierarchical(ICM))[0]
    for r in recs:
        if r.core == "adder":
            r.core_config["join_mode"] = 1
    return recs, {r.io_name: r for r in recs if r.io_name}


def test_vm_sums():
    from unicell_super_automaton_v1 import SuperGrid
    recs, io = _recs()
    g = SuperGrid(recs)
    for _ in range(10):
        g.tick()
    o = io["output"]
    got = []
    for v in VECS:
        for k, x in enumerate(v):
            g.inject(io["input_%d" % k].row, io["input_%d" % k].col, x & 0xFFFFFFFF)
        for _ in range(200):
            g.tick()
        c = g.cells[(o.row, o.col)]                       # the exit ram keeps offering its last sum: read it settled
        got.append(c.ram_data_reg - (1 << 32) if c.ram_data_reg & 0x80000000 else c.ram_data_reg)
    assert got == [sum(v) for v in VECS]


def _rtl(fam):
    import standalone_grid_v1 as S, carrier_grid_v3 as G
    recs, io = _recs()
    loads, t = [], 60
    for v in VECS:
        for k, x in enumerate(v):
            loads.append((t + 4 * k, io["input_%d" % k].cell_id, x))
        t += 300
    wd = tempfile.mkdtemp()
    if fam == "std":
        got = S.simulate(recs, io["output"].cell_id, t + 300, loads=loads, workdir=wd)
    else:
        got = G.simulate(recs, io["output"].cell_id, t + 300, loads=loads, workdir=wd, keep=("adder", "ram"))
    return [v for _, v in got]


@needs
@pytest.mark.parametrize("fam", ["std", "carrier"])
def test_rtl_sums_equal_the_arithmetic(fam):
    assert _rtl(fam) == [sum(v) for v in VECS]


def test_cli_with_tap_io():
    out = tempfile.mkdtemp()
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "std", "--icm", ICM, "--tap-io", "output", "--output", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "std", "--icm", ICM, "--output", out], capture_output=True, text=True)
    assert r.returncode == 1 and "result" in r.stderr
