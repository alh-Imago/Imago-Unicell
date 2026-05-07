// top_icebreaker.v — Top Level for iCEBreaker (iCE40UP5K)
// Claudette v2.1 / unicell-edge variant
//
// CLOCK: SB_HFOSC internal oscillator — no external clock pin needed.
//   "0b01" = 24MHz VALIDATED on iCEBreaker 14 May 2026.
//   External 12MHz crystal pin numbering inconsistent across docs — avoid.
//
// UART pins: RX=6, TX=9, BTN_N=10, LEDR_N=11, LEDG_N=12
//
// NUM_CELLS: 8 for iCEBreaker bring-up (edge variant ~550 LUTs/cell)
//
// Build:
//   yosys -p "read_verilog verilog/unicell.v; read_verilog verilog/unicell_array.v; read_verilog verilog/uart_bridge.v; read_verilog verilog/top_icebreaker.v; synth_ice40 -top top -json build/edge.json"
//   nextpnr-ice40 --up5k --package sg48 --pcf constraints/icebreaker.pcf --json build/edge.json --asc build/edge.asc --freq 24
//   icepack build/edge.asc build/edge.bin
//   iceprog build/edge.bin

`timescale 1ns / 1ps
`default_nettype none

module top (
    input  wire BTN_N,
    input  wire RX,
    output wire TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// ── Clock — internal SB_HFOSC, 24MHz validated ───────────────────────────────
wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b01")) osc (
    .CLKHFPU(1'b1), .CLKHFEN(1'b1), .CLKHF(CLK)
);

wire rst = ~BTN_N;

localparam NUM_CELLS    = 8;
localparam BASE_ADDRESS = 32'h00000000;  // matches fpga_bridge.py

wire [31:0] cpu_addr, cpu_data;
wire        cpu_valid, array_rst_req, array_freeze_req;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

// ── UniCell edge array ────────────────────────────────────────────────────────
unicell_array #(
    .NUM_CELLS   (NUM_CELLS),
    .BASE_ADDRESS(BASE_ADDRESS)
) array (
    .clk         (CLK),
    .rst         (rst | array_rst_req),
    .freeze      (array_freeze_req),
    .cpu_addr    (cpu_addr),
    .cpu_data    (cpu_data),
    .cpu_valid   (cpu_valid),
    .cpu_inject  (cpu_valid),   // same as cpu_valid for host-initiated transactions
    .out_addr    (out_addr),
    .out_data    (out_data),
    .out_valid   (out_valid),
    .armed_count (armed_count),
    .cycle_count (cycle_count)
);

// ── UART bridge ───────────────────────────────────────────────────────────────
uart_bridge #(
    .CLK_FREQ (24_000_000),
    .BAUD_RATE(115_200)
) bridge (
    .clk          (CLK),
    .rst          (rst),
    .uart_rx      (RX),
    .uart_tx      (TX),
    .cpu_addr     (cpu_addr),
    .cpu_data     (cpu_data),
    .cpu_valid    (cpu_valid),
    .array_rst    (array_rst_req),
    .array_freeze (array_freeze_req),
    .out_addr     (out_addr),
    .out_data     (out_data),
    .out_valid    (out_valid),
    .armed_count  (armed_count),
    .cycle_count  (cycle_count)
);

// ── LEDs ──────────────────────────────────────────────────────────────────────
assign LEDR_N = (armed_count == 0);

reg [23:0] fired_stretch = 0;
always @(posedge CLK) begin
    if (rst) fired_stretch <= 0;
    else if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end
assign LEDG_N = (fired_stretch == 0);

endmodule
