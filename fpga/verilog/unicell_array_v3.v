// unicell_array_v3.v -- Parameterised array of unicell_v3 cells
// 2026-05-14 -- with output delivery FIFO for simultaneous fires

`timescale 1ns / 1ps

module unicell_array_v3 #(
    parameter NUM_CELLS  = 8,
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
    output reg  [31:0] cycle_count
);

// -- Per-cell wires ------------------------------------------------------------
wire [31:0] cell_out_addr [0:NUM_CELLS-1];
wire [31:0] cell_out_data [0:NUM_CELLS-1];
wire        cell_out_valid[0:NUM_CELLS-1];
wire [31:0] cell_cmd_latch[0:NUM_CELLS-1];

// -- Internal bus -------------------------------------------------------------
// Cells see ibus_* which is either host input or feedback from fired cells.
reg  [31:0] ibus_cmd   = 32'h0;
reg         ibus_cmd_v = 1'b0;
reg  [31:0] ibus_addr  = 32'h0;
reg  [31:0] ibus_data  = 32'h0;
reg         ibus_valid = 1'b0;

// -- Output FIFO (depth 4) ----------------------------------------------------
// Collects all cells that fired this cycle, delivers one per cycle.
// Depth 4 handles up to 4 simultaneous fires (sufficient for 8-cell array).
reg  [31:0] fifo_addr [0:3];
reg  [31:0] fifo_data [0:3];
reg  [2:0]  fifo_wr   = 3'h0;   // write pointer (next slot to write)
reg  [2:0]  fifo_rd   = 3'h0;   // read pointer (next slot to deliver)
wire        fifo_empty = (fifo_wr == fifo_rd);
wire        fifo_full  = (fifo_wr[1:0] == fifo_rd[1:0]) && (fifo_wr[2] != fifo_rd[2]);

// Fill FIFO from cell outputs each cycle
// Each cell that fired gets one slot
integer fi;
always @(posedge clk) begin : fifo_fill
    integer fw;
    fw = fifo_wr;
    if (rst) begin
        fifo_wr <= 3'h0;
    end else begin
        // Collect all cells that fired this cycle into FIFO
        for (fi = 0; fi < NUM_CELLS; fi = fi + 1) begin
            if (cell_out_valid[fi] && !fifo_full) begin
                fifo_addr[fw[1:0]] <= cell_out_addr[fi];
                fifo_data[fw[1:0]] <= cell_out_data[fi];
                fw = fw + 1;
            end
        end
        fifo_wr <= fw[2:0];
        // Reset FIFO on host packet (avoids stale feedback after config)
        if (bus_valid)
            fifo_wr <= fifo_rd;  // drain
    end
end

// -- Bus mux + feedback delivery ----------------------------------------------
// Each cycle: deliver one FIFO entry as feedback, or pass host input.
// Host input takes priority and drains the FIFO.
always @(posedge clk) begin
    if (rst) begin
        ibus_cmd   <= 32'h0;
        ibus_cmd_v <= 1'b0;
        ibus_addr  <= 32'h0;
        ibus_data  <= 32'h0;
        ibus_valid <= 1'b0;
        fifo_rd    <= 3'h0;
    end else if (bus_valid) begin
        // Host packet takes priority
        ibus_cmd   <= cmd_bus;
        ibus_cmd_v <= cmd_valid;
        ibus_addr  <= bus_addr;
        ibus_data  <= bus_data;
        ibus_valid <= 1'b1;
        fifo_rd    <= fifo_rd;  // don't advance -- FIFO drains via fifo_wr reset
    end else if (!fifo_empty) begin
        // Deliver next FIFO entry as feedback
        ibus_cmd   <= 32'h00008001;  // CMD_DATA_WRITE | raw_addr
        ibus_cmd_v <= 1'b1;
        ibus_addr  <= fifo_addr[fifo_rd[1:0]];
        ibus_data  <= fifo_data[fifo_rd[1:0]];
        ibus_valid <= 1'b1;
        fifo_rd    <= fifo_rd + 1;
    end else begin
        ibus_cmd_v <= 1'b0;
        ibus_valid <= 1'b0;
    end
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
// Any cell firing this cycle goes to host (wired-OR for simultaneous)
integer j;
always @(posedge clk) begin
    out_addr  <= 32'h0;
    out_data  <= 32'h0;
    out_valid <= 1'b0;
    for (j = 0; j < NUM_CELLS; j = j + 1) begin
        if (cell_out_valid[j]) begin
            out_addr  <= cell_out_addr[j];
            out_data  <= cell_out_data[j];
            out_valid <= 1'b1;
        end
    end
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
