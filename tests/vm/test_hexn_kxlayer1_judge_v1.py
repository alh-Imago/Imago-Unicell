"""tests/vm/test_hexn_kxlayer1_judge_v1.py - layer 1 detector (core v2) -> batch judge with the host in the middle (tools/hexn_kxlayer1_judge_v1.py), 5 Nov 2026. Simulation only.
Fast: word packing, the NONE rule, the reference, and that a wrong judge answer is counted. Slow (about 4 minutes): the detector bench (core v2 behind the JTAG bridge) and the base (hex5, judge inside) in iverilog, end to end on 3 words of 8 sensors."""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_kxlayer1_judge_v1 as L, hexn_scorer_ref_v1 as R


def test_packing_none_rule_and_reference():
    row = [0, 3, -1, 6, 1, 2, 5, 4]; assert L.bins_of(row) == [0, 3, L.NONE_BIN, 6, 1, 2, 5, 4]
    w = R.w_score(L.bins_of(row)); assert [(w >> 4 * i) & 15 for i in range(8)] == L.bins_of(row) and w >> 28 < 12      # the top nibble is sensor 7's bin, a score word
    m, samples, W, bias = L.make_data(1, 2); assert len(samples) == 2 and len(samples[0]) == 8 and len(W) == 2 and len(W[0]) == 8 and len(W[0][0]) == 16
    e = L.expected_results(W, bias, [row]); assert e == [R.score(W, bias, L.bins_of(row))[0]]


def test_wrong_judge_answer_is_counted():
    m, samples, W, bias = L.make_data(1, 2); rows = [[0, 1, 2, 3, 4, 5, 6, 0], [1, 1, 1, 1, 1, 1, 1, 1]]; e = L.expected_results(W, bias, rows)
    ok = [bytes([1]) + x.to_bytes(4, "little") + bytes([0]) for x in e]; assert L.check_results(ok, W, bias, rows) == (2, 0)
    bad = [ok[0], bytes([1]) + (e[1] ^ 1).to_bytes(4, "little") + bytes([0])]; assert L.check_results(bad, W, bias, rows) == (2, 1)
    assert L.check_results([ok[0], bytes([0]) + e[1].to_bytes(4, "little") + bytes([0])], W, bias, rows) == (2, 1)           # no result waiting counts as a miss


@pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
def test_end_to_end_in_simulation():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hexn_kxlayer1_judge_v1.py"), "sim", "--words", "3"], capture_output=True, text=True, timeout=3000)
    assert "0 differ from the model" in r.stdout and "0 differ from the reference" in r.stdout and "LAYER 1 -> JUDGE PASS" in r.stdout, r.stdout + r.stderr[-800:]
