// top_icebreaker.v — Imago UniCell Top Level for iCEBreaker
// Uses internal SB_HFOSC oscillator — NO external clock pin needed.
//
// CLOCK WARNING:
//   The iCEBreaker 12MHz crystal is on physical pin 35.
//   Documentation inconsistency: schematic says pin 2, manual says pin 35.
//   DO NOT use the external crystal — use SB_HFOSC instead (simpler, stable).
//
// SB_HFOSC divider settings:
//   "0b00" = 48MHz   (may fail timing on some paths)
//   "0b01" = 24MHz   ← VALIDATED on hardware, solid, recommended
//   "0b10" = 12MHz   (nominal, actual ~12.26MHz measured)
//   "0b11" = 6MHz    (safe but slow)
//
// VALIDATED: 24MHz solid on first silicon bring-up, 14 May 2026.
// NOT gate and wired-OR NAND both confirmed correct. Errors: 0.

`default_nettype none

module top (
    input  wire BTN_N,
    input  wire RX,
    output wire TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// Internal HFOSC — 24MHz (48MHz / 2), validated on hardware
wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b01")) osc (
    .CLKHFPU(1'b1),
    .CLKHFEN(1'b1),
    .CLKHF(CLK)
);

// rst permanently low for now
wire rst = 1'b0;

// Cell array
wire [31:0] cpu_addr, cpu_data;
wire        cpu_valid, array_rst_req, array_freeze_req;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

unicell_array #(
    .NUM_CELLS(8),
    .BASE_ADDRESS(32'h00000000)  // cell 0=0x0, cell 1=0x1 -- matches fpga_bridge.py
) array (
    .clk        (CLK),
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

// UART bridge
uart_bridge #(
    .CLK_FREQ (24_000_000),  // SB_HFOSC "0b01" = 24MHz, validated on hardware
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

// LEDs
assign LEDR_N = (armed_count == 0);  // Red LED on when cells are armed
assign LEDG_N = 1'b0;   // Green always on

endmodule
