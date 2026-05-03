// top_asic.v — Top Level for ASIC / Custom Silicon
// Claudette v2.1 / unicell-standard variant
//
// ASIC-facing top-level. Board-specific constraints (pin names, clock
// frequency, UART baud) are the ONLY things that differ from the FPGA
// top files. The cell and array below are identical to the FPGA build.
//
// Intended for:
//   SKY130 open PDK (Tiny Tapeout 130nm)
//   GF180 open PDK
//   Any 28nm–3nm foundry process via standard cell library
//
// Interface:
//   clk      — system clock (any frequency; parameterise BAUD below)
//   rst      — synchronous active-high reset
//   rx / tx  — UART host interface (replaceable with AXI-Lite, SPI, etc)
//
// The UART bridge is included as the default host interface because it
// requires no vendor IP and works from a simple serial connection. For
// production ASIC the bridge module can be swapped for AXI-Lite, PCIe,
// or any other bus protocol — the unicell_array interface is unchanged.
//
// Parameterisation:
//   NUM_CELLS  — array size. Scale to fit die area.
//                SKY130 Tiny Tapeout target: 8–32 cells (small die area).
//                Full production ASIC: tens of thousands of cells.
//   CLK_FREQ   — system clock frequency in Hz. Sets UART baud divisor.
//   BAUD_RATE  — UART baud rate. 115200 default; increase for faster host I/O.
//
// No vendor-specific primitives. Standard Verilog-2001 only.
// Hand this file (plus unicell.v, unicell_array.v, uart_bridge.v) to
// the foundry flow. All synthesis constraints are external to these files.
//
// Tiny Tapeout 130nm resource estimate (per cell):
//   Standard cell area: ~1500 μm² per UniCell at 130nm
//   8-cell array: ~12,000 μm² (~0.012 mm²) — fits comfortably in 1 tile
//   32-cell array: ~48,000 μm² (~0.048 mm²) — tight for 1 tile, fine for 2
//
// Next steps for tapeout:
//   1. Select PDK and standard cell library
//   2. Run synthesis: yosys + abc (SKY130) or commercial tool (GF180+)
//   3. Timing analysis at target clock frequency
//   4. Place and route — cells and array are regular structures, route well
//   5. DRC / LVS clean
//   6. GDS handoff

`timescale 1ns / 1ps

module top_asic #(
    parameter NUM_CELLS  = 8,            // Scale for die area. 8 = SKY130 1-tile target.
    parameter CLK_FREQ   = 50_000_000,   // 50MHz default; set to actual PLL output
    parameter BAUD_RATE  = 115_200       // UART baud rate
) (
    input  wire clk,        // System clock
    input  wire rst,        // Synchronous reset (active high)

    // UART host interface — replace with AXI-Lite / SPI / custom for production
    input  wire rx,         // UART RX from host
    output wire tx,         // UART TX to host

    // Status outputs — connect to bond pads or leave unconnected
    output wire [15:0] armed_count,   // Number of armed cells
    output wire [31:0] cycle_count    // Execution cycle counter
);

// ── Internal wires ────────────────────────────────────────────────────────────
wire [31:0] cpu_addr, cpu_data;
wire        cpu_valid;
wire        array_rst_req, array_freeze_req;
wire [31:0] out_addr, out_data;
wire        out_valid;

// ── UniCell array ─────────────────────────────────────────────────────────────
unicell_array #(
    .NUM_CELLS(NUM_CELLS)
) array_inst (
    .clk        (clk),
    .rst        (rst | array_rst_req),
    .freeze     (array_freeze_req),
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
// Replace this module with AXI-Lite, SPI, or custom host interface as needed.
// The unicell_array interface (cpu_addr, cpu_data, cpu_valid, out_*) is stable.
uart_bridge #(
    .CLK_FREQ (CLK_FREQ),
    .BAUD_RATE(BAUD_RATE)
) bridge_inst (
    .clk          (clk),
    .rst          (rst),
    .uart_rx      (rx),
    .uart_tx      (tx),
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

endmodule
