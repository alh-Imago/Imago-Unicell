#!/usr/bin/env python3
"""tools/board_sub_tiles_v1.py -- ledger #1184: the NATIVE cross and corner cells in the SUB family (v4s) as a board bitstream; the flex version is tools/board_tiles_v1.py (#1169, passed on the card #1170).
Same grid, same six streams, same words (build_grid / words come from board_tiles_v1). The sub family has no acknowledge, so the generated design cannot be driven by the flex handshake: a small SUB SHIM collects six words from the board wrapper, pulses ALL six entries in the same clock (the tiles carry their streams at the same time), latches each exit's word when its valid pulses, and hands the six words to the wrapper in order. A tile that mixed, swapped or lost a stream changes the order or the words (or the shim never sees the exit valid and the wrapper times out) -> FAIL; the bite is
checked in simulation with every tile built as an ordinary ram relay (--bite).
  python3 tools/board_sub_tiles_v1.py [--out fpga/board_tests_sub_tiles] [--seed N] [--no-pnr] [--n 8] [--bite]"""
import argparse, os, random, re, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "nano"))
import board_loops_v1 as BL                                   # noqa: E402
import board_tiles_v1 as T                                    # noqa: E402
from icm_v3 import IcmV3File                                  # noqa: E402
ROOT = BL.ROOT


def sub_shim(dut_top, ents, exits):
    n = len(ents); idx = lambda s: re.sub(r"\W", "_", s)
    L = ["`default_nettype none", "module tiles_shim (input wire clk, input wire rst, input wire cfg_valid,",
         "    input wire [31:0] in_x_in_data, input wire in_x_in_valid, output wire in_x_in_ack,",
         "    output wire [31:0] out_y_out_data, output wire out_y_out_valid, input wire out_y_out_ack);",
         f"// rounds of {n}: collect {n} words, pulse ALL {n} entries in the same clock (so the tiles carry their streams at the same time), latch each exit's word when its valid pulses, then hand the {n} words to the wrapper in order",
         "reg [2:0] cnt = 3'd0; reg [1:0] st = 2'd0; reg [2:0] oc = 3'd0; reg fire = 1'b0;",
         f"reg [31:0] inw [0:{n - 1}]; reg [31:0] outw [0:{n - 1}]; reg [{n - 1}:0] have = {n}'d0;",
         "assign in_x_in_ack = (st == 2'd0);"]
    conn = []
    for i, e in enumerate(ents):
        conn.append(f".in_{idx(e)}_data(inw[{i}]), .in_{idx(e)}_valid(fire)")
    for i, e in enumerate(exits):
        L.append(f"wire [31:0] d_o{i}; wire v_o{i};")
        conn.append(f".out_{idx(e)}_data(d_o{i}), .out_{idx(e)}_valid(v_o{i})")
    L.append(f"{dut_top} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), " + ", ".join(conn) + ");")
    L.append("assign out_y_out_valid = (st == 2'd2); assign out_y_out_data = outw[oc];")
    L += ["always @(posedge clk) begin", "    fire <= 1'b0;", "    if (rst) begin cnt <= 3'd0; st <= 2'd0; oc <= 3'd0; have <= 0; end else begin"]
    for i in range(n):
        L.append(f"        if (v_o{i}) begin outw[{i}] <= d_o{i}; have[{i}] <= 1'b1; end")
    L += ["        case (st)",
          f"        2'd0: if (in_x_in_valid) begin inw[cnt] <= in_x_in_data; if (cnt == 3'd{n - 1}) begin cnt <= 3'd0; fire <= 1'b1; st <= 2'd1; have <= 0; end else cnt <= cnt + 3'd1; end",
          f"        2'd1: if (have == {{{n}{{1'b1}}}}) begin st <= 2'd2; oc <= 3'd0; end",
          f"        2'd2: if (out_y_out_ack) begin if (oc == 3'd{n - 1}) st <= 2'd0; else oc <= oc + 3'd1; end",
          "        default: st <= 2'd0;", "        endcase", "    end", "end", "endmodule"]
    return "\n".join(L) + "\n"


def make(work, name, n_words, core_override=None):
    g, ents, exits = T.build_grid(core_override)
    icm = os.path.join(work, name + ".icm"); IcmV3File(name=name, records=g.records()).save(icm)
    gen = os.path.join(work, "gen_" + name)
    top, files = BL.assemble(["-s", "sub", "--icm", icm, "--top", "tiles_dut"], gen)
    sp = os.path.join(gen, "tiles_shim.v"); open(sp, "w").write(sub_shim(top, ents, exits))
    r = random.Random(1184); xs = [r.getrandbits(32) for _ in range(n_words * len(ents))]
    return top, files + [sp], xs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "fpga", "board_tests_sub_tiles")); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--no-pnr", action="store_true"); ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--bite", action="store_true")
    a = ap.parse_args(); out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True); work = tempfile.mkdtemp(prefix="bsubtiles_")
    name = "tiles_sub"
    if a.bite:
        top, files, xs = make(work, "tiles_sub_bite", a.n, "ram")
        import board_tests_v1 as bt
        wd = os.path.join(work, "w_bite"); os.makedirs(wd)
        open(os.path.join(wd, "board_uart_tx.v"), "w").write(bt.UART_V)
        open(os.path.join(wd, "board_top_bite.v"), "w").write(bt.wrapper("bite", "tiles_shim", {"x_in": xs}, "y_out", xs, False, True, bt.CPB, bt.SETTLE, bt.TIMEOUT))
        sim = bt.simulate(wd, "bite", [os.path.join(wd, "board_uart_tx.v"), os.path.join(wd, "board_top_bite.v")] + files)
        print(next((l for l in sim.splitlines() if l.startswith("UCT")), sim[-400:])); return
    top, files, xs = make(work, name, a.n)
    what = "NATIVE cross + corner (turn 0, turn 1) tiles in the SUB family: 6 streams x %d words, six streams at the same time, output must equal input, random exit stalls" % a.n
    r = BL.build(name, what, "stream", "tiles_shim", files, None, xs, xs, out, not a.no_pnr, a.seed, work)
    print("   ok: %s   %s LUT4  Fmax %s" % (r["sim_line"], r.get("lut4", "-"), r.get("fmax_mhz", "-")))
    for fn in ("run_all.bat", "board_run.py", "board_collect.py", "run_one.sh", "run_all.sh", "run_all_v2.sh", "run_one_v2.sh", "watch_serial.py"):
        src = os.path.join(ROOT, "fpga", "board_tests_loops", fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(out, fn))


if __name__ == "__main__":
    main()
