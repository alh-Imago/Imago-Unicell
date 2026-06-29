// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// top_arria10.v — Imago UniCell Top Level for IEI Mustang-F100 (Arria 10 GX660)
// v1.0 — initial bring-up, 2×8 zone grid
//
// Target: 10AX066H2F34E2SG  Board: IEI Mustang-F100-A0E2-R10
//
// Grid: 2 rows × 8 cols = 16 zones × 28 cells = 448 cells total (~68% ALM load)
//
// Clock: 50MHz board ref → PLL stub → 200MHz target
//        Replace pll_stub with Quartus ALTPLL megafunction before full compile
//
// UART: fpga_bridge.py protocol unchanged from iCEBreaker
//
// Bridge wiring: all adjacent zones connected, unused directions tied low.
// Corner zones (Z00,Z07,Z08,Z15) stress the wired-OR bus across max distance.
//
// Pin assignments: set in .qsf — UART_RX, UART_TX, LED0_N, LED1_N
//
// TODO post bring-up:
//   - Replace PLL stub with generated megafunction
//   - Add PCIe Hard IP for DDR streaming
//   - Tune NUM_CELLS after first timing report

`default_nettype none
`timescale 1ns / 1ps

module top_arria10_zone1 (
    input  wire CLK_100M,  // 100 MHz board ref — diff pair CLK_2K_1, p-leg on E23 (pin in project .qsf)
    input  wire UART_RX,
    output wire UART_TX,
    output wire LED0_N,    // armed indicator (low = cells armed)
    output wire LED1_N     // heartbeat blink
);

// ── Parameters ────────────────────────────────────────────────────────────────
localparam NUM_CELLS   = 25;
localparam NUM_BRIDGES = 2;

// ── Clock — 100 MHz → 25 MHz via synchronous /4 divider ──────────────────────
// Board ref measured at 100.00 MHz on the CLK_2K_1 differential pair (E23/E24).
// /4 keeps the fabric at the original 25 MHz target (clk_div Fmax ~40 MHz).
// Synchronous counter (not a ripple toggle) so there's no derived-clock skew.
// Refinement: feed CLK_100M into an IOPLL for a jitter-clean, tunable fabric clock.
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk_div = div_cnt[1];   // CLK_100M / 4 = 25 MHz
wire CLK = clk_div;

// ── Reset — simple power-on reset, no PLL lock dependency ────────────────────
reg [3:0] rst_sr = 4'hF;
always @(posedge CLK)
    rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// ── Command bus — two masters muxed (UART + JTAG/ISSP) ───────────────────────
wire [31:0] u_bus, u_data;   wire u_valid;   // UART master (uart_bridge)
wire [31:0] j_bus, j_data;   wire j_valid;   // JTAG master (unicell_issp_bridge)
wire        array_rst_req;

// JTAG (ISSP) wins while it is issuing a transaction; UART drives otherwise.
wire [31:0] cpu_bus  = j_valid ? j_bus  : u_bus;
wire [31:0] cpu_data = j_valid ? j_data : u_data;
wire        cpu_valid = j_valid | u_valid;

// ── Target latch — the address-lane transport for CMD_LOAD_AT (opcode 23) ───────
// The 2-word ISSP cannot carry target + config + opcode at once. SET_TARGET (opcode
// 24, top-only — the cells ignore it) latches the target address and HOLDS it on the
// address lane. The following CMD_LOAD_AT then carries config on cpu_data while the
// held target drives cpu_addr, so the addressed cell's addr_match delivers the load.
// Stream an ICM file as (SET_TARGET addr, CMD_LOAD_AT config) pairs. 16-bit now;
// widen to the full hierarchical address later with zero cell impact.
localparam [7:0] OP_SET_TARGET = 8'd24;
localparam [7:0] OP_LOAD_AT    = 8'd23;
reg [15:0] load_target = 16'h0;
always @(posedge CLK) begin
    if (cpu_valid && (cpu_bus[7:0] == OP_SET_TARGET))
        load_target <= cpu_data[15:0];
end

wire [15:0] cpu_addr_w   = (cpu_bus[7:0] == 8'd1)         ? cpu_data[31:16]
                         : (cpu_bus[7:0] == OP_LOAD_AT)   ? load_target
                         : (cpu_bus[7:0] == 8'd2)         ? load_target  // SET_INPUT_ADDR
                         : (cpu_bus[7:0] == 8'd3)         ? load_target  // SET_OUTPUT_ADDR
                         : (cpu_bus[7:0] == 8'd25)        ? load_target  // CMD_SET_METHOD (64-bit upper-half write)
                         : cpu_data[15:0];
wire        preload_act  = (cpu_bus[18:17] != 2'b00);
wire        cmd_valid_w  = cpu_valid
                         && (cpu_bus[7:0] != 8'd1)
                         && ((cpu_bus[7:0] != 8'd0) || preload_act);

// ── Authenticated array reset ──────────────────────────────────────────────────
reg auth_rst_pulse = 1'b0;
always @(posedge CLK) begin
    auth_rst_pulse <= 1'b0;
    if (cpu_valid && (cpu_bus[7:0] == 8'd8) && (cpu_bus[28:21] != 8'h0))
        auth_rst_pulse <= 1'b1;
end
wire rst_all = rst | array_rst_req | auth_rst_pulse;

// ── Zone output wires ─────────────────────────────────────────────────────────
wire [15:0] z_out_addr  [0:15];
wire [31:0] z_out_data  [0:15];
wire        z_out_valid [0:15];
wire [15:0] z_armed     [0:15];
wire [15:0] z_arrived   [0:15];
wire [15:0] z_outset    [0:15];
wire [15:0] z_emit      [0:15];
wire [31:0] z_dbg0_cl; wire [31:0] z_dbg0_ia; wire [31:0] z_dbg0_oa; wire [31:0] z_dbg0_ad;
wire [31:0] z_cycles    [0:15];

// ── Bridge wires ──────────────────────────────────────────────────────────────
// Horizontal: between zone[r*8+c] east ↔ zone[r*8+c+1] west, r=0..1, c=0..6
// bh[r][c] carries east output of col c into west input of col c+1
wire [NUM_BRIDGES-1:0]    bh_v [0:1][0:6];
wire [NUM_BRIDGES*16-1:0] bh_a [0:1][0:6];
wire [NUM_BRIDGES*32-1:0] bh_d [0:1][0:6];

// Vertical: between zone[c] south ↔ zone[8+c] north, c=0..7
// bv[c] carries south output of row 0 into north input of row 1
wire [NUM_BRIDGES-1:0]    bv_v [0:7];
wire [NUM_BRIDGES*16-1:0] bv_a [0:7];
wire [NUM_BRIDGES*32-1:0] bv_d [0:7];

// Tie-off constants for unused bridge inputs
wire [NUM_BRIDGES-1:0]    tie_v  = {NUM_BRIDGES{1'b0}};
wire [NUM_BRIDGES*16-1:0] tie_a  = {(NUM_BRIDGES*16){1'b0}};
wire [NUM_BRIDGES*32-1:0] tie_d  = {(NUM_BRIDGES*32){1'b0}};

// ── Zone macro — reduces repetition ───────────────────────────────────────────
// 16 explicit instantiations: row 0 (Z00-Z07) then row 1 (Z08-Z15)
// Bridge connectivity:
//   Row 0: no north input  (tie), south output → bv[c]
//   Row 1: north input ← bv[c], no south output (tie outputs unused)
//   Col 0: no west input   (tie), east output → bh[r][0]
//   Col 7: east input ← bh[r][6], no east output (tie outputs unused)

// ── Row 0 ─────────────────────────────────────────────────────────────────────

// Z00  (r=0, c=0)  corners: no N, south→bv[0], no W, east→bh[0][0]
unicell_zone64 #(.NUM_CELLS(NUM_CELLS),.NUM_BRIDGES(NUM_BRIDGES),.ZONE_ID(0),.DEBUG_SELECT(1)) z00 (
    .clk(CLK),.rst(rst_all),
    .cmd_bus(cpu_bus),.cmd_data(cpu_data),.cmd_valid(cmd_valid_w),
    .cpu_addr(cpu_addr_w),.cpu_data(cpu_data),.cpu_valid(cpu_valid),
    .out_addr(z_out_addr[0]),.out_data(z_out_data[0]),.out_valid(z_out_valid[0]),
    .armed_count(z_armed[0]),.arrived_count(z_arrived[0]),.output_set_count(z_outset[0]),.emit_count(z_emit[0]),.dbg0_cmd_latch(z_dbg0_cl),.dbg0_input_addr(z_dbg0_ia),.dbg0_output_addr(z_dbg0_oa),.dbg0_a_data(z_dbg0_ad),.cycle_count(z_cycles[0]),
    .bridge_n_in_valid(tie_v),.bridge_n_in_addr(tie_a),.bridge_n_in_data(tie_d),
    .bridge_n_out_valid(),.bridge_n_out_addr(),.bridge_n_out_data(),
    .bridge_s_in_valid(tie_v),.bridge_s_in_addr(tie_a),.bridge_s_in_data(tie_d),
    .bridge_s_out_valid(bv_v[0]),.bridge_s_out_addr(bv_a[0]),.bridge_s_out_data(bv_d[0]),
    .bridge_e_in_valid(tie_v),.bridge_e_in_addr(tie_a),.bridge_e_in_data(tie_d),
    .bridge_e_out_valid(),.bridge_e_out_addr(),.bridge_e_out_data(),
    .bridge_w_in_valid(tie_v),.bridge_w_in_addr(tie_a),.bridge_w_in_data(tie_d),
    .bridge_w_out_valid(bh_v[0][0]),.bridge_w_out_addr(bh_a[0][0]),.bridge_w_out_data(bh_d[0][0])
);

// ── (single-zone build: zones Z01..Z15 removed; only Z00 active) ──

// ── Output collection — priority encoder, Z0 highest ──────────────────────────
reg [15:0] out_addr_r;
reg [31:0] out_data_r;
reg        out_valid_r;
reg [15:0] total_armed;
reg [15:0] total_arrived;
reg [15:0] total_outset;
reg [15:0] total_emit;

integer i;
always @(*) begin
    out_addr_r  = 16'h0;
    out_data_r  = 32'h0;
    out_valid_r = 1'b0;
    total_armed = 16'h0; total_arrived = 16'h0; total_outset = 16'h0; total_emit = 16'h0;
    for (i = 0; i >= 0; i = i - 1) begin
        if (z_out_valid[i]) begin
            out_addr_r  = z_out_addr[i];
            out_data_r  = z_out_data[i];
            out_valid_r = 1'b1;
        end
        total_armed = total_armed + z_armed[i]; total_arrived = total_arrived + z_arrived[i]; total_outset = total_outset + z_outset[i]; total_emit = total_emit + z_emit[i];
    end
end

// ── UART bridge ───────────────────────────────────────────────────────────────
uart_bridge #(
    .CLK_FREQ  (25_000_000),
    .BAUD_RATE (115_200)
) bridge (
    .clk         (CLK),
    .rst         (rst),
    .uart_rx     (UART_RX),
    .uart_tx     (UART_TX),
    .cpu_bus     (u_bus),
    .cpu_data    (u_data),
    .cpu_valid   (u_valid),
    .array_rst   (array_rst_req),
    .array_freeze(),
    .out_addr    (out_addr_r),
    .out_data    (out_data_r),
    .out_valid   (out_valid_r),
    .armed_count (total_armed),
    .cycle_count (z_cycles[0])
);

// ── ISSP (JTAG) host bridge — In-System Sources & Probes test channel ─────────
// Second command-bus master, driven from quartus_stp over the USB-Blaster.
// Requires the `issp` IP (source width 66, probe width 113, source clock = CLK)
// and unicell_issp_bridge.v added to the project.
unicell_issp_bridge issp_host (
    .clk         (CLK),
    .rst         (rst_all),
    .cpu_bus_o   (j_bus),
    .cpu_data_o  (j_data),
    .cpu_valid_o (j_valid),
    .out_addr    (out_addr_r),
    .out_data    (out_data_r),
    .out_valid   (out_valid_r),
    .armed_count (total_armed),
    .arrived_count   (total_arrived),
    .output_set_count(total_outset),
    .emit_count      (total_emit),
    .dbg0_cmd_latch  (z_dbg0_cl),
    .dbg0_input_addr (z_dbg0_ia),
    .dbg0_output_addr(z_dbg0_oa),
    .dbg0_a_data     (z_dbg0_ad),
    .cycle_count (z_cycles[0])
);

// ── Status LEDs ───────────────────────────────────────────────────────────────
reg led0_r    = 1'b1;
reg led1_r    = 1'b0;
reg [23:0] hb = 24'h0;

always @(posedge CLK) begin
    led0_r <= (total_armed == 0);
    hb     <= hb + 1'b1;
    led1_r <= hb[21];   // ~12Hz blink at 25MHz
end

assign LED0_N = led0_r;
assign LED1_N = ~led1_r;

endmodule
