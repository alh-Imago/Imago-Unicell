// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// unicell.v — Imago UniCell — Single Cell Implementation
// Protocol v3.1 — unified 32-bit command bus, two-state boot/run model,
//                 command-emit cells (the fabric can command itself)
//
// v3.1: edge model REMOVED (latched two-arrival model is the only model). The freed
//   bit cmd_latch[10] now flags a command-emit cell (is_command_cell = cmd_latch[10]),
//   a single-bit tap that deletes the per-cell topology comparator. Set by opcode or
//   directly in the config word. (Shift reverted to a fixed-pattern ladder in v3.0.)
//
// v3.0 (major): COMMAND_EMIT cell type. A cell whose command_cell flag is set
//   drives its stored command word (a_data) onto the COMMAND bus, targeted
//   by output_address, instead of a gate result onto the data bus. This lets the
//   fabric issue its own commands — Shore and the tile system are built from cells,
//   so without it nothing in-fabric could command anything. The cell stays dumb: it
//   holds no program flow, the command content is assembled as DATA upstream, and
//   ordering is the fabric topology. Auth is the cell's own stored auth_mask.
//   Flagged by cmd_latch[10] (a single-bit tap, no comparator). Set via
//   CMD_TOPO_COMMAND_EMIT[_COLD] (0x47/0x46) or directly in the RECONFIGURE/ICM word.
//   Also v3.0: bit-granular shift (sub-nibble), group_tag on BOOT_COMMIT.
//
// TWO STATES:
//   BOOT state: cell exposes baked-in CELL_ID on address bus.
//               Boot controller finds cell by CELL_ID, sends logical address
//               + auth_mask in one transaction, then CMD_BOOT_COMMIT flips
//               cell to RUN state. physical_mode cleared permanently.
//   RUN  state: TWO match paths (v3 addressing split, verified in logic ~L559):
//               - addr_match   = (bus_addr == input_address): the MUTABLE LISTEN
//                 point (the "watching" address). Freely re-pointable; NOT identity.
//               - config_match = (bus_addr == CELL_ID): the PERMANENT IDENTITY.
//                 ALL config/reconfigure targets the cell by CELL_ID, never by the
//                 listen address. Identity is fixed; the listen point is mutable.
//               Command bus carries control + modifiers per transaction.
//
// Command bus (32-bit unified word — RUN state):
//   cmd_bus [31:0]:
//   ACTUAL layout referenced in v3 logic today (verified ~L592-600):
//     bits  7:0   opcode        — 8-bit operation code (256 opcodes)
//     bit   8      FREE          — (old gate_enable removed; group-filter gone)
//     bits 16:9    FREE          — (old gate_set removed; group-filter gone)
//     bit  18     arm            — transient; sets start_flag. (preload_sel REMOVED — collided)
//                                 01 = preload 0x00000000, 10 = 0xFFFFFFFF
//     bits 29:19  auth_token     — 11-bit (t_shift_in/out REMOVED — collided with auth)
//     (shift is now stored methodology via METH_SET_SHIFT_IN/OUT, not transient bus bits)
//     bits 28:21  auth_token    — 8-bit token, matched against stored auth_mask [63:53] (11-bit, upper latch)
//     bits 31:29  spare         — reserved, must be zero
//
//   PLANNED (spec settled in cmd_latch_64bit.md, NOT YET IMPLEMENTED): the two-slot
//   four-state encoding replaces the transient modifiers with two opcode slots:
//     [7:0] opcode A, [15:8] opcode B, [16] A_is_methodology, [17] B_to_methodology,
//     [18] arm, [29:19] auth_token (11-bit), [31:30] spare. Four states 00/01/10/11
//     (topology-only / topology+meth / meth-lower8 / meth-16bit). One-function guard:
//     a pass may name at most one FUNCTION (topology); methodologies compose. Auth
//     widens to 11 bits: stored = {cmd_latch[63:61], cmd_latch[18:11]}. See that note.
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
//   [10]    command_cell — 1 = this is a command-emit cell (was edge_mode; removed)
//   [18:11] FREED (auth_mask moved to upper [63:53]); reserved-zero
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
// NOTE: transient preload_sel/shift modifiers REMOVED (collided with arm/auth); use stored
//       methodology (METH_SET_*) and explicit opcodes instead of bus-bit side effects.
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
//                                cmd_data[23:16]=auth_mask to store in cmd_latch[18:11],
//                                cmd_data[31:24]=group_tag (gate-filter group for later
//                                partial-zone ops via gate_enable/gate_set).
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
//   0x12 CMD_SWAP_AB           — load a_data from cmd_data[12:0], set a_arrived. FIXED
//                                2026-07-05: now config_match+auth gated (was auth-only,
//                                broadcasting to every cell -- see the case handler).
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
//   0x46/47 CMD_TOPO_COMMAND_EMIT — sets cmd_latch[10] (emitter; 0x46 cold, 0x47 armed)
//   0x17 CMD_LOAD_AT           — opcode 23, listed above. EXTENDED this session: optional
//                                bank-2 methodology (cycle 1 of the 3-cycle load protocol =
//                                "topology + methodology 1"). Gated by cmd_bus[16] (valid) +
//                                cmd_bus[15:8] (methodology opcode), payload in cmd_data[30:23]
//                                (the one range LOAD_AT's own lower-latch payload never uses
//                                post-boot) -- NOT the same offset as CMD_SET_METHOD's slot B
//                                (cmd_data[23:16]), which was already fully claimed here.
//                                Only active when !physical_mode (boot's LOAD_AT keeps
//                                cmd_data[30:20] for auth; the loader's 3-cycle protocol runs
//                                post-boot, so this never collides in practice).
//   0x1B CMD_LOAD_DONE (27) — cycle-3 "I'm finished" marker of the fixed 3-cycle load
//                             protocol (config_match+auth gated, same as CMD_LOAD_AT).
//                             Emits ONE command-bus pulse (cmd_emit_bus/data/valid) at
//                             output_address (the push address) with bus bit 17 set =
//                             completion flag, opcode field = CMD_NOP. A loader's write-
//                             counter watches for (addr==push_address && cmd_emit_bus[17])
//                             to advance to the next cell. Independent of is_command_cell —
//                             every cell can confirm its own load, not just emitter cells.
//
// CMD_RECONFIGURE payload mapping (cmd_data[31:0] → cmd_latch):
//   cmd_data[9:0]   → topology
//   cmd_data[10]    → command_cell flag
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
module unicell64_v3 #(
    parameter CELL_ID        = 0,   // Unique cell identifier for debug only
    parameter ENABLE_LATCH_IN = 0   // 0 = disable latch_in feature (saves LCs + timing)
                                    // 1 = enable  latch_in (needed for Kintex-7 workloads)
) (
    input  wire        clk,         // System clock (rising edge)
    input  wire        rst,         // Synchronous reset (active high)

    // Command bus (configuration + control) — 32-bit unified word (v2.3)
    input  wire [31:0] cmd_bus,     // [7:0]=opcode [8]=target_en [16:9]=target_addr
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
    output reg  [3:0]  out_routing, // Snapshot of routing_mask at the moment of this fire --
                                    // which bridge directions (N/S/E/W) the zone wrapper should
                                    // also forward this fire to, beyond the local cluster.
    output reg         out_transit, // Snapshot of transit_only at this fire. 1 => this fire is
                                    // route-across-ONLY; the array must NOT present it on the
                                    // local cluster bus (only out_routing carries it onward).
                                    // 0 => normal: present locally (and route too if masked).

    // Command emit — a command cell (topology COMMAND_EMIT) drives its stored
    // command word (a_data) onto the COMMAND bus instead of the data bus, targeted
    // by output_address. Lets the fabric command itself: Shore/tiles become cells.
    output reg  [31:0] cmd_emit_bus,   // emitted cmd_bus word  (from a_data)
    output reg  [31:0] cmd_emit_data,  // emitted cmd_data word (target=output_address)
    output reg         cmd_emit_valid, // this cell emitted a command this cycle

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
localparam CMD_LOAD_AT          = 8'd23; // targeted reconfigure: addr_match-gated, target on the address lane, config in cmd_data, auth-verified. Per-cell heterogeneous config.
localparam CMD_LOAD_DONE        = 8'd27; // programming-cycle-3 completion marker: config_match+auth gated like
                                          // CMD_LOAD_AT. On receipt the cell EMITS a completion pulse on the
                                          // command bus (cmd_emit_*), targeted at its own output_address (the
                                          // "push address" set by the loader) with bus bit 17 set as the
                                          // completion flag. Lets a BRAM-driven loader's write-counter advance
                                          // on a real per-cell confirm instead of a fixed delay. See
                                          // sessions/latest.md "Programming protocol FINALISED".
localparam CMD_SET_METHOD       = 8'd25; // 64-bit two-slot four-state decoder (v3.1): slot A [7:0],
                                         // slot B [15:8], flags [16][17], arm [18]. See cmd_latch_64bit.md.
// Methodology sub-opcodes (carried in slot A when [16]=1, or slot B when [17]=1). Each is
// self-describing: the decoder maps it to the correct methodology field [51:32]. Auth [63:53]
// is NEVER touched by these. Payload (mask value / shift amount) rides the paired cmd_data half.
localparam METH_SET_MASK        = 8'd30; // nibble_mask[39:32] + mask_en[40]
localparam METH_SET_SHIFT_IN    = 8'd31; // shift_amt[46:41] + in_shift_en[47]
localparam METH_SET_SHIFT_OUT   = 8'd32; // shift_amt[46:41] + out_shift_en[48]
localparam METH_SET_LANE        = 8'd33; // lane_cut[51:49]
localparam METH_SET_TRANSIT     = 8'd35; // transit_only[15] -- 1 = route-across-only, do not
                                          // present on the local cluster bus (pure conduit).
                                          // The WHETHER-HERE half of the two-axis routing model
                                          // (routing_mask is the WHERE half). See cmd_latch[15].
localparam METH_SET_ROUTING     = 8'd34; // routing_mask[14:11] -- which bridge directions
                                          // (N/S/E/W, one bit each) this cell's OWN fire should
                                          // reach, in addition to its local cluster. Load-time
                                          // configured per cell (part of the ICM, via LOAD_AT's
                                          // bank-2 slot or CMD_SET_METHOD), NOT a synthesis-time
                                          // parameter -- the zone wrapper reads this per-fire
                                          // instead of a fixed N_ZONE/N_ACTIVE routing table, so
                                          // a model's routing is data it loads, not silicon it
                                          // needs resynthesized. A bitmask (not a single target)
                                          // gives genuine multicast: one fire can set N and E
                                          // together, reaching two neighbor clusters at once.
localparam METH_NONE            = 8'd0;  // no-op methodology slot
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
localparam CMD_TOPO_COMMAND_EMIT_COLD = 8'd70;  // sets cmd_latch[10] (command cell) armed=0
localparam CMD_TOPO_COMMAND_EMIT      = 8'd71;  // sets cmd_latch[10] (command cell) armed=1

// ── Command latch bit positions ────────────────────────────────────────────────
// cmd_latch[31:0] layout:
// [9:0]   topology   (NOR gate selection, one-hot)
// [10]    command_cell (1 = command-emit cell)
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
reg [63:0] cmd_latch     = 64'h0;   // 64-bit: lower 32 unchanged, upper 32 = methodology setup
reg [15:0] input_address  = CELL_ID[15:0];   // narrowed to 16 bits — preset to CELL_ID
reg [15:0] output_address = CELL_ID[15:0] + 1; // preset to CELL_ID+1
reg [31:0] data_reg       = 32'h0;
reg        frozen         = 1'b0;
reg        physical_mode  = 1'b1;  // 1=boot(physical ID), 0=run(logical addr)
reg        output_set     = 1'b0;  // 1=output address configured, cell may fire

// Convenience wires into cmd_latch fields
wire [9:0] topology   = cmd_latch[9:0];
// COMMAND_EMIT — a reserved topology code (well outside the gate-selection space
// 0x000..0x0BC). A cell with this topology is a command emitter: on fire it drives
// its stored command word (a_data) onto the command bus, targeted by output_address,
// instead of computing a gate result onto the data bus. The cell stays dumb — it
// holds no program flow; the command content is assembled as data upstream and the
// ordering is the fabric topology. Auth is the cell's own stored auth_mask.
// is_command_cell is a single-bit tap (cmd_latch[10]) — no comparator. Bit 10 sits
// directly above the 10-bit topology field: topology[9:0] wires to the gates, bit 10
// above says "or don't — you are a command cell". Set by opcode CMD_TOPO_COMMAND_EMIT
// or directly via the RECONFIGURE/ICM config word. (Was the edge_mode bit; the edge
// model has been removed — the latched two-arrival model is the only model now.)
wire is_command_cell = cmd_latch[10];
wire       start_flag = cmd_latch[22];
wire       invert_out = cmd_latch[25];  // invert computed output
wire       latch_in   = cmd_latch[26];  // hold a_arrived set — single arrival fires
wire       one_shot   = cmd_latch[30];  // fire once then disarm
wire       loop_back  = cmd_latch[31];  // feed computed output back to data_reg
wire       latch_A_dis = cmd_latch[20]; // disable A latch — live value flows through
wire       latch_B_dis = cmd_latch[21]; // disable B trigger — stored value rebroadcast
wire [1:0] dtype      = cmd_latch[24:23]; // NUMERIC/SIGNED/ALPHA/DATETIME
wire       priority_f = cmd_latch[27];  // high priority scheduling
wire       trace      = cmd_latch[28];  // log every fire to Ward
wire       breakpoint = cmd_latch[29];  // halt array on fire
wire [3:0] routing_mask = cmd_latch[14:11]; // N/S/E/W bridge directions this cell's fire also
                                             // reaches, beyond its local cluster (bit0=N,1=S,
                                             // 2=E,3=W by convention below). Set via
                                             // METH_SET_ROUTING; lives in the freed cmd_latch[18:11]
                                             // window.
wire       transit_only = cmd_latch[15];    // TRANSIT flag (2026-07-07). Two-axis model with
                                             // routing_mask: routing_mask = WHERE a fire goes
                                             // (which directions); transit_only = WHETHER the
                                             // LOCAL cluster is included.
                                             //   0 (default) = data is FOR HERE: present on the
                                             //     local cluster bus as normal, AND also route
                                             //     across per routing_mask if any bits set
                                             //     (the both-local-and-across working-cell case).
                                             //   1 = data is ONLY passing through: route across
                                             //     per routing_mask, do NOT present locally. A
                                             //     pure conduit (transit/routing-hub cell).
                                             // Set via METH_SET_TRANSIT. Lives at cmd_latch[15],
                                             // in the freed [18:11] window ([18:16] still free).

// ── 64-bit upper half: methodology setup (shift + nibble mask moved off the bus) ──
// Layout per docs/design-notes/cmd_latch_64bit.md. These were transient cmd_bus
// modifiers in the 32-bit cell; here they are STORED, so a configured cell fires on
// a bare trigger with no per-fire modifier stream. 17 of 32 upper bits used.
wire [7:0] m_nibble_mask = cmd_latch[39:32]; // per-nibble BLOCK(1)/PASS(0) on the input operand
wire       m_mask_en     = cmd_latch[40];    // 1 = nibble mask active
wire [5:0] m_shift_amt   = cmd_latch[46:41]; // 0..31 bits ([44:41]=nibble*4, [46:45]=sub-nibble)
wire       m_in_shift_en = cmd_latch[47];    // shift input LEFT  by m_shift_amt before the gate
wire       m_out_shift_en= cmd_latch[48];    // shift result RIGHT by m_shift_amt after the gate

reg        out_buf_valid   = 1'b0;
reg [31:0] out_buf_data    = 32'h0;
reg [31:0] out_buf_addr    = 32'h0;
// command-emit buffer (mirrors out_buf, but drains to the command-emit outputs)
reg        cmd_emit_buf_valid = 1'b0;
reg [31:0] cmd_emit_buf_bus   = 32'h0;
reg [31:0] cmd_emit_buf_data  = 32'h0;

// Pipeline registers for bus inputs — breaks high-fanout routing path
// bus_addr/bus_data/bus_valid fan out to all cells; registering inside
// each cell cuts the combinatorial path at the cost of 1 cycle latency.
reg [15:0] bus_addr_r  = 16'h0;
reg [31:0] bus_data_r  = 32'h0;
reg        bus_valid_r = 1'b0;
reg        one_shot_fired  = 1'b0;

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
// Debug bank select (v3.1): a 1-bit bank chooses which HALF of the 64-bit cmd_latch the
// 32-bit dbg_cmd_latch port exposes — 0 = lower [31:0], 1 = upper [63:32]. Set via opcode 26
// from cmd_data[16]. REGISTERED output so ISSP samples a STABLE value (combinational mux off a
// live latch can be caught mid-transition by the async probe snapshot). Host reads bank0, flips
// to bank1, reads upper half (methodology [51:32] + auth [63:53]). Sideways-ROM-style banking.
reg dbg_bank = 1'b0;
reg [31:0] dbg_cmd_latch_r = 32'h0;
always @(posedge clk) begin
    if (rst) begin
        dbg_bank <= 1'b0;
        dbg_cmd_latch_r <= 32'h0;
    end else begin
        if (cmd_valid && (cmd_bus[7:0] == 8'd26)) dbg_bank <= cmd_data[16];
        dbg_cmd_latch_r <= dbg_bank ? cmd_latch[63:32] : cmd_latch[31:0]; // registered banked window
    end
end
assign dbg_cmd_latch = dbg_cmd_latch_r;
// NOTE (ICM format, evolving): auth_mask now lives at cmd_latch[63:53] (upper half). ICM
// serialisation must zero auth in the UPPER half now, not [18:11]. Lower [18:11] is freed.
// Upper-half ICM exposure + auth-zero lands with the wall-cell ICM format work.
assign dbg_input_addr       = {16'h0, input_address};
assign dbg_input_addr_short = input_address;
assign dbg_output_addr = {16'h0, output_address};
assign dbg_start_flag  = start_flag;
assign dbg_armed       = start_flag;  // NOTE: start_flag only, not fire-readiness.
                                      // Real fire needs !frozen && start_flag &&
                                      // output_set && bus_valid_r && addr_match.
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

// shift_in_en  (cmd_bus[19]): shift bus_data LEFT  by shift_amt bits before gate
// shift_out_en (cmd_bus[20]): shift computed_output RIGHT by shift_amt bits on emit
// shift_amt = cmd_data[3:0]*4 + cmd_data[5:4] (0..31 bits). [5:4]=0 == old nibble
// encoding. Barrel shift — purely combinational, no state, fresh each transaction.
// Only applied when bus_hit is true (gate tree live).

wire [31:0] bus_data_shifted;
// Fixed-pattern shift: a constant shift is pure rewiring (zero logic), selected
// by the loaded shift amount — a small mux, NOT a variable barrel shifter. Set is
// the nibble multiples (4..28) plus sub-nibble 1 and 2 (the spans the packed
// Kogge-Stone adder needs). Unsupported amounts pass through unshifted.
assign bus_data_shifted = !shift_in_en      ? bus_data_r :
                          (shift_amt==5'd1)  ? {bus_data_r[30:0],  1'h0} :
                          (shift_amt==5'd2)  ? {bus_data_r[29:0],  2'h0} :
                          (shift_amt==5'd4)  ? {bus_data_r[27:0],  4'h0} :
                          (shift_amt==5'd8)  ? {bus_data_r[23:0],  8'h0} :
                          (shift_amt==5'd12) ? {bus_data_r[19:0], 12'h0} :
                          (shift_amt==5'd16) ? {bus_data_r[15:0], 16'h0} :
                          (shift_amt==5'd20) ? {bus_data_r[11:0], 20'h0} :
                          (shift_amt==5'd24) ? {bus_data_r[7:0],  24'h0} :
                          (shift_amt==5'd28) ? {bus_data_r[3:0],  28'h0} :
                          bus_data_r;  // unsupported amount: no shift

// ── Stored nibble mask: per-nibble BLOCK(1)/PASS(0), applied AFTER shift, before gate ──
// 64-bit cut (cmd_latch[40] mask_en, [39:32] nibble_mask). Pure rewiring + per-nibble
// AND — cheap. When disabled the operand passes through untouched (32-bit behaviour).
wire [31:0] nibble_keep = {{4{~m_nibble_mask[7]}},{4{~m_nibble_mask[6]}},
                           {4{~m_nibble_mask[5]}},{4{~m_nibble_mask[4]}},
                           {4{~m_nibble_mask[3]}},{4{~m_nibble_mask[2]}},
                           {4{~m_nibble_mask[1]}},{4{~m_nibble_mask[0]}}};
wire [31:0] bus_data_masked = m_mask_en ? (bus_data_shifted & nibble_keep) : bus_data_shifted;

wire [31:0] input_val = (bus_valid_r && !cmd_valid && addr_match && start_flag && !frozen && output_set)
                 ? (a_arrived ? a_data : bus_data_masked)   // latched: a_data, else shifted+masked live
                 : data_reg;

// 32-bit NOR gate tree — each gate operates bitwise across the full word.
// Topology selects which gate's output becomes computed_output.
// The two-arrival model: A is stored in a_data (first arrival),
// B is the trigger value (second arrival, live on bus_data when new_data fires).
// For binary ops: input_val carries A (stored), second_val carries B (trigger).
// For single-input ops (NOT, PASS): compiler sends same value twice so A==B.

wire [31:0] second_val = (bus_valid_r && !cmd_valid && addr_match && start_flag && !frozen && output_set)
                 ? bus_data_masked  // B = shifted+masked bus value (trigger, second arrival)
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

// shift_out: right-shift computed_output by shift_amt bits before emit.
// Applied only when shift_out_en=1 (cmd_bus[20]) and bus_hit is true.
wire [31:0] computed_shifted;
assign computed_shifted = !shift_out_en     ? computed_output :
                          (shift_amt==5'd1)  ? { 1'h0, computed_output[31: 1]} :
                          (shift_amt==5'd2)  ? { 2'h0, computed_output[31: 2]} :
                          (shift_amt==5'd4)  ? { 4'h0, computed_output[31: 4]} :
                          (shift_amt==5'd8)  ? { 8'h0, computed_output[31: 8]} :
                          (shift_amt==5'd12) ? {12'h0, computed_output[31:12]} :
                          (shift_amt==5'd16) ? {16'h0, computed_output[31:16]} :
                          (shift_amt==5'd20) ? {20'h0, computed_output[31:20]} :
                          (shift_amt==5'd24) ? {24'h0, computed_output[31:24]} :
                          (shift_amt==5'd28) ? {28'h0, computed_output[31:28]} :
                          computed_output;  // unsupported amount: no shift

// ── LANE-aware out-shift: breakable byte boundaries on the result ─────────────
// m_lane_cut[2:0] = cut bits for the 3 inter-byte boundaries (bit8/bit16/bit24).
//   0 = boundary connected (bits cross normally), 1 = boundary cut (bits drop).
// All cuts 0 (default / reserved-zero) -> lane_kill = all ones -> computed_lane ==
// computed_shifted, BIT-IDENTICAL to the proven 32-bit out-shift (regression-safe).
// A cut boundary zeros the bits that crossed it: under a right-shift by s, bits that
// moved from >=B to <B land at positions [B-s, B-1]; an active cut zeros that window.
// Depth: the existing shifter + ONE final AND (the kill-mask is parallel, not in
// series with the shift). This is the "4 shifters with breakable boundaries, shared
// shift amount" model — chunked shifting + lane truncation in one stage, flat depth.
wire [2:0] m_lane_cut = cmd_latch[51:49];      // reserved-zero until used
wire [6:0] lane_s     = {1'b0, shift_amt};      // shift amount (zero-extended)
wire [63:0] lane_ones = (64'd1 << lane_s) - 64'd1;
wire [31:0] lane_win8  = m_lane_cut[0] ? ((lane_ones << 8 ) >> lane_s) : 32'd0;
wire [31:0] lane_win16 = m_lane_cut[1] ? ((lane_ones << 16) >> lane_s) : 32'd0;
wire [31:0] lane_win24 = m_lane_cut[2] ? ((lane_ones << 24) >> lane_s) : 32'd0;
wire [31:0] lane_kill  = ~(lane_win8 | lane_win16 | lane_win24);
wire [31:0] computed_lane = computed_shifted & lane_kill;

// Firing condition wires — parallel, not chained ────────────────────────────
// All cells use latch-then-fire by default:
//   First arrival  → stored in a_data, a_arrived set, no output
//   Second arrival → fires using a_data, a_arrived cleared
// Command bus operations bypass this — they go directly to target latches.
// cmd_latch[10] = command_cell flag (was edge_mode; edge model removed).
// In physical_mode cell only responds to its physical CELL_ID on the bus.
// After CMD_SET_LOGICAL, cell responds to logical input_address only.
// output_set must be 1 before cell can fire — prevents bus pollution during boot.
// v3 ADDRESSING SPLIT: data and config match on DIFFERENT keys, NO physical/logical mode.
//  - addr_match (DATA): ALWAYS the mutable LISTEN address (input_address). It DEFAULTS to
//    CELL_ID, so a cell listens on its identity until SET_INPUT_ADDR points it elsewhere.
//    No physical_mode flip — data always keys on input_address.
//  - config_match (CONFIG): the cell's PERMANENT IDENTITY (CELL_ID). Config always targets the
//    identity, never the mutable listen. So changing the listen never moves where config lands,
//    and two cells sharing a listen are still individually configurable — fusion impossible.
wire addr_match   = (bus_addr_r == input_address);
wire config_match = (bus_addr_r == CELL_ID[15:0]);
// bus_hit includes !cmd_valid: commands and data are time-MULTIPLEXED, never
// concurrent. A command broadcast in the same cycle as a data event suppresses the
// fire — this is part of the programming model, not an accident. Emitted commands
// (from COMMAND_EMIT cells) ride the same command bus and so obey the same rule.
wire bus_hit  = !frozen && start_flag && output_set && bus_valid_r && !cmd_valid
                && addr_match;

// Pre-registered bus_hit — breaks high-fanout path for Kintex-7 timing.
// On iCEBreaker, bus_hit is used directly (1-cycle lower latency).
// For Kintex-7 implementation: replace bus_hit references with bus_hit_r
// and add one cycle to KS_DEPTH in run_int32_function.
reg bus_hit_r = 1'b0;

wire new_data = !(one_shot && one_shot_fired)
                && (bus_hit && a_arrived);   // latched: fire on the second arrival

// latch_reemit is registered — computed at end of cycle N, used at cycle N+1.
// This keeps it off the CEN path of out_buf_addr FFs (CEN has tight setup on iCE40).
// One cycle latency is acceptable — latch_in re-emission is not time-critical.
reg latch_reemit = 1'b0;

// ── Auth check — combinational ────────────────────────────────────────────────
// auth_mask stored in cmd_latch[63:53] (11-bit, upper latch). Token arrives in cmd_bus[29:19].
// Boot bypass: if stored mask is all zeros, CMD_BOOT_COMMIT accepted
// unconditionally (cell not yet configured). After that, silent reject on mismatch.
// CMD_BOOT_COMMIT (0x07) is exempt from auth — cell has no auth_mask yet.
// v3.1: auth widened to 11 bits and the STORED mask MOVED as one contiguous lump
// into the upper methodology latch [63:53], freeing lower latch [18:11] (now reserved).
// (The bus TOKEN must stay on the command bus to arrive — only storage relocated.)
wire  [10:0] auth_mask   = cmd_latch[63:53];
wire         auth_boot   = (auth_mask == 11'h0);
wire         auth_ok     = auth_boot || (auth_token == auth_mask);
// cmd_latch[18:11] — FREED (was 8-bit auth_mask); reserved-zero, held for future use.

// ── Command bus field decode (v2.3) ───────────────────────────────────────────
wire  [7:0] cmd_opcode    = cmd_bus[7:0];    // operation code
// Command targeting is by config_match on CELL_ID inside each cell; the ARRAY simply
// broadcasts the command word to all cells (verified: array references only cmd_bus[7:0]
// + the broadcast). The OLD per-cell target_en[8]/target_addr[16:9] was DROPPED several
// versions ago — bits 8 and 16:9 are GENUINELY FREE (available for slot B [15:8] of the
// planned two-slot encoding).
// Transient modifier wires REMOVED (preload_sel[18:17], t_shift_in_en[19], t_shift_out_en[20]):
// they overlapped arm[18] and auth_token[29:19], causing silent shift/preload side effects on
// auth-carrying and arm commands. Superseded by the two-slot decoder (stored methodology). Bits
// [17] and [30:31] are spare; [18]=arm; [29:19]=auth_token.
wire  [10:0] auth_token   = cmd_bus[29:19];  // STAGE 1: 11-bit token position (Stage 2 two-slot
// decoder retires the transient preload_sel[18:17]/t_shift[19:20] that nominally overlap here;
// for Stage-1 auth-relocation testing, auth transactions do not also carry transient modifiers,
// so the 11-bit read is clean on auth-gated commands. Full retirement lands in Stage 2.
// cmd_bus[31:30] spare — must be zero

// Shift amount from cmd_data (nibble count 0-7, used when shift_in/out_en set)
wire  [3:0] shift_nibbles = cmd_data[3:0];
// Bit-granular shift amount: nibbles*4 + sub-nibble remainder in cmd_data[5:4].
wire  [4:0] t_shift_amt = {shift_nibbles, 2'b00} + {3'b0, cmd_data[5:4]};

// ── Effective shift = STORED (methodology latch) OR TRANSIENT (bus) ───────────────
// 64-bit cut: a configured cell fires on a bare trigger using its STORED shift; the
// transient bus path still works (host-driven), so nothing the 32-bit cell did breaks.
// Stored takes precedence when its enable is set.
// Shift enables come ONLY from stored methodology (METH_SET_SHIFT_IN/OUT). The old transient
// t_shift_in_en(bus19)/t_shift_out_en(bus20) are REMOVED: they collided with auth_token[29:19]
// (token bit0=bus19, bit1=bus20), so any auth token with those bits set silently forced a shift.
// The two-slot decoder replaced transient shift with stored methodology — retirement completed here.
wire        shift_in_en  = m_in_shift_en;
wire        shift_out_en = m_out_shift_en;
wire  [4:0] shift_amt    = m_in_shift_en  ? m_shift_amt[4:0]
                         : m_out_shift_en ? m_shift_amt[4:0]
                         : t_shift_amt;

// (gate filter removed — see note above; targeting is array-side)


always @(posedge clk) begin
    if (rst) begin
        cmd_latch         <= 64'h0;
        input_address     <= CELL_ID[15:0];
        output_address    <= CELL_ID[15:0] + 1;
        data_reg          <= 32'h0;
        frozen            <= 1'b0;
        physical_mode     <= 1'b1;  // boot in physical mode
        output_set        <= 1'b0;  // no output until SET_OUTPUT_ADDR
        out_valid         <= 1'b0;
        out_data          <= 32'h0;
        out_addr          <= 32'h0;
        out_routing       <= 4'h0;
        out_transit       <= 1'b0;
        out_buf_valid     <= 1'b0;
        out_buf_data      <= 32'h0;
        out_buf_addr      <= 32'h0;
        cmd_emit_valid     <= 1'b0;
        cmd_emit_bus       <= 32'h0;
        cmd_emit_data      <= 32'h0;
        cmd_emit_buf_valid <= 1'b0;
        cmd_emit_buf_bus   <= 32'h0;
        cmd_emit_buf_data  <= 32'h0;
        one_shot_fired    <= 1'b0;
        a_arrived         <= 1'b0;
        a_data            <= 32'h0;
        latch_reemit      <= 1'b0;
        armed_r           <= 1'b0;
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
        if (cmd_valid) begin   // array already address-gated this
            case (cmd_opcode)
                CMD_RECONFIGURE: begin
                    if (auth_ok) begin
                        cmd_latch[9:0]   <= cmd_data[9:0];    // topology
                        cmd_latch[10]    <= cmd_data[10];     // command_cell flag (direct write)
                        // auth_mask is written ONLY in boot (physical_mode) — same as
                        // CMD_LOAD_AT. After boot the data-path route to auth is closed:
                        // post-boot, opcodes may change a cell's FUNCTION but never its
                        // auth (invariant clause 3 — write-once, boot-only auth).
                        if (physical_mode)
                            cmd_latch[63:53] <= cmd_data[30:20];  // 11-bit auth_mask -> upper latch (boot-only)
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
                CMD_LOAD_AT: begin
                    // Targeted reconfigure (Alan's address-lane model): the cell's
                    // OWN address comparator gates this. Target rides the address
                    // lane (bus_addr -> addr_match); config rides cmd_data; auth in
                    // cmd_bus. Only the addressed cell applies it — per-cell
                    // heterogeneous config without cramming an address into the
                    // command word. auth_mask is written ONLY in boot (physical_mode):
                    // after boot the data-path route to auth is closed (security).
                    if (config_match && auth_ok) begin
                        cmd_latch[9:0]   <= cmd_data[9:0];    // topology
                        cmd_latch[10]    <= cmd_data[10];     // command_cell flag
                        if (physical_mode)
                            cmd_latch[63:53] <= cmd_data[30:20]; // 11-bit auth_mask -> upper latch (boot-only)
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

                        // ── CYCLE 1 extension: optional bank-2 methodology ("topology +
                        // methodology 1") — sessions/latest.md "Programming protocol
                        // FINALISED". cmd_data[22:0] is fully claimed by the lower-latch
                        // payload above (and [30:20] doubles for boot auth), so this rides
                        // the ONE range LOAD_AT never touches post-boot: cmd_data[30:23]
                        // (8 bits, right-aligned per methodology, mirrors SET_METHOD's own
                        // slot-B convention just at a different offset forced by the
                        // narrower budget). Only valid when NOT physical_mode (boot's
                        // LOAD_AT keeps [30:20] for auth; the loader's 3-cycle protocol
                        // runs post-boot, so this never collides in practice). Gated by
                        // cmd_bus[16] (bank-2 valid) + cmd_bus[15:8] (bank-2 opcode) —
                        // same convention as CMD_SET_METHOD's slot B. Only methodology
                        // opcodes accepted (one-function guard, same as SET_METHOD).
                        if (cmd_bus[16] && !physical_mode) begin
                            case (cmd_bus[15:8])
                                METH_SET_MASK:      begin cmd_latch[39:32] <= cmd_data[30:23]; cmd_latch[40] <= 1'b1; end
                                METH_SET_SHIFT_IN:  begin cmd_latch[46:41] <= cmd_data[28:23]; cmd_latch[47] <= 1'b1; end
                                METH_SET_SHIFT_OUT: begin cmd_latch[46:41] <= cmd_data[28:23]; cmd_latch[48] <= 1'b1; end
                                METH_SET_LANE:      cmd_latch[51:49] <= cmd_data[25:23];
                                METH_SET_ROUTING:    cmd_latch[14:11] <= cmd_data[26:23];
                                METH_SET_TRANSIT:    cmd_latch[15]    <= cmd_data[23];
                                default: ; // non-methodology in bank 2 REFUSED: no-op (one-function guard)
                            endcase
                        end
                    end
                end
                CMD_LOAD_DONE: begin
                    // Cycle-3 completion marker of the fixed 3-cycle load protocol
                    // (sessions/latest.md, "Programming protocol FINALISED"). Same
                    // gate as CMD_LOAD_AT: config_match on this cell's permanent
                    // CELL_ID + auth. On receipt, confirm completion by EMITTING a
                    // pulse on the command bus — NOT the is_command_cell/topology
                    // path (that needs a two-arrival data fire and only exists for
                    // emitter-typed cells); this is a dedicated, always-available
                    // confirm every cell has regardless of its configured topology.
                    // Target = output_address (the "push address" — pre-set by the
                    // loader via SET_TARGET+SET_OUTPUT_ADDR to point at the write-
                    // counter's listen address). Completion flag = cmd_bus[17], the
                    // verified-free bus bit; opcode field is CMD_NOP so a receiver
                    // that only checks bit 17 (not opcode) sees a clean confirm.
                    // Bit 52 (free upper-latch bit) records "load confirmed" for
                    // debug readback via the existing dbg_bank/dbg_cmd_latch path —
                    // internal bookkeeping only, not part of the wire protocol.
                    if (config_match && auth_ok) begin
                        cmd_latch[52]      <= 1'b1;
                        cmd_emit_buf_bus   <= 32'h00020000; // bit17=1 (completion flag), opcode=CMD_NOP
                        cmd_emit_buf_data  <= {16'h0, output_address}; // push address
                        cmd_emit_buf_valid <= 1'b1;
                    end
                end
                CMD_BOOT_COMMIT: begin
                    // BOOT STATE ONLY — no auth required (cell unconfigured)
                    // Accepts logical address + auth_mask, flips to RUN state.
                    // Ignored in RUN state (physical_mode already 0).
                    if (physical_mode) begin
                        input_address    <= cmd_data[15:0];   // logical address
                        cmd_latch[63:53] <= {3'b0, cmd_data[23:16]};  // auth_mask -> upper latch (8 low bits;
                                                              // upper 3 auth bits default 0 here, set via LOAD_AT if needed)
                        physical_mode    <= 1'b0;             // → RUN state
                    end
                end
                // Methodology opcodes are TOP-LEVEL and SELF-DESCRIBING (collapsed encoding
                // v3.1): slot A = cmd_bus[7:0] IS the opcode (no SET_METHOD wrapper — that
                // removes the slot-A/selector collision). Each writes its own field [51:32];
                // never touches auth [63:53] or topology. Slot B [15:8] = optional SECOND
                // methodology, decoded only when B_valid ([16])=1. arm ([18]) is a transient
                // that arms the cell on the completing pass. GUARD: slot B may carry ONLY a
                // methodology op — a topology op in B is refused (one-function invariant).
                METH_SET_MASK, METH_SET_SHIFT_IN, METH_SET_SHIFT_OUT, METH_SET_LANE, METH_SET_ROUTING, METH_SET_TRANSIT: begin
                    if (config_match && auth_ok) begin
                        // --- slot A: apply the primary methodology (self-describing opcode) ---
                        case (cmd_opcode)
                            METH_SET_MASK:      begin cmd_latch[39:32] <= cmd_data[7:0]; cmd_latch[40] <= 1'b1; end
                            METH_SET_SHIFT_IN:  begin cmd_latch[46:41] <= cmd_data[5:0]; cmd_latch[47] <= 1'b1; end
                            METH_SET_SHIFT_OUT: begin cmd_latch[46:41] <= cmd_data[5:0]; cmd_latch[48] <= 1'b1; end
                            METH_SET_LANE:      cmd_latch[51:49] <= cmd_data[2:0];
                            METH_SET_ROUTING:    cmd_latch[14:11] <= cmd_data[3:0];
                            METH_SET_TRANSIT:    cmd_latch[15]    <= cmd_data[0];
                        endcase
                        // --- slot B: optional second methodology, gated by B_valid [16] ---
                        // GUARD: only methodology opcodes accepted in B; anything else = no-op.
                        if (cmd_bus[16]) begin
                            case (cmd_bus[15:8])
                                METH_SET_MASK:      begin cmd_latch[39:32] <= cmd_data[23:16]; cmd_latch[40] <= 1'b1; end
                                METH_SET_SHIFT_IN:  begin cmd_latch[46:41] <= cmd_data[21:16]; cmd_latch[47] <= 1'b1; end
                                METH_SET_SHIFT_OUT: begin cmd_latch[46:41] <= cmd_data[21:16]; cmd_latch[48] <= 1'b1; end
                                METH_SET_LANE:      cmd_latch[51:49] <= cmd_data[18:16];
                                METH_SET_ROUTING:    cmd_latch[14:11] <= cmd_data[19:16];
                                METH_SET_TRANSIT:    cmd_latch[15]    <= cmd_data[16];
                                default: ; // non-methodology in B (incl. topology) REFUSED: no-op
                            endcase
                        end
                        // --- arm [18]: transient, arm on the completing pass ---
                        if (cmd_bus[18]) begin
                            cmd_latch[22] <= 1'b1;   // start_flag = armed
                            output_set    <= 1'b1;
                        end
                    end
                end
                CMD_SET_INPUT_ADDR: begin
                    // Option A: addr_match-gated like CMD_LOAD_AT — target rides the
                    // address lane (held by SET_TARGET), the new address value rides
                    // cmd_data. One comparator gates everything (invariant clause 1/4).
                    if (config_match && auth_ok) begin
                        input_address <= cmd_data[15:0];
                        out_buf_valid <= 1'b0;
                        out_valid     <= 1'b0;
                        a_arrived     <= 1'b0;
                        data_reg      <= 32'h0;
                    end
                end
                CMD_SET_OUTPUT_ADDR: begin
                    if (config_match && auth_ok) begin
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
                    // FIXED (session of 2026-07-05, building the 45-cell packed
                    // adder): this opcode previously had NO address gating at
                    // all -- just auth_ok, no config_match -- meaning it
                    // broadcast to EVERY cell in the array simultaneously,
                    // not just whichever cell SET_TARGET held on the address
                    // lane. That's inconsistent with every other per-cell
                    // config opcode (LOAD_AT, SET_INPUT_ADDR, SET_OUTPUT_ADDR,
                    // LOAD_DONE all check config_match) and broke a priming
                    // pass that assumed CMD_SWAP_AB was targetable the same
                    // way -- every cell got spuriously pre-armed (a_arrived=1)
                    // during priming, not just the intended relay cells.
                    // config_match added to match the addressing invariant
                    // ("one comparator gates everything").
                    if (config_match && auth_ok) begin
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
                // COMMAND_EMIT: turn this cell into a command emitter. On fire it
                // drives a_data->cmd_bus and output_address->cmd_data instead of a
                // gate result onto the data bus. _COLD loads disarmed; armed = LSB.
                // COMMAND_EMIT: set the command-cell flag (bit 10). No topology
                // comparator — the cell taps cmd_latch[10] directly. _COLD loads
                // disarmed; armed = opcode LSB.
                CMD_TOPO_COMMAND_EMIT_COLD, CMD_TOPO_COMMAND_EMIT: begin
                    if (auth_ok) begin
                        cmd_latch[10] <= 1'b1;             // command-cell flag
                        cmd_latch[26] <= 1'b0;             // no latch_in re-emit
                        cmd_latch[22] <= cmd_opcode[0];    // armed = opcode LSB
                    end
                end
                default: ;
            endcase

            // ── transient preload_sel REMOVED ──────────────────────────────
            // The old preload_sel=cmd_bus[18:17] collided with the arm bit (bus[18]):
            // arming a cell set preload_sel[1], triggering a preload that overwrote a_data
            // with 0xFFFFFFFF. Preload is deprecated (CMD_PRELOAD); the transient path is
            // retired. If a constant is needed, use an explicit opcode, not a bus-bit side effect.
        end

        // ── Output buffer drain (odd_phase = negedge emulation) ───────────────
        if (odd_phase && out_buf_valid) begin
            out_addr      <= out_buf_addr;
            // Apply nibble mask if active — only affects stored data_reg update
            // Output itself is always full word (mask is a data manipulation tool)
            out_data      <= invert_out ? ~out_buf_data : out_buf_data;
            out_valid     <= 1'b1;
            out_routing   <= routing_mask; // snapshot at fire time -- zone wrapper reads this
            out_transit   <= transit_only; // snapshot: array suppresses local presentation if 1
            out_buf_valid <= 1'b0;
        end

        // ── Command-emit buffer drain — drives the command bus ────────────────
        if (odd_phase && cmd_emit_buf_valid) begin
            cmd_emit_bus       <= cmd_emit_buf_bus;
            cmd_emit_data      <= cmd_emit_buf_data;
            cmd_emit_valid     <= 1'b1;
            cmd_emit_buf_valid <= 1'b0;
        end else begin
            cmd_emit_valid <= 1'b0;
        end

        // ── Data bus ─────────────────────────────────────────────────────────
        // Latched two-arrival model: first arrival loads a_data, second triggers.

        // First arrival store — gated by latch_A_dis
        // latch_A_dis=1: skip storing — live bus_data flows as PASS(B) effect
        if (bus_hit && !a_arrived && !latch_A_dis) begin
            a_data    <= bus_data_r;
            a_arrived <= 1'b1;
        end

        // Normal fire (two-arrival: a_arrived was set on first arrival)
        if (new_data) begin
            // data_reg stores unshifted computed_output for latch_in re-emission
            // and loop_back. Shift is a bus-side modifier only — internal state
            // always sees the raw gate tree output.
            data_reg      <= computed_output;
            if (is_command_cell) begin
                // EMIT: drive the stored command word onto the command bus,
                // targeted by output_address. The second arrival (B) is the
                // trigger only — its value is ignored. No data-bus output.
                // SECURITY: a_data is only writable under auth_ok (first-arrival
                // store requires bus_hit, which requires the cell be armed/authed;
                // any future raw-write-to-a_data opcode MUST stay auth-guarded).
                cmd_emit_buf_bus   <= a_data;                   // command word
                cmd_emit_buf_data  <= {16'h0, output_address};  // target cell
                cmd_emit_buf_valid <= 1'b1;
            end else begin
                out_buf_addr  <= {16'h0, output_address};
                out_buf_data  <= computed_lane;  // out-shift + lane truncation here
                out_buf_valid <= 1'b1;
            end
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
