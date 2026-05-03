// unicell_latch.v — Imago UniCell — Latch Model
// Claudette v2.1 / unicell-latch variant
//
// The latch model separates the clock from the compute path entirely.
// The NOR gate tree is purely combinational. Two flip-flop banks (input FF
// and output FF) are the only registered elements. The clock controls only
// when data flows through these banks — it never touches the gate tree.
//
// Timing (pipeline formula: chain_latency(n) = n + 1):
//
//   Tick N:   bus → input_ff  (Phase 2: array delivers bus data to input latch)
//   Tick N+1: input_ff → gate tree → output_ff  (Phase 3: compute)
//   Tick N+2: output_ff → bus  (Phase 1: array drains output latch)
//
//   Single cell: 2 ticks.
//   Chain of n cells: n + 1 ticks.
//   PASS cells add exactly 1 tick each — use for path balancing.
//
// Gate tree:
//   9 NOR gates in a fixed topology. gate_state[8:0] selects which gates
//   are "active" (the rest are bypassed, passing their first operand through).
//   One-input mode: A alone feeds the tree (standard / SYNC_WAIT v1 compat).
//   Two-input mode: A (rising edge) and B (falling edge) feed distinct inputs.
//
// SYNC_WAIT (bit 15):
//   Cell waits until both A (input_ff) and B (input_b_ff) are valid before
//   computing. B arrives from a separate bus address (input_b_address).
//   Once both are present, the gate tree fires and both latches are cleared.
//   This models the v2 two-input cell — posedge A, negedge B.
//
// Configuration sequence (same as standard variant):
//   1. Send LOAD_PATTERN (0xA5A5A5A5) to CONFIG_ADDRESS
//   2. Next bus value → gate_state
//   3. Next bus value → input_address
//   4. Next bus value → output_address (+ optional input_b_address for SYNC_WAIT)
//   Cell arms after step 4. SELECT cells take an additional output_address_alt.
//
// Freeze line:
//   When asserted, the cell is fully decoupled. State is preserved.
//   Used for pond migration and snapshots.
//
// Vendor-neutral RTL:
//   No vendor-specific primitives. Standard Verilog-2001 only.
//   Synthesises on iCE40, ECP5, Xilinx 7-series, Intel Cyclone, SKY130 ASIC.
//   Board-specific constraints live in top_*.v only.
//
// Resource estimate (gate tree + two FF banks):
//   iCE40:   ~95 LUTs per cell
//   Artix-7: ~54 LUTs per cell
//   ECP5:    ~60 LUTs per cell
//
// A 32-cell latch array fits comfortably on iCEBreaker (iCE40UP5K: 5280 LUTs).

`timescale 1ns / 1ps

module unicell_latch #(
    parameter CELL_ID        = 0,
    parameter CONFIG_ADDRESS = CELL_ID   // Fixed synthesis-time config address.
                                         // Runtime data routing uses input_address.
                                         // These are intentionally separate.
) (
    input  wire        clk,         // System clock
    input  wire        rst,         // Synchronous reset (active high)
    input  wire        freeze,      // Freeze line — decouples cell entirely

    // Shared bus interface (all cells see same bus)
    input  wire [31:0] bus_addr,    // Current bus address
    input  wire [31:0] bus_data,    // Current bus data
    input  wire        bus_valid,   // Bus transaction valid this cycle

    // Output to bus (wired-OR topology: only one cell writes per address per cycle)
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    // Direct start_flag control — dedicated hardware line, not a bus address.
    // Set/cleared by controller. Never via bus data.
    input  wire        start_flag,

    // Debug / observability
    output wire [31:0] dbg_gate_state,
    output wire [31:0] dbg_input_addr,
    output wire [31:0] dbg_output_addr,
    output wire [31:0] dbg_input_b_addr,
    output wire        dbg_armed,
    output wire        dbg_frozen,
    output wire        dbg_input_valid,
    output wire        dbg_output_valid,
    output wire        dbg_b_valid
);

// ── Constants ─────────────────────────────────────────────────────────────────
localparam LOAD_PATTERN = 32'hA5A5A5A5;

// gate_state bit assignments (gate_states.py)
// Bits 8:0  — NOR gate topology (which of 9 gates are active)
// Bit  9    — GS_SELECT (conditional router, not compute)
// Bit  10   — LOOP_MODE (stay armed after firing)
// Bit  11   — GS_LATCH  (re-emit stored value every tick)
// Bit  12   — GS_ONE_SHOT (fire once then lock permanently)
// Bit  13   — GS_INVERT_OUT (flip output after gate tree)
// Bit  14   — GS_BROADCAST (fan out to all — array level)
// Bit  15   — GS_SYNC_WAIT (wait for both A and B before firing)
// Bit  16   — GS_LOOP_BACK (internal G8→G0 feedback — future)
// Bit  23   — GS_ADDR_LATCH (extended 64-bit address — bridge cells)
// Bit  24   — GS_FALL_EDGE (assert on falling edge — standard variant only)
// Bits 29-31 — PRIORITY / TRACE / BREAKPOINT

// Config state machine
localparam CFG_IDLE         = 3'd0;
localparam CFG_LOAD_GS      = 3'd1;
localparam CFG_LOAD_IADDR   = 3'd2;
localparam CFG_LOAD_OADDR   = 3'd3;
localparam CFG_LOAD_BADDR   = 3'd4;   // input_b_address (SYNC_WAIT cells)
localparam CFG_LOAD_ALT     = 3'd4;   // output_address_alt (SELECT cells)
// Note: SYNC_WAIT and SELECT are mutually exclusive so CFG_LOAD_BADDR
// and CFG_LOAD_ALT share step 4 — gate_state[15] distinguishes them.

// ── Configuration registers ───────────────────────────────────────────────────
reg [31:0] gate_state;       // NOR topology + mode flags
reg [31:0] input_address;    // Runtime data listen address A
reg [31:0] input_b_address;  // Runtime data listen address B (SYNC_WAIT)
reg [31:0] output_address;   // Address this cell drives
reg [31:0] output_address_alt; // SELECT branch — condition=0 target
reg [2:0]  cfg_state;        // Config state machine

// Mode flags — registered copies of gate_state bits for fast decode
reg        mode_loop;        // bit 10: stay armed after firing
reg        mode_latch;       // bit 11: hold + re-emit stored value
reg        mode_one_shot;    // bit 12: fire once then lock
reg        mode_invert;      // bit 13: invert gate output
reg        mode_sync_wait;   // bit 15: two-input A+B gate
reg        mode_select;      // bit 9:  conditional router
reg        one_shot_fired;   // latched after GS_ONE_SHOT fires

// ── Input FF bank (Phase 2: bus → input latches) ─────────────────────────────
// These registers model the input side of the latch model pipeline.
// Loaded when bus delivers data to this cell's listen address.
reg [31:0] input_ff;          // A input (from input_address)
reg        input_ff_valid;    // 1 when input_ff holds unprocessed data

reg [31:0] input_b_ff;        // B input (from input_b_address, SYNC_WAIT only)
reg        input_b_ff_valid;  // 1 when input_b_ff holds unprocessed data

// ── Output FF bank (Phase 3: gate tree → output latch, Phase 1: → bus) ───────
// Loaded by the compute phase. Drained to bus on the following clock edge.
reg [31:0] output_ff_addr;    // Address to write
reg [31:0] output_ff_data;    // Data to write
reg        output_ff_valid;   // 1 when output_ff holds undrained data

// Stored value for LATCH mode (re-emitted every tick)
reg [31:0] stored_value;
reg        stored_valid;

// ── Debug outputs ─────────────────────────────────────────────────────────────
assign dbg_gate_state   = gate_state;
assign dbg_input_addr   = input_address;
assign dbg_output_addr  = output_address;
assign dbg_input_b_addr = input_b_address;
assign dbg_armed        = start_flag;
assign dbg_frozen       = freeze;
assign dbg_input_valid  = input_ff_valid;
assign dbg_output_valid = output_ff_valid;
assign dbg_b_valid      = input_b_ff_valid;

// ── NOR Gate Tree (purely combinational) ──────────────────────────────────────
//
// 9-gate topology. gate_state[8:0] selects which gates are "active".
// An inactive gate passes its first operand unchanged (bypassed).
// This matches the Python _execute_nor_gates_v2(a, b) implementation exactly.
//
// Gate map:
//   g0 = active(0) ? NOR(a, a) : a        — NOT(A)
//   g1 = active(1) ? NOR(b, b) : b        — NOT(B)
//   g2 = active(2) ? NOR(g0, g1) : g0     — AND(A, B) when g0=NOT(A), g1=NOT(B)
//   g3 = active(3) ? NOR(g2, b)  : g2
//   g4 = active(4) ? NOR(g2, a)  : g2
//   g5 = active(5) ? NOR(g3, g4) : g3
//   g6 = active(6) ? NOR(g5, b)  : g5
//   g7 = active(7) ? NOR(g6, g5) : g6
//   g8 = active(8) ? NOR(g7, 1'b0) : g7   — final output gate
//
// One-input mode: b = a (A feeds both ports). Matches _execute_nor_gates(value).
// Two-input mode: a and b are independent (SYNC_WAIT).

// Gate tree operates on single bits (1-bit logic throughout).
// Full 32-bit data: only data[0] is meaningful (Imago is 1-bit per cell output).
//
// IMPORTANT: The gate tree is purely combinational and reads directly from the
// input FF registers (input_ff, input_b_ff). This means computed_bit always
// reflects the CURRENT contents of those registers — no extra pipeline stage.
// When the clocked block loads input_ff and immediately reads computed_bit in
// the same always block, it reads the OLD value (before assignment). This is
// intentional: the result is stored in output_ff this tick and drained to bus
// the NEXT tick, giving chain_latency(n) = n+1.

// Gate tree A and B inputs come directly from input FFs (combinational).
// In one-input mode, B mirrors A. In SYNC_WAIT mode, B comes from input_b_ff.
wire a_in = input_ff[0];
wire b_in = mode_sync_wait ? input_b_ff[0] : input_ff[0];

wire g0 = gate_state[0] ? ~(a_in | a_in) : a_in;  // NOT(A) or pass A
wire g1 = gate_state[1] ? ~(b_in | b_in) : b_in;  // NOT(B) or pass B
wire g2 = gate_state[2] ? ~(g0   | g1  ) : g0;
wire g3 = gate_state[3] ? ~(g2   | b_in) : g2;
wire g4 = gate_state[4] ? ~(g2   | a_in) : g2;
wire g5 = gate_state[5] ? ~(g3   | g4  ) : g3;
wire g6 = gate_state[6] ? ~(g5   | b_in) : g5;
wire g7 = gate_state[7] ? ~(g6   | g5  ) : g6;
wire g8 = gate_state[8] ? ~(g7   | 1'b0) : g7;

// Final output with optional invert
wire computed_bit = mode_invert ? ~g8 : g8;

// ── SELECT routing ────────────────────────────────────────────────────────────
// SELECT cell: routes data wave to output_address (condition=1) or
// output_address_alt (condition=0). The value forwarded is the condition bit.
wire        select_condition = input_ff[0];
wire [31:0] select_target    = select_condition ? output_address : output_address_alt;

// ── Phase 1: Drain output FF → bus ────────────────────────────────────────────
// At the start of each tick the array drains output_ff → bus.
// Implemented here as an always block driven by clk posedge.
// The output_ff is cleared after draining.
//
// NOTE: In the Python array the three phases are sequenced within a single
// tick() call. In RTL we collapse Phase 1 (drain) and Phase 2 (load) into
// a single clocked always block — they happen on the same clock edge.
// This matches the Python observation that chain_latency(n) = n+1, not n*2:
// drain and load happen together, so each cell adds only 1 tick of latency.

always @(posedge clk) begin
    if (rst) begin
        // ── Reset ──────────────────────────────────────────────────────────
        gate_state         <= 32'h0;
        input_address      <= 32'h0;
        input_b_address    <= 32'h0;
        output_address     <= 32'h0;
        output_address_alt <= 32'h0;
        cfg_state          <= CFG_IDLE;
        mode_loop          <= 1'b0;
        mode_latch         <= 1'b0;
        mode_one_shot      <= 1'b0;
        mode_invert        <= 1'b0;
        mode_sync_wait     <= 1'b0;
        mode_select        <= 1'b0;
        one_shot_fired     <= 1'b0;
        input_ff           <= 32'h0;
        input_ff_valid     <= 1'b0;
        input_b_ff         <= 32'h0;
        input_b_ff_valid   <= 1'b0;
        output_ff_addr     <= 32'h0;
        output_ff_data     <= 32'h0;
        output_ff_valid    <= 1'b0;
        stored_value       <= 32'h0;
        stored_valid       <= 1'b0;
        out_valid          <= 1'b0;
        out_addr           <= 32'h0;
        out_data           <= 32'h0;

    end else if (freeze) begin
        // ── Freeze — preserve state, suppress bus output ───────────────────
        out_valid <= 1'b0;

    end else begin
        // ── Phase 1: Drain output_ff → bus ───────────────────────────────
        // Done first so downstream cells can receive this cycle's output.
        if (output_ff_valid && start_flag) begin
            out_addr      <= output_ff_addr;
            out_data      <= output_ff_data;
            out_valid     <= 1'b1;
            output_ff_valid <= 1'b0;
        end else begin
            out_valid <= 1'b0;
        end

        // ── LATCH mode re-emission ─────────────────────────────────────────
        // In latch mode, re-emit stored_value every tick when no new compute
        // result is pending. This fires after output_ff is drained.
        if (mode_latch && stored_valid && start_flag && !output_ff_valid) begin
            out_addr  <= output_address;
            out_data  <= stored_value;
            out_valid <= 1'b1;
        end

        // ── Phase 2: Bus → input FFs ──────────────────────────────────────
        // Deliver bus data to this cell's listen addresses.
        // Config traffic is handled first.
        if (bus_valid) begin
            case (cfg_state)
                CFG_IDLE: begin
                    if (bus_addr == CONFIG_ADDRESS[31:0] &&
                        bus_data == LOAD_PATTERN) begin
                        // Config sequence triggered
                        cfg_state      <= CFG_LOAD_GS;
                        one_shot_fired <= 1'b0;
                        input_ff_valid   <= 1'b0;
                        input_b_ff_valid <= 1'b0;
                        output_ff_valid  <= 1'b0;
                        stored_valid     <= 1'b0;
                    end else if (bus_addr == input_address && start_flag) begin
                        // A input arrived
                        input_ff       <= bus_data;
                        input_ff_valid <= 1'b1;
                    end else if (mode_sync_wait &&
                                 bus_addr == input_b_address && start_flag) begin
                        // B input arrived (SYNC_WAIT cells only)
                        input_b_ff       <= bus_data;
                        input_b_ff_valid <= 1'b1;
                    end
                end

                CFG_LOAD_GS: begin
                    gate_state     <= bus_data;
                    mode_loop      <= bus_data[10];
                    mode_latch     <= bus_data[11];
                    mode_one_shot  <= bus_data[12];
                    mode_invert    <= bus_data[13];
                    mode_sync_wait <= bus_data[15];
                    mode_select    <= bus_data[9];
                    stored_valid   <= 1'b0;
                    cfg_state      <= CFG_LOAD_IADDR;
                end

                CFG_LOAD_IADDR: begin
                    input_address <= bus_data;
                    cfg_state     <= CFG_LOAD_OADDR;
                end

                CFG_LOAD_OADDR: begin
                    output_address <= bus_data;
                    // SELECT and SYNC_WAIT cells need one more config word.
                    // Standard cells close config here.
                    if (gate_state[9] || gate_state[15]) begin
                        cfg_state <= CFG_LOAD_BADDR; // step 4
                    end else begin
                        cfg_state <= CFG_IDLE;
                    end
                end

                CFG_LOAD_BADDR: begin
                    // Step 4: input_b_address for SYNC_WAIT cells,
                    //         output_address_alt for SELECT cells.
                    if (gate_state[15])
                        input_b_address <= bus_data;    // SYNC_WAIT B address
                    else
                        output_address_alt <= bus_data; // SELECT alt target
                    cfg_state <= CFG_IDLE;
                end

                default: cfg_state <= CFG_IDLE;
            endcase
        end // bus_valid

        // ── Phase 3: Compute — input_ff → gate tree → output_ff ──────────
        // Fire the gate tree when input data is ready.
        // Conditions:
        //   - Cell is armed (start_flag)
        //   - Not in config mode (cfg_state == CFG_IDLE)
        //   - ONE_SHOT: has not already fired
        //   - Standard: input_ff_valid
        //   - SYNC_WAIT: input_ff_valid AND input_b_ff_valid
        //   - LATCH mode: input_ff_valid (updates stored_value)
        //   - SELECT: input_ff_valid (routes condition bit)

        if (start_flag && cfg_state == CFG_IDLE &&
                !(mode_one_shot && one_shot_fired)) begin

            // ── SYNC_WAIT (two-input) ────────────────────────────────────
            if (mode_sync_wait) begin
                if (input_ff_valid && input_b_ff_valid) begin
                    input_ff_valid   <= 1'b0;
                    input_b_ff_valid <= 1'b0;
                    // computed_bit is a combinational wire from input_ff[0] and
                    // input_b_ff[0]. Since both FFs were loaded in a previous tick
                    // (input_ff_valid was 1), computed_bit reflects their stored values.
                    output_ff_addr  <= output_address;
                    output_ff_data  <= {31'h0, computed_bit};
                    output_ff_valid <= 1'b1;
                    if (mode_one_shot)
                        one_shot_fired <= 1'b1;
                end

            // ── SELECT cell ──────────────────────────────────────────────
            end else if (mode_select) begin
                if (input_ff_valid) begin
                    input_ff_valid  <= 1'b0;
                    output_ff_addr  <= select_target;
                    output_ff_data  <= {31'h0, select_condition};
                    output_ff_valid <= 1'b1;
                end

            // ── LATCH mode ───────────────────────────────────────────────
            end else if (mode_latch) begin
                if (input_ff_valid) begin
                    input_ff_valid <= 1'b0;
                    // computed_bit is combinational from input_ff[0] (loaded last tick)
                    stored_value   <= {31'h0, computed_bit};
                    stored_valid   <= 1'b1;
                    // output_ff not used in latch mode — re-emission
                    // goes directly to out_* from stored_value (Phase 1).
                end

            // ── Standard compute ─────────────────────────────────────────
            end else begin
                if (input_ff_valid) begin
                    input_ff_valid  <= 1'b0;
                    // computed_bit is combinational from input_ff[0] (loaded last tick)
                    output_ff_addr  <= output_address;
                    output_ff_data  <= {31'h0, computed_bit};
                    output_ff_valid <= 1'b1;
                    if (mode_one_shot)
                        one_shot_fired <= 1'b1;
                end
            end
        end // start_flag && compute enable

    end // not freeze, not rst
end // always @(posedge clk)

endmodule
