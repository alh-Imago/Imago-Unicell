// unicell_array.v — Imago UniCell Array
// Claudette v1.2
//
// A configurable array of UniCells sharing a common wired-OR bus.
//
// Changes from v1.1:
//   - Passes CONFIG_ADDRESS = c (cell index) to each cell — fixed config
//     address separate from runtime input_address. Prevents address-zero
//     collisions and accidental config intercepts between cells.
//   - Passes clk_n (inverted clock) for GS_FALL_EDGE cells
//   - Passes freeze line — global freeze for pond migration / snapshot
//   - dbg_frozen connected per cell
//
// Parameters:
//   NUM_CELLS — number of cells (default 32 for safe iCEBreaker bring-up)
//               32 cells:   comfortable on iCE40UP5K (~50% utilisation)
//               64 cells:   fits at ~97% — tight but valid
//               256 cells:  fits Artix-7 (Basys 3)
//               1024 cells: fits larger Artix-7 (Arty A7-100)
//
// Bus architecture:
//   One shared bus: bus_addr + bus_data + bus_valid
//   Each cell monitors the bus and writes when it fires
//   Multiple cells writing the same address in the same cycle
//   produce OR'd result (wired-OR) — architecturally correct.
//   GS_FALL_EDGE cells write on negedge — separating simultaneous
//   writers within the same cycle without pad cells.

`timescale 1ns / 1ps

module unicell_array #(
    parameter NUM_CELLS = 32       // 32 for safe iCEBreaker bring-up
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze,     // Global freeze — all cells decouple simultaneously

    // CPU/host interface
    input  wire [31:0] cpu_addr,
    input  wire [31:0] cpu_data,
    input  wire        cpu_valid,
    input  wire        cpu_inject,

    // Output to host
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    // Status
    output wire [15:0] armed_count,
    output wire [31:0] cycle_count
);

// ── Inverted clock for GS_FALL_EDGE cells ─────────────────────────────────────
wire clk_n = ~clk;

// ── Internal bus ──────────────────────────────────────────────────────────────
reg  [31:0] bus_addr;
reg  [31:0] bus_data;
reg         bus_valid;

// ── Cell outputs ──────────────────────────────────────────────────────────────
wire [31:0] cell_out_addr  [0:NUM_CELLS-1];
wire [31:0] cell_out_data  [0:NUM_CELLS-1];
wire        cell_out_valid [0:NUM_CELLS-1];
wire        cell_armed     [0:NUM_CELLS-1];
wire        cell_frozen    [0:NUM_CELLS-1];

// ── Counters ──────────────────────────────────────────────────────────────────
reg [31:0] cycles;
assign cycle_count = cycles;

reg [15:0] armed;
assign armed_count = armed;

integer i;
always @(*) begin
    armed = 0;
    for (i = 0; i < NUM_CELLS; i = i + 1)
        if (cell_armed[i]) armed = armed + 1;
end

// ── Cell instantiation ────────────────────────────────────────────────────────
// Each cell receives:
//   CELL_ID        = c  (for debug)
//   CONFIG_ADDRESS = c  (fixed synthesis-time config address)
// The CONFIG_ADDRESS is permanently bound at synthesis — it is NOT the same
// as the runtime input_address register inside the cell.
genvar c;
generate
    for (c = 0; c < NUM_CELLS; c = c + 1) begin : cell_array
        unicell #(
            .CELL_ID        (c),
            .CONFIG_ADDRESS (BASE_ADDRESS + c)  // base + index, matches fpga_bridge.py
        ) cell_inst (
            .clk       (clk),
            .clk_n     (clk_n),    // Falling edge for GS_FALL_EDGE
            .rst       (rst),
            .freeze    (freeze),   // Global freeze line
            .bus_addr  (bus_addr),
            .bus_data  (bus_data),
            .bus_valid (bus_valid),
            .out_addr  (cell_out_addr[c]),
            .out_data  (cell_out_data[c]),
            .out_valid (cell_out_valid[c]),
            .dbg_gate_state  (),
            .dbg_input_addr  (),
            .dbg_output_addr (),
            .dbg_start_flag  (),
            .dbg_armed       (cell_armed[c]),
            .dbg_frozen      (cell_frozen[c])
        );
    end
endgenerate

// ── Wired-OR bus ──────────────────────────────────────────────────────────────
// Collects all cell outputs and ORs data onto the bus.
// Two NOT cells sharing an output address produce NAND via wired-OR.
// GS_FALL_EDGE cells contribute their output at negedge — captured here
// in the combinational always block and forwarded next posedge.

reg [31:0] or_addr;
reg [31:0] or_data;
reg        or_valid;

always @(*) begin
    or_addr  = 32'h0;
    or_data  = 32'h0;
    or_valid = 1'b0;

    for (i = 0; i < NUM_CELLS; i = i + 1) begin
        if (cell_out_valid[i]) begin
            or_addr = cell_out_addr[i];          // Last writer wins for address
            or_data = or_data | cell_out_data[i]; // Wired-OR for data
            or_valid = 1'b1;
        end
    end
end

// ── Main clock process ────────────────────────────────────────────────────────
always @(posedge clk) begin
    if (rst) begin
        bus_addr  <= 32'h0;
        bus_data  <= 32'h0;
        bus_valid <= 1'b0;
        out_valid <= 1'b0;
        out_addr  <= 32'h0;
        out_data  <= 32'h0;
        cycles    <= 32'h0;
    end else begin
        cycles    <= cycles + 1;
        out_valid <= 1'b0;

        if (cpu_valid) begin
            // Host driving the bus this cycle
            bus_addr  <= cpu_addr;
            bus_data  <= cpu_data;
            bus_valid <= 1'b1;
        end else if (or_valid) begin
            // Cell fired — put output on bus for downstream cells next cycle
            bus_addr  <= or_addr;
            bus_data  <= or_data;
            bus_valid <= 1'b1;
            // Forward to host
            out_addr  <= or_addr;
            out_data  <= or_data;
            out_valid <= 1'b1;
        end else begin
            bus_valid <= 1'b0;
        end
    end
end

endmodule
