"""tests/vm/test_runner_hw_count_v1.py -- ledger #1283: runner v3 takes the HARDWARE's count for equal words in a row (Alan: the VM is corrected to the hardware, not the other way round).
1. priority_weighted (two equal words in a row): v2 reports DISAGREES (the VM side merged them); v3 PASSES with the hardware's list, which equals the VM's raw list (9 words).
2. a real difference is still a DISAGREES: ram_hold with its default vectors (the HOLD ram written three times against a flowing stream).
Needs iverilog (fails without it)."""
import json, os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano")); sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_icm_generate_v2 as g2  # noqa: E402
import kintex_icm_runner_v2 as k2  # noqa: E402
import kintex_icm_runner_v3 as k3  # noqa: E402
import flexsub_assemble_v1 as fa  # noqa: E402

MAN = fa.load_man_flexsub(os.path.join(ROOT, "docs", "man", "kintex7-ypcb00338.man.json"))
CT = os.path.join(ROOT, "nano", "examples", "card_tested")


def _wrap(kr, icm, d):
    g2.generate(icm, d, family="flex", rings=True)
    return kr.wrap(d, icm, MAN)


def test_equal_words_in_a_row_are_counted_by_the_hardware():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    icm = os.path.join(CT, "priority_weighted.icm.json")
    with tempfile.TemporaryDirectory() as t:
        assert _wrap(k2, icm, os.path.join(t, "a"))["sim"]["verdict"] == "DISAGREES WITH THE VM"      # v2: the VM side merged the two 2s
        r = _wrap(k3, icm, os.path.join(t, "b"))
        assert r["sim"]["verdict"] == "PASS" and "hardware" in r["sim"]["note"]
        words = json.load(open(os.path.join(t, "b", "expected.json")))["vectors.txt"]["exits"]["O"]["words"]
        assert words == [20, 30, 1, 10, 1, 2, 2, 1, 2]


def test_a_real_difference_is_still_a_disagreement():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    with tempfile.TemporaryDirectory() as t:
        assert _wrap(k3, os.path.join(CT, "ram_hold.icm.json"), os.path.join(t, "c"))["sim"]["verdict"] == "DISAGREES WITH THE VM"
