"""tests/vm/test_walker_card_v1.py -- ledger #1286: the Walker's reading of a card over JTAG, tested against the runner's SIMULATION and a synthetic card read.
1. a folder made by project_assemble_v4 has design_map.json and the design fingerprint in design.json; the testbench (which checks the fingerprint word on every run) PASSES.
2. walker_card_v1 on a read-back with the right fingerprint says SAME DESIGN and prints neighbours; with a wrong fingerprint it says IS NOT and exits 1; with a wrong magic it exits 1.
Needs iverilog (fails without it). NOT a card run."""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICM = os.path.join(ROOT, "nano", "examples", "card_tested", "priority_weighted.icm.json")
MAN = os.path.join(ROOT, "docs", "man", "kintex7-ypcb00338.man.json")


def _make(t):
    out = os.path.join(t, "f")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v4.py"), "-s", "flex", "--icm", ICM, "--man", MAN, "--output", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    return out, r.stdout


def _log(folder, fp=None, magic=0x52554E31):
    d, m = json.load(open(folder + "/design.json")), json.load(open(folder + "/design_map.json"))
    lay = d["layout"]
    w = [0] * d["nw"]
    w[0], w[1], w[3] = magic, 99, 1
    w[2] = (1 << 30) | (len(d["entries"]) << 16) | (d["depth"] << 8) | len(d["exits"])
    w[lay["ebuf"]] = int(fp or m["fingerprint"], 16)
    p = folder + "/walk.log"
    open(p, "w").write("SNAP result " + " ".join("%08x" % x for x in w) + "\n")
    return p


def _walk(folder, log):
    return subprocess.run([sys.executable, os.path.join(ROOT, "tools", "walker_card_v1.py"), folder, log], capture_output=True, text=True)


def test_folder_has_map_and_fingerprint_and_simulation_passes():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    with tempfile.TemporaryDirectory() as t:
        out, stdout = _make(t)
        assert "Simulation against the VM: PASS" in stdout
        d, m = json.load(open(out + "/design.json")), json.load(open(out + "/design_map.json"))
        assert d["fingerprint"] == m["fingerprint"] and len(m["fingerprint"]) == 8
        assert "design fingerprint" in open(out + "/tb_" + d["proj"] + ".v").read()


def test_walker_says_same_design_or_not():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    with tempfile.TemporaryDirectory() as t:
        out, _ = _make(t)
        good = _walk(out, _log(out))
        assert good.returncode == 0 and "IS this folder's design" in good.stdout and "NEIGHBOURS" in good.stdout and "E1" in good.stdout
        other = _walk(out, _log(out, fp="deadbeef"))
        assert other.returncode == 1 and "IS NOT this folder's design" in other.stdout and "NEIGHBOURS" not in other.stdout
        assert _walk(out, _log(out, magic=0x12345678)).returncode == 1
