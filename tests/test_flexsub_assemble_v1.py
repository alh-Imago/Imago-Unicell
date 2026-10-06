#!/usr/bin/env python3
"""tests/test_flexsub_assemble_v1.py -- Flex-Sub assembler (-s flex/sub/nano, -w), step 1.

Run: python3 tests/test_flexsub_assemble_v1.py   (not pytest -- same convention as the rest of tests/)
Needs iverilog and yosys for the elaboration/synthesis checks; those are SKIPPED (stated, not
silently passed) when the tool is missing.

Covers: width resolution (#914), CLI error paths, the existing assembler untouched (-s nano ==
default), EVERY supported cell in BOTH families generated + elaborated + simulated (X-free, live),
the real-port-list guard, a generated chain == the hand-built reference under synthesis, and the
generated folders' cell files reproducing the per-cell costs recorded in the ledger/README.
"""
import copy
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_assemble_v1 as fsa  # noqa: E402

CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
TANG = os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json")
MUSTANG = os.path.join(ROOT, "docs", "man", "mustang-f100-a10.man.json")
SUBV = os.path.join(ROOT, "sub", "verilog")
# Testbench: no X on the pins or on the FIRST cell's output after reset, and that output must move
# (probes the generated top's own stage arrays, which every kind -- chain/source/split -- defines).
TB = """`timescale 1ns/1ps
module tb;
  reg clk = 0, rstn = 0, entry = 0; wire l0, l1, l2;
  `TOP dut (.BOARD_CLK(clk), .BTN_RST_N(rstn), .BTN_ENTRY(entry), .LED0_N(l0), .LED1_N(l1), .LED2_N(l2));
  always #5 clk = ~clk;
  wire [63:0] probe = {dut.stage_valid[1], dut.stage_data[1]};
  reg [63:0] pp = 0; integer xs = 0, act = 0;
  always @(posedge clk) begin
    if (rstn && ((^{l0, l1, l2}) === 1'bx || (^probe) === 1'bx)) xs = xs + 1;
    if (rstn && probe !== pp) act = act + 1;
    pp <= probe;
  end
  initial begin #200 rstn = 1; #400000; $display("RESULT xs=%0d act=%0d", xs, act); $finish; end
endmodule
"""
passed = failed = skipped = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def cli(*args):
    return subprocess.run(CLI + list(args), capture_output=True, text=True)


def have(tool):
    return shutil.which(tool) is not None


def mult_stubs(path):
    """The repo's own sim-only behavioural MULT36X36/MULT18X18 stand-ins (yosys ships none, #901/#902),
    pulled from the testbenches that already carry them."""
    out = ["`timescale 1ns/1ps"]
    for f, mod in (("tb_mul_cell_v4sa_dsp.v", "MULT36X36"), ("tb_mul_cell_v4s_dsp3.v", "MULT18X18")):
        out.append(re.search(rf"module {mod}\b.*?endmodule", open(os.path.join(SUBV, f)).read(), re.S).group(0))
    open(path, "w").write("\n\n".join(out) + "\n")


def synth_stat(files, top, cwd, chparam=""):
    out = subprocess.run(["yosys", "-p", f"read_verilog -sv {' '.join(files)}; {chparam} hierarchy -top {top}; "
                          f"synth_gowin -top {top} -json /dev/null; stat"], cwd=cwd, capture_output=True, text=True).stdout
    c = {}
    for line in out.split("Number of cells")[-1].splitlines():
        p = line.split()
        if len(p) == 2 and p[1].isdigit():
            c[p[0]] = int(p[1])
    return (sum(v for k, v in c.items() if k.startswith("LUT")), c.get("ALU", 0),
            sum(v for k, v in c.items() if k.startswith("DFF")), sum(v for k, v in c.items() if k.startswith("MULT")))


tmp = tempfile.mkdtemp(prefix="flexsub_test_")
try:
    print("width resolution (#914 contract)")
    man = fsa.load_man_flexsub(TANG)
    check("MAN native_width is 18", man["native_width"] == 18, str(man["native_width"]))
    check("MAN supplies width when no -w", fsa.resolve_width("flex", None, man)[0] == 18)
    check("-w overrides MAN", fsa.resolve_width("flex", 9, man)[0] == 9)
    check("no MAN + -w works", fsa.resolve_width("flex", 18, None)[0] == 18)
    check("MAN without field falls back to 32", fsa.resolve_width("flex", None, dict(man, native_width=None))[0] == 32)
    for label, fn in (("no MAN and no -w is an error", lambda: fsa.resolve_width("flex", None, None)),
                      ("-w rejected for sub", lambda: fsa.resolve_width("sub", 18, None)),
                      ("width 0 rejected", lambda: fsa.resolve_width("flex", 0, None)),
                      ("width 65 rejected", lambda: fsa.resolve_width("flex", 65, None)),
                      ("width above a cell's hardware ceiling rejected", lambda: fsa.resolve_width("flex", 40, None, 36))):
        try:
            fn()
            check(label, False, "no error raised")
        except ValueError:
            check(label, True)
    check("sub is fixed 32", fsa.resolve_width("sub", None, None)[0] == 32)

    print("name handling")
    for given, want in (("adder", "adder"), ("adder_cell", "adder"), ("adder_cell_v4sa", "adder"),
                        ("mul_cell_v4sa_dsp", "mul_dsp"), ("mul_dsp3", "mul_dsp3"), ("shift_stage_v4s", "shift_stage")):
        check(f"normalise {given!r} -> {want!r}", fsa.normalise_cell_name(given) == want, fsa.normalise_cell_name(given))
    check("flex has 13 cells, sub has 16 (branch_cell_v4s completes the sub set)", len(fsa.cells_for("flex")) == 13 and len(fsa.cells_for("sub")) == 16,
          f"{len(fsa.cells_for('flex'))}/{len(fsa.cells_for('sub'))}")

    print("CLI generation + error paths")
    cases = {"a": ("flex", "adder", ["--man", TANG]), "b": ("flex", "adder", ["-w", "18"]),
             "c": ("sub", "adder", ["--man", TANG]), "d": ("flex", "compare", ["--man", TANG, "-w", "9"])}
    for k, (fam, cell, extra) in cases.items():
        r = cli("-s", fam, "-S", cell, "--cells", "4", "--output", os.path.join(tmp, k), *extra)
        check(f"{fam}/{cell} {extra[-2:]} generates", r.returncode == 0, r.stderr.strip())
    a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
    check("MAN width and -w 18 give the identical top",
          open(os.path.join(a, "flexsub_adder_v4sa_n4_w18.v")).read() == open(os.path.join(b, "flexsub_adder_v4sa_n4_w18.v")).read())
    check("Gowin MAN yields a .cst; no MAN does not",
          os.path.exists(os.path.join(a, "flexsub_adder_v4sa_n4_w18.cst"))
          and not os.path.exists(os.path.join(b, "flexsub_adder_v4sa_n4_w18.cst")))
    check("adder folder carries adder_v1.v (shared primitive from fpga/verilog)", os.path.exists(os.path.join(a, "adder_v1.v")))
    for label, args in (("flex without --man/-w", ["-s", "flex", "-S", "adder"]),
                        ("unsupported cell (command)", ["--man", TANG, "-s", "flex", "-S", "command"]),
                                                ("cell not in this family (shift is sub-only)", ["--man", TANG, "-s", "flex", "-S", "shift"]),
                        ("flex without -S", ["--man", TANG, "-s", "flex"]),
                        ("-w with sub", ["--man", TANG, "-s", "sub", "-S", "adder", "-w", "18"]),
                        ("mul_dsp above its 36-bit ceiling", ["--man", TANG, "-s", "flex", "-S", "mul_dsp", "-w", "40"]),
                        ("shell option with flex", ["--man", TANG, "-s", "flex", "-S", "adder", "--logiclock"])):
        r = cli(*args, "--cells", "4", "--output", os.path.join(tmp, "err"))
        check(f"error: {label}", r.returncode != 0 and "error:" in r.stderr, r.stderr.strip())
    r = cli("--cells", "4", "--output", os.path.join(tmp, "err"))
    check("default path still requires --man (same message as before)",
          r.returncode == 2 and "the following arguments are required: --man" in r.stderr)
    r = cli("--man", MUSTANG, "--cells", "4", "--output", os.path.join(tmp, "err"), "-w", "18")
    check("-w without -s flex is rejected on the default path", r.returncode == 2 and "only applies with -s flex" in r.stderr)

    print("real-port-list guard (a wrong shape fails loudly, never silently)")
    saved = copy.deepcopy(fsa.SHAPES)
    try:
        fsa.SHAPES["adder"]["in_data"] = "in_x"                       # a port the cell does not have
        try:
            fsa.check_ports("adder", "flex", os.path.join(SUBV, "adder_cell_v4sa.v"), "adder_cell_v4sa")
            check("bogus port name is caught", False, "no error")
        except ValueError as e:
            check("bogus port name is caught", "in_x" in str(e) and "in_a" in str(e), str(e)[:160])
        fsa.SHAPES["adder"] = copy.deepcopy(saved["adder"]); fsa.SHAPES["adder"]["stim_data"] = []   # leaves in_b unconnected
        try:
            fsa.check_ports("adder", "flex", os.path.join(SUBV, "adder_cell_v4sa.v"), "adder_cell_v4sa")
            check("an unconnected real input is caught", False, "no error")
        except ValueError as e:
            check("an unconnected real input is caught", "in_b" in str(e), str(e)[:160])
    finally:
        fsa.SHAPES.clear(); fsa.SHAPES.update(saved)
    bad = []
    for fam in fsa.FAMILIES:
        for cell in fsa.cells_for(fam):
            mod = fsa.cell_module(cell, fam)
            try:
                fsa.check_ports(cell, fam, os.path.join(SUBV, mod + ".v"), mod)
            except ValueError as e:
                bad.append(str(e)[:120])
    check("every shape in the table matches its cell's real module header (both families)", not bad, "; ".join(bad))

    print("-s nano == default (existing behaviour untouched)")
    r1 = cli("--man", MUSTANG, "--cells", "10", "--output", os.path.join(tmp, "n_def"))
    r2 = cli("--man", MUSTANG, "--cells", "10", "-s", "nano", "--output", os.path.join(tmp, "n_exp"))
    cmp_ = filecmp.dircmp(os.path.join(tmp, "n_def"), os.path.join(tmp, "n_exp"))
    check("-s nano output identical to default", r1.returncode == 0 and r2.returncode == 0
          and not (cmp_.diff_files or cmp_.left_only or cmp_.right_only))

    print("every cell, both families: generate, elaborate, simulate (X-free and live)")
    if not have("iverilog"):
        skipped += 1
        print("  SKIP  iverilog not installed")
    else:
        open(os.path.join(tmp, "tb.v"), "w").write(TB)
        mult_stubs(os.path.join(tmp, "mult_stubs.v"))
        matrix = {}
        for fam in fsa.FAMILIES:
            for cell in fsa.cells_for(fam):
                d = os.path.join(tmp, f"m_{fam}_{cell}")
                r = cli("--man", TANG, "-s", fam, "-S", cell, "--cells", "4", "--output", d)
                if r.returncode:
                    check(f"{fam}/{cell}: generates", False, r.stderr.strip())
                    continue
                rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
                matrix[(fam, cell)] = (d, rec)
                vs = [f for f in rec["files"] if f.endswith(".v")]
                extra = [os.path.join(tmp, "mult_stubs.v")] if rec.get("sim_note") else []
                exe = os.path.join(tmp, f"{fam}_{cell}.vvp")
                c = subprocess.run(["iverilog", "-g2012", f"-DTOP={rec['top']}", "-o", exe, os.path.join(tmp, "tb.v"), *vs, *extra],
                                   cwd=d, capture_output=True, text=True)
                if c.returncode:
                    check(f"{fam}/{cell}: folder is self-contained and elaborates", False, c.stderr.strip()[:200])
                    continue
                m = re.search(r"xs=(\d+) act=(\d+)", subprocess.run(["vvp", exe], capture_output=True, text=True).stdout)
                xs, act = (int(m.group(1)), int(m.group(2))) if m else (None, None)
                check(f"{fam}/{cell} (W={rec['width']}): self-contained, X-free, first cell live",
                      m is not None and xs == 0 and act > 0, f"xs={xs} act={act}")

    print("synthesis (yosys synth_gowin)")
    if not have("yosys"):
        skipped += 1
        print("  SKIP  yosys not installed")
    else:
        gen = os.path.join(tmp, "n100")
        cli("--man", TANG, "-s", "flex", "-S", "adder", "--cells", "100", "--output", gen)
        rec = json.load(open(os.path.join(gen, "ASSEMBLY.json")))
        g = synth_stat([f for f in rec["files"] if f.endswith(".v")], rec["top"], gen)
        ref = synth_stat([f"{SUBV}/adder_chain_v4sa_top100_width18.v", f"{SUBV}/adder_chain_v4sa.v",
                          f"{SUBV}/adder_cell_v4sa.v", f"{ROOT}/fpga/verilog/adder_v1.v"],
                         "adder_chain_v4sa_top100_width18", ROOT)
        check("generated 100-cell W=18 chain == hand-built reference (LUT1-4, ALU, DFF, MULT)", g == ref, f"{g} vs {ref}")

        # The generated folder's OWN files, bare cell as top with chparam (the ledger's convention), must
        # reproduce the figures recorded in the ledger/README. (A flattened stimulus harness is NOT a valid
        # per-cell cost for live-config cells -- shared-LFSR flops merge across stages -- so none is used here.)
        recorded = {("flex", "adder"): (23, 18, 21, 0), ("flex", "branch"): (201, 36, 69, 0),   # README / #918; flex nano 626 -> 627 LUT4 at #971 (the `armed` gate on capture costs one LUT4)
                    ("flex", "nano"): (627, 0, 48, 0), ("flex", "accumulator"): (242, 72, 63, 0),
                    ("sub", "adder"): (66, 32, 35, 0), ("sub", "nano"): (1117, 0, 76, 0),        # README / #917
                    ("sub", "shift"): (3261, 62, 46, 0), ("sub", "mul_dsp3"): (71, 32, 151, 1)}  # README
        if not matrix:
            skipped += 1
            print("  SKIP  per-cell cost guard needs the generated matrix (iverilog section)")
        for (fam, cell), want in recorded.items():
            if (fam, cell) not in matrix:
                continue
            d, rec = matrix[(fam, cell)]
            deps = [f for f in rec["files"] if f.endswith(".v") and f != rec["top"] + ".v"]
            cp = f"chparam -set WIDTH {rec['width']} {rec['cell_module']};" if fam == "flex" else ""
            got = synth_stat(deps, rec["cell_module"], d, cp)
            check(f"{fam}/{cell}: generated folder reproduces the recorded cost (LUT1-4, ALU, DFF, MULT)", got == want, f"{got} vs {want}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
sys.exit(1 if failed else 0)
