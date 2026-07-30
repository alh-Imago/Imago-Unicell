// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
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

module unicell_array64_v3 #(
    parameter NUM_CELLS = 32,   // 32 for safe iCEBreaker bring-up
    parameter CELL_BASE = 0,    // global flat offset of this block's cells
    parameter DEBUG_SELECT = 0  // 1 = per-cell debug readback mux (DEV builds, area-costly);
                                // 0 = hardwire dbg0_* to cell 0 (PRODUCTION, lean + fast fit)
                                // (ZONE_ID*NUM_CELLS) — physical CELL_ID is a
                                // single flat address point per the architecture
                                // doc (block boundary = bus boundary); zones are
                                // physical routing only, not an address level.
) (
    input  wire        clk,
    input  wire        rst,

    // Command bus — broadcast to all cells
    input  wire [31:0] cmd_bus,
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
    output reg  [3:0]  out_routing,   // routing_mask of whichever cell's fire won this cycle --
                                      // ties to the SAME cell as out_addr (not OR'd across
                                      // simultaneous firers, since routing is cell-identity-tied)
    output reg         out_transit,   // transit flag of the winning cell -- 1 = this outbound
                                      // fire was route-only (suppressed on the local bus).
                                      // Exposed so the zone wrapper can see it if needed; the
                                      // local-bus suppression itself happens inside this module.
    // Local cluster bus, exposed for observation (2026-07-08). This is the signal
    // the transit flag SUPPRESSES -- distinct from out_valid (the outbound path,
    // which always fires so the value can reach the bridges). Watching bus_valid
    // is the only direct way to prove a transit fire left the local bus untouched.
    output wire        obs_bus_valid,
    output wire [15:0] obs_bus_addr,
    output wire [31:0] obs_bus_data,

    // Status
    output wire [15:0] armed_count,
    output wire [15:0] arrived_count,
    output wire [15:0] output_set_count,
    output wire [15:0] emit_count,          // command-emit events (v3.0)
    output wire [31:0] dbg0_cmd_latch,
    output wire [31:0] dbg0_input_addr,
    output wire [31:0] dbg0_output_addr,
    output wire [31:0] dbg0_a_data,
    output wire [31:0] cycle_count
);

// ── Internal bus — registered ─────────────────────────────────────────────────
// bus_addr/bus_data/bus_valid are registered one cycle.
// Two arrivals always required — NOR(A,B) model.
// NOT(A) = NOR(A,A): send same value twice to same address.
reg  [15:0] bus_addr  = 16'h0;
reg  [31:0] bus_data  = 32'h0;
reg         bus_valid = 1'b0;

// Observation taps for the local cluster bus (2026-07-08, corrected 2026-07-09).
//
// IMPORTANT: we must NOT simply mirror bus_valid. The host INJECT path also
// drives bus_valid ("if (cpu_valid) ... bus_valid <= !cmd_valid" below) -- so a
// raw mirror latches the inject itself and can never prove that a *transit fire*
// left the local bus quiet. What we want is specifically: did a CELL FIRE present
// on the local cluster bus?  That is exactly the or_valid branch, gated by
// !or_transit. Tap that condition combinationally.
//
//   obs_fire_on_bus = a cell fired AND it was not transit-only
// so for transit=1 this stays 0 (fire routed across, local suppressed), while a
// normal fire (transit=0) raises it. Inject traffic never sets it.
wire obs_fire_on_bus = or_valid && !or_transit && !cpu_valid;
assign obs_bus_valid = obs_fire_on_bus;
assign obs_bus_addr  = or_addr;
assign obs_bus_data  = or_data;

// ── Cell outputs ──────────────────────────────────────────────────────────────
wire [15:0] cell_out_addr  [0:NUM_CELLS-1];
wire [31:0] cell_out_data  [0:NUM_CELLS-1];
wire        cell_out_valid [0:NUM_CELLS-1];
wire [3:0]  cell_out_routing[0:NUM_CELLS-1];
wire        cell_out_transit[0:NUM_CELLS-1];
wire        cell_armed     [0:NUM_CELLS-1];
wire        cell_arrived    [0:NUM_CELLS-1];
wire        cell_output_set  [0:NUM_CELLS-1];
wire [31:0] cell_cmd_latch   [0:NUM_CELLS-1];
wire [31:0] cell_in_addr_full[0:NUM_CELLS-1];
wire [31:0] cell_out_addr_full[0:NUM_CELLS-1];
wire [31:0] cell_adata       [0:NUM_CELLS-1];
// command-emit outputs from each cell (v3.0)
wire [31:0] cell_emit_bus    [0:NUM_CELLS-1];
wire [31:0] cell_emit_data   [0:NUM_CELLS-1];
wire        cell_emit_valid  [0:NUM_CELLS-1];
// ── Debug cell-select (opcode 26 = CMD_DBG_SELECT) ────────────────────────────
// Host picks WHICH cell of this array drives the dbg0_* ports, instead of the
// hardwired cell 0. cpu_data[clog2(NUM_CELLS)-1:0] = physical index within the
// array. Reuses the command bus; cells have no decode case for op 26 so it is a
// pure side-effect-free debug write. Lets the host walk every programmed cell on
// die (read-only observability), targeting by the same index space it placed into.
localparam DBG_W = (NUM_CELLS <= 2)  ? 1 : (NUM_CELLS <= 4)  ? 2 :
                   (NUM_CELLS <= 8)  ? 3 : (NUM_CELLS <= 16) ? 4 :
                   (NUM_CELLS <= 32) ? 5 : 6;
generate
if (DEBUG_SELECT) begin : g_dbgsel
    // DEV build: host picks which cell drives dbg0_* via op 26 (a wide NUM_CELLS:1 mux on
    // 4 buses — area-costly, only worth it where you actually walk cells to debug programs).
    reg [DBG_W-1:0] dbg_sel = {DBG_W{1'b0}};
    always @(posedge clk) begin
        if (rst)
            dbg_sel <= {DBG_W{1'b0}};
        else if (cmd_valid && (cmd_bus[7:0] == 8'd26) && (cpu_data[DBG_W-1:0] < NUM_CELLS))
            dbg_sel <= cpu_data[DBG_W-1:0];
    end
    assign dbg0_cmd_latch   = cell_cmd_latch[dbg_sel];
    assign dbg0_input_addr  = cell_in_addr_full[dbg_sel];
    assign dbg0_output_addr = cell_out_addr_full[dbg_sel];
    assign dbg0_a_data      = cell_adata[dbg_sel];
end else begin : g_dbg0
    // PRODUCTION build: hardwire dbg0_* to cell 0 — no mux, lean area, faster fit.
    // (op 26 still no-ops in the cells; per-cell readback simply isn't surfaced here.)
    assign dbg0_cmd_latch   = cell_cmd_latch[0];
    assign dbg0_input_addr  = cell_in_addr_full[0];
    assign dbg0_output_addr = cell_out_addr_full[0];
    assign dbg0_a_data      = cell_adata[0];
end
endgenerate

// ── Counters ──────────────────────────────────────────────────────────────────
reg [31:0] cycles;
assign cycle_count = cycles;

// armed_count is registered — computed combinationally then clocked.
// Keeps the carry-chain adder off the async output path to the LED IO pad.
reg [15:0] armed_comb;
reg [15:0] armed_reg = 16'h0;
assign armed_count = armed_reg;
reg [15:0] arrived_comb;  reg [15:0] arrived_reg = 16'h0;  assign arrived_count    = arrived_reg;
reg [15:0] outset_comb;   reg [15:0] outset_reg  = 16'h0;  assign output_set_count = outset_reg;

integer i;
always @(*) begin
    armed_comb = 0; arrived_comb = 0; outset_comb = 0;
    for (i = 0; i < NUM_CELLS; i = i + 1) begin
        if (cell_armed[i])      armed_comb   = armed_comb   + 1;
        if (cell_arrived[i])    arrived_comb = arrived_comb + 1;
        if (cell_output_set[i]) outset_comb  = outset_comb  + 1;
    end
end

always @(posedge clk) begin
    if (rst) begin armed_reg <= 16'h0; arrived_reg <= 16'h0; outset_reg <= 16'h0; end
    else     begin armed_reg <= armed_comb; arrived_reg <= arrived_comb; outset_reg <= outset_comb; end
end

// ── Cell instantiation ────────────────────────────────────────────────────────
// Boot-state targeting: during boot, physical CELL_ID == cpu_addr routes
// targeted commands (RECONFIGURE, SET_IN, SET_OUT) to the right cell.
// After boot the cell operates on logical addresses only — physical ID suppressed.
// Broadcast commands (FREEZE, RELEASE, PING, NOP) always reach all cells.
//
// ── Command-emit arbiter (v3.0) ─────────────────────────────────────────────────
// Collect emitted commands from command cells (topology COMMAND_EMIT) and
// priority-select the lowest index. FIRST-CUT arbitration: one winner per cycle,
// any simultaneous emitters are dropped (no queue/fairness yet — that is a later
// design decision). The winner is muxed into the command distribution below, so an
// emitted command routes through exactly the same targeting/decode as a host one.
reg [31:0] sel_emit_bus, sel_emit_data;
reg        sel_emit_valid;
integer e;
always @(*) begin
    sel_emit_valid = 1'b0; sel_emit_bus = 32'h0; sel_emit_data = 32'h0;
    for (e = NUM_CELLS-1; e >= 0; e = e - 1) begin   // high->low so lowest index wins
        if (cell_emit_valid[e]) begin
            sel_emit_valid = 1'b1;
            sel_emit_bus   = cell_emit_bus[e];
            sel_emit_data  = cell_emit_data[e];
        end
    end
end

reg [15:0] emit_count_r = 16'h0;
always @(posedge clk) begin
    if (rst)                 emit_count_r <= 16'h0;
    else if (sel_emit_valid) emit_count_r <= emit_count_r + 1'b1;
end
assign emit_count = emit_count_r;

// Effective command: an emitted command (when present) overrides the host command
// this cycle. Emitted commands target/broadcast via cmd_data[15:0] (the emit cell
// wrote output_address there); the host path keeps its supplied cpu_addr.
wire [31:0] eff_cmd_bus   = sel_emit_valid ? sel_emit_bus       : cmd_bus;
wire [31:0] eff_cmd_data  = sel_emit_valid ? sel_emit_data      : cmd_data;
wire        eff_cmd_valid = sel_emit_valid ? 1'b1               : cmd_valid;
wire [15:0] eff_cpu_addr  = sel_emit_valid ? sel_emit_data[15:0]: cpu_addr;

// cmd_bus is now 32-bit unified word — opcode in [7:0], modifiers in upper bits.
wire [7:0] cmd_code = eff_cmd_bus[7:0];

// Commands that require cell targeting via cpu_addr
// Boot opcode 14 (SET_LOGICAL) matches physical CELL_ID during the boot walk.
// SET_INPUT_ADDR(2)/SET_OUTPUT_ADDR(3) are NO LONGER array-targeted — they now
// broadcast and the CELL self-gates on addr_match (Option A, invariant clause 1):
// target rides the address lane via the SET_TARGET latch (top drives cpu_addr_w =
// load_target for opcodes 2/3/23), the new address value rides cmd_data. One
// comparator (the cell's addr_match) gates everything; no parallel array comparator.
// CMD_BOOT_COMMIT (0x07) intentionally not listed — broadcasts, each cell
// checks physical_mode internally.
wire cmd_is_boot_targeted = (cmd_code == 8'd14);    // CMD_SET_LOGICAL (boot walk)
// BOOT_COMMIT (opcode 7) is BROADCAST: it is the final auth commit, sent once to
// all cells after the per-cell walk completes (auth is still 0000 during the
// walk, so every cell accepts it). The per-cell walk (health check + logical
// address) uses the targeted address opcodes above, not BOOT_COMMIT.

wire cmd_is_runtime_targeted = sel_emit_valid;  // FIX (2026-07-30, Alan): emitted
                                          // commands MUST be targeted, not broadcast --
                                          // that's what output_address is for. Before
                                          // this fix, an emitted command's low byte
                                          // (whatever a_data happened to hold) was
                                          // interpreted as a real opcode and applied to
                                          // EVERY cell if that opcode was one of the
                                          // broadcast-type ones (auth_ok only, no
                                          // config_match) -- a command-emit cell's
                                          // "harmless data" could silently reconfigure
                                          // the whole array (points.md #65: 0x1234's low
                                          // byte happened to equal CMD_TOPO_NOR_COLD,
                                          // disarming everything). eff_cpu_addr/
                                          // cmd_is_this_cell_runtime already existed for
                                          // exactly this purpose, just never enabled.
                                          // Host-issued commands are UNCHANGED (still
                                          // broadcast-unless-the-opcode-itself-gates-on-
                                          // config_match, same as always) -- this only
                                          // changes emitted commands, which now reach
                                          // ONLY the cell whose input_address matches
                                          // the emitting cell's output_address,
                                          // regardless of the payload's opcode content.

wire cmd_is_targeted = cmd_is_boot_targeted || cmd_is_runtime_targeted;

genvar c;
generate
    for (c = 0; c < NUM_CELLS; c = c + 1) begin : cell_array
        // Boot targeting: targeted commands only reach cell whose physical ID
        // matches cpu_addr. Broadcast commands reach all cells.
        // Boot targeted: match physical CELL_ID
        // Runtime targeted: match logical input_address via dedicated port
        wire [15:0] cell_input_addr;
        wire cmd_is_this_cell_boot    = (eff_cpu_addr[15:0] == (CELL_BASE + c));
        wire cmd_is_this_cell_runtime = (eff_cpu_addr[15:0] == cell_input_addr);
        wire cmd_is_this_cell = cmd_is_boot_targeted    ? cmd_is_this_cell_boot
                              : cmd_is_runtime_targeted ? cmd_is_this_cell_runtime
                              : 1'b1;  // untargeted — broadcast
        wire cell_cmd_valid = eff_cmd_valid &&
                              (!cmd_is_targeted || cmd_is_this_cell);
        unicell64_v3 #(
            .CELL_ID         (CELL_BASE + c),
            .ENABLE_LATCH_IN (0)   // disabled on iCEBreaker — timing constraint
        ) cell_inst (
            .clk        (clk),
            .rst        (rst),
            .cmd_bus    (eff_cmd_bus),
            .cmd_data   (eff_cmd_data),
            .cmd_valid  (cell_cmd_valid),
            .bus_addr   (bus_addr),
            .bus_data   (bus_data),
            .bus_valid  (bus_valid),
            .out_addr   (cell_out_addr[c]),
            .out_data   (cell_out_data[c]),
            .out_valid  (cell_out_valid[c]),
            .out_routing(cell_out_routing[c]),
            .out_transit(cell_out_transit[c]),
            .cmd_emit_bus   (cell_emit_bus[c]),
            .cmd_emit_data  (cell_emit_data[c]),
            .cmd_emit_valid (cell_emit_valid[c]),
            .dbg_cmd_latch        (cell_cmd_latch[c]),
            .dbg_input_addr       (cell_in_addr_full[c]),
            .dbg_input_addr_short (cell_input_addr),
            .dbg_output_addr (cell_out_addr_full[c]),
            .dbg_start_flag  (),
            .dbg_armed       (cell_armed[c]),
            .dbg_frozen      (),
            .dbg_priority    (),
            .dbg_trace       (),
            .dbg_breakpoint  (),
            .dbg_dtype       (),
            .dbg_output_set  (cell_output_set[c]),
            .dbg_a_arrived   (cell_arrived[c]),
            .dbg_a_data      (cell_adata[c])
        );
    end
endgenerate

// ── Wired-OR bus ──────────────────────────────────────────────────────────────
reg [15:0] or_addr;
reg [31:0] or_data;
reg        or_valid;
reg [3:0]  or_routing;
reg        or_transit;

always @(*) begin
    or_addr    = 16'h0;
    or_data    = 32'h0;
    or_valid   = 1'b0;
    or_routing = 4'h0;
    or_transit = 1'b0;

    for (i = 0; i < NUM_CELLS; i = i + 1) begin
        if (cell_out_valid[i]) begin
            or_addr    = cell_out_addr[i];
            or_data    = or_data | cell_out_data[i];  // wired-OR
            or_routing = cell_out_routing[i];          // ties to the SAME winning cell as or_addr
            or_transit = cell_out_transit[i];          // ditto -- transit is cell-identity-tied
            or_valid   = 1'b1;
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
        out_routing <= 4'h0;
        out_transit <= 1'b0;
        cycles    <= 32'h0;
    end else begin
        cycles    <= cycles + 1;
        bus_valid <= 1'b0;

        out_valid <= 1'b0;

        if (cpu_valid) begin
            // All host packets update bus registers — keeps bus consistent
            // Drive the data bus for any data-carrying cpu cycle (host DATA_WRITE
            // OR an inbound bridge token), but NOT for commands. A command pulses
            // cmd_valid; a host inject (opcode 1) and a bridge token both arrive
            // with cmd_valid=0. The old test (cmd_code==1) dropped bridge tokens,
            // because a bridge token rides ibus with the command bus idle/stale —
            // so cross-zone delivery silently failed while in-zone (or_valid path)
            // worked. Gating on !cmd_valid covers all three cases correctly.
            bus_addr  <= cpu_addr[15:0];
            bus_data  <= cpu_data;
            bus_valid <= !cmd_valid;
        end else if (or_valid) begin
            // Split (2026-07-07 transit primitive): the outbound path
            // (out_*, which the zone wrapper reads and routes across per
            // out_routing) always fires. The LOCAL cluster bus (bus_*) is
            // gated by !or_transit -- a transit-only fire routes ACROSS but
            // does NOT present on its host cluster's bus, so it never
            // injects into the host's own computation. A normal fire
            // (or_transit=0) drives both, exactly as before.
            out_addr    <= or_addr;
            out_data    <= or_data;
            out_valid   <= 1'b1;
            out_routing <= or_routing;
            out_transit <= or_transit;
            if (!or_transit) begin
                bus_addr  <= or_addr;
                bus_data  <= or_data;
                bus_valid <= 1'b1;
            end
        end
    end
end

endmodule
