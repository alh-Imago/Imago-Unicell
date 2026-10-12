"""tests/vm/test_mixed_blocks_v1.py -- ledger #1114: blocks tagged with a cell family (flex / sub); the Flex-Sub assembler splits the design at the family boundaries and inserts the sub bridge on every
crossing by itself; the Composer and the Workbench show the families in different colours. Chain in the example: A (flex, +1000) -> B (SUB, +234) -> C (flex, +5): out = x + 1239.
Needs iverilog (fails loudly without it, #965)."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
for sub in ("tools", "nano"):
    sys.path.insert(0, os.path.join(ROOT, sub))
import flexsub_mixed_v1 as mx  # noqa: E402

EX = os.path.join(ROOT, "nano", "examples", "mixed_flex_sub_flex_v1.icm-hier.json")
TB = os.path.join(ROOT, "sub", "verilog", "tb_mixed_flex_sub_flex_v1.v")
ASM = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]


def doc():
    return json.load(open(EX))


def write(d):
    p = os.path.join(tempfile.mkdtemp(), "m.icm-hier.json")
    json.dump(d, open(p, "w"))
    return p


@pytest.fixture(scope="module")
def built():
    out = tempfile.mkdtemp()
    r = subprocess.run(ASM + ["-s", "flex", "--icm", EX, "--top", "mix", "--output", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
    return out


def sim(built, stall, n=30):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"
    srcs = [os.path.join(built, f) for f in os.listdir(built) if f.endswith(".v")]
    exe = os.path.join(built, f"t{stall}.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-DTOP=mix", f"-DN={n}", f"-DSTALL={stall}", "-o", exe, TB] + srcs, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[-500:]
    out = subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=300).stdout
    return [int(l.split()[2]) for l in out.splitlines() if l.startswith("O ")], out


def test_the_family_tag_round_trips_and_the_vm_ignores_it():
    import icm_vix_v1 as vix
    f = vix.IcmVixFile.load(EX)
    assert [p.family for p in f.placements] == ["flex", "sub", "flex"]
    p = write(doc())
    assert [x.family for x in vix.IcmVixFile.load(p).placements] == ["flex", "sub", "flex"]
    f.save(p)
    assert [x.family for x in vix.IcmVixFile.load(p).placements] == ["flex", "sub", "flex"]
    recs, _ = f.flatten()
    assert len(recs) == 12                                           # flattening (the VM's view) is unchanged


def test_the_planner_cuts_at_the_family_boundaries():
    p = mx.plan(EX)
    assert [(r["family"], len(r["cells"])) for r in p["regions"]] == [("flex", 4), ("sub", 4), ("flex", 4)]
    assert [(x["from"], x["to"]) for x in p["crossings"]] == [("flex0", "sub1"), ("sub1", "flex2")]


def test_the_assembler_inserts_both_bridges_by_itself(built):
    top = open(os.path.join(built, "mix.v")).read()
    assert top.count("flex_to_sub_v1") == 1 and top.count("sub_to_flex_v1") == 1
    assert "sub1_done" in top                                        # the exit bridge opens the entry bridge


@pytest.mark.parametrize("stall", [0, 1])
def test_every_word_equals_x_plus_1239_in_order(built, stall):
    vals, out = sim(built, stall)
    assert vals == [100 + 7 * k + 1239 for k in range(30)] and "END" in out


def test_negative_control_without_the_done_line_words_are_lost(built):
    bad = tempfile.mkdtemp()
    for f in os.listdir(built):
        if f.endswith(".v"):
            shutil.copy(os.path.join(built, f), bad)
    t = open(os.path.join(bad, "mix.v")).read()
    open(os.path.join(bad, "mix.v"), "w").write(t.replace(".done(sub1_done));   // flex flex0", ".done(1'b1));   // flex flex0"))   # entry bridge never held: a word every clock
    vals, out = sim(bad, 1)
    assert vals != [100 + 7 * k + 1239 for k in range(30)] or "TIMEOUT" in out


def test_a_design_without_a_family_tag_is_not_routed_here():
    d = doc()
    for p in d["design_map"]["placements"]:
        p.pop("family", None)
    assert not mx.is_mixed(write(d)) and mx.is_mixed(EX)


def test_a_sub_block_with_a_host_port_is_refused_with_its_reason():
    d = doc()
    d["design_map"]["placements"][1]["overrides"]["in"] = {"io_name": "sneak"}
    with pytest.raises(mx.MixedError, match="host names"):
        mx.plan(write(d))


def test_a_sub_block_with_two_entries_is_refused():
    d = copy.deepcopy(doc())
    d["design_map"]["placements"][1]["family"] = "sub"
    d["design_map"]["placements"][0]["family"] = "sub"
    d["design_map"]["placements"][2]["family"] = "flex"
    with pytest.raises(mx.MixedError, match="ONE entry crossing"):
        mx.plan(write(d))


def test_composer_shows_and_keeps_the_family(tmp_path):
    import flex_layout_view_v1 as flv
    lay = flv.Layout.new(40, 60, "m")
    res = lay.place_block(os.path.join(ROOT, "nano", "examples", "cordic_z_convergence.icm-hier.json"), 2, 2)
    assert res.get("ok"), res
    name = res["block"]
    assert lay.snapshot()["mixed"] is None and lay.snapshot()["blocks"][0]["family"] is None
    assert lay.set_block_family(name, "sub").get("ok")
    v = lay.snapshot()
    assert v["blocks"][0]["family"] == "sub" and v["mixed"] is not None
    assert not lay.set_block_family(name, "nano").get("ok")
    p = tmp_path / "x.icm-hier.json"
    lay.save(str(p), "vix")
    assert any(pl.get("family") == "sub" for pl in json.load(open(p))["design_map"]["placements"])
    lay2 = flv.Layout.load(str(p))
    assert lay2.snapshot()["blocks"][0]["family"] == "sub"               # reload keeps it
    lay2.undo()


def test_workbench_colours_cells_by_family_and_stays_plain_without_tags():
    import workbench_v1 as w
    c = w.WorkbenchController()
    r = c.load_icm_vix(EX)
    assert r["ok"] and r["families"] == ["flex", "sub"] and "standard mode" in r["family_note"]
    fams = {v["family"] for v in c.state()["state"]["cells"].values()}
    assert fams == {"flex", "sub"}
    r2 = c.load_icm_vix(os.path.join(ROOT, "nano", "examples", "cordic_z_convergence.icm-hier.json"))
    assert r2["ok"] and r2["families"] == [] and r2["family_note"] is None
    assert {v["family"] for v in c.state()["state"]["cells"].values()} == {None}
    assert "fam-sub" in w.WORKBENCH_HTML and ".cell.fam-sub" in w.WORKBENCH_HTML
