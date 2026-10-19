#!/usr/bin/env python3
"""tools/kintex_tree4_pack_v2.py -- Kintex-7 kit with a JTAG user register (ledger #1239).

Clone of kintex_tree4_pack_v1.py's output (v1 is NOT edited): the same wrapper around the unchanged Tang std_tree4 design,
plus a BSCANE2 JTAG user register (USER1) that lets a host read the design's own state straight out of the chip:

    word 0 (bits  31..0 ) 0x554E4943  ("UNIC", a fixed pattern: proves the path)
    word 1 (bits  63..32) a free-running 32-bit counter of 50 MHz clocks, captured at the moment of the scan
    word 2 (bits  95..64) {16'h0, idx[7:0], 4'h0, lamp_on, timeout, bad, seen}  -- the wrapper's own registers

Whether the open-source flow (nextpnr-xilinx) can place a BSCANE2 is NOT known: the build itself is the first test.
Writes fpga/kintex7_tests/k7_tree4_jtag/ (rtl/, top, tb, xdc, Makefile, OpenOCD config and scripts, README).
    python3 tools/kintex_tree4_pack_v2.py
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kintex_tree4_pack_v1 as p1  # noqa: E402

OUT = os.path.join(ROOT, "fpga", "kintex7_tests", "k7_tree4_jtag")
NAME = "k7_tree4_jtag_v1"

JTAG_BLOCK = r"""
    // ---- JTAG user register (USER1), ledger #1239. CAPTURE loads a snapshot, SHIFT moves it out through TDO, LSB first.
    //  bits 31..0  0x554E4943 ("UNIC")   bits 63..32  free-running clock counter   bits 95..64  {16'h0, idx, 4'h0, lamp_on, timeout, bad, seen}
    //  The snapshot is taken in the JTAG clock domain without synchronisers: fine for a bring-up read (the counter is only a liveness
    //  check; seen/bad/timeout are steady after the compare finishes; idx moves only while a line is arriving).
    reg [31:0] jcnt = 32'd0;
    always @(posedge CLK) jcnt <= jcnt + 32'd1;
    wire j_capture, j_shift, j_sel, j_tck, j_tdi, j_update, j_reset, j_runtest, j_drck, j_tms, j_tdo;
    BSCANE2 #(.JTAG_CHAIN(1)) bscan (
        .CAPTURE(j_capture), .DRCK(j_drck), .RESET(j_reset), .RUNTEST(j_runtest), .SEL(j_sel), .SHIFT(j_shift),
        .TCK(j_tck), .TDI(j_tdi), .TMS(j_tms), .UPDATE(j_update), .TDO(j_tdo));
    reg [95:0] jsr = 96'd0;
    wire [95:0] jsnap = {16'h0000, idx, 4'h0, lamp_on, timeout, bad, seen, jcnt, 32'h554E4943};
    always @(posedge j_tck) if (j_sel) begin
        if (j_capture) jsr <= jsnap;
        else if (j_shift) jsr <= {j_tdi, jsr[95:1]};
    end
    assign j_tdo = jsr[0];
"""

BSCAN_MODEL_TB = r"""// tb_k7_tree4_jtag_v1.v -- simulation: let the wrapper finish its compare, then do a USER1-style scan through a
// behavioural BSCANE2 (defined HERE, for simulation only; the real primitive is a blackbox for the synthesiser).
`timescale 1ns/1ps
module BSCANE2 #(parameter JTAG_CHAIN = 1) (
    output reg CAPTURE = 0, output reg DRCK = 0, output reg RESET = 0, output reg RUNTEST = 0, output reg SEL = 0,
    output reg SHIFT = 0, output reg TCK = 0, output reg TDI = 0, output reg TMS = 0, output reg UPDATE = 0, input TDO);
endmodule

module tb_k7_tree4_jtag_v1;
    reg clk = 0; always #10 clk = ~clk;
    wire l0, l1, l2;
    top #(.CPB(8), .LAMP_BIT(10), .HB_BIT(12), .FAST_BIT(11), .WATCHDOG(30000000)) t (.CLK(clk), .LED0(l0), .LED1(l1), .LED2(l2));
    reg [95:0] got; integer i;
    task tck_pulse; begin #50 t.bscan.TCK = 1; #50 t.bscan.TCK = 0; end endtask
    initial begin
        #6000000;                                   // 6 ms: the compare has finished
        t.bscan.SEL = 1;
        t.bscan.CAPTURE = 1; tck_pulse; t.bscan.CAPTURE = 0;
        t.bscan.SHIFT = 1;
        for (i = 0; i < 96; i = i + 1) begin
            #10 got[i] = t.bscan.TDO;               // bit i leaves before the clock that shifts it
            tck_pulse;
        end
        t.bscan.SHIFT = 0; t.bscan.SEL = 0;
        $display("scan word0=%08X word1=%08X word2=%08X", got[31:0], got[63:32], got[95:64]);
        if (got[31:0] === 32'h554E4943 && got[63:32] !== 32'd0 && got[64] === 1'b1 && got[65] === 1'b0 && got[66] === 1'b0 && got[95:80] === 16'h0)
            $display("PASS");
        else $display("FAIL");
        $finish;
    end
endmodule
"""

OPENOCD_CFG = """# k7_ft232h.cfg -- OpenOCD config for the Kintex-7 card through the FT232H-type cable ("-c ft232" in openFPGALoader).
# Pins as openFPGALoader's own table for that cable: VID:PID 0403:6014, interface A, initial output value 0x08, direction 0x0B
# (the usual MPSSE layout: TCK = ADBUS0, TDI = ADBUS1, TDO = ADBUS2, TMS = ADBUS3, no reset line).
# Reads and shifts only; this project's scripts never send JPROGRAM or any configuration instruction.
adapter driver ftdi
ftdi vid_pid 0x0403 0x6014
ftdi channel 0
ftdi layout_init 0x0008 0x000b
transport select jtag
adapter speed 6000
jtag newtap xc7 tap -irlen 6 -expected-id 0x23751093
"""

SCAN_SH = """#!/bin/sh
# scan_chain.sh -- step A: does OpenOCD see the chip through this cable? Prints the JTAG chain; changes nothing.
# Run inside the openXC7 Nix shell, with OpenOCD added:   nix shell nixpkgs#openocd   (then run this).  Use sudo env "PATH=$PATH" if it says permission denied.
cd "$(dirname "$0")" || exit 1
openocd -f k7_ft232h.cfg -c "init; scan_chain; shutdown"
"""

READ_SH = """#!/bin/sh
# read_user1.sh -- step C: read the design's JTAG user register (needs the k7_tree4_jtag bitstream loaded). Selects USER1 (IR 0x02)
# and shifts 96 bits out as three 32-bit words. Reads only: no configuration instruction is sent.
cd "$(dirname "$0")" || exit 1
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; set w [drscan xc7.tap 32 0 32 0 32 0]; puts \\"USER1 \\$w\\"; shutdown" 2>&1 | tee read_user1.log
python3 decode_user1.py read_user1.log
"""

DECODE_PY = '''#!/usr/bin/env python3
"""decode_user1.py -- turn the three words printed by read_user1.sh into plain statements."""
import re
import sys

text = open(sys.argv[1]).read()
m = re.search(r"USER1\\s+([0-9a-fA-F]+)\\s+([0-9a-fA-F]+)\\s+([0-9a-fA-F]+)", text)
if not m:
    sys.exit("no USER1 line found: step B (load the bitstream) or the OpenOCD run failed; see the log")
w0, w1, w2 = (int(x, 16) for x in m.groups())
print("word0 = 0x%08X   %s" % (w0, "OK, the fixed pattern 'UNIC' came back" if w0 == 0x554E4943 else "NOT the expected 0x554E4943"))
print("word1 = %d clocks of 50 MHz since power-up (a snapshot; changes on every read) -> %.3f s" % (w1, w1 / 50e6))
seen, bad, tmo, lamp = w2 & 1, (w2 >> 1) & 1, (w2 >> 2) & 1, (w2 >> 3) & 1
print("word2 = 0x%08X   seen=%d bad=%d timeout=%d lamp_on=%d idx=%d" % (w2, seen, bad, tmo, lamp, (w2 >> 8) & 0xFF))
print("compare: %s" % ("PASS (a complete line was received and every byte matched)" if seen and not bad and not tmo else "NOT a pass"))
'''

README = """# k7_tree4_jtag_v1 -- read the design's own state out of the Kintex chip over JTAG (ledger #1239)

Same as k7_tree4_v1 (Tang std_tree4 design, unchanged, compared byte for byte, LEDs show PASS) plus a JTAG user register that a host can read:
96 bits: 0x554E4943 ("UNIC"), a clock counter, and the wrapper's own registers (seen / bad / timeout / idx). It is the first step towards
Alan's idea of freezing the design and reading the latch states.

Three steps, each only after the one before worked. Nothing here writes the card's flash or sends a configuration instruction.

**A. Can OpenOCD see the chip through this cable? (no bitstream needed)**
    nix shell nixpkgs#openocd          # adds OpenOCD to the openXC7 shell; a download the first time
    sh scan_chain.sh                   # expect: one TAP, xc7.tap, IDCODE 0x23751093.  (if permission denied: sudo env "PATH=$PATH" sh scan_chain.sh)

**B. Build and load (the open question: can nextpnr-xilinx place a BSCANE2? the build is the test)**
    copy this folder into demo-projects (next to blinky-ypcb003381p1), then:  make   and   make program JTAG_LINK="-c ft232"
    The LEDs must show the same PASS pattern as k7_tree4_v1 (green, yellow, green + yellow, off; red off).
    If `make` stops with an error mentioning BSCANE2 or an unknown cell, paste it: that is the answer to the question.

**C. Read the register**
    sh read_user1.sh                   # prints the three words and what they mean
    Expect word0 = 0x554E4943, a counter that differs on every read, and seen=1 bad=0 timeout=0.

The OpenOCD config uses the pin table openFPGALoader uses for its "ft232" cable (FT232H, 0403:6014, TCK/TDI/TDO/TMS on the low four pins). I read that
table in openFPGALoader v1.1.1 (the version you have); I have not run OpenOCD against your cable.
"""


def main():
    p1.OUT = OUT
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    p1.main()
    old = lambda n: os.path.join(OUT, n)       # noqa: E731
    # rename the project files
    for a, b in (("k7_tree4_v1.v", NAME + ".v"), ("k7_tree4_v1.xdc", NAME + ".xdc")):
        os.rename(old(a), old(b))
    top = open(old(NAME + ".v")).read()
    top = top.replace("k7_tree4_v1.v -- GENERATED by tools/kintex_tree4_pack_v1.py (ledger #1234)",
                      NAME + ".v -- GENERATED by tools/kintex_tree4_pack_v2.py (ledger #1239) from the v1 wrapper + a JTAG user register")
    assert top.rstrip().endswith("endmodule")
    top = top.rstrip()[: -len("endmodule")] + JTAG_BLOCK + "endmodule\n"
    open(old(NAME + ".v"), "w").write(top)
    mk = open(old("Makefile")).read()
    mk = mk.replace("k7_tree4_v1", NAME)
    open(old("Makefile"), "w").write(mk)
    xdc = open(old(NAME + ".xdc")).read().replace("k7_tree4_v1.xdc", NAME + ".xdc")
    open(old(NAME + ".xdc"), "w").write(xdc)
    os.remove(old("tb_k7_tree4_v1.v"))
    open(old("tb_k7_tree4_jtag_v1.v"), "w").write(BSCAN_MODEL_TB)
    mk = open(old("Makefile")).read()
    mk = mk.replace("tb_" + NAME + ".v", "tb_k7_tree4_jtag_v1.v")
    open(old("Makefile"), "w").write(mk)
    for fn, txt in (("k7_ft232h.cfg", OPENOCD_CFG), ("scan_chain.sh", SCAN_SH), ("read_user1.sh", READ_SH),
                    ("decode_user1.py", DECODE_PY), ("README.md", README)):
        open(old(fn), "w").write(txt)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
