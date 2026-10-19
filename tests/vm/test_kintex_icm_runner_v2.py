"""Ledger #1259: an ICM file becomes a Kintex project with a JTAG runner; the runner agrees with the VM in simulation; host scripts build the command and decode a read; export-only and Gowin ICM output are separate."""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import kintex_icm_runner_v2 as kr  # noqa: E402

TREE = os.path.join(ROOT, "nano", "examples", "reduction_tree4_exit_v1.icm-hier.json")
KMAN = os.path.join(ROOT, "docs", "man", "kintex7-ypcb00338.man.json")
AMAN = os.path.join(ROOT, "docs", "man", "mustang-f100-a10.man.json")
TMAN = os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json")


def build(tmp_path, man, icm=TREE, sim=True):
    out = str(tmp_path / "o")
    env = dict(os.environ, UNICELL_RUNNER_SIM="1" if sim else "0")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", icm, "--man", man, "--output", out], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return out, r.stdout


def test_kintex_project_files_and_vm_expectation(tmp_path):
    out, text = build(tmp_path, KMAN, sim=False)
    names = set(os.listdir(out))
    assert {"Makefile", "kit.json", "design.json", "expected.json", "vectors.txt", "run_vectors.sh", "decode_run.py", "make_cmd.py", "k7_ft232h.cfg"} <= names
    assert not any(n.endswith(".ys") for n in names)                      # no Gowin script
    assert all(n.endswith(".sv") or not n.startswith(("adder", "ram", "icm_")) for n in names)
    d = json.load(open(os.path.join(out, "design.json")))
    assert [e["name"] for e in d["entries"]] == ["input_0", "input_1", "input_2", "input_3"] and [e["name"] for e in d["exits"]] == ["output"]
    exp = json.load(open(os.path.join(out, "expected.json")))
    assert exp["vectors.txt"]["exits"]["output"]["words"] == [100, 4, 8]    # 10+20+30+40, 1+1+1+1, 2+2+2+2
    assert exp["vectors2.txt"]["exits"]["output"]["words"] == [98, 406, 12]
    mk = open(os.path.join(out, "Makefile")).read()
    assert "TOP_MODULE = top" in mk and "PART    = xc7k480tffg1156-1" in mk
    for f in ("run_vectors.sh", "run_read.sh"):
        t = open(os.path.join(out, f)).read()
        assert "flash" not in t.lower() and "program" not in t
        subprocess.run(["sh", "-n", os.path.join(out, f)], check=True)


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_runner_agrees_with_the_vm_in_simulation(tmp_path):
    out, text = build(tmp_path, KMAN, sim=True)
    assert "Simulation against the VM: PASS" in text
    rec = json.load(open(os.path.join(out, "ASSEMBLY.json")))
    assert rec["sim_vs_vm"]["verdict"] == "PASS"
    assert json.load(open(os.path.join(out, "kit.json")))["sim"] == "PASS"


def test_host_scripts_roundtrip_and_a_wrong_card_answer_fails(tmp_path):
    out, _ = build(tmp_path, KMAN, sim=False)
    d = json.load(open(os.path.join(out, "design.json")))
    lay, nw = d["layout"], d["nw"]
    subprocess.run([sys.executable, "-I", os.path.join(out, "make_cmd.py"), os.path.join(out, "vectors.txt"), os.path.join(out, "cmd.txt")], check=True, capture_output=True)
    w = [int(x, 16) for x in open(os.path.join(out, "cmd.txt")).read().split()]
    assert len(w) == nw and w[0] == 3 and w[lay["ecnt"]:lay["ecnt"] + 4] == [3, 3, 3, 3] and w[lay["ebuf"]] == 10 and w[lay["ebuf"] + 16] == 20
    bad = subprocess.run([sys.executable, "-I", os.path.join(out, "make_cmd.py"), os.path.join(out, "vectors.txt"), os.path.join(out, "x.txt")], capture_output=True)
    assert bad.returncode == 0

    def snap(words_out):
        s = [0] * nw
        s[0], s[1], s[2] = 0x52554E31, 1600, (1 << 30) | (4 << 16) | (16 << 8) | 1
        b = lay["xst"]
        s[b], s[b + 1], s[b + 2] = len(words_out), kr.sig_of(words_out), 1562
        for k, v in enumerate(words_out):
            s[lay["xbuf"] + k] = v
        return "SNAP result " + " ".join("%08x" % x for x in s) + "\n"
    for words_out, verdict in (([100, 4, 8], "OVERALL: PASS"), ([100, 4, 9], "OVERALL: FAIL")):
        open(os.path.join(out, "r.log"), "w").write(snap(words_out))
        r = subprocess.run([sys.executable, "-I", os.path.join(out, "decode_run.py"), os.path.join(out, "r.log"), "vectors.txt"], capture_output=True, text=True)
        assert verdict in r.stdout, r.stdout


def test_unknown_entry_in_vectors_is_refused(tmp_path):
    out, _ = build(tmp_path, KMAN, sim=False)
    open(os.path.join(out, "v.txt"), "w").write("nope: 1 2\n")
    r = subprocess.run([sys.executable, "-I", os.path.join(out, "make_cmd.py"), os.path.join(out, "v.txt"), os.path.join(out, "c.txt")], capture_output=True, text=True)
    assert r.returncode != 0 and "unknown entry" in r.stderr


def test_other_cards_icm_output(tmp_path):
    out, _ = build(tmp_path / "a", AMAN, sim=False)                         # Arria 10: export-only, plain Verilog
    names = set(os.listdir(out))
    assert "README.md" in names and not any(n.endswith(".ys") for n in names) and "Makefile" not in names
    out2, _ = build(tmp_path / "t", TMAN, sim=False)                        # Tang: unchanged Gowin output
    assert any(n.endswith(".ys") for n in os.listdir(out2))
