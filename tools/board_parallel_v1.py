#!/usr/bin/env python3
"""tools/board_parallel_v1.py -- ledger #1180: Tang-only tests for the "no interrupts" and "parallel" claims (docs/NO_INTERRUPT_PARALLEL_TEST_PLAN_v1.md: T1, T4, T5).

A JOB is one small flex lane: entry -> relay -> adder (+ constant 5, from a fixed-mode ram) -> exit, the proven `d_adder_const` pattern (tools/board_tests_v1.py). 64 words go through; every output must be input + 5.
All runs are STALL-FREE (no random gaps, no random exit stalls) so the clock count on the card, `last=`, is deterministic and can be compared with the simulation exactly.

 T1 isolation   iso_s0 / iso_s4 / iso_s8: the same job alone, then beside 4 and 8 STORM lanes (the same cells, fed a new word on every clock by a generator and drained by an always-ready sink).
                Claim under test: the job's `last=` does not change. (The storm is separate cells; the clock, the reset and the report line are all they share.)
 T5 shared port sh_k2 / sh_k4 / sh_k8 (and iso_s0 as k1): the SAME 64 words handed round-robin to K lanes through ONE input and taken back through ONE output (the bench's shared port).
                Expected: `last=` falls as K grows, then flattens where the shared port (not the lanes) is the limit. This is where the speed-up stops, by design of the bench.
 T4 copies      ind_0..ind_3: four independent copies of the job, each with its own driver and checker, all running at once. Each must finish at the SAME clock as the single job (iso_s0).

  python3 tools/board_parallel_v1.py [--out fpga/board_tests_parallel] [--no-pnr] [--sizes] [--seed N] [--only NAME,NAME]"""
import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "nano"))
import board_loops_v1 as BL  # noqa: E402
import board_tests_v1 as bt  # noqa: E402
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

ROOT = BL.ROOT
CONST = 5
N_WORDS = 64
SEED = 1180
SELBIT = 24            # each design owns the serial line for 2^SELBIT clocks (about 0.6 s) in turn

# name, K work lanes behind the shared port, S storm lanes, design to use (None = its own), what it shows
DESIGNS = [
    ("iso_s0", 1, 0, None, "T1/T5 baseline: the job alone (one lane)"),
    ("iso_s4", 1, 4, None, "T1: the job beside 4 storm lanes (a new word offered on every clock)"),
    ("iso_s8", 1, 8, None, "T1: the job beside 8 storm lanes"),
    ("sh_k2", 2, 0, None, "T5: the same 64 words through 2 lanes behind one input and one output"),
    ("sh_k4", 4, 0, None, "T5: through 4 lanes"),
    ("sh_k8", 8, 0, None, "T5: through 8 lanes"),
    ("ind_0", 1, 0, "iso_s0", "T4: independent copy 0 of the job (own driver and checker)"),
    ("ind_1", 1, 0, "iso_s0", "T4: independent copy 1"),
    ("ind_2", 1, 0, "iso_s0", "T4: independent copy 2"),
    ("ind_3", 1, 0, "iso_s0", "T4: independent copy 3"),
]
GROUPS = {"P": ["iso_s0", "iso_s4", "iso_s8"], "Q": ["sh_k2", "sh_k4", "sh_k8"], "R": ["ind_0", "ind_1", "ind_2", "ind_3"]}


def lane(tag, r0):
    return [bt.ram(f"X{tag}", r0, 0, [], ["e"]), bt.ram(f"R{tag}", r0, 1, ["w"], ["s"]),
            IcmV3Record(cell_id=f"K{tag}", row=r0 + 1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"], "fixed_mode": 1, "load_data_valid": 1, "init_data": CONST}),
            bt.adder(f"A{tag}", r0 + 1, 1, ["n", "w"], ["e"]), bt.ram(f"O{tag}", r0 + 1, 2, ["w"], [])]


def records(k, s):
    recs = []
    for i in range(k):
        recs += lane(f"w{i}", 2 * i)
    for j in range(s):
        recs += lane(f"s{j}", 2 * (k + j))
    return recs


def shim(name, dut, k, s):
    """one stream in, one stream out for the standard board wrapper: round-robin to the K work lanes and back; storm lanes driven by a generator and drained by a sink."""
    w = max(1, (k - 1).bit_length())
    L = ["`default_nettype none", f"module {name}_shim (input wire clk, input wire rst, input wire cfg_valid,",
         "    input wire [31:0] in_x_in_data, input wire in_x_in_valid, output wire in_x_in_ack,",
         "    output wire [31:0] out_y_out_data, output wire out_y_out_valid, input wire out_y_out_ack);",
         f"reg [{w - 1}:0] ti = {w}'d0; reg [{w - 1}:0] to = {w}'d0;"]
    conn = []
    for i in range(k):
        L.append(f"wire ack_i{i}; wire v_i{i} = in_x_in_valid && (ti == {w}'d{i});")
        conn.append(f".in_Xw{i}_data(in_x_in_data), .in_Xw{i}_valid(v_i{i}), .in_Xw{i}_ack(ack_i{i})")
        L.append(f"wire [31:0] d_o{i}; wire v_o{i}; wire a_o{i} = out_y_out_ack && (to == {w}'d{i});")
        conn.append(f".out_Ow{i}_data(d_o{i}), .out_Ow{i}_valid(v_o{i}), .out_Ow{i}_ack(a_o{i})")
    if s:
        L += ["reg seen = 1'b0; reg [3:0] gc = 4'd0; reg storm_go = 1'b0;",
              "always @(posedge clk) if (rst) begin seen <= 1'b0; gc <= 4'd0; storm_go <= 1'b0; end else begin",
              "    if (cfg_valid) seen <= 1'b1; if (seen && gc != 4'd6) gc <= gc + 4'd1; if (gc == 4'd5) storm_go <= 1'b1; end"]
        for j in range(s):
            L += [f"reg [31:0] sd{j} = 32'd{j}; wire sack{j}; wire sv{j} = storm_go;",
                  f"always @(posedge clk) if (rst) sd{j} <= 32'd{j}; else if (sv{j} && sack{j}) sd{j} <= sd{j} + 32'd1;"]
            conn.append(f".in_Xs{j}_data(sd{j}), .in_Xs{j}_valid(sv{j}), .in_Xs{j}_ack(sack{j}), .out_Os{j}_data(), .out_Os{j}_valid(), .out_Os{j}_ack(1'b1)")
    L.append(f"{dut} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), " + ", ".join(conn) + ");")
    L.append("assign in_x_in_ack = " + " : ".join(f"(ti == {w}'d{i}) ? ack_i{i}" for i in range(k)) + " : 1'b0;")
    L.append("assign out_y_out_data = " + " : ".join(f"(to == {w}'d{i}) ? d_o{i}" for i in range(k)) + " : 32'd0;")
    L.append("assign out_y_out_valid = " + " : ".join(f"(to == {w}'d{i}) ? v_o{i}" for i in range(k)) + " : 1'b0;")
    L.append("always @(posedge clk) begin if (rst) begin ti <= 0; to <= 0; end else begin")
    L.append(f"    if (in_x_in_valid && in_x_in_ack) ti <= (ti == {w}'d{k - 1}) ? {w}'d0 : ti + {w}'d1;")
    L.append(f"    if (out_y_out_valid && out_y_out_ack) to <= (to == {w}'d{k - 1}) ? {w}'d0 : to + {w}'d1;")
    L.append("end end")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def words():
    r = random.Random(SEED)
    xs = [r.getrandbits(32) for _ in range(N_WORDS)]
    return xs, [(x + CONST) & 0xFFFFFFFF for x in xs]


def build_designs(work, only=None):
    """-> {design name: (shim module name, [verilog files])} for the designs that own a grid."""
    out = {}
    for name, k, s, use, _ in DESIGNS:
        if use is not None or (only and name not in only and not any(u == name and n in only for n, _, _, u, _ in DESIGNS)):
            continue
        icm = os.path.join(work, name + ".icm")
        IcmV3File(name=name, records=records(k, s), description=f"{k} work lane(s) and {s} storm lane(s)").save(icm)
        gen = os.path.join(work, "gen_" + name)
        top, files = BL.assemble(["-s", "flex", "--icm", icm, "--top", name + "_dut"], gen)
        sp = os.path.join(gen, name + "_shim.v")
        open(sp, "w").write(shim(name, top, k, s))
        out[name] = (name + "_shim", files + [sp])
    return out


def sim_one(work, name, shim_mod, files, exp, xs):
    wd = os.path.join(work, "w_" + name)
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(wd)
    open(os.path.join(wd, "board_uart_tx.v"), "w").write(bt.UART_V)
    top = "board_top_" + name
    open(os.path.join(wd, top + ".v"), "w").write(bt.wrapper(name, shim_mod, {"x_in": xs}, "y_out", exp, False, False, bt.CPB, bt.SETTLE, bt.TIMEOUT))
    sim = bt.simulate(wd, name, [os.path.join(wd, "board_uart_tx.v"), os.path.join(wd, top + ".v")] + files)
    line = next((ln for ln in sim.splitlines() if ln.startswith("UCT")), "")
    return wd, line.strip()


def group_top(names):
    n = len(names)
    w = max(1, (n - 1).bit_length())
    t = ["`default_nettype none",
         f"module board_top_group #(parameter integer SELBIT = {SELBIT}, parameter integer CPB = {bt.CPB}, parameter integer SETTLE = {bt.SETTLE}, parameter integer TIMEOUT = {bt.TIMEOUT}) (input wire BOARD_CLK, output wire UART_TX, output wire LED0_N, output wire LED1_N, output wire LED2_N, output wire LED3_N);",
         f"wire [{n - 1}:0] tx, p_n, f_n, d_n;"]
    for i, nm in enumerate(names):
        t.append(f"board_top_{nm} #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t{i} (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[{i}]), .LED0_N(), .LED1_N(p_n[{i}]), .LED2_N(f_n[{i}]), .LED3_N(d_n[{i}]));")
    t += ["reg [27:0] sel_cnt = 28'd0; always @(posedge BOARD_CLK) sel_cnt <= sel_cnt + 28'd1;",
          f"reg [{w - 1}:0] sel = {w}'d0; reg wrap = 1'b0; always @(posedge BOARD_CLK) begin wrap <= sel_cnt[SELBIT]; if (wrap && !sel_cnt[SELBIT]) sel <= (sel == {w}'d{n - 1}) ? {w}'d0 : sel + {w}'d1; end",
          "assign UART_TX = tx[sel];",
          f"wire all_done = (d_n == {n}'d0); wire any_fail = (f_n != {{{n}{{1'b1}}}}); wire all_pass = (p_n == {n}'d0);",
          "reg [23:0] hb = 24'd0; always @(posedge BOARD_CLK) hb <= hb + 24'd1;",
          "assign LED0_N = ~hb[23]; assign LED1_N = ~(all_done && all_pass && !any_fail); assign LED2_N = ~any_fail; assign LED3_N = ~all_done;", "endmodule"]
    return "\n".join(t) + "\n"


def build_group(gname, names, designs, sims, out, work, pnr, seed):
    """one bitstream holding the wrappers of `names` (each with its own checker), the serial line shared in turn."""
    wd = os.path.join(work, "_group_" + gname)
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(wd)
    xs, exp = words()
    mods, wraps = {}, []
    by_name = {n: (use or n) for n, _, _, use, _ in DESIGNS}
    for nm in names:
        shim_mod, files = designs[by_name[nm]]
        for f in files:
            if f.endswith(".v"):
                txt, key = open(f).read(), os.path.basename(f)
                if key in mods and mods[key] != txt:
                    raise SystemExit(f"module file {key} differs between designs")
                mods[key] = txt
        wraps.append(bt.wrapper(nm, shim_mod, {"x_in": xs}, "y_out", exp, False, False, bt.CPB, bt.SETTLE, bt.TIMEOUT))
    for k, t in mods.items():
        open(os.path.join(wd, k), "w").write(t)
    strip = re.compile(r"`(default_nettype none|timescale[^\n]*)")
    open(os.path.join(wd, "board_uart_tx.v"), "w").write(bt.UART_V)
    open(os.path.join(wd, "wrappers.v"), "w").write("`timescale 1ns / 1ps\n`default_nettype none\n" + "\n".join(strip.sub("", w) for w in wraps))
    open(os.path.join(wd, "board_top_group.v"), "w").write(group_top(names))
    flist = ["board_uart_tx.v", "wrappers.v", "board_top_group.v"] + sorted(mods)
    cst = bt.cst()
    open(os.path.join(out, f"group_{gname}.cst"), "w").write(cst)
    open(os.path.join(wd, "g.cst"), "w").write(cst)
    shutil.copy(os.path.join(wd, "board_top_group.v"), os.path.join(out, f"group_{gname}.v"))
    res = dict(group=gname, tests=names, sim_lines={n: sims[n] for n in names}, selbit=SELBIT, n_words=N_WORDS)
    s = subprocess.run(["yosys", "-q", "-l", "y.log", "-p", "read_verilog -sv %s; hierarchy -top board_top_group; synth_gowin -top board_top_group -nowidelut -json g.json" % " ".join(flist)], cwd=wd, capture_output=True, text=True, timeout=3000)
    if s.returncode:
        raise RuntimeError("yosys: " + (s.stderr or s.stdout)[-600:])
    if pnr:
        p = subprocess.run(["yowasp-nextpnr-himbaechel-gowin", "--device", bt.DEVICE, "--vopt", "family=GW2A-18C", "--vopt", "cst=g.cst", "--seed", str(seed), "--json", "g.json",
                            "--write", "g_r.json", "--report", "g_rep.json", "--freq", "27"], cwd=wd, capture_output=True, text=True, timeout=7000)
        if p.returncode:
            raise RuntimeError("nextpnr: " + (p.stdout[-500:] + p.stderr[-600:]))
        rep = json.load(open(os.path.join(wd, "g_rep.json")))
        fmax = rep["fmax"]["clk"]["achieved"] if "clk" in rep["fmax"] else min(v["achieved"] for v in rep["fmax"].values())
        u = rep["utilization"]
        res.update(fmax_mhz=round(fmax, 1), lut4=u["LUT4"]["used"], dff=u["DFF"]["used"])
        if fmax < 27:
            raise SystemExit(f"group {gname}: timing NOT met at 27 MHz (Fmax {fmax:.1f}); NOT written")
        g = subprocess.run(["gowin_pack", "-d", bt.DEVICE, "-o", os.path.abspath(os.path.join(out, f"group_{gname}.fs")), "-s", "g.cst", "g_r.json"], cwd=wd, capture_output=True, text=True)
        if g.returncode:
            raise RuntimeError("gowin_pack: " + g.stderr[-400:])
    else:
        st = open(os.path.join(wd, "y.log")).read()
        m = re.findall(r"^\s+(\d+)\s+LUT4", st, re.M)
        if m:
            res["lut4_synth"] = int(m[-1])
    json.dump(res, open(os.path.join(out, f"group_{gname}.json"), "w"), indent=1)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "fpga", "board_tests_parallel"))
    ap.add_argument("--no-pnr", action="store_true")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--groups", default="", help="comma list of group letters to build (default all); other groups' files are kept")
    ap.add_argument("--only", default="", help="comma list of design names (simulate and size just these)")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    gdir = os.path.join(out, "groups")
    os.makedirs(gdir, exist_ok=True)
    work = tempfile.mkdtemp(prefix="bpar_")
    only = set(x for x in a.only.split(",") if x)
    xs, exp = words()
    designs = build_designs(work, only)
    by_name = {n: (use or n) for n, _, _, use, _ in DESIGNS}
    sims = {}
    for name, k, s, use, what in DESIGNS:
        if only and name not in only:
            continue
        shim_mod, files = designs[by_name[name]]
        _, line = sim_one(work, name, shim_mod, files, exp, xs)
        if " res=P " not in line + " ":
            raise SystemExit(f"{name}: the wrapper FAILED in simulation: {line}")
        sims[name] = line
        print(f"{name:8s} K={k} S={s}  {line[:60]}  last={re.search(r'last=([0-9A-F]+)', line).group(1)} ({int(re.search(r'last=([0-9A-F]+)', line).group(1), 16)} clocks)")
    if only:
        return
    for g, names in GROUPS.items():
        if a.groups and g not in a.groups.split(","):
            continue
        r = build_group(g, names, designs, sims, gdir, work, not a.no_pnr, a.seed)
        print(f"group {g}: {names}  LUT4 {r.get('lut4', r.get('lut4_synth', '?'))}  Fmax {r.get('fmax_mhz', '-')}")
    json.dump(dict(n_words=N_WORDS, const=CONST, designs=[dict(name=n, k=k, s=s, uses=u, what=w) for n, k, s, u, w in DESIGNS], groups=GROUPS, sim_lines=sims),
              open(os.path.join(out, "parallel_meta.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
