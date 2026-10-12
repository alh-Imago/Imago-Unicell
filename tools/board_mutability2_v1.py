#!/usr/bin/env python3
"""tools/board_mutability2_v1.py -- ledger #1088: TEST 2 of the mutability proof for the Tang Nano 20K (Alan, 12 Oct 2026): a MIXED-FAMILY card with timing.

On one card (this is a deliberate test mix, not something a normal build would do):
  * the VIX carrier v1d (the v4c-family carrier, only the cores named by --keep) -- the thing being reconfigured;
  * a STANDALONE command_cell_v4 in programmer mode, wired to the carrier's live programming channel (the same wiring as tb_vix_carrier_select_redirect_v1.v, but with the full v4
    command cell instead of the carrier's built-in command core). It is the ONLY way the carrier is configured: cfg_valid on the carrier is tied to 0 for the whole run;
  * a STANDALONE sequencer_cell_v4 feeding operands into the carrier's north face on its own (streaming);
  * a wrapper that plays the part of the outside world (serial link, operand source for single shots, result consumer) and COUNTS CLOCKS.

Serial protocol, 115200 8N1 (the PC is the host; the bitstream never changes):
  'W' n w1..wn   (n <= 12 words, 4 bytes each, big-endian) -> the words are handed to the command cell one by one; it relays them into the carrier.
                  reply 'K' + 4 bytes = clocks from the first word offered to the command cell going quiet again (carrier released), or 'T'.
  'D' A(4) B(4)  -> A then B go in on the north face, the board answers 'R' + result(4) + latency(4) (clocks from B going in to the result appearing on the east face), or 'T'.
  'S' cfg(8) n(2)-> the sequencer is configured with cfg64 (see sequencer_cell_v4) and streams its values into the carrier; the wrapper takes n results.
                  reply 'U' + first_result_clock(4) + clock_of_nth_result(4) + first_value(4) + last_value(4), or 'T'.
Clock counts are exact (counted on the card). Time in ns = clocks x clock period; Fmax claims come only from nextpnr (static) and are labelled so.

  python3 tools/board_mutability2_v1.py [--out DIR] [--keep adder,accum,mul] [--seed N] [--no-pnr] [--mutant none|nocfg|wrongexp|nocmd|noseq]
  python3 tools/board_mutability2_v1.py --fit "adder,mul;adder,accum,mul,compare,branch,latch,ram;all"    (place-and-route only: what fits and how fast, per keep set)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import make_carrier_subset_v2 as sub  # noqa: E402
import verilog_deps_v1 as vd  # noqa: E402
import board_tests_v1 as bt  # noqa: E402
import board_mutability_v1 as bm  # noqa: E402  (test 1: operands, add-on helper, UART receiver; not modified)

NAME = "mutability2"
M32 = 0xFFFFFFFF
A_WORD, B_WORD = bm.A_WORD, bm.B_WORD
SEL_ADDER, SEL_MUL, SEL_ADDON = 1, 9, 11
DOWN_E, UP_N = 0b000100, 0b000001
SEQ_VALUES = (0x12, 0x34, 0x56, 0x78)
SEQ_CFG = SEQ_VALUES[0] | SEQ_VALUES[1] << 8 | SEQ_VALUES[2] << 16 | SEQ_VALUES[3] << 24 | 3 << 32 | 0b000010 << 34   # 4 values, offered south (into the carrier's north face)
STREAM_N = 64
CMD_CFG = 0xE9                                   # command cell: mode=1 programmer, drive_dir=E(2), toggle_pattern=7 (3-bit COMPLETE)


def wd(pid, w=0):
    return (pid << 20) | w


SACRIFICE = wd(6, 0)    # PROG_ID 6 is unused by adder, mul and the add-on block: a harmless no-op word (see the finding in README: the carrier's first word of a SECOND session is read with the old state)


def core_words(sel, sub_mode=0):
    """first word = core select (the carrier resets the new core to blank), then downstream east, upstream north, subtract/wide mode, COMPLETE+arm."""
    return [SACRIFICE, sel, wd(0, DOWN_E), wd(1, UP_N), wd(2, sub_mode), wd(7, 1)]


def addon_words(cfg20):
    """first word 11 = address the carrier's shared add-on block (does not touch the running core), then the add-on word, then COMPLETE."""
    return [SACRIFICE, SEL_ADDON, wd(0, cfg20), wd(7, 1)]


def phases():
    s = (A_WORD + B_WORD) & M32
    keep = ~0xFF & M32
    addon = bm.addon
    def ph(label, sel, sm, ad, exp):
        return dict(kind="d", label=label, words=core_words(sel, sm) + addon_words(ad), expected=exp)
    out = [
        ph("adder add", SEL_ADDER, 0, 0, s),
        ph("adder subtract", SEL_ADDER, 1, 0, (A_WORD - B_WORD) & M32),
        ph("add + invert", SEL_ADDER, 0, addon(inv=1), (~s) & M32),
        ph("add + shift right 8", SEL_ADDER, 0, addon(en_shift=1, right=1, amt=8), s >> 8),
        ph("add + nibble mask 03", SEL_ADDER, 0, addon(mask_en=1, nib=0x03), s & keep),
        ph("core changed to mul", SEL_MUL, 0, 0, (A_WORD * B_WORD) & M32),
        ph("back to adder add", SEL_ADDER, 0, 0, s),
    ]
    for label, sel, f in (("stream adder", SEL_ADDER, lambda a, b: a + b), ("stream mul", SEL_MUL, lambda a, b: a * b)):
        n = STREAM_N
        pr = [f(SEQ_VALUES[0], SEQ_VALUES[1]) & M32, f(SEQ_VALUES[2], SEQ_VALUES[3]) & M32]
        out.append(dict(kind="s", label=label, words=core_words(sel, 0) + addon_words(0), n=n, first=pr[0], last=pr[(n - 1) % 2]))
    return out


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------
def wrapper(cpb, mutant="none", timeout_clk=2000000):
    cmd_init = "1'b0" if mutant == "nocmd" else "1'b1"
    seq_act = "1'b0" if mutant == "noseq" else "1'b1"
    T = r"""// board_top_mutability2.v -- GENERATED by tools/board_mutability2_v1.py (ledger #1088); do not hand-edit.
`default_nettype none
`timescale 1ns / 1ps
module board_top_mutability2 #(parameter integer CPB = @CPB@) (
    input wire BOARD_CLK, input wire UART_RX, output wire UART_TX, output wire LED0_N, output wire LED1_N, output wire LED2_N, output wire LED3_N);
wire clk = BOARD_CLK;
reg [7:0] por_cnt = 8'h00; wire rst = (por_cnt != 8'hFF); always @(posedge clk) if (rst) por_cnt <= por_cnt + 8'd1;

// ---------------- the command cell (standalone command_cell_v4, programmer mode, drives EAST into the carrier's west face)
reg cmd_cfgv = 1'b0, cmd_init_done = 1'b0;
always @(posedge clk) begin cmd_cfgv <= 1'b0; if (!rst && !cmd_init_done) begin cmd_cfgv <= @CMDINIT@; cmd_init_done <= 1'b1; end end
reg [31:0] w_val = 32'h0; reg w_arr = 1'b0;
wire cmd_ready, cmd_active, cmd_fz_e, cmd_po_e, cmd_pa_e; wire [31:0] cmd_pd_e; wire car_pack_w, car_ack_n;
command_cell_v4 #(.CELL_ID(16'hA000)) CMD (
    .clk(clk), .rst(rst), .active(1'b1), .cfg_valid(cmd_cfgv), .cfg_data(64'h@CMDCFG@),
    .data_in_n(w_val), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(w_arr), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(), .ready_out(cmd_ready),
    .freeze_out_n(), .freeze_out_s(), .freeze_out_e(cmd_fz_e), .freeze_out_w(),
    .program_out_n(), .program_out_s(), .program_out_e(cmd_po_e), .program_out_w(),
    .prog_data_out_n(), .prog_data_out_s(), .prog_data_out_e(cmd_pd_e), .prog_data_out_w(),
    .prog_arrived_out_n(), .prog_arrived_out_s(), .prog_arrived_out_e(cmd_pa_e), .prog_arrived_out_w(),
    .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(car_pack_w), .prog_ack_in_w(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
    .freeze_in(1'b0), .status_active(cmd_active), .status_freeze_state());

// ---------------- the sequencer (standalone sequencer_cell_v4), offers SOUTH into the carrier's north face
reg seq_cfgv = 1'b0; reg [63:0] seq_cfg = 64'h0; reg seq_active = 1'b0; reg use_seq = 1'b0;
wire [31:0] seq_dout; wire seq_fire;
sequencer_cell_v4 #(.CELL_ID(16'hA001)) SEQ (
    .clk(clk), .rst(rst), .active(seq_active), .cfg_valid(seq_cfgv), .cfg_data(seq_cfg),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(seq_dout), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(seq_fire), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(car_ack_n), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
    .freeze_in(1'b0), .ready_out(), .status_seq_index());

// ---------------- the carrier: cfg_valid is tied to 0 -- the command cell is the only thing that ever configures it
reg [31:0] val_n = 32'h0; reg arr_n = 1'b0; reg ack_e = 1'b0;
wire [31:0] dn = use_seq ? seq_dout : val_n; wire an = use_seq ? seq_fire : arr_n;
wire [31:0] dout_e; wire fire_e;
unicell_vix_carrier_v1dm #(.CELL_ID(16'hC200)) VIX (
    .clk(clk), .rst(rst),
    .active_in_n(1'b1), .active_in_s(1'b0), .active_in_e(1'b0), .active_in_w(1'b0),
    .freeze_in_n(1'b0), .freeze_in_s(1'b0), .freeze_in_e(1'b0), .freeze_in_w(cmd_fz_e),
    .cfg_valid(1'b0), .cfg_data(160'h0),
    .data_in_n(dn), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(an), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(car_ack_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_e), .ack_in_w(1'b0),
    .program_in(cmd_po_e), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(cmd_pd_e),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(cmd_pa_e),
    .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(car_pack_w),
    .freeze_out_n(), .freeze_out_s(), .freeze_out_e(), .freeze_out_w(),
    .program_out_n(), .program_out_s(), .program_out_e(), .program_out_w(),
    .prog_data_out_n(), .prog_data_out_s(), .prog_data_out_e(), .prog_data_out_w(),
    .prog_arrived_out_n(), .prog_arrived_out_s(), .prog_arrived_out_e(), .prog_arrived_out_w(),
    .prog_ack_in_n(1'b0), .prog_ack_in_s(1'b0), .prog_ack_in_e(1'b0), .prog_ack_in_w(1'b0),
    .status_core_select());

// ---------------- serial link
wire rx_v; wire [7:0] rx_d; board_uart_rx #(.CPB(CPB)) urx (.clk(clk), .rx(UART_RX), .valid(rx_v), .data(rx_d));
wire tx_busy; reg tx_start = 1'b0; reg [7:0] tx_data = 8'h00;
board_uart_tx #(.CPB(CPB)) utx (.clk(clk), .start(tx_start), .data(tx_data), .tx(UART_TX), .busy(tx_busy));

// ---------------- the frame engine
localparam [4:0] H_IDLE = 5'd0, H_WN = 5'd1, H_WB = 5'd2, H_WPRES = 5'd3, H_WSET = 5'd4, H_WEND = 5'd5,
                 H_DAT = 5'd6, H_A = 5'd7, H_AW = 5'd8, H_B = 5'd9, H_WAIT = 5'd10, H_SETTLE = 5'd11,
                 H_SQ = 5'd12, H_SRUN = 5'd13, H_SDRAIN = 5'd14, H_REPLY = 5'd15;
reg [4:0] st = H_IDLE; reg [4:0] nrx = 5'd0; reg [3:0] wcnt = 4'd0, widx = 4'd0; reg [1:0] bcnt = 2'd0; reg [23:0] wsh = 24'h0;
reg [31:0] wbuf [0:15]; reg prime = 1'b1, primed_run = 1'b0; reg [63:0] ops = 64'h0; reg [15:0] w = 16'd0; reg [23:0] tmo = 24'd0;
reg [31:0] tcnt = 32'd0; reg cnt_en = 1'b0; reg [31:0] result = 32'h0, lat = 32'h0;
reg [15:0] ncount = 16'd0, scount = 16'd0; reg [31:0] first_clk = 32'h0, total_clk = 32'h0, first_val = 32'h0, last_val = 32'h0;
reg [143:0] txq = 144'h0; reg [4:0] txn = 5'd0; reg [15:0] frames = 16'd0;
always @(posedge clk) begin
    cfg_pulse_clear;
end
endmodule
"""
    # the always block is written out below rather than in the template so the template stays readable
    body = r"""always @(posedge clk) begin
    seq_cfgv <= 1'b0; w_arr <= 1'b0; arr_n <= 1'b0; ack_e <= 1'b0; tx_start <= 1'b0;
    if (cnt_en) tcnt <= tcnt + 32'd1;
    if (rst) begin st <= H_IDLE; nrx <= 5'd0; txn <= 5'd0; cnt_en <= 1'b0; use_seq <= 1'b0; seq_active <= 1'b0; end
    else case (st)
        H_IDLE: if (prime && cmd_init_done && !cmd_cfgv && cmd_ready) begin
                    // power-up priming session: select the adder so the carrier's select state is known before the first host frame (see README)
                    wbuf[0] <= 32'h00000001; wbuf[1] <= 32'h00700001; wcnt <= 4'd2; widx <= 4'd0; tcnt <= 32'd0; cnt_en <= 1'b1; tmo <= 24'd0; prime <= 1'b0; primed_run <= 1'b1; st <= H_WPRES;
                end else if (rx_v) begin
                    nrx <= 5'd0;
                    if (rx_d == 8'h57) st <= H_WN;
                    else if (rx_d == 8'h44) st <= H_DAT;
                    else if (rx_d == 8'h53) st <= H_SQ;
                end
        // ---- W: words for the command cell
        H_WN:   if (rx_v) begin
                    if (rx_d == 8'd0 || rx_d > 8'd12) begin txq <= {8'h54, 136'h0}; txn <= 5'd1; st <= H_REPLY; end
                    else begin wcnt <= rx_d[3:0]; widx <= 4'd0; bcnt <= 2'd0; st <= H_WB; end
                end
        H_WB:   if (rx_v) begin
                    if (bcnt == 2'd3) begin wbuf[widx] <= {wsh, rx_d}; bcnt <= 2'd0;
                        if (widx + 4'd1 == wcnt) begin widx <= 4'd0; tcnt <= 32'd0; cnt_en <= 1'b1; tmo <= 24'd0; st <= H_WPRES; end else widx <= widx + 4'd1; end
                    else begin wsh <= {wsh[15:0], rx_d}; bcnt <= bcnt + 2'd1; end
                end
        H_WPRES: begin tmo <= tmo + 24'd1;
                    if (cmd_ready) begin w_val <= wbuf[widx]; w_arr <= 1'b1; widx <= widx + 4'd1; w <= 16'd0; st <= H_WSET; end
                    else if (tmo >= 24'd@TMO@) begin cnt_en <= 1'b0; txq <= {8'h54, 136'h0}; txn <= 5'd1; st <= H_REPLY; end
                end
        H_WSET: begin tmo <= tmo + 24'd1; w <= w + 16'd1; if (w == 16'd2) st <= (widx == wcnt) ? H_WEND : H_WPRES; end
        H_WEND: begin tmo <= tmo + 24'd1;
                    if (cmd_ready && !cmd_active) begin cnt_en <= 1'b0; if (primed_run) begin primed_run <= 1'b0; st <= H_IDLE; end else begin txq <= {8'h4B, tcnt, 104'h0}; txn <= 5'd5; st <= H_REPLY; end end
                    else if (tmo >= 24'd@TMO@) begin cnt_en <= 1'b0; txq <= {8'h54, 136'h0}; txn <= 5'd1; st <= H_REPLY; end
                end
        // ---- D: one operand pair from the wrapper
        H_DAT:  if (rx_v) begin ops <= {ops[55:0], rx_d}; nrx <= nrx + 5'd1; if (nrx == 5'd7) st <= H_A; end
        H_A:    begin val_n <= ops[63:32]; arr_n <= 1'b1; w <= 16'd0; st <= H_AW; end
        H_AW:   begin w <= w + 16'd1; if (w == 16'd16) begin w <= 16'd0; st <= H_B; end end
        H_B:    begin val_n <= ops[31:0]; arr_n <= 1'b1; tmo <= 24'd0; tcnt <= 32'd1; cnt_en <= 1'b1; st <= H_WAIT; end
        H_WAIT: begin tmo <= tmo + 24'd1;
                    if (fire_e) begin cnt_en <= 1'b0; result <= dout_e; lat <= tcnt; ack_e <= 1'b1; w <= 16'd0; st <= H_SETTLE; end
                    else if (tmo >= 24'd@TMO@) begin cnt_en <= 1'b0; txq <= {8'h54, 136'h0}; txn <= 5'd1; st <= H_REPLY; end
                end
        H_SETTLE: begin w <= w + 16'd1; if (w == 16'd64) begin txq <= {8'h52, result, lat, 72'h0}; txn <= 5'd9; st <= H_REPLY; end end
        // ---- S: the sequencer streams into the carrier, the wrapper takes ncount results
        H_SQ:   if (rx_v) begin
                    if (nrx < 5'd8) seq_cfg <= {seq_cfg[55:0], rx_d};
                    else if (nrx == 5'd8) ncount[15:8] <= rx_d;
                    nrx <= nrx + 5'd1;
                    if (nrx == 5'd9) begin ncount[7:0] <= rx_d; st <= H_SRUN; scount <= 16'd0; tcnt <= 32'd0; cnt_en <= 1'b1; tmo <= 24'd0; seq_cfgv <= 1'b1; use_seq <= 1'b1; seq_active <= @SEQACT@; end
                end
        H_SRUN: begin tmo <= tmo + 24'd1;
                    if (fire_e) begin
                        if (scount == 16'd0) begin first_clk <= tcnt; first_val <= dout_e; end
                        last_val <= dout_e; total_clk <= tcnt; scount <= scount + 16'd1; ack_e <= 1'b1; tmo <= 24'd0; st <= H_SDRAIN;
                    end else if (tmo >= 24'd@TMO@) begin cnt_en <= 1'b0; use_seq <= 1'b0; seq_active <= 1'b0; txq <= {8'h54, 136'h0}; txn <= 5'd1; st <= H_REPLY; end
                end
        H_SDRAIN: begin
                    if (!fire_e && !ack_e) begin
                        if (scount == ncount) begin cnt_en <= 1'b0; use_seq <= 1'b0; seq_active <= 1'b0; txq <= {8'h55, first_clk, total_clk, first_val, last_val, 8'h00}; txn <= 5'd17; st <= H_REPLY; end
                        else st <= H_SRUN;
                    end
                end
        H_REPLY: begin
                    if (txn == 5'd0) st <= H_IDLE;
                    else if (!tx_busy && !tx_start) begin tx_data <= txq[143:136]; tx_start <= 1'b1; txq <= {txq[135:0], 8'h00}; txn <= txn - 5'd1; end
                end
        default: st <= H_IDLE;
    endcase
    if (rx_v) frames <= frames + 16'd1;
end
reg [23:0] hb = 24'd0; always @(posedge clk) hb <= hb + 24'd1;
reg [23:0] blink = 24'd0; always @(posedge clk) begin if (cmd_active) blink <= 24'hFFFFFF; else if (blink != 24'd0) blink <= blink - 24'd1; end
assign LED0_N = ~hb[23]; assign LED1_N = ~(blink != 24'd0); assign LED2_N = ~(st != H_IDLE); assign LED3_N = ~(frames != 16'd0);
endmodule
"""
    T = T.replace("always @(posedge clk) begin\n    cfg_pulse_clear;\nend\nendmodule\n", body)
    for k, v in (("@CPB@", str(cpb)), ("@CMDINIT@", cmd_init), ("@CMDCFG@", "%016X" % CMD_CFG), ("@SEQACT@", seq_act), ("@TMO@", str(timeout_clk))):
        T = T.replace(k, v)
    return T


def sim_host(work, files, ph, cpb=8, nocfg=False):
    """A testbench that plays the PC. For every phase: a W frame, then a D (or S) frame; each reply is checked against the Python-computed word."""
    tasks = []
    for i, p in enumerate(ph):
        wb = " ".join(f"sendb(8'h{(w >> (8 * (3 - j))) & 0xFF:02X});" for w in p["words"] for j in range(4))
        wf = "" if (nocfg and i > 0) else (
            f"sendb(8'h57); sendb(8'd{len(p['words'])}); {wb} getb(rb);\n"
            f"    if (rb !== 8'h4B) begin bad = bad + 1; $display(\"phase {i}: no K (got %02X)\", rb); end else begin getn(4, v); $display(\"phase {i} {p['label']}: reprogram took %0d clocks\", v[31:0]); end")
        if p["kind"] == "d":
            db = " ".join(f"sendb(8'h{(w >> (8 * (3 - j))) & 0xFF:02X});" for w in (A_WORD, B_WORD) for j in range(4))
            tasks.append(f"    {wf}\n    sendb(8'h44); {db} getb(rb);\n"
                         f"    if (rb !== 8'h52) begin bad = bad + 1; $display(\"phase {i}: no R (got %02X)\", rb); end else begin getn(8, v);\n"
                         f"      $display(\"phase {i} {p['label']}: got %08X want {p['expected']:08X} %s  latency %0d clocks\", v[63:32], (v[63:32] == 32'h{p['expected']:08X}) ? \"ok\" : \"WRONG\", v[31:0]); if (v[63:32] != 32'h{p['expected']:08X}) bad = bad + 1; end")
        else:
            sb = " ".join(f"sendb(8'h{(SEQ_CFG >> (8 * (7 - j))) & 0xFF:02X});" for j in range(8))
            tasks.append(f"    {wf}\n    sendb(8'h53); {sb} sendb(8'h{p['n'] >> 8:02X}); sendb(8'h{p['n'] & 0xFF:02X}); getb(rb);\n"
                         f"    if (rb !== 8'h55) begin bad = bad + 1; $display(\"phase {i}: no U (got %02X)\", rb); end else begin getn(16, v);\n"
                         f"      $display(\"stream {i} {p['label']}: n={p['n']} first_clk %0d total_clk %0d first %08X want {p['first']:08X} last %08X want {p['last']:08X} %s\", v[127:96], v[95:64], v[63:32], v[31:0],\n"
                         f"               (v[63:32] == 32'h{p['first']:08X} && v[31:0] == 32'h{p['last']:08X}) ? \"ok\" : \"WRONG\"); if (v[63:32] != 32'h{p['first']:08X} || v[31:0] != 32'h{p['last']:08X}) bad = bad + 1; end")
    tb = f"""`timescale 1ns/1ps
module tbh;
  reg clk = 0; reg rx = 1; wire tx, l0, l1, l2, l3;
  board_top_{NAME} #(.CPB({cpb})) dut (.BOARD_CLK(clk), .UART_RX(rx), .UART_TX(tx), .LED0_N(l0), .LED1_N(l1), .LED2_N(l2), .LED3_N(l3));
  always #5 clk = ~clk;
  integer bad = 0; reg [7:0] rb; reg [143:0] v;
  task sendb(input [7:0] b); integer i; begin
    rx = 0; repeat ({cpb}) @(posedge clk);
    for (i = 0; i < 8; i = i + 1) begin rx = b[i]; repeat ({cpb}) @(posedge clk); end
    rx = 1; repeat ({cpb} * 2) @(posedge clk); end endtask
  task getb(output [7:0] b); integer i; begin
    @(negedge tx); repeat ({cpb} + {cpb} / 2) @(posedge clk); b = 0;
    for (i = 0; i < 8; i = i + 1) begin b[i] = tx; repeat ({cpb}) @(posedge clk); end end endtask
  task getn(input integer n, output [143:0] o); integer k; reg [7:0] t; begin o = 0; for (k = 0; k < n; k = k + 1) begin getb(t); o = {{o[135:0], t}}; end end endtask
  initial begin
    repeat (400) @(posedge clk);
{chr(10).join(tasks)}
    if (bad == 0) $display("UCM2 PASS"); else $display("UCM2 FAIL %0d", bad);
    $finish;
  end
  initial begin #4000000000; $display("SIMTIMEOUT"); $finish; end
endmodule
"""
    open(os.path.join(work, "tbh.v"), "w").write(tb)
    c = subprocess.run(["iverilog", "-g2012", "-o", "tbh.vvp", "tbh.v"] + files, cwd=work, capture_output=True, text=True)
    if c.returncode:
        raise SystemExit("iverilog: " + c.stderr[:1500])
    return subprocess.run(["vvp", "tbh.vvp"], cwd=work, capture_output=True, text=True, timeout=6000).stdout


def pnr_report(work, name, top, files, seed, freq, pack_to=None, meta=None):
    """yosys + nextpnr. Returns dict(luts..., fmax). With pack_to, also writes the bitstream (only if timing met at `freq`)."""
    files = [os.path.relpath(f, work) if f.startswith(work + os.sep) else f for f in files]       # yosys cannot read a path with a segment starting with '-'
    s = subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {' '.join(files)}; hierarchy -check -top {top}; synth_gowin -top {top} -nowidelut -json {name}.json; tee -o {name}.stat stat"],
                       cwd=work, capture_output=True, text=True, timeout=6000)
    if s.returncode:
        raise SystemExit("yosys: " + s.stderr[-800:])
    p = subprocess.run(["yowasp-nextpnr-himbaechel-gowin", "--device", bt.DEVICE, "--vopt", "family=GW2A-18C", "--vopt", f"cst={name}.cst", "--seed", str(seed), "--json", f"{name}.json",
                        "--write", f"{name}_r.json", "--report", f"{name}_rep.json", "--freq", str(freq)], cwd=work, capture_output=True, text=True, timeout=9000)
    log = p.stdout[-8000:] + p.stderr[-4000:]
    if p.returncode:
        import re
        mm = re.search(r"Max frequency for clock '[^']*': ([0-9.]+) MHz", log)
        if mm and "FAIL at" in log:          # timing target not met: nextpnr still tells us the best it reached
            return dict(target_mhz=freq, fmax_mhz=float(mm.group(1)), met=False, utilization={}, seed=seed)
        raise SystemExit("nextpnr: " + log[-1200:])
    rep = json.load(open(os.path.join(work, name + "_rep.json")))
    fm = rep["fmax"]["clk"]["achieved"] if "clk" in rep["fmax"] else min(v["achieved"] for v in rep["fmax"].values())
    util = {k: dict(used=v["used"], available=v["available"]) for k, v in rep["utilization"].items() if v.get("used")}
    r = dict(target_mhz=freq, fmax_mhz=round(fm, 1), met=fm >= freq, utilization=util, seed=seed)
    if pack_to:
        open(os.path.join(pack_to, name + ".pnr.log"), "w").write(log)
        if fm < freq:
            raise SystemExit("timing NOT met at %s MHz (achieved %.1f); no bitstream written" % (freq, fm))
        g = subprocess.run(["gowin_pack", "-d", bt.DEVICE, "-o", os.path.join(pack_to, name + ".fs"), "-s", os.path.join(work, name + ".cst"), f"{name}_r.json"], cwd=work, capture_output=True, text=True)
        if g.returncode:
            raise SystemExit("gowin_pack: " + g.stderr[-500:])
        print("bitstream:", os.path.join(pack_to, name + ".fs"))
    if meta is not None:
        meta.update(r)
    return r


def build_files(work, keep, wrapper_text):
    carrier_v, removed = sub.make(keep)
    open(os.path.join(work, "carrier_sub.v"), "w").write(carrier_v)
    open(os.path.join(work, "board_uart_tx.v"), "w").write(bt.UART_V)
    open(os.path.join(work, "board_uart_rx.v"), "w").write(bm.UART_RX_V)
    top = "board_top_" + NAME
    open(os.path.join(work, top + ".v"), "w").write(wrapper_text)
    # the carrier's dependencies, plus the two standalone cells
    deps = set(vd.deps("unicell_vix_carrier_v1dm", [work, os.path.join(ROOT, "fpga", "verilog")]))
    deps |= set(vd.deps("command_cell_v4", [os.path.join(ROOT, "fpga", "verilog")]))
    deps |= set(vd.deps("sequencer_cell_v4", [os.path.join(ROOT, "fpga", "verilog")]))
    files = [os.path.join(work, "board_uart_tx.v"), os.path.join(work, "board_uart_rx.v"), os.path.join(work, top + ".v")] + sorted(deps)
    return top, files, removed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--out", default=os.path.join(ROOT, "fpga", "board_tests_mutability2"))
    ap.add_argument("--keep", default="adder,accum,mul")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--freq", type=float, default=27.0, help="nextpnr target MHz for the build (a bitstream is written only if this is met)")
    ap.add_argument("--no-pnr", action="store_true")
    ap.add_argument("--mutant", default="none", choices=["none", "nocfg", "wrongexp", "nocmd", "noseq"], help="simulation only: break the test on purpose and confirm it reports FAIL")
    ap.add_argument("--fit", help="semicolon list of keep sets (each a comma list, or 'all'): place-and-route only, report what fits and the static Fmax")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    work = os.path.join(out, "_work")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    if a.fit:
        rows = []
        for ks in [x for x in a.fit.split(";") if x]:
            keep = sub.CORES if ks == "all" else [k for k in ks.split(",") if k]
            top, files, removed = build_files(work, keep, wrapper(bt.CPB))
            open(os.path.join(work, NAME + ".cst"), "w").write(bm.cst_host())
            r = pnr_report(work, NAME, top, files, a.seed, a.freq)
            r["keep"] = ks
            rows.append(r)
            print("FIT keep=%s: Fmax %.1f MHz (target %s); %s" % (ks, r["fmax_mhz"], a.freq, {k: "%d/%d" % (v["used"], v["available"]) for k, v in r["utilization"].items()}), flush=True)
        json.dump(rows, open(os.path.join(out, "fit_%s.json" % ("%g" % a.freq)), "w"), indent=1)
        shutil.rmtree(work, ignore_errors=True)
        return
    keep = [k for k in a.keep.split(",") if k]
    if "adder" not in keep or "mul" not in keep:
        raise SystemExit("this test needs the adder and the mul in the carrier")
    ph = phases()
    if a.mutant == "wrongexp":
        ph[2] = dict(ph[2], expected=ph[2]["expected"] ^ 1)
    top, files, removed = build_files(work, keep, wrapper(bt.CPB, mutant=a.mutant, timeout_clk=100000))   # short timeouts only so a failing simulation ends quickly
    sim = sim_host(work, files, ph, nocfg=(a.mutant == "nocfg"))
    verdict = next((l for l in sim.splitlines() if l.startswith("UCM2")), "no verdict: " + sim[-400:])
    print("simulated (the testbench plays the PC):")
    print("  " + "\n  ".join(l for l in sim.splitlines() if l.startswith(("phase", "stream"))))
    print("  " + verdict)
    if a.mutant != "none":
        caught = "FAIL" in verdict
        print("  MUTANT %s -> %s" % (a.mutant, "caught (FAIL reported)" if caught else "NOT CAUGHT"))
        shutil.rmtree(work, ignore_errors=True)
        raise SystemExit(0 if caught else 1)
    if "PASS" not in verdict:
        raise SystemExit("the design did NOT pass in simulation; no bitstream written")
    meta = dict(name=NAME, cores_in_carrier=sorted(keep), cores_removed=removed, operands=[A_WORD, B_WORD], seq_cfg=SEQ_CFG, seq_values=list(SEQ_VALUES), stream_n=STREAM_N, cmd_cfg=CMD_CFG,
                phases=[dict(label=p["label"], kind=p["kind"], words_hex=["%08X" % w for w in p["words"]],
                             **({"expected": p["expected"]} if p["kind"] == "d" else {"n": p["n"], "first": p["first"], "last": p["last"]})) for p in ph],
                sim=[l for l in sim.splitlines() if l.startswith(("phase", "stream", "UCM2"))])
    open(os.path.join(work, top + ".v"), "w").write(wrapper(bt.CPB))      # the real build uses the long timeouts
    open(os.path.join(out, NAME + ".cst"), "w").write(bm.cst_host())
    shutil.copy(os.path.join(out, NAME + ".cst"), os.path.join(work, NAME + ".cst"))
    shutil.copy(os.path.join(work, top + ".v"), os.path.join(out, NAME + ".v"))
    shutil.copy(os.path.join(work, "carrier_sub.v"), os.path.join(out, "unicell_vix_carrier_v1dm.v"))
    if not a.no_pnr:
        pnr_report(work, NAME, top, files, a.seed, a.freq, pack_to=out, meta=meta.setdefault("build", {}))
        print("place and route: Fmax %.1f MHz (target %s); used: %s" % (meta["build"]["fmax_mhz"], a.freq, {k: "%d/%d" % (v["used"], v["available"]) for k, v in meta["build"]["utilization"].items()}))
    json.dump(meta, open(os.path.join(out, NAME + ".json"), "w"), indent=1)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
