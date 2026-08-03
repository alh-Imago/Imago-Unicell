// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_stripped_ring_test_v1.v — FIRST REAL-SILICON FIT CHECK for the
// stripped/next-hop cell (points.md #88-#94). NOT YET BUILT OR FIT — this is
// the prepared project, per #83's own sequencing: RTL and sim are done and
// confirmed; this is what turns "confirmed correct in software" into
// "confirmed real in hardware" (or reveals it isn't, at whatever clock speed
// Quartus reports — either answer is the actual point of this build).
//
// SCOPE, deliberately small (per #83: "whatever scope is needed to test the
// timing question directly, not the full hybrid architecture at once"):
// A (compute, NOR) -> B (PURE RELAY, cardinal_edge tags its North input as
// relay per #94) -> C (leaf consumer). This is the SAME 3-cell topology as
// tb_stripped_v1_relay.v, confirmed correct in sim -- built here as a real
// chain (not a closed ring; the ring closure in tb_stripped_v1_ring.v was a
// sim-only topology check, not needed to answer the timing/fit question).
// C is periodically frozen and released by a free-running counter, so the
// SAME freeze/cascade mechanism confirmed in sim (#92/#93) also gets
// exercised continuously on real silicon, not just fit statically.
//
// Configuration is NOT yet wired to loader_fsm_v3.v (that integration is
// still deferred, per #88's own note) -- a simple one-shot power-on
// autoconfig sequencer drives each cell's cfg_valid/cfg_data directly after
// reset, matching exactly the config words already confirmed correct in
// tb_stripped_v1_relay.v.
//
// WHAT THIS BUILD ANSWERS: does unicell_stripped_v1 close timing at a
// reasonable clock, and what does it actually cost in ALMs -- the two
// questions #83 identified as answerable ONLY by real synthesis, never by
// simulation. WHAT THIS BUILD DOES NOT YET ANSWER: whether it's functionally
// correct ON SILICON (no JTAG/ISSP readback wired up yet -- that's a
// separate, larger follow-on once this fits and closes timing at all).
`default_nettype none
`timescale 1ns / 1ps

module top_stripped_ring_test_v1 (
    input  wire CLK_100M,   // 100 MHz board ref, PIN_E23 (same as existing projects)
    output wire LED0_N,     // lit (low) whenever ANY of A/B/C is NOT ready -- a
                             // direct, continuous real-hardware view of the
                             // exact freeze/cascade behavior confirmed in #92/#93
    output wire LED1_N      // heartbeat -- confirms the design is alive/clocking
);

// ── Clock/reset — same convention as top_arria10_zone1.v ─────────────────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // CLK_100M / 4 = 25 MHz, matching existing fabric clock

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

localparam [9:0] TOPO_NOR = 10'h004;

// ── One-shot power-on autoconfig (stand-in for loader_fsm_v3.v — deferred
// per #88) — pulses cfg_valid/cfg_data for A, B, C in turn right after
// reset, then stops. Config words match tb_stripped_v1_relay.v exactly. ──
reg [3:0]   cfg_step = 4'h0;
reg         cfgA=0, cfgB=0, cfgC=0;
reg [127:0] cfgA_d=0, cfgB_d=0, cfgC_d=0;

always @(posedge clk) begin
    if (rst) begin
        cfg_step <= 4'h0;
        cfgA <= 0; cfgB <= 0; cfgC <= 0;
    end else begin
        cfgA <= 0; cfgB <= 0; cfgC <= 0;
        case (cfg_step)
            4'h1: begin cfgA_d <= 128'h0; cfgA_d[9:0] <= TOPO_NOR; cfgA_d[69:64] <= 6'b000010; cfgA <= 1; end
            4'h3: begin cfgB_d <= 128'h0; cfgB_d[69:64] <= 6'b000010; cfgB_d[75:70] <= 6'b000001; cfgB <= 1; end // relay, per #94
            4'h5: begin cfgC_d <= 128'h0; cfgC_d[9:0] <= TOPO_NOR; cfgC_d[69:64] <= 6'b000000; cfgC <= 1; end
            default: ;
        endcase
        if (cfg_step != 4'hF) cfg_step <= cfg_step + 4'h1;
    end
end

// ── Free-running stimulus into A's north port — every 256 cycles, present
// a new counter-derived value. A needs 2 arrivals to fire, so this drives a
// steady stream of real fires through the whole chain (not a fixed/dead
// value Quartus could optimize away). ──
reg [31:0] stim_cnt = 32'h0;
always @(posedge clk) if (!rst) stim_cnt <= stim_cnt + 32'h1;
wire        seed_pulse = (stim_cnt[7:0] == 8'h00);   // one cycle in 256
wire [31:0] seed_data  = {stim_cnt[15:0], stim_cnt[31:16]};  // varies fire-to-fire

// ── Freeze cycling on C — a slow counter bit, so the freeze/cascade path
// (#92/#93) runs continuously on real silicon, not just once. ──
wire freezeC = stim_cnt[13];   // toggles roughly every ~8k cycles each way

wire [31:0] a2b_data, b2c_data;
wire        a2b_fire, b2c_fire;
wire        a_ready, b_ready, c_ready;
wire        a2b_ack, b2c_ack;

unicell_stripped_v1 #(.CELL_ID(16'h0001)) A (
    .clk(clk), .rst(rst), .cfg_valid(cfgA), .cfg_data(cfgA_d),
    .data_in_n(seed_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(seed_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(a2b_data), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(a2b_fire), .fire_e(), .fire_w(),
    .ready_out(a_ready),
    .ready_in_n(1'b1), .ready_in_s(b_ready), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(a2b_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
    .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
    .freeze_in(1'b0),

    .hold_in(1'b0),


    .fb_internal_in(1'b0),



    .a_reemit_in(1'b0),



    .a_update_in(1'b0),




    .a_self_update_in(1'b0),





    .program_in(1'b0),





    .program_done(),






    .prog_data_in(32'h0),






    .prog_arrived_in(1'b0),






    .prog_ack_out()
);

unicell_stripped_v1 #(.CELL_ID(16'h0002)) B (
    .clk(clk), .rst(rst), .cfg_valid(cfgB), .cfg_data(cfgB_d),
    .data_in_n(a2b_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(a2b_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(b2c_data), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(b2c_fire), .fire_e(), .fire_w(),
    .ready_out(b_ready),
    .ready_in_n(1'b1), .ready_in_s(c_ready), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(a2b_ack), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(b2c_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
    .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
    .freeze_in(1'b0),

    .hold_in(1'b0),


    .fb_internal_in(1'b0),



    .a_reemit_in(1'b0),



    .a_update_in(1'b0),




    .a_self_update_in(1'b0),





    .program_in(1'b0),





    .program_done(),






    .prog_data_in(32'h0),






    .prog_arrived_in(1'b0),






    .prog_ack_out()
);

unicell_stripped_v1 #(.CELL_ID(16'h0003)) C (
    .clk(clk), .rst(rst), .cfg_valid(cfgC), .cfg_data(cfgC_d),
    .data_in_n(b2c_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(b2c_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(c_ready),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(b2c_ack), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
    .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
    .freeze_in(freezeC),

    .hold_in(1'b0),


    .fb_internal_in(1'b0),



    .a_reemit_in(1'b0),



    .a_update_in(1'b0),




    .a_self_update_in(1'b0),





    .program_in(1'b0),





    .program_done(),






    .prog_data_in(32'h0),






    .prog_arrived_in(1'b0),






    .prog_ack_out()
);

assign LED0_N = a_ready && b_ready && c_ready;   // active-low: lit = something stuck
assign LED1_N = ~stim_cnt[23];                    // slow heartbeat blink

endmodule
