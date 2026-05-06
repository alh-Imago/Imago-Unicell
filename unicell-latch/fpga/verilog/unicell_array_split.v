// unicell_array_split.v — Array wrapper for unicell_latch_split
// Claudette v2.1 / unicell-latch-split variant
//
// Identical interface to unicell_array_latch.v.
// Generates both clk and clk_2x from SB_HFOSC internally.
// External interface unchanged — drop-in replacement.

`timescale 1ns / 1ps
`default_nettype none

module unicell_array_split #(
    parameter NUM_CELLS    = 8,
    parameter BASE_ADDRESS = 0
) (
    input  wire        clk,         // 24MHz external cell clock
    input  wire        clk_2x,      // 48MHz internal tree clock
    input  wire        rst,
    input  wire        freeze,

    input  wire [31:0] cpu_addr,
    input  wire [31:0] cpu_data,
    input  wire        cpu_valid,

    input  wire [NUM_CELLS-1:0] start_flags_in,
    output wire [NUM_CELLS-1:0] start_flags_out,

    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    output wire [15:0] armed_count,
    output wire [31:0] cycle_count
);

// ── Wired-OR bus (same as unicell_array_latch.v) ──────────────────────────────
wire [31:0] cell_out_addr  [0:NUM_CELLS-1];
wire [31:0] cell_out_data  [0:NUM_CELLS-1];
wire        cell_out_valid [0:NUM_CELLS-1];

// ── Cell instantiation ────────────────────────────────────────────────────────
genvar i;
generate
    for (i = 0; i < NUM_CELLS; i = i + 1) begin : cell_array
        unicell_latch_split #(
            .CONFIG_ADDRESS (BASE_ADDRESS + i)
        ) cell (
            .clk            (clk),
            .clk_2x         (clk_2x),
            .rst            (rst),
            .freeze         (freeze),
            .bus_addr       (cpu_addr),
            .bus_data       (cpu_data),
            .bus_valid      (cpu_valid),
            .start_flag_in  (start_flags_in[i]),
            .start_flag_out (start_flags_out[i]),
            .out_addr       (cell_out_addr[i]),
            .out_data       (cell_out_data[i]),
            .out_valid      (cell_out_valid[i])
        );
    end
endgenerate

// ── Wired-OR output arbitration ───────────────────────────────────────────────
integer j;
always @(*) begin
    out_addr  = 32'h0;
    out_data  = 32'h0;
    out_valid = 1'b0;
    for (j = 0; j < NUM_CELLS; j = j + 1) begin
        if (cell_out_valid[j]) begin
            out_addr  = out_addr  | cell_out_addr[j];
            out_data  = out_data  | cell_out_data[j];
            out_valid = 1'b1;
        end
    end
end

// ── Status ────────────────────────────────────────────────────────────────────
assign start_flags_out = {NUM_CELLS{1'b0}};  // echo via cell ports above

reg [15:0] armed = 16'h0;
always @(posedge clk) begin
    if (rst) armed <= 16'h0;
    else begin
        armed = 16'h0;
        for (j = 0; j < NUM_CELLS; j = j + 1)
            if (start_flags_in[j]) armed = armed + 1;
    end
end
assign armed_count = armed;

reg [31:0] cycles = 32'h0;
always @(posedge clk) begin
    if (rst) cycles <= 32'h0;
    else cycles <= cycles + 1;
end
assign cycle_count = cycles;

endmodule
