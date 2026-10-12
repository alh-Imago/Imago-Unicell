"""tests/vm/test_vixen_v1.py -- ledger #1105: the VIXeN cores (adder/mul/div join mode, priority sequenced channel, nano hold-from-config) and a mutation check for each.

RTL only. Needs iverilog and fails loudly without it (#965). A mutation check copies a core, breaks one line, and the bench MUST then fail: a bench that cannot fail proves nothing."""
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "fpga", "verilog")


def _need():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"


def _run(tmp_path, srcs, top=None, defs=()):
    _need()
    exe = str(tmp_path / "t")
    cmd = ["iverilog", "-g2012"] + [f"-D{d}" for d in defs] + (["-s", top] if top else []) + ["-o", exe] + srcs
    c = subprocess.run(cmd, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr
    return subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=900).stdout


def _mutant(tmp_path, name, old, new):
    text = open(os.path.join(V, name)).read()
    assert old in text, f"mutation anchor missing in {name}"
    p = tmp_path / ("mut_" + name)
    p.write_text(text.replace(old, new, 1))
    return str(p)


F = lambda n: os.path.join(V, n)

HELP = {"adder_cell_v4e.v": ["adder_v1.v"], "mul_cell_v5e.v": ["bitwise_multiplier_32bit.v"], "div_cell_v4e.v": []}
JOIN = [("tb_vixen_join_adder", "adder_cell_v4e.v"), ("tb_vixen_join_mul", "mul_cell_v5e.v"), ("tb_vixen_join_div", "div_cell_v4e.v")]


@pytest.mark.parametrize("top,core", JOIN)
def test_join_bench_passes(top, core, tmp_path):
    out = _run(tmp_path, [F(core), F("tb_vixen_join_v1.v")] + [F(h) for h in HELP[core]], top)
    assert "PASS" in out and "FAIL" not in out, out[-600:]


@pytest.mark.parametrize("top,core", JOIN)
def test_join_bench_catches_a_broken_join(top, core, tmp_path):
    bad = _mutant(tmp_path, core, "join_mode && j_arr_a && j_arr_b", "join_mode && (j_arr_a || j_arr_b)")
    out = _run(tmp_path, [bad, F("tb_vixen_join_v1.v")] + [F(h) for h in HELP[core]], top)
    assert "FAIL" in out or "PASS" not in out, "mutation not caught"


@pytest.mark.parametrize("steps", [4, 8])
def test_div_v4e_old_bench(steps, tmp_path):
    out = _run(tmp_path, [F("div_cell_v4e.v"), F("tb_div_cell_v4.v")], defs=("CELL=div_cell_v4e", f"STEPS={steps}"))
    assert "PASS" in out and "FAIL" not in out, out[-600:]


def test_priority_sequenced(tmp_path):
    out = _run(tmp_path, [F("priority_cell_v4e.v"), F("tb_vixen_priority_seq_v1.v")])
    assert "PASS" in out and "FAIL" not in out, out[-600:]


def test_priority_bench_catches_a_broken_sequence(tmp_path):
    bad = _mutant(tmp_path, "priority_cell_v4e.v", "seq_live && cand_n && seq_due == 2'd0", "seq_live && cand_n")
    out = _run(tmp_path, [bad, F("tb_vixen_priority_seq_v1.v")])
    assert "FAIL" in out or "PASS" not in out, "mutation not caught"


def test_nano_config_equals_live_wires(tmp_path):
    out = _run(tmp_path, [F("nano_gate_v4e.v"), F("tb_vixen_nano_cfg_v1.v")])
    assert "PASS" in out and "FAIL" not in out, out[-600:]


def test_nano_bench_catches_a_dead_config_bit(tmp_path):
    bad = _mutant(tmp_path, "nano_gate_v4e.v", "hold_in | cmd_latch[14]", "hold_in")
    out = _run(tmp_path, [bad, F("tb_vixen_nano_cfg_v1.v")])
    assert "FAIL" in out, "mutation not caught"
