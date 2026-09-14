// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// latch_cell_v2.v — points.md #563: cloned from latch_cell_v1.v,
// zero behavioral change to the default path. Adds a genuinely
// OPTIONAL external-storage capability, per Alan's own real framing:
// "as a wrapper it's an optional extra, not a core function." The
// core's own computation logic (CLEAR>SET>TOGGLE, the real capture/
// offer protocol) is completely unchanged from v1 -- only WHERE the
// persistent state physically lives becomes selectable.
//
// THE REAL MECHANISM: a new parameter, EXTERNAL_STORAGE (default 0).
// - EXTERNAL_STORAGE=0 (default): every internal reg declared and
//   updated exactly as in v1. The two new ext_state_* ports exist
//   (Verilog module ports can't be conditional on a parameter) but
//   are simply unused -- safe to leave unconnected at instantiation,
//   completely standard, zero real cost. Standalone use (self-tests,
//   anything today) needs zero changes at all.
// - EXTERNAL_STORAGE=1: the core holds NO internal state register of
//   its own for the 23 real persistent bits (set_dir, clear_dir,
//   downstream_mask, toggle_dir, latched, out_buffer, data_valid,
//   pending_ack) -- it reads its current state from `ext_state_in`
//   and drives its computed next-state onto `ext_state_out`, which an
//   external wrapper (e.g. a super carrier shell's own shared buffer)
//   is responsible for actually registering.
//
// Real, precise bit layout for the 23-bit external state word,
// chosen to match this file's own real field order exactly:
//   [3:0]   set_dir
//   [7:4]   clear_dir
//   [11:8]  downstream_mask
//   [15:12] toggle_dir
//   [16]    latched
//   [17]    out_buffer
//   [18]    data_valid
//   [22:19] pending_ack
`default_nettype none
`timescale 1ns / 1ps

module latch_cell_v2 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        EXTERNAL_STORAGE = 0
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

    output wire         ready_out,
    output wire         status_latched,

    // ── real, optional external-storage interface (points.md #563) --
    // unused and safe to leave unconnected when EXTERNAL_STORAGE=0. ──
    input  wire [22:0]  ext_state_in,
    output wire [22:0]  ext_state_out
);

    // ── Real, internal-mode registers -- used only when
    // EXTERNAL_STORAGE=0, byte-for-byte identical to v1. ──
    reg [3:0] int_set_dir         = 4'h0;
    reg [3:0] int_clear_dir       = 4'h0;
    reg [3:0] int_downstream_mask = 4'h0;
    reg [3:0] int_toggle_dir      = 4'h0;
    reg int_latched    = 1'b0;
    reg int_out_buffer = 1'b0;
    reg int_data_valid = 1'b0;
    reg [3:0] int_pending_ack = 4'h0;

    // ── Real, current-state view -- reads from external storage when
    // EXTERNAL_STORAGE=1, from the internal regs otherwise. Every
    // piece of real combinational logic below reads ONLY through
    // these wires, never the internal regs directly, so the same
    // logic works unmodified in both modes. ──
    wire [3:0] set_dir         = EXTERNAL_STORAGE ? ext_state_in[3:0]   : int_set_dir;
    wire [3:0] clear_dir       = EXTERNAL_STORAGE ? ext_state_in[7:4]   : int_clear_dir;
    wire [3:0] downstream_mask = EXTERNAL_STORAGE ? ext_state_in[11:8]  : int_downstream_mask;
    wire [3:0] toggle_dir      = EXTERNAL_STORAGE ? ext_state_in[15:12] : int_toggle_dir;
    wire       latched         = EXTERNAL_STORAGE ? ext_state_in[16]    : int_latched;
    wire       out_buffer      = EXTERNAL_STORAGE ? ext_state_in[17]    : int_out_buffer;
    wire       data_valid      = EXTERNAL_STORAGE ? ext_state_in[18]    : int_data_valid;
    wire [3:0] pending_ack     = EXTERNAL_STORAGE ? ext_state_in[22:19] : int_pending_ack;

    // ── Real computation logic, IDENTICAL to v1 -- reads only through
    // the wires above, never cares which mode is active. ──
    wire effective_freeze = freeze_in;

    wire sel_set_n = arrived_n && set_dir[0];
    wire sel_set_s = arrived_s && set_dir[1];
    wire sel_set_e = arrived_e && set_dir[2];
    wire sel_set_w = arrived_w && set_dir[3];
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

    wire sel_tog_n = arrived_n && toggle_dir[0];
    wire sel_tog_s = arrived_s && toggle_dir[1];
    wire sel_tog_e = arrived_e && toggle_dir[2];
    wire sel_tog_w = arrived_w && toggle_dir[3];
    wire capture_tog = (sel_tog_n | sel_tog_s | sel_tog_e | sel_tog_w) && !effective_freeze;

    assign ack_out_n = (sel_set_n || sel_clr_n || sel_tog_n) && !effective_freeze;
    assign ack_out_s = (sel_set_s || sel_clr_s || sel_tog_s) && !effective_freeze;
    assign ack_out_e = (sel_set_e || sel_clr_e || sel_tog_e) && !effective_freeze;
    assign ack_out_w = (sel_set_w || sel_clr_w || sel_tog_w) && !effective_freeze;

    wire next_latched = capture_clr ? 1'b0 : capture_set ? 1'b1 : capture_tog ? ~latched : latched;

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

    wire next_out_buffer = (pending_ack == 4'h0) ? next_latched : out_buffer;

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = {31'h0, out_buffer};
    assign data_out_s = {31'h0, out_buffer};
    assign data_out_e = {31'h0, out_buffer};
    assign data_out_w = {31'h0, out_buffer};

    assign status_latched = latched;
    assign ready_out = !effective_freeze;

    // ── Real next-state computation, identical regardless of mode --
    // this is what gets registered internally OR driven externally. ──
    wire [3:0] next_set_dir         = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[3:0]   : set_dir;
    wire [3:0] next_clear_dir       = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[7:4]   : clear_dir;
    wire [3:0] next_downstream_mask = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[11:8]  : downstream_mask;
    wire [3:0] next_toggle_dir      = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[15:12] : toggle_dir;
    wire       next_latched_reg     = (rst) ? 1'b0 : (cfg_valid) ? 1'b0 : (capture_set || capture_clr || capture_tog) ? next_latched : latched;
    wire       next_out_buffer_reg  = (rst) ? 1'b0 : (cfg_valid) ? 1'b0 : next_out_buffer;
    wire       next_data_valid_reg  = (rst) ? 1'b0 : (cfg_valid) ? 1'b1 : data_valid;
    wire [3:0] next_pending_ack_reg = (rst) ? 4'h0 : (cfg_valid) ? 4'h0 : next_pending_ack;

    assign ext_state_out = {next_pending_ack_reg, next_data_valid_reg, next_out_buffer_reg,
                             next_latched_reg, next_toggle_dir, next_downstream_mask,
                             next_clear_dir, next_set_dir};

    // ── Real internal registration -- ONLY happens when
    // EXTERNAL_STORAGE=0. In external mode, this block simply doesn't
    // drive anything (the int_* regs are unused, matching a normal,
    // safe Verilog pattern for genuinely dead signals). ──
    generate
        if (!EXTERNAL_STORAGE) begin : internal_storage
            always @(posedge clk) begin
                int_set_dir         <= next_set_dir;
                int_clear_dir       <= next_clear_dir;
                int_downstream_mask <= next_downstream_mask;
                int_toggle_dir      <= next_toggle_dir;
                int_latched         <= next_latched_reg;
                int_out_buffer      <= next_out_buffer_reg;
                int_data_valid      <= next_data_valid_reg;
                int_pending_ack     <= next_pending_ack_reg;
            end
        end
    endgenerate

endmodule
