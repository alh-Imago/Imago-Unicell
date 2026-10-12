"""tests/vm/test_sub_div_v1.py -- ledger #1072: division through the SUB family (fixed latency, no ack) from an ICM, in generated RTL and in the std VM.

The sub generator instantiates div_cell_v4s at its default STEPS = 32: the whole division in one clock, the same fixed ONE-cycle latency as adder_cell_v4s / mul_cell_v4s, fully pipelined. Y (the
dividend) reaches the divider directly, X (the divisor) through a relay; the generator pads the shorter path so both arrive together. Checks: the result, the predicted cycle, back-to-back items on
consecutive cycles, remainder_primary (x mod y on the single output), and the refusals (no second port on sub). Requires iverilog."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flex_rtl_harness_v1 as h  # noqa: E402
import unicell_super_automaton_v1 as vm  # noqa: E402
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

M = 0xFFFFFFFF


def design(**cfg):
    mid = IcmV3Record(cell_id="M", row=1, col=1, core="div", core_config=dict({"upstream_mask": ["n", "w"], "downstream_mask": ["e"]}, **cfg))
    return [h.ram("X", 0, 0, [], ["e"]), h.ram("P", 0, 1, ["w"], ["s"]), h.ram("Y", 1, 0, [], ["e"]), mid, h.ram("E", 1, 2, ["w"], [])]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="subdiv_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def build(tmp, name, recs):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    return d, h.cli("-s", "sub", "--icm", icm, "--output", d)


def simulate(folder, items):
    """items: [{input name: value}], item k injected as a 1-cycle valid on cycle k. Returns [(cycle, data)] of every valid output cycle."""
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
    outs = re.findall(r"output\s+wire\s+\[31:0\]\s+out_(\w+)_data", text)
    assert len(outs) == 1
    conn = ", ".join([f".in_{n}_data(d_{n}), .in_{n}_valid(v_{n})" for n in ins] + [f".out_{outs[0]}_data(od), .out_{outs[0]}_valid(ov)"])
    decl = "\n".join(f"  reg [31:0] d_{n} = 0; reg v_{n} = 0;" for n in ins)
    drive = "\n".join(f"      if (c == {k}) begin " + " ".join(f"d_{n} = 32'd{it[n]}; v_{n} = 1;" for n in ins) + " end" for k, it in enumerate(items))
    clear = " ".join(f"v_{n} = 0; d_{n} = 0;" for n in ins)
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg_valid = 0; wire [31:0] od; wire ov;
{decl}
  {top} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {conn});
  always #5 clk = ~clk;
  integer c;
  initial begin
    repeat (4) @(posedge clk); #1 rst = 0;
    @(posedge clk); #1 cfg_valid = 1; @(posedge clk); #1 cfg_valid = 0;
    repeat (3) @(posedge clk); #1;
    for (c = 0; c < {len(items) + 40}; c = c + 1) begin
      {clear}
{drive}
      #3 $display("OUT %0d %0d %0d", c, ov, od);
      @(posedge clk); #1;
    end
    $finish;
  end
endmodule
"""
    open(os.path.join(folder, "tb_gen.v"), "w").write(tb)
    files = [f for f in rec["files"] if f.endswith(".v")]
    c = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(folder, "tb.vvp"), "tb_gen.v", *files], cwd=folder, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:400]
    out = subprocess.run(["vvp", os.path.join(folder, "tb.vvp")], capture_output=True, text=True).stdout
    return [(int(cyc), int(d)) for cyc, v, d in re.findall(r"OUT (\d+) (\d+) (\d+)", out) if int(v)], rec


def vm_answer(recs, a, b):
    g = vm.SuperGrid(recs)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    g.inject(*pos["Y"], a)
    g.inject(*pos["X"], b)
    for _ in range(120):
        g.tick()
    return g.cells[pos["E"]].ram_data_reg


PAIRS = [(23, 7), (M, 1), (M, M), (0, 5), (5, 0), (0, 0), (M, 0), (1, 2), (M - 1, M), (1 << 31, 3), (1 << 31, 1 << 31), (1000000007, 12345), (4000000000, 3)]


def want(a, b, rem_first):
    q, r = (M, a) if b == 0 else (a // b, a % b)
    return r if rem_first else q


@pytest.mark.parametrize("rem_first", [0, 1])
def test_sub_division_in_generated_rtl_and_the_vm(tmp, rem_first):
    recs = design(remainder_primary=rem_first)
    d, r = build(tmp, f"one_r{rem_first}", recs)
    assert r.returncode == 0, (r.stderr or r.stdout)[:500]
    lat = list(json.load(open(os.path.join(d, "ASSEMBLY.json")))["output_latency_cycles"].values())[0]
    text = open(os.path.join(d, json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"] + ".v")).read()
    assert "div_cell_v4s" in text and "div_cell_v4sa" not in text
    for a, b in PAIRS:
        hits, _ = simulate(d, [{"X": b, "Y": a}])
        assert hits == [(lat, want(a, b, rem_first))], (a, b, hits)
        assert vm_answer(recs, a, b) == want(a, b, rem_first), (a, b)


def test_back_to_back_items_each_clock_come_out_in_order(tmp):
    recs = design()
    d, r = build(tmp, "stream", recs)
    assert r.returncode == 0, (r.stderr or r.stdout)[:500]
    lat = list(json.load(open(os.path.join(d, "ASSEMBLY.json")))["output_latency_cycles"].values())[0]
    items = [{"X": b, "Y": a} for a, b in PAIRS]
    hits, _ = simulate(d, items)
    assert hits == [(lat + k, want(a, b, 0)) for k, (a, b) in enumerate(PAIRS)]


def test_the_sub_family_has_no_second_port_so_second_output_is_refused(tmp):
    d, r = build(tmp, "second", design(second_output=1))
    assert r.returncode != 0 and "second" in (r.stderr + r.stdout).lower()
