"""Ledger #1126: `family: std|carrier` in the DSL. The mixed_flex_sub_flex example re-tagged as one standard-line design compiles, assembles with no -s, and the RTL gives x + 1239; mixes with flex/sub are refused."""
import json, os, re, shutil, subprocess, sys, tempfile
import pytest
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
for sub in ("tools", "nano", "."):
    sys.path.insert(0, os.path.join(ROOT, sub))
UC = os.path.join(ROOT, "nano", "examples", "mixed_flex_sub_flex_v1.uc")
CLI = [sys.executable, os.path.join(ROOT, "nano", "dsl_cli_v1.py")]
ASM = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
needs = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")


def _icm(fam, d, only=None):
    src = re.sub(r"family: (flex|sub)", "family: " + fam, open(UC).read())
    uc = os.path.join(d, "p.uc")
    open(uc, "w").write(src)
    out = os.path.join(d, "p.icm-hier.json")
    r = subprocess.run(CLI + [uc, "--target", "vixen", "-o", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


@pytest.mark.parametrize("fam", ["std", "carrier"])
def test_dsl_accepts_the_family_and_the_assembler_needs_no_dash_s(fam):
    d = tempfile.mkdtemp()
    icm = _icm(fam, d)
    assert {p["family"] for p in json.load(open(icm))["design_map"]["placements"]} == {fam}
    r = subprocess.run(ASM + ["--icm", icm, "--tap-io", "y_out", "--output", os.path.join(d, "o")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "Family: " + fam in r.stdout
    r = subprocess.run(ASM + ["-s", "flex" if fam == "std" else "std", "--icm", icm, "--tap-io", "y_out", "--output", os.path.join(d, "o2")], capture_output=True, text=True)
    assert r.returncode != 0


def test_a_mix_with_flex_is_refused_and_a_bad_family_named():
    d = tempfile.mkdtemp()
    icm = _icm("std", d)
    j = json.load(open(icm))
    j["design_map"]["placements"][0]["family"] = "flex"
    j["design_map"]["placements"].append(dict(j["design_map"]["placements"][0], instance="x", family="std"))
    p = os.path.join(d, "mix.icm-hier.json")
    json.dump(j, open(p, "w"))
    r = subprocess.run(ASM + ["--icm", p, "--tap-io", "y_out", "--output", os.path.join(d, "o")], capture_output=True, text=True)
    # ledger #1162: a flex + std mix is no longer refused for 'no bridge' (adapters are built; see test_mixed_std_regions_v1.py). This hand-edited file has no valid record hash, so it is still refused, but not for that old reason.
    assert r.returncode == 1 and "not built yet" not in r.stderr
    bad = os.path.join(d, "b.uc")
    open(bad, "w").write(open(UC).read().replace("family: sub", "family: nope", 1))
    r = subprocess.run(CLI + [bad, "--target", "vixen"], capture_output=True, text=True)
    assert r.returncode != 0 and "std, carrier" in (r.stdout + r.stderr)


@needs
@pytest.mark.parametrize("fam", ["std", "carrier"])
def test_rtl_adds_1239(fam):
    import std_icm_generate_v1 as SG, standalone_grid_v1 as S, carrier_grid_v3 as G
    from icm_vix_v1 import IcmVixFile
    d = tempfile.mkdtemp()
    icm = _icm(fam, d)
    recs = IcmVixFile.load(icm).flatten()[0]
    SG.normalise(recs)
    for r in recs:
        if r.core == "adder":
            r.core_config["join_mode"] = 1
    inp = next(r for r in recs if r.io_name == "x_in")
    out = next(r for r in recs if r.io_name == "y_out")
    assert SG.observe(out, recs)
    xs = [5, 100, -7, 12345]
    loads = [(60 + 300 * i, inp.cell_id, x) for i, x in enumerate(xs)]
    if fam == "std":
        got = S.simulate(recs, out.cell_id, 60 + 300 * len(xs) + 200, loads=loads, workdir=tempfile.mkdtemp())
    else:
        got = G.simulate(recs, out.cell_id, 60 + 300 * len(xs) + 200, loads=loads, workdir=tempfile.mkdtemp(), keep=("adder", "ram"))
    import itertools                                  # the exit ram holds its word and keeps offering it: one run of equal values per word
    assert [k for k, _ in itertools.groupby(v for _, v in got)] == [x + 1239 for x in xs]
