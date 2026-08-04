// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// top_arty_a7.v — Top Level for Arty A7-35 and Arty A7-100 (Artix-7)
// Claudette v1.1
//
// Works for both Arty A7-35T and Arty A7-100T.
// Change the XDC file and NUM_CELLS to match your board.
//
// Arty A7 pinout (relevant signals):
//   CLK:     E3   (100MHz)
//   UART_TX: D10  (USB-UART via FTDI)
//   UART_RX: A9   (USB-UART via FTDI)
//   LED[0]:  H5   (armed indicator, RGB LED0 green)
//   LED[1]:  J5   (fired indicator, RGB LED0 red)
//   LED[2]:  T9   (user LED 0)
//   LED[3]:  T10  (user LED 1)
//   BTN[0]:  D9   (reset)
//
// Resource usage:
//   Arty A7-35T (33280 LUTs) at 256 cells:  ~35%  — good
//   Arty A7-100T (101440 LUTs) at 1024 cells: ~14% — comfortable
//
// Build with Vivado WebPack:
//   1. Create project, add all .v files
//   2. Add arty_a7_35.xdc or arty_a7_100.xdc as constraint file
//   3. Set top module to 'top', set NUM_CELLS parameter
//   4. Run Synthesis → Implementation → Generate Bitstream
//   5. Program via Vivado Hardware Manager
//
// For A7-35: set NUM_CELLS = 256 (comfortable) or up to 512 (tight)
// For A7-100: set NUM_CELLS = 1024 (comfortable) or up to 2000 (tight)

`timescale 1ns / 1ps

module top (
    input  wire       CLK,      // 100MHz system clock
    input  wire [3:0] BTN,      // Push buttons (BTN[0] = reset)
    input  wire [3:0] SW,       // Slide switches
    input  wire       RX,       // UART RX
    output wire       TX,       // UART TX
    output wire [3:0] LED,      // User LEDs
    output wire [2:0] LED0_RGB, // RGB LED 0 (R, G, B)
    output wire [2:0] LED1_RGB  // RGB LED 1 (R, G, B)
);

// Clock divider: 100MHz → 25MHz
// Remove if targeting higher clock, add PLL for anything above 50MHz
reg [1:0] clk_div;
reg       clk_25;
always @(posedge CLK) begin
    clk_div <= clk_div + 1;
    if (clk_div == 2'b11) clk_25 <= ~clk_25;
end

wire clk = clk_25;
wire rst = BTN[0];

// ── Select cell count — change to match your board ────────────────────────────
// A7-35: 256 recommended, 512 maximum
// A7-100: 1024 recommended, 2000 maximum
`ifdef ARTY_A7_100
    parameter NUM_CELLS = 1024;
`else
    parameter NUM_CELLS = 256;   // Default: A7-35
`endif

// ── UniCell array ─────────────────────────────────────────────────────────────
wire [31:0] cpu_addr, cpu_data;
wire        cpu_valid, array_rst_req;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

unicell_array #(
    .NUM_CELLS(NUM_CELLS)
) array (
    .clk        (clk),
    .rst        (rst | array_rst_req),
    .cpu_addr   (cpu_addr),
    .cpu_data   (cpu_data),
    .cpu_valid  (cpu_valid),
    .cpu_inject (1'b0),
    .out_addr   (out_addr),
    .out_data   (out_data),
    .out_valid  (out_valid),
    .armed_count(armed_count),
    .cycle_count(cycle_count)
);

// ── UART bridge ───────────────────────────────────────────────────────────────
uart_bridge #(
    .CLK_FREQ (25_000_000),
    .BAUD_RATE(115_200)
) bridge (
    .clk        (clk),
    .rst        (rst),
    .uart_rx    (RX),
    .uart_tx    (TX),
    .cpu_addr   (cpu_addr),
    .cpu_data   (cpu_data),
    .cpu_valid  (cpu_valid),
    .array_rst  (array_rst_req),
    .out_addr   (out_addr),
    .out_data   (out_data),
    .out_valid  (out_valid),
    .armed_count(armed_count),
    .cycle_count(cycle_count)
);

// ── Status LEDs ───────────────────────────────────────────────────────────────
reg [23:0] fired_stretch;
always @(posedge clk) begin
    if (rst) fired_stretch <= 0;
    else if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end

// RGB LED 0: Green = armed cells present, Red = cell fired recently
assign LED0_RGB[0] = (fired_stretch > 0);   // Red — fired
assign LED0_RGB[1] = (armed_count > 0);     // Green — armed
assign LED0_RGB[2] = 1'b0;                  // Blue — off

// RGB LED 1: shows armed count upper bits
assign LED1_RGB[0] = armed_count[8];
assign LED1_RGB[1] = armed_count[9];
assign LED1_RGB[2] = armed_count[10];

// User LEDs: lower 4 bits of armed_count
assign LED = armed_count[3:0];

endmodule
