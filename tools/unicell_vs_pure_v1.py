#!/usr/bin/env python3
"""unicell_vs_pure_v1.py -- the arguments for UniCell against a pure Verilog design, each run as a test on the CORDIC z-convergence example (ledger #1036 addendum 59).
Imports the baselines from cordic_baseline_v1.py. Sub-commands:  stream | change | agree | freeze | all   (results go to docs/measurements/unicell_vs_pure_v1.json)."""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "nano"))
import cordic_baseline_v1 as cb  # noqa: E402

OUTJSON = os.path.join(ROOT, "docs", "measurements", "unicell_vs_pure_v1.json")

HAND = lambda *n: [os.path.join(cb.BASE, x) for x in n]
PORTS = {   # how each design is instantiated: (module, port text)
    "pipe": ("cordic_z_pipe_v1", ".clk(clk), .rst(rst), .in_data(zin), .in_valid(vin), .out_data(od), .out_valid(ov)", False),
    "hs": ("cordic_z_hs_v1", ".clk(clk), .rst(rst), .in_data(zin), .in_valid(vin), .in_ack(ack), .out_data(od), .out_valid(ov), .out_ack(1'b1)", True),
    "flex": ("icm_cordic_z_convergence_flex", ".clk(clk), .rst(rst), .cfg_valid(cfgv), .in_z_input_data(zin), .in_z_input_valid(vin), .in_z_input_ack(ack), .out_z_output_data(od), .out_z_output_valid(ov), .out_z_output_ack(1'b1)", True),
    "sub": ("icm_cordic_z_convergence_sub", ".clk(clk), .rst(rst), .cfg_valid(cfgv), .in_z_input_data(zin), .in_z_input_valid(vin), .out_z_output_data(od), .out_z_output_valid(ov)", False),
}


def assemble(family, out):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", family, "--icm", cb.ICM, "--man", cb.MAN, "--output", out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]
    return [os.path.join(out, f) for f in sorted(os.listdir(out)) if f.endswith(".v")], r.stdout


def stream_tb(kind, n, vec_path):
    mod, ports, has_ack = PORTS[kind]
    return f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfgv = 0; always #5 clk = ~clk;
  localparam N = {n};
  reg signed [31:0] vecs [0:N-1]; initial $readmemh("{vec_path}", vecs);
  reg signed [31:0] zin = 0; reg vin = 0; wire ack; wire signed [31:0] od; wire ov;
  { 'wire ack_unused;' }
  {mod} dut ({ports});
  integer i = 0, cyc = 0, nout = 0, first_in = -1, last_out = -1, started = 0;
  reg signed [31:0] got [0:N+63]; integer gcyc [0:N+63];
  always @(posedge clk) begin
    cyc <= cyc + 1;
    if (ov && nout < N + 64) begin got[nout] <= od; gcyc[nout] <= cyc; nout <= nout + 1; last_out <= cyc; end
  end
  always @(posedge clk) if (started) begin
    if (vin && ({'ack' if has_ack else '1'})) begin
      if (first_in < 0) first_in <= cyc;
      if (i + 1 < N) begin i <= i + 1; zin <= vecs[i + 1]; end else begin vin <= 0; end
    end
  end
  initial begin
    repeat (4) @(posedge clk); rst <= 0; repeat (2) @(posedge clk); cfgv <= 1; @(posedge clk); cfgv <= 0; repeat (12) @(posedge clk);
    zin <= vecs[0]; vin <= 1; started = 1;
    repeat (N * 12 + 200) @(posedge clk);
    $display("NOUT %0d FIRST_IN %0d LAST_OUT %0d", nout, first_in, last_out);
    for (i = 0; i < nout && i < N + 4; i = i + 1) $display("OUT %0d %0d %0d", i, got[i], gcyc[i]);
    $finish;
  end
endmodule
"""


def run_stream(kind, files, n=64):
    d = tempfile.mkdtemp(prefix="stream_")
    try:
        r = random.Random(59)
        vs = [r.randint(-120000, 120000) for _ in range(n)]
        vp = os.path.join(d, "v.hex")
        open(vp, "w").write("\n".join("%08x" % (v & 0xFFFFFFFF) for v in vs) + "\n")
        tb = os.path.join(d, "tb.v")
        open(tb, "w").write(stream_tb(kind, n, vp))
        rr = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "t.vvp"), tb] + files, capture_output=True, text=True)
        assert rr.returncode == 0, rr.stderr[:1500]
        out = subprocess.run(["vvp", os.path.join(d, "t.vvp")], capture_output=True, text=True, timeout=900).stdout
        head = next(l for l in out.splitlines() if l.startswith("NOUT")).split()
        nout, first_in, last_out = int(head[1]), int(head[3]), int(head[5])
        got = [int(l.split()[2]) for l in out.splitlines() if l.startswith("OUT")]
        cycs = [int(l.split()[3]) for l in out.splitlines() if l.startswith("OUT")]
        want = [cb.model(v) for v in vs]
        correct = sum(1 for a, b in zip(got, want) if a == b)
        span = last_out - first_in if first_in >= 0 and last_out >= 0 else None
        return {"items_in": n, "results_out": nout, "correct_in_order": correct, "cycles_first_in_to_last_out": span,
                "latency_first_result_after_first_in": (cycs[0] - first_in) if cycs and first_in >= 0 else None,
                "steady_cycles_per_item": round((cycs[-1] - cycs[nout // 4]) / (nout - 1 - nout // 4), 2) if nout > 8 else None}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def stream():
    d = tempfile.mkdtemp(prefix="uvp_")
    try:
        flex_files, _ = assemble("flex", os.path.join(d, "f"))
        sub_files, sub_out = assemble("sub", os.path.join(d, "s"))
        res = {"sub_assembler_says": sub_out.strip().splitlines()[-1]}
        for kind, files in (("pipe", HAND("cordic_z_pipe_v1.v")), ("hs", HAND("cordic_z_hs_v1.v")), ("flex", flex_files), ("sub", sub_files)):
            res[kind] = run_stream(kind, files)
        res["sub_synth"] = cb.synth_counts(sub_files, "icm_cordic_z_convergence_sub")
        res["sub_pnr_in_wrapper"] = place_sub(sub_files)
        return res
    finally:
        shutil.rmtree(d, ignore_errors=True)


def place_sub(files):
    old = cb.wrapper

    def w(kind):
        text = old("unicell").replace("icm_cordic_z_convergence_flex dut (.clk(clk), .rst(rst), .cfg_valid(cfgv), .in_z_input_data(zin), .in_z_input_valid(1'b1), .in_z_input_ack(), .out_z_output_data(od), .out_z_output_valid(ov), .out_z_output_ack(1'b1));",
                                      "icm_cordic_z_convergence_sub dut (.clk(clk), .rst(rst), .cfg_valid(cfgv), .in_z_input_data(zin), .in_z_input_valid(1'b1), .out_z_output_data(od), .out_z_output_valid(ov));")
        assert "convergence_sub" in text
        return text
    cb.wrapper = w
    try:
        return cb.place_and_route(files, "unicell")
    finally:
        cb.wrapper = old


# ---------------------------------------------------------------- VM side (agree / freeze)
def vm_setup():
    sys.path.insert(0, os.path.join(ROOT, "nano", "examples"))
    from hierarchical_icm_prototype_loader import load_hierarchical, flatten
    import unicell_super_automaton_v1 as vm
    import flex_grid_v1 as fg
    records, _ = flatten(load_hierarchical(cb.ICM))
    ic = next(x for x in records if x.io_name == "z_input")
    oc = next(x for x in records if x.io_name == "z_output")
    return vm, fg, records, ic, oc


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >= (1 << 31) else v


def vm_out(g, oc):
    o = g.cells[(oc.row, oc.col)]
    return s32(o.ram_data_reg) if o.ram_data_valid else None


def vm_run(cls, records, ic, oc, z0, settle):
    g = cls(records)
    for _ in range(settle):
        g.tick()
    g.inject(ic.row, ic.col, z0 & 0xFFFFFFFF)
    for t in range(1, 300):
        g.tick()
        if vm_out(g, oc) is not None:
            return vm_out(g, oc), t
    return None, None


def agree():
    vm, fg, records, ic, oc = vm_setup()
    r = random.Random(59)
    zs = [50000, -50000, 0, 1, -1, 2**31 - 1, -2**31] + [r.randint(-2**31, 2**31 - 1) for _ in range(30)] + [r.randint(-150000, 150000) for _ in range(30)]
    res = {"inputs": len(zs)}
    for name, cls, settle in (("standard_vm_SuperGrid", vm.SuperGrid, 6), ("FlexGrid", fg.FlexGrid, 20)):
        bad, ticks = 0, set()
        for z in zs:
            v, t = vm_run(cls, records, ic, oc, z, settle)
            ticks.add(t)
            bad += (v != cb.model(z))
        res[name] = {"wrong": bad, "ticks_to_result_values_seen": sorted(ticks)}
    return res


def freeze(via_file_every=2):
    import copy
    vm, fg, records, ic, oc = vm_setup()
    from mixed_grid_checkpoint_v1 import save_mixed_model, load_mixed_model

    def cut_run(cls, z0, settle, cut, keep_pending, via_file):
        g = cls(records)
        for _ in range(settle):
            g.tick()
        g.inject(ic.row, ic.col, z0 & 0xFFFFFFFF)
        for _ in range(cut):
            g.tick()
        pend = copy.deepcopy(g._pending) if keep_pending else {}
        tc, w, m = g.tick_count, g.width, g.mask
        npend = sum(len(v) for v in g._pending.values())
        if via_file:
            d = tempfile.mkdtemp(prefix="freeze_")
            try:
                pth = os.path.join(d, "s.json")
                save_mixed_model(dict(g.cells), pth, name="cordic cut")
                cells = load_mixed_model(pth)
            finally:
                shutil.rmtree(d, ignore_errors=True)
        else:
            cells = {k: c.restore(c.checkpoint()) for k, c in g.cells.items()}
        del g
        g2 = cls(records)                       # a fresh grid built from the same program: the wiring comes from the records, the state from the checkpoint
        for k, c in cells.items():
            c.width, c.mask = w, m
            g2.cells[k] = c
        g2._pending, g2.tick_count = pend, tc
        t = cut
        while t < 300:
            if vm_out(g2, oc) is not None:
                return vm_out(g2, oc), t, npend
            g2.tick()
            t += 1
        return None, None, npend

    out = {}
    for name, cls, settle in (("standard_vm_SuperGrid", vm.SuperGrid, 6), ("FlexGrid", fg.FlexGrid, 20)):
        runs = wrong_value = wrong_tick = with_pending = 0
        wrong_without_pending = tested_without_pending = 0
        for z0 in (50000, -50000, 0, 123456):
            want_v, want_t = vm_run(cls, records, ic, oc, z0, settle)
            for cut in range(0, want_t):                         # every tick while the item is genuinely in flight
                v, t, npend = cut_run(cls, z0, settle, cut, True, via_file=(cut % via_file_every == 0))
                runs += 1
                wrong_value += (v != want_v)
                wrong_tick += (t != want_t)
                with_pending += (npend > 0)
                if npend > 0:
                    v2, t2, _ = cut_run(cls, z0, settle, cut, False, via_file=False)
                    tested_without_pending += 1
                    wrong_without_pending += (v2 != want_v or t2 != want_t)
        out[name] = {"cuts_tested": runs, "wrong_value": wrong_value, "wrong_finish_tick": wrong_tick, "cuts_with_words_in_flight_between_cells": with_pending,
                     "same_cuts_but_cells_only_no_pending_words": {"tested": tested_without_pending, "wrong": wrong_without_pending}}
    return out


# ---------------------------------------------------------------- change time (what it takes to change the design)
def change():
    """Change ONE constant (K1 = 26565 -> 26566) in each form and time what it takes to get a runnable result. Wall-clock on this machine, one run each, indicative only."""
    res = {"change": "K1 26565 -> 26566 (a different angle table entry)", "machine_note": "one run each on the build machine; PnR is one seed, without the final bitstream-pack step (seconds)"}
    d = tempfile.mkdtemp(prefix="chg_")
    try:
        # A. pure Verilog (hs): edit, synthesise, place and route
        pure = os.path.join(d, "pure")
        shutil.copytree(cb.BASE, pure)
        pf = os.path.join(pure, "cordic_z_hs_v1.v")
        t = open(pf).read()
        assert "32'sd26565" in t
        open(pf, "w").write(t.replace("32'sd26565", "32'sd26566"))
        t0 = time.time()
        r_ = cb.place_and_route([pf], "hs", seeds=(1,))
        res["pure_verilog_edit_to_placed_seconds"] = round(time.time() - t0, 1)
        res["pure_verilog_pnr"] = r_
        # simulation turn-around for the same edit
        t0 = time.time()
        subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "x.vvp"), pf, os.path.join(pure, "cordic_z_pipe_v1.v")], capture_output=True)
        res["pure_verilog_iverilog_compile_seconds"] = round(time.time() - t0, 2)
        # B. UniCell on the Tang (flex): edit the program, regenerate, synthesise, place and route
        icm = json.load(open(cb.ICM))
        n_ = 0
        for pat in icm["patterns"].values():
            for c in pat["cells"]:
                if c.get("preload_value") == 26565:
                    c["preload_value"] = 26566
                    n_ += 1
                elif c.get("preload_value") == (-26565) & 0xFFFFFFFF:
                    c["preload_value"] = (-26566) & 0xFFFFFFFF
                    n_ += 1
        assert n_ == 2
        icm_path = os.path.join(d, "cordic_z_convergence.icm-hier.json")
        json.dump(icm, open(icm_path, "w"))
        t0 = time.time()
        out = os.path.join(d, "uc")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", icm_path, "--man", cb.MAN, "--output", out], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-400:]
        res["unicell_flex_generate_seconds"] = round(time.time() - t0, 2)
        files = [os.path.join(out, f) for f in sorted(os.listdir(out)) if f.endswith(".v")]
        t1 = time.time()
        res["unicell_flex_pnr"] = cb.place_and_route(files, "unicell", seeds=(1,))
        res["unicell_flex_edit_to_placed_seconds"] = round(time.time() - t0, 1)
        # C. UniCell in the VM: the same edit is data: rebuild the grid and run one item
        sys.path.insert(0, os.path.join(ROOT, "nano", "examples"))
        from hierarchical_icm_prototype_loader import load_hierarchical, flatten
        vm, fg, _, ic, oc = vm_setup()
        t0 = time.time()
        recs, _ = flatten(load_hierarchical(icm_path))
        ic2 = next(x for x in recs if x.io_name == "z_input")
        oc2 = next(x for x in recs if x.io_name == "z_output")
        v, tk = vm_run(vm.SuperGrid, recs, ic2, oc2, 50000, 6)
        res["unicell_vm_edit_to_first_result_seconds"] = round(time.time() - t0, 3)
        res["unicell_vm_result_for_z0_50000"] = v
        want = 50000
        for k in (45000, 26566, 14036, 7125):
            want = want - k if want > 0 else want + k
        res["expected_for_edited_table"] = want
        return res
    finally:
        shutil.rmtree(d, ignore_errors=True)


def effort():
    """What can be counted about describing the design (NOT a measure of how long a person takes): size of each description."""
    def lines(path):
        return sum(1 for _ in open(path))
    hand = {f: lines(os.path.join(cb.BASE, f)) for f in sorted(os.listdir(cb.BASE)) if f.endswith(".v")}
    d = tempfile.mkdtemp(prefix="eff_")
    try:
        files, _ = assemble("flex", os.path.join(d, "f"))
        gen = sum(lines(f) for f in files if "icm_cordic" in f)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return {"hand_written_verilog_lines": hand, "unicell_program_file_lines": lines(cb.ICM), "unicell_program_distinct_cell_kinds": 3,
            "generated_top_verilog_lines_flex": gen,
            "note": "line counts only; the UniCell program is a hierarchical JSON that a tool (composer) can draw, so lines are not what a person types; no timing of a person was made"}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "stream":
        res = stream()
        print(json.dumps(res, indent=1))
        old = json.load(open(OUTJSON)) if os.path.exists(OUTJSON) else {}
        old["stream"] = res
        json.dump(old, open(OUTJSON, "w"), indent=1)
    elif cmd in ("agree", "freeze", "change", "effort"):
        res = {"agree": agree, "freeze": freeze, "change": change, "effort": effort}[cmd]()
        print(json.dumps(res, indent=1))
        old = json.load(open(OUTJSON)) if os.path.exists(OUTJSON) else {}
        old[cmd] = res
        json.dump(old, open(OUTJSON, "w"), indent=1)
    else:
        print(__doc__)
