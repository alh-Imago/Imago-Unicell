// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// top_icebreaker.v — Imago UniCell v3 Top Level for iCEBreaker
//
// PURPOSE: fast, fully-open-toolchain (yosys + nextpnr-ice40 + icepack/
// iceprog) iteration rig for small cell-internal changes -- cardinal bits
// (#42), comparator + routing latch (#49/#51) -- before committing to a
// full Quartus rebuild on the Arria 10. Builds in seconds, not minutes.
// 2 cells max: enough to prove decode logic and inter-cell wired-OR
// propagation, deliberately not meant to be a scale test.
//
// CAPACITY, confirmed empirically 2026-07-29 (not assumed): the v3 cell is
// considerably larger than the old v1.2/v2.3 cell this board was
// originally sized for (64-bit cmd_latch, 17 opcodes, the full addressing
// model, methodology bus -- real logic that didn't exist before). 4 cells
// was the old ceiling; it does NOT fit the v3 cell -- tried directly,
// yosys reports 7528 LCs needed (142% of the UP5K's 5280), and nextpnr
// fails placement outright ("no BELs remaining"). 2 cells DOES fit, with
// real margin: 4242/5280 LCs (80%), places and routes cleanly, Fmax
// 14.12MHz against a 12MHz target (PASS).
//
// PORTED 2026-07-29 from the old v2.3 top (which instantiated the retired
// unicell_array/unicell.v, 32-bit-only command bus). This version
// instantiates unicell64_v3.v directly -- the same cell module the Arria 10
// build uses, so decode-logic changes made here are the same RTL that
// carries forward, only the board-level wiring differs (per-project
// convention: "the verilog is essentially the same, just the tops change").
//
// CLOCK: SB_HFOSC internal oscillator, 12MHz (48MHz / 4) -- no external
// crystal needed, same as the old top.
//
// RESET: tied to 1'b0 permanently, same as the old top. CMD_ARRAY_RESET
// (opcode 8) is handled entirely inside unicell64_v3.v as a normal command
// now (v3's own auth_ok-gated case, not the old top's hand-rolled
// auth_rst_pulse hack that was needed because unicell_array/unicell.v
// didn't handle it internally). iCE40 SRAM cells power up to their
// synthesis-time initial values, which is what rst=0 permanently relies on
// -- same proven pattern as the original bring-up.
//
// BUS TOPOLOGY: cmd_bus/cmd_data/cmd_valid (the host command channel) are
// broadcast identically to both cells straight from uart_bridge's
// cpu_bus/cpu_data/cpu_valid -- no manual opcode re-gating at the top level,
// unlike the old v2.3 top's DATA_WRITE/preload_sel special-casing, which
// doesn't apply to v3's command format. bus_addr/bus_data/bus_valid is a
// SEPARATE, genuine miniature wired-OR bus: each cell's own
// (out_addr/out_data/out_valid) is OR-combined every cycle into one shared
// bus that both cells (and the host readback path) see -- the same
// wired-OR principle as the full array, just at 2-cell scale instead of
// 25/400.
//
// out_routing/out_transit (cardinal-bit scaffolding already present in
// unicell64_v3.v's port list) are intentionally left unconnected here --
// this rig doesn't yet need inter-zone bridging, only in-bus propagation.
// Revisit once #42 actually adds per-edge cardinal decode logic to route
// through them.

`default_nettype none

module top (
    input  wire BTN_N,   // present on the board, currently unused (matches old top)
    input  wire RX,
    output wire TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// Internal HFOSC — 12MHz (48MHz / 4), same as the old top
wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b10")) osc (
    .CLKHFPU(1'b1),
    .CLKHFEN(1'b1),
    .CLKHF(CLK)
);

wire rst = 1'b0;

// ── Host command channel (from uart_bridge, broadcast to all cells) ────────
wire [31:0] cpu_bus, cpu_data;
wire        cpu_valid, array_rst_req;

// ── Miniature wired-OR data bus (cell-to-cell, NOT host-driven) ────────────
reg  [15:0] bus_addr_r;
reg  [31:0] bus_data_r;
reg         bus_valid_r;

localparam NUM_CELLS = 2;

wire [31:0] c_out_addr  [0:NUM_CELLS-1];
wire [31:0] c_out_data  [0:NUM_CELLS-1];
wire        c_out_valid [0:NUM_CELLS-1];
wire [3:0]  c_out_routing [0:NUM_CELLS-1]; // unused for now, see header note
wire        c_out_transit  [0:NUM_CELLS-1]; // unused for now, see header note
wire [31:0] c_cmd_emit_bus  [0:NUM_CELLS-1];
wire [31:0] c_cmd_emit_data [0:NUM_CELLS-1];
wire        c_cmd_emit_valid[0:NUM_CELLS-1];
wire [31:0] c_dbg_cmd_latch [0:NUM_CELLS-1];
wire        c_dbg_armed     [0:NUM_CELLS-1];

genvar gi;
generate
    for (gi = 0; gi < NUM_CELLS; gi = gi + 1) begin : cells
        unicell64_v3 #(
            .CELL_ID(gi),
            .ENABLE_LATCH_IN(1)   // needed for the continuous-fire loop_back
                                  // pattern already sim-proven this session
                                  // (tb_freeze_loop_v3.v) -- kept on here so
                                  // this rig can exercise the same tests
        ) u_cell (
            .clk        (CLK),
            .rst        (rst),
            .cmd_bus    (cpu_bus),
            .cmd_data   (cpu_data),
            .cmd_valid  (cpu_valid),

            .bus_addr   (bus_addr_r),
            .bus_data   (bus_data_r),
            .bus_valid  (bus_valid_r),

            .out_addr   (c_out_addr[gi]),
            .out_data   (c_out_data[gi]),
            .out_valid  (c_out_valid[gi]),
            .out_routing(c_out_routing[gi]),
            .out_transit(c_out_transit[gi]),

            .cmd_emit_bus  (c_cmd_emit_bus[gi]),
            .cmd_emit_data (c_cmd_emit_data[gi]),
            .cmd_emit_valid(c_cmd_emit_valid[gi]),

            .dbg_cmd_latch       (c_dbg_cmd_latch[gi]),
            .dbg_input_addr      (),
            .dbg_input_addr_short(),
            .dbg_output_addr     (),
            .dbg_start_flag      (),
            .dbg_armed           (c_dbg_armed[gi]),
            .dbg_frozen          (),
            .dbg_priority        (),
            .dbg_trace           (),
            .dbg_breakpoint      (),
            .dbg_dtype           (),
            .dbg_output_set      (),
            .dbg_a_arrived       (),
            .dbg_a_data          ()
        );
    end
endgenerate

// OR-combine every cell's output into one shared bus each cycle -- the
// same wired-OR principle the full array uses, just 2 cells instead of
// 25/400. Safe as a plain OR since these test sequences fire one cell at
// a time; if that assumption ever needs revisiting for a genuinely
// concurrent multi-fire test, switch to the priority-mux style used in
// top_arria10_zone1_v3.v instead.
integer i;
always @(posedge CLK) begin
    bus_addr_r  <= 16'h0;
    bus_data_r  <= 32'h0;
    bus_valid_r <= 1'b0;
    for (i = 0; i < NUM_CELLS; i = i + 1) begin
        if (c_out_valid[i]) begin
            bus_addr_r  <= c_out_addr[i][15:0];
            bus_data_r  <= c_out_data[i];
            bus_valid_r <= 1'b1;
        end
    end
end

// Host-visible readback: same combined bus, straight to the bridge
wire [31:0] out_addr_host  = {16'h0, bus_addr_r};
wire [31:0] out_data_host  = bus_data_r;
wire        out_valid_host = bus_valid_r;

// armed_count: sum of dbg_armed across both cells (simple, matches the
// old top's LED-driving intent; not a full zone-style aggregate)
wire [15:0] armed_count = c_dbg_armed[0] + c_dbg_armed[1];
wire [31:0] cycle_count_unused = 32'h0; // no free-running counter wired up yet

uart_bridge #(
    .CLK_FREQ (12_000_000),
    .BAUD_RATE(115_200)
) bridge (
    .clk         (CLK),
    .rst         (rst),
    .uart_rx     (RX),   // real, live pin -- FTDI TX -> here. NOT the
                          // Arria 10 situation from this session: this RX
                          // is genuinely wired to real UART hardware, not
                          // floating, so no tie-off needed here.
    .uart_tx     (TX),
    .cpu_bus     (cpu_bus),
    .cpu_data    (cpu_data),
    .cpu_valid   (cpu_valid),
    .array_rst   (array_rst_req),  // currently unused -- CMD_ARRAY_RESET
                                    // (opcode 8) is handled per-cell inside
                                    // unicell64_v3.v now, see header note
    .array_freeze(),                // CMD_FREEZE (opcode 5) on the command
                                    // bus handles it per-cell instead
    .out_addr    (out_addr_host),
    .out_data    (out_data_host),
    .out_valid   (out_valid_host),
    .armed_count (armed_count),
    .cycle_count (cycle_count_unused)
);

// LEDs — registered to keep combinational comparison off async IO path
reg ledr_n_reg = 1'b1;
always @(posedge CLK) ledr_n_reg <= (armed_count == 0);
assign LEDR_N = ledr_n_reg;
assign LEDG_N = 1'b0;  // Green always on (heartbeat/power indicator)

endmodule
