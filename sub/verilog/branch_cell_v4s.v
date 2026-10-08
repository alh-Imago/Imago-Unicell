// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// branch_cell_v4s.v -- the sub-family (fixed-latency, no ack) branch. Completes the v4s cell set.
//
// Alan's call (4 Oct 2026, after #934 showed flex-at-32-bits-with-the-handshake-tied-off behaves exactly like sub on 12 of 12
// shared cells): "you can use the branch v4sa as the basis for the v4s version, a slight change but it completes the picture
// for the v4s (sub) set of cell types." So this is branch_cell_v4sa.v with EXACTLY the transformation every other v4s cell
// already shows against its v4sa twin (read from adder_cell_v4s vs adder_cell_v4sa, not assumed):
//   - freeze_in, ack_out, ack_in_1, ack_in_2 and the WIDTH parameter are gone (fixed 32 bits);
//   - the pending_1 / pending_2 hold registers and the `busy` gate are gone: nothing is held waiting for an ack;
//   - the output is a plain pipeline stage: out_buffer is registered every cycle, and each output's valid is a one-cycle
//     registered pulse -- valid_out_N <= armed && real_event && target_N  (one cycle of latency, like every v4s cell).
// Everything about WHAT the cell decides is unchanged from branch_cell_v4sa.v: two dedicated inputs each runtime-selectable
// as fixed (held, reloaded by its own valid) or flowing; the 3-way signed compare of in1 against in2; ONE shared emit_source
// (fixed constant / in1 / in2 / diff = in1 - in2); per-outcome routing to out1, out2, both or neither.
//
// cfg_data field map (identical to branch_cell_v4sa.v):
//   [0] in1_fixed_mode   [1] in2_fixed_mode   [3:2] emit_source (00 fixed, 01 in1, 10 in2, 11 diff)
//   [5:4] route_low   [7:6] route_equal   [9:8] route_high   -- each: bit0 = out1, bit1 = out2 (neither = swallow)
// cfg_emit_fixed_value[31:0]: its own port (does not fit alongside everything else in one 32-bit cfg_data).
//
// Fixed-latency contract (same as the rest of the family): no backpressure. The caller must present rounds no faster than it
// wants results, and converging paths must be latency-matched; a round routed to neither output simply produces no pulse.
`default_nettype none
`timescale 1ns / 1ps

module branch_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,
    input  wire [31:0]  cfg_emit_fixed_value,

    input  wire [31:0]  in1_data,
    input  wire         in1_valid,
    input  wire [31:0]  in2_data,
    input  wire         in2_valid,

    output wire [31:0]  data_out_1,
    output wire         valid_out_1,
    output wire [31:0]  data_out_2,
    output wire         valid_out_2
);

    reg        in1_fixed_mode = 1'b0;
    reg        in2_fixed_mode = 1'b0;
    reg [1:0]  emit_source    = 2'b00;
    reg [1:0]  route_low      = 2'b00;
    reg [1:0]  route_equal    = 2'b00;
    reg [1:0]  route_high     = 2'b00;
    reg        armed          = 1'b0;

    reg [31:0] held1_reg    = 32'h0;
    reg [31:0] held2_reg    = 32'h0;
    reg        has_loaded_1 = 1'b0;
    reg        has_loaded_2 = 1'b0;

    reg [31:0] out_buffer    = 32'h0;
    reg        valid_out_1_r = 1'b0;
    reg        valid_out_2_r = 1'b0;

    // The value actually compared this cycle: the live input if flowing, the stored register if fixed.
    wire [31:0] live1 = in1_fixed_mode ? held1_reg : in1_data;
    wire [31:0] live2 = in2_fixed_mode ? held2_reg : in2_data;

    // A "round" is ready once both sides have a usable value THIS cycle: a fixed side once it has ever been loaded, a flowing
    // side only on the cycle its own valid fires.
    wire in1_ready_now = in1_fixed_mode ? has_loaded_1 : in1_valid;
    wire in2_ready_now = in2_fixed_mode ? has_loaded_2 : in2_valid;
    wire real_event    = in1_ready_now && in2_ready_now;

    wire signed [31:0] signed1 = live1;
    wire signed [31:0] signed2 = live2;
    wire is_low   = (signed1 <  signed2);
    wire is_equal = (signed1 == signed2);

    wire [1:0] active_route = is_low ? route_low : is_equal ? route_equal : route_high;
    wire target_1 = active_route[0];
    wire target_2 = active_route[1];

    wire [31:0] diff_val = live1 + (~live2) + 1'b1;     // in1 - in2, same convention as adder_cell_v4s's subtract_mode

    wire [31:0] emit_val = (emit_source == 2'b00) ? cfg_emit_fixed_value :
                           (emit_source == 2'b01) ? live1 :
                           (emit_source == 2'b10) ? live2 :
                                                    diff_val;

    assign data_out_1  = out_buffer;
    assign data_out_2  = out_buffer;
    assign valid_out_1 = valid_out_1_r;
    assign valid_out_2 = valid_out_2_r;

    always @(posedge clk) begin
        if (rst) begin
            in1_fixed_mode <= 1'b0;
            in2_fixed_mode <= 1'b0;
            emit_source    <= 2'b00;
            route_low      <= 2'b00;
            route_equal    <= 2'b00;
            route_high     <= 2'b00;
            armed          <= 1'b0;
            held1_reg      <= 32'h0;
            held2_reg      <= 32'h0;
            has_loaded_1   <= 1'b0;
            has_loaded_2   <= 1'b0;
            out_buffer     <= 32'h0;
            valid_out_1_r  <= 1'b0;
            valid_out_2_r  <= 1'b0;
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
            valid_out_1_r  <= 1'b0;
            valid_out_2_r  <= 1'b0;
        end else begin
            // Loading a fixed input is a silent side effect: it changes what future comparisons use, but is not an offer.
            if (in1_fixed_mode && in1_valid) begin
                held1_reg    <= in1_data;
                has_loaded_1 <= 1'b1;
            end
            if (in2_fixed_mode && in2_valid) begin
                held2_reg    <= in2_data;
                has_loaded_2 <= 1'b1;
            end
            // Pipeline stage: data every cycle, one registered valid pulse per targeted output. Routed to neither: the round is
            // consumed (held state above already updated) but nothing is offered downstream.
            out_buffer    <= emit_val;
            valid_out_1_r <= armed && real_event && target_1;
            valid_out_2_r <= armed && real_event && target_2;
        end
    end

endmodule
