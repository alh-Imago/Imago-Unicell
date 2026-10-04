// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// branch_cell_v4sa.v -- points.md #918: the real Flex-Sub redesign of branch,
// resolving the architectural tension flagged since #898 (branch being the
// one cell whose whole job is a runtime decision). Designed through a full
// conversation with Alan, confirming the real original (branch_cell_v4c.v)
// first, then building the new shape together, point by point.
//
// Real differences from the original, each a deliberate, discussed choice:
//   - TWO dedicated inputs (in1, in2), each INDEPENDENTLY runtime-selectable
//     as fixed (held, reloaded via its own valid pulse, reused every firing)
//     or flowing (a fresh value expected every firing) -- matching ram_cell_
//     v4sa's own fixed/flowing choice, applied per-input here. This gives a
//     real new capability the original never had: comparing two genuinely
//     live streams against each other, not just one value against a held
//     reference.
//   - The 3-way signed compare (low/equal/high) is unchanged in spirit.
//   - emit_source is ONE SHARED, config-time choice (fixed constant / in1 /
//     in2 / diff), not independently chosen per outcome the way the
//     original's value_source_low/equal/high were -- a real, deliberate
//     simplification Alan chose once per-outcome value selection was found
//     to add real complexity for comparatively little value.
//   - diff = in1 - in2, true signed two's-complement subtraction, same
//     convention as adder_cell_v4sa.v's own subtract_mode.
//   - Per-outcome ROUTING (low/equal/high each independently choose out1,
//     out2, both, or neither) replaces the original's independent per-
//     outcome emit-enable AND routing-mask with one thing: routing to
//     "neither" IS the emit-disable case, for free -- no separate enable bit
//     needed. The original's routing could ALSO fan out across up to 4 real
//     cardinal directions simultaneously per outcome; here it is narrowed to
//     exactly 2 fixed ports, each independently selectable per outcome
//     (every real combination: out1 only, out2 only, both, or neither).
//   - ack/freeze: standard Flex-Sub shape. ONE shared ack_out gates
//     acceptance of a new (in1, in2) round -- the same "one ack per atomic
//     operand pair" principle adder_cell_v4sa.v's own single ack_out already
//     established, not two separate input acks. TWO independent output
//     pending/ack pairs, mirroring router_cell_v4sa.v's own per-output
//     handshake exactly, since a given firing may target either, both, or
//     neither output.
//
// cfg_data field map:
//   [0]   in1_fixed_mode
//   [1]   in2_fixed_mode
//   [3:2] emit_source   -- 00=fixed constant, 01=in1, 10=in2, 11=diff(in1-in2)
//   [5:4] route_low     -- bit0=out1, bit1=out2 (any combination, including neither)
//   [7:6] route_equal
//   [9:8] route_high
// cfg_emit_fixed_value[WIDTH-1:0]: its own port, same reason sequencer_cell_v4s.v
// and ram_cell_v4s.v each needed one -- does not fit alongside everything
// else in one 32-bit cfg_data.
`default_nettype none
`timescale 1ns / 1ps

module branch_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,
    input  wire [WIDTH-1:0] cfg_emit_fixed_value,

    input  wire [WIDTH-1:0]  in1_data,
    input  wire               in1_valid,
    input  wire [WIDTH-1:0]  in2_data,
    input  wire               in2_valid,
    output wire                ack_out,     // ONE shared ack, gates a new (in1,in2) round

    output wire [WIDTH-1:0]  data_out_1,
    output wire               valid_out_1,
    input  wire                ack_in_1,

    output wire [WIDTH-1:0]  data_out_2,
    output wire               valid_out_2,
    input  wire                ack_in_2
);

    reg        in1_fixed_mode = 1'b0;
    reg        in2_fixed_mode = 1'b0;
    reg [1:0]  emit_source    = 2'b00;
    reg [1:0]  route_low      = 2'b00;
    reg [1:0]  route_equal    = 2'b00;
    reg [1:0]  route_high     = 2'b00;
    reg        armed          = 1'b0;

    reg [WIDTH-1:0] held1_reg = {WIDTH{1'b0}};
    reg [WIDTH-1:0] held2_reg = {WIDTH{1'b0}};
    reg             has_loaded_1 = 1'b0;
    reg             has_loaded_2 = 1'b0;

    reg pending_1 = 1'b0;
    reg pending_2 = 1'b0;
    reg [WIDTH-1:0] out_buffer = {WIDTH{1'b0}};

    // ── Which value is actually used for this cycle's comparison -- the
    // live input if flowing, the stored register if fixed. ──────────────
    wire [WIDTH-1:0] live1 = in1_fixed_mode ? held1_reg : in1_data;
    wire [WIDTH-1:0] live2 = in2_fixed_mode ? held2_reg : in2_data;

    // ── A "round" is ready once both sides have a usable value THIS
    // cycle: a fixed side is ready once it has ever been loaded; a flowing
    // side is ready only on the cycle its own valid fires. ──────────────
    wire in1_ready_now = in1_fixed_mode ? has_loaded_1 : in1_valid;
    wire in2_ready_now = in2_fixed_mode ? has_loaded_2 : in2_valid;
    wire real_event    = in1_ready_now && in2_ready_now;

    wire busy = pending_1 || pending_2;
    assign ack_out = armed && !busy && !freeze_in;

    // ── The real 3-way signed compare -- unchanged in spirit from the
    // original's is_low/is_equal/is_high. ────────────────────────────────
    wire signed [WIDTH-1:0] signed1 = live1;
    wire signed [WIDTH-1:0] signed2 = live2;
    wire is_low   = (signed1 <  signed2);
    wire is_equal = (signed1 == signed2);
    wire is_high  = (signed1 >  signed2);

    wire [1:0] active_route = is_low ? route_low : is_equal ? route_equal : route_high;
    wire target_1 = active_route[0];
    wire target_2 = active_route[1];

    // ── diff = in1 - in2, true signed subtraction, same convention as
    // adder_cell_v4sa.v's own subtract_mode. ─────────────────────────────
    wire [WIDTH-1:0] diff_val = live1 + (~live2) + 1'b1;

    wire [WIDTH-1:0] emit_val = (emit_source == 2'b00) ? cfg_emit_fixed_value :
                                (emit_source == 2'b01) ? live1 :
                                (emit_source == 2'b10) ? live2 :
                                                          diff_val;

    assign data_out_1  = out_buffer;
    assign data_out_2  = out_buffer;
    assign valid_out_1 = pending_1;
    assign valid_out_2 = pending_2;

    always @(posedge clk) begin
        if (rst) begin
            in1_fixed_mode <= 1'b0;
            in2_fixed_mode <= 1'b0;
            emit_source    <= 2'b00;
            route_low      <= 2'b00;
            route_equal    <= 2'b00;
            route_high     <= 2'b00;
            armed          <= 1'b0;
            held1_reg      <= {WIDTH{1'b0}};
            held2_reg      <= {WIDTH{1'b0}};
            has_loaded_1   <= 1'b0;
            has_loaded_2   <= 1'b0;
            pending_1      <= 1'b0;
            pending_2      <= 1'b0;
            out_buffer     <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            in1_fixed_mode <= cfg_data[0];
            in2_fixed_mode <= cfg_data[1];
            emit_source    <= cfg_data[3:2];
            route_low      <= cfg_data[5:4];
            route_equal    <= cfg_data[7:6];
            route_high     <= cfg_data[9:8];
            armed          <= 1'b1;
            has_loaded_1   <= 1'b0;   // a reconfigure is a fresh start -- reload required
            has_loaded_2   <= 1'b0;
            pending_1      <= 1'b0;
            pending_2      <= 1'b0;
        end else if (!freeze_in) begin
            // Loading a fixed input is a real, silent side effect -- same
            // reasoning as nano_cell_v4sa.v's own load_hold: it changes what
            // future comparisons use, but is not itself an offer.
            if (in1_fixed_mode && in1_valid) begin
                held1_reg    <= in1_data;
                has_loaded_1 <= 1'b1;
            end
            if (in2_fixed_mode && in2_valid) begin
                held2_reg    <= in2_data;
                has_loaded_2 <= 1'b1;
            end

            // Each output clears independently on its own ack -- real,
            // separate handshakes, same shape as router_cell_v4sa.v.
            if (pending_1 && ack_in_1) pending_1 <= 1'b0;
            if (pending_2 && ack_in_2) pending_2 <= 1'b0;

            // A new round is only captured once NEITHER output is still
            // busy (pre-edge busy, same priority discipline every other
            // v4sa cell uses) -- conservative: gates on both outputs being
            // free regardless of which the upcoming outcome will actually
            // target, since the real target is only known after the
            // compare itself runs.
            if (!busy && real_event) begin
                out_buffer <= emit_val;
                if (target_1) pending_1 <= 1'b1;
                if (target_2) pending_2 <= 1'b1;
                // target_1==target_2==0 (routed to neither): a real, valid
                // "swallow silently" case -- the round is consumed (fixed
                // inputs' own has_loaded/held state already updated above;
                // a flowing input's own round is simply over) but nothing
                // is offered downstream at all.
            end
        end
    end

endmodule
