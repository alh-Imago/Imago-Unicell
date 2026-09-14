// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// adder_cell_v4c.v — points.md #720: the "c" (carrier) variant of
// adder_cell_v4.v. Alan's own real, direct observation: the VIX
// carrier's whole design concept is to hold COMMON functionality
// centrally, so each wrapped core only does its own specific task --
// but adder_cell_v4's own internal 3-addon chain (nibble_mask/shift_
// lane/invert) duplicates exactly what the carrier itself is meant to
// provide once, shared across whichever core is active. Confirmed
// directly, not assumed: an audit of all 9 VIX core types found this
// EXACT SAME 3-addon chain built into 8 of the 9 (every one except
// command, which does programming/routing, not data transformation)
// -- a real, genuine case of the "inflation problem," not a one-off.
//
// adder_cell_v4.v itself is UNCHANGED and stays exactly as it is --
// still the real, proven, standalone core used wherever a carrier
// isn't wrapping it. This "c" variant exists ONLY for use inside a
// carrier that already supplies the addon chain itself.
//
// Real, honest scope of this specific file's own changes from v4:
//   1. The internal addon chain (nibble_mask_addon_v1/shift_lane_
//      addon_v1/invert_addon_v1) is REMOVED entirely -- data_out_n/s/
//      e/w now come directly from out_buffer, the real computed sum,
//      matching what data_out_n/s/e/w already were BEFORE the addon
//      chain's own real transform in v4.
//   2. addon_config (20 bits) is removed from cfg_data's own field
//      map, the register, and the live-programming PROG_ID case --
//      there is nothing left for it to configure at this core level.
//      cfg_data itself KEEPS its original 64-bit width (simpler, no
//      risk to any wiring elsewhere that assumes it) -- the bits
//      addon_config used to occupy are now genuinely reserved.
//   3. Real, honest, considered decision -- NOT the same fix v9's own
//      _v3 cells got: downstream_mask/upstream_mask/subtract_mode
//      STAY real registers here (latched on cfg_valid or the live
//      programming channel), not continuous wires. v9's own _v3 cells
//      have no live-programming channel at all, so reading core_config
//      continuously is both safe and the strongest fix (genuinely
//      always current). This cell's own live-programming channel
//      (program_in/prog_data_in, #617) genuinely NEEDS a register it
//      can independently write to -- a continuous wire would silence
//      that feature entirely. The real, correct config-off-shell fix
//      for a v4c cell lives at the SHELL level instead: the carrier
//      must feed this cell's own cfg_data from its own stable
//      core_config, not a transient incoming/about-to-commit value --
//      once that's true, every cfg_valid latch here reads the correct,
//      current value, and core_config's own UNION semantics (the same
//      physical bits mean this core's own fields ONLY while it's
//      actually selected) mean there is no real window where this
//      core's own config could change without cfg_valid also pulsing
//      for it.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   downstream_mask  — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  upstream_mask    — one-hot(s), N/S/E/W real + 2 reserved
//   [12]    subtract_mode    — 0=A+B, 1=A-B
//   [63:13] reserved (addon_config's own old home, now genuinely free)
`default_nettype none
`timescale 1ns / 1ps

module adder_cell_v4c #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         active,

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

    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         status_data_valid,
    output wire         status_a_arrived
);

    reg [31:0] a_reg           = 32'h0;
    reg        a_arrived       = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    reg        data_valid      = 1'b0;
    reg [5:0]  downstream_mask = 6'h0;
    reg [5:0]  upstream_mask   = 6'h0;
    reg        subtract_mode   = 1'b0;
    reg [3:0]  pending_ack     = 4'h0;
    reg        armed           = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    wire capture_now = any_upstream_arrived && !a_arrived && !effective_freeze &&
                       effective_armed && !program_in;
    wire can_fire = any_upstream_arrived && a_arrived && !data_valid && !effective_freeze &&
                    effective_armed && !program_in;

    assign ack_out_n = (capture_now || can_fire) && sel_n;
    assign ack_out_s = (capture_now || can_fire) && sel_s;
    assign ack_out_e = (capture_now || can_fire) && sel_e;
    assign ack_out_w = (capture_now || can_fire) && sel_w;

    // ── The real arithmetic — unchanged from v4/v1 ──────────────────
    wire [31:0] adder_b_in = subtract_mode ? ~upstream_val : upstream_val;
    wire [31:0] adder_sum;
    wire        adder_cout;
    adder_v1 #(.WIDTH(32)) ADD (
        .a(a_reg), .b(adder_b_in), .cin(subtract_mode),
        .sum(adder_sum), .cout(adder_cout)
    );

    wire want_to_offer = data_valid && !effective_freeze && effective_armed;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask[3:0] & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    // ── points.md #720: NO addon chain here at all — the carrier
    // already provides one, shared across whichever core is active.
    // data_out_n/s/e/w are the real computed sum, directly. ──
    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    assign ready_out = effective_armed && !effective_freeze && !(a_arrived && data_valid);
    assign status_data_valid = data_valid;
    assign status_a_arrived  = a_arrived;

    // points.md #720: PROG_ID_ADDON_CONFIG removed -- nothing left at
    // this core level for it to configure. IDs kept numerically stable
    // for the three real remaining fields (matching v4's own numbering
    // exactly, so a v4-vs-v4c swap doesn't also require re-deriving
    // programming words elsewhere).
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd0;
    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd1;
    localparam [2:0] PROG_ID_SUBTRACT_MODE   = 3'd2;
    localparam [2:0] PROG_ID_COMPLETE        = 3'd7;

    wire prog_any_arrived = prog_arrived_in_n | prog_arrived_in_s | prog_arrived_in_e | prog_arrived_in_w;
    wire prog_sel_n = prog_arrived_in_n;
    wire prog_sel_s = prog_arrived_in_s && !prog_arrived_in_n;
    wire prog_sel_e = prog_arrived_in_e && !prog_arrived_in_n && !prog_arrived_in_s;
    wire prog_sel_w = prog_arrived_in_w && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e;
    wire [31:0] prog_data_val = prog_sel_n ? prog_data_in_n :
                                prog_sel_s ? prog_data_in_s :
                                prog_sel_e ? prog_data_in_e :
                                             prog_data_in_w;
    wire [2:0]  prog_id   = prog_data_val[22:20];
    wire [19:0] prog_word = prog_data_val[19:0];

    wire programming_active = program_in && active && prog_any_arrived;
    assign program_done = program_done_r;
    reg   program_done_r = 1'b0;

    assign prog_ack_out_n = programming_active && prog_sel_n;
    assign prog_ack_out_s = programming_active && prog_sel_s;
    assign prog_ack_out_e = programming_active && prog_sel_e;
    assign prog_ack_out_w = programming_active && prog_sel_w;

    always @(posedge clk) begin
        if (rst) begin
            a_reg           <= 32'h0;
            a_arrived       <= 1'b0;
            out_buffer      <= 32'h0;
            data_valid      <= 1'b0;
            downstream_mask <= 6'h0;
            upstream_mask   <= 6'h0;
            subtract_mode   <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            subtract_mode   <= cfg_data[12];
            a_arrived       <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask   <= prog_word[5:0];
                PROG_ID_SUBTRACT_MODE:   subtract_mode   <= prog_word[0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (can_fire) begin
                out_buffer <= adder_sum;
                data_valid <= 1'b1;
                a_arrived  <= 1'b0;
            end else if (capture_now) begin
                a_reg     <= upstream_val;
                a_arrived <= 1'b1;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end
            pending_ack <= next_pending_ack;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
