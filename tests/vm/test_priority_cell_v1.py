"""tests/vm/test_priority_cell_v1.py -- ledger #1017: the flex PRIORITY core (sub/verilog/priority_cell_v4sa.v) against its self-checking bench (tb_priority_cell_v4sa.v), and the bench against
deliberate DEFECTS planted in the RTL: every defect must make the bench fail (a bench that cannot fail proves nothing). Requires iverilog."""
import os
import re
import subprocess
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SUBV = os.path.normpath(os.path.join(HERE, "..", "..", "sub", "verilog"))
RTL = os.path.join(SUBV, "priority_cell_v4sa.v")
TB = os.path.join(SUBV, "tb_priority_cell_v4sa.v")


def run_bench(rtl_path, tmp):
    exe = os.path.join(tmp, "tb.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-o", exe, TB, rtl_path], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:800]
    r = subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=120)
    return r.stdout


def test_bench_passes():
    out = run_bench(RTL, tempfile.mkdtemp())
    assert "ALL PASS" in out and "FAIL" not in out, out[-600:]
    assert out.count("PASS:") >= 100


DEFECTS = {
    "strict: highest rank wins":            ("{6'h0, (2'd3 - rank_n)}", "{6'h0, rank_n}"),
    "tie goes to south, not north":         ("(!cand_s || score_n >= score_s)", "(!cand_s || score_n > score_s)"),
    "losers acknowledged too":              ("assign ack_out_s = ready && win_s;", "assign ack_out_s = ready && cand_s;"),
    "upstream mask ignored":                ("wire cand_e = valid_in_e && upstream_mask[2] && (!sequenced || due_e);", "wire cand_e = valid_in_e && (!sequenced || due_e);"),
    "ready while pending":                  ("wire ready = armed && !pending && !freeze_in && !seq_cap;", "wire ready = armed && !freeze_in && !seq_cap;"),
    "freeze ignored":                       ("wire ready = armed && !pending && !freeze_in && !seq_cap;", "wire ready = armed && !pending && !seq_cap;"),
    "south's data from east":               ("(win_s ? in_s : {WIDTH{1'b0}})", "(win_s ? in_e : {WIDTH{1'b0}})"),
    "winner's credit never reduced":        ("credit_n <= win_n ? ((inc_n > total_weight) ? (inc_n - total_weight) : 8'h0) : inc_n;", "credit_n <= inc_n;"),
    "reconfiguration keeps the credits":    ("credit_n <= 8'h0; credit_s <= 8'h0; credit_e <= 8'h0; credit_w <= 8'h0;\n            armed <= 1'b1;", "armed <= 1'b1;"),
    "reconfiguration keeps a pending item": ("armed <= 1'b1; pending <= 1'b0; out_buffer", "armed <= 1'b1; out_buffer"),
    "released without ack_in":              ("if (ack_in) pending <= 1'b0;", "pending <= 1'b0;"),
    "weighted mode ignored":                ("scheduling_mode <= cfg_data[12];", "scheduling_mode <= 1'b0;"),
    "south's rank read from north's field": ("rank_s          <= cfg_data[7:6];", "rank_s          <= cfg_data[5:4];"),
    # ledger #1018: the sequenced channel
    "sequenced: every face a candidate":    ("wire cand_w = valid_in_w && upstream_mask[3] && (!sequenced || due_w);", "wire cand_w = valid_in_w && upstream_mask[3];"),
    "sequenced: the turn never advances":   ("if (sequenced) seq_idx <=", "if (1'b0) seq_idx <="),
    "sequenced: the turn wraps too late":   ("(seq_idx + 3'h1 >= seq_len) ? 3'h0", "(seq_idx + 3'h1 > seq_len) ? 3'h0"),
    "sequenced: reconfiguration keeps the turn": ("seq_order       <= cfg_data[24:17];\n            seq_idx         <= 3'h0;", "seq_order       <= cfg_data[24:17];"),
    "sequenced: an empty order has every turn due": ("wire       due_ok   = sequenced && (seq_len != 3'h0);", "wire       due_ok   = sequenced;"),
    "sequenced: turn 1 read from turn 0's field": ("wire [1:0] due_face = seq_order[{seq_idx[1:0], 1'b0} +: 2];", "wire [1:0] due_face = seq_order[1:0];"),
    "sequenced: bit 13 not read":           ("sequenced       <= cfg_data[13];", "sequenced       <= 1'b0;"),
    "sequenced: length read from turn field": ("seq_len         <= cfg_data[16:14];", "seq_len         <= cfg_data[15:13];"),
    "weights not added for candidates":     ("wire [7:0] inc_s = cand_s ? (credit_s + {6'h0, rank_s}) : credit_s;", "wire [7:0] inc_s = credit_s;"),
}


@pytest.mark.parametrize("name", list(DEFECTS))
def test_defect_is_caught(name):
    old, new = DEFECTS[name]
    src = open(RTL).read()
    assert old in src, f"the defect {name!r} no longer applies: {old!r} is not in the RTL"
    tmp = tempfile.mkdtemp()
    bad = os.path.join(tmp, "priority_cell_v4sa.v")
    open(bad, "w").write(src.replace(old, new, 1))
    out = run_bench(bad, tmp)
    assert "ALL PASS" not in out, f"defect not caught: {name}"
