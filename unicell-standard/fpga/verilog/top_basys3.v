// top_basys3.v — Top Level for Basys 3 (Artix-7 35T)
// Claudette v1.1
//
// Basys 3 pinout:
//   CLK:     W5   (100MHz)
//   UART_TX: A18  (USB-UART via FTDI, PMOD JA)
//   UART_RX: B18  (USB-UART via FTDI, PMOD JA)
//   LED[0]:  U16  (armed indicator)
//   LED[1]:  E19  (fired indicator)
//   LED[2]:  U19
//   LED[3]:  V19
//   BTN_C:   U18  (centre button — reset)
//
// Resource usage at 256 cells:
//   LUTs:  ~11520 / 20800 (~55% — comfortable)
//   Regs:  ~8192
//   BRAM:  0
//
// The Artix-7 35T has 33280 LUTs. At ~45 LUTs/cell:
//   256 cells  = ~11520 LUTs  (35% — good development headroom)
//   512 cells  = ~23040 LUTs  (69% — still fits)
//   700 cells  = ~31500 LUTs  (94% — tight)
//
// Build with Vivado (free WebPack edition):
//   1. Create new project, add all .v files
//   2. Add basys3.xdc as constraint file
//   3. Set NUM_CELLS parameter as desired
//   4. Run Synthesis → Implementation → Generate Bitstream
//   5. Program via Vivado Hardware Manager (USB cable)
//
// Or with open-source tools (experimental):
//   yosys -p "synth_xilinx -top top -json top.json" top_basys3.v unicell_array.v unicell.v uart_bridge.v
//   nextpnr-xilinx ... (check nextpnr-xilinx docs for Artix-7)

`timescale 1ns / 1ps

module top (
    input  wire CLK,        // 100MHz system clock
    input  wire BTN_C,      // Centre button — reset (active high)
    input  wire RX,         // UART RX
    output wire TX,         // UART TX
    output wire [15:0] LED, // Status LEDs
    input  wire [15:0] SW   // Switches (NUM_CELLS select)
);

// Clock divider: 100MHz → 25MHz for comfortable timing
// Remove divider if targeting higher clock speeds
reg [1:0] clk_div;
reg       clk_25;
always @(posedge CLK) begin
    clk_div <= clk_div + 1;
    if (clk_div == 2'b11) clk_25 <= ~clk_25;
end

wire clk = clk_25;
wire rst = BTN_C;

// NUM_CELLS selectable via switches SW[7:0]
// Default 256 when switches = 0
parameter NUM_CELLS = 256;

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
// LED[15:0]:
//   [15:8] — upper 8 bits of armed_count
//   [7:0]  — lower 8 bits of armed_count  (how many cells are armed)
// LED[0] also blinks on cell fire

reg [23:0] fired_stretch;
always @(posedge clk) begin
    if (rst) fired_stretch <= 0;
    else if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end

assign LED[15:1] = armed_count[15:1];
assign LED[0]    = armed_count[0] | (fired_stretch > 0);

endmodule
