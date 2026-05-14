// unicell_array_v3.v -- Parameterised array of unicell_v3 cells
// 2026-05-14 -- simple single-register feedback (no FIFO needed)
// Works correctly when cells fire to different addresses each cycle,
// which is the case for chained cells and SYNC_WAIT on different cycles.

`timescale 1ns / 1ps

module unicell_array_v3 #(
    parameter NUM_CELLS  = 6,
    parameter BASE_ID    = 0
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze,

    input  wire [31:0] cmd_bus,
    input  wire        cmd_valid,
    input  wire [31:0] bus_addr,
    input  wire [31:0] bus_data,
    input  wire        bus_valid,

    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    output reg  [15:0] armed_count,
    output reg  [31:0] cycle_count,

    // Raw bus tap -- every internal bus transaction
    output reg  [31:0] tap_addr,
    output reg  [31:0] tap_data,
    output reg         tap_valid
);

// -- Per-cell wires ------------------------------------------------------------
wire [31:0] cell_out_addr [0:NUM_CELLS-1];
wire [31:0] cell_out_data [0:NUM_CELLS-1];
wire        cell_out_valid[0:NUM_CELLS-1];
wire [31:0] cell_cmd_latch[0:NUM_CELLS-1];

// -- Wired-OR of cell outputs (combinatorial) ---------------------------------
reg  [31:0] or_addr;
reg  [31:0] or_data;
reg         or_valid;
integer     j;

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

// -- Internal bus registers ---------------------------------------------------
// Host input takes priority over cell feedback.
// Cell outputs re-enter the bus on the next cycle so downstream
// cells receive values from upstream cells (chain propagation).
reg  [31:0] ibus_cmd   = 32'h0;
reg         ibus_cmd_v = 1'b0;
reg  [31:0] ibus_addr  = 32'h0;
reg  [31:0] ibus_data  = 32'h0;
reg         ibus_valid = 1'b0;

always @(posedge clk) begin
    if (rst) begin
        ibus_cmd   <= 32'h0;
        ibus_cmd_v <= 1'b0;
        ibus_addr  <= 32'h0;
        ibus_data  <= 32'h0;
        ibus_valid <= 1'b0;
    end else if (bus_valid) begin
        // Host packet
        ibus_cmd   <= cmd_bus;
        ibus_cmd_v <= cmd_valid;
        ibus_addr  <= bus_addr;
        ibus_data  <= bus_data;
        ibus_valid <= 1'b1;
    end else if (or_valid) begin
        // Cell output feedback -- CMD_DATA_WRITE | raw_addr
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

// -- Raw bus tap --------------------------------------------------------------
// Only captures cell output feedback (or_valid), NOT host input packets.
// Host packets are already known to the host -- only cell-to-cell traffic
// is new information. This prevents host packets clogging the UART queue.
always @(posedge clk) begin
    tap_addr  <= or_addr;
    tap_data  <= or_data;
    tap_valid <= or_valid;
end

// -- Cell array ---------------------------------------------------------------
genvar gi;
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

// -- Output to host -----------------------------------------------------------
always @(posedge clk) begin
    out_addr  <= or_addr;
    out_data  <= or_data;
    out_valid <= or_valid;
end

// -- Armed count --------------------------------------------------------------
integer k;
always @(posedge clk) begin : armed_blk
    integer cnt;
    cnt = 0;
    for (k = 0; k < NUM_CELLS; k = k + 1)
        if (cell_cmd_latch[k][22]) cnt = cnt + 1;
    armed_count <= cnt[15:0];
end

// -- Cycle counter ------------------------------------------------------------
always @(posedge clk) begin
    if (rst) cycle_count <= 32'h0;
    else     cycle_count <= cycle_count + 1;
end

endmodule
