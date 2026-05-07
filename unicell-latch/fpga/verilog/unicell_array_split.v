// unicell_array_split.v — Array wrapper for unicell_latch_split
// Claudette v2.1 / unicell-latch-split variant

`timescale 1ns / 1ps
`default_nettype none

module unicell_array_split #(
    parameter NUM_CELLS    = 8,
    parameter BASE_ADDRESS = 0
) (
    input  wire        clk,
    input  wire        clk_2x,
    input  wire        rst,
    input  wire        freeze,

    input  wire [31:0] cpu_addr,
    input  wire [31:0] cpu_data,
    input  wire        cpu_valid,

    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    output wire [15:0] armed_count,
    output wire [31:0] cycle_count
);

// ── Registered bus ────────────────────────────────────────────────────────────
reg [31:0] bus_addr  = 32'h0;
reg [31:0] bus_data  = 32'h0;
reg        bus_valid = 1'b0;

// ── Cell output wires ─────────────────────────────────────────────────────────
wire [31:0] cell_out_addr  [0:NUM_CELLS-1];
wire [31:0] cell_out_data  [0:NUM_CELLS-1];
wire        cell_out_valid [0:NUM_CELLS-1];
wire        cell_dbg_armed [0:NUM_CELLS-1];

// ── Cell instantiation ────────────────────────────────────────────────────────
genvar c;
generate
    for (c = 0; c < NUM_CELLS; c = c + 1) begin : cell_array
        unicell_latch_split #(
            .CELL_ID        (c),
            .CONFIG_ADDRESS (BASE_ADDRESS + c)
        ) cell (
            .clk        (clk),
            .clk_2x     (clk_2x),
            .rst        (rst),
            .freeze     (freeze),
            .bus_addr   (bus_addr),
            .bus_data   (bus_data),
            .bus_valid  (bus_valid),
            .start_flag (1'b0),        // cells self-arm via armed_reg
            .out_addr   (cell_out_addr[c]),
            .out_data   (cell_out_data[c]),
            .out_valid  (cell_out_valid[c]),
            .dbg_armed  (cell_dbg_armed[c])
        );
    end
endgenerate

// ── Bus arbitration ───────────────────────────────────────────────────────────
wire        or_valid;
wire [31:0] or_addr, or_data;

assign or_valid = |{cell_out_valid[NUM_CELLS-1:0]};

integer i;
reg [31:0] or_addr_r, or_data_r;
always @(*) begin
    or_addr_r = 32'h0;
    or_data_r = 32'h0;
    for (i = 0; i < NUM_CELLS; i = i + 1) begin
        if (cell_out_valid[i]) begin
            or_addr_r = or_addr_r | cell_out_addr[i];
            or_data_r = or_data_r | cell_out_data[i];
        end
    end
end
assign or_addr = or_addr_r;
assign or_data = or_data_r;

// ── Bus + output registers ────────────────────────────────────────────────────
always @(posedge clk) begin
    if (rst) begin
        bus_addr  <= 32'h0;
        bus_data  <= 32'h0;
        bus_valid <= 1'b0;
        out_valid <= 1'b0;
        out_addr  <= 32'h0;
        out_data  <= 32'h0;
    end else if (!freeze) begin
        out_valid <= 1'b0;
        if (cpu_valid) begin
            bus_addr  <= cpu_addr;
            bus_data  <= cpu_data;
            bus_valid <= 1'b1;
        end else if (or_valid) begin
            bus_addr  <= or_addr;
            bus_data  <= or_data;
            bus_valid <= 1'b1;
            out_addr  <= or_addr;
            out_data  <= or_data;
            out_valid <= 1'b1;
        end else begin
            bus_valid <= 1'b0;
        end
    end
end

// ── Status ────────────────────────────────────────────────────────────────────
reg [15:0] armed = 16'h0;
always @(posedge clk) begin
    if (rst) armed <= 16'h0;
    else begin : armed_count_block
        integer j;
        armed = 16'h0;
        for (j = 0; j < NUM_CELLS; j = j + 1)
            if (cell_dbg_armed[j]) armed = armed + 1;
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
