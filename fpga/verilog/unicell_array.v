// unicell_array.v — Imago UniCell Array
// v2.0 — command bus architecture
//
// Changes from v1.2:
//   - freeze wire removed — CMD_FREEZE (code 5) on command bus handles it
//   - clk_n removed — odd_phase toggle handles negedge in each cell
//   - CONFIG_ADDRESS parameter removed — cells have no fixed config address
//   - BASE_ADDRESS parameter removed — not needed without CONFIG_ADDRESS
//   - New ports: cmd_bus, cmd_data, cmd_valid broadcast to all cells
//   - cpu_inject removed — host drives bus directly via cpu_valid
//   - dbg_gate_state → dbg_cmd_latch

`timescale 1ns / 1ps

module unicell_array #(
    parameter NUM_CELLS = 32    // 32 for safe iCEBreaker bring-up
) (
    input  wire        clk,
    input  wire        rst,

    // Command bus — broadcast to all cells
    input  wire [31:0] cmd_bus,
    input  wire [31:0] cmd_data,
    input  wire        cmd_valid,

    // CPU/host data bus interface
    input  wire [31:0] cpu_addr,
    input  wire [31:0] cpu_data,
    input  wire        cpu_valid,

    // Output to host
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    // Status
    output wire [15:0] armed_count,
    output wire [31:0] cycle_count
);

// ── Internal bus — registered ─────────────────────────────────────────────────
// bus_addr/bus_data/bus_valid are registered one cycle.
// Chain latency: cell0 fires cycle N → bus updates cycle N+1 → cell1 fires N+2.
// This avoids a combinational loop (cell→OR→bus→cell) which kills timing.
// The one-cycle pipeline is acceptable — all computation is pipelined anyway.
reg  [31:0] bus_addr  = 32'h0;
reg  [31:0] bus_data  = 32'h0;
reg         bus_valid = 1'b0;

// ── Cell outputs ──────────────────────────────────────────────────────────────
wire [31:0] cell_out_addr  [0:NUM_CELLS-1];
wire [31:0] cell_out_data  [0:NUM_CELLS-1];
wire        cell_out_valid [0:NUM_CELLS-1];
wire        cell_armed     [0:NUM_CELLS-1];

// ── Counters ──────────────────────────────────────────────────────────────────
reg [31:0] cycles;
assign cycle_count = cycles;

// armed_count is registered — computed combinationally then clocked.
// Keeps the carry-chain adder off the async output path to the LED IO pad.
reg [15:0] armed_comb;
reg [15:0] armed_reg = 16'h0;
assign armed_count = armed_reg;

integer i;
always @(*) begin
    armed_comb = 0;
    for (i = 0; i < NUM_CELLS; i = i + 1)
        if (cell_armed[i]) armed_comb = armed_comb + 1;
end

always @(posedge clk) begin
    if (rst) armed_reg <= 16'h0;
    else     armed_reg <= armed_comb;
end

// ── Cell instantiation ────────────────────────────────────────────────────────
// cmd_valid is gated per-cell for targeted commands (RECONFIGURE, SET_IN, SET_OUT).
// Target cell ID carried in cmd_bus[26:16] — compared against genvar constant c.
// Yosys folds this to a constant at synthesis time — zero runtime LUT cost.
// Broadcast commands (FREEZE, RELEASE, PING, NOP) use cmd_bus[26:16] = 11'h7FF.
wire [3:0]  cmd_code       = cmd_bus[3:0];
wire [10:0] cmd_target_id  = cmd_bus[26:16];

// Commands that require cell targeting
wire cmd_is_targeted = (cmd_code == 4'd2) ||   // CMD_SET_INPUT_ADDR
                       (cmd_code == 4'd3) ||   // CMD_SET_OUTPUT_ADDR
                       (cmd_code == 4'd4);     // CMD_RECONFIGURE

// Broadcast sentinel: 11'h7FF means "all cells" (used for FREEZE/RELEASE/PING)
wire cmd_is_broadcast = (cmd_target_id == 11'h7FF);

genvar c;
generate
    for (c = 0; c < NUM_CELLS; c = c + 1) begin : cell_array
        // cell_cmd_valid: targeted commands only reach the addressed cell;
        // broadcast commands reach all cells; non-targeted commands broadcast.
        wire cell_cmd_valid = cmd_valid &&
                              (!cmd_is_targeted ||
                               cmd_is_broadcast ||
                               (cmd_target_id == c[10:0]));
        unicell #(
            .CELL_ID         (c),
            .ENABLE_LATCH_IN (0)   // disabled on iCEBreaker — timing constraint
        ) cell_inst (
            .clk        (clk),
            .rst        (rst),
            .cmd_bus    (cmd_bus),
            .cmd_data   (cmd_data),
            .cmd_valid  (cell_cmd_valid),
            .bus_addr   (bus_addr),
            .bus_data   (bus_data),
            .bus_valid  (bus_valid),
            .out_addr   (cell_out_addr[c]),
            .out_data   (cell_out_data[c]),
            .out_valid  (cell_out_valid[c]),
            .dbg_cmd_latch   (),
            .dbg_input_addr  (),
            .dbg_output_addr (),
            .dbg_start_flag  (),
            .dbg_armed       (cell_armed[c]),
            .dbg_frozen      (),
            .dbg_priority    (),
            .dbg_trace       (),
            .dbg_breakpoint  (),
            .dbg_dtype       ()
        );
    end
endgenerate

// ── Wired-OR bus ──────────────────────────────────────────────────────────────
reg [31:0] or_addr;
reg [31:0] or_data;
reg        or_valid;

always @(*) begin
    or_addr  = 32'h0;
    or_data  = 32'h0;
    or_valid = 1'b0;

    for (i = 0; i < NUM_CELLS; i = i + 1) begin
        if (cell_out_valid[i]) begin
            or_addr = cell_out_addr[i];
            or_data = or_data | cell_out_data[i];  // wired-OR
            or_valid = 1'b1;
        end
    end
end

// ── Main clock process ────────────────────────────────────────────────────────
// bus_addr/bus_data/bus_valid register on each posedge.
// cpu_valid takes priority; cell wired-OR output feeds back next cycle.
// Chain: cell0 fires cycle N (odd_phase drain) → bus_valid=1 cycle N+1
//        → cell1 sees it cycle N+1 → fires cycle N+2 (odd_phase drain).
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
        bus_valid <= 1'b0;

        if (cpu_valid && (cmd_bus[3:0] == 4'd1)) begin
            // CMD_DATA only — commands don't go on the data bus
            bus_addr  <= cpu_addr;
            bus_data  <= cpu_data;
            bus_valid <= 1'b1;
        end else if (or_valid) begin
            // Cell output feeds back onto bus next cycle — enables chaining
            bus_addr  <= or_addr;
            bus_data  <= or_data;
            bus_valid <= 1'b1;
            out_addr  <= or_addr;
            out_data  <= or_data;
            out_valid <= 1'b1;
        end
    end
end

endmodule
