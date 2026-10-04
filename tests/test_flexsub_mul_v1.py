#!/usr/bin/env python3
"""tests/test_flexsub_mul_v1.py -- the multiplier fall back ladder on the sub family (Alan #941).

Run: python3 tests/test_flexsub_mul_v1.py      (needs llvmlite, iverilog, yosys)
Alan: "the mul side has to be taken into account as a fall back if the card resources are used." A `mul` is realised as the DSP cell
(mul_cell_v4s_dsp2: one MULT36X36, a few dozen LUTs) while the card has DSP blocks left, as the exact LUT multiplier (mul_cell_v4s, ~4,277 LUT4)
as the fall back, and refused if even that cannot fit. The two are drop-in: same ports, exact low-32-bit product, the same ONE cycle of latency.
mul_cell_v4s_dsp3 (time-multiplexed, 4 cycles) is deliberately NOT in the ladder: it would drop the whole design's item rate.
Layers: (1) the cells are cycle-for-cycle identical; (2) the ladder arithmetic and refusals, including the boundary; (3) the generated hardware is
right under each realisation; (4) real synthesis shows the DSP blocks actually used and the LUTs actually paid.
"""
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("nano", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
SUBV = os.path.join(ROOT, "sub", "verilog")
TANG = os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json")
MUSTANG = os.path.join(ROOT, "docs", "man", "mustang-f100-a10.man.json")
CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
M = 0xFFFFFFFF
passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def cli(*a):
    return subprocess.run(CLI + list(a), capture_output=True, text=True)


def mult_stub(path):
    """The repo's own sim-only behavioural MULT36X36 (yosys ships none, #901/#902), pulled from the testbench that carries it."""
    t = open(os.path.join(SUBV, "tb_mul_cell_v4sa_dsp.v")).read()
    open(path, "w").write("`timescale 1ns/1ps\n" + re.search(r"module MULT36X36\b.*?endmodule", t, re.S).group(0) + "\n")


def man_with(tmp, name, blocks=None, lut4=None):
    m = json.load(open(TANG))
    if blocks is not None:
        m["device"]["dsp"]["total_blocks"] = blocks
    if lut4 is not None:
        m["device"]["logic"]["lut4_total"] = lut4
    path = os.path.join(tmp, name + ".man.json")
    json.dump(m, open(path, "w"))
    return path


def simulate(folder, port_values, stub):
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
    outs = re.findall(r"output\s+wire\s+\[31:0\]\s+out_(\w+)_data", text)
    key = lambda cid: re.sub(r"[^A-Za-z0-9_]", "_", cid)  # noqa: E731
    vals = {key(c): v for c, v in port_values.items() if key(c) in ins}
    assert sorted(ins) == sorted(vals) and len(outs) == 1, (ins, list(vals), outs)
    conn = ", ".join([f".in_{n}_data(d_{n}), .in_{n}_valid(v_{n})" for n in ins] + [f".out_{outs[0]}_data(od), .out_{outs[0]}_valid(ov)"])
    decl = "\n".join(f"  reg [31:0] d_{n} = 0; reg v_{n} = 0;" for n in ins)
    drive = " ".join(f"d_{n} = 32'd{vals[n]}; v_{n} = 1;" for n in ins)
    clear = " ".join(f"v_{n} = 0; d_{n} = 0;" for n in ins)
    settle = int(rec["settle_cycles"])
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
    repeat ({settle + 3}) @(posedge clk); #1;
    for (c = 0; c < 70; c = c + 1) begin
      {clear}
      if (c == 0) begin {drive} end
      #3 $display("OUT %0d %0d %0d", c, ov, od);
      @(posedge clk); #1;
    end
    $finish;
  end
endmodule
"""
    open(os.path.join(folder, "tb_gen.v"), "w").write(tb)
    files = [f for f in rec["files"] if f.endswith(".v")] + ([stub] if rec["multipliers"]["dsp2"] else [])
    c = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(folder, "tb.vvp"), "tb_gen.v", *files], cwd=folder, capture_output=True, text=True)
    if c.returncode:
        raise RuntimeError(c.stderr[:300])
    out = subprocess.run(["vvp", os.path.join(folder, "tb.vvp")], capture_output=True, text=True).stdout
    return [(int(a), int(d)) for a, v, d in re.findall(r"OUT (\d+) (\d+) (\d+)", out) if v == "1"]


def synth_counts(folder):
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    files = [f for f in rec["files"] if f.endswith(".v")]
    out = subprocess.run(["yosys", "-p", f"read_verilog -sv {' '.join(files)}; hierarchy -top {rec['top']}; synth_gowin -top {rec['top']} -json /dev/null; stat"],
                         cwd=folder, capture_output=True, text=True, timeout=600).stdout
    c = {}
    for line in out.split("Number of cells")[-1].splitlines():
        p = line.split()
        if len(p) == 2 and p[1].isdigit():
            c[p[0]] = int(p[1])
    return sum(v for k, v in c.items() if k.startswith("LUT")), c.get("MULT36X36", 0)


try:
    import llvmlite  # noqa: F401
except ImportError:
    print("SKIP: llvmlite not installed")
    sys.exit(0)
if not (shutil.which("iverilog") and shutil.which("yosys")):
    print("SKIP: iverilog and yosys are both needed")
    sys.exit(0)
import flexsub_compile_v1 as fc  # noqa: E402
import flexsub_icm_generate_v1 as gen  # noqa: E402

SRC = ("define i32 @f(i32 %x, i32 %y, i32 %z) {\nentry:\n  %a = mul i32 %x, %y\n  %b = mul i32 %y, %z\n  %c = mul i32 %z, %x\n"
       "  %s = add i32 %a, %b\n  %r = add i32 %s, %c\n  ret i32 %r\n}\n")
tmp = tempfile.mkdtemp(prefix="mul_")
try:
    stub = os.path.join(tmp, "mult36_stub.v")
    mult_stub(stub)

    print("1. the two cells are drop-in: cycle-for-cycle identical on edge and random operands (one cycle of latency each)")
    rnd = random.Random(941)
    ops = [(0, 0), (1, 1), (M, M), (0x80000000, 2), (0x7FFFFFFF, 0x7FFFFFFF), (0x10000, 0x10000), (123456789, 987654321), (M, 1), (0x80000000, 0x80000000)] + \
          [(rnd.getrandbits(32), rnd.getrandbits(32)) for _ in range(300)]
    lines = "\n".join(f"      a = 32'h{x:08X}; b = 32'h{y:08X}; v = {1 if (k % 3) else 0}; @(posedge clk); #1; chk();" for k, (x, y) in enumerate(ops))
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg_valid = 0; always #5 clk = ~clk;
  reg [31:0] a = 0, b = 0; reg v = 0; wire [31:0] dl, dd; wire vl, vd;
  mul_cell_v4s      L (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(32'h0), .in_a(a), .in_b(b), .valid_in(v), .data_out(dl), .valid_out(vl));
  mul_cell_v4s_dsp2 D (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(32'h0), .in_a(a), .in_b(b), .valid_in(v), .data_out(dd), .valid_out(vd));
  integer bad = 0, n = 0, pulses = 0;
  task chk; begin n = n + 1; if (vl !== vd) bad = bad + 1; else if (vl && (dl !== dd)) bad = bad + 1; if (vl) pulses = pulses + 1; end endtask
  initial begin repeat (3) @(posedge clk); #1 rst = 0; @(posedge clk); #1 cfg_valid = 1; @(posedge clk); #1 cfg_valid = 0; @(posedge clk); #1;
{lines}
    $display("EQV n=%0d bad=%0d pulses=%0d", n, bad, pulses); $finish; end
endmodule
"""
    open(os.path.join(tmp, "eqv.v"), "w").write(tb)
    files = [f"{SUBV}/mul_cell_v4s.v", f"{SUBV}/mul_cell_v4s_dsp2.v", stub, os.path.join(ROOT, "fpga", "verilog", "bitwise_multiplier_32bit.v")]
    c = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(tmp, "eqv.vvp"), os.path.join(tmp, "eqv.v"), *files], capture_output=True, text=True)
    m = re.search(r"EQV n=(\d+) bad=(\d+) pulses=(\d+)", subprocess.run(["vvp", os.path.join(tmp, "eqv.vvp")], capture_output=True, text=True).stdout) if c.returncode == 0 else None
    check(f"mul_cell_v4s_dsp2 == mul_cell_v4s over {m.group(1) if m else '?'} cycles ({m.group(3) if m else '?'} results): identical valid and data -- a drop-in",
          m is not None and m.group(2) == "0" and int(m.group(3)) > 150, c.stderr[:200] if not m else m.group(0))

    file, report, _ = fc.compile_for_flexsub(SRC, "mul3")
    icm = os.path.join(tmp, "mul3.icm")
    file.save(icm)

    print("2. the ladder: DSP while blocks last, LUT as the fall back, a refusal when even that cannot fit")
    cases = [
        ("Tang MAN (12 DSP blocks): all 3 DSP", ["--man", TANG], 3, 0),
        ("2 DSP blocks left: 2 DSP + 1 LUT fall back", ["--man", man_with(tmp, "b2", blocks=2)], 2, 1),
        ("0 DSP blocks: all 3 LUT", ["--man", man_with(tmp, "b0", blocks=0)], 0, 3),
        ("no MAN: no resource information -> the always-exact LUT multiplier", [], 0, 3),
        ("a non-Gowin card (Arria 10): MULT36X36 is a Gowin primitive -> LUT", ["--man", MUSTANG], 0, 3),
        ("--mul lut forces LUT even with 12 blocks", ["--man", TANG, "--mul", "lut"], 0, 3),
    ]
    dirs = {}
    for label, extra, n_dsp, n_lut in cases:
        d = os.path.join(tmp, "g_" + re.sub(r"\W+", "_", label)[:30])
        r = cli("-s", "sub", "--icm", icm, "--output", d, *extra)
        if r.returncode:
            check(label, False, r.stderr.strip()[:240])
            continue
        mi = json.load(open(os.path.join(d, "ASSEMBLY.json")))["multipliers"]
        check(f"{label}  [{len(mi['dsp2'])} DSP, {len(mi['lut'])} LUT]", (len(mi["dsp2"]), len(mi["lut"])) == (n_dsp, n_lut), str(mi))
        dirs[label] = d
    for label, extra, needles in (
            ("--mul dsp with only 2 DSP blocks for 3 multipliers is refused", ["--man", man_with(tmp, "b2d", blocks=2), "--mul", "dsp"], ["only 2 DSP blocks"]),
            ("--mul dsp with no MAN is refused", ["--mul", "dsp"], ["Gowin MAN"]),
            ("0 DSP blocks and a 5,000-LUT4 card: 3 LUT multipliers (~12.8k) do not fit -> refused", ["--man", man_with(tmp, "tiny", blocks=0, lut4=5000)], ["resources are used up"]),
            ("1 DSP block + 2 LUT multipliers (8,554 LUT4) on a 9,500-LUT4 card (limit 8,550): refused by 4", ["--man", man_with(tmp, "edge_no", blocks=1, lut4=9500)], ["resources are used up"])):
        r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_ref"), *extra)
        check(label, r.returncode != 0 and all(n in r.stderr for n in needles), r.stderr.strip()[:260])
    r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_edge"), "--man", man_with(tmp, "edge_ok", blocks=1, lut4=9600))
    check("...and on a 9,600-LUT4 card (limit 8,640) the same 1 DSP + 2 LUT design is accepted: the boundary is where it says",
          r.returncode == 0, r.stderr.strip()[:200])

    print("3. the generated hardware is right under every realisation, with the same latency")
    lats = {}
    for label, d in dirs.items():
        rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
        lat = list(rec["output_latency_cycles"].values())[0]
        lats[label] = lat
        bad = []
        vecs = [dict(x=a, y=b, z=c) for a, b, c in ((0, 0, 0), (1, 2, 3), (M, M, M), (0x80000000, 2, 3), (123456, 654321, 99999))] + \
               [dict(x=rnd.getrandbits(32), y=rnd.getrandbits(32), z=rnd.getrandbits(32)) for _ in range(5)]
        for v in vecs:
            pv = {c: v[a] for a in v for c in report["arg_cells"][a]}
            want = (v["x"] * v["y"] + v["y"] * v["z"] + v["z"] * v["x"]) & M
            if simulate(d, pv, stub) != [(lat, want)]:
                bad.append(v)
        check(f"{label.split(':')[0]}: x*y + y*z + z*x == arithmetic on {len(vecs)} vectors (latency {lat})", not bad, str(bad[:1]))
    check("every realisation has the SAME latency (the DSP cell is a true drop-in)", len(set(lats.values())) == 1, str(lats))

    print("4. real synthesis (yosys synth_gowin): the DSP blocks actually used, the LUTs actually paid")
    for label, want_dsp, lut_lo, lut_hi in (("Tang MAN (12 DSP blocks): all 3 DSP", 3, 0, 2500),
                                            ("2 DSP blocks left: 2 DSP + 1 LUT fall back", 2, 4000, 7500),
                                            ("0 DSP blocks: all 3 LUT", 0, 11000, 16000)):
        luts, dsps = synth_counts(dirs[label])
        check(f"{label.split(':')[0]}: {dsps} MULT36X36 primitives (want {want_dsp}), {luts} LUT1-4 (expected {lut_lo}..{lut_hi})",
              dsps == want_dsp and lut_lo <= luts <= lut_hi, f"dsps={dsps} luts={luts}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
