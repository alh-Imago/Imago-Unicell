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


def man_with(tmp, name, blocks=None, lut4=None, bpi36=None, drop=None, abilities=None):
    """A copy of the Tang MAN with its DSP/logic data edited: block count, LUT4 total, the MULT36X36 blocks_per_instance, primitives removed by name."""
    m = json.load(open(TANG))
    d = m["device"]["dsp"]
    if blocks is not None:
        d["total_blocks"] = blocks
    if lut4 is not None:
        m["device"]["logic"]["lut4_total"] = lut4
    if bpi36 is not None:
        next(pr for pr in d["primitives"] if pr["name"] == "MULT36X36")["blocks_per_instance"] = bpi36
    if drop:
        d["primitives"] = [pr for pr in d["primitives"] if pr["name"] not in drop]
    if abilities is not None:
        d["abilities"] = abilities
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
        ("Tang MAN (12 blocks, MULT36X36 = 1 block): all 3 DSP", ["--man", TANG], 3, 0),
        ("2 DSP blocks left: 2 DSP + 1 LUT fall back", ["--man", man_with(tmp, "b2", blocks=2)], 2, 1),
        ("0 DSP blocks: all 3 LUT", ["--man", man_with(tmp, "b0", blocks=0)], 0, 3),
        ("no MAN: no resource information -> the always-exact LUT multiplier", [], 0, 3),
        ("the Arria 10 MAN lists no DSP primitives -> LUT (its MAN says so; not a vendor rule)", ["--man", MUSTANG], 0, 3),
        ("--mul lut forces LUT even with 12 blocks", ["--man", TANG, "--mul", "lut"], 0, 3),
        ("a MAN that lists only MULT18X18 (no MULT36X36): no cell uses it -> LUT", ["--man", man_with(tmp, "only18", drop=["MULT36X36"])], 0, 3),
        ("blocks_per_instance is READ from the MAN: 4 blocks, a 36x36 needs 2 -> 2 instances: 2 DSP + 1 LUT", ["--man", man_with(tmp, "bpi2", blocks=4, bpi36=2.0)], 2, 1),
        ("...and 2 blocks with a 36x36 needing half a block -> 4 instances: all 3 DSP", ["--man", man_with(tmp, "bpi_half", blocks=2, bpi36=0.5)], 3, 0),
        ("abilities in the MAN are carried and change nothing yet (no cell asks for one)",
         ["--man", man_with(tmp, "abil", abilities=[{"name": "shift", "note": "test entry"}])], 3, 0),
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
            ("--mul dsp with a card that can host only 2 MULT36X36 for 3 multipliers is refused", ["--man", man_with(tmp, "b2d", blocks=2), "--mul", "dsp"], ["can host only 2"]),
            ("--mul dsp with no MAN (or a MAN that does not list the primitive) is refused", ["--mul", "dsp"], ["list the MULT36X36 primitive"]),
            ("[--wide-lut: the default-flow cost, 4,277 LUT4 each] 0 DSP blocks and a 5,000-LUT4 card: 3 LUT multipliers (~12.8k) do not fit -> refused", ["--man", man_with(tmp, "tiny", blocks=0, lut4=5000), "--wide-lut"], ["resources are used up"]),
            ("[--wide-lut] 1 DSP block + 2 LUT multipliers (8,554 LUT4) on a 9,500-LUT4 card (limit 8,550): refused by 4", ["--man", man_with(tmp, "edge_no", blocks=1, lut4=9500), "--wide-lut"], ["resources are used up"]),
            # the NEW default flow (-nowidelut): the LUT multiplier costs at most ~1,398 LUT4 (a whole 3-multiplier + 2-adder design is 4,195, #949/#950)
            ("[default flow, 1,398 LUT4 each] 0 DSP blocks and a 3,000-LUT4 card: 3 LUT multipliers (4,194) do not fit -> refused", ["--man", man_with(tmp, "tiny_nw", blocks=0, lut4=3000)], ["resources are used up", "1398"]),
            ("[default flow] 1 DSP block + 2 LUT multipliers (2,796 LUT4) on a 3,100-LUT4 card (limit 2,790): refused by 6", ["--man", man_with(tmp, "edge_nw_no", blocks=1, lut4=3100)], ["resources are used up"])):
        r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_ref"), *extra)
        check(label, r.returncode != 0 and all(n in r.stderr for n in needles), r.stderr.strip()[:260])
    r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_edge"), "--man", man_with(tmp, "edge_ok", blocks=1, lut4=9600), "--wide-lut")
    check("[--wide-lut] ...and on a 9,600-LUT4 card (limit 8,640) the same 1 DSP + 2 LUT design is accepted: the boundary is where it says",
          r.returncode == 0, r.stderr.strip()[:200])
    r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_edge_nw"), "--man", man_with(tmp, "edge_nw_ok", blocks=1, lut4=3200))
    mi = json.load(open(os.path.join(tmp, "g_edge_nw", "ASSEMBLY.json")))["multipliers"] if r.returncode == 0 else {}
    check("[default flow] ...and on a 3,200-LUT4 card (limit 2,880) the same 1 DSP + 2 LUT design is accepted, and the record names the flow",
          r.returncode == 0 and mi.get("synth_flow") == "nowidelut", r.stderr.strip()[:200] + str(mi.get("synth_flow")))
    r = cli("-s", "sub", "--icm", icm, "--output", os.path.join(tmp, "g_flowrec"), "--man", man_with(tmp, "flowrec", blocks=0), "--wide-lut")
    mi = json.load(open(os.path.join(tmp, "g_flowrec", "ASSEMBLY.json")))["multipliers"] if r.returncode == 0 else {}
    check("--wide-lut records the OLD flow in the multiplier record (so the 4,277 cost is the one applied)", mi.get("synth_flow") == "default" and mi.get("lut_multiplier_cost_estimate") == 3 * 4277, str(mi))

    print("   the MAN is the SINGLE source of the card's DSP facts")
    import flexsub_assemble_v1 as fsa
    man = fsa.load_man_flexsub(TANG)
    decl = open("/usr/share/yosys/gowin/cells_xtra.v").read()
    got = {n: (int(re.search(rf"module {n} \(\.\.\.\);.*?input\s+\[(\d+):0\]\s+A\b", decl, re.S).group(1)) + 1) for n in ("MULT18X18", "MULT36X36")}
    check("the Tang MAN's DSP primitives equal what yosys itself declares (operand widths 18 and 36), so it cannot drift from the toolchain",
          {n: man["dsp_primitives"][n]["operands"] for n in got} == {n: [w, w] for n, w in got.items()}, str(man["dsp_primitives"]))
    check("the sharing is recorded as DERIVED, with its arithmetic (a 36x36 uses (36/18)^2 = 4 of a block's 4 multipliers = 1 block)",
          man["dsp_primitives"]["MULT36X36"]["blocks_per_instance"] == 1.0 and man["dsp_primitives"]["MULT18X18"]["blocks_per_instance"] == 0.25
          and "DERIVED" in man["dsp_primitives"]["MULT36X36"]["blocks_per_instance_provenance"])
    a10 = fsa.load_man_flexsub(MUSTANG)
    check("the Arria 10 MAN: 1,687 DSP blocks recorded, NO primitives listed, an abilities list present but EMPTY (nothing is invented about its shift option)",
          a10["dsp_blocks"] == 1687 and a10["dsp_primitives"] == {} and a10["dsp_abilities"] == [], str((a10["dsp_blocks"], a10["dsp_primitives"], a10["dsp_abilities"])))
    a10man = json.load(open(MUSTANG))["device"]["dsp"]
    check("the Arria 10 MAN does NOT assert a DSP shift ability: the note carries the CORRECTION (it came from a possibly garbled voice message, no record exists)",
          a10man["abilities"] == [] and "CORRECTION" in a10man["abilities_note"] and "no record" in a10man["abilities_note"].lower().replace("has no record", "no record"), a10man["abilities_note"][:120])
    su = a10man["soft_units"][0]
    check("the known-working SOFT DSP is recorded on the Arria 10 (ledger #472): zero hard DSP blocks used, verified on actual hardware, and flagged as floating point -- not an integer multiplier",
          "ZERO" in su["kind"] and "#472" in su["provenance"] and "568 ALM" in su["verified_on_actual_hardware"] and "NOT an integer multiplier" in su["function_note"], str(su)[:160])
    check("the Arria 10's logic unit is read as ALM from its MAN (no vendor assumption), so the LUT4 cost cannot be applied", a10["logic_unit"] == "ALM" and man["logic_unit"] == "LUT4")
    ra = json.load(open(os.path.join(dirs["the Arria 10 MAN lists no DSP primitives -> LUT (its MAN says so; not a vendor rule)"], "ASSEMBLY.json")))["multipliers"]
    check("the record says WHY and that the LUT budget could not be checked for an ALM card (no measured ALM cost for the LUT multiplier)",
          "does not list MULT36X36" in ra["reason"] and "cannot be checked" in ra["lut_budget"], str(ra))
    ab = json.load(open(os.path.join(dirs["abilities in the MAN are carried and change nothing yet (no cell asks for one)"], "ASSEMBLY.json")))["multipliers"]
    check("a MAN's abilities are carried into the record for a cell to ask for by name", ab["dsp_abilities_in_man"] == [{"name": "shift", "note": "test entry"}], str(ab["dsp_abilities_in_man"]))

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
    for label, want_dsp, lut_lo, lut_hi in (("Tang MAN (12 blocks, MULT36X36 = 1 block): all 3 DSP", 3, 0, 2500),
                                            ("2 DSP blocks left: 2 DSP + 1 LUT fall back", 2, 4000, 7500),
                                            ("0 DSP blocks: all 3 LUT", 0, 11000, 16000)):
        luts, dsps = synth_counts(dirs[label])
        check(f"{label.split(':')[0]}: {dsps} MULT36X36 primitives (want {want_dsp}), {luts} LUT1-4 (expected {lut_lo}..{lut_hi})",
              dsps == want_dsp and lut_lo <= luts <= lut_hi, f"dsps={dsps} luts={luts}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
