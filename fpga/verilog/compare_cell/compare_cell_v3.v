// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// compare_cell_v3.v — points.md #584: a real, THIRD axis on this
// core's own design space, distinct from v2's own EXTERNAL_STORAGE
// parameter (#563, which moved RUNTIME state out to a shared register
// and was found, at the shell level, to cost far more than it saved --
// #575/#580's own real write-arbitration finding). This file changes
// NOTHING about runtime state -- out_buffer/data_valid/pending_ack
// stay exactly where v1 already keeps them, real per-core registers,
// matching the cheapest real design measured so far (#579's own v3
// baseline). The ONE real change, per Alan's own real, direct
// proposal: downstream_mask/upstream_mask/threshold are no longer
// re-latched into a private local copy on cfg_valid. Confirmed
// directly against unicell_super_v3.v's own real RTL before writing
// this file: the shell ALREADY holds this exact same information,
// stable, continuously, in its own `core_config` register
// (`super_latch[46:5]`) for as long as this core stays selected --
// v1 was building and holding a second, fully redundant copy inside
// every core, for no real reason. This core now simply reads its own
// config fields straight off a CONTINUOUSLY-VALID `cfg_data` input
// (the shell must wire this to `core_config`, NOT the transient
// `incoming_config` pulse v1 uses -- see unicell_super_v6.v).
//
// WHY THIS IS SAFE, confirmed against the real RTL, not assumed:
// arrived_n/s/e/w are ALREADY AND-gated with sel_active_cmp at the
// shell level (`unicell_super_v3.v`'s own real, existing wiring,
// unchanged) -- so any_upstream_arrived is force-zero whenever this
// core isn't genuinely selected, REGARDLESS of what core_config
// happens to hold at that moment (another core's own real config
// fields, reused bit positions, since core_config is shared budget
// across all 8 core types). capture_now can therefore never fire on
// a misread config value while deselected -- the combinational
// result_bit may glitch to nonsense while deselected, but nothing
// ever LATCHES it unless a genuine capture event occurs, which
// structurally cannot happen while deselected. The exact same real
// reasoning `#563`/`#564`'s own differential testbenches already
// relied on for shared runtime state applies here even more safely,
// since config is read-only from this core's own perspective -- no
// write-back, no arbitration, a single source (the host, via
// cfg_valid into super_latch) already writes it once.
//
// cfg_data[63:0] field map — UNCHANGED from v1:
//   [3:0]   downstream_mask   — where the boolean result is offered
//   [7:4]   upstream_mask     — where the value to compare arrives from
//   [39:8]  threshold         — the configured reference (32-bit signed)
//   [63:40] reserved
`default_nettype none
`timescale 1ns / 1ps

module compare_cell_v3 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,   // points.md #584: must be CONTINUOUSLY
                                    // valid (wired to the shell's own
                                    // core_config), NOT the transient
                                    // one-shot pulse v1's own cfg_data
                                    // port expects -- see the real,
                                    // precise reasoning above.

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire         status_data_valid
);

    // ── points.md #584: THE real change -- config fields read straight
    // off the continuously-valid cfg_data input, no local register, no
    // load-vs-hold mux. The shell's own super_latch already does that
    // holding once, centrally, for every core simultaneously. ──
    wire [3:0]  downstream_mask = cfg_data[3:0];
    wire [3:0]  upstream_mask   = cfg_data[7:4];
    wire signed [31:0] threshold = cfg_data[39:8];

    // ── UNCHANGED from v1: genuine runtime state, real per-core
    // registers, exactly where the cheapest real design (#579) keeps
    // it. ──
    reg [31:0] out_buffer  = 32'h0;
    reg        data_valid  = 1'b0;
    reg [3:0]  pending_ack = 4'h0;

    wire effective_freeze = freeze_in;

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire signed [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                                      (sel_s ? data_in_s : 32'h0) |
                                      (sel_e ? data_in_e : 32'h0) |
                                      (sel_w ? data_in_w : 32'h0);

    // Same doubly-full guard as v1 — don't capture a new value while
    // the previous comparison result is still undrained.
    wire capture_now = any_upstream_arrived && !data_valid && !effective_freeze;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    // ── THE CORE — unchanged, a genuine two's-complement comparison ──
    wire result_bit = (upstream_val >= threshold);

    wire want_to_offer = data_valid && !effective_freeze;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    assign ready_out = !effective_freeze && !data_valid;
    assign status_data_valid = data_valid;

    // ── points.md #584: the reset/reload block is now ONLY about
    // genuine runtime state -- no config fields left to latch here at
    // all. ──
    always @(posedge clk) begin
        if (rst) begin
            out_buffer      <= 32'h0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else begin
            if (capture_now) begin
                out_buffer <= {31'h0, result_bit};
                data_valid <= 1'b1;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
