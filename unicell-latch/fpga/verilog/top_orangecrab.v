// top_orangecrab.v — Top Level for OrangeCrab (ECP5 25F)
// Claudette v1.1
//
// OrangeCrab pinout:
//   CLK:     A9   (48MHz via USB PLL, or use onboard 48MHz osc)
//   UART_TX: N17  (GPIO — connect USB-serial adapter)
//   UART_RX: M18  (GPIO — connect USB-serial adapter)
//   LED_R:   K4   (RGB LED red — armed indicator)
//   LED_G:   M3   (RGB LED green — fired indicator)
//   LED_B:   J3   (RGB LED blue)
//   BTN:     V17  (user button — reset)
//
// Resource usage at 256 cells (ECP5 25F: 24288 LUTs):
//   LUTs:  ~12800 / 24288 (~53% — comfortable)
//
// At ~50 LUTs/cell on ECP5:
//   256 cells  = ~12800 LUTs (53% of 25F)
//   400 cells  = ~20000 LUTs (82% of 25F)
//   512+ cells = use ULX3S 85F
//
// Build with open source toolchain (yosys + nextpnr-ecp5):
//   yosys -p "synth_ecp5 -top top -json top.json" top_orangecrab.v unicell_array.v unicell.v uart_bridge.v
//   nextpnr-ecp5 --25k --package CSFBGA285 --json top.json --textcfg top.config --lpf orangecrab.lpf
//   ecppack --compress top.config top.bit
//   dfu-util -d 1209:5af0 -D top.bit   (via DFU bootloader)

`timescale 1ns / 1ps

module top (
    input  wire CLK,        // 48MHz system clock
    input  wire BTN,        // User button (active low, reset)
    input  wire RX,         // UART RX
    output wire TX,         // UART TX
    output wire LED_R,      // RGB red — armed indicator (active low)
    output wire LED_G,      // RGB green — fired indicator (active low)
    output wire LED_B       // RGB blue
);

parameter NUM_CELLS = 256;

// Clock divider: 48MHz → 12MHz for safe UART timing
reg [1:0] clk_div;
reg       clk_12;
always @(posedge CLK) begin
    clk_div <= clk_div + 1;
    if (clk_div == 2'b11) clk_12 <= ~clk_12;
end

wire clk = clk_12;
wire rst = ~BTN;            // Active low button

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
    .CLK_FREQ (12_000_000),
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

// ── Status LEDs (active low RGB) ─────────────────────────────────────────────
reg [23:0] fired_stretch;
always @(posedge clk) begin
    if (rst) fired_stretch <= 0;
    else if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end

assign LED_R = ~(fired_stretch > 0);    // Red: cell fired recently
assign LED_G = ~(armed_count > 0);      // Green: cells armed
assign LED_B = 1'b1;                    // Blue: off

endmodule
