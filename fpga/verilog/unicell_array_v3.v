// unicell_array_v3.v - Parameterised array of unicell_v3 cells
// Matches CELL_INTERNALS.md spec (2026-05-14)
//
// Key feature: cell output feedback loop.
// When a cell fires, its output re-enters the bus on the next cycle
// so downstream cells (SYNC_WAIT etc.) can receive it.
// Host input takes priority over cell feedback.

`timescale 1ns / 1ps

module unicell_array_v3 #(
    parameter NUM_CELLS  = 8,
    parameter BASE_ID    = 0
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze,

    // Command bus (Bus 1) - from host
    input  wire [31:0] cmd_bus,
    input  wire        cmd_valid,

    // Data bus (Bus 2/3) - from host
    input  wire [31:0] bus_addr,
    input  wire [31:0] bus_data,
    input  wire        bus_valid,

    // Output to host (wired-OR)
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    // Status
    output reg  [15:0] armed_count,
    output reg  [31:0] cycle_count
);

// -- Per-cell wires -------------------------------------------------------------
wire [31:0] cell_out_addr [0:NUM_CELLS-1];
wire [31:0] cell_out_data [0:NUM_CELLS-1];
wire        cell_out_valid[0:NUM_CELLS-1];
wire [31:0] cell_cmd_latch[0:NUM_CELLS-1];

// -- Internal bus registers -----------------------------------------------------
// Cells see the registered bus - either host input or cell feedback.
reg  [31:0] ibus_cmd   = 32'h0;
reg         ibus_cmd_v = 1'b0;
reg  [31:0] ibus_addr  = 32'h0;
reg  [31:0] ibus_data  = 32'h0;
reg         ibus_valid = 1'b0;
reg  [31:0] pend_addr  = 32'h0;
reg  [31:0] pend_data  = 32'h0;
reg         pend_valid = 1'b0;
reg  [31:0] prev_or_addr  = 32'h0;
reg  [31:0] prev_or_data  = 32'h0;
reg         prev_or_valid = 1'b0;
integer     j, k;
genvar      gi;

// -- Wired-OR of cell outputs (combinatorial) -----------------------------------
reg  [31:0] or_addr;
reg  [31:0] or_data;
reg         or_valid;

always @(*) begin
    or_addr  = 32'h0;
    or_data  = 32'h0;
    or_valid = 1'b0;
    for (j = NUM_CELLS-1; j >= 0; j = j - 1) begin
        if (cell_out_valid[j]) begin
            or_addr  = cell_out_addr[j];
            or_data  = cell_out_data[j];
            or_valid = 1'b1;
        end
    end
end

// -- Bus mux + feedback register -----------------------------------------------
// Priority: host > pending second output > new cell output.
// Pending register handles simultaneous cell fires (e.g. two NOTs
// both writing to the same SYNC_WAIT input address on the same cycle).
always @(posedge clk) begin
    if (rst) begin
        ibus_cmd   <= 32'h0;
        ibus_cmd_v <= 1'b0;
        ibus_addr  <= 32'h0;
        ibus_data  <= 32'h0;
        ibus_valid <= 1'b0;
        pend_addr  <= 32'h0;
        pend_data  <= 32'h0;
        pend_valid <= 1'b0;
        prev_or_addr  <= 32'h0;
        prev_or_data  <= 32'h0;
        prev_or_valid <= 1'b0;
    end else begin
        // Detect second simultaneous fire: or_valid this cycle AND last cycle
        // were different addresses -- save the previous one as pending
        if (or_valid && prev_or_valid && (or_addr != prev_or_addr)) begin
            pend_addr  <= prev_or_addr;
            pend_data  <= prev_or_data;
            pend_valid <= 1'b1;
        end else if (ibus_valid && (ibus_addr == pend_addr)) begin
            // Pending was just delivered -- clear it
            pend_valid <= 1'b0;
        end
        prev_or_addr  <= or_addr;
        prev_or_data  <= or_data;
        prev_or_valid <= or_valid;

        if (bus_valid) begin
            // Host packet takes priority
            ibus_cmd   <= cmd_bus;
            ibus_cmd_v <= cmd_valid;
            ibus_addr  <= bus_addr;
            ibus_data  <= bus_data;
            ibus_valid <= 1'b1;
            pend_valid <= 1'b0;  // host resets pending
        end else if (pend_valid) begin
            // Deliver pending second output
            ibus_cmd   <= 32'h00008001;
            ibus_cmd_v <= 1'b1;
            ibus_addr  <= pend_addr;
            ibus_data  <= pend_data;
            ibus_valid <= 1'b1;
            pend_valid <= 1'b0;
        end else if (or_valid) begin
            // Normal single cell output feedback
            ibus_cmd   <= 32'h00008001;
            ibus_cmd_v <= 1'b1;
            ibus_addr  <= or_addr;
            ibus_data  <= or_data;
            ibus_valid <= 1'b1;
        end else begin
            ibus_cmd_v <= 1'b0;
            ibus_valid <= 1'b0;
        end
    end
end

// -- Cell array -----------------------------------------------------------------
generate
    for (gi = 0; gi < NUM_CELLS; gi = gi + 1) begin : cells
        unicell_v3 #(
            .CELL_ID(BASE_ID + gi)
        ) ucell (
            .clk            (clk),
            .rst            (rst),
            .freeze         (freeze),
            .cmd_bus        (ibus_cmd),
            .cmd_valid      (ibus_cmd_v),
            .bus_addr       (ibus_addr),
            .bus_data       (ibus_data),
            .bus_valid      (ibus_valid),
            .out_addr       (cell_out_addr [gi]),
            .out_data       (cell_out_data [gi]),
            .out_valid      (cell_out_valid[gi]),
            .dbg_cmd_latch  (cell_cmd_latch[gi]),
            .dbg_input_addr (),
            .dbg_output_addr(),
            .dbg_frozen     (),
            .dbg_trace      (),
            .dbg_breakpoint (),
            .dbg_priority   ()
        );
    end
endgenerate

// -- Output to host -------------------------------------------------------------
always @(posedge clk) begin
    out_addr  <= or_addr;
    out_data  <= or_data;
    out_valid <= or_valid;
end

// -- Armed count ----------------------------------------------------------------
always @(posedge clk) begin : armed_blk
    integer cnt;
    cnt = 0;
    for (k = 0; k < NUM_CELLS; k = k + 1)
        if (cell_cmd_latch[k][22]) cnt = cnt + 1;
    armed_count <= cnt[15:0];
end

// -- Cycle counter --------------------------------------------------------------
always @(posedge clk) begin
    if (rst) cycle_count <= 32'h0;
    else     cycle_count <= cycle_count + 1;
end

endmodule
