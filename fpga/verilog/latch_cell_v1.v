// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// latch_cell_v1.v — closes the real gap `#295` identified directly:
// `compare_cell_v1.v` is stateless (reports the CURRENT comparison
// fresh every time), but `sentinel_counter_v1/v2.v`'s own `err_
// overflow`/`err_negative` are STICKY (latch once true, stay true
// until an explicit host action). A genuine new CORE, per `#253`'s
// SHELL/CORE model.
//
// Structurally the SAME pattern as `accumulator_cell_v1.v` — a
// continuously-live status that never goes back to "empty" just
// because it's been read downstream — but SET/CLEAR semantics instead
// of increment/decrement: arrivals on `set_dir` latch the value to 1
// and STAY there regardless of how many times it's read; arrivals on
// `clear_dir` reset it to 0. CLEAR TAKES PRIORITY if both arrive the
// same cycle — matching `#279`/`#284`'s own established rule that an
// explicit host action always wins over an ongoing trigger condition
// (the same reason `sentinel_counter_v1.v`'s own error-latch priority
// bug — `#281` — got fixed the way it did).
//
// Same real, deliberate protocol adaptation as the accumulator
// (`#294`'s own header explains the general reasoning): the internal
// latch state updates immediately and unconditionally on every real
// set/clear event — a slow downstream reader must never cause a
// missed set or a missed clear. The OFFERED snapshot only refreshes
// when free to accept a new one, keeping the standard "offered data
// stays stable until acked" shell protocol every other cell here has.
//
// cfg_data[63:0] field map:
//   [3:0]   set_dir           — one-hot direction, arrivals here latch to 1
//   [7:4]   clear_dir         — one-hot direction, arrivals here clear to 0
//   [11:8]  downstream_mask   — where the current latched value is offered
//   [63:12] reserved
`default_nettype none
`timescale 1ns / 1ps

module latch_cell_v1 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire         ready_out,   // same fix as accumulator_cell_v1.v — this port was missing
                                      // entirely. Capture is unconditional by design, so ready_out
                                      // is simply "not frozen."
    output wire         status_latched   // the raw internal latch state, for debug/bridging
);

    reg [3:0] set_dir         = 4'h0;
    reg [3:0] clear_dir       = 4'h0;
    reg [3:0] downstream_mask = 4'h0;

    reg latched    = 1'b0;   // ALWAYS correct, unconditional update, never blocked
    reg out_buffer = 1'b0;   // the OFFERED snapshot — stable while a transfer is in flight
    reg data_valid = 1'b0;
    reg [3:0] pending_ack = 4'h0;

    wire effective_freeze = freeze_in;

    wire sel_set_n = arrived_n && set_dir[0];
    wire sel_set_s = arrived_s && set_dir[1];
    wire sel_set_e = arrived_e && set_dir[2];
    wire sel_set_w = arrived_w && set_dir[3];
    // REAL BUG FIX, found via tb_sentinel_discrete_full_v1.v's own
    // integration test: an earlier draft treated ANY arrival on
    // set_dir as a trigger, regardless of the actual VALUE carried —
    // meaning a genuinely correct "0" (not-over-threshold) reading
    // from compare_cell_v1.v's own continuous output was
    // misinterpreted as a SET, immediately re-latching right after a
    // real clear. Fixed: only an arrival that actually CARRIES a 1
    // triggers a set. Confirmed via direct signal tracing, not
    // reasoning alone — the comparator's own output was already
    // correctly showing 0 when the bug fired.
    wire set_arrived_value = (sel_set_n ? data_in_n[0] : 1'b0) |
                             (sel_set_s ? data_in_s[0] : 1'b0) |
                             (sel_set_e ? data_in_e[0] : 1'b0) |
                             (sel_set_w ? data_in_w[0] : 1'b0);
    wire capture_set = (sel_set_n | sel_set_s | sel_set_e | sel_set_w) && !effective_freeze && set_arrived_value;

    wire sel_clr_n = arrived_n && clear_dir[0];
    wire sel_clr_s = arrived_s && clear_dir[1];
    wire sel_clr_e = arrived_e && clear_dir[2];
    wire sel_clr_w = arrived_w && clear_dir[3];
    wire capture_clr = (sel_clr_n | sel_clr_s | sel_clr_e | sel_clr_w) && !effective_freeze;

    assign ack_out_n = (sel_set_n || sel_clr_n) && !effective_freeze;
    assign ack_out_s = (sel_set_s || sel_clr_s) && !effective_freeze;
    assign ack_out_e = (sel_set_e || sel_clr_e) && !effective_freeze;
    assign ack_out_w = (sel_set_w || sel_clr_w) && !effective_freeze;

    // CLEAR takes priority — same rule #279/#284 already established
    // for the monolithic sentinel's own error latches.
    wire next_latched = capture_clr ? 1'b0 : capture_set ? 1'b1 : latched;

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

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = {31'h0, out_buffer};
    assign data_out_s = {31'h0, out_buffer};
    assign data_out_e = {31'h0, out_buffer};
    assign data_out_w = {31'h0, out_buffer};

    assign status_latched = latched;
    assign ready_out = !effective_freeze;   // always genuinely ready — capture is never blocked

    always @(posedge clk) begin
        if (rst) begin
            latched         <= 1'b0;
            out_buffer      <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            set_dir         <= 4'h0;
            clear_dir       <= 4'h0;
            downstream_mask <= 4'h0;
        end else if (cfg_valid) begin
            set_dir         <= cfg_data[3:0];
            clear_dir       <= cfg_data[7:4];
            downstream_mask <= cfg_data[11:8];
            latched         <= 1'b0;
            out_buffer      <= 1'b0;
            data_valid      <= 1'b1;   // live from the first cycle after config
            pending_ack     <= 4'h0;
        end else begin
            if (capture_set || capture_clr) begin
                latched <= next_latched;
            end

            if (pending_ack == 4'h0) begin
                out_buffer <= next_latched;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
