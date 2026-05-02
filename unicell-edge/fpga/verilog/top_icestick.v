// top_icestick.v — Top Level for IceStick (iCE40HX1K)
// Claudette v1.1
//
// IceStick pinout:
//   CLK:     21  (12MHz)
//   UART_TX: 8   (FTDI direct)
//   UART_RX: 9   (FTDI direct)
//   LED[0]:  99  (armed indicator — PMOD D1)
//   LED[1]:  98  (fired indicator — PMOD D2)
//   LED[2]:  97  (PMOD D3)
//   LED[3]:  96  (PMOD D4)
//   LED[4]:  95  (PMOD D7)
//
// Resource usage at 16 cells:
//   LUTs:  ~1280 / 1280 (100% — tight, may need 12 cells)
//   Regs:  ~512
//
// The HX1K has only 1280 LUTs. At ~80 LUTs/cell:
//   8 cells  = ~640 LUTs  (50% — comfortable)
//   12 cells = ~960 LUTs  (75% — good)
//   16 cells = ~1280 LUTs (100% — may not route)
//
// Recommended: NUM_CELLS = 8 for first build, 12 if it fits.
// This is a proof-of-concept board — use iCEBreaker for real work.
//
// Build with open source toolchain:
//   yosys -p "synth_ice40 -top top -json top.json" top_icestick.v unicell_array.v unicell.v uart_bridge.v
//   nextpnr-ice40 --hx1k --package tq144 --json top.json --asc top.asc --pcf icestick.pcf
//   icepack top.asc top.bin
//   iceprog top.bin

`timescale 1ns / 1ps

module top (
    input  wire CLK,        // 12MHz system clock
    input  wire RX,         // UART RX (FTDI)
    output wire TX,         // UART TX (FTDI)
    output wire LED0,       // Armed indicator
    output wire LED1,       // Fired indicator
    output wire LED2,
    output wire LED3,
    output wire LED4
);

parameter NUM_CELLS = 8;    // Conservative — fits HX1K comfortably

wire rst = 1'b0;            // IceStick has no button — hold reset low

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
    .clk        (CLK),
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
    .clk        (CLK),
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
assign LED0 = (armed_count > 0);    // Any cells armed

reg [23:0] fired_stretch;
always @(posedge CLK) begin
    if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end
assign LED1 = (fired_stretch > 0);  // Cell fired recently

assign LED2 = armed_count[0];
assign LED3 = armed_count[1];
assign LED4 = armed_count[2];

endmodule
