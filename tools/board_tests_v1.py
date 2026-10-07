#!/usr/bin/env python3
"""tools/board_tests_v1.py -- ledger #1023: the ON-BOARD TEST PACKAGE for the Tang Nano 20K (Alan: "generate the bitstream, plus a test file for each, so I can run a batch file which gathers the results into one file").

For each test design (a flex design made from an ICM file by the normal generator) this builds a SELF-CHECKING bitstream:
  * the generated flex design is the device under test;
  * a small wrapper feeds it a fixed set of input words (back-to-back, or with random gaps / exit stalls), captures what comes out, and compares it with the EXPECTED words stored in the
    bitstream (computed by FlexGrid, the VM's flex mirror, which is proven equal to the generated hardware);
  * after the results settle it prints ONE LINE over the board's USB serial port (pin 69, 115200 baud, repeated every ~0.3 s) and shows pass / fail on the LEDs
    (LED0 heartbeat, LED1 on = PASS, LED2 on = FAIL, LED3 on = finished; the LEDs are active low).
Every wrapper is also simulated here in iverilog with the real UART bit timing shrunk, and the decoded line must say PASS, so a package is only written if each test passes in simulation first.

Output folder (default fpga/board_tests/): <name>.fs (bitstream), <name>.v / .cst / .json (what is inside), run_all.bat, board_run.py, README.md.

  python3 tools/board_tests_v1.py [--out DIR] [--only a,b] [--seed N] [--no-pnr]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("nano", "tools"):
    sys.path.insert(0, os.path.join(ROOT, sub))
from icm_v3 import IcmV3File, IcmV3Record  # noqa: E402

DEVICE = "GW2AR-LV18QN88C8/I7"
CLK_HZ = 27_000_000
BAUD = 115200
CPB = round(CLK_HZ / BAUD)                 # 234 clocks per UART bit
SETTLE = 1 << 17                           # quiet cycles after the last expected word before the verdict (nothing extra may arrive)
TIMEOUT = 1 << 25                          # about 1.2 s: give up
KEEP = 8                                   # captured words echoed in the report line

PINS = {"BOARD_CLK": 4, "UART_TX": 69, "LED0_N": 15, "LED1_N": 16, "LED2_N": 17, "LED3_N": 18}   # docs/man/tang-nano-20k.man.json


# --------------------------------------------------------------------------- the designs
def ram(cid, r, c, up, down, **kw):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down}, **kw)


def adder(cid, r, c, up, down, sub=0):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="adder", core_config={"upstream_mask": up, "downstream_mask": down, "subtract_mode": sub})


def pri(mode, ranks=(1, 0, 2), order=None):
    cfg = {"upstream_mask": ["n", "w", "s"], "downstream_mask": ["e"], "scheduling_mode": mode}
    for f, rk in zip(("n", "w", "s"), ranks):
        cfg[f"priority_rank_{f}"] = rk
    if order:
        d = {"n": 0, "s": 1, "e": 2, "w": 3}
        cfg["sequence_len"] = len(order)
        for k, f in enumerate(order):
            cfg[f"sequence_{k}"] = d[f]
    return [IcmV3Record(cell_id="P", row=1, col=1, core="priority", core_config=cfg), ram("O", 1, 2, ["w"], []),
            ram("E1", 0, 1, [], ["s"]), ram("E2", 1, 0, [], ["e"]), ram("E3", 2, 1, [], ["n"])]


def d_relay():
    return [ram("E", 0, 0, [], ["e"])] + [ram(f"R{k}", 0, k, ["w"], ["e"]) for k in range(1, 4)] + [ram("O", 0, 4, ["w"], [])]


def d_adder():       # X reaches the adder in one hop, Y through a relay (two hops): the generator needs a defined operand order
    return [ram("X", 0, 2, [], ["s"]), ram("Y", 1, 0, [], ["e"]), ram("R", 1, 1, ["w"], ["e"]), adder("A", 1, 2, ["w", "n"], ["e"]), ram("O", 1, 3, ["w"], [])]


def d_adder_const():
    k = IcmV3Record(cell_id="K", row=1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"], "fixed_mode": 1, "load_data_valid": 1, "init_data": 5})
    return [ram("X", 0, 0, [], ["e"]), ram("R", 0, 1, ["w"], ["s"]), k, adder("A", 1, 1, ["n", "w"], ["e"]), ram("O", 1, 2, ["w"], [])]


def d_hold():
    h = IcmV3Record(cell_id="H", row=1, col=1, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], "fixed_mode": 1})
    return [ram("W", 1, 0, [], ["e"]), h, ram("X", 0, 2, [], ["s"]), adder("A", 1, 2, ["w", "n"], ["e"]), ram("O", 1, 3, ["w"], [])]


def d_oneshot():
    k = IcmV3Record(cell_id="K", row=0, col=1, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["s"], "init_data": 100, "load_data_valid": 1})
    return [k, ram("E", 0, 0, [], ["s"]), ram("R", 1, 0, ["n"], ["e"]), adder("A", 1, 1, ["n", "w"], ["e"]), ram("O", 1, 2, ["w"], [])]


S3 = {"E1": [11, 12, 13, 14, 15, 16], "E2": [21, 22, 23, 24, 25, 26], "E3": [31, 32, 33, 34, 35, 36]}
# name, what it proves, records, input streams, input gaps, exit stalls
TESTS = [
    ("relay_chain", "four ram cells in a row pass 16 distinct words through unchanged (the basic handshake)", d_relay,
     {"E": [0x00000001, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0x12345678, 0xDEADBEEF, 0xA5A5A5A5, 0x5A5A5A5A, 0, 1, 2, 3, 0xCAFEF00D, 0x0F0F0F0F, 0xF0F0F0F0, 42]}, False, False),
    ("relay_chain_stalled", "the same chain with random gaps on the input and random stalls on the output (nothing lost, repeated or reordered)", d_relay,
     {"E": [0x1000 + 17 * k for k in range(24)]}, True, True),
    ("adder_stream", "an adder joins two streams, 12 sums (32-bit wraparound included)", d_adder,
     {"X": [1, 2, 3, 0xFFFFFFFF, 0x7FFFFFFF, 100, 200, 300, 0x80000000, 5, 6, 7], "Y": [10, 20, 30, 1, 1, 0xFFFFFF00, 5, 6, 0x80000000, 1, 2, 3]}, False, False),
    ("adder_stalled", "the adder with random gaps on both inputs and random output stalls", d_adder,
     {"X": [3 * k + 1 for k in range(20)], "Y": [1000 + k for k in range(20)]}, True, True),
    ("adder_constant", "a fixed-mode ram feeds the constant 5 to an adder (offered on every tick, never used up)", d_adder_const,
     {"X": [1, 2, 3, 4, 5, 6, 7, 8]}, False, False),
    ("ram_hold", "the ram's HOLD behaviour: 7 is written once and added to six items; it is offered again each time (never used up) (#1021)", d_hold,
     {"W": [7], "X": [1, 2, 3, 4, 5, 6]}, False, False),
    ("ram_oneshot", "the ram's ONE-SHOT preload: the configured 100 is offered once; only the first item sees it, the rest wait (#1021)", d_oneshot,
     {"E": [10, 20, 30]}, False, False),
    ("priority_strict", "priority core, strict ranks west > north > south, three sources of six items", lambda: pri(0, (1, 0, 2)), S3, False, False),
    ("priority_weighted", "priority core, weighted round robin (weights north 1, west 3, south 2)", lambda: pri(1, (1, 3, 2)), S3, False, False),
    ("priority_sequenced", "priority core, sequenced channel with the fixed turn order south, west, west, north", lambda: pri(2, (0, 0, 0), ("s", "w", "w", "n")), S3, False, False),
]


# --------------------------------------------------------------------------- expected results (FlexGrid, the VM's flex mirror)
def expected(recs, streams, out="O", ticks=900):
    import flex_grid_v1 as fg
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = fg.FlexGrid(recs)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    todo = {k: list(v) for k, v in streams.items()}
    seen, e = [], g.cells[pos[out]]
    for _ in range(ticks):
        for k, vals in todo.items():
            c = g.cells[pos[k]]
            if vals and not c.ram_data_valid and not g._pending.get(pos[k]):
                g.inject(*pos[k], vals.pop(0))
        g.tick()
        if e.ram_data_valid:
            seen.append(e.ram_data_reg)
            e.ram_data_valid = False
    return seen


# --------------------------------------------------------------------------- the wrapper
UART_V = f"""// board_uart_tx.v -- 8N1 transmitter, CPB clocks per bit (ledger #1023)
`default_nettype none
module board_uart_tx #(parameter integer CPB = {CPB}) (input wire clk, input wire start, input wire [7:0] data, output reg tx, output wire busy);
    reg [3:0] nbit = 4'd0; reg [15:0] cnt = 16'd0; reg [9:0] sh = 10'h3FF;
    assign busy = (nbit != 4'd0);
    initial tx = 1'b1;
    always @(posedge clk) begin
        if (nbit == 4'd0) begin
            tx <= 1'b1;
            if (start) begin sh <= {{1'b1, data, 1'b0}}; nbit <= 4'd10; cnt <= CPB - 1; end
        end else begin
            tx <= sh[0];
            if (cnt == 16'd0) begin sh <= {{1'b1, sh[9:1]}}; nbit <= nbit - 4'd1; cnt <= CPB - 1; end else cnt <= cnt - 16'd1;
        end
    end
endmodule
"""


def wrapper(name, dut_top, entries, exits, exp, gaps, stalls, cpb, settle, timeout):
    """entries: {port: [words]}; exits: the single exit port name; exp: expected words."""
    n_exp = len(exp)
    lines = [f"// board_top_{name}.v -- GENERATED by tools/board_tests_v1.py (ledger #1023); do not hand-edit.",
             "`default_nettype none", "`timescale 1ns / 1ps",
             f"module board_top_{name} #(parameter integer CPB = {cpb}, parameter integer SETTLE = {settle}, parameter integer TIMEOUT = {timeout}) (",
             "    input wire BOARD_CLK, output wire UART_TX, output wire LED0_N, output wire LED1_N, output wire LED2_N, output wire LED3_N);",
             "wire clk = BOARD_CLK;",
             "reg [7:0] por_cnt = 8'h00; wire rst = (por_cnt != 8'hFF); always @(posedge clk) if (rst) por_cnt <= por_cnt + 8'd1;",
             "reg [3:0] cfg_sr = 4'hF; always @(posedge clk) if (!rst) cfg_sr <= {cfg_sr[2:0], 1'b0};",
             "wire cfg_valid = !rst && cfg_sr[3] && !cfg_sr[2];",
             "reg [5:0] wait_cnt = 6'd0; reg started = 1'b0;",
             "always @(posedge clk) if (!rst && !cfg_sr[3] && !started) begin wait_cnt <= wait_cnt + 6'd1; if (wait_cnt == 6'd8) started <= 1'b1; end",
             "reg [31:0] lfsr = 32'hACE1ACE1; always @(posedge clk) lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};",
             "reg done = 1'b0;"]
    conn, drv = [], []
    for k, (port, vals) in enumerate(sorted(entries.items())):
        n = len(vals)
        lines.append(f"reg [31:0] mem_{port} [0:{n}]; integer idx_{port} = 0; reg act_{port} = 1'b0; wire ack_{port};")
        lines.append("initial begin " + " ".join(f"mem_{port}[{j}] = 32'h{v & 0xFFFFFFFF:08X};" for j, v in enumerate(vals)) + f" mem_{port}[{n}] = 32'h0; end")
        lines.append(f"wire [31:0] d_{port} = mem_{port}[idx_{port}];")
        gap = f"(lfsr[{(3 * k + 2) % 31}] | lfsr[{(5 * k + 7) % 31}])" if gaps else "1'b1"
        drv.append(f"    if (act_{port} && ack_{port}) begin idx_{port} <= idx_{port} + 1; act_{port} <= 1'b0; end\n"
                   f"    else if (!act_{port} && idx_{port} < {n} && {gap}) act_{port} <= 1'b1;")
        conn.append(f".in_{port}_data(d_{port}), .in_{port}_valid(act_{port}), .in_{port}_ack(ack_{port})")
    lines.append("always @(posedge clk) if (started && !done) begin")
    lines += drv
    lines.append("end")
    ready = "lfsr[19]" if stalls else "1'b1"
    lines.append(f"wire [31:0] od; wire ov; wire oa = {ready};")
    conn.append(f".out_{exits}_data(od), .out_{exits}_valid(ov), .out_{exits}_ack(oa)")
    lines.append(f"{dut_top} dut (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {', '.join(conn)});")
    E = max(n_exp, 1)
    lines.append(f"reg [31:0] expm [0:{E}]; initial begin " + " ".join(f"expm[{j}] = 32'h{v & 0xFFFFFFFF:08X};" for j, v in enumerate(exp)) + f" expm[{E}] = 32'h0; end")
    lines += ["reg [15:0] cnt = 16'd0, bad = 16'd0; reg [31:0] sig = 32'd0, cyc = 32'd0, last = 32'd0, quiet = 32'd0; reg timed_out = 1'b0;"]
    for j in range(KEEP):
        lines.append(f"reg [31:0] w{j} = 32'd0;")
    lines.append(f"wire [15:0] want = 16'd{n_exp};")
    lines.append("wire cap = ov && oa && started && !done;")
    lines.append("always @(posedge clk) begin")
    lines.append("    if (started && !done) begin")
    lines.append("        cyc <= cyc + 32'd1; quiet <= quiet + 32'd1;")
    lines.append("        if (cap) begin")
    lines.append("            cnt <= cnt + 16'd1; last <= cyc; quiet <= 32'd0; sig <= {sig[30:0], sig[31]} ^ od;")
    lines.append(f"            if (cnt >= want || od != expm[cnt]) bad <= bad + 16'd1;")
    for j in range(KEEP):
        lines.append(f"            if (cnt == 16'd{j}) w{j} <= od;")
    lines.append("        end")
    lines.append("        if (cnt >= want && quiet >= SETTLE) done <= 1'b1;")
    lines.append("        if (cyc >= TIMEOUT) begin done <= 1'b1; timed_out <= (cnt < want); end")
    lines.append("    end")
    lines.append("end")
    lines.append("wire pass = done && !timed_out && (cnt == want) && (bad == 16'd0);")
    # ---- the report line
    items = [("s", "UCT " + name + " res=")]
    items += [("c", "pass ? 8'h50 : 8'h46")]                     # P / F
    items += [("s", " n="), ("h", "cnt", 4), ("s", " e="), ("h", "want", 4), ("s", " bad="), ("h", "bad", 4), ("s", " to="), ("h", "{15'd0, timed_out}", 1),
              ("s", " last="), ("h", "last", 8), ("s", " sig="), ("h", "sig", 8), ("s", " w=")]
    for j in range(min(KEEP, max(n_exp, 1))):
        if j:
            items.append(("s", ","))
        items.append(("h", f"w{j}", 8))
    items.append(("s", "\r\n"))
    body, idx = [], 0
    for it in items:
        if it[0] == "s":
            for ch in it[1]:
                body.append(f"        10'd{idx}: msg_byte = 8'h{ord(ch):02X};")
                idx += 1
        elif it[0] == "c":
            body.append(f"        10'd{idx}: msg_byte = {it[1]};")
            idx += 1
        else:
            _, expr, nd = it
            for d in range(nd):
                sh = (nd - 1 - d) * 4
                body.append(f"        10'd{idx}: msg_byte = hexch(({expr} >> {sh}) & 4'hF);")
                idx += 1
    lines.append("function [7:0] hexch(input [3:0] v); hexch = (v < 4'd10) ? (8'h30 + v) : (8'h41 + v - 4'd10); endfunction")
    lines.append("reg [9:0] mi = 10'd0;")
    lines.append("reg [7:0] msg_byte_r; function [7:0] msg_byte(input [9:0] i); begin case (i)")
    lines += body
    lines.append("        default: msg_byte = 8'h20; endcase end endfunction")
    lines.append(f"localparam integer MSGLEN = {idx};")
    lines.append("wire tx_busy; reg tx_start = 1'b0; reg [7:0] tx_data = 8'h00; reg [31:0] gapc = 32'd0; reg [1:0] ps = 2'd0;")
    lines.append("board_uart_tx #(.CPB(CPB)) utx (.clk(clk), .start(tx_start), .data(tx_data), .tx(UART_TX), .busy(tx_busy));")
    lines.append("always @(posedge clk) begin")
    lines.append("    tx_start <= 1'b0;")
    lines.append("    case (ps)")
    lines.append("        2'd0: if (done) begin mi <= 10'd0; ps <= 2'd1; end")
    lines.append("        2'd1: if (!tx_busy && !tx_start) begin tx_data <= msg_byte(mi); tx_start <= 1'b1; ps <= 2'd2; end")
    lines.append("        2'd2: if (tx_busy) begin if (mi == MSGLEN - 1) begin gapc <= 32'd0; ps <= 2'd3; end else begin mi <= mi + 10'd1; ps <= 2'd1; end end")
    lines.append("        2'd3: if (!tx_busy) begin gapc <= gapc + 32'd1; if (gapc >= SETTLE * 4) ps <= 2'd0; end")
    lines.append("    endcase")
    lines.append("end")
    lines.append("reg [23:0] hb = 24'd0; always @(posedge clk) hb <= hb + 24'd1;")
    lines.append("assign LED0_N = ~hb[23]; assign LED1_N = ~pass; assign LED2_N = ~(done && !pass); assign LED3_N = ~done;")
    lines.append("endmodule")
    return "\n".join(lines) + "\n"


def cst():
    out = []
    for p, n in PINS.items():
        out.append(f'IO_LOC "{p}" {n};')
        out.append(f'IO_PORT "{p}" IO_TYPE=LVCMOS33' + (" PULL_MODE=NONE" if p == "BOARD_CLK" else " DRIVE=8") + ";")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- simulation (UART decoded in iverilog)
def simulate(work, name, files, entries_unused=None):
    tb = f"""`timescale 1ns/1ps
module tbb;
  reg clk = 0; wire tx, l0, l1, l2, l3;
  board_top_{name} #(.CPB(8), .SETTLE(2000), .TIMEOUT(2000000)) dut (.BOARD_CLK(clk), .UART_TX(tx), .LED0_N(l0), .LED1_N(l1), .LED2_N(l2), .LED3_N(l3));
  always #5 clk = ~clk;
  reg [7:0] b; integer i, lines = 0;
  initial begin
    forever begin
      @(negedge tx);
      repeat (4) @(posedge clk);
      for (i = 0; i < 8; i = i + 1) begin repeat (8) @(posedge clk); b[i] = tx; end
      repeat (8) @(posedge clk);
      $write("%c", b);
      if (b == 8'h0A) begin lines = lines + 1; if (lines >= 2) $finish; end
    end
  end
  initial begin #300000000; $display("SIMTIMEOUT"); $finish; end
endmodule
"""
    open(os.path.join(work, "tbb.v"), "w").write(tb)
    c = subprocess.run(["iverilog", "-g2012", "-o", "tbb.vvp", "tbb.v"] + files, cwd=work, capture_output=True, text=True)
    if c.returncode:
        raise RuntimeError("iverilog: " + c.stderr[:600])
    return subprocess.run(["vvp", "tbb.vvp"], cwd=work, capture_output=True, text=True, timeout=1500).stdout


# --------------------------------------------------------------------------- build
def build_one(name, desc, mk, streams, gaps, stalls, out, pnr=True, seed=1):
    recs = mk()
    exp = expected(recs, streams)
    if not exp:
        raise RuntimeError(f"{name}: the VM produced no output")
    work = os.path.join(out, "_work_" + name)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    icm = os.path.join(work, name + ".icm")
    IcmV3File(name=name, records=recs).save(icm)
    gen = os.path.join(work, "gen")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "project_assemble_v1.py"), "-s", "flex", "--icm", icm, "--output", gen], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{name}: generator: {r.stderr[-400:]}{r.stdout[-400:]}")
    rec = json.load(open(os.path.join(gen, "ASSEMBLY.json")))
    srcs = [os.path.join(gen, f) for f in rec["files"] if f.endswith(".v")]
    top = f"board_top_{name}"
    open(os.path.join(work, "board_uart_tx.v"), "w").write(UART_V)
    open(os.path.join(work, top + ".v"), "w").write(wrapper(name, rec["top"], streams, "O", exp, gaps, stalls, CPB, SETTLE, TIMEOUT))
    open(os.path.join(work, top + "_sim.v"), "w").write(open(os.path.join(work, top + ".v")).read())
    files = [os.path.join(work, "board_uart_tx.v"), os.path.join(work, top + ".v")] + srcs
    # 1. simulate with the real UART text decoded
    sim = simulate(work, name, files)
    line = next((l for l in sim.splitlines() if l.startswith("UCT")), "")
    if " res=P " not in line + " ":
        raise RuntimeError(f"{name}: the wrapper FAILED in simulation (the package is not written): {sim[-500:]}")
    res = dict(name=name, what=desc, expected=[int(v) & 0xFFFFFFFF for v in exp], sim_line=line.strip(), inputs={k: list(v) for k, v in streams.items()}, gaps=gaps, stalls=stalls)
    # 2. synthesise, place and route, pack
    open(os.path.join(out, name + ".cst"), "w").write(cst())
    shutil.copy(os.path.join(work, top + ".v"), os.path.join(out, name + ".v"))
    if pnr:
        s = subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {' '.join(files)}; hierarchy -top {top}; synth_gowin -top {top} -nowidelut -json {name}.json"], cwd=work, capture_output=True, text=True, timeout=3000)
        if s.returncode:
            raise RuntimeError(f"{name}: yosys: {s.stderr[-500:]}")
        shutil.copy(os.path.join(out, name + ".cst"), os.path.join(work, name + ".cst"))
        p = subprocess.run(["yowasp-nextpnr-himbaechel-gowin", "--device", DEVICE, "--vopt", "family=GW2A-18C", "--vopt", f"cst={name}.cst", "--seed", str(seed), "--json", f"{name}.json",
                            "--write", f"{name}_r.json", "--report", f"{name}_rep.json", "--freq", "27"], cwd=work, capture_output=True, text=True, timeout=3000)
        if p.returncode:
            raise RuntimeError(f"{name}: nextpnr: {p.stderr[-600:]}")
        rep = json.load(open(os.path.join(work, name + "_rep.json")))
        fmax = rep["fmax"]["clk"]["achieved"] if "clk" in rep["fmax"] else min(v["achieved"] for v in rep["fmax"].values())
        u = rep["utilization"]
        res.update(fmax_mhz=round(fmax, 1), lut4=u["LUT4"]["used"], dff=u["DFF"]["used"])
        if fmax < 27:
            raise RuntimeError(f"{name}: timing NOT met at 27 MHz (Fmax {fmax:.1f}); not shipped")
        g = subprocess.run(["gowin_pack", "-d", DEVICE, "-o", os.path.join(out, name + ".fs"), "-s", os.path.join(work, name + ".cst"), f"{name}_r.json"], cwd=work, capture_output=True, text=True)
        if g.returncode:
            raise RuntimeError(f"{name}: gowin_pack: {g.stderr[-400:]}")
    json.dump(res, open(os.path.join(out, name + ".json"), "w"), indent=1)
    shutil.rmtree(work, ignore_errors=True)
    return res


BAT = r"""@echo off
:: run_all.bat -- ledger #1023: load each self-checking test bitstream onto the Tang Nano 20K, read its result line from the
:: board's USB serial port, and gather everything into ONE file: board_results.txt (also board_results.csv).
::
:: Needs: openFPGALoader and Python with pyserial (pip install pyserial) on this PC; the board plugged in by USB-C.
:: Usage:  run_all.bat            (auto-detects the serial port)
::         run_all.bat COM7      (name the serial port yourself: the board's second COM port is usually the FPGA UART)
:: Each bitstream goes to SRAM (lost at power-off, the flash is NOT touched).
setlocal enabledelayedexpansion
cd /d "%~dp0"
set PORT=%1
python board_run.py %PORT%
echo.
echo Finished. Results are in %~dp0board_results.txt
pause
"""

SH = r"""#!/bin/sh
# run_all.sh -- ledger #1023 (Linux): load each self-checking test bitstream onto the Tang Nano 20K, read its result line from the
# board's USB serial port, and gather everything into ONE file: board_results.txt (also board_results.csv).
#
# Needs: openFPGALoader, python3 with pyserial (sudo apt install openfpgaloader python3-serial), the board plugged in by USB-C, and
# permission for the USB devices: add yourself to the dialout group once (sudo usermod -aG dialout $USER, then log out and in),
# or run this with sudo.
# Usage:  ./run_all.sh              (auto-detects the serial port)
#         ./run_all.sh /dev/ttyUSB1 (name it yourself: the board shows two ports, the FPGA UART is the second)
cd "$(dirname "$0")" || exit 1
python3 board_run.py "$1"
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
"""

RUNPY = r'''#!/usr/bin/env python3
"""board_run.py -- loads every <name>.fs next to this file with openFPGALoader, listens to the board's serial port for the test's result line, and writes ONE results file
(board_results.txt, plus board_results.csv). Ledger #1023.  usage: python board_run.py [COMPORT]"""
import csv
import glob
import json
import os
import re
import subprocess
import sys
import time
import datetime

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial is missing: run   pip install pyserial   and try again")

HERE = os.path.dirname(os.path.abspath(__file__))
BAUD = 115200
LISTEN_S = 6.0


def serial_ports():
    """every serial port the PC currently shows (the BL616 can come back under another name after the FPGA is reprogrammed)"""
    return sorted(p.device for p in list_ports.comports())


def pick_port(arg):
    if arg:
        return arg
    ports = [p for p in list_ports.comports()]
    if not ports:
        sys.exit("no serial port found: plug the board in, or name it:  python3 board_run.py /dev/ttyUSB1   (Windows: COM7)")
    ports.sort(key=lambda p: p.device)
    return ports[-1].device       # the Tang Nano 20K shows two ports; the FPGA UART is the second one


def load(fs):
    r = subprocess.run(["openFPGALoader", "-b", "tangnano20k", fs], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr)[-400:]


def read_lines(ser, seconds, want=2):
    """read from an ALREADY OPEN port for `seconds`, return the UCT lines (the port is never closed between tests: some USB-serial bridges stop sending after a close/open)"""
    got = []
    t0, buf = time.time(), b""
    while time.time() - t0 < seconds:
        try:
            buf += ser.read(256)
        except (serial.SerialException, OSError):
            return got, True            # the port vanished
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            text = line.decode("ascii", "replace").strip()
            if text.startswith("UCT"):
                got.append(text)
                if len(got) >= want:
                    return got, False
    return got, False


def open_port(port):
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, BAUD, 0.2
    s.dtr = False                       # do not toggle the bridge's modem lines
    s.rts = False
    s.open()
    return s


def listen(ser, port):
    """listen on the held-open port; if it is gone (or silent) try reopening it, then every other serial port. returns (lines, ser, port, ports seen, note)"""
    time.sleep(1.0)
    seen = serial_ports()
    lines, gone = read_lines(ser, LISTEN_S)
    if lines:
        return lines, ser, port, seen, "held-open port"
    note = "held-open port silent" if not gone else "held-open port vanished"
    try:
        ser.close()
    except Exception:  # noqa: BLE001
        pass
    for p in [port] + [x for x in seen if x != port]:
        try:
            ser = open_port(p)
        except (serial.SerialException, OSError):
            continue
        lines, gone = read_lines(ser, 3.0)
        if lines:
            return lines, ser, p, seen, note + "; answered after reopening " + p
        ser.close()
    try:
        ser = open_port(port)
    except (serial.SerialException, OSError):
        ser = None
    return [], ser, port, seen, note + "; nothing on any port"


def main():
    port = pick_port(sys.argv[1] if len(sys.argv) > 1 else None)
    tests = sorted(glob.glob(os.path.join(HERE, "*.fs")))
    if not tests:
        sys.exit("no .fs files next to board_run.py")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ser = open_port(port)
    rows, out = [], [f"UniCell on-board test run  {stamp}   serial port {port}   {len(tests)} bitstreams   ports at start: {serial_ports()}", "=" * 100]
    for fs in tests:
        name = os.path.splitext(os.path.basename(fs))[0]
        meta = json.load(open(fs[:-3] + ".json")) if os.path.exists(fs[:-3] + ".json") else {}
        print(f"[{name}] loading ...", flush=True)
        ok, msg = load(fs)
        status, line, answered, seen, note = "NOLOAD", "", "", [], ""
        if ok:
            lines, ser, answered, seen, note = listen(ser, port)
            line = lines[-1] if lines else ""
            if lines:
                port = answered
            m = re.search(r"res=([PF])", line)
            status = ("PASS" if m.group(1) == "P" else "FAIL") if m else "NOREPORT"
            if m and not line.startswith(f"UCT {name} "):
                status = "WRONGTEST(the line is from another bitstream: the board did not reload)"
            elif m and meta.get("sim_line"):
                same = re.sub(r"last=[0-9A-F]+", "", line) == re.sub(r"last=[0-9A-F]+", "", meta["sim_line"])
                if status == "PASS" and not same:
                    status = "PASS(line differs from simulation)"
        print(f"[{name}] {status}", flush=True)
        out += [f"{name:<22} {status}", f"   what     : {meta.get('what', '')}", f"   board    : {line or '(nothing received)'}", f"   simulated: {meta.get('sim_line', '')}"]
        out.append(f"   loader   : {'ok' if ok else 'FAILED'}; serial ports seen after loading: {seen}; {note}")
        if not ok or status == "NOREPORT":
            out.append("   loader output: " + msg.replace("\n", " | "))
        out.append(f"   built    : {meta.get('lut4', '?')} LUT4, {meta.get('dff', '?')} flip-flops, Fmax {meta.get('fmax_mhz', '?')} MHz (27 MHz needed)")
        out.append("")
        rows.append([name, status, line, meta.get("sim_line", ""), meta.get("lut4", ""), meta.get("dff", ""), meta.get("fmax_mhz", "")])
    npass = sum(1 for r in rows if r[1].startswith("PASS"))
    out += ["=" * 100, f"SUMMARY: {npass} of {len(rows)} passed"]
    open(os.path.join(HERE, "board_results.txt"), "w").write("\n".join(out) + "\n")
    with open(os.path.join(HERE, "board_results.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["test", "status", "board_line", "simulated_line", "lut4", "dff", "fmax_mhz"])
        w.writerows(rows)
    print("\n".join(out[-3:]))


if __name__ == "__main__":
    main()
'''


def readme(results):
    L = ["# Tang Nano 20K on-board tests (ledger #1023)\n",
         "Each `<name>.fs` is a complete, self-checking bitstream: a UniCell flex design, a fixed input stream, and the expected answers built in. When it has run it sends one line over the board's USB serial port "
         "(115200 baud, repeated about every 0.3 s) and lights the LEDs: **LED1 on = PASS, LED2 on = FAIL, LED3 on = finished, LED0 = heartbeat** (all active low, LED numbers as on the board silkscreen's `LED0..LED3` = pins 15-18).\n",
         "## To run them all\n", "1. Plug the board in by USB-C. 2. Install `openFPGALoader` and `pip install pyserial` (see `docs/shared/TOOLCHAIN_SETUP.md`). 3. **Linux:** `./run_all.sh` (or `./run_all.sh /dev/ttyUSB1`; you may need `sudo usermod -aG dialout $USER` once, then log out and in, or run it with sudo; `sudo apt install openfpgaloader python3-serial`). **Windows:** `run_all.bat` (or `run_all.bat COM7`). "
         "4. Read `board_results.txt` (and `board_results.csv`).\n",
         "The bitstreams are loaded to SRAM only (gone at power-off); the flash is not touched.\n",
         "## The line\n", "`UCT <name> res=P|F n=<words received> e=<words expected> bad=<wrong or extra words> to=<1 if it timed out> last=<cycle of the last word> sig=<checksum> w=<first 8 words>` (all hex). "
         "`board_results.txt` puts the line the **simulation** produced beside the one the **board** produced; for a pass they match except `last=` (cycle counts can differ by a few at the start-up).\n",
         "## The tests\n", "| test | what it proves | LUT4 | FF | Fmax (MHz, 27 needed) |", "|---|---|---|---|---|"]
    for r in results:
        L.append(f"| `{r['name']}` | {r['what']} | {r.get('lut4', '')} | {r.get('dff', '')} | {r.get('fmax_mhz', '')} |")
    L += ["\n## What a failure would mean\n", "- **NOLOAD**: the loader could not program the board (cable, driver, `openFPGALoader` not on the PATH).",
          "- **NOREPORT**: it loaded but nothing came back on the serial port: wrong serial port (the board shows two, e.g. /dev/ttyUSB0 and /dev/ttyUSB1 or COM7 and COM8; the FPGA UART is the second; on Linux also check the dialout group), or the UART pin (69) does not reach the PC the way the MAN file says (it has never been used by this project). The LEDs still show the verdict.",
          "- **FAIL** with a line: the design ran on silicon and gave a different answer from the simulation: compare `board` and `simulated` (`bad=` counts wrong words, `n=` the words that arrived).",
          "\n## Honest limits\n", "- Every bitstream passed in simulation (with the UART text decoded) and closed timing at 27 MHz in place-and-route, but nothing here has been on the board yet. The UART pin is unverified (the earlier smoke test used LEDs only).",
          "- 27 MHz only: there is no PLL, so this is not a speed test. The designs are small (a few cells), so they test the cell RTL and the handshake on real silicon, not capacity.",
          "- The expected words come from FlexGrid (the VM's flex mirror), which is proven equal to the generated RTL; the simulation then proves the wrapper's own checker agrees.\n"]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "fpga", "board_tests"))
    ap.add_argument("--only", default="")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-pnr", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    only = [x for x in a.only.split(",") if x]
    results = []
    for name, desc, mk, streams, gaps, stalls in TESTS:
        if only and name not in only:
            continue
        print(f"== {name}", flush=True)
        r = build_one(name, desc, mk, streams, gaps, stalls, a.out, pnr=not a.no_pnr, seed=a.seed)
        print(f"   ok: {r['sim_line']}   {r.get('lut4', '-')} LUT4  Fmax {r.get('fmax_mhz', '-')}", flush=True)
        results.append(r)
    open(os.path.join(a.out, "run_all.bat"), "w", newline="\r\n").write(BAT)
    open(os.path.join(a.out, "board_run.py"), "w").write(RUNPY)
    sh = os.path.join(a.out, "run_all.sh")
    open(sh, "w", newline="\n").write(SH)
    os.chmod(sh, 0o755)
    open(os.path.join(a.out, "README.md"), "w").write(readme(results))
    print(f"wrote {len(results)} tests to {a.out}")


if __name__ == "__main__":
    main()
