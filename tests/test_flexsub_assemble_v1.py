#!/usr/bin/env python3
"""tests/test_flexsub_assemble_v1.py -- Flex-Sub assembler, step 1 (-s flex/sub/nano, -w).

Run: python3 tests/test_flexsub_assemble_v1.py   (not pytest -- same convention as the rest of tests/)
Needs iverilog and yosys for the elaboration/synthesis checks; those two are SKIPPED (stated, not
silently passed) when the tool is missing.
"""
import filecmp
import json
import os
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
TB = """`timescale 1ns/1ps
module tb;
  reg clk = 0, rstn = 0, entry = 0; wire l0, l1, l2;
  `TOP dut (.BOARD_CLK(clk), .BTN_RST_N(rstn), .BTN_ENTRY(entry), .LED0_N(l0), .LED1_N(l1), .LED2_N(l2));
  always #5 clk = ~clk;
  integer xs = 0, t0 = 0; reg p0 = 1;
  always @(posedge clk) begin
    if (rstn && (^{l0, l1, l2} === 1'bx)) xs = xs + 1;
    if (l0 !== p0) t0 = t0 + 1; p0 <= l0;
  end
  initial begin #200 rstn = 1; #400000; $display("RESULT xs=%0d t0=%0d", xs, t0); $finish; end
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
                      ("width 65 rejected", lambda: fsa.resolve_width("flex", 65, None))):
        try:
            fn()
            check(label, False, "no error raised")
        except ValueError:
            check(label, True)
    check("sub is fixed 32", fsa.resolve_width("sub", None, None)[0] == 32)

    print("CLI generation")
    cases = {"a": ("flex", "adder", ["--man", TANG]), "b": ("flex", "adder", ["-w", "18"]),
             "c": ("sub", "adder", ["--man", TANG]), "d": ("flex", "compare", ["--man", TANG, "-w", "9"])}
    for k, (fam, cell, extra) in cases.items():
        r = cli("-s", fam, "-S", cell, "--cells", "4", "--output", os.path.join(tmp, k), *extra)
        check(f"{fam}/{cell} {extra[-2:]} generates", r.returncode == 0, r.stderr.strip())
    a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
    ta = open(os.path.join(a, "flexsub_adder_v4sa_n4_w18.v")).read()
    tb_ = open(os.path.join(b, "flexsub_adder_v4sa_n4_w18.v")).read()
    check("MAN width and -w 18 give the identical top", ta == tb_)
    check("Gowin MAN yields a .cst; no MAN does not",
          os.path.exists(os.path.join(a, "flexsub_adder_v4sa_n4_w18.cst"))
          and not os.path.exists(os.path.join(b, "flexsub_adder_v4sa_n4_w18.cst")))
    check("adder folder carries adder_v1.v (shared primitive from fpga/verilog)",
          os.path.exists(os.path.join(a, "adder_v1.v")))
    for label, args in (("flex without --man/-w", ["-s", "flex", "-S", "adder"]),
                        ("unsupported cell", ["--man", TANG, "-s", "flex", "-S", "branch"]),
                        ("flex without -S", ["--man", TANG, "-s", "flex"]),
                        ("-w with sub", ["--man", TANG, "-s", "sub", "-S", "adder", "-w", "18"]),
                        ("shell option with flex", ["--man", TANG, "-s", "flex", "-S", "adder", "--logiclock"])):
        r = cli(*args, "--cells", "4", "--output", os.path.join(tmp, "err"))
        check(f"error: {label}", r.returncode != 0 and "error:" in r.stderr, r.stderr.strip())
    r = cli("--cells", "4", "--output", os.path.join(tmp, "err"))
    check("default path still requires --man (same message as before)",
          r.returncode == 2 and "the following arguments are required: --man" in r.stderr)
    r = cli("--man", MUSTANG, "--cells", "4", "--output", os.path.join(tmp, "err"), "-w", "18")
    check("-w without -s flex is rejected on the default path", r.returncode == 2 and "only applies with -s flex" in r.stderr)

    print("-s nano == default (existing behaviour untouched)")
    r1 = cli("--man", MUSTANG, "--cells", "10", "--output", os.path.join(tmp, "n_def"))
    r2 = cli("--man", MUSTANG, "--cells", "10", "-s", "nano", "--output", os.path.join(tmp, "n_exp"))
    cmp_ = filecmp.dircmp(os.path.join(tmp, "n_def"), os.path.join(tmp, "n_exp"))
    check("-s nano output identical to default", r1.returncode == 0 and r2.returncode == 0
          and not (cmp_.diff_files or cmp_.left_only or cmp_.right_only))

    print("elaboration + simulation (iverilog)")
    if not have("iverilog"):
        skipped += 1
        print("  SKIP  iverilog not installed")
    else:
        open(os.path.join(tmp, "tb.v"), "w").write(TB)
        for k in cases:
            rec = json.load(open(os.path.join(tmp, k, "ASSEMBLY.json")))
            vs = [f for f in rec["files"] if f.endswith(".v")]
            exe = os.path.join(tmp, f"{k}.vvp")
            c = subprocess.run(["iverilog", "-g2012", f"-DTOP={rec['top']}", "-o", exe, os.path.join(tmp, "tb.v"), *vs],
                               cwd=os.path.join(tmp, k), capture_output=True, text=True)
            ok = c.returncode == 0
            res = subprocess.run(["vvp", exe], capture_output=True, text=True).stdout if ok else ""
            check(f"{rec['top']}: folder is self-contained and elaborates", ok, c.stderr.strip()[:200])
            check(f"{rec['top']}: no X on outputs after reset", "xs=0" in res, res.strip())

    print("synthesis equals the hand-built reference (yosys synth_gowin)")
    if not have("yosys"):
        skipped += 1
        print("  SKIP  yosys not installed")
    else:
        def stat(ys_args, cwd):
            out = subprocess.run(["yosys", "-p", ys_args], cwd=cwd, capture_output=True, text=True).stdout
            tail = out.split("Number of cells")[-1]
            c = {}
            for line in tail.splitlines():
                p = line.split()
                if len(p) == 2 and p[1].isdigit():
                    c[p[0]] = int(p[1])
            return (sum(v for k, v in c.items() if k.startswith("LUT")), c.get("ALU"),
                    sum(v for k, v in c.items() if k.startswith("DFF")))
        gen = os.path.join(tmp, "n100")
        cli("--man", TANG, "-s", "flex", "-S", "adder", "--cells", "100", "--output", gen)
        rec = json.load(open(os.path.join(gen, "ASSEMBLY.json")))
        g = stat(f"read_verilog -sv {' '.join(f for f in rec['files'] if f.endswith('.v'))}; "
                 f"hierarchy -top {rec['top']}; synth_gowin -top {rec['top']} -json /dev/null; stat", gen)
        sv = os.path.join(ROOT, "sub", "verilog")
        ref = stat(f"read_verilog -sv {sv}/adder_chain_v4sa_top100_width18.v {sv}/adder_chain_v4sa.v "
                   f"{sv}/adder_cell_v4sa.v {ROOT}/fpga/verilog/adder_v1.v; "
                   f"hierarchy -top adder_chain_v4sa_top100_width18; "
                   f"synth_gowin -top adder_chain_v4sa_top100_width18 -json /dev/null; stat", ROOT)
        check("generated 100-cell W=18 chain == hand-built reference (LUT1-4, ALU, DFF)", g == ref, f"{g} vs {ref}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
sys.exit(1 if failed else 0)
