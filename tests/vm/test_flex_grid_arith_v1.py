"""tests/vm/test_flex_grid_arith_v1.py -- FlexGrid step 3: the flex ADDER (add and subtract) and MULTIPLIER at width W, checked against the REAL RTL cells (ledger #967).

adder_cell_v4sa / mul_cell_v4sa take in_a, in_b and valid_in and have a WIDTH parameter, so the real cells are the oracle at W = 4, 8, 18, 32, 36. Operand roles: A is the earlier
arrival, B the later (the rule the flex generator reproduces by wiring); in the VM the first operand is injected first. A result must equal the RTL for add, subtract (order matters,
so a swapped pair would be caught) and the low-W-bit product. Requires iverilog and FAILS without it.
"""
import os
import random
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import flex_grid_v1 as fg  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402

WIDTHS = (4, 8, 18, 32, 36)
V = os.path.join(ROOT, "sub", "verilog")
MODULES = {"add": ("adder_cell_v4sa", ["adder_cell_v4sa.v", "adder_v1.v"], 0), "sub": ("adder_cell_v4sa", ["adder_cell_v4sa.v", "adder_v1.v"], 1),
           "mul": ("mul_cell_v4sa", ["mul_cell_v4sa.v"], 0)}


def sources(names):
    out = []
    for n in names:
        for d in (V, os.path.join(ROOT, "nano"), os.path.join(ROOT, "sub"), ROOT):
            p = os.path.join(d, n)
            if os.path.exists(p):
                out.append(p)
                break
        else:
            found = subprocess.run(["find", ROOT, "-name", n], capture_output=True, text=True).stdout.split()
            assert found, f"cannot find {n}"
            out.append(found[0])
    return out


def pairs(w):
    r = random.Random(w)
    m = (1 << w) - 1
    fixed = [(0, 0), (m, 0), (0, m), (m, m), (1 << (w - 1), 1), (1, m), (3, 5 & m), (7 & m, 2)]
    return fixed + [(r.getrandbits(w), r.getrandbits(w)) for _ in range(10)]


def rtl_results(kind, w, cases, tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    mod, files, cfg = MODULES[kind]
    tie = ".ack_in_c(1'b1)" if mod == "adder_cell_v4sa" else ".ack_in_hi(1'b1)"   # #974: unused second output port
    body = "\n".join(f"    run({w}'h{a:X}, {w}'h{b:X});" for a, b in cases)
    tb = f"""`timescale 1ns/1ps
module tb;
  parameter W = {w};
  reg clk = 0, rst = 1, freeze = 0, cfgv = 0, vin = 0, ackin = 0;
  reg [31:0] cfgd = 0; reg [W-1:0] ia = 0, ib = 0;
  wire ackout, vout; wire [W-1:0] dout;
  {mod} #(.CELL_ID(16'd0), .WIDTH(W)) dut (.clk(clk), .rst(rst), .freeze_in(freeze), .cfg_valid(cfgv), .cfg_data(cfgd),
      .in_a(ia), .in_b(ib), .valid_in(vin), .ack_out(ackout), .data_out(dout), .valid_out(vout), .ack_in(ackin), {tie});
  always #5 clk = ~clk;
  task run(input [W-1:0] a, input [W-1:0] b);
    begin
      cfgd = 32'd{cfg}; cfgv = 1; @(posedge clk); #1; cfgv = 0;
      ia = a; ib = b; vin = 1; @(posedge clk); #1; vin = 0;
      if (!vout) $display("NOVALID");
      $display("R %h %h %h", a, b, dout);
      ackin = 1; @(posedge clk); #1; ackin = 0;
    end
  endtask
  initial begin
    repeat (3) @(posedge clk); #1 rst = 0;
{body}
    $finish;
  end
endmodule
"""
    f = tmp_path / f"tb_{kind}_{w}.v"
    f.write_text(tb)
    exe = tmp_path / f"tb_{kind}_{w}.vvp"
    c = subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(f)] + sources(files), capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:500]
    out = subprocess.run(["vvp", str(exe)], capture_output=True, text=True).stdout
    assert "NOVALID" not in out, out[:300]
    res = {}
    for line in out.splitlines():
        if line.startswith("R "):
            _, a, b, d = line.split()
            res[(int(a, 16), int(b, 16))] = int(d, 16)
    assert len(res) == len(set(cases)), (len(res), len(cases))
    return res


def vm_result(kind, a, b, w, mutate=None):
    """A injected first (the earlier arrival = operand A), B later."""
    ram = lambda cid, r, c, up, dn: IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": dn})
    if kind == "mul":
        mid = IcmV3Record(cell_id="M", row=1, col=1, core="mul", core_config={"upstream_mask": ["w", "n"], "downstream_mask": ["e"]})
    else:
        mid = IcmV3Record(cell_id="M", row=1, col=1, core="adder", core_config={"upstream_mask": ["w", "n"], "downstream_mask": ["e"], "subtract_mode": 1 if kind == "sub" else 0})
    recs = [ram("X", 1, 0, [], ["e"]), ram("Y", 0, 1, [], ["s"]), mid, ram("E", 1, 2, ["w"], [])]
    g = fg.FlexGrid(recs, width=w)
    if mutate:
        mutate(g)
    for _ in range(4):
        g.tick()
    g.inject(1, 0, a)
    for _ in range(8):
        g.tick()
    g.inject(0, 1, b)
    for _ in range(30):
        g.tick()
    e = g.cells[(1, 2)]
    return e.ram_data_reg if e.ram_data_valid else None


@pytest.mark.parametrize("kind", ["add", "sub", "mul"])
@pytest.mark.parametrize("w", WIDTHS)
def test_flexgrid_equals_the_real_rtl_at_every_width(kind, w, tmp_path):
    cases = pairs(w)
    rtl = rtl_results(kind, w, cases, tmp_path)
    bad = []
    for a, b in cases:
        got = vm_result(kind, a, b, w)
        if got != rtl[(a, b)]:
            bad.append((hex(a), hex(b), "vm", None if got is None else hex(got), "rtl", hex(rtl[(a, b)])))
    assert not bad, f"{kind} width {w}: {len(bad)} of {len(cases)} differ, first: {bad[:3]}"


@pytest.mark.parametrize("kind", ["sub", "mul"])
def test_the_comparison_bites_a_mask_forced_to_32_bits_disagrees_at_width_18(kind, tmp_path):
    w = 18
    cases = pairs(w)
    rtl = rtl_results(kind, w, cases, tmp_path)

    def widen(g):
        g.mask = 0xFFFFFFFF
        g.width = 32
        for c in g.cells.values():
            c.mask = 0xFFFFFFFF
            c.width = 32
    wrong = sum(1 for a, b in cases if vm_result(kind, a, b, w, mutate=widen) != rtl[(a, b)])
    assert wrong > 0, "forcing 32 bits changed nothing: the test would not catch a missing width"


def test_a_swapped_operand_order_is_caught_by_subtract(tmp_path):
    w = 18
    cases = [(a, b) for a, b in pairs(w) if a != b]
    rtl = rtl_results("sub", w, cases, tmp_path)
    assert sum(1 for a, b in cases if vm_result("sub", b, a, w) != rtl[(a, b)]) > 0, "subtract with operands swapped matched the RTL: order is not being checked"
