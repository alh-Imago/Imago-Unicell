#!/usr/bin/env python3
"""tools/kintex_tree4_pack_v1.py -- first Kintex-7 self-check kit (ledger #1234).

Takes the std_tree4 design that already ran on the Tang Nano 20K (ledger #1060: res=P, sig=7FEF5298,
last=0000061A, identical to simulation) and wraps it for the XC7K480T card, which has only three LEDs.

How: the Tang top (board_top_std_tree4, UNCHANGED) prints one 163-byte report line on its UART pin. Here that pin
is not wired out. A small receiver inside the FPGA reads it and compares EVERY byte with the line the Tang printed
(captured from simulation of the same RTL, equal to the card line). Every byte equal = PASS, including the
cycle count `last` and the checksum `sig`. So the test says: the same design gives the same answers, in the same
number of clocks, on a different chip family at a different clock (50 MHz here, 27 MHz on the Tang).

Writes fpga/kintex7_tests/k7_tree4/ : rtl/*.sv, k7_tree4_v1.v (top), tb_k7_tree4_v1.v, k7_tree4_v1.xdc, Makefile,
README.md. The Makefile follows openXC7.mk (TOP_VERILOG = <PROJECT>.v, ADDITIONAL_SOURCES, files given to yosys as plain
arguments, so .sv for SystemVerilog).   Needs iverilog (for the one capture run).
    python3 tools/kintex_tree4_pack_v1.py
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import board_loops_v1 as BL
import verilog_deps_v1 as vd

TREE = os.path.join(ROOT, "nano", "examples", "reduction_tree4_exit_v1.icm-hier.json")
OUT = os.path.join(ROOT, "fpga", "kintex7_tests", "k7_tree4")
BOARD_TOP = os.path.join(ROOT, "fpga", "board_tests_designs", "std_tree4.v")
UART_TX = os.path.join(ROOT, "fpga", "board_serial_probe", "board_uart_tx.v")


def main():
    work = tempfile.mkdtemp(prefix="k7tree4_")
    g = os.path.join(work, "gen")
    r = subprocess.run(BL.ASM + ["-s", "std", "--icm", TREE, "--tap-io", "output", "--top", "std_tree4", "--output", g],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("generator failed: " + r.stderr[-500:])
    meta = json.load(open(os.path.join(g, "GRID.json")))
    deps = set()
    for m in meta["shells"]:
        deps |= set(vd.deps(m, [g, os.path.join(ROOT, "fpga", "verilog")]))
    rtl = os.path.join(OUT, "rtl")
    if os.path.isdir(rtl):
        shutil.rmtree(rtl)
    os.makedirs(rtl)
    files = []
    for src in [os.path.join(g, "std_tree4.v"), BOARD_TOP, UART_TX] + sorted(deps):
        base = "board_top_std_tree4.v" if src == BOARD_TOP else os.path.basename(src)
        dst = os.path.join(rtl, base[:-2] + ".sv")      # openXC7.mk hands files to yosys as plain arguments: .sv = SystemVerilog
        shutil.copy(src, dst)
        files.append(os.path.basename(dst))
    # ---- capture the report line from simulation of the unchanged Tang top (CPB 8 = fast)
    tb = os.path.join(work, "tb_cap.v")
    open(tb, "w").write("""`timescale 1ns/1ps
module tb_cap;
 reg clk=0; always #10 clk=~clk;
 wire tx; wire l0,l1,l2,l3;
 board_top_std_tree4 #(.CPB(8)) d(.BOARD_CLK(clk),.UART_TX(tx),.LED0_N(l0),.LED1_N(l1),.LED2_N(l2),.LED3_N(l3));
 integer n=0; reg [7:0] b; integer i;
 initial begin
  forever begin
   @(negedge tx); #(8*20*1.5);
   for(i=0;i<8;i=i+1) begin b[i]=tx; #(8*20); end
   $write("%02x ",b); n=n+1;
   if(n==163) begin $write("\\n"); $finish; end
  end
 end
 initial begin #400000000; $display("TIMEOUT"); $finish; end
endmodule
""")
    exe = os.path.join(work, "cap")
    subprocess.run(["iverilog", "-g2012", "-o", exe, tb] + [os.path.join(rtl, f) for f in files], check=True)
    out = subprocess.run(["vvp", exe], capture_output=True, text=True).stdout.split("\n")[0].split()
    line = bytes(int(x, 16) for x in out)
    assert len(line) == 163 and line.endswith(b"\r\n"), len(line)
    txt = line.decode().strip()
    assert "res=P" in txt and "last=0000061A" in txt and "sig=7FEF5298" in txt, txt
    exp = json.load(open(os.path.join(ROOT, "fpga", "board_tests_designs", "std_tree4.json")))["sim_line"]
    assert txt == exp, (txt, exp)
    rom = "\n".join("            8'd%d: exp_byte = 8'h%02X;" % (i, b) for i, b in enumerate(line))
    open(os.path.join(OUT, "k7_tree4_v1.v"), "w").write(TOP.replace("@ROM@", rom).replace("@LINE@", txt))
    open(os.path.join(OUT, "tb_k7_tree4_v1.v"), "w").write(TB)
    open(os.path.join(OUT, "k7_tree4_v1.xdc"), "w").write(XDC)
    srcs = " ".join(["k7_tree4_v1.v"] + ["rtl/" + f for f in files])
    add = " ".join("rtl/" + f for f in files)
    open(os.path.join(OUT, "Makefile"), "w").write(MAKE.replace("@SRCS@", srcs).replace("@ADD@", add))
    old = os.path.join(OUT, "build_k7_tree4_v1.sh")
    if os.path.exists(old):
        os.remove(old)
    old = os.path.join(OUT, "top_k7_tree4_v1.v")
    if os.path.exists(old):
        os.remove(old)
    open(os.path.join(OUT, "README.md"), "w").write(README.replace("@LINE@", txt))
    shutil.rmtree(work)
    print("wrote", OUT, "(%d rtl files)" % len(files))
    print("expected line:", txt)


TOP = r"""// SPDX-License-Identifier: CERN-OHL-P-2.0
// k7_tree4_v1.v -- GENERATED by tools/kintex_tree4_pack_v1.py (ledger #1234); do not hand-edit.
// Kintex-7 (XC7K480T card) self-check wrapper around the UNCHANGED Tang Nano 20K design board_top_std_tree4.
// The Tang top prints one 163-byte report line on its UART pin. This wrapper reads that pin inside the chip and
// compares every byte with the line the Tang printed:
//   @LINE@
// All bytes equal (including last=0000061A, the clock count, and sig=7FEF5298, the checksum) = PASS.
//
// LEDs (pins from the card's board file, shown to work in ledger #1197; active-high assumed):
//   first ~1.3 s : "lamp test", all three LEDs driven ON (tells you which state is ON; see README)
//   then  yellow N30 : heartbeat (slow blink) = clock is running
//         green  M30 : fast blink (about 3 per second) = PASS
//         red    P30 : steady = FAIL (a byte differed, or no complete line within about 4 s)
//   (running or waiting: red and green not driven)
`default_nettype none

module top #(
    parameter integer CPB     = 434,      // 50 MHz / 115200 baud for the Tang top's UART (the line is not wired out)
    parameter integer LAMP_BIT = 26,      // lamp test lasts 2^LAMP_BIT clocks (1.34 s at 50 MHz); sim uses a small value
    parameter integer HB_BIT   = 24,      // heartbeat bit (0.34 s per toggle at 50 MHz)
    parameter integer FAST_BIT = 23,      // pass blink bit (0.17 s per toggle)
    parameter integer WATCHDOG = 200000000 // clocks without a complete line before FAIL (4 s at 50 MHz)
) (
    input  wire CLK,      // 50 MHz, AA28, LVCMOS18
    output wire LED0,     // red    P30
    output wire LED1,     // green  M30
    output wire LED2      // yellow N30
);
    wire utx;
    board_top_std_tree4 #(.CPB(CPB)) dut (
        .BOARD_CLK(CLK), .UART_TX(utx), .LED0_N(), .LED1_N(), .LED2_N(), .LED3_N());

    // ---- 8N1 receiver, CPB clocks per bit, sampled in the middle of each bit
    reg tx1 = 1'b1, tx2 = 1'b1;
    always @(posedge CLK) begin tx1 <= utx; tx2 <= tx1; end
    reg        busy = 1'b0;
    reg [15:0] cnt  = 16'd0;
    reg [3:0]  nb   = 4'd0;
    reg [7:0]  sh   = 8'd0;
    reg        got  = 1'b0;
    reg [7:0]  rxb  = 8'd0;
    always @(posedge CLK) begin
        got <= 1'b0;
        if (!busy) begin
            if (!tx2) begin busy <= 1'b1; cnt <= (CPB + CPB / 2) - 1; nb <= 4'd0; end   // start bit seen: first sample 1.5 bits on
        end else if (cnt != 16'd0) cnt <= cnt - 16'd1;
        else begin
            cnt <= CPB - 1;
            if (nb < 4'd8) begin sh <= {tx2, sh[7:1]}; nb <= nb + 4'd1; end
            else begin busy <= 1'b0; got <= 1'b1; rxb <= sh; end                          // stop-bit time: byte complete
        end
    end

    // ---- compare with the expected line, byte by byte, line after line
    reg [7:0] exp_b;
    reg [7:0] idx = 8'd0;
    function [7:0] exp_byte(input [7:0] i);
        case (i)
@ROM@
            default: exp_byte = 8'h00;
        endcase
    endfunction
    reg bad = 1'b0, seen = 1'b0;
    always @(posedge CLK) if (got) begin
        if (rxb != exp_byte(idx)) bad <= 1'b1;
        if (idx == 8'd162) begin idx <= 8'd0; seen <= 1'b1; end else idx <= idx + 8'd1;
    end

    // ---- watchdog and LEDs
    reg [27:0] wd = 28'd0;
    reg        timeout = 1'b0;
    always @(posedge CLK) begin
        if (seen) wd <= 28'd0;
        else if (wd >= WATCHDOG) timeout <= 1'b1;
        else wd <= wd + 28'd1;
    end
    reg [LAMP_BIT:0] lamp = 0;
    always @(posedge CLK) if (!lamp[LAMP_BIT]) lamp <= lamp + 1'b1;
    reg [27:0] free = 28'd0;
    always @(posedge CLK) free <= free + 28'd1;
    wire lamp_on = !lamp[LAMP_BIT];
    wire fail = bad || timeout;
    wire pass = seen && !fail;
    assign LED0 = lamp_on | fail;
    assign LED1 = lamp_on | (pass & free[FAST_BIT]);
    assign LED2 = lamp_on | free[HB_BIT];
endmodule
"""

TB = r"""// tb_k7_tree4_v1.v -- simulation of the Kintex wrapper (small CPB so it runs in seconds).
// Case 1: the unchanged design must give PASS (green blinks, red never on after the lamp test).
// Case 2: a corrupted expectation (parameter BREAK) must give FAIL. Run:  make sim   (see Makefile)
`timescale 1ns/1ps
module tb_k7_tree4_v1;
    reg clk = 0; always #10 clk = ~clk;
    wire l0, l1, l2;
    top #(.CPB(8), .LAMP_BIT(10), .HB_BIT(12), .FAST_BIT(11), .WATCHDOG(30000000)) t (.CLK(clk), .LED0(l0), .LED1(l1), .LED2(l2));
    integer green_toggles = 0, red_late = 0, ycount = 0; reg lg = 0, ly = 0;
    always @(posedge clk) if (!t.lamp_on) begin
        if (l1 !== lg) green_toggles = green_toggles + 1; lg <= l1;
        if (l0) red_late = red_late + 1;
        if (l2 !== ly) ycount = ycount + 1; ly <= l2;
    end
    initial begin
        #60000000;
        $display("seen=%b bad=%b timeout=%b idx=%0d green_toggles=%0d red_on_clocks=%0d yellow_toggles=%0d",
                 t.seen, t.bad, t.timeout, t.idx, green_toggles, red_late, ycount);
        if (t.seen && !t.bad && !t.timeout && green_toggles > 4 && red_late == 0 && ycount > 4) $display("PASS");
        else $display("FAIL");
        $finish;
    end
endmodule
"""

XDC = """## k7_tree4_v1.xdc -- pins as proven by the blink in ledger #1197 (card YPCB-00338-1P1, xc7k480tffg1156)
set_property PACKAGE_PIN AA28      [get_ports CLK]
set_property IOSTANDARD  LVCMOS18  [get_ports CLK]
create_clock -period 20.000 -name sys_clk [get_ports CLK]

set_property PACKAGE_PIN P30       [get_ports LED0]
set_property PACKAGE_PIN M30       [get_ports LED1]
set_property PACKAGE_PIN N30       [get_ports LED2]
set_property IOSTANDARD  LVCMOS18  [get_ports LED0]
set_property IOSTANDARD  LVCMOS18  [get_ports LED1]
set_property IOSTANDARD  LVCMOS18  [get_ports LED2]
"""

MAKE = """# k7_tree4_v1: self-check of the Tang std_tree4 design on the Kintex card, through the openXC7 flow.
# Copy this whole folder into demo-projects/ (next to blinky-ypcb003381p1) so ../openXC7.mk is found, then:
#   make            (build)      make program JTAG_LINK="-c ft232"   (load into SRAM only)
# Never write the card's flash. openXC7.mk gives yosys the files as plain arguments: a .v file is read as plain Verilog,
# a .sv file as SystemVerilog, so the design files under rtl/ are .sv (they use always_comb) and the small top is .v.
FAMILY  = kintex7
PART    = xc7k480tffg1156-1
BOARD   = ypcb003381p1
PROJECT = k7_tree4_v1
TOP_MODULE = top
XDC     = k7_tree4_v1.xdc
ADDITIONAL_SOURCES = @ADD@
CHIPDB  = ${KINTEX7_CHIPDB}
PYPY3  ?= python3

include ../openXC7.mk

sim:
\tiverilog -g2012 -o sim.vvp tb_k7_tree4_v1.v @SRCS@ && vvp sim.vvp
"""

README = """# k7_tree4_v1 -- first Kintex-7 self-check (ledger #1234)

The design is the Tang Nano 20K `std_tree4` (a 4-input sum tree built from the standard cell shells, 2,109 LUT4 on the Tang),
unchanged. On the Tang it printed, on the card (ledger #1060), res=P, sig=7FEF5298, last=0000061A, equal to simulation.
Here the Kintex card runs the same RTL at 50 MHz (the Tang ran at 27 MHz). The wrapper reads the report line the design
prints and compares all 163 bytes with the Tang's line:

    @LINE@

PASS means every byte is equal: the six sums (10, 57, -10, 10000, -530806 and the one that wraps 32 bits), the number of
clocks (`last=0000061A` = 1,562 clocks) and the checksum. The clock count is in clocks, so it should not change with the
clock speed; this is the check that it does not.

## LEDs (active-high assumed)
1. About 1.3 s after loading, all three LEDs are ON (lamp test). If instead they are OFF for that time and then come on,
   the LEDs are active-low: tell Alan/Claude, one parameter flips it.
2. Then: yellow (N30) blinks slowly = clock running. Green (M30) blinks fast = PASS. Red (P30) steady = FAIL.

A steady green on the card that is not driven by the design (seen in ledger #1195) may be a power LED: that is why PASS is a
blink, not a steady light.

## Simulation (done in the cloud workspace, see ledger #1234)
`make sim` (needs iverilog): expects `PASS`.  The same wrapper with one byte of the expected line changed gives FAIL.

## Build
Inside `nix develop github:openxc7/toolchain-nix`: copy this folder into demo-projects (next to `blinky-ypcb003381p1`),
`make`, then `make program JTAG_LINK="-c ft232"` (SRAM only). Never write the card's flash. Do not load a bitstream that failed timing.
"""

if __name__ == "__main__":
    main()
