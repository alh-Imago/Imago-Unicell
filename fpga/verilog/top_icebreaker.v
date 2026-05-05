// top_icebreaker.v — Imago UniCell Top Level for iCEBreaker
// HFOSC 48MHz, uart_bridge connected, unicell_array_stub

`default_nettype none

module top (
    input  wire BTN_N,
    input  wire RX,
    output wire TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// Internal HFOSC — 12MHz nominal (actual ~12.26MHz measured)
wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b10")) osc (
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
    .CLK_FREQ (12_257_280),  // HFOSC actual ~12.26MHz (CPB=106 at 115200 baud)
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
assign LEDR_N = 1'b0;   // Red always on — design running
assign LEDG_N = 1'b0;   // Green always on

endmodule
