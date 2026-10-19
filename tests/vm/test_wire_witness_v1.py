"""Ledger #1289: the WIRE WITNESSES. The v4 flex emitter adds a read-only `witness` port (one sticky bit per connection, one per cell); runner v5 puts it in the card read-back; the Walker (walker_card_v2)
marks the neighbour connections the card itself saw a word cross. Simulation only (the card result is a separate ledger entry)."""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import flexsub_icm_generate_v3 as g3  # noqa: E402
import flexsub_icm_flex_v3 as f3  # noqa: E402
import flexsub_icm_generate_v4 as g4  # noqa: E402
import flexsub_icm_flex_v4 as f4  # noqa: E402
import walker_card_v2 as wk  # noqa: E402

ICM = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence_v2.icm-hier.json")
KMAN = os.path.join(ROOT, "docs", "man", "kintex7-ypcb00338.man.json")
need = pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog missing")


def test_emitter_without_witness_is_v3_byte_for_byte():
    t3 = f3.emit_top_flex("t", g3.plan(ICM, family="flex"), "arbitrate")[0]
    t4 = f4.emit_top_flex("t", g4.plan(ICM, family="flex"), "arbitrate", 32, witness=False)[0]
    assert t3 == t4
    w = f4.emit_top_flex("t", g4.plan(ICM, family="flex"), "arbitrate")[0]
    assert re.search(r"output wire \[78:0\] witness", w) and "assign witness = witness_r;" in w     # 39 connections + 40 cells


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if not shutil.which("iverilog"):
        pytest.skip("iverilog missing")
    out = str(tmp_path_factory.mktemp("w") / "o")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v5.py"), "-s", "flex", "--icm", ICM, "--man", KMAN, "--output", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "Simulation against the VM: PASS" in r.stdout
    d = json.load(open(os.path.join(out, "design.json")))
    exe = os.path.join(out, "s.vvp")
    tb = [f for f in os.listdir(out) if f.startswith("tb_")][0]
    top = d["proj"] + ".v"
    svs = [f for f in os.listdir(out) if f.endswith(".sv")]
    assert subprocess.run(["iverilog", "-g2012", "-o", exe, tb, top] + svs, cwd=out).returncode == 0
    text = subprocess.run(["vvp", exe], cwd=out, capture_output=True, text=True).stdout
    logs = []
    for k in (0, 1):
        h = re.search(r"SNAPALL %d ([0-9a-f]+)" % k, text).group(1)
        ws = [h[i:i + 8] for i in range(0, len(h), 8)][::-1]
        p = os.path.join(out, "run%d.log" % k)
        open(p, "w").write("SNAP result " + " ".join(ws) + "\n")
        logs.append(p)
    return out, d, logs


@need
def test_layout_and_map_numbering(built):
    out, d, logs = built
    m = json.load(open(os.path.join(out, "design_map.json")))
    assert d["witness_bits"] == m["witness"]["bits"] == 79 and d["layout"]["nwit"] == 3 and d["nw"] == d["layout"]["wit"] + 3
    assert sorted(e["k"] for e in m["witness"]["edges"]) == list(range(39)) and sorted(c["k"] for c in m["witness"]["cells"]) == list(range(39, 79))


@need
def test_card_witnesses_are_consistent_and_show_the_working_path(built, capsys):
    out, d, logs = built
    m = json.load(open(os.path.join(out, "design_map.json")))
    words = [int(x, 16) for x in open(logs[0]).read().split()[2:]]
    seen_e, seen_c = wk.witness_bits(m, d, words)
    assert all(v in (0, 1) for v in list(seen_e.values()) + list(seen_c.values()))        # no X reached the read-back
    ek = {(e["from"], e["to"]): e["k"] for e in m["witness"]["edges"]}
    ck = {c["id"]: c["k"] for c in m["witness"]["cells"]}
    for s in range(4):                                           # every stage's gather received a word and passed it on: those connections must have carried one
        assert seen_e[ek[(f"s{s}.gather.merge", f"s{s}.gather")]] == 1
        assert seen_c[ck[f"s{s}.gather"]] == 1
    for (a, b), k in ek.items():                                 # a connection can carry a word only if its source offered one
        if seen_e[k] and a in ck:
            assert seen_c[ck[a]] == 1, (a, b)
    assert wk.main([out, logs[0]]) == 0
    t = capsys.readouterr().out
    assert "IS this folder's design" in t and "connections carried a word" in t and "*" in t


@need
def test_walker_refuses_other_design_and_catches_inconsistent_witness(built, capsys, tmp_path):
    out, d, logs = built
    m = json.load(open(os.path.join(out, "design_map.json")))
    words = [int(x, 16) for x in open(logs[0]).read().split()[2:]]
    wrong = list(words); wrong[d["layout"]["ebuf"]] ^= 1
    p = tmp_path / "wrong.log"; p.write_text("SNAP result " + " ".join("%08x" % x for x in wrong) + "\n")
    assert wk.main([out, str(p)]) == 1
    t = capsys.readouterr().out
    assert "IS NOT this folder's design" in t and "carried a word" not in t and "NEIGHBOURS" not in t
    seen_e, seen_c = wk.witness_bits(m, d, words)                # clear a source cell's flag while its outgoing connection stays set -> impossible on a real card
    ck = {c["id"]: c["k"] for c in m["witness"]["cells"]}
    src = next(e["from"] for e in m["witness"]["edges"] if seen_e[e["k"]] and e["from"] in ck)
    bad = list(words); k = ck[src]; bad[d["layout"]["wit"] + k // 32] &= ~(1 << (k % 32))
    q = tmp_path / "bad.log"; q.write_text("SNAP result " + " ".join("%08x" % x for x in bad) + "\n")
    assert wk.main([out, str(q)]) == 1
    assert "INCONSISTENT" in capsys.readouterr().out


@need
def test_walker_writes_the_card_shape_and_the_mirror_side_can_read_it(built, capsys, tmp_path):
    out, d, logs = built
    sp = str(tmp_path / "card.shape.json")
    assert wk.main([out, logs[0], logs[1], "--shape", sp]) == 0
    sh = wk.read_card_shape(sp)
    h = sh["header"]
    assert h["shape_version"] == "1.0" and h["discovery_method"] == "card_wire_witness_v1" and h["design_fingerprint"] == json.load(open(os.path.join(out, "design_map.json")))["fingerprint"]
    assert len(sh["cells"]) == 40 and len(sh["edges"]) == 39 and h["edges_confirmed"] == len(sh["confirmed"]) and h["edges_confirmed"] + h["edges_not_exercised"] == 39
    assert 0 < h["edges_confirmed"] < 39 and not sh["complete"]            # this vector set leaves one side of each branch idle: honest partial
    c0 = sh["cells"]["s0.branch"]
    assert (c0["module_type"], c0["row"], c0["col"], c0["cell_id"]) == ("branch", 0, 0, 0)
    e = next(x for x in sh["edges"] if x["from"]["instance"] == "s0.branch" and x["to"]["instance"] == "s0.add_neg")
    assert (e["from"]["direction"], e["to"]["direction"]) == ("N", "S") or (e["from"]["direction"], e["to"]["direction"]) == ("S", "N")
    assert e["confirmed_by_card"] is True
    bad = tmp_path / "x.json"; bad.write_text(json.dumps({"shape_version": "1.0", "discovery_method": "simulated_walker_ping_protocol"}))
    with pytest.raises(ValueError):
        wk.read_card_shape(str(bad))
    wrong = list(int(x, 16) for x in open(logs[0]).read().split()[2:]); wrong[d["layout"]["ebuf"]] ^= 1
    wp = tmp_path / "w.log"; wp.write_text("SNAP result " + " ".join("%08x" % x for x in wrong) + "\n")
    sp2 = str(tmp_path / "none.json")
    assert wk.main([out, str(wp), "--shape", sp2]) == 1 and not os.path.exists(sp2)
