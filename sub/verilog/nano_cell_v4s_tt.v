// nano_cell_v4s_tt.v -- CLONE of nano_cell_v4s.v (kept unchanged) with the per-bit topology decode replaced by a 4-bit truth table decoded once (1 Nov 2026, Alan 05:38).
// Same ports, same behaviour (checked against the original for all 1,024 topology words, tb_nano_tt_v1.v).
// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// nano_cell_v4s.v -- points.md #917: the stripped version of the real,
// original logic core, `nano_gate_v4c.v` -- the one cell this whole family
// has been missing since being flagged as the real structural exception back
// in #898/#899, finally built.
//
// The real function, read from nano_gate_v4c.v directly and verified by hand
// before trusting it (a full truth-table check against every one of its 12
// real cases, not assumed from the gate names alone): a universal 2-input
// logic function, selected by a `topology` field, applied between a HELD
// operand and a FLOWING one:
//   topology 10'h000: pass through HELD
//   topology 10'h02C: pass through FLOW
//   topology 10'h001: NOT HELD
//   topology 10'h002: NOT FLOW
//   topology 10'h004: NOR(HELD, FLOW)
//   topology 10'h007: AND(HELD, FLOW)
//   topology 10'h024: OR(HELD, FLOW)
//   topology 10'h027: NAND(HELD, FLOW)
//   topology 10'h0BC: XOR(HELD, FLOW)
//   topology 10'h03C: XNOR(HELD, FLOW)
//   topology 10'h030: constant all-zero
//   topology 10'h0B0: constant all-one
//   any other value: pass through HELD (the original's own default)
//
// The real structural exception this cell needed, per #898's own framing:
// every other v4s cell is fixed-role, single-shot-per-cycle -- this one
// genuinely needs TWO different input roles. The original solved this with
// `hold_in` (a continuous level: while high, the cell's `a_arrived` stays
// permanently set, so `input_val` keeps using the SAME captured value while
// `second_val` tracks each fresh arrival) plus cardinal arrival-order
// tracking to tell the two operands apart on a shared wire. With no more
// cardinal routing or arrival-order tricks in this family, the two roles get
// two genuinely dedicated ports instead: `hold_in_data` (loaded rarely, via
// an explicit `load_hold` pulse -- there is no more "first arrival" to
// infer it from) and `flow_in_data` (a new value every time `valid_in`
// fires), matching the same "one dedicated wire per real role" principle
// `adder_cell_v4s.v`'s own `in_a`/`in_b` already established, applied here
// to a cell whose two roles are genuinely different in KIND (one persistent,
// one transient), not just two equal operands.
//
// What's stripped, same reasoning as every other v4s cell: the real 4-way
// cardinal routing (routing_mask/cardinal_edge/dynamic routing) is gone --
// a fixed, single output, the family's own "no cardinality" principle. Live
// reprogramming (program_in and the whole prog_id channel) is gone -- #899's
// own established choice, boot-load config only. Relay-vs-consume
// classification, internal feedback/self-update, and the ack/pending_ack
// mask machinery are all gone -- that machinery existed specifically to
// serve cardinal routing and live reprogramming, both removed here.
//
// cfg_data field map:
//   [9:0] topology -- the same 12 real gate codes, unchanged from the original
`default_nettype none
`timescale 1ns / 1ps

module nano_cell_v4s_tt #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [31:0]  hold_in_data,
    input  wire         load_hold,     // explicit "capture hold_in_data now" pulse

    input  wire [31:0]  flow_in_data,
    input  wire         valid_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg [9:0]  topology    = 10'h0;
    reg        armed       = 1'b0;
    reg [31:0] held_value  = 32'h0;
    reg [31:0] out_buffer  = 32'h0;
    reg        valid_out_r = 1'b0;

    // ── The real gate logic -- unchanged from nano_gate_v4c.v, verified by
    // a full truth-table check before trusting it, not assumed from names ──
    // TRUTH-TABLE form (1 Nov 2026): every one of the 12 topologies is a bitwise function of (HELD bit, FLOW bit), i.e. a 4-bit table decoded ONCE
    // from the 10-bit topology, instead of decoding the topology for every bit. Same behaviour for all 1,024 topology words (undefined ones keep HELD).
    reg [3:0] tt;
    always_comb case (topology)
        10'h000: tt = 4'b1010;   // HELD
        10'h02C: tt = 4'b1100;   // FLOW
        10'h001: tt = 4'b0101;   // NOT HELD
        10'h002: tt = 4'b0011;   // NOT FLOW
        10'h004: tt = 4'b0001;   // NOR
        10'h007: tt = 4'b1000;   // AND
        10'h024: tt = 4'b1110;   // OR
        10'h027: tt = 4'b0111;   // NAND
        10'h0BC: tt = 4'b0110;   // XOR
        10'h03C: tt = 4'b1001;   // XNOR
        10'h030: tt = 4'b0000;   // constant 0
        10'h0B0: tt = 4'b1111;   // constant 1
        default: tt = 4'b1010;   // HELD
    endcase
    wire [31:0] computed_output;
    genvar gi;
    generate for (gi = 0; gi < 32; gi = gi + 1) begin : g_tt
        assign computed_output[gi] = tt[{flow_in_data[gi], held_value[gi]}];
    end endgenerate
    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            topology    <= 10'h0;
            armed       <= 1'b0;
            held_value  <= 32'h0;
            out_buffer  <= 32'h0;
            valid_out_r <= 1'b0;
        end else if (cfg_valid) begin
            topology    <= cfg_data[9:0];
            armed       <= 1'b1;
            valid_out_r <= 1'b0;
        end else begin
            if (load_hold) held_value <= hold_in_data;
            out_buffer  <= computed_output;
            valid_out_r <= armed && valid_in;
        end
    end

endmodule
