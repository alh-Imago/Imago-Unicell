// top_icebreaker.v — Top Level for iCEBreaker (iCE40UP5K)
// Claudette v2.1 / unicell-latch variant
//
// CLOCK: Uses internal SB_HFOSC — NO external clock pin needed.
//   External 12MHz crystal pin numbering is inconsistent across docs.
//   SB_HFOSC "0b01" = 24MHz — VALIDATED on iCEBreaker 14 May 2026.
//
// UART pins (iCEBreaker PMOD1A):
//   TX: pin 9  (PMOD1A pin 1)
//   RX: pin 10 (PMOD1A pin 2)
//
// LEDs:
//   LEDR_N: pin 11 (active low — lit when cells armed)
//   LEDG_N: pin 37 (active low — blinks on cell fire)
//
// BTN: pin 10 (reset, active low)
//
// Resource usage at 8 cells (latch variant ~550 LUTs/cell estimated):
//   ~4400 LUTs / 5280 (83%) — fits with some headroom
//   Reduce NUM_CELLS if synthesis fails timing.
//
// Build:
//   yosys -p "synth_ice40 -top top -json top.json" \
//     top_icebreaker.v unicell_array_latch.v unicell_latch.v uart_bridge.v
//   nextpnr-ice40 --up5k --package sg48 --json top.json --asc top.asc \
//     --pcf icebreaker.pcf --freq 24
//   icepack top.asc top.bin
//   iceprog top.bin

`default_nettype none
`timescale 1ns / 1ps

module top (
    input  wire BTN_N,      // Reset button (active low)
    input  wire RX,         // UART RX
    output wire TX,         // UART TX
    output wire LEDR_N,     // Red LED  (active low) — cells armed
    output wire LEDG_N      // Green LED (active low) — cell fired
);

// ── Clock — internal SB_HFOSC, 24MHz validated ───────────────────────────────
wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b01")) osc (
    .CLKHFPU(1'b1),
    .CLKHFEN(1'b1),
    .CLKHF(CLK)
);

// ── Reset ─────────────────────────────────────────────────────────────────────
wire rst = ~BTN_N;

// ── Parameters ────────────────────────────────────────────────────────────────
localparam NUM_CELLS    = 8;            // Safe for iCEBreaker at ~550 LUTs/cell
localparam BASE_ADDRESS = 32'h00000000; // Cell 0=0x0 ... matches fpga_bridge.py

// ── Wiring ────────────────────────────────────────────────────────────────────
wire [31:0] cpu_addr, cpu_data;
wire        cpu_valid, array_rst_req, array_freeze_req;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;
// start_flags: tie high to keep all cells armed after config
assign start_flags_wire = {NUM_CELLS{1'b1}};
wire [NUM_CELLS-1:0] start_flags_out_w;

// ── UniCell latch array ───────────────────────────────────────────────────────
unicell_array_latch #(
    .NUM_CELLS   (NUM_CELLS),
    .BASE_ADDRESS(BASE_ADDRESS)
) array (
    .clk             (CLK),
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
    .CLK_FREQ (24_000_000),   // SB_HFOSC "0b01" = 24MHz, validated
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

// ── Status LEDs ───────────────────────────────────────────────────────────────
assign LEDR_N = (armed_count == 0);    // Red: lit when cells armed

reg [23:0] fired_stretch;
always @(posedge CLK) begin
    if (rst) fired_stretch <= 0;
    else if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end
assign LEDG_N = (fired_stretch == 0);  // Green: blinks on cell fire

endmodule
