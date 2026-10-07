#!/usr/bin/env python3
"""tests/test_flexsub_icm_generate_v1.py -- ICM-VIX -> sub Verilog (Flex-Sub assembler step 2, slice 2).

Run: python3 tests/test_flexsub_icm_generate_v1.py     (needs iverilog; yosys optional)
The load-bearing checks simulate the GENERATED RTL and compare it with the answer the VM itself gives for
the same inputs, plus a negative control (--no-align) proving the latency padding is what makes it right.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("nano", "tools", ""):
    sys.path.insert(0, os.path.join(ROOT, sub) if sub else ROOT)
import flexsub_icm_netlist_v1 as nl  # noqa: E402
import unicell_super_automaton_v1 as vm  # noqa: E402

EX = os.path.join(ROOT, "nano", "examples")
CLI = [sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py")]
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


def simulate(folder, values, names=None):
    """Drive 1-cycle valid pulses per input, record the output every cycle. `values` is ONE input set
    (list of ints, injected at cycle 0) or a LIST of sets injected on consecutive cycles (back-to-back
    items). Returns [(cycle, valid, data)]; cycle 0 = the first cycle an input valid is high."""
    sets = [values] if values and not isinstance(values[0], list) else values
    rec = json.load(open(os.path.join(folder, "ASSEMBLY.json")))
    top = rec["top"]
    text = open(os.path.join(folder, top + ".v")).read()
    ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
    outs = re.findall(r"output\s+wire\s+\[31:0\]\s+out_(\w+)_data", text)
    if names:                                   # values are given in `names` order -> reorder to the top's own port order
        sets = [[st[names.index(n)] for n in ins] for st in sets]
    assert all(len(st) == len(ins) for st in sets) and len(outs) == 1, (ins, outs)
    conn = ", ".join([f".in_{n}_data(d_{n}), .in_{n}_valid(v_{n})" for n in ins] + [f".out_{outs[0]}_data(od), .out_{outs[0]}_valid(ov)"])
    decl = "\n".join(f"  reg [31:0] d_{n} = 0; reg v_{n} = 0;" for n in ins)
    drive = "\n".join(
        f"      if (c == {k}) begin " + " ".join(f"d_{n} = 32'd{val}; v_{n} = 1;" for n, val in zip(ins, st)) + " end"
        for k, st in enumerate(sets))
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
    for (c = 0; c < 60; c = c + 1) begin
      {clear}
{drive}
      #3 $display("OUT %0d %0d %0d", c, ov, od);
      @(posedge clk); #1;
    end
    $finish;
  end
endmodule
"""
    files = [f for f in rec["files"] if f.endswith(".v")]
    open(os.path.join(folder, "tb_gen.v"), "w").write(tb)
    exe = os.path.join(folder, "tb.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-o", exe, "tb_gen.v", *files], cwd=folder, capture_output=True, text=True)
    if c.returncode:
        raise RuntimeError(c.stderr[:300])
    out = subprocess.run(["vvp", exe], capture_output=True, text=True).stdout
    return [(int(a), int(b), int(d)) for a, b, d in re.findall(r"OUT (\d+) (\d+) (\d+)", out)]


def vm_answer(path, values, drive_names):
    """What the VM itself computes: inject the same values, run, read the output cell's value."""
    doc, recs, *_ = nl.extract(path)
    grid = vm.SuperGrid(recs)
    byname = {r.io_name: r for r in recs if r.io_name}
    for n, val in zip(drive_names, values):
        grid.inject(byname[n].row, byname[n].col, val)
    for _ in range(80):
        grid.tick()
    out = next(r for r in recs if r.io_name == "output")
    cell = grid.cells[(out.row, out.col)]
    return cell.adder_out_buffer if out.core == "adder" else cell.ram_data_reg if hasattr(cell, "ram_data_reg") else None


if not shutil.which("iverilog"):
    print("SKIP: iverilog not installed")
    sys.exit(0)

tmp = tempfile.mkdtemp(prefix="icmgen_")
try:
    print("relay chain (8 ram cells)")
    d = os.path.join(tmp, "relay")
    r = cli("-s", "sub", "--icm", os.path.join(EX, "small_relay_chain.icm-hier.json"), "--output", d)
    check("generates", r.returncode == 0, r.stderr.strip()[:200])
    rec = json.load(open(os.path.join(d, "ASSEMBLY.json")))
    check("no padding needed, 8-cycle latency", rec["pad_relay_cells"] == 0 and list(rec["output_latency_cycles"].values()) == [8], str(rec["output_latency_cycles"]))
    res = simulate(d, [0xDEADBEEF])
    hits = [(c, dv) for c, v, dv in res if v]
    check("value passes through unchanged, exactly one valid pulse, at the predicted cycle (8)", hits == [(8, 0xDEADBEEF)], str(hits[:4]))

    print("parallel reduction tree (3 adders, 4 lanes): RTL vs the real VM")
    path = os.path.join(EX, "parallel_reduction_tree.icm-hier.json")
    d = os.path.join(tmp, "tree")
    r = cli("-s", "sub", "--icm", path, "--output", d)
    check("generates, 6 padding relay cells (1+2+3), 6-cycle latency", r.returncode == 0 and json.load(open(os.path.join(d, "ASSEMBLY.json")))["pad_relay_cells"] == 6
          and list(json.load(open(os.path.join(d, "ASSEMBLY.json")))["output_latency_cycles"].values()) == [6], r.stderr.strip()[:200])
    names = [f"input_{k}" for k in range(4)]
    for vals in ([1, 2, 3, 4], [100, 200, 300, 400], [0xFFFFFFFF, 1, 0, 0], [7, 0, 0, 0], [1000000, 2000000, 3000000, 4000000]):
        res = simulate(d, vals)
        hits = [(c, dv) for c, v, dv in res if v]
        want = sum(vals) & 0xFFFFFFFF
        vmv = vm_answer(path, vals, names)
        check(f"inputs {vals}: RTL == VM == arithmetic ({want}), one pulse at cycle 6",
              hits == [(6, want)] and vmv == want, f"rtl={hits[:3]} vm={vmv} want={want}")
    print("pipelining: aligned design is a full pipeline; the padding is what makes back-to-back items correct")
    sets = [[1, 2, 3, 4], [10, 20, 30, 40], [100, 200, 300, 400], [1000, 2000, 3000, 4000]]
    want = [(6 + k, sum(s)) for k, s in enumerate(sets)]
    hits = [(c, dv) for c, v, dv in simulate(d, sets) if v]
    check("aligned: 4 items injected on consecutive cycles -> 4 correct results on consecutive cycles (1/cycle)", hits == want, f"{hits} vs {want}")
    dn = os.path.join(tmp, "tree_noalign")
    r = cli("-s", "sub", "--icm", path, "--output", dn, "--no-align")
    check("--no-align generates with no padding", r.returncode == 0 and json.load(open(os.path.join(dn, "ASSEMBLY.json")))["pad_relay_cells"] == 0)
    one = [(c, dv) for c, v, dv in simulate(dn, [1, 2, 3, 4]) if v]
    check("FINDING: an unaligned ONE-SHOT value is still right (a flowing ram holds its data) -- padding is not about one-shots",
          one == [(6, 10)], str(one))
    bad = [(c, dv) for c, v, dv in simulate(dn, sets) if v]
    check("NEGATIVE CONTROL: unaligned BACK-TO-BACK items are wrong (items mix) -- so the padding does real work",
          bad != want and len(bad) == len(want), f"{bad} vs {want}")

    print("COMPILED LLVM programs (ICM v3, as the compiler writes them): generated RTL vs the real VM")
    try:
        import llvmlite  # noqa: F401
        have_llvm = True
    except ImportError:
        have_llvm = False
        print("  SKIP  llvmlite not installed")
    if have_llvm:
        sys.path.insert(0, os.path.join(ROOT, "nano"))
        import llvm_cli_v1
        progs = {"add": "%a = add i32 %x, %y", "addyx": "%a = add i32 %y, %x"}
        for name, body in progs.items():
            src = os.path.join(tmp, name + ".ll")
            open(src, "w").write(f"define i32 @f(i32 %x, i32 %y) {{\nentry:\n  {body}\n  ret i32 %a\n}}\n")
            icm = os.path.join(tmp, name + ".icm")
            check(f"{name}: compiles to ICM v3", llvm_cli_v1.main([src, "-o", icm]) == 0)
            dc = os.path.join(tmp, "g_" + name)
            r = cli("-s", "sub", "--icm", icm, "--output", dc)
            check(f"{name}: generates (priority arbiter eliminated)", r.returncode == 0, r.stderr.strip()[:300])
            rec = json.load(open(os.path.join(dc, "ASSEMBLY.json")))
            check(f"{name}: one priority cell eliminated, 5 cells left", len(rec["eliminated_priority_cells"]) == 1 and rec["cells"] == 5, str(rec["eliminated_priority_cells"]))
            doc, recs, cells, edges, inputs, outputs, ext, w = nl.extract(icm)
            ents = sorted([c for c in recs if c.core == "ram" and not (c.core_config or {}).get("upstream_mask")], key=lambda c: (c.row, c.col))
            port_names = [re.sub(r"[^A-Za-z0-9_]", "_", c.cell_id) for c in ents]
            for x, y in ((6, 7), (100, 3), (0xFFFFFFFF, 2), (0, 0), (123456789, 987654321)):
                got = [(c, dv) for c, v, dv in simulate(dc, [x, y], names=port_names) if v]
                grid = vm.SuperGrid(recs)
                for c, val in zip(ents, (x, y)):
                    cell = grid.cells[(c.row, c.col)]
                    cell.ram_data_reg, cell.ram_data_valid = val & 0xFFFFFFFF, True
                ex = [c.cell_id for c in recs if not outputs.get(c.cell_id)][0]
                exc = grid.cells[next((c.row, c.col) for c in recs if c.cell_id == ex)]
                vmv = None
                for _ in range(120):
                    grid.tick()
                    if getattr(exc, f"{exc.core}_data_valid", None):
                        vmv = getattr(exc, f"{exc.core}_out_buffer")
                        break
                want = (x + y) & 0xFFFFFFFF
                check(f"{name}({x}, {y}): RTL == VM == arithmetic ({want}), one pulse", got == [(3, want)] and vmv == want, f"rtl={got[:3]} vm={vmv} want={want}")
        # a program that needs an ORDERED operand pair: the compiler uses the sequenced-channel priority. Since #1018 its turn order IS recorded in the saved ICM, so the file generates
        # (the arbiter becomes operand wiring, the turn deciding A / B) and the saved file runs on the VM; the RTL equals the VM.
        src = os.path.join(tmp, "subx.ll")
        open(src, "w").write("define i32 @f(i32 %x, i32 %y) {\nentry:\n  %a = sub i32 %x, %y\n  ret i32 %a\n}\n")
        icm = os.path.join(tmp, "subx.icm")
        llvm_cli_v1.main([src, "-o", icm])
        dc = os.path.join(tmp, "g_subx")
        r = cli("-s", "sub", "--icm", icm, "--output", dc)
        check("x - y (sequenced-channel priority, order RECORDED in the file): generates, the arbiter eliminated", r.returncode == 0
              and len(json.load(open(os.path.join(dc, "ASSEMBLY.json")))["eliminated_priority_cells"]) == 1, r.stderr.strip()[:240])
        if r.returncode == 0:
            doc, recs, cells, edges, inputs, outputs, ext, w = nl.extract(icm)
            ents = sorted([c for c in recs if c.core == "ram" and not (c.core_config or {}).get("upstream_mask")], key=lambda c: (c.row, c.col))
            port_names = [re.sub(r"[^A-Za-z0-9_]", "_", c.cell_id) for c in ents]
            for x, y in ((6, 7), (100, 3), (0, 0), (123456789, 987654321)):
                got = [(c, dv) for c, v, dv in simulate(dc, [x, y], names=port_names) if v]
                grid = vm.SuperGrid(recs)
                for c, val in zip(ents, (x, y)):
                    cell = grid.cells[(c.row, c.col)]
                    cell.ram_data_reg, cell.ram_data_valid = val & 0xFFFFFFFF, True
                ex = [c.cell_id for c in recs if not outputs.get(c.cell_id)][0]
                exc = grid.cells[next((c.row, c.col) for c in recs if c.cell_id == ex)]
                vmv = None
                for _ in range(160):
                    grid.tick()
                    if getattr(exc, f"{exc.core}_data_valid", None):
                        vmv = getattr(exc, f"{exc.core}_out_buffer")
                        break
                check(f"sub({x}, {y}): RTL == VM (the saved file's recorded turn order), a difference of the two", len(got) == 1 and got[0][1] == vmv
                      and vmv in ((x - y) & 0xFFFFFFFF, (y - x) & 0xFFFFFFFF), f"rtl={got[:3]} vm={vmv}")

    print("refusals are specific, never silent")
    sys.path.insert(0, os.path.join(ROOT, "nano"))
    from icm_v3 import IcmV3File as _F, IcmV3Record as _R
    _F(name="seq", records=[_R(cell_id="S", row=1, col=0, core="sequencer", core_config={"VALUE_0": 1, "VALUE_1": 2, "VALUE_2": 3, "VALUE_3": 4, "SEQUENCE_LEN": 3, "downstream_mask": ["e"]}, addon_config={"invert_en": 1}),
                            _R(cell_id="E", row=1, col=1, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]).save(os.path.join(tmp, "seq.icm"))
    for label, args, needles in (
                        ("flex --icm still refuses what is not translated (a sequencer carrying an addon), with the reason", ["-s", "flex", "--icm", os.path.join(tmp, "seq.icm")], ["addon_config on a sequencer"]),
            ("--icm without -s", ["--icm", path], ["-s sub"])):
        r = cli(*args, "--output", os.path.join(tmp, "ref"))
        check(f"{label}: refused, names the reason", r.returncode != 0 and all(n in r.stderr for n in needles)
              and (("constant" not in r.stderr and "merge" not in r.stderr) if "cordic" in label else True), r.stderr.strip()[:200])
    r = cli("-s", "flex", "--icm", path, "--output", os.path.join(tmp, "g_flex_tree"))
    check("flex --icm now GENERATES what stage 1 covers (the reduction tree); its proof is tests/test_flexsub_flex_v1.py", r.returncode == 0, r.stderr.strip()[:200])
    r = cli("-s", "sub", "--icm", os.path.join(EX, "cordic_z_convergence.icm-hier.json"), "--output", os.path.join(tmp, "g_cordic"))
    check("cordic NOW generates on sub (branch lowered, constant-reference merges removed); its RTL-vs-VM proof is tests/test_flexsub_branch_v1.py",
          r.returncode == 0, r.stderr.strip()[:240])
    r = cli("--man", os.path.join(ROOT, "docs", "man", "mustang-f100-a10.man.json"), "--output", os.path.join(tmp, "z"))
    check("default path still reports every missing required argument", r.returncode == 2 and "--man" not in r.stderr.split("required:")[-1] and "--cells" in r.stderr, r.stderr.strip()[-120:])
    r = cli("--output", os.path.join(tmp, "z"))
    check("both missing -> '--man, --cells' (the original message)", "required: --man, --cells" in r.stderr, r.stderr.strip()[-120:])

    print("synthesis")
    if shutil.which("yosys"):
        top = json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"]
        files = [f for f in json.load(open(os.path.join(d, "ASSEMBLY.json")))["files"] if f.endswith(".v")]
        out = subprocess.run(["yosys", "-p", f"read_verilog -sv {' '.join(files)}; hierarchy -top {top}; synth_gowin -top {top} -json /dev/null; stat"],
                             cwd=d, capture_output=True, text=True).stdout
        alu = re.findall(r"^\s+ALU\s+(\d+)", out.split("Number of cells")[-1], re.M)
        check("generated tree synthesises under synth_gowin; 3 adders = 96 ALU", bool(alu) and int(alu[0]) == 96, str(alu))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
