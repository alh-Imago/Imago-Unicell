"""tests/vm/flex_rtl_harness_v1.py -- helpers to generate a FLEX design from an ICM (tools/project_assemble_v1.py -s flex), run the generated RTL in iverilog with streamed inputs and read what each exit
receives. Copied (not imported: that file runs its checks at import) from tests/test_flexsub_flex_merge_v1.py (ledger #968+), so FlexGrid can be checked against the real generated hardware."""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for sub in ("nano", "nano/examples", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]


def cli(*a):
    return subprocess.run(CLI + list(a), capture_output=True, text=True)


def ram(cid, r, c, up, down, **kw):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down}, **kw)


def build(tmp, name, recs):
    icm = os.path.join(tmp, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    d = os.path.join(tmp, "g_" + name)
    return d, cli("-s", "flex", "--icm", icm, "--output", d)


def run_level(folder, streams, mode="plain", seed=1, settle=60, cycles=3000, serial=False):
    """streams: {entry port suffix: [values]} (lengths may DIFFER). mode: plain (items back-to-back, exit always ready) | stall (random input gaps + random exit stalls) |
    skewfirst / skewlast (the first / last input slow, to stagger them). Returns (levels {exit: per-cycle data}, got {exit: [values captured on valid&ack]})."""
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = sorted(set(re.findall(r"in_(\w+)_data", text)))
    outs = sorted(set(re.findall(r"out_(\w+)_data", text)))
    assert sorted(ins) == sorted(streams), (ins, list(streams))
    decl, drv, conn, dones = [], [], [], []
    for k, name in enumerate(ins):
        vals = streams[name]
        n = len(vals)
        decl.append(f"  reg [31:0] mem_{name} [0:{n}]; integer idx_{name} = 0; reg act_{name} = 0; wire ack_{name};\n"
                    f"  wire [31:0] d_{name} = (idx_{name} < {n}) ? mem_{name}[idx_{name}] : 32'h0;")
        decl.append("  initial begin " + " ".join(f"mem_{name}[{j}] = 32'd{v};" for j, v in enumerate(vals)) + " end")
        slow3 = f"(lfsr[{(3 * k + 2) % 31}] & lfsr[{(5 * k + 7) % 31}] & lfsr[{(2 * k + 13) % 31}])"
        gap = (f"(lfsr[{(3 * k + 2) % 31}] | lfsr[{(5 * k + 7) % 31}])" if mode == "stall" else
               slow3 if (mode == "skewfirst" and k == 0) or (mode == "skewlast" and k == len(ins) - 1) else "(1'b1)")
        gate = f"(got_n >= idx_{name})" if serial else gap                  # serial: the next item enters only once the previous RESULT has come out
        drv.append(f"      if (act_{name} && ack_{name}) begin idx_{name} <= idx_{name} + 1; act_{name} <= 1'b0; end\n"
                   f"      else if (!act_{name} && idx_{name} < {n} && {gate}) act_{name} <= 1'b1;")
        conn.append(f".in_{name}_data(d_{name}), .in_{name}_valid(act_{name}), .in_{name}_ack(ack_{name})")
        dones.append(f"idx_{name} >= {n}")
    cap = []
    for k, name in enumerate(outs):
        ready = f"lfsr[{(7 * k + 11) % 31}]" if mode == "stall" else "1'b1"
        decl.append(f"  wire [31:0] od_{name}; wire ov_{name}; wire oa_{name} = {ready};")
        cap.append(f'      $display("LV {name} %0d %0d", cyc, od_{name});\n'
                   f'      if (ov_{name} && oa_{name}) begin $display("GOT {name} %0d", od_{name}); got_n <= got_n + 1; end')
        conn.append(f".out_{name}_data(od_{name}), .out_{name}_valid(ov_{name}), .out_{name}_ack(oa_{name})")
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg_valid = 0;
  reg [31:0] lfsr = 32'h{(0xACE1 ^ (seed * 0x9E3779B1)) & 0xFFFFFFFF or 1:08X};
{chr(10).join(decl)}
  {top} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {', '.join(conn)});
  always #5 clk = ~clk;
  integer cyc = 0, post = 0, got_n = 0; reg started = 0;
  always @(posedge clk) begin
    lfsr <= {{lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]}};
    if (started) begin
      cyc <= cyc + 1;
{chr(10).join(drv)}
{chr(10).join(cap)}
      if ({' && '.join(dones)}) post <= post + 1;
      if (post > {settle} || cyc > {cycles}) $finish;
    end
  end
  initial begin
    repeat (4) @(posedge clk); #1 rst = 0;
    @(posedge clk); #1 cfg_valid = 1; @(posedge clk); #1 cfg_valid = 0;
    repeat (3) @(posedge clk); #1 started = 1;
  end
endmodule
"""
    open(os.path.join(folder, "tb_gen.v"), "w").write(tb)
    files = [f for f in rec["files"] if f.endswith(".v")]
    c = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(folder, "tb.vvp"), "tb_gen.v", *files], cwd=folder, capture_output=True, text=True)
    if c.returncode:
        raise RuntimeError(c.stderr[:400])
    out = subprocess.run(["vvp", os.path.join(folder, "tb.vvp")], capture_output=True, text=True).stdout
    levels = {o: [] for o in outs}
    got = {o: [] for o in outs}
    for o, cy, v in re.findall(r"LV (\w+) (\d+) (\d+)", out):
        levels[o].append(int(v))
    for o, v in re.findall(r"GOT (\w+) (\d+)", out):
        got[o].append(int(v))
    return levels, got


