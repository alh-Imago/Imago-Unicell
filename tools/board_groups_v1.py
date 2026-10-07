#!/usr/bin/env python3
"""tools/board_groups_v1.py -- ledger #1025: the on-board tests GROUPED into two bitstreams of five, so each needs only ONE load per power-up.

Why: on Alan's PC the board's USB-serial path went silent after the 2nd..4th load following a power-up (LEDs showed the design running and passing; replug cured it;
reload and USB reset did not), but the FIRST load after a power-up always worked. So: one load per power cycle, five tests per load.
Each test keeps its own self-checking wrapper (own power-on reset, checker and result line). A rotating selector (SELBIT=26: 2.5 s per test) connects ONE
test's UART line to the board's TX pin at a time; each test repeats its line every ~36 ms, so every test is heard dozens of times per slot.
LEDs: LED0 heartbeat, LED1 on = every test in the group passed, LED2 on = any failed, LED3 on = every test finished (active low).

  python3 tools/board_groups_v1.py [--out fpga/board_tests/groups] [--no-pnr] [--sim]
"""
import argparse, json, os, re, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import board_tests_v1 as bt  # noqa: E402

GROUPS = {"A": ["relay_chain", "relay_chain_stalled", "adder_stream", "adder_stalled", "adder_constant"],
          "B": ["priority_strict", "priority_weighted", "priority_sequenced", "ram_hold", "ram_oneshot"]}
BY_NAME = {t[0]: t for t in bt.TESTS}
STRIP = re.compile(r"`(default_nettype none|timescale[^\n]*)")


def build(gname, names, out, pnr, sim, seed=1):
    work = os.path.join(out, "_work_" + gname)
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    mods, wraps, sims = {}, [], {}
    for name in names:
        _, desc, mk, streams, gaps, stalls = BY_NAME[name]
        recs = mk(); exp = bt.expected(recs, streams)
        icm = os.path.join(work, name + ".icm"); bt.IcmV3File(name=name, records=recs).save(icm)
        gen = os.path.join(work, "gen_" + name)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", icm, "--output", gen], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"{name}: generator failed {r.stderr[-300:]}")
        rec = json.load(open(os.path.join(gen, "ASSEMBLY.json")))
        for f in rec["files"]:
            if f.endswith(".v"):
                txt = open(os.path.join(gen, f)).read(); key = os.path.basename(f)
                if key in mods and mods[key] != txt:
                    raise SystemExit(f"module file {key} differs between tests")
                mods[key] = txt
        wraps.append(bt.wrapper(name, rec["top"], streams, "O", exp, gaps, stalls, bt.CPB, bt.SETTLE, bt.TIMEOUT))
        sims[name] = json.load(open(os.path.join(ROOT, "fpga", "board_tests", name + ".json")))["sim_line"] if os.path.exists(os.path.join(ROOT, "fpga", "board_tests", name + ".json")) else ""
    n = len(names)
    top = ["`default_nettype none", "module board_top_group #(parameter integer SELBIT = 26, parameter integer CPB = 234, parameter integer SETTLE = 131072, parameter integer TIMEOUT = 33554432) (input wire BOARD_CLK, output wire UART_TX, output wire LED0_N, output wire LED1_N, output wire LED2_N, output wire LED3_N);",
           f"wire [{n-1}:0] tx, p_n, f_n, d_n;"]
    for i, nm in enumerate(names):
        top.append(f"board_top_{nm} #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t{i} (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[{i}]), .LED0_N(), .LED1_N(p_n[{i}]), .LED2_N(f_n[{i}]), .LED3_N(d_n[{i}]));")
    top += ["reg [27:0] sel_cnt = 28'd0; always @(posedge BOARD_CLK) sel_cnt <= sel_cnt + 28'd1;",
            f"reg [2:0] sel = 3'd0; reg wrap = 1'b0; always @(posedge BOARD_CLK) begin wrap <= sel_cnt[SELBIT]; if (wrap && !sel_cnt[SELBIT]) sel <= (sel == 3'd{n-1}) ? 3'd0 : sel + 3'd1; end",
            "assign UART_TX = tx[sel];",
            f"wire all_done = (d_n == {n}'d0); wire any_fail = (f_n != {{{n}{{1'b1}}}}); wire all_pass = (p_n == {n}'d0);",
            "reg [23:0] hb = 24'd0; always @(posedge BOARD_CLK) hb <= hb + 24'd1;",
            "assign LED0_N = ~hb[23]; assign LED1_N = ~(all_done && all_pass && !any_fail); assign LED2_N = ~any_fail; assign LED3_N = ~all_done;", "endmodule"]
    for k, t in mods.items():
        open(os.path.join(work, k), "w").write(t)
    open(os.path.join(work, "board_uart_tx.v"), "w").write(bt.UART_V)
    open(os.path.join(work, "wrappers.v"), "w").write("`timescale 1ns / 1ps\n`default_nettype none\n" + "\n".join(STRIP.sub("", w) for w in wraps))
    open(os.path.join(work, "board_top_group.v"), "w").write("\n".join(top) + "\n")
    files = [os.path.join(work, f) for f in ["board_uart_tx.v", "wrappers.v", "board_top_group.v"] + sorted(mods)]
    cstp = os.path.join(out, f"group_{gname}.cst"); open(cstp, "w").write(bt.cst()); shutil.copy(cstp, os.path.join(work, "g.cst"))
    shutil.copy(os.path.join(work, "board_top_group.v"), os.path.join(out, f"group_{gname}.v"))
    res = dict(group=gname, tests=names, sim_lines=sims)
    if sim:   # simulate with a short selector and a shrunk UART; decode the text per slot
        tb = f"""`timescale 1ns/1ps
module tbg; reg clk=0; wire tx,l0,l1,l2,l3; always #5 clk=~clk;
board_top_group #(.SELBIT(17), .CPB(8), .SETTLE(2000), .TIMEOUT(2000000)) d(.BOARD_CLK(clk),.UART_TX(tx),.LED0_N(l0),.LED1_N(l1),.LED2_N(l2),.LED3_N(l3));
reg [7:0] b; integer i;
initial forever begin
  @(negedge tx); repeat (4) @(posedge clk);
  for (i = 0; i < 8; i = i + 1) begin repeat (8) @(posedge clk); b[i] = tx; end
  repeat (8) @(posedge clk); $write("%c", b);
end
initial begin #{int(n * 2**18 * 10 * 1.4)}; $display("LEDS pass=%b fail=%b done=%b", ~l1, ~l2, ~l3); $finish; end
endmodule"""
        open(os.path.join(work, "tbg.v"), "w").write(tb)
        c = subprocess.run(["iverilog", "-g2012", "-o", "tbg.vvp", os.path.join(work, "tbg.v")] + files, cwd=work, capture_output=True, text=True)
        if c.returncode:
            raise SystemExit("iverilog: " + c.stderr[:600])
        txt = subprocess.run(["vvp", "tbg.vvp"], cwd=work, capture_output=True, text=True, errors="replace", timeout=3000).stdout
        got = {nm: sum(1 for l in txt.splitlines() if l.strip() == sims[nm].strip()) for nm in names}
        res["sim_exact_lines"] = got
        res["sim_leds"] = [l for l in txt.splitlines() if l.startswith("LEDS")]
        if sims and not all(got.values()):
            raise SystemExit(f"group {gname}: simulation did not show every test's exact line: {got}\n{txt[-600:]}")
    if pnr:
        s = subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {' '.join(files)}; hierarchy -top board_top_group; synth_gowin -top board_top_group -nowidelut -json g.json"], cwd=work, capture_output=True, text=True)
        if s.returncode:
            raise SystemExit("yosys: " + s.stderr[-600:])
        p = subprocess.run(["yowasp-nextpnr-himbaechel-gowin", "--device", bt.DEVICE, "--vopt", "family=GW2A-18C", "--vopt", "cst=g.cst", "--seed", str(seed), "--json", "g.json", "--write", "g_r.json", "--report", "g_rep.json", "--freq", "27"], cwd=work, capture_output=True, text=True)
        if p.returncode:
            raise SystemExit("nextpnr: " + p.stderr[-600:])
        rep = json.load(open(os.path.join(work, "g_rep.json"))); fm = list(rep["fmax"].values())[0]["achieved"]; u = rep["utilization"]
        res.update(fmax_mhz=round(fm, 1), lut4=u["LUT4"]["used"], dff=u["DFF"]["used"])
        if fm < 27:
            raise SystemExit(f"group {gname}: timing not met ({fm:.1f} MHz)")
        g = subprocess.run(["gowin_pack", "-d", bt.DEVICE, "-o", os.path.join(out, f"group_{gname}.fs"), "-s", os.path.join(work, "g.cst"), "g_r.json"], cwd=work, capture_output=True, text=True)
        if g.returncode:
            raise SystemExit("pack: " + g.stderr[-400:])
    json.dump(res, open(os.path.join(out, f"group_{gname}.json"), "w"), indent=1)
    print(f"group {gname}: {res}")
    if not sim:
        shutil.rmtree(work, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "fpga", "board_tests", "groups")); ap.add_argument("--no-pnr", action="store_true"); ap.add_argument("--sim", action="store_true"); ap.add_argument("--only", default="")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    for g, names in GROUPS.items():
        if a.only and g not in a.only:
            continue
        build(g, names, a.out, not a.no_pnr, a.sim)


if __name__ == "__main__":
    main()
