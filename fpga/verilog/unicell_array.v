// unicell_array.v — Imago UniCell Array
// Claudette v1.1
//
// A configurable array of UniCells sharing a common bus.
// The wired-OR bus property is implemented in software here —
// on silicon this would be a physical wired-OR connection.
//
// Parameters:
//   NUM_CELLS — number of cells in the array (default 64)
//               64 cells: fits iCE40UP5K (iCEBreaker)
//               256 cells: fits Artix-7 (Basys 3)
//               1024 cells: fits larger Artix-7 (Arty A7-100)
//
// Bus architecture:
//   One global bus: bus_addr + bus_data + bus_valid
//   Each cell monitors the bus and writes to it when it fires
//   Multiple cells writing the same address in the same cycle
//   produces OR'd result (wired-OR) — this is architecturally correct
//   and is how NAND emerges from two NOT cells sharing an output address
//
// CPU interface:
//   The host CPU (or Python workbench via UART/USB) drives the bus
//   for configuration and input injection.
//   Cell outputs are captured and forwarded to the host.

`timescale 1ns / 1ps

module unicell_array #(
    parameter NUM_CELLS = 64       // Number of cells in the array
) (
    input  wire        clk,
    input  wire        rst,

    // CPU/host interface — drives the bus
    input  wire [31:0] cpu_addr,   // Address from host
    input  wire [31:0] cpu_data,   // Data from host
    input  wire        cpu_valid,  // Host is driving the bus this cycle
    input  wire        cpu_inject, // Host injecting directly (bypasses cell output)

    // Output to host — aggregated cell outputs
    output reg  [31:0] out_addr,   // Address of most recent cell output
    output reg  [31:0] out_data,   // Data of most recent cell output
    output reg         out_valid,  // A cell fired this cycle

    // Status
    output wire [15:0] armed_count, // Number of armed cells
    output wire [31:0] cycle_count  // Total cycles executed
);

// ── Internal bus ──────────────────────────────────────────────────────────────
reg  [31:0] bus_addr;
reg  [31:0] bus_data;
reg         bus_valid;

// ── Cell outputs ──────────────────────────────────────────────────────────────
wire [31:0] cell_out_addr [0:NUM_CELLS-1];
wire [31:0] cell_out_data [0:NUM_CELLS-1];
wire        cell_out_valid [0:NUM_CELLS-1];
wire        cell_armed [0:NUM_CELLS-1];

// ── Cycle counter ─────────────────────────────────────────────────────────────
reg [31:0] cycles;
assign cycle_count = cycles;

// ── Armed cell counter ────────────────────────────────────────────────────────
reg [15:0] armed;
assign armed_count = armed;

integer i;
always @(*) begin
    armed = 0;
    for (i = 0; i < NUM_CELLS; i = i + 1)
        if (cell_armed[i]) armed = armed + 1;
end

// ── Instantiate cells ─────────────────────────────────────────────────────────
genvar c;
generate
    for (c = 0; c < NUM_CELLS; c = c + 1) begin : cell_array
        unicell #(
            .CELL_ID(c)
        ) cell_inst (
            .clk       (clk),
            .rst       (rst),
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
            .dbg_armed       (cell_armed[c])
        );
    end
endgenerate

// ── Bus arbitration and wired-OR ──────────────────────────────────────────────
// Collect all cell outputs and OR them onto the bus
// This implements the wired-OR property of the UniCell architecture
// Two NOT cells sharing an output address produce NAND via wired-OR

reg [31:0] or_addr;
reg [31:0] or_data;
reg        or_valid;

always @(*) begin
    or_addr  = 32'h0;
    or_data  = 32'h0;
    or_valid = 1'b0;

    for (i = 0; i < NUM_CELLS; i = i + 1) begin
        if (cell_out_valid[i]) begin
            or_addr  = cell_out_addr[i];   // Last writer wins for address
            or_data  = or_data | cell_out_data[i];  // Wired-OR for data
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
        cycles <= cycles + 1;
        out_valid <= 1'b0;

        if (cpu_valid) begin
            // Host is driving the bus this cycle
            bus_addr  <= cpu_addr;
            bus_data  <= cpu_data;
            bus_valid <= 1'b1;
        end else if (or_valid) begin
            // A cell fired — put its output on the bus
            // so other cells can receive it next cycle
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
