"""tests/vm/test_ram_offer_preload_v1.py -- ledger #1021: the ram cell's two new build parameters: OFFER_PRELOAD (a flowing ram offers its configured value ONCE at start, as the VM's load_data_valid
does) and HOLD (fixed mode whose stored value is replaced by arrivals: constant / one-shot / hold are the ram's three behaviours).
The bench (tb_ram_cell_v4sa.v) covers the original behaviour (default parameter, unchanged) and the new option; planted defects must each make it fail. Requires iverilog."""
import os
import subprocess
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SUBV = os.path.normpath(os.path.join(HERE, "..", "..", "sub", "verilog"))
RTL = os.path.join(SUBV, "ram_cell_v4sa.v")
TB = os.path.join(SUBV, "tb_ram_cell_v4sa.v")


def run_bench(rtl_path, tmp):
    exe = os.path.join(tmp, "tb.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-o", exe, TB, rtl_path], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:800]
    return subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=120).stdout


def test_bench_passes():
    out = run_bench(RTL, tempfile.mkdtemp())
    assert "ALL PASS" in out and "FAIL" not in out, out[-600:]
    assert out.count("PASS:") >= 20


DEFECTS = {
    "the preload is never offered":            ("pending     <= (OFFER_PRELOAD != 0) && !cfg_fixed_mode;", "pending     <= 1'b0;"),
    "the default ram offers its preload too":  ("pending     <= (OFFER_PRELOAD != 0) && !cfg_fixed_mode;", "pending     <= !cfg_fixed_mode;"),
    "hold: arrivals never replace the value":   ("data_reg <= data_in;\n                have     <= 1'b1;\n            end\n            // fixed_mode without HOLD", "have     <= 1'b1;\n            end\n            // fixed_mode without HOLD"),
    "hold: offers while empty":                 ("assign valid_out = fixed_mode ? ((HOLD != 0) ? (armed && have) : armed) : pending;", "assign valid_out = fixed_mode ? armed : pending;"),
    "hold: a write does not mark it non-empty": ("data_reg <= data_in;\n                have     <= 1'b1;\n            end\n            // fixed_mode without HOLD", "data_reg <= data_in;\n            end\n            // fixed_mode without HOLD"),
    "hold: reconfiguration keeps it non-empty": ("have        <= (OFFER_PRELOAD != 0);                       // HOLD", "have        <= have || (OFFER_PRELOAD != 0);                       // HOLD"),
    "hold: the constant (HOLD=0) takes writes":  ("else if (HOLD != 0 && valid_in) begin", "else if (valid_in) begin"),
    "the preload offer is not single-shot":    ("if (ack_in) pending <= 1'b0;", "if (ack_in) pending <= (OFFER_PRELOAD != 0) && data_reg == cfg_data[WIDTH-1:0];"),
}


@pytest.mark.parametrize("name", list(DEFECTS))
def test_defect_is_caught(name):
    old, new = DEFECTS[name]
    src = open(RTL).read()
    assert old in src, f"the defect {name!r} no longer applies"
    tmp = tempfile.mkdtemp()
    bad = os.path.join(tmp, "ram_cell_v4sa.v")
    open(bad, "w").write(src.replace(old, new, 1))
    assert "ALL PASS" not in run_bench(bad, tmp), f"defect not caught: {name}"
