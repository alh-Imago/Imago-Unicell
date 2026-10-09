// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// ram_cell_v3.v — points.md #699: the same real config-off-shell
// change `#584`/`#587`/`#592` already applied to compare/latch/
// accumulator, now applied to RAM for the first time. Real, careful
// distinction made before writing this, not assumed: RAM has BOTH
// real, ongoing config fields (downstream_mask/upstream_mask/
// fixed_mode — read every cycle for live routing/offer behavior) AND
// real, genuine one-time SEED fields (`load_data_valid`/`init_data`,
// cfg_data[9]/[41:10] — used only at the instant of `cfg_valid` to
// write `data_reg`/`data_valid` once, then never referenced as config
// again; `data_reg`/`data_valid` become pure runtime state from that
// point on, managed entirely by `capture_now`/`offer_draining`).
// Confirmed directly against `ram_cell_v1.v`'s own real always block
// before changing anything: `fixed_mode` IS read every cycle after
// config (`!fixed_mode && offer_draining`), so it belongs in the
// continuous group alongside downstream_mask/upstream_mask -- it is
// NOT a one-time seed like `load_data_valid`/`init_data` are. This
// file changes NOTHING about `data_reg`/`data_valid`/`pending_ack` --
// real per-core runtime state, kept exactly where v1 already keeps
// it, matching `compare_cell_v3.v`'s own real discipline exactly.
//
// The shell wiring this file needs (matching `unicell_super_v6.v`'s
// own real precedent for compare): `cfg_data` must be wired to the
// shell's own continuously-valid `core_config`, NOT the transient
// `incoming_config` pulse v1 uses -- `load_data_valid`/`init_data`
// still only take effect through the real `cfg_valid` pulse itself
// (a real, one-time write trigger, unaffected by which wire feeds
// `cfg_data` the rest of the time).
//
// WHY THIS IS SAFE, confirmed against the real RTL, not assumed:
// arrived_n/s/e/w are already AND-gated with sel_active_ram at the
// shell level (unchanged) -- so ram_any_upstream_arrived is force-zero
// whenever this core isn't genuinely selected, regardless of what
// core_config happens to hold at that moment. capture_now can
// therefore never fire on a misread config value while deselected --
// the same real reasoning `compare_cell_v3.v`'s own header already
// relied on.
`default_nettype none
`timescale 1ns / 1ps

module ram_cell_v3 #(
    parameter [15:0] CELL_ID = 16'h0000  // fixed grid position, identification only
) (
    input  wire        clk,
    input  wire         rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

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

    // ── Real config fields, read CONTINUOUSLY off cfg_data (#699) --
    // no local latch at all for these three. ──────────────────────
    wire [3:0] downstream_mask = cfg_data[3:0];
    wire [3:0] upstream_mask   = cfg_data[7:4];
    wire       fixed_mode      = cfg_data[8];

    // ── Real, genuine runtime state -- unchanged from v1, still a
    // real per-core register, seeded ONCE by cfg_valid's own real
    // load_data_valid/init_data fields, then managed entirely by
    // capture_now/offer_draining below. ──────────────────────────
    reg [31:0] data_reg        = 32'h0;
    reg        data_valid      = 1'b0;
    reg [3:0]  pending_ack     = 4'h0;

    wire effective_freeze = freeze_in;

    wire ram_sel_n = arrived_n && upstream_mask[0];
    wire ram_sel_s = arrived_s && upstream_mask[1];
    wire ram_sel_e = arrived_e && upstream_mask[2];
    wire ram_sel_w = arrived_w && upstream_mask[3];
    wire ram_any_upstream_arrived = ram_sel_n | ram_sel_s | ram_sel_e | ram_sel_w;
    wire [31:0] upstream_val = (ram_sel_n ? data_in_n : 32'h0) |
                               (ram_sel_s ? data_in_s : 32'h0) |
                               (ram_sel_e ? data_in_e : 32'h0) |
                               (ram_sel_w ? data_in_w : 32'h0);

    wire capture_now = ram_any_upstream_arrived && !data_valid && !fixed_mode && !effective_freeze;

    assign ack_out_n = capture_now && ram_sel_n;
    assign ack_out_s = capture_now && ram_sel_s;
    assign ack_out_e = capture_now && ram_sel_e;
    assign ack_out_w = capture_now && ram_sel_w;

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

    assign data_out_n = data_reg;
    assign data_out_s = data_reg;
    assign data_out_e = data_reg;
    assign data_out_w = data_reg;

    assign ready_out = !data_valid && !fixed_mode && !effective_freeze;
    assign status_data_valid = data_valid;

    always @(posedge clk) begin
        if (rst) begin
            data_reg        <= 32'h0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            // load_data_valid/init_data -- real, genuine ONE-TIME
            // seeds, unchanged from v1. downstream_mask/upstream_mask/
            // fixed_mode are no longer latched here at all (#699).
            data_valid      <= cfg_data[9];
            data_reg        <= cfg_data[41:10];
            pending_ack     <= 4'h0;
        end else begin
            if (capture_now) begin
                data_reg   <= upstream_val;
                data_valid <= 1'b1;
            end else if (!fixed_mode && offer_draining) begin
                data_valid <= 1'b0;
            end
            pending_ack <= next_pending_ack;
        end
    end

endmodule
