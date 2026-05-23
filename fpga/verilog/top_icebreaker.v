// top_icebreaker.v — Imago UniCell Top Level for iCEBreaker
// v2.0 — command bus architecture
//
// CLOCK: SB_HFOSC internal oscillator, NOT the external crystal.
//   "0b10" = 12MHz — reduced from 24MHz; 32-bit gate tree needs timing margin.
//
// Changes from v1.2:
//   - freeze wire removed — CMD_FREEZE on command bus handles it
//   - BASE_ADDRESS removed — cells have no fixed config address
//   - cpu_inject removed
//   - cmd_bus/cmd_data/cmd_valid wired from bridge to array

`default_nettype none

module top (
    input  wire BTN_N,
    input  wire RX,
    output wire TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// Internal HFOSC — 12MHz (48MHz / 4), reduced from 24MHz for 32-bit gate tree timing
wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b10")) osc (
    .CLKHFPU(1'b1),
    .CLKHFEN(1'b1),
    .CLKHF(CLK)
);

wire rst = 1'b0;

// ── Wires between bridge and array ───────────────────────────────────────────
wire  [7:0] cpu_cmd;
wire [15:0] cpu_addr;
wire [31:0] cpu_data;
wire        cpu_valid, array_rst_req;

// Command bus — from bridge to all cells
wire  [7:0] cmd_bus_w  = cpu_cmd;   // 8-bit opcode
wire [31:0] cmd_data_w = cpu_data;  // 32-bit payload (auth[31:24] + config[23:0])
wire        cmd_valid_w;             // driven when bridge issues a command word

// Data bus — from bridge to array
wire [15:0] out_addr;
wire [31:0] out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

// cmd_valid fires when bridge drives a command (cpu_cmd non-NOP)
// For this baseline: treat cpu_valid as cmd_valid when cmd byte indicates
// a command-bus operation (codes 2-6,9), data bus otherwise.
// Simple split: bridge 0x01 packet → data bus; all others → command bus.
// uart_bridge already separates these via cpu_cmd vs cpu_addr/cpu_data.
// Here we just broadcast cmd on every cpu_valid — cell ignores NOP (code 0).
assign cmd_valid_w = cpu_valid;

unicell_array #(
    .NUM_CELLS(4)
) array (
    .clk        (CLK),
    .rst        (rst | array_rst_req),
    .cmd_bus    (cmd_bus_w),
    .cmd_data   (cmd_data_w),
    .cmd_valid  (cmd_valid_w),
    .cpu_addr   (cpu_addr),
    .cpu_data   (cpu_data),
    .cpu_valid  (cpu_valid),
    .out_addr   (out_addr),
    .out_data   (out_data),
    .out_valid  (out_valid),
    .armed_count(armed_count),
    .cycle_count(cycle_count)
);

uart_bridge #(
    .CLK_FREQ (12_000_000),
    .BAUD_RATE(115_200)
) bridge (
    .clk         (CLK),
    .rst         (rst),
    .uart_rx     (RX),
    .uart_tx     (TX),
    .cpu_cmd     (cpu_cmd),
    .cpu_addr    (cpu_addr),
    .cpu_data    (cpu_data),
    .cpu_valid   (cpu_valid),
    .array_rst   (array_rst_req),
    .array_freeze(),             // no longer a wire — CMD_FREEZE handles it
    .out_addr    (out_addr),
    .out_data    (out_data),
    .out_valid   (out_valid),
    .armed_count (armed_count),
    .cycle_count (cycle_count)
);

// LEDs — registered to keep combinational comparison off async IO path
reg ledr_n_reg = 1'b1;
always @(posedge CLK) ledr_n_reg <= (armed_count == 0);
assign LEDR_N = ledr_n_reg;
assign LEDG_N = 1'b0;  // Green always on

endmodule
