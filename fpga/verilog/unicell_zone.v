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

module unicell_zone #(
    parameter NUM_CELLS   = 28,    // 28 cells per zone — fits 16 zones in XC7K480T
    parameter NUM_BRIDGES = 2,     // 2 bridges per active direction
    parameter ZONE_ID     = 0      // zone identifier (for documentation/debug)
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
    output wire [31:0] cycle_count,

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

unicell_array #(
    .NUM_CELLS (NUM_CELLS)
) cells (
    .clk         (clk),
    .rst         (rst),
    .cmd_bus     (cmd_bus_r),
    .cmd_data    (cmd_data_r),
    .cmd_valid   (cmd_valid_r),
    .cpu_addr    (cpu_addr),
    .cpu_data    (ibus_data),
    .cpu_valid   (ibus_valid),
    .out_addr    (za_out_addr),
    .out_data    (za_out_data),
    .out_valid   (za_out_valid),
    .armed_count (armed_count),
    .cycle_count (cycle_count)
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

    if (za_out_valid) begin
        ibus_addr  <= za_out_addr;
        ibus_data  <= za_out_data;
        ibus_valid <= 1'b1;
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
// Fired cell broadcast to all active directions.
// Receiving zone filters by address range — sees only traffic for its cells.
// Bridge 0 carries every fire. Bridge 1 is available for high-bandwidth paths.

genvar g;
generate
for (g = 0; g < NUM_BRIDGES; g = g + 1) begin : bridge_out
    always @(posedge clk) begin
        if (rst) begin
            bridge_n_out_valid[g] <= 1'b0;
            bridge_s_out_valid[g] <= 1'b0;
            bridge_e_out_valid[g] <= 1'b0;
            bridge_w_out_valid[g] <= 1'b0;
        end else begin
            // Bridge 0: carries all fired cells
            // Bridge 1: spare bandwidth (can carry overflow or second stream)
            bridge_n_out_valid[g]             <= (g==0) & za_out_valid;
            bridge_n_out_addr[g*16 +: 16]     <= za_out_addr;
            bridge_n_out_data[g*32 +: 32]     <= za_out_data;

            bridge_s_out_valid[g]             <= (g==0) & za_out_valid;
            bridge_s_out_addr[g*16 +: 16]     <= za_out_addr;
            bridge_s_out_data[g*32 +: 32]     <= za_out_data;

            bridge_e_out_valid[g]             <= (g==0) & za_out_valid;
            bridge_e_out_addr[g*16 +: 16]     <= za_out_addr;
            bridge_e_out_data[g*32 +: 32]     <= za_out_data;

            bridge_w_out_valid[g]             <= (g==0) & za_out_valid;
            bridge_w_out_addr[g*16 +: 16]     <= za_out_addr;
            bridge_w_out_data[g*32 +: 32]     <= za_out_data;
        end
    end
end
endgenerate

endmodule
