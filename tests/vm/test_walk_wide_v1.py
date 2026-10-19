"""Ledger #1291: runner v6 adds a WIDE vector set (plus and minus, small to large) and walk_card.sh (both sets, then the Walker). In simulation the wide set makes every connection and cell of the
CORDIC carry a word (39/39, 40/40), which the first small set does not (23/39), and the runner agrees with the VM on it."""
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
import kintex_icm_runner_v6 as kr  # noqa: E402
import walker_card_v2 as wk  # noqa: E402

ICM = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence_v2.icm-hier.json")
KMAN = os.path.join(ROOT, "docs", "man", "kintex7-ypcb00338.man.json")


def test_wide_vectors_shape():
    v = kr.wide_vectors([("a", 32), ("b", 16)])
    assert len(v["a"]) == 16 == len(v["b"]) and v["a"][:2] == [3, 0xFFFFFFFD] and v["b"][:2] == [4, 0xFFFC] and all(0 <= x < 65536 for x in v["b"])


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog missing")
def test_wide_set_covers_every_wire_and_walk_script_is_written(tmp_path):
    out = str(tmp_path / "o")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v6.py"), "-s", "flex", "--icm", ICM, "--man", KMAN, "--output", out], capture_output=True, text=True)
    assert r.returncode == 0 and "Simulation against the VM: PASS" in r.stdout, r.stderr
    sh = open(os.path.join(out, "walk_card.sh")).read()
    assert "vectors_wide.txt" in sh and "walker_card_v2.py" in sh and "--shape card.shape.json" in sh and ROOT in sh and "REPOROOT" not in sh
    assert subprocess.run(["sh", "-n", os.path.join(out, "walk_card.sh")]).returncode == 0
    d = json.load(open(os.path.join(out, "design.json")))
    exp = json.load(open(os.path.join(out, "expected.json")))
    assert "vectors_wide.txt" in exp and exp["vectors_wide.txt"]["exits"]["z_output"]["words"]
    entries = [(e["name"], e["width"]) for e in d["entries"]]; exits = [(e["name"], e["width"]) for e in d["exits"]]
    sets = [(kr.wide_vectors(entries), {n: exp["vectors_wide.txt"]["exits"][n]["words"] for n, _ in exits})]
    lay = d["layout"]
    tb = kr.TB.replace("PROJECT", d["proj"]).replace("NWV", str(lay["nw"])).replace("NEV", str(len(entries))).replace("NXV", str(len(exits))).replace("DEPTHV", str(kr.DEPTH)).replace("MAGIC", str(kr.MAGIC))
    tb = tb.replace("RUNS", kr.tb_runs(entries, exits, lay, sets, int(d["fingerprint"], 16)))
    open(os.path.join(out, "tb_wide.v"), "w").write(tb)
    svs = [f for f in os.listdir(out) if f.endswith(".sv")]
    assert subprocess.run(["iverilog", "-g2012", "-o", os.path.join(out, "w.vvp"), os.path.join(out, "tb_wide.v"), os.path.join(out, d["proj"] + ".v")] + [os.path.join(out, f) for f in svs]).returncode == 0
    t = subprocess.run(["vvp", os.path.join(out, "w.vvp")], capture_output=True, text=True).stdout
    assert "PASS" in [x.strip() for x in t.splitlines()]                    # the runner agrees with the VM on the wide set
    h = re.search(r"SNAPALL 0 ([0-9a-f]+)", t).group(1)
    ws = [h[i:i + 8] for i in range(0, len(h), 8)][::-1]
    log = os.path.join(out, "runw.log"); open(log, "w").write("SNAP result " + " ".join(ws) + "\n")
    m = json.load(open(os.path.join(out, "design_map.json")))
    e, c = wk.witness_bits(m, d, [int(x, 16) for x in ws])
    assert sum(e.values()) == 39 and sum(c.values()) == 40
    sp = os.path.join(out, "card.shape.json")
    assert wk.main([out, log, "--shape", sp]) == 0 and wk.read_card_shape(sp)["complete"]
