#!/usr/bin/env python3
"""tools/board_tiles_v1.py -- ledger #1169: a board bitstream for the NATIVE cross and corner cells (flex family, #1165).
One generated flex design holds three tiles stacked in a grid: a CROSS (W->E and N->S) and a CORNER with turn 0 (W->S and E->N) and a CORNER with turn 1 (W->N and E->S).
Two independent streams enter each tile (six streams in all), through two relay cells per arm; a tiny shim in front of the design hands the input words round-robin to the six
streams and takes the outputs back in the same order, so the board wrapper (the one used by every other card test) sees ONE stream in and ONE stream out and the expected
output equals the input. A tile that mixed, swapped or lost a stream would change the order or the words and the test would FAIL (the bite is checked in simulation: a cross built as
an ordinary ram relay mixes the streams).
  python3 tools/board_tiles_v1.py [--out fpga/board_tests_tiles] [--seed N] [--no-pnr] [--n 8]"""
import argparse, os, random, re, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "nano"))
import board_loops_v1 as BL                                   # noqa: E402
from flex_layout_v1 import Grid                               # noqa: E402
from icm_v3 import IcmV3File                                  # noqa: E402
ROOT = BL.ROOT
ARM = {"W": [(2, 0), (2, 1)], "E": [(2, 4), (2, 3)], "N": [(0, 2), (1, 2)], "S": [(4, 2), (3, 2)]}      # outer cell first, inner (next to the tile) second
TILES = [("x", "cross", None, {"W": "E", "N": "S"}), ("c0", "corner", 0, {"W": "S", "E": "N"}), ("c1", "corner", 1, {"W": "N", "E": "S"})]


def build_grid(core_override=None):
    g = Grid(rows=5 * len(TILES), cols=5); ents, exits = [], []
    for t, (pre, core, turn, pairs) in enumerate(TILES):
        r0 = 5 * t
        g.add(pre + "_T", r0 + 2, 2, core_override or core, ({"turn": turn} if (turn is not None and not core_override) else None))
        for arm, out in pairs.items():
            for k, (r, c) in enumerate(ARM[arm]):
                g.add(f"{pre}_{arm}{k}", r0 + r, c)
            for k, (r, c) in enumerate(ARM[out]):
                g.add(f"{pre}_{out}{k}", r0 + r, c)
            g.link(f"{pre}_{arm}0", f"{pre}_{arm}1"); g.link(f"{pre}_{arm}1", pre + "_T")
            g.link(pre + "_T", f"{pre}_{out}1"); g.link(f"{pre}_{out}1", f"{pre}_{out}0")
            ents.append(f"{pre}_{arm}0"); exits.append(f"{pre}_{out}0")
    return g, ents, exits


def shim(dut_top, ents, exits):
    n = len(ents); idx = lambda s: re.sub(r"\W", "_", s)
    L = ["`default_nettype none", "module tiles_shim (input wire clk, input wire rst, input wire cfg_valid,",
         "    input wire [31:0] in_x_in_data, input wire in_x_in_valid, output wire in_x_in_ack,",
         "    output wire [31:0] out_y_out_data, output wire out_y_out_valid, input wire out_y_out_ack);",
         f"reg [2:0] ti = 3'd0; reg [2:0] to = 3'd0;"]
    conn = []
    for k, e in enumerate(ents):
        L.append(f"wire ack_i{k}; wire v_i{k} = in_x_in_valid && (ti == 3'd{k});")
        conn.append(f".in_{idx(e)}_data(in_x_in_data), .in_{idx(e)}_valid(v_i{k}), .in_{idx(e)}_ack(ack_i{k})")
    for k, e in enumerate(exits):
        L.append(f"wire [31:0] d_o{k}; wire v_o{k}; wire a_o{k} = out_y_out_ack && (to == 3'd{k});")
        conn.append(f".out_{idx(e)}_data(d_o{k}), .out_{idx(e)}_valid(v_o{k}), .out_{idx(e)}_ack(a_o{k})")
    L.append(f"{dut_top} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), " + ", ".join(conn) + ");")
    L.append("assign in_x_in_ack = " + " : ".join(f"(ti == 3'd{k}) ? ack_i{k}" for k in range(n)) + " : 1'b0;")
    L.append("assign out_y_out_data = " + " : ".join(f"(to == 3'd{k}) ? d_o{k}" for k in range(n)) + " : 32'd0;")
    L.append("assign out_y_out_valid = " + " : ".join(f"(to == 3'd{k}) ? v_o{k}" for k in range(n)) + " : 1'b0;")
    L.append(f"always @(posedge clk) begin if (rst) begin ti <= 3'd0; to <= 3'd0; end else begin")
    L.append(f"    if (in_x_in_valid && in_x_in_ack) ti <= (ti == 3'd{n - 1}) ? 3'd0 : ti + 3'd1;")
    L.append(f"    if (out_y_out_valid && out_y_out_ack) to <= (to == 3'd{n - 1}) ? 3'd0 : to + 3'd1;")
    L.append("end end"); L.append("endmodule")
    return "\n".join(L) + "\n"


def make(work, name, n_words, core_override=None):
    g, ents, exits = build_grid(core_override)
    icm = os.path.join(work, name + ".icm"); IcmV3File(name=name, records=g.records()).save(icm)
    gen = os.path.join(work, "gen_" + name)
    top, files = BL.assemble(["-s", "flex", "--icm", icm, "--top", "tiles_dut"], gen)
    sp = os.path.join(gen, "tiles_shim.v"); open(sp, "w").write(shim(top, ents, exits))
    r = random.Random(1169); xs = [r.getrandbits(32) for _ in range(n_words * len(ents))]
    return top, files + [sp], xs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "fpga", "board_tests_tiles")); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--no-pnr", action="store_true"); ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--bite", action="store_true", help="build the control with every tile an ordinary ram relay: the board wrapper must report FAIL in simulation")
    a = ap.parse_args(); out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True); work = tempfile.mkdtemp(prefix="btiles_")
    name = "tiles_flex"
    if a.bite:
        top, files, xs = make(work, "tiles_bite", a.n, "ram")
        import board_tests_v1 as bt, subprocess, shutil
        wd = os.path.join(work, "w_bite"); os.makedirs(wd)
        open(os.path.join(wd, "board_uart_tx.v"), "w").write(bt.UART_V)
        open(os.path.join(wd, "board_top_bite.v"), "w").write(bt.wrapper("bite", "tiles_shim", {"x_in": xs}, "y_out", xs, False, True, bt.CPB, bt.SETTLE, bt.TIMEOUT))
        sim = bt.simulate(wd, "bite", [os.path.join(wd, "board_uart_tx.v"), os.path.join(wd, "board_top_bite.v")] + files)
        print(next((l for l in sim.splitlines() if l.startswith("UCT")), sim[-400:])); return
    top, files, xs = make(work, name, a.n)
    what = "NATIVE cross + corner (turn 0, turn 1) tiles: %d streams x %d words through three tiles, round-robin in and out, output must equal input, random exit stalls" % (6, a.n)
    r = BL.build(name, what, "stream", "tiles_shim", files, None, xs, xs, out, not a.no_pnr, a.seed, work)
    print("   ok: %s   %s LUT4  Fmax %s" % (r["sim_line"], r.get("lut4", "-"), r.get("fmax_mhz", "-")))
    import shutil
    for fn in ("run_all.bat", "board_run.py", "board_collect.py", "run_one.sh", "run_all.sh", "run_all_v2.sh", "run_one_v2.sh", "watch_serial.py"):
        src = os.path.join(ROOT, "fpga", "board_tests_loops", fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(out, fn))


if __name__ == "__main__":
    main()
