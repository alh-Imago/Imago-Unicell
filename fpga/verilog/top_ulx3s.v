// top_ulx3s.v — Top Level for ULX3S (ECP5 85F)
// Claudette v1.1
//
// ULX3S pinout:
//   CLK:     G2   (25MHz)
//   UART_TX: L4   (FTDI USB-UART)
//   UART_RX: M1   (FTDI USB-UART)
//   LED[0]:  B2   (armed indicator)
//   LED[1]:  C2   (fired indicator)
//   LED[2]:  D2
//   LED[3]:  D1
//   LED[4]:  E2
//   LED[5]:  E1
//   LED[6]:  H3
//   LED[7]:  H2
//   BTN_PWR: R1   (reset — active low)
//
// Resource usage at 1024 cells (ECP5 85F: 83640 LUTs):
//   LUTs:  ~51200 / 83640 (~61% — comfortable)
//
// At ~50 LUTs/cell on ECP5:
//   1024 cells = ~51200 LUTs (61% of 85F — plenty of room)
//   1500 cells = ~75000 LUTs (90% — tight)
//
// The ULX3S is the roomiest board in the supported set.
// Use it when you need 1024+ cells with comfortable routing headroom.
//
// Build with open source toolchain:
//   yosys -p "synth_ecp5 -top top -json top.json" top_ulx3s.v unicell_array.v unicell.v uart_bridge.v
//   nextpnr-ecp5 --85k --package CABGA381 --json top.json --textcfg top.config --lpf ulx3s.lpf
//   ecppack --compress top.config top.bit
//   fujprog top.bit   (or openFPGALoader -b ulx3s top.bit)

`timescale 1ns / 1ps

module top (
    input  wire       CLK,      // 25MHz system clock
    input  wire       BTN_PWR,  // Power/reset button (active low)
    input  wire [6:0] BTN,      // User buttons
    input  wire       RX,       // UART RX (FTDI)
    output wire       TX,       // UART TX (FTDI)
    output wire [7:0] LED       // User LEDs
);

parameter NUM_CELLS = 1024;

// No clock division needed at 25MHz — safe for UART and cell timing
wire clk = CLK;
wire rst = ~BTN_PWR;

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
// LED[0]: any cells armed
// LED[1]: cell fired recently (blinks on activity)
// LED[7:2]: upper 6 bits of armed_count (shows scale)

reg [23:0] fired_stretch;
always @(posedge clk) begin
    if (rst) fired_stretch <= 0;
    else if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end

assign LED[0] = (armed_count > 0);
assign LED[1] = (fired_stretch > 0);
assign LED[7:2] = armed_count[9:4];   // Scale indicator

endmodule
