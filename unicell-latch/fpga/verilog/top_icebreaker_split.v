// top_icebreaker_split.v — iCEBreaker top for unicell_latch_split variant
// Claudette v2.1 / unicell-latch-split
//
// Two clocks from same SB_HFOSC:
//   clk    = 24MHz (0b01) — external cell timing
//   clk_2x = 48MHz (0b00) — internal tree (2x speed)
//
// Build:
//   yosys -p "read_verilog verilog/unicell_latch_split.v; read_verilog verilog/unicell_array_split.v; read_verilog verilog/uart_bridge.v; read_verilog verilog/top_icebreaker_split.v; synth_ice40 -top top -json build/split.json"
//   nextpnr-ice40 --up5k --package sg48 --pcf constraints/icebreaker.pcf --json build/split.json --asc build/split.asc --freq 24
//   icepack build/split.asc build/split.bin
//   iceprog build/split.bin

`default_nettype none
`timescale 1ns / 1ps

module top (
    input  wire BTN_N,
    input  wire RX,
    output wire TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// ── Clocks ────────────────────────────────────────────────────────────────────
wire clk, clk_2x;
SB_HFOSC #(.CLKHF_DIV("0b01")) osc_24 (
    .CLKHFPU(1'b1), .CLKHFEN(1'b1), .CLKHF(clk)
);
SB_HFOSC #(.CLKHF_DIV("0b00")) osc_48 (
    .CLKHFPU(1'b1), .CLKHFEN(1'b1), .CLKHF(clk_2x)
);

wire rst = ~BTN_N;

localparam NUM_CELLS    = 8;
localparam BASE_ADDRESS = 32'h00000000;

wire [31:0] cpu_addr, cpu_data;
wire        cpu_valid, array_rst_req, array_freeze_req;
wire [31:0] out_addr, out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

// ── Split cell array ──────────────────────────────────────────────────────────
unicell_array_split #(
    .NUM_CELLS   (NUM_CELLS),
    .BASE_ADDRESS(BASE_ADDRESS)
) array (
    .clk         (clk),
    .clk_2x      (clk_2x),
    .rst         (rst | array_rst_req),
    .freeze      (array_freeze_req),
    .cpu_addr    (cpu_addr),
    .cpu_data    (cpu_data),
    .cpu_valid   (cpu_valid),
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
    .clk          (clk),
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
always @(posedge clk) begin
    if (rst) fired_stretch <= 0;
    else if (out_valid) fired_stretch <= 24'hFFFFFF;
    else if (fired_stretch > 0) fired_stretch <= fired_stretch - 1;
end
assign LEDG_N = (fired_stretch == 0);

endmodule
