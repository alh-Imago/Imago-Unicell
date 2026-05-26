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
    input  wire  [7:0] cmd_bus,
    input  wire [31:0] cmd_data,
    input  wire        cmd_valid,

    // CPU/host data bus interface
    input  wire [15:0] cpu_addr,
    input  wire [31:0] cpu_data,
    input  wire        cpu_valid,

    // Output to host
    output reg  [15:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    // Status
    output wire [15:0] armed_count,
    output wire [31:0] cycle_count
);

// ── Internal bus — registered ─────────────────────────────────────────────────
// bus_addr/bus_data/bus_valid are registered one cycle.
// Two arrivals always required — NOR(A,B) model.
// NOT(A) = NOR(A,A): send same value twice to same address.
reg  [15:0] bus_addr  = 16'h0;
reg  [31:0] bus_data  = 32'h0;
reg         bus_valid = 1'b0;

// ── Cell outputs ──────────────────────────────────────────────────────────────
wire [15:0] cell_out_addr  [0:NUM_CELLS-1];
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
// Boot-state targeting: during boot, physical CELL_ID == cpu_addr routes
// targeted commands (RECONFIGURE, SET_IN, SET_OUT) to the right cell.
// After boot the cell operates on logical addresses only — physical ID suppressed.
// Broadcast commands (FREEZE, RELEASE, PING, NOP) always reach all cells.
//
// cmd_bus is now 8-bit opcode only — target address carried on data bus during boot.
wire [7:0] cmd_code = cmd_bus;

// Commands that require cell targeting via cpu_addr
// Boot opcodes (2,3,4,14) match physical CELL_ID
// Runtime opcodes (5,6,10-21,48-69) match logical input_address
wire cmd_is_boot_targeted = (cmd_code == 8'd2)  ||  // CMD_SET_INPUT_ADDR
                            (cmd_code == 8'd3)  ||  // CMD_SET_OUTPUT_ADDR
                            (cmd_code == 8'd4)  ||  // CMD_RECONFIGURE
                            (cmd_code == 8'd14);    // CMD_SET_LOGICAL

wire cmd_is_runtime_targeted = (cmd_code == 8'd5)  ||  // CMD_FREEZE
                               (cmd_code == 8'd6)  ||  // CMD_RELEASE
                               (cmd_code == 8'd10) ||  // CMD_LATCH_IN_ON
                               (cmd_code == 8'd11) ||  // CMD_LATCH_IN_OFF
                               (cmd_code == 8'd12) ||  // CMD_MEM_CALL
                               (cmd_code == 8'd13) ||  // CMD_REARM
                               (cmd_code >= 8'd16 && cmd_code <= 8'd21) || // state ctrl
                               (cmd_code >= 8'd48 && cmd_code <= 8'd69);   // topo presets

wire cmd_is_targeted = cmd_is_boot_targeted || cmd_is_runtime_targeted;

genvar c;
generate
    for (c = 0; c < NUM_CELLS; c = c + 1) begin : cell_array
        // Boot targeting: targeted commands only reach cell whose physical ID
        // matches cpu_addr. Broadcast commands reach all cells.
        // Boot targeted: match physical CELL_ID
        // Runtime targeted: match logical input_address via dedicated port
        wire [15:0] cell_input_addr;
        wire cmd_is_this_cell_boot    = (cpu_addr[15:0] == c[15:0]);
        wire cmd_is_this_cell_runtime = (cpu_addr[15:0] == cell_input_addr);
        wire cmd_is_this_cell = cmd_is_boot_targeted    ? cmd_is_this_cell_boot
                              : cmd_is_runtime_targeted ? cmd_is_this_cell_runtime
                              : 1'b1;  // untargeted — broadcast
        wire cell_cmd_valid = cmd_valid &&
                              (!cmd_is_targeted || cmd_is_this_cell);
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
            .dbg_cmd_latch        (),
            .dbg_input_addr       (),
            .dbg_input_addr_short (cell_input_addr),
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
reg [15:0] or_addr;
reg [31:0] or_data;
reg        or_valid;

always @(*) begin
    or_addr  = 16'h0;
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
        bus_addr  <= 16'h0;
        bus_data  <= 32'h0;
        bus_valid <= 1'b0;
        out_valid <= 1'b0;
        out_addr  <= 16'h0;
        out_data  <= 32'h0;
        cycles    <= 32'h0;
    end else begin
        cycles    <= cycles + 1;
        bus_valid <= 1'b0;

        out_valid <= 1'b0;

        if (cpu_valid) begin
            // All host packets update bus registers — keeps bus consistent
            // bus_valid=1 only for DATA_WRITE (opcode 1), not commands
            bus_addr  <= cpu_addr[15:0];
            bus_data  <= cpu_data;
            bus_valid <= (cmd_bus == 8'd1) ? 1'b1 : 1'b0;
        end else if (or_valid) begin
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
