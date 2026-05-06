// top_icebreaker_split.v — iCEBreaker top for unicell_latch_split variant
// Claudette v2.1 / unicell-latch-split
//
// VARIANT EXPLORER: This file builds the split variant for LUT comparison.
// Synthesise both top_icebreaker.v (latch) and this file, compare reports.
//
// Clock scheme:
//   clk    = SB_HFOSC "0b01" = 24MHz — external cell timing
//   clk_2x = SB_HFOSC "0b00" = 48MHz — internal tree (2x speed)
//   Both from same oscillator — no jitter, no PLL.
//
// External interface: identical to top_icebreaker.v
// Build:
//   yosys -p "synth_ice40 -top top -json top_split.json" \
//     top_icebreaker_split.v unicell_array_split.v unicell_latch_split.v uart_bridge.v
//   nextpnr-ice40 --up5k --package sg48 --json top_split.json \
//     --asc top_split.asc --pcf ../constraints/icebreaker.pcf --freq 24
//   icepack top_split.asc top_split.bin
//   iceprog top_split.bin

`default_nettype none
`timescale 1ns / 1ps

module top (
    input  wire BTN_N,
    input  wire RX,
    output wire TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// ── Clocks — 24MHz external, 48MHz internal ───────────────────────────────────
wire clk, clk_2x;
SB_HFOSC #(.CLKHF_DIV("0b01")) osc_24 (
    .CLKHFPU(1'b1), .CLKHFEN(1'b1), .CLKHF(clk)
);
SB_HFOSC #(.CLKHF_DIV("0b00")) osc_48 (
    .CLKHFPU(1'b1), .CLKHFEN(1'b1), .CLKHF(clk_2x)
);

wire rst = ~BTN_N;

localparam NUM_CELLS    = 8;
localparam BASE_ADDRESS = 32'h00000000;

wire [31:0] cpu_addr, cpu_data;
wire        cpu_valid, array_rst_req, array_freeze_req;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;
wire [NUM_CELLS-1:0] start_flags_wire;
wire [NUM_CELLS-1:0] start_flags_out_w;

// ── Split cell array ──────────────────────────────────────────────────────────
unicell_array_split #(
    .NUM_CELLS   (NUM_CELLS),
    .BASE_ADDRESS(BASE_ADDRESS)
) array (
    .clk             (clk),
    .clk_2x          (clk_2x),
    .rst             (rst | array_rst_req),
    .freeze          (array_freeze_req),
    .cpu_addr        (cpu_addr),
    .cpu_data        (cpu_data),
    .cpu_valid       (cpu_valid),
    .start_flags_in  (start_flags_wire),
    .start_flags_out (start_flags_out_w),
    .out_addr        (out_addr),
    .out_data        (out_data),
    .out_valid       (out_valid),
    .armed_count     (armed_count),
    .cycle_count     (cycle_count)
);

// ── UART bridge ───────────────────────────────────────────────────────────────
uart_bridge #(
    .CLK_FREQ (24_000_000),
    .BAUD_RATE(115_200)
) bridge (
    .clk          (clk),
    .rst          (rst),
    .uart_rx      (RX),
    .uart_tx      (TX),
    .cpu_addr     (cpu_addr),
    .cpu_data     (cpu_data),
    .cpu_valid    (cpu_valid),
    .array_rst    (array_rst_req),
    .array_freeze (array_freeze_req),
    .start_flags  (start_flags_wire),
    .out_addr     (out_addr),
    .out_data     (out_data),
    .out_valid    (out_valid),
    .armed_count  (armed_count),
    .cycle_count  (cycle_count)
);

// ── Status LEDs ───────────────────────────────────────────────────────────────
assign LEDR_N = (armed_count == 0);

reg [23:0] fired_stretch;
always @(posedge clk) begin
    if (rst) fired_stretch <= 0;
    else if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end
assign LEDG_N = (fired_stretch == 0);

endmodule
