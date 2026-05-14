// unicell_array_v3.v — Parameterised array of unicell_v3 cells
// Matches CELL_INTERNALS.md spec (2026-05-14)
//
// Each cell has CELL_ID = BASE_ID + index.
// The cmd_bus and data bus are shared across all cells.
// Outputs are wired-OR — only one cell should fire per address per cycle.
// armed_count and cycle_count provided for host status queries.

`timescale 1ns / 1ps

module unicell_array_v3 #(
    parameter NUM_CELLS  = 8,
    parameter BASE_ID    = 0
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze,

    // Command bus (Bus 1)
    input  wire [31:0] cmd_bus,
    input  wire        cmd_valid,

    // Data bus (Bus 2/3)
    input  wire [31:0] bus_addr,
    input  wire [31:0] bus_data,
    input  wire        bus_valid,

    // Wired-OR output
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    // Status
    output reg  [15:0] armed_count,
    output reg  [31:0] cycle_count
);

// ── Per-cell output wires ──────────────────────────────────────────────────────
wire [31:0] cell_out_addr [0:NUM_CELLS-1];
wire [31:0] cell_out_data [0:NUM_CELLS-1];
wire        cell_out_valid[0:NUM_CELLS-1];
wire [31:0] cell_cmd_latch[0:NUM_CELLS-1];

// ── Generate cell array ────────────────────────────────────────────────────────
genvar i;
generate
    for (i = 0; i < NUM_CELLS; i = i + 1) begin : cells
        unicell_v3 #(
            .CELL_ID(BASE_ID + i)
        ) cell (
            .clk            (clk),
            .rst            (rst),
            .freeze         (freeze),
            .cmd_bus        (cmd_bus),
            .cmd_valid      (cmd_valid),
            .bus_addr       (bus_addr),
            .bus_data       (bus_data),
            .bus_valid      (bus_valid),
            .out_addr       (cell_out_addr [i]),
            .out_data       (cell_out_data [i]),
            .out_valid      (cell_out_valid[i]),
            .dbg_cmd_latch  (cell_cmd_latch[i]),
            .dbg_input_addr (),
            .dbg_output_addr(),
            .dbg_frozen     (),
            .dbg_trace      (),
            .dbg_breakpoint (),
            .dbg_priority   ()
        );
    end
endgenerate

// ── Wired-OR output ────────────────────────────────────────────────────────────
// Priority: lowest cell index wins if two fire on same cycle (shouldn't happen
// in correct programs but prevents metastability on wired-OR)
integer j;
always @(*) begin
    out_addr  = 32'h0;
    out_data  = 32'h0;
    out_valid = 1'b0;
    for (j = NUM_CELLS-1; j >= 0; j = j - 1) begin
        if (cell_out_valid[j]) begin
            out_addr  = cell_out_addr[j];
            out_data  = cell_out_data[j];
            out_valid = 1'b1;
        end
    end
end

// ── Armed count ────────────────────────────────────────────────────────────────
// Count cells with start_flag (cmd_latch bit 22) set
integer k;
always @(posedge clk) begin
    armed_count = 0;
    for (k = 0; k < NUM_CELLS; k = k + 1) begin
        if (cell_cmd_latch[k][22])
            armed_count = armed_count + 1;
    end
end

// ── Cycle counter ──────────────────────────────────────────────────────────────
always @(posedge clk) begin
    if (rst)
        cycle_count <= 32'h0;
    else
        cycle_count <= cycle_count + 1;
end

endmodule
