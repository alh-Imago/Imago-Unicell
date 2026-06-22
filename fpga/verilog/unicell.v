// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// unicell.v — Imago UniCell — Single Cell Implementation
// Protocol v2.3 — unified 32-bit command bus, two-state boot/run model
//
// TWO STATES:
//   BOOT state: cell exposes baked-in CELL_ID on address bus.
//               Boot controller finds cell by CELL_ID, sends logical address
//               + auth_mask in one transaction, then CMD_BOOT_COMMIT flips
//               cell to RUN state. physical_mode cleared permanently.
//   RUN  state: cell responds to logical input_address only.
//               Command bus carries all control + modifiers per transaction.
//               CELL_ID register repurposed — physical address gone.
//
// Command bus (32-bit unified word — RUN state):
//   cmd_bus [31:0]:
//     bits  7:0   opcode        — 8-bit operation code (256 opcodes)
//     bit   8     gate_enable   — 1 = apply gate_set filter; 0 = broadcast
//     bits 16:9   gate_set      — 8-bit group select (cells check own group tag)
//     bits 18:17  preload_sel   — transient: load constant into a_data/a_arrived
//                                 00 = no preload
//                                 01 = preload 0x00000000 (AND tree false side)
//                                 10 = preload 0xFFFFFFFF (NOT/XOR constant)
//                                 11 = reserved
//     bits 20:19  shift_sel     — transient per-transaction shift modifier
//                                 bit 19 = shift_in_en  (shift input before gate)
//                                 bit 20 = shift_out_en (shift output after gate)
//                                 shift amount carried in cmd_data[3:0] (nibble count)
//     bits 28:21  auth_token    — 8-bit token, matched against stored auth_mask
//     bits 31:29  spare         — reserved, must be zero
//
//   cmd_data [31:0] — payload (address, cfg word, or shift amount):
//     SET_INPUT_ADDR / SET_OUTPUT_ADDR: cmd_data[15:0] = address
//     CMD_RECONFIGURE:                  cmd_data[31:0] = full cmd_latch word
//                                       (auth_mask in cmd_latch[18:11])
//     shift ops:                        cmd_data[3:0]  = nibble shift count (0-7)
//
//   cmd_valid [0] — command valid this cycle (unchanged)
//
// Data bus (unchanged):
//   bus_addr [15:0]  — data bus address (logical)
//   bus_data [31:0]  — data bus payload
//
//
// cmd_latch[31:0] — cell internal state (loaded by CMD_RECONFIGURE, NOT the command bus):
//   [9:0]   topology    — NOR gate selection (one-hot, bit 0 = NOT/pass)
//   [10]    edge_mode   — 0=STANDARD/LATCH, 1=EDGE cell
//   [18:11] auth_mask   — 8-bit security token (zeroed before ICM serialisation)
//   [19]    output_set  — 1=output address configured, cell may fire
//   [20]    latch_A_dis — 1=disable A latch store (PASS(B) effect from any topology)
//   [21]    latch_B_dis — 1=disable B arrival trigger (PASS(A) effect from any topology)
//   [22]    start_flag  — 1=cell armed and listening
//   [24:23] dtype       — 00=NUMERIC 01=SIGNED 10=ALPHA 11=DATETIME
//   [25]    invert_out  — invert computed output
//   [26]    latch_in    — hold a_arrived set after firing (single arrival fires next)
//   [27]    priority    — high priority scheduling
//   [28]    trace       — log every fire
//   [29]    breakpoint  — halt array on fire
//   [30]    one_shot    — fire once then disarm (start_flag → 0)
//   [31]    loop_back   — feed computed output back as next a_data (counter/accumulator)
//
// NOTE: preload_sel and shift_sel are command bus transient modifiers only.
//       They are NOT stored in cmd_latch. preload_sel triggers a write to
//       a_data + a_arrived at command time. shift_sel modifies data in-flight.
//       No cmd_latch bits consumed by these features.
//
// Opcode table (cmd_bus[7:0]) — auth required unless noted:
//   0x00 CMD_NOP
//   0x01 CMD_DATA_WRITE        — inject data onto bus (no auth)
//   0x02 CMD_SET_INPUT_ADDR    — cmd_data[15:0] → input_address (auth)
//   0x03 CMD_SET_OUTPUT_ADDR   — cmd_data[15:0] → output_address, output_set=1 (auth)
//   0x04 CMD_RECONFIGURE       — cmd_data[31:0] → cmd_latch (auth_mask in [18:11]) (auth)
//   0x05 CMD_FREEZE            — disarm cell (auth)
//   0x06 CMD_RELEASE           — re-arm cell (auth)
//   0x07 CMD_BOOT_COMMIT       — BOOT STATE ONLY: accept logical addr + auth_mask,
//                                flip physical_mode=0 (RUN state). No auth needed
//                                (cell not yet configured). cmd_data[15:0]=logical addr,
//                                cmd_data[23:16]=auth_mask to store in cmd_latch[18:11].
//   0x08 CMD_ARRAY_RESET       — System-wide authenticated hard reset. All cells
//                                simultaneously revert to BOOT state (physical_mode=1,
//                                CELL_ID addresses, cmd_latch cleared). Requires
//                                auth_token != 0 in cmd_bus[28:21]. Implemented in
//                                top_icebreaker.v — pulses array rst for one cycle.
//                                Safe: simultaneous reset, no bus address collision.
//   0x09 CMD_PING              — no-op response
//   0x0A CMD_LATCH_IN_ON       — set latch_in (auth)
//   0x0B CMD_LATCH_IN_OFF      — clear latch_in, reset a_arrived (auth)
//   0x0C CMD_MEM_CALL          — latch_in+one_shot+rearm atomically (auth)
//   0x0D CMD_REARM             — rearm one-shot, clear arrived (auth)
//   0x0E CMD_SET_LOGICAL       — set logical input addr, suppress physical ID (auth)
//   0x0F CMD_PRELOAD           — [DEPRECATED — use preload_sel bits 18:17 on cmd_bus]
//                                kept for iCEBreaker compatibility only
//   0x10 CMD_CLEAR_ARRIVED     — clear a_arrived + a_data (auth)
//   0x11 CMD_RESET_CELL        — clear arrived+data+one_shot_fired, rearm (auth)
//   0x12 CMD_SWAP_AB           — load a_data from cmd_data[12:0], set a_arrived (auth)
//   0x13 CMD_CAPTURE_REARM     — fire output + rearm one_shot (auth)
//   0x14 CMD_SET_TOPO          — write topology bits only (auth)
//   0x15 CMD_SET_INVERT        — toggle invert_out (auth)
//   0x16 CMD_PRELOAD_HI        — [DEPRECATED — use preload_sel bits 18:17 on cmd_bus]
//                                kept for iCEBreaker compatibility only
//
//   Topology presets (0x30-0x45, cold=even opcode, armed=odd opcode):
//   0x30/31 CMD_TOPO_PASS_A    — topology=0x000 latch_in=1
//   0x32/33 CMD_TOPO_NOT_A     — topology=0x001 latch_in=1
//   0x34/35 CMD_TOPO_NOR       — topology=0x004
//   0x36/37 CMD_TOPO_AND       — topology=0x007
//   0x38/39 CMD_TOPO_OR        — topology=0x024
//   0x3A/3B CMD_TOPO_NAND      — topology=0x027
//   0x3C/3D CMD_TOPO_PASS_B    — topology=0x02C
//   0x3E/3F CMD_TOPO_XNOR      — topology=0x03C
//   0x40/41 CMD_TOPO_XOR       — topology=0x0BC
//   0x42/43 CMD_TOPO_ZERO      — topology=0x030 latch_in=1
//   0x44/45 CMD_TOPO_ONE       — topology=0x0B0 latch_in=1
//
// CMD_RECONFIGURE payload mapping (cmd_data[31:0] → cmd_latch):
//   cmd_data[9:0]   → topology
//   cmd_data[10]    → edge_mode
//   cmd_data[11]    → start_flag
//   cmd_data[12]    → latch_A_dis
//   cmd_data[13]    → latch_B_dis
//   cmd_data[15:14] → dtype[1:0]
//   cmd_data[16]    → invert_out
//   cmd_data[17]    → latch_in
//   cmd_data[18]    → priority
//   cmd_data[19]    → trace
//   cmd_data[20]    → breakpoint
//   cmd_data[21]    → one_shot
//   cmd_data[22]    → loop_back
//   cmd_data[30:23] → auth_mask → stored in cmd_latch[18:11]
//   (auth_mask arrives in cmd_data on RECONFIGURE, not cmd_bus auth_token field)
//
// preload_sel handling (cmd_bus[18:17], transient — any opcode):
//   01 → a_data = 32'h00000000, a_arrived = 1  (AND tree false, NOR constant)
//   10 → a_data = 32'hFFFFFFFF, a_arrived = 1  (NOT/XOR/XNOR constant)
//   Applied after opcode logic, if auth_ok.
//
// shift_sel handling (cmd_bus[20:19], transient — data bus transactions):
//   bit 19 shift_in_en:  bus_data shifted left by cmd_data[3:0] nibbles before gate
//   bit 20 shift_out_en: computed_output shifted right by cmd_data[3:0] nibbles on emit
//   shift amount: cmd_data[3:0] = nibble count (0=no shift, 1=4 bits, ... 7=28 bits)
//
// Boot sequence per cell (2 transactions):
//   1. CMD_BOOT_COMMIT (opcode 0x07, no auth needed):
//      cmd_data[15:0]  = logical input_address
//      cmd_data[23:16] = auth_mask to store
//      Cell: stores logical addr, stores auth_mask, clears physical_mode (→ RUN)
//   2. CMD_RECONFIGURE (opcode 0x04, auth now required):
//      cmd_data[31:0]  = full cmd_latch word (topology, flags, etc.)
//      + CMD_SET_OUTPUT_ADDR as needed
//      + CMD_RELEASE to arm
//
// Two-arrival latch (default behaviour):
//   First arrival:  stored as a_data, a_arrived=1, no output
//   Second arrival: fires GATE(a_data, bus_data), resets a_arrived
//
// Silicon status (May 2026):
//   iCEBreaker: test_sync_wait 16/16, test_new_opcodes 26/29
//   Kintex-7 100-cell: 57,338 LUTs (9%), 26.73 MHz
//
// See docs/FPGA_HARDWARE.md for complete reference.

`timescale 1ns / 1ps

(* dont_touch = "true" *)
module unicell #(
    parameter CELL_ID        = 0,   // Unique cell identifier for debug only
    parameter ENABLE_LATCH_IN = 0   // 0 = disable latch_in feature (saves LCs + timing)
                                    // 1 = enable  latch_in (needed for Kintex-7 workloads)
) (
    input  wire        clk,         // System clock (rising edge)
    input  wire        rst,         // Synchronous reset (active high)

    // Command bus (configuration + control) — 32-bit unified word (v2.3)
    input  wire [31:0] cmd_bus,     // [7:0]=opcode [8]=gate_en [16:9]=gate_set
                                    // [18:17]=preload_sel [20:19]=shift_sel
                                    // [28:21]=auth_token [31:29]=spare
    input  wire [31:0] cmd_data,    // Payload: address, cfg word, or shift amount
    input  wire        cmd_valid,   // Command valid this cycle

    // Shared data bus interface
    input  wire [15:0] bus_addr,    // Current bus address (16-bit)
    input  wire [31:0] bus_data,    // Current bus data
    input  wire        bus_valid,   // Bus transaction valid this cycle

    // Output to bus (wired-OR with other cells)
    output reg  [31:0] out_addr,    // Address this cell is writing to
    output reg  [31:0] out_data,    // Data this cell is writing
    output reg         out_valid,   // This cell has output this cycle

    // Debug/observability
    output wire [31:0] dbg_cmd_latch,
    output wire [31:0] dbg_input_addr,
    output wire [15:0] dbg_input_addr_short,
    output wire [31:0] dbg_output_addr,
    output wire        dbg_start_flag,
    output wire        dbg_armed,
    output wire        dbg_frozen,
    output wire        dbg_priority,
    output wire        dbg_trace,
    output wire        dbg_breakpoint,
    output wire [1:0]  dbg_dtype,
    output wire        dbg_output_set,
    output wire        dbg_a_arrived,
    output wire [31:0] dbg_a_data
);

// ── Command codes ──────────────────────────────────────────────────────────────
localparam CMD_NOP              = 8'd0;
localparam CMD_SET_INPUT_ADDR   = 8'd2;
localparam CMD_SET_OUTPUT_ADDR  = 8'd3;
localparam CMD_RECONFIGURE      = 8'd4;
localparam CMD_FREEZE           = 8'd5;
localparam CMD_RELEASE          = 8'd6;
localparam CMD_BOOT_COMMIT      = 8'd7;  // BOOT STATE: set logical addr + auth_mask, → RUN
localparam CMD_ARRAY_RESET      = 8'd8;  // System-wide auth hard reset → all cells → BOOT state
localparam CMD_PING             = 8'd9;
localparam CMD_LATCH_IN_ON      = 8'd10;
localparam CMD_LATCH_IN_OFF     = 8'd11;
localparam CMD_MEM_CALL         = 8'd12;
localparam CMD_REARM            = 8'd13;
localparam CMD_SET_LOGICAL      = 8'd14; // kept for compatibility; use CMD_BOOT_COMMIT for new code
localparam CMD_PRELOAD          = 8'd15; // DEPRECATED — use preload_sel bits on cmd_bus
localparam CMD_CLEAR_ARRIVED    = 8'd16;
localparam CMD_RESET_CELL       = 8'd17;
localparam CMD_SWAP_AB          = 8'd18;
localparam CMD_CAPTURE_REARM    = 8'd19;
localparam CMD_SET_TOPO         = 8'd20;
localparam CMD_SET_INVERT       = 8'd21;
localparam CMD_PRELOAD_HI       = 8'd22; // DEPRECATED — use preload_sel bits on cmd_bus

// Topology presets — cold=even (disarmed), armed=odd
// Pattern: CMD_TOPO_BASE + (gate_index * 2) + armed
// latch_in=1 set automatically for single-input gates
localparam CMD_TOPO_PASS_A_COLD = 8'd48;  // topology=0x000 latch_in=1 armed=0
localparam CMD_TOPO_PASS_A      = 8'd49;  // topology=0x000 latch_in=1 armed=1
localparam CMD_TOPO_NOT_A_COLD  = 8'd50;  // topology=0x001 latch_in=1 armed=0
localparam CMD_TOPO_NOT_A       = 8'd51;  // topology=0x001 latch_in=1 armed=1
localparam CMD_TOPO_NOR_COLD    = 8'd52;  // topology=0x004 latch_in=0 armed=0
localparam CMD_TOPO_NOR         = 8'd53;  // topology=0x004 latch_in=0 armed=1
localparam CMD_TOPO_AND_COLD    = 8'd54;  // topology=0x007 latch_in=0 armed=0
localparam CMD_TOPO_AND         = 8'd55;  // topology=0x007 latch_in=0 armed=1
localparam CMD_TOPO_OR_COLD     = 8'd56;  // topology=0x024 latch_in=0 armed=0
localparam CMD_TOPO_OR          = 8'd57;  // topology=0x024 latch_in=0 armed=1
localparam CMD_TOPO_NAND_COLD   = 8'd58;  // topology=0x027 latch_in=0 armed=0
localparam CMD_TOPO_NAND        = 8'd59;  // topology=0x027 latch_in=0 armed=1
localparam CMD_TOPO_PASS_B_COLD = 8'd60;  // topology=0x02C latch_in=0 armed=0
localparam CMD_TOPO_PASS_B      = 8'd61;  // topology=0x02C latch_in=0 armed=1
localparam CMD_TOPO_XNOR_COLD   = 8'd62;  // topology=0x03C latch_in=0 armed=0
localparam CMD_TOPO_XNOR        = 8'd63;  // topology=0x03C latch_in=0 armed=1
localparam CMD_TOPO_XOR_COLD    = 8'd64;  // topology=0x0BC latch_in=0 armed=0
localparam CMD_TOPO_XOR         = 8'd65;  // topology=0x0BC latch_in=0 armed=1
localparam CMD_TOPO_ZERO_COLD   = 8'd66;  // topology=0x030 latch_in=1 armed=0
localparam CMD_TOPO_ZERO        = 8'd67;  // topology=0x030 latch_in=1 armed=1
localparam CMD_TOPO_ONE_COLD    = 8'd68;  // topology=0x0B0 latch_in=1 armed=0
localparam CMD_TOPO_ONE         = 8'd69;  // topology=0x0B0 latch_in=1 armed=1

// ── Command latch bit positions ────────────────────────────────────────────────
// cmd_latch[31:0] layout:
// [9:0]   topology   (NOR gate selection, one-hot)
// [10]    edge_mode  (0=STANDARD/LATCH, 1=EDGE)
// [18:11] auth_mask  (8-bit, 256 tokens — zeroed before ICM serialisation)
// [19]    output_set  (1=output address explicitly configured, cell may fire)
// [20]    latch_A_dis (1=disable A latch store — PASS(B) effect from any topology)
// [21]    latch_B_dis (1=disable B arrival trigger — PASS(A) effect from any topology)
// [22]    start_flag  (armed — set by CMD_RELEASE)
// [24:23] dtype      (NUMERIC/SIGNED/ALPHA/DATETIME)
// [25]    invert_out
// [26]    latch_in   (single arrival fires, holds value)
// [27]    priority
// [28]    trace
// [29]    breakpoint
// [30]    one_shot   (fire once then disarm)
// [31]    loop_back  (feed output back as next A input)

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
reg        physical_mode  = 1'b1;  // 1=boot(physical ID), 0=run(logical addr)
reg        output_set     = 1'b0;  // 1=output address configured, cell may fire

// Convenience wires into cmd_latch fields
wire [9:0] topology   = cmd_latch[9:0];
wire       edge_mode  = cmd_latch[10];  // 0=STANDARD/LATCH, 1=EDGE cell
wire       start_flag = cmd_latch[22];
wire       invert_out = cmd_latch[25];  // invert output (EDGE: selects negedge)
wire       latch_in   = cmd_latch[26];  // hold a_arrived set — single arrival fires
wire       one_shot   = cmd_latch[30];  // fire once then disarm
wire       loop_back  = cmd_latch[31];  // feed computed output back to data_reg
wire       latch_A_dis = cmd_latch[20]; // disable A latch — live value flows through
wire       latch_B_dis = cmd_latch[21]; // disable B trigger — stored value rebroadcast
wire [1:0] dtype      = cmd_latch[24:23]; // NUMERIC/SIGNED/ALPHA/DATETIME
wire       priority_f = cmd_latch[27];  // high priority scheduling
wire       trace      = cmd_latch[28];  // log every fire to Ward
wire       breakpoint = cmd_latch[29];  // halt array on fire

reg        out_buf_valid   = 1'b0;
reg [31:0] out_buf_data    = 32'h0;
reg [31:0] out_buf_addr    = 32'h0;

// Pipeline registers for bus inputs — breaks high-fanout routing path
// bus_addr/bus_data/bus_valid fan out to all cells; registering inside
// each cell cuts the combinatorial path at the cost of 1 cycle latency.
reg [15:0] bus_addr_r  = 16'h0;
reg [31:0] bus_data_r  = 32'h0;
reg        bus_valid_r = 1'b0;
reg        one_shot_fired  = 1'b0;
reg        prev_data       = 1'b0;  // last seen bus_data[0] — for edge detection  // set after first fire when one_shot=1

// Two-arrival latch state — a_arrived flag, a_data register
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
assign dbg_cmd_latch   = cmd_latch & 32'hFFF807FF;  // auth_mask [18:11] zeroed
assign dbg_input_addr       = {16'h0, input_address};
assign dbg_input_addr_short = input_address;
assign dbg_output_addr = {16'h0, output_address};
assign dbg_start_flag  = start_flag;
assign dbg_armed       = start_flag;
assign dbg_frozen      = frozen;
assign dbg_priority    = priority_f;
assign dbg_trace       = trace;
assign dbg_breakpoint  = breakpoint;
assign dbg_dtype       = dtype;
assign dbg_output_set  = output_set;
assign dbg_a_arrived   = a_arrived;
assign dbg_a_data      = a_data;

// ── NOR Gate Topology — combinational, 32-bit wide ────────────────────────────
// The gate tree operates on all 32 bits of the bus word in parallel.
// input_val[31:0] selects between: bus_data (live), a_data (stored first arrival),
// or data_reg (loop_back / latch_reemit). All 32 bits flow through identically.
//
// Edge mode uses bus_data[0] for transition detection (prev_data is 1-bit),
// but the data word that enters the gate tree is still the full 32-bit bus_data.
// This means an edge cell can detect a transition on bit 0 and propagate the
// full 32-bit bus word — useful for triggering on a strobe while passing a payload.
//
// Firing condition wires (new_data, latch_reemit) are parallel — no else-if
// chain on the critical path.

// ── Nibble shift — combinational, transient (cmd_bus[20:19]) ─────────────────
// shift_in_en  (cmd_bus[19]): shift bus_data LEFT  by shift_nibbles×4 bits
//                             before it enters the gate tree as B (second_val).
// shift_out_en (cmd_bus[20]): shift computed_output RIGHT by shift_nibbles×4 bits
//                             before loading into out_buf_data.
// shift_nibbles = cmd_data[3:0]: 0=no shift, 1=4 bits, ..., 7=28 bits.
// Purely combinational — no registers, no state held. Sent fresh each transaction.
// Nibble-aligned shifts are zero-cell operations. Non-nibble-aligned residuals
// require up to 3 extra cells for the remaining bits.
// Only applied when bus_hit is true (gate tree is live).

wire [31:0] bus_data_shifted;
assign bus_data_shifted = !shift_in_en ? bus_data_r :
                          (shift_nibbles == 4'd1) ? {bus_data_r[27:0],  4'h0} :
                          (shift_nibbles == 4'd2) ? {bus_data_r[23:0],  8'h0} :
                          (shift_nibbles == 4'd3) ? {bus_data_r[19:0], 12'h0} :
                          (shift_nibbles == 4'd4) ? {bus_data_r[15:0], 16'h0} :
                          (shift_nibbles == 4'd5) ? {bus_data_r[11:0], 20'h0} :
                          (shift_nibbles == 4'd6) ? {bus_data_r[7:0],  24'h0} :
                          (shift_nibbles == 4'd7) ? {bus_data_r[3:0],  28'h0} :
                          bus_data_r;  // 0 or >7: no shift

wire [31:0] input_val = (bus_valid_r && !cmd_valid && addr_match && start_flag && !frozen && output_set)
                 ? (edge_mode ? bus_data_shifted                         // EDGE: shifted word on transition
                              : (a_arrived ? a_data : bus_data_shifted)) // STANDARD: a_data or shifted live
                 : data_reg;

// 32-bit NOR gate tree — each gate operates bitwise across the full word.
// Topology selects which gate's output becomes computed_output.
// The two-arrival model: A is stored in a_data (first arrival),
// B is the trigger value (second arrival, live on bus_data when new_data fires).
// For binary ops: input_val carries A (stored), second_val carries B (trigger).
// For single-input ops (NOT, PASS): compiler sends same value twice so A==B.

wire [31:0] second_val = (bus_valid_r && !cmd_valid && addr_match && start_flag && !frozen && output_set)
                 ? bus_data_shifted  // B = shifted bus value (trigger, second arrival)
                 : data_reg;

wire [31:0] g0 = ~(input_val  | input_val);   // NOT(A)
wire [31:0] g1 = ~(second_val | second_val);  // NOT(B)
wire [31:0] g2 = ~(g0 | g1);                  // AND(A,B)    = NOR(NOT(A),NOT(B))
wire [31:0] g3 = ~(g2 | g2);                  // NAND(A,B)   = NOT(AND)
wire [31:0] g4 = ~(input_val  | second_val);  // NOR(A,B)
wire [31:0] g5 = ~(g4 | g4);                  // OR(A,B)     = NOT(NOR)
wire [31:0] g6 = ~(input_val  | g4);          // NOR(A, NOR(A,B))
wire [31:0] g7 = ~(second_val | g4);          // NOR(B, NOR(A,B))
wire [31:0] g8 = ~(g6 | g7);                  // XNOR(A,B)
wire [31:0] g9 = ~(g8 | g8);                  // XOR(A,B)    = NOT(XNOR)

// Topology values match gate_states.py constants exactly.
// Verified against A=0xDEADBEEF, B=0xCAFEBABE in simulation.
reg [31:0] computed_output;
always @(*) begin
    computed_output = input_val;  // default PASS(A)
    case (topology)
        10'h000: computed_output = input_val;           // PASS(A)
        10'h02C: computed_output = second_val;          // PASS(B)
        10'h001: computed_output = g0;                  // NOT(A)
        10'h002: computed_output = g1;                  // NOT(B)
        10'h004: computed_output = g4;                  // NOR(A,B)
        10'h007: computed_output = g2;                  // AND(A,B)
        10'h024: computed_output = g5;                  // OR(A,B)
        10'h027: computed_output = g3;                  // NAND(A,B)
        10'h0BC: computed_output = g9;                  // XOR(A,B)
        10'h03C: computed_output = g8;                  // XNOR(A,B)
        10'h030: computed_output = 32'h0;               // ZERO
        10'h0B0: computed_output = 32'hFFFFFFFF;        // ONE
        default: computed_output = input_val;           // fallback PASS(A)
    endcase
    // invert_out applied in drain cycle — keeps it off the data load path
end

// shift_out: right-shift computed_output by shift_nibbles×4 before emit.
// Applied only when shift_out_en=1 (cmd_bus[20]) and bus_hit is true.
wire [31:0] computed_shifted;
assign computed_shifted = !shift_out_en ? computed_output :
                          (shift_nibbles == 4'd1) ? { 4'h0, computed_output[31: 4]} :
                          (shift_nibbles == 4'd2) ? { 8'h0, computed_output[31: 8]} :
                          (shift_nibbles == 4'd3) ? {12'h0, computed_output[31:12]} :
                          (shift_nibbles == 4'd4) ? {16'h0, computed_output[31:16]} :
                          (shift_nibbles == 4'd5) ? {20'h0, computed_output[31:20]} :
                          (shift_nibbles == 4'd6) ? {24'h0, computed_output[31:24]} :
                          (shift_nibbles == 4'd7) ? {28'h0, computed_output[31:28]} :
                          computed_output;

// Firing condition wires — parallel, not chained ────────────────────────────
// All cells use latch-then-fire by default:
//   First arrival  → stored in a_data, a_arrived set, no output
//   Second arrival → fires using a_data, a_arrived cleared
// Command bus operations bypass this — they go directly to target latches.
// cmd_latch[10] = edge_mode (was sync_wait in v1 — repurposed).
// In physical_mode cell only responds to its physical CELL_ID on the bus.
// After CMD_SET_LOGICAL, cell responds to logical input_address only.
// output_set must be 1 before cell can fire — prevents bus pollution during boot.
wire addr_match = physical_mode ? (bus_addr_r == CELL_ID[15:0])
                                : (bus_addr_r == input_address);
wire bus_hit  = !frozen && start_flag && output_set && bus_valid_r && !cmd_valid
                && addr_match;

// Pre-registered bus_hit — breaks high-fanout path for Kintex-7 timing.
// On iCEBreaker, bus_hit is used directly (1-cycle lower latency).
// For Kintex-7 implementation: replace bus_hit references with bus_hit_r
// and add one cycle to KS_DEPTH in run_int32_function.
reg bus_hit_r = 1'b0;

// Edge detection: posedge = 0→1, negedge = 1→0 (invert_out selects polarity)
wire edge_detected = edge_mode && bus_hit
                     && (invert_out ? (prev_data && !bus_data_r[0])   // negedge: 1→0
                                    : (!prev_data && bus_data_r[0])); // posedge: 0→1

wire new_data = !(one_shot && one_shot_fired)
                && (edge_mode ? edge_detected          // EDGE: fire on transition
                              : (bus_hit && a_arrived)); // STANDARD: two arrivals

// latch_reemit is registered — computed at end of cycle N, used at cycle N+1.
// This keeps it off the CEN path of out_buf_addr FFs (CEN has tight setup on iCE40).
// One cycle latency is acceptable — latch_in re-emission is not time-critical.
reg latch_reemit = 1'b0;

// ── Auth check — combinational ────────────────────────────────────────────────
// auth_mask stored in cmd_latch[18:11] (8-bit). Token arrives in cmd_bus[28:21].
// Boot bypass: if stored mask is all zeros, CMD_BOOT_COMMIT accepted
// unconditionally (cell not yet configured). After that, silent reject on mismatch.
// CMD_BOOT_COMMIT (0x07) is exempt from auth — cell has no auth_mask yet.
wire  [7:0] auth_mask    = cmd_latch[18:11];
wire        auth_boot    = (auth_mask == 8'h0);
wire        auth_ok      = auth_boot || (auth_token == auth_mask);

// ── Command bus field decode (v2.3) ───────────────────────────────────────────
wire  [7:0] cmd_opcode    = cmd_bus[7:0];    // operation code
wire        gate_enable   = cmd_bus[8];       // 1 = filter by gate_set
wire  [7:0] gate_set      = cmd_bus[16:9];   // group select tag
wire  [1:0] preload_sel   = cmd_bus[18:17];  // transient preload constant
wire        shift_in_en   = cmd_bus[19];     // shift input before gate
wire        shift_out_en  = cmd_bus[20];     // shift output after gate
wire  [7:0] auth_token    = cmd_bus[28:21];  // auth token (matched vs stored mask)
// cmd_bus[31:29] spare — must be zero

// Shift amount from cmd_data (nibble count 0-7, used when shift_in/out_en set)
wire  [3:0] shift_nibbles = cmd_data[3:0];

// Gate filter: cell responds if gate_enable=0 (broadcast) OR gate_set matches
// cell's own group tag. group_tag is set at boot via CMD_BOOT_COMMIT.
// For iCEBreaker bring-up: gate_enable=0 always (broadcast), gate_set ignored.
reg   [7:0] group_tag = 8'h00;  // cell's group membership tag
wire        gate_match = !gate_enable || (gate_set == group_tag);


always @(posedge clk) begin
    if (rst) begin
        cmd_latch         <= 32'h0;
        input_address     <= CELL_ID[15:0];
        output_address    <= CELL_ID[15:0] + 1;
        data_reg          <= 32'h0;
        frozen            <= 1'b0;
        physical_mode     <= 1'b1;  // boot in physical mode
        output_set        <= 1'b0;  // no output until SET_OUTPUT_ADDR
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
        prev_data         <= 1'b0;
        odd_phase         <= 1'b0;
        bus_addr_r        <= 16'h0;
        bus_data_r        <= 32'h0;
        bus_valid_r       <= 1'b0;

    end else begin
        out_valid <= 1'b0;
        odd_phase <= ~odd_phase;
        if (ENABLE_LATCH_IN)
            armed_r <= !frozen && start_flag;

        // Pipeline bus inputs — 1 cycle latency, dramatically cuts fanout path
        bus_addr_r  <= bus_addr;
        bus_data_r  <= bus_data;
        bus_valid_r <= bus_valid;
        // Pre-register bus_hit for Kintex-7 fan-out prep.
        // bus_hit_r is available for high-fanout designs; iCEBreaker uses bus_hit directly.
        bus_hit_r   <= bus_hit;

        // ── Command bus ───────────────────────────────────────────────────────
        if (cmd_valid && gate_match) begin
            case (cmd_opcode)
                CMD_RECONFIGURE: begin
                    if (auth_ok) begin
                        cmd_latch[9:0]   <= cmd_data[9:0];    // topology
                        cmd_latch[10]    <= cmd_data[10];     // edge_mode
                        cmd_latch[18:11] <= cmd_data[30:23];  // auth_mask from cmd_data
                        cmd_latch[22]    <= cmd_data[11];     // start_flag
                        cmd_latch[20]    <= cmd_data[12];     // latch_A_dis
                        cmd_latch[21]    <= cmd_data[13];     // latch_B_dis
                        cmd_latch[24:23] <= cmd_data[15:14];  // dtype
                        cmd_latch[25]    <= cmd_data[16];     // invert_out
                        cmd_latch[26]    <= cmd_data[17];     // latch_in
                        cmd_latch[27]    <= cmd_data[18];     // priority
                        cmd_latch[28]    <= cmd_data[19];     // trace
                        cmd_latch[29]    <= cmd_data[20];     // breakpoint
                        cmd_latch[30]    <= cmd_data[21];     // one_shot
                        cmd_latch[31]    <= cmd_data[22];     // loop_back
                        frozen         <= 1'b0;
                        one_shot_fired <= 1'b0;
                        a_arrived      <= 1'b0;
                        output_set     <= 1'b1;
                    end
                end
                CMD_BOOT_COMMIT: begin
                    // BOOT STATE ONLY — no auth required (cell unconfigured)
                    // Accepts logical address + auth_mask, flips to RUN state.
                    // Ignored in RUN state (physical_mode already 0).
                    if (physical_mode) begin
                        input_address    <= cmd_data[15:0];   // logical address
                        cmd_latch[18:11] <= cmd_data[23:16];  // auth_mask
                        physical_mode    <= 1'b0;             // → RUN state
                        group_tag        <= cmd_data[31:24];  // group tag for gate_set
                    end
                end
                CMD_SET_INPUT_ADDR: begin
                    if (auth_ok) begin
                        input_address <= cmd_data[15:0];
                        out_buf_valid <= 1'b0;
                        out_valid     <= 1'b0;
                        a_arrived     <= 1'b0;
                        data_reg      <= 32'h0;
                    end
                end
                CMD_SET_OUTPUT_ADDR: begin
                    if (auth_ok) begin
                        output_address <= cmd_data[15:0];
                        output_set     <= 1'b1;
                        out_buf_valid  <= 1'b0;
                        out_valid      <= 1'b0;
                        a_arrived      <= 1'b0;
                        data_reg       <= 32'h0;
                    end
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
                CMD_LATCH_IN_ON: begin
                    if (auth_ok) cmd_latch[26] <= 1'b1;
                end
                CMD_LATCH_IN_OFF: begin
                    if (auth_ok) begin
                        cmd_latch[26] <= 1'b0;
                        a_arrived     <= 1'b0;
                    end
                end
                CMD_MEM_CALL: begin
                    if (auth_ok) begin
                        cmd_latch[26] <= 1'b1;
                        cmd_latch[30] <= 1'b1;
                        cmd_latch[22] <= 1'b1;
                        one_shot_fired <= 1'b0;
                        frozen        <= 1'b0;
                    end
                end
                CMD_REARM: begin
                    if (auth_ok) begin
                        cmd_latch[22] <= 1'b1;
                        one_shot_fired <= 1'b0;
                        a_arrived      <= 1'b0;
                        frozen         <= 1'b0;
                    end
                end
                CMD_SET_LOGICAL: begin
                    if (auth_ok) begin
                        input_address  <= cmd_data[15:0];
                        physical_mode  <= 1'b0;
                    end
                end
                CMD_CLEAR_ARRIVED: begin
                    if (auth_ok) begin
                        a_arrived <= 1'b0;
                        a_data    <= 32'h0;
                    end
                end
                CMD_RESET_CELL: begin
                    if (auth_ok) begin
                        a_arrived      <= 1'b0;
                        a_data         <= 32'h0;
                        one_shot_fired <= 1'b0;
                        cmd_latch[22]  <= 1'b1;
                        frozen         <= 1'b0;
                    end
                end
                CMD_SWAP_AB: begin
                    if (auth_ok) begin
                        a_data    <= {19'h0, cmd_data[12:0]};
                        a_arrived <= 1'b1;
                    end
                end
                CMD_SET_TOPO: begin
                    if (auth_ok) cmd_latch[9:0] <= cmd_data[9:0];
                end
                CMD_SET_INVERT: begin
                    if (auth_ok) cmd_latch[25] <= ~cmd_latch[25];
                end
                // Topology presets — single-input (latch_in=1 automatic)
                CMD_TOPO_PASS_A_COLD, CMD_TOPO_PASS_A: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h000; cmd_latch[26] <= 1'b1;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_NOT_A_COLD, CMD_TOPO_NOT_A: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h001; cmd_latch[26] <= 1'b1;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_NOR_COLD, CMD_TOPO_NOR: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h004; cmd_latch[26] <= 1'b0;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_AND_COLD, CMD_TOPO_AND: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h007; cmd_latch[26] <= 1'b0;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_OR_COLD, CMD_TOPO_OR: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h024; cmd_latch[26] <= 1'b0;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_NAND_COLD, CMD_TOPO_NAND: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h027; cmd_latch[26] <= 1'b0;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_PASS_B_COLD, CMD_TOPO_PASS_B: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h02C; cmd_latch[26] <= 1'b0;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_XNOR_COLD, CMD_TOPO_XNOR: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h03C; cmd_latch[26] <= 1'b0;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_XOR_COLD, CMD_TOPO_XOR: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h0BC; cmd_latch[26] <= 1'b0;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_ZERO_COLD, CMD_TOPO_ZERO: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h030; cmd_latch[26] <= 1'b1;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                CMD_TOPO_ONE_COLD, CMD_TOPO_ONE: begin
                    if (auth_ok) begin
                        cmd_latch[9:0] <= 10'h0B0; cmd_latch[26] <= 1'b1;
                        cmd_latch[22]  <= cmd_opcode[0];
                    end
                end
                default: ;
            endcase

            // ── preload_sel — transient, applied after opcode, if auth_ok ────
            // Loads a constant into a_data and arms a_arrived.
            // 01 = 0x00000000 (AND tree false side, NOR constant)
            // 10 = 0xFFFFFFFF (NOT/XOR/XNOR constant)
            // Independent of opcode — can accompany any command.
            if (auth_ok && preload_sel != 2'b00) begin
                a_data    <= (preload_sel == 2'b10) ? 32'hFFFFFFFF : 32'h00000000;
                a_arrived <= 1'b1;
            end
        end

        // ── Output buffer drain (odd_phase = negedge emulation) ───────────────
        if (odd_phase && out_buf_valid) begin
            out_addr      <= out_buf_addr;
            // Apply nibble mask if active — only affects stored data_reg update
            // Output itself is always full word (mask is a data manipulation tool)
            out_data      <= invert_out ? ~out_buf_data : out_buf_data;
            out_valid     <= 1'b1;
            out_buf_valid <= 1'b0;
        end

        // ── Data bus ─────────────────────────────────────────────────────────
        // EDGE mode: prev_data tracks last value, fires on transition
        // STANDARD mode: two arrivals — first loads a_data, second triggers
        if (bus_hit) prev_data <= bus_data_r[0];

        // First arrival store — STANDARD mode only, gated by latch_A_dis
        // latch_A_dis=1: skip storing — live bus_data flows as PASS(B) effect
        if (bus_hit && !a_arrived && !edge_mode && !latch_A_dis) begin
            a_data    <= bus_data_r;
            a_arrived <= 1'b1;
        end

        // Normal fire (two-arrival: a_arrived was set on first arrival)
        if (new_data) begin
            // data_reg stores unshifted computed_output for latch_in re-emission
            // and loop_back. Shift is a bus-side modifier only — internal state
            // always sees the raw gate tree output.
            data_reg      <= computed_output;
            out_buf_addr  <= {16'h0, output_address};
            out_buf_data  <= computed_shifted;  // shift_out applied here
            out_buf_valid <= 1'b1;
            if (latch_in) begin
                a_arrived <= 1'b1;          // stay armed — single arrival fires next time
                a_data    <= bus_data_r;     // update stored value to the new arrival
            end else begin
                a_arrived <= 1'b0;
            end
            if (loop_back)
                a_data <= computed_output;  // feed result back as next A input
            if (one_shot) begin
                one_shot_fired <= 1'b1;
                cmd_latch[22]  <= 1'b0;    // clear start_flag
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
