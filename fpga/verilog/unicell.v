// unicell.v — Imago UniCell — Single Cell Implementation
// v2.0 — command latch + command bus architecture
//
// Change from v1 (Claudette v1.2):
//   - Configuration now arrives on a separate command bus (cmd_bus / cmd_valid)
//     rather than via a LOAD_PATTERN sequence on the data bus.
//   - CMD_RECONFIGURE (code 4): loads the 32-bit command latch in one word.
//     No auth check in this baseline — accepted unconditionally.
//   - CMD_SET_INPUT_ADDR (code 2): sets input_address at any time.
//   - CMD_SET_OUTPUT_ADDR (code 3): sets output_address at any time.
//   - CMD_FREEZE (code 5) / CMD_RELEASE (code 6): replace the freeze wire.
//   - freeze wire and clk_n port removed.
//   - CONFIG_ADDRESS parameter removed — cells no longer have a fixed config
//     address; all config arrives via the command bus.
//
// Command latch (32 bits, one word):
//   [9:0]   topology   — NOR gate selection (one-hot, bit 0 = NOT)
//   [10]    sync_wait  — wait for two sequential inputs before firing
//   [21:11] auth_mask  — (stored, not checked in this baseline)
//   [22]    start_flag — 1 = armed
//   [24:23] dtype      — 00=NUMERIC 01=SIGNED 10=ALPHA 11=DATETIME
//   [26:25] ctype      — 00=STANDARD 01=LATCH 10=POSEDGE 11=NEGEDGE
//   [27]    priority   — (stored, transparent in this baseline)
//   [28]    trace      — (stored, transparent in this baseline)
//   [29]    breakpoint — (stored, transparent in this baseline)
//   [31:30] reserved
//
// Command bus codes (bits [3:0]):
//   0 = CMD_NOP
//   2 = CMD_SET_INPUT_ADDR   — bus_data → input_address
//   3 = CMD_SET_OUTPUT_ADDR  — bus_data → output_address
//   4 = CMD_RECONFIGURE      — bus_data → cmd_latch, arms cell
//   5 = CMD_FREEZE           — disarm, suppress output
//   6 = CMD_RELEASE          — re-arm
//   9 = CMD_PING             — (accepted, no response in this baseline)
//
// Data path: unchanged from v1.
//   bus_data[0] → NOR tree (topology[9:0]) → computed_output → out_data[0]
//   odd_phase toggle emulates negedge drain on single-edge iCE40 fabric.
//
// Silicon status (May 2026, iCEBreaker v1.0e, 24 MHz):
//   v1 validated. v2 command latch baseline — pending frequency check.
//
// Timing notes: see docs/VERILOG_SPEC.md

`timescale 1ns / 1ps

module unicell #(
    parameter CELL_ID        = 0,   // Unique cell identifier for debug only
    parameter ENABLE_LATCH_IN = 0   // 0 = disable latch_in feature (saves LCs + timing)
                                    // 1 = enable  latch_in (needed for Kintex-7 workloads)
) (
    input  wire        clk,         // System clock (rising edge)
    input  wire        rst,         // Synchronous reset (active high)

    // Command bus (configuration + control)
    input  wire [31:0] cmd_bus,     // Command word
    input  wire [31:0] cmd_data,    // Payload (address or config word)
    input  wire        cmd_valid,   // Command valid this cycle

    // Shared data bus interface
    input  wire [31:0] bus_addr,    // Current bus address
    input  wire [31:0] bus_data,    // Current bus data
    input  wire        bus_valid,   // Bus transaction valid this cycle
    input  wire        bus_from_cell, // 1=cell origin (single arrival fires), 0=host

    // Output to bus (wired-OR with other cells)
    output reg  [31:0] out_addr,    // Address this cell is writing to
    output reg  [31:0] out_data,    // Data this cell is writing
    output reg         out_valid,   // This cell has output this cycle

    // Debug/observability
    output wire [31:0] dbg_cmd_latch,
    output wire [31:0] dbg_input_addr,
    output wire [31:0] dbg_output_addr,
    output wire        dbg_start_flag,
    output wire        dbg_armed,
    output wire        dbg_frozen,
    output wire        dbg_priority,
    output wire        dbg_trace,
    output wire        dbg_breakpoint,
    output wire [1:0]  dbg_dtype
);

// ── Command codes ──────────────────────────────────────────────────────────────
localparam CMD_NOP              = 4'd0;
localparam CMD_SET_INPUT_ADDR   = 4'd2;
localparam CMD_SET_OUTPUT_ADDR  = 4'd3;
localparam CMD_RECONFIGURE      = 4'd4;
localparam CMD_FREEZE           = 4'd5;
localparam CMD_RELEASE          = 4'd6;
localparam CMD_PING             = 4'd9;

// ── Command latch bit positions ────────────────────────────────────────────────
// [9:0]   topology   (NOR gate selection, one-hot)
// [10]    sync_wait
// [21:11] auth_mask  (stored, not checked in this baseline)
// [22]    start_flag
// [24:23] dtype
// [26:25] ctype
// [27]    priority
// [28]    trace
// [29]    breakpoint
// [31:30] reserved

// Topology constants (cmd_latch[9:0])
localparam TOPO_PASS = 10'b0000000000;  // identity
localparam TOPO_NOT  = 10'b0000000001;  // NOT(input)
localparam TOPO_NOR  = 10'b0000000100;  // NOR(g0,g1) — baseline gate type

// ── Registers ──────────────────────────────────────────────────────────────────
reg [31:0] cmd_latch     = 32'h0;
reg [15:0] input_address  = CELL_ID[15:0];   // narrowed to 16 bits — preset to CELL_ID
reg [15:0] output_address = CELL_ID[15:0] + 1; // preset to CELL_ID+1
reg [31:0] data_reg       = 32'h0;
reg        frozen         = 1'b0;

// Convenience wires into cmd_latch fields
wire [9:0] topology   = cmd_latch[9:0];
wire       sync_wait  = cmd_latch[10];
wire       start_flag = cmd_latch[22];
wire       invert_out = cmd_latch[25];  // invert after gate tree
wire       latch_in   = cmd_latch[26];  // hold input, re-fire on odd_phase
wire       one_shot   = cmd_latch[30];  // fire once then disarm
wire       loop_back  = cmd_latch[31];  // feed output back to data_reg
wire [1:0] dtype      = cmd_latch[24:23]; // NUMERIC/SIGNED/ALPHA/DATETIME
wire       priority   = cmd_latch[27];  // high priority scheduling
wire       trace      = cmd_latch[28];  // log every fire to Ward
wire       breakpoint = cmd_latch[29];  // halt array on fire

reg        out_buf_valid   = 1'b0;
reg [31:0] out_buf_data    = 32'h0;
reg [31:0] out_buf_addr    = 32'h0;
reg        one_shot_fired  = 1'b0;  // set after first fire when one_shot=1

// sync_wait state — two sequential arrivals required before firing
reg        a_arrived  = 1'b0;   // first input has landed
reg [31:0] a_data     = 32'h0;  // value from first arrival

// Pre-registered armed signal — breaks frozen+start_flag out of latch_reemit chain.
// Yosys would otherwise merge !frozen && start_flag with the bus_hit computation,
// pulling a_arrived and one_shot_fired onto the latch_reemit setup path.
reg        armed_r    = 1'b0;   // registered: !frozen && start_flag, one cycle delayed

// Phase flag: toggles each posedge — emulates negedge drain on single-edge fabric.
// odd_phase=0: load output buffer from data path
// odd_phase=1: drain output buffer to output registers
reg odd_phase = 1'b0;

// ── Debug outputs ──────────────────────────────────────────────────────────────
assign dbg_cmd_latch   = cmd_latch & 32'hFFC007FF;  // auth_mask [21:11] zeroed
assign dbg_input_addr  = {16'h0, input_address};
assign dbg_output_addr = {16'h0, output_address};
assign dbg_start_flag  = start_flag;
assign dbg_armed       = start_flag;
assign dbg_frozen      = frozen;
assign dbg_priority    = priority;
assign dbg_trace       = trace;
assign dbg_breakpoint  = breakpoint;
assign dbg_dtype       = dtype;

// ── NOR Gate Topology — combinational ─────────────────────────────────────────
// input_val, gate chain, and computed_output are all combinational wires.
// Firing condition wires (new_data, latch_reemit) are parallel — no else-if
// chain on the critical path.

wire input_val = (bus_valid && !cmd_valid && (bus_addr[15:0] == input_address) && start_flag && !frozen)
                 ? (bus_from_cell ? bus_data[0]             // cell origin: use directly
                                  : (a_arrived ? a_data[0]  // host 2nd: use latched
                                               : bus_data[0])) // host 1st: store only
                 : data_reg[0];

wire g0 = ~(input_val | input_val);   // NOT
wire g1 = ~(input_val | input_val);
wire g2 = ~(g0 | g1);                 // NOR(NOT,NOT) = AND
wire g3 = ~(g2 | input_val);
wire g4 = ~(g2 | input_val);
wire g5 = ~(g3 | g4);
wire g6 = ~(g5 | input_val);
wire g7 = ~(g6 | g5);
wire g8 = ~(g7 | 1'b0);

reg computed_output;
always @(*) begin
    case (topology)
        10'b0000000001: computed_output = g0;  // NOT
        10'b0000000010: computed_output = g1;
        10'b0000000100: computed_output = g2;  // NOR (baseline)
        10'b0000001000: computed_output = g3;
        10'b0000010000: computed_output = g4;
        10'b0000100000: computed_output = g5;
        10'b0001000000: computed_output = g6;
        10'b0010000000: computed_output = g7;
        10'b0100000000: computed_output = g8;
        default:        computed_output = input_val;  // PASS
    endcase
    // invert_out applied in drain cycle — keeps it off the data load path
end

// Firing condition wires — parallel, not chained ────────────────────────────
// All cells use latch-then-fire by default:
//   First arrival  → stored in a_data, a_arrived set, no output
//   Second arrival → fires using a_data, a_arrived cleared
// Command bus operations bypass this — they go directly to target latches.
// sync_wait bit retained in cmd_latch[10] for future repurposing.
wire bus_hit  = !frozen && start_flag && bus_valid && !cmd_valid
                && (bus_addr[15:0] == input_address);
wire new_data = bus_hit
                && !(one_shot && one_shot_fired)
                && (bus_from_cell || a_arrived);  // cell origin: fire immediately
                                                  // host origin: require two arrivals

// latch_reemit is registered — computed at end of cycle N, used at cycle N+1.
// This keeps it off the CEN path of out_buf_addr FFs (CEN has tight setup on iCE40).
// One cycle latency is acceptable — latch_in re-emission is not time-critical.
reg latch_reemit = 1'b0;

// ── Auth check — combinational ────────────────────────────────────────────────
// auth_mask stored in cmd_latch[21:11]. Token arrives on cmd_bus[14:4].
// Boot bypass: if stored mask is all zeros, first RECONFIGURE accepted
// unconditionally and sets the mask. After that, silent reject on mismatch.
wire [10:0] auth_mask    = cmd_latch[21:11];
wire [10:0] auth_token   = cmd_bus[14:4];
wire        auth_boot    = (auth_mask == 11'h0);  // not yet set
wire        auth_ok      = auth_boot || (auth_token == auth_mask);


always @(posedge clk) begin
    if (rst) begin
        cmd_latch         <= 32'h0;
        input_address     <= CELL_ID[15:0];
        output_address    <= CELL_ID[15:0] + 1;
        data_reg          <= 32'h0;
        frozen            <= 1'b0;
        out_valid         <= 1'b0;
        out_data          <= 32'h0;
        out_addr          <= 32'h0;
        out_buf_valid     <= 1'b0;
        out_buf_data      <= 32'h0;
        out_buf_addr      <= 32'h0;
        one_shot_fired    <= 1'b0;
        a_arrived         <= 1'b0;
        a_data            <= 32'h0;
        latch_reemit      <= 1'b0;
        armed_r           <= 1'b0;
        odd_phase         <= 1'b0;

    end else begin
        out_valid <= 1'b0;
        odd_phase <= ~odd_phase;
        if (ENABLE_LATCH_IN)
            armed_r <= !frozen && start_flag;

        // ── Command bus ───────────────────────────────────────────────────────
        if (cmd_valid) begin
            case (cmd_bus[3:0])
                CMD_RECONFIGURE: begin
                    if (auth_ok) begin
                        cmd_latch      <= cmd_data;
                        frozen         <= 1'b0;
                        one_shot_fired <= 1'b0;
                        a_arrived      <= 1'b0;
                    end
                end
                CMD_SET_INPUT_ADDR: begin
                    input_address <= cmd_data[15:0];
                end
                CMD_SET_OUTPUT_ADDR: begin
                    output_address <= cmd_data[15:0];
                end
                CMD_FREEZE: begin
                    if (auth_ok) begin
                        frozen        <= 1'b1;
                        out_valid     <= 1'b0;
                        out_buf_valid <= 1'b0;
                    end
                end
                CMD_RELEASE: begin
                    if (auth_ok) frozen <= 1'b0;
                end
                default: ;
            endcase
        end

        // ── Output buffer drain (odd_phase = negedge emulation) ───────────────
        if (odd_phase && out_buf_valid) begin
            out_addr      <= out_buf_addr;
            out_data      <= invert_out ? {31'h0, ~out_buf_data[0]} : out_buf_data;
            out_valid     <= 1'b1;
            out_buf_valid <= 1'b0;
        end

        // ── Data bus ─────────────────────────────────────────────────────────
        // First arrival: store in a_data latch, set a_arrived, no output.
        // Second arrival: fires using a_data, clears a_arrived for next pair.
        if (bus_hit && !a_arrived) begin
            a_data    <= bus_data;
            a_arrived <= 1'b1;
        end

        // Normal fire (or sync_wait second arrival)
        if (new_data) begin
            // data_reg stores computed output for latch_in re-emission.
            // loop_back uses it to feed output back as next input.
            data_reg      <= {31'h0, computed_output};
            out_buf_addr  <= {16'h0, output_address};
            out_buf_data  <= {31'h0, computed_output};
            out_buf_valid <= 1'b1;
            a_arrived     <= 1'b0;  // reset for next pair
            if (one_shot) begin
                one_shot_fired <= 1'b1;
                cmd_latch[22]  <= 1'b0;  // clear start_flag
            end
        end else if (ENABLE_LATCH_IN && latch_reemit) begin
            out_buf_addr  <= {16'h0, output_address};
            out_buf_data  <= data_reg;
            out_buf_valid <= 1'b1;
        end

        // ── Register latch_reemit for next cycle — keeps it off CEN path ─────
        // Only compiled when ENABLE_LATCH_IN=1. Zero logic when disabled.
        if (ENABLE_LATCH_IN)
            latch_reemit <= armed_r && latch_in && !out_buf_valid;
    end
end

// ── odd_phase / negedge emulation note ────────────────────────────────────────
// iCE40 does not support negedge-triggered flip-flops. The odd_phase toggle
// gives half-cycle granularity using only posedge registers. Data arrives and
// loads the output buffer on even phases; the buffer drains to out_* on odd
// phases. See docs/VERILOG_SPEC.md § Timing Issues Found and Resolved.

endmodule
