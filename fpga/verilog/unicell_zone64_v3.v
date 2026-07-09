// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// unicell_zone.v — Timing Zone Module v2
// Protocol v2.3
//
// A self-contained timing island of NUM_CELLS cells with registered
// bridge interfaces to adjacent zones in a 2D grid arrangement.
//
// 2×8 grid layout (16 zones, 28 cells each = 448 cells total):
//
//  [Z00]─2─[Z01]─2─[Z02]─2─[Z03]─2─[Z04]─2─[Z05]─2─[Z06]─2─[Z07]
//    |        |        |        |        |        |        |        |
//    2        2        2        2        2        2        2        2
//    |        |        |        |        |        |        |        |
//  [Z08]─2─[Z09]─2─[Z10]─2─[Z11]─2─[Z12]─2─[Z13]─2─[Z14]─2─[Z15]
//
// Bridge count per zone (2 bridges per active direction):
//   Corner zones  (Z00,Z07,Z08,Z15): 2 directions × 2 = 4 bridge cells
//   Top/Bot edge  (Z01-Z06, Z09-Z14): 3 directions × 2 = 6 bridge cells
//
// Each bridge: RELAY cell (PASS_B | GS_LATCH_IN), 1 tick latency.
// Registered handoff — deterministic timing at every zone boundary.
// CONTAIN_ROUTING true on each Pblock — router sees 28 cells max.
//
// LUT budget (XC7K480T, 597,200 LUTs):
//   28 cells × 1,284 LUTs = 35,952 LUTs per zone
//   16 zones × 35,952    = 575,232 LUTs (96.3%) — fits with headroom
//   Bridge cells negligible (RELAY ≈ 4 LUTs each)
//
// Clock: 125MHz target. Each zone independently meets timing.
// Bridge latency: exactly 1 tick per zone crossing (registered).

`default_nettype none
`timescale 1ns / 1ps

module unicell_zone64_v3 #(
    parameter NUM_CELLS   = 28,    // 28 cells per zone — fits 16 zones in XC7K480T
    parameter NUM_BRIDGES = 2,     // 2 bridges per active direction
    parameter ZONE_ID     = 0,     // zone identifier (for documentation/debug)
    parameter DEBUG_SELECT = 0     // per-cell debug readback mux (dev=1, production=0)

    // Bridge routing (2026-07-06, replacing the 2026-07-05 address-decode
    // parameters): which directions a fire reaches is no longer a synthesis-
    // time fact about this zone -- it's read straight off the firing cell's
    // own routing_mask (unicell64_v3.v, set via METH_SET_ROUTING, part of the
    // ICM's per-cell load config). A model's routing is now data it loads,
    // not silicon it needs resynthesized for. See fire_to_n/s/e/w below.
) (
    input  wire        clk,
    input  wire        rst,

    // Command bus — broadcast from top level to all zones
    input  wire [31:0] cmd_bus,
    input  wire [31:0] cmd_data,
    input  wire        cmd_valid,
    input  wire [15:0] cpu_addr,
    input  wire [31:0] cpu_data,
    input  wire        cpu_valid,

    // Fired cell output (to top-level collection bus)
    output wire [15:0] out_addr,
    output wire [31:0] out_data,
    output wire        out_valid,

    // Status
    output wire [15:0] armed_count,
    output wire [15:0] arrived_count,
    output wire [15:0] output_set_count,
    output wire [15:0] emit_count,
    output wire [31:0] dbg0_cmd_latch,
    output wire [31:0] dbg0_input_addr,
    output wire [31:0] dbg0_output_addr,
    output wire [31:0] dbg0_a_data,
    output wire [31:0] cycle_count,
    // Local cluster bus observation (2026-07-08) -- the signal transit suppresses.
    output wire        obs_bus_valid,
    output wire [15:0] obs_bus_addr,
    output wire [31:0] obs_bus_data,

    // ── Bridge interfaces (2 per active direction, registered) ───────────
    // Unused directions: tie in_valid=0, leave out_* unconnected at top level

    // North (row 1 zones only — row 0 has no north neighbour)
    input  wire [NUM_BRIDGES-1:0]       bridge_n_in_valid,
    input  wire [NUM_BRIDGES*16-1:0]    bridge_n_in_addr,
    input  wire [NUM_BRIDGES*32-1:0]    bridge_n_in_data,
    output reg  [NUM_BRIDGES-1:0]       bridge_n_out_valid,
    output reg  [NUM_BRIDGES*16-1:0]    bridge_n_out_addr,
    output reg  [NUM_BRIDGES*32-1:0]    bridge_n_out_data,

    // South (row 0 zones only — row 1 has no south neighbour)
    input  wire [NUM_BRIDGES-1:0]       bridge_s_in_valid,
    input  wire [NUM_BRIDGES*16-1:0]    bridge_s_in_addr,
    input  wire [NUM_BRIDGES*32-1:0]    bridge_s_in_data,
    output reg  [NUM_BRIDGES-1:0]       bridge_s_out_valid,
    output reg  [NUM_BRIDGES*16-1:0]    bridge_s_out_addr,
    output reg  [NUM_BRIDGES*32-1:0]    bridge_s_out_data,

    // East (all except rightmost column: Z07, Z15)
    input  wire [NUM_BRIDGES-1:0]       bridge_e_in_valid,
    input  wire [NUM_BRIDGES*16-1:0]    bridge_e_in_addr,
    input  wire [NUM_BRIDGES*32-1:0]    bridge_e_in_data,
    output reg  [NUM_BRIDGES-1:0]       bridge_e_out_valid,
    output reg  [NUM_BRIDGES*16-1:0]    bridge_e_out_addr,
    output reg  [NUM_BRIDGES*32-1:0]    bridge_e_out_data,

    // West (all except leftmost column: Z00, Z08)
    input  wire [NUM_BRIDGES-1:0]       bridge_w_in_valid,
    input  wire [NUM_BRIDGES*16-1:0]    bridge_w_in_addr,
    input  wire [NUM_BRIDGES*32-1:0]    bridge_w_in_data,
    output reg  [NUM_BRIDGES-1:0]       bridge_w_out_valid,
    output reg  [NUM_BRIDGES*16-1:0]    bridge_w_out_addr,
    output reg  [NUM_BRIDGES*32-1:0]    bridge_w_out_data
);

// ── Internal bus — local cells + inbound bridge traffic ───────────────────
reg  [15:0] ibus_addr  = 16'h0;
reg  [31:0] ibus_data  = 32'h0;
reg         ibus_valid = 1'b0;

// ── cmd_bus pipeline register — breaks cross-boundary fanout ─────────────
// Registers cmd_bus/cmd_data/cmd_valid at zone entry so the fanout to
// NUM_CELLS cells happens entirely within the zone from a local register.
// Eliminates Dont Touch violations and closes timing at 125 MHz.
reg  [31:0] cmd_bus_r   = 32'h0;
reg  [31:0] cmd_data_r  = 32'h0;
reg         cmd_valid_r = 1'b0;

always @(posedge clk) begin
    cmd_bus_r   <= cmd_bus;
    cmd_data_r  <= cmd_data;
    cmd_valid_r <= cmd_valid;
end

// ── Cell array ────────────────────────────────────────────────────────────
wire [15:0] za_out_addr;
wire [31:0] za_out_data;
wire        za_out_valid;
wire [3:0]  za_out_routing;
wire        za_out_transit;  // 1 = winning fire was route-only (local already suppressed
                             // inside the array). Available here for debug/future use; the
                             // bridge routing below is unaffected -- a transit fire still
                             // asserts za_out_valid and carries za_out_routing across.

unicell_array64_v3 #(
    .NUM_CELLS (NUM_CELLS),
    .DEBUG_SELECT (DEBUG_SELECT),
    .CELL_BASE (ZONE_ID << 5)   // flat address = {block[3:0], cell[4:0]}:
                                // cell in bits [4:0] (32/block), block in [8:5].
                                // Block N owns N*32 .. N*32+NUM_CELLS-1. 9 bits
                                // total, well inside the 16-bit local address.
) cells (
    .clk         (clk),
    .rst         (rst),
    .cmd_bus     (cmd_bus_r),
    .cmd_data    (cmd_data_r),
    .cmd_valid   (cmd_valid_r),
    .cpu_addr    (ibus_addr),
    .cpu_data    (ibus_data),
    .cpu_valid   (ibus_valid),
    .out_addr    (za_out_addr),
    .out_data    (za_out_data),
    .out_valid   (za_out_valid),
    .out_routing (za_out_routing),
    .out_transit (za_out_transit),
    .armed_count (armed_count),
    .arrived_count   (arrived_count),
    .output_set_count(output_set_count),
    .emit_count      (emit_count),
    .dbg0_cmd_latch  (dbg0_cmd_latch),
    .dbg0_input_addr (dbg0_input_addr),
    .dbg0_output_addr(dbg0_output_addr),
    .dbg0_a_data     (dbg0_a_data),
    .cycle_count (cycle_count),
    .obs_bus_valid (obs_bus_valid),
    .obs_bus_addr  (obs_bus_addr),
    .obs_bus_data  (obs_bus_data)
);

assign out_addr  = za_out_addr;
assign out_data  = za_out_data;
assign out_valid = za_out_valid;

// ── Bridge input arbiter ──────────────────────────────────────────────────
// Priority: local > north > south > east > west
// Each bridge slot checked in order. First valid wins each cycle.
// For 2 bridges per direction: bridge 0 has priority over bridge 1.
// TODO: upgrade to round-robin for equal bandwidth across directions.

integer bi;
always @(posedge clk) begin
    ibus_valid <= 1'b0;
    ibus_addr  <= 16'h0;
    ibus_data  <= 32'h0;

    if (cpu_valid) begin
        // Host inject (DATA_WRITE over ISSP/UART) — top priority so a host
        // seed reaches the cells. Without this, ibus only ever carried cell
        // feedback + inter-zone bridge traffic and host injects were dropped,
        // so an armed fabric could never be seeded (out_count stayed 0).
        ibus_addr  <= cpu_addr;
        ibus_data  <= cpu_data;
        ibus_valid <= 1'b1;
    // NOTE: local fired output (za_out_valid) is NOT re-injected here.
    // The array already chains its own output internally via or_valid->bus.
    // Re-injecting it through the cpu port double-drove every fired address
    // onto the bus (once by the array's or_valid path, again by this branch),
    // and the lingering second exposure re-armed cells that had just fired
    // (first-arrival store hit after a_arrived had cleared). Symptom diverged
    // sim vs silicon (sim: arrived stuck high; silicon: arrived->0, no output
    // surfaced). Host-inject (cpu_valid) and inbound bridge paths are retained;
    // intra-zone chaining is handled entirely by the array's internal feedback.
    end else begin
        for (bi = 0; bi < NUM_BRIDGES; bi = bi + 1) begin
            if (bridge_n_in_valid[bi] && !ibus_valid) begin
                ibus_addr  <= bridge_n_in_addr[bi*16 +: 16];
                ibus_data  <= bridge_n_in_data[bi*32 +: 32];
                ibus_valid <= 1'b1;
            end
        end
        for (bi = 0; bi < NUM_BRIDGES; bi = bi + 1) begin
            if (bridge_s_in_valid[bi] && !ibus_valid) begin
                ibus_addr  <= bridge_s_in_addr[bi*16 +: 16];
                ibus_data  <= bridge_s_in_data[bi*32 +: 32];
                ibus_valid <= 1'b1;
            end
        end
        for (bi = 0; bi < NUM_BRIDGES; bi = bi + 1) begin
            if (bridge_e_in_valid[bi] && !ibus_valid) begin
                ibus_addr  <= bridge_e_in_addr[bi*16 +: 16];
                ibus_data  <= bridge_e_in_data[bi*32 +: 32];
                ibus_valid <= 1'b1;
            end
        end
        for (bi = 0; bi < NUM_BRIDGES; bi = bi + 1) begin
            if (bridge_w_in_valid[bi] && !ibus_valid) begin
                ibus_addr  <= bridge_w_in_addr[bi*16 +: 16];
                ibus_data  <= bridge_w_in_data[bi*32 +: 32];
                ibus_valid <= 1'b1;
            end
        end
    end
end

// ── Bridge outputs (registered — 1 tick latency) ─────────────────────────
// FIXED 2026-07-05: this used to be "bridges are dumb physical wiring,
// every fire goes to every direction" -- a genuine broadcast, harmless
// with one bridge partner, real contention with several. First fix
// (2026-07-05) made routing depend on the fired address's own zone field
// matched against per-direction N_ZONE/N_ACTIVE parameters -- but those
// were synthesis-time parameters, meaning a different model's routing
// needs would require a full resynthesize/reflash, exactly the kind of
// per-target rebuild the ICM is supposed to avoid (Alan, 2026-07-06).
//
// FIXED AGAIN 2026-07-06: routing now reads directly off the firing
// cell's own routing_mask (unicell64_v3.v cmd_latch[14:11], set via
// METH_SET_ROUTING as part of the cell's normal load-time config, same
// mechanism as topology/latch_in). Bit0=N, bit1=S, bit2=E, bit3=W. This
// makes routing part of the ICM's own per-cell data, loaded fresh with
// every model, not a fact baked into the bitstream -- and a bitmask
// (rather than a single target) gives genuine multicast: one fire can
// set two direction bits and reach two neighbor clusters at once, no
// separate table lookup needed.
genvar g;
wire fire_to_n = za_out_routing[0];
wire fire_to_s = za_out_routing[1];
wire fire_to_e = za_out_routing[2];
wire fire_to_w = za_out_routing[3];
generate
for (g = 0; g < NUM_BRIDGES; g = g + 1) begin : bridge_out
    always @(posedge clk) begin
        if (rst) begin
            bridge_n_out_valid[g] <= 1'b0;
            bridge_s_out_valid[g] <= 1'b0;
            bridge_e_out_valid[g] <= 1'b0;
            bridge_w_out_valid[g] <= 1'b0;
        end else begin
            bridge_n_out_valid[g]             <= (g==0) & za_out_valid & fire_to_n;
            bridge_n_out_addr[g*16 +: 16]     <= za_out_addr;
            bridge_n_out_data[g*32 +: 32]     <= za_out_data;

            bridge_s_out_valid[g]             <= (g==0) & za_out_valid & fire_to_s;
            bridge_s_out_addr[g*16 +: 16]     <= za_out_addr;
            bridge_s_out_data[g*32 +: 32]     <= za_out_data;

            bridge_e_out_valid[g]             <= (g==0) & za_out_valid & fire_to_e;
            bridge_e_out_addr[g*16 +: 16]     <= za_out_addr;
            bridge_e_out_data[g*32 +: 32]     <= za_out_data;

            bridge_w_out_valid[g]             <= (g==0) & za_out_valid & fire_to_w;
            bridge_w_out_addr[g*16 +: 16]     <= za_out_addr;
            bridge_w_out_data[g*32 +: 32]     <= za_out_data;
        end
    end
end
endgenerate

endmodule
